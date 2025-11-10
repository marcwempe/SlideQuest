from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

from PySide6.QtCore import QObject, QUrl, Signal, QVariantAnimation
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

from slidequest.models.slide import PlaylistTrack
from slidequest.utils.media import resolve_media_path


class PlayerKey(NamedTuple):
    context: int
    index: int


class AudioService(QObject):
    track_state_changed = Signal(int, bool)
    position_changed = Signal(int, int)
    duration_changed = Signal(int, int)

    def __init__(self) -> None:
        super().__init__()
        self._context_counter = 0
        self._active_context = 0
        self._context_tracks: dict[int, list[PlaylistTrack]] = {self._active_context: []}
        self._players: dict[PlayerKey, tuple[QMediaPlayer, QAudioOutput]] = {}
        self._track_durations: dict[PlayerKey, int] = {}
        self._track_fade_levels: dict[PlayerKey, float] = {}
        self._fade_animations: dict[PlayerKey, QVariantAnimation] = {}
        self._auto_next_triggered: set[PlayerKey] = set()
        self._manual_stop_fades: set[PlayerKey] = set()
        self._pending_play: set[PlayerKey] = set()
        self._master_volume = 1.0

    def _current_tracks(self) -> list[PlaylistTrack]:
        return self._context_tracks.setdefault(self._active_context, [])

    def _set_current_tracks(self, tracks: list[PlaylistTrack]) -> None:
        self._context_tracks[self._active_context] = tracks or []

    def _make_key(self, index: int, context: int | None = None) -> PlayerKey:
        ctx = self._active_context if context is None else context
        return PlayerKey(ctx, index)

    def _get_track_for_key(self, key: PlayerKey) -> PlaylistTrack | None:
        tracks = self._context_tracks.get(key.context)
        if tracks and 0 <= key.index < len(tracks):
            return tracks[key.index]
        return None

    def _cleanup_context(self, context: int) -> None:
        if any(key.context == context for key in self._players.keys()):
            return
        self._context_tracks.pop(context, None)

    def set_tracks(self, tracks: list[PlaylistTrack], *, new_context: bool = False) -> None:
        was_empty = True if new_context else not self._current_tracks()
        if new_context or self._active_context not in self._context_tracks:
            self._context_counter += 1
            self._active_context = self._context_counter
        self._set_current_tracks(tracks or [])
        current_tracks = self._current_tracks()
        invalid_keys = [
            key for key in self._players.keys() if key.context == self._active_context and key.index >= len(current_tracks)
        ]
        for key in invalid_keys:
            self.stop(key.index)
        def prune_dict(source: dict[PlayerKey, object]) -> None:
            removable = [
                key for key in source.keys() if key.context == self._active_context and key.index >= len(current_tracks)
            ]
            for key in removable:
                source.pop(key, None)

        prune_dict(self._track_durations)
        prune_dict(self._fade_animations)
        prune_dict(self._track_fade_levels)
        self._auto_next_triggered = {
            key for key in self._auto_next_triggered if key.context != self._active_context or key.index < len(current_tracks)
        }
        self._manual_stop_fades = {
            key for key in self._manual_stop_fades if key.context != self._active_context or key.index < len(current_tracks)
        }
        self._pending_play = {
            key for key in self._pending_play if key.context != self._active_context or key.index < len(current_tracks)
        }
        if current_tracks and not any(key.context == self._active_context for key in self._players.keys()) and was_empty:
            self._ensure_player(0, preload_only=True)

    def play(self, index: int, position_ms: int | None = None, *, context: int | None = None) -> None:
        key = self._make_key(index, context)
        slot = self._ensure_player(index, context=context)
        if slot is None:
            return
        self._stop_fade_animation(key)
        if position_ms is not None:
            slot[0].setPosition(position_ms)
        track = self._get_track_for_key(key)
        fade_in_ms = int(track.fade_in_seconds * 1000) if track else 0
        if fade_in_ms > 0:
            self._set_track_fade_level(key, 0.0)
            self._start_fade_animation(key, fade_in_ms, 0.0, 1.0)
        slot[0].play()
        self._pending_play.add(key)
        if fade_in_ms <= 0:
            self._set_track_fade_level(key, 1.0)
            self._apply_fade_volume(key, slot[0].position())
        self.track_state_changed.emit(index, True)

    def stop(self, index: int | None = None, *, context: int | None = None) -> None:
        if index is None:
            keys = [key for key in self._players.keys() if context is None or key.context == context]
            for key in keys:
                self.stop(key.index, context=key.context)
            return
        key = self._make_key(index, context)
        slot = self._players.pop(key, None)
        if slot is None:
            return
        self._stop_fade_animation(key)
        slot[0].stop()
        slot[0].deleteLater()
        slot[1].deleteLater()
        self._track_fade_levels.pop(key, None)
        if key.context == self._active_context:
            self.track_state_changed.emit(index, False)
        self._auto_next_triggered.discard(key)
        self._manual_stop_fades.discard(key)
        self._pending_play.discard(key)
        self._track_durations.pop(key, None)
        self._cleanup_context(key.context)

    def stop_with_fade(self, index: int, *, context: int | None = None) -> None:
        key = self._make_key(index, context)
        slot = self._players.get(key)
        if slot is None:
            return
        track = self._get_track_for_key(key)
        fade_ms = int(track.fade_out_seconds * 1000) if track else 0
        if fade_ms <= 0:
            self.stop(index, context=context)
            return
        self._manual_stop_fades.add(key)
        current_level = self._track_fade_levels.get(key, slot[1].volume())
        self._start_fade_animation(key, fade_ms, current_level, 0.0, stop_after=True)

    def set_master_volume(self, value: float) -> None:
        clamped = max(0.0, min(1.0, value))
        if clamped == self._master_volume:
            return
        self._master_volume = clamped
        self._apply_master_volume()

    def pause_all(self) -> None:
        for player, _output in self._players.values():
            if player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                player.pause()

    def resume_all(self) -> bool:
        resumed = False
        for key, (player, _output) in self._players.items():
            if player.playbackState() == QMediaPlayer.PlaybackState.PausedState:
                player.play()
                self._apply_output_volume(key)
                resumed = True
        return resumed

    def seek(self, index: int, position_ms: int) -> None:
        key = self._make_key(index)
        slot = self._players.get(key)
        if slot is None:
            return
        slot[0].setPosition(max(0, position_ms))
        self._apply_fade_volume(key, position_ms)

    def _handle_state_changed(self, key: PlayerKey, state: QMediaPlayer.PlaybackState) -> None:
        playing = state == QMediaPlayer.PlaybackState.PlayingState
        if key.context == self._active_context:
            self.track_state_changed.emit(key.index, playing)
        if playing:
            self._pending_play.discard(key)

    def _handle_media_status_changed(self, key: PlayerKey, status: QMediaPlayer.MediaStatus) -> None:
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self._auto_start_next(key)
            self.stop(key.index, context=key.context)
        elif status in (
            QMediaPlayer.MediaStatus.LoadedMedia,
            QMediaPlayer.MediaStatus.BufferedMedia,
            QMediaPlayer.MediaStatus.BufferingMedia,
        ):
            if key in self._pending_play:
                slot = self._players.get(key)
                if slot is not None:
                    slot[0].play()

    def _handle_position_changed(self, key: PlayerKey, position: int) -> None:
        self._apply_fade_volume(key, position)
        self._maybe_start_next_track(key, position)
        if key.context == self._active_context:
            self.position_changed.emit(key.index, position)

    def _handle_duration_changed(self, key: PlayerKey, duration: int) -> None:
        self._track_durations[key] = duration
        if key.context == self._active_context:
            self.duration_changed.emit(key.index, duration)

    def _apply_fade_volume(self, key: PlayerKey, position_ms: int) -> None:
        if key in self._fade_animations:
            return
        slot = self._players.get(key)
        track = self._get_track_for_key(key)
        if slot is None or track is None:
            return
        duration = self._track_durations.get(key)
        if (not duration or duration <= 0) and track.duration_seconds > 0:
            duration = int(track.duration_seconds * 1000)
        fade_in = max(0.0, track.fade_in_seconds)
        fade_out = max(0.0, track.fade_out_seconds)
        volume = 1.0
        if fade_in > 0:
            volume = min(volume, min(1.0, position_ms / (fade_in * 1000)))
        if fade_out > 0 and duration and duration > 0:
            remaining = max(0, duration - position_ms)
            volume = min(volume, min(1.0, remaining / (fade_out * 1000)))
        self._set_track_fade_level(key, volume)

    def _maybe_start_next_track(self, key: PlayerKey, position_ms: int) -> None:
        if key.context != self._active_context:
            return
        tracks = self._current_tracks()
        if len(tracks) <= 1:
            return
        if key in self._manual_stop_fades:
            return
        track = self._get_track_for_key(key)
        if track is None or track.fade_out_seconds <= 0:
            return
        duration = self._track_durations.get(key)
        if not duration or duration <= 0:
            return
        remaining = duration - position_ms
        trigger_ms = int(track.fade_out_seconds * 1000)
        if remaining <= trigger_ms:
            self._auto_start_next(key)

    def _auto_start_next(self, key: PlayerKey) -> None:
        if key.context != self._active_context:
            return
        tracks = self._current_tracks()
        if len(tracks) <= 1:
            return
        if key in self._manual_stop_fades or key in self._auto_next_triggered:
            return
        next_index = (key.index + 1) % len(tracks)
        if next_index == key.index:
            return
        self._auto_next_triggered.add(key)
        self.play(next_index, context=key.context)

    def _start_fade_animation(
        self,
        key: PlayerKey,
        duration_ms: int,
        start_volume: float,
        end_volume: float,
        *,
        stop_after: bool = False,
    ) -> None:
        slot = self._players.get(key)
        if slot is None:
            return
        self._stop_fade_animation(key)
        animation = QVariantAnimation(self)
        animation.setDuration(max(0, duration_ms))
        animation.setStartValue(start_volume)
        animation.setEndValue(end_volume)
        self._set_track_fade_level(key, start_volume)

        def update(value: float, key_ref=key) -> None:
            self._set_track_fade_level(key_ref, float(value))

        def finished(key_ref=key, target=end_volume, stop_flag=stop_after) -> None:
            self._set_track_fade_level(key_ref, target)
            self._fade_animations.pop(key_ref, None)
            animation.deleteLater()
            if stop_flag:
                self.stop(key_ref.index, context=key_ref.context)

        animation.valueChanged.connect(update)
        animation.finished.connect(finished)
        self._fade_animations[key] = animation
        animation.start()

    def _set_track_fade_level(self, key: PlayerKey, level: float) -> None:
        clamped = max(0.0, min(1.0, float(level)))
        self._track_fade_levels[key] = clamped
        self._apply_output_volume(key)

    def _apply_output_volume(self, key: PlayerKey) -> None:
        slot = self._players.get(key)
        if slot is None:
            return
        level = self._track_fade_levels.get(key, 1.0)
        slot[1].setVolume(self._master_volume * level)

    def _apply_master_volume(self) -> None:
        for key in list(self._players.keys()):
            self._apply_output_volume(key)

    def _ensure_player(
        self,
        index: int,
        *,
        context: int | None = None,
        preload_only: bool = False,
    ) -> tuple[QMediaPlayer, QAudioOutput] | None:
        key = self._make_key(index, context)
        tracks = self._context_tracks.setdefault(key.context, [])
        if not (0 <= index < len(tracks)):
            return None
        track = tracks[index]
        source_path = resolve_media_path(track.source)
        if not Path(source_path).exists():
            return None
        desired_url = QUrl.fromLocalFile(source_path)
        slot = self._players.get(key)
        if slot is None:
            player = QMediaPlayer()
            output = QAudioOutput()
            player.setAudioOutput(output)
            player.setSource(desired_url)
            slot = (player, output)
            self._players[key] = slot
            player.positionChanged.connect(lambda pos, key_ref=key: self._handle_position_changed(key_ref, pos))
            player.durationChanged.connect(lambda dur, key_ref=key: self._handle_duration_changed(key_ref, dur))
            player.playbackStateChanged.connect(
                lambda state, key_ref=key: self._handle_state_changed(key_ref, state)
            )
            player.mediaStatusChanged.connect(
                lambda status, key_ref=key: self._handle_media_status_changed(key_ref, status)
            )
        else:
            player, _output = slot
            if player.source() != desired_url:
                player.setSource(desired_url)
        self._track_fade_levels.setdefault(key, 1.0)
        self._apply_output_volume(key)
        if preload_only:
            return slot
        return slot

    def _stop_fade_animation(self, key: PlayerKey) -> None:
        animation = self._fade_animations.pop(key, None)
        if animation is not None:
            animation.stop()
            animation.deleteLater()
