from __future__ import annotations

from dataclasses import dataclass

from slidequest.models.slide import (
    PlaylistTrack,
    SlideAudioPayload,
    SlideData,
    SlideLayoutPayload,
    SlideNotesPayload,
)
from slidequest.viewmodels.master import MasterViewModel


@dataclass
class _InMemoryStorage:
    slide: SlideData

    def load_slides(self) -> list[SlideData]:
        return [self.slide]

    def save_slides(self, slides: list[SlideData]) -> None:
        self.slide = slides[0]


def _make_slide() -> SlideData:
    return SlideData(
        title="Test",
        subtitle="",
        group="G",
        layout=SlideLayoutPayload("1S|100/1R|100"),
        audio=SlideAudioPayload(),
        notes=SlideNotesPayload(),
    )


def test_add_and_remove_playlist_tracks() -> None:
    storage = _InMemoryStorage(_make_slide())
    vm = MasterViewModel(storage)  # loads initial slide

    vm.add_playlist_tracks(["audio/track1.mp3", "audio/track2.mp3"])
    assert len(vm.current_slide.audio.playlist) == 2
    assert vm.current_slide.audio.playlist[0].source == "audio/track1.mp3"

    vm.remove_playlist_track(0)
    playlist = vm.current_slide.audio.playlist
    assert len(playlist) == 1
    assert playlist[0].source == "audio/track2.mp3"


def test_reorder_playlist_tracks() -> None:
    slide = _make_slide()
    slide.audio.playlist = [
        PlaylistTrack(source="a.mp3"),
        PlaylistTrack(source="b.mp3"),
        PlaylistTrack(source="c.mp3"),
    ]
    storage = _InMemoryStorage(slide)
    vm = MasterViewModel(storage)

    vm.reorder_playlist_tracks([2, 0, 1])
    playlist = [track.source for track in vm.current_slide.audio.playlist]
    assert playlist == ["c.mp3", "a.mp3", "b.mp3"]
