from __future__ import annotations

from pathlib import Path

from dataclasses import dataclass

from PySide6.QtCore import QObject, QUrl, Signal
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
        self._players: dict[int, _PlayerSlot] = {}
        self._track_durations: dict[int, int] = {}

    def set_tracks(self, tracks: list[PlaylistTrack]) -> None:
        self._tracks = tracks or []
        invalid = [idx for idx in self._players.keys() if idx >= len(self._tracks)]
        for idx in invalid:
            self.stop(idx)
        self._track_durations = {idx: dur for idx, dur in self._track_durations.items() if idx < len(self._tracks)}

    def play(self, index: int, position_ms: int | None = None) -> None:
        if not (0 <= index < len(self._tracks)):
            return
        track = self._tracks[index]
        source_path = resolve_media_path(track.source)
        if not Path(source_path).exists():
            return
        slot = self._players.get(index)
        if slot is None:
            player = QMediaPlayer()
            output = QAudioOutput()
            player.setAudioOutput(output)
            player.setSource(QUrl.fromLocalFile(source_path))
            self._players[index] = (player, output)
            player.positionChanged.connect(lambda pos, idx=index: self._handle_position_changed(idx, pos))
            player.durationChanged.connect(lambda dur, idx=index: self._handle_duration_changed(idx, dur))
            player.playbackStateChanged.connect(
                lambda state, idx=index: self._handle_state_changed(idx, state)
            )
        else:
            slot[0].setSource(QUrl.fromLocalFile(source_path))
        if position_ms is not None:
            slot.player.setPosition(position_ms)
        slot[0].play()
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
        slot[0].stop()
        slot[0].deleteLater()
        slot[1].deleteLater()
        self.track_state_changed.emit(index, False)
        
    def seek(self, index: int, position_ms: int) -> None:
        slot = self._players.get(index)
        if slot is None:
            return
        slot[0].setPosition(max(0, position_ms))
        self._apply_fade_volume(index, position_ms)

    def _handle_state_changed(self, index: int, state: QMediaPlayer.PlaybackState) -> None:
        playing = state == QMediaPlayer.PlaybackState.PlayingState
        self.track_state_changed.emit(index, playing)
        if state == QMediaPlayer.PlaybackState.StoppedState:
            self.stop(index)

        
    def _handle_position_changed(self, idx: int, position: int) -> None:
        self.position_changed.emit(idx, position)
        self._apply_fade_volume(idx, position)

    def _handle_duration_changed(self, idx: int, duration: int) -> None:
        self._track_durations[idx] = duration
        self.duration_changed.emit(idx, duration)

    def _apply_fade_volume(self, idx: int, position_ms: int) -> None:
        slot = self._players.get(idx)
        track = self._tracks[idx] if 0 <= idx < len(self._tracks) else None
        if slot is None or track is None:
            return
        duration = self._track_durations.get(idx)
        fade_in = max(0.0, track.fade_in_seconds)
        fade_out = max(0.0, track.fade_out_seconds)
        volume = 1.0
        if fade_in > 0:
            volume = min(volume, min(1.0, position_ms / (fade_in * 1000)))
        if fade_out > 0 and duration and duration > 0:
            remaining = max(0, duration - position_ms)
            volume = min(volume, min(1.0, remaining / (fade_out * 1000)))
        slot[1].setVolume(max(0.0, min(1.0, volume)))
