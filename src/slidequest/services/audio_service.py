from __future__ import annotations

from pathlib import Path

from dataclasses import dataclass

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

from slidequest.models.slide import PlaylistTrack
from slidequest.utils.media import resolve_media_path


@dataclass
class _PlayerSlot:
    player: QMediaPlayer
    output: QAudioOutput


class AudioService(QObject):
    track_state_changed = Signal(int, bool)
    position_changed = Signal(int, int)
    duration_changed = Signal(int, int)

    def __init__(self) -> None:
        super().__init__()
        self._tracks: list[PlaylistTrack] = []
        self._players: dict[int, _PlayerSlot] = {}

    def set_tracks(self, tracks: list[PlaylistTrack]) -> None:
        self._tracks = tracks or []
        invalid = [idx for idx in self._players.keys() if idx >= len(self._tracks)]
        for idx in invalid:
            self.stop(idx)

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
            slot = _PlayerSlot(player=player, output=output)
            self._players[index] = slot
            player.positionChanged.connect(lambda pos, idx=index: self.position_changed.emit(idx, pos))
            player.durationChanged.connect(lambda dur, idx=index: self.duration_changed.emit(idx, dur))
            player.playbackStateChanged.connect(
                lambda state, idx=index: self._handle_state_changed(idx, state)
            )
        if position_ms is not None:
            slot.player.setPosition(position_ms)
        if position_ms is not None:
            slot.player.setPosition(position_ms)
        slot.player.play()
        self.track_state_changed.emit(index, True)

    def stop(self, index: int | None = None) -> None:
        if index is None:
            for idx in list(self._players.keys()):
                self.stop(idx)
            return
        slot = self._players.pop(index, None)
        if slot is None:
            return
        slot.player.stop()
        slot.player.deleteLater()
        slot.output.deleteLater()
        self.track_state_changed.emit(index, False)

    def seek(self, index: int, position_ms: int) -> None:
        slot = self._players.get(index)
        if slot is None:
            return
        slot.player.setPosition(max(0, position_ms))

    def _handle_state_changed(self, index: int, state: QMediaPlayer.PlaybackState) -> None:
        playing = state == QMediaPlayer.PlaybackState.PlayingState
        self.track_state_changed.emit(index, playing)
        if state == QMediaPlayer.PlaybackState.StoppedState:
            # allow natural stop without deleting slot so the button toggles off, but keep player for restart
            pass
