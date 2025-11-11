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
    soundboard_states: dict[str, int] = field(default_factory=dict)


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
    tokens: list["SlideTokenPlacement"] = field(default_factory=list)


@dataclass
class SlideTokenPlacement:
    token_id: str = ""
    source: str = ""
    overlay: str = ""
    mask: str = ""
    position_x: float = 0.5
    position_y: float = 0.5
    scale: float = 1.0
    rotation_deg: float = 0.0
