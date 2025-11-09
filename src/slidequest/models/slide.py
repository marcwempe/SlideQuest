from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PlaylistTrack:
    source: str
    title: str = ""
    duration_seconds: float = 0.0
    position_seconds: float = 0.0
    fade_in_seconds: float = 0.0
    fade_out_seconds: float = 0.0


@dataclass
class SlideLayoutPayload:
    active_layout: str
    thumbnail_url: str = ""
    content: list[str] = field(default_factory=list)


@dataclass
class SlideAudioPayload:
    playlist: list[PlaylistTrack] = field(default_factory=list)
    effects: list[str] = field(default_factory=list)


@dataclass
class SlideNotesPayload:
    notebooks: list[str] = field(default_factory=list)


@dataclass
class SlideData:
    title: str
    subtitle: str
    group: str
    layout: SlideLayoutPayload
    audio: SlideAudioPayload
    notes: SlideNotesPayload
    images: dict[int, str] = field(default_factory=dict)
