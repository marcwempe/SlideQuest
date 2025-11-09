from __future__ import annotations

from pathlib import Path

from dataclasses import dataclass

from PySide6.QtCore import QObject, QUrl, Signal, QTimeLine, QEasingCurve
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

from slidequest.models.slide import PlaylistTrack
from slidequest.utils.media import resolve_media_path


@dataclass
class _PlayerSlot:
    player: QMediaPlayer
    output: QAudioOutput
    timeline: QTimeLine | None = None


class AudioService(QObject):
    track_state_changed = Signal(int, bool)
    position_changed = Signal(int, int)
    duration_changed = Signal(int, int)

    def __init__(self) -> None:
        super().__init__()
        self._tracks: list[PlaylistTrack] = []
        self._players: dict[int, _PlayerSlot] = {}
        self._track_durations: dict[int, int] = {}
        self._fade_out_started: set[int] = set()

    def set_tracks(self, tracks: list[PlaylistTrack]) -> None:
        self._tracks = tracks or []
        invalid = [idx for idx in self._players.keys() if idx >= len(self._tracks)]
        for idx in invalid:
            self.stop(idx)
        self._fade_out_started = {idx for idx in self._fade_out_started if idx < len(self._tracks)}

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
            player.positionChanged.connect(lambda pos, idx=index: self._handle_position_changed(idx, pos))
            player.durationChanged.connect(lambda dur, idx=index: self._handle_duration_changed(idx, dur))
            player.playbackStateChanged.connect(
                lambda state, idx=index: self._handle_state_changed(idx, state)
            )
        else:
            slot.output.setVolume(1.0)
            self._fade_out_started.discard(index)
            if slot.timeline:
                slot.timeline.stop()
                slot.timeline.deleteLater()
                slot.timeline = None
            slot.player.setSource(QUrl.fromLocalFile(source_path))
        if position_ms is not None:
            slot.player.setPosition(position_ms)
        slot.player.play()
        fade_in_ms = int(self._tracks[index].fade_in_seconds * 1000)
        if fade_in_ms > 0:
            self._start_fade(index, fade_in_ms, 0.0, 1.0)
        else:
            slot.output.setVolume(1.0)
        self.track_state_changed.emit(index, True)

    def stop(self, index: int | None = None) -> None:
        if index is None:
            for idx in list(self._players.keys()):
                self.stop(idx)
            return
        slot = self._players.pop(index, None)
        if slot is None:
            return
        if slot.timeline:
            slot.timeline.stop()
            slot.timeline.deleteLater()
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
            self.stop(index)

        
    def _handle_position_changed(self, idx: int, position: int) -> None:
        self.position_changed.emit(idx, position)
        self._maybe_start_fade_out(idx, position)

    def _handle_duration_changed(self, idx: int, duration: int) -> None:
        self._track_durations[idx] = duration
        self.duration_changed.emit(idx, duration)

    def _maybe_start_fade_out(self, idx: int, position: int) -> None:
        if idx in self._fade_out_started:
            return
        track = self._tracks[idx] if 0 <= idx < len(self._tracks) else None
        if track is None:
            return
        fade_ms = int(track.fade_out_seconds * 1000)
        if fade_ms <= 0:
            return
        duration = self._track_durations.get(idx)
        if not duration or duration <= 0:
            return
        remaining = duration - position
        if remaining <= fade_ms:
            self._fade_out_started.add(idx)
            slot = self._players.get(idx)
            current_volume = slot.output.volume() if slot else 1.0
            self._start_fade(idx, fade_ms, current_volume, 0.0, stop_after=True)

    def _start_fade(self, idx: int, duration_ms: int, start_volume: float, target_volume: float, *, stop_after: bool = False) -> None:
        slot = self._players.get(idx)
        if slot is None:
            return
        if duration_ms <= 0:
            slot.output.setVolume(target_volume)
            if stop_after:
                self.stop(idx)
            return
        if slot.timeline:
            slot.timeline.stop()
            slot.timeline.deleteLater()
        slot.output.setVolume(start_volume)
        timeline = QTimeLine(duration_ms, self)
        timeline.setEasingCurve(QEasingCurve.Type.Linear)
        slot.timeline = timeline

        def handle_value(value: float, index=idx, sv=start_volume, tv=target_volume) -> None:
            slot = self._players.get(index)
            if slot is None:
                return
            volume = sv + (tv - sv) * value
            slot.output.setVolume(max(0.0, min(1.0, volume)))

        def handle_finished(index=idx, target=target_volume, stop=stop_after) -> None:
            slot = self._players.get(index)
            if slot:
                slot.output.setVolume(target)
                if slot.timeline:
                    slot.timeline.deleteLater()
                    slot.timeline = None
            if stop:
                self.stop(index)

        timeline.valueChanged.connect(handle_value)
        timeline.finished.connect(handle_finished)
        timeline.start()
