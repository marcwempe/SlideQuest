from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QUrl, Signal, QVariantAnimation
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

from slidequest.models.slide import PlaylistTrack
from slidequest.utils.media import resolve_media_path


class AudioService(QObject):
    track_state_changed = Signal(int, bool)
    position_changed = Signal(int, int)
    duration_changed = Signal(int, int)

    def __init__(self) -> None:
        super().__init__()
        self._tracks: list[PlaylistTrack] = []
        self._players: dict[int, tuple[QMediaPlayer, QAudioOutput]] = {}
        self._track_durations: dict[int, int] = {}
        self._fade_animations: dict[int, QVariantAnimation] = {}
        self._auto_next_triggered: set[int] = set()
        self._manual_stop_fades: set[int] = set()
        self._pending_play: set[int] = set()

    def set_tracks(self, tracks: list[PlaylistTrack]) -> None:
        was_empty = not self._tracks
        self._tracks = tracks or []
        invalid = [idx for idx in self._players.keys() if idx >= len(self._tracks)]
        for idx in invalid:
            self.stop(idx)
        self._track_durations = {idx: dur for idx, dur in self._track_durations.items() if idx < len(self._tracks)}
        self._fade_animations = {idx: anim for idx, anim in self._fade_animations.items() if idx < len(self._tracks)}
        self._auto_next_triggered = {idx for idx in self._auto_next_triggered if idx < len(self._tracks)}
        self._manual_stop_fades = {idx for idx in self._manual_stop_fades if idx < len(self._tracks)}
        self._pending_play = {idx for idx in self._pending_play if idx < len(self._tracks)}
        if self._tracks and not self._players and was_empty:
            self._ensure_player(0, preload_only=True)

    def play(self, index: int, position_ms: int | None = None) -> None:
        slot = self._ensure_player(index)
        if slot is None:
            return
        self._stop_fade_animation(index)
        if position_ms is not None:
            slot[0].setPosition(position_ms)
        slot[1].setVolume(1.0)
        fade_in_ms = int(self._tracks[index].fade_in_seconds * 1000)
        if fade_in_ms > 0:
            slot[1].setVolume(0.0)
            self._start_fade_animation(index, fade_in_ms, 0.0, 1.0)
        slot[0].play()
        self._pending_play.add(index)
        if fade_in_ms <= 0:
            self._apply_fade_volume(index, slot[0].position())
        self.track_state_changed.emit(index, True)

    def stop(self, index: int | None = None) -> None:
        if index is None:
            for idx in list(self._players.keys()):
                self.stop(idx)
            return
        slot = self._players.pop(index, None)
        if slot is None:
            return
        self._stop_fade_animation(index)
        slot[0].stop()
        slot[0].deleteLater()
        slot[1].deleteLater()
        self.track_state_changed.emit(index, False)
        self._auto_next_triggered.discard(index)
        self._manual_stop_fades.discard(index)
        self._pending_play.discard(index)

    def stop_with_fade(self, index: int) -> None:
        slot = self._players.get(index)
        if slot is None:
            return
        track = self._tracks[index] if 0 <= index < len(self._tracks) else None
        fade_ms = int(track.fade_out_seconds * 1000) if track else 0
        if fade_ms <= 0:
            self.stop(index)
            return
        current_volume = slot[1].volume()
        self._manual_stop_fades.add(index)
        self._start_fade_animation(index, fade_ms, current_volume, 0.0, stop_after=True)
        
    def seek(self, index: int, position_ms: int) -> None:
        slot = self._players.get(index)
        if slot is None:
            return
        slot[0].setPosition(max(0, position_ms))
        self._apply_fade_volume(index, position_ms)

    def _handle_state_changed(self, index: int, state: QMediaPlayer.PlaybackState) -> None:
        playing = state == QMediaPlayer.PlaybackState.PlayingState
        self.track_state_changed.emit(index, playing)
        if playing:
            self._pending_play.discard(index)

    def _handle_media_status_changed(self, index: int, status: QMediaPlayer.MediaStatus) -> None:
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self._auto_start_next(index)
            self.stop(index)
        elif status in (
            QMediaPlayer.MediaStatus.LoadedMedia,
            QMediaPlayer.MediaStatus.BufferedMedia,
            QMediaPlayer.MediaStatus.BufferingMedia,
        ):
            if index in self._pending_play:
                slot = self._players.get(index)
                if slot is not None:
                    slot[0].play()

        
    def _handle_position_changed(self, idx: int, position: int) -> None:
        self.position_changed.emit(idx, position)
        self._apply_fade_volume(idx, position)
        self._maybe_start_next_track(idx, position)

    def _handle_duration_changed(self, idx: int, duration: int) -> None:
        self._track_durations[idx] = duration
        self.duration_changed.emit(idx, duration)

    def _apply_fade_volume(self, idx: int, position_ms: int) -> None:
        if idx in self._fade_animations:
            return
        slot = self._players.get(idx)
        track = self._tracks[idx] if 0 <= idx < len(self._tracks) else None
        if slot is None or track is None:
            return
        duration = self._track_durations.get(idx)
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
        slot[1].setVolume(max(0.0, min(1.0, volume)))

    def _maybe_start_next_track(self, idx: int, position_ms: int) -> None:
        if len(self._tracks) <= 1:
            return
        if idx in self._manual_stop_fades:
            return
        track = self._tracks[idx] if 0 <= idx < len(self._tracks) else None
        if track is None or track.fade_out_seconds <= 0:
            return
        duration = self._track_durations.get(idx)
        if not duration or duration <= 0:
            return
        remaining = duration - position_ms
        trigger_ms = int(track.fade_out_seconds * 1000)
        if remaining <= trigger_ms:
            self._auto_start_next(idx)

    def _auto_start_next(self, current_index: int) -> None:
        if len(self._tracks) <= 1:
            return
        if current_index in self._manual_stop_fades or current_index in self._auto_next_triggered:
            return
        next_idx = (current_index + 1) % len(self._tracks)
        if next_idx == current_index:
            return
        self._auto_next_triggered.add(current_index)
        self.play(next_idx)

    def _start_fade_animation(self, index: int, duration_ms: int, start_volume: float, end_volume: float, *, stop_after: bool = False) -> None:
        slot = self._players.get(index)
        if slot is None:
            return
        self._stop_fade_animation(index)
        animation = QVariantAnimation(self)
        animation.setDuration(max(0, duration_ms))
        animation.setStartValue(start_volume)
        animation.setEndValue(end_volume)

        def update(value: float, idx=index) -> None:
            slot = self._players.get(idx)
            if slot is None:
                return
            slot[1].setVolume(max(0.0, min(1.0, float(value))))

        def finished(idx=index, target=end_volume, stop_flag=stop_after) -> None:
            slot = self._players.get(idx)
            if slot is not None:
                slot[1].setVolume(target)
            self._fade_animations.pop(idx, None)
            animation.deleteLater()
            if stop_flag:
                self.stop(idx)

        animation.valueChanged.connect(update)
        animation.finished.connect(finished)
        self._fade_animations[index] = animation
        animation.start()

    def _ensure_player(self, index: int, *, preload_only: bool = False) -> tuple[QMediaPlayer, QAudioOutput] | None:
        if not (0 <= index < len(self._tracks)):
            return None
        track = self._tracks[index]
        source_path = resolve_media_path(track.source)
        if not Path(source_path).exists():
            return None
        desired_url = QUrl.fromLocalFile(source_path)
        slot = self._players.get(index)
        if slot is None:
            player = QMediaPlayer()
            output = QAudioOutput()
            player.setAudioOutput(output)
            player.setSource(desired_url)
            slot = (player, output)
            self._players[index] = slot
            player.positionChanged.connect(lambda pos, idx=index: self._handle_position_changed(idx, pos))
            player.durationChanged.connect(lambda dur, idx=index: self._handle_duration_changed(idx, dur))
            player.playbackStateChanged.connect(
                lambda state, idx=index: self._handle_state_changed(idx, state)
            )
            player.mediaStatusChanged.connect(
                lambda status, idx=index: self._handle_media_status_changed(idx, status)
            )
        else:
            player, _output = slot
            if player.source() != desired_url:
                player.setSource(desired_url)
        if preload_only:
            return slot
        return slot

    def _stop_fade_animation(self, index: int) -> None:
        animation = self._fade_animations.pop(index, None)
        if animation is not None:
            animation.stop()
            animation.deleteLater()
