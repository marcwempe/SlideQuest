from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SlideLayoutPayload:
    active_layout: str
    thumbnail_url: str = ""
    content: list[str] = field(default_factory=list)


@dataclass
class SlideAudioPayload:
    playlist: list[str] = field(default_factory=list)
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
