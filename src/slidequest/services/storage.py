from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from slidequest.models.layouts import LAYOUT_ITEMS
from slidequest.models.slide import (
    PlaylistTrack,
    SlideAudioPayload,
    SlideData,
    SlideLayoutPayload,
    SlideNotesPayload,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"
SLIDES_FILE = DATA_DIR / "slides.json"
THUMBNAIL_DIR = PROJECT_ROOT / "assets" / "thumbnails"


class SlideStorage:
    def __init__(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)

    def load_slides(self) -> list[SlideData]:
        if SLIDES_FILE.exists():
            try:
                payload = json.loads(SLIDES_FILE.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                payload = {}
            entries = payload.get("slides") or []
            slides = [self._slide_from_payload(entry) for entry in entries]
            if slides:
                return slides
        return self._seed_from_layouts()

    def save_slides(self, slides: list[SlideData]) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        payload = {"slides": [self._slide_to_payload(slide) for slide in slides]}
        SLIDES_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def _slide_from_payload(self, data: dict[str, Any]) -> SlideData:
        layout_data = data.get("layout") or {}
        audio_data = data.get("audio") or {}
        notes_data = data.get("notes") or {}
        layout = SlideLayoutPayload(
            layout_data.get("active_layout") or "1S|100/1R|100",
            layout_data.get("thumbnail_url") or "",
            list(layout_data.get("content") or []),
        )
        playlist_entries = []
        for entry in audio_data.get("playlist") or []:
            if isinstance(entry, str):
                source = entry.strip()
                if not source:
                    continue
                playlist_entries.append(PlaylistTrack(source=source))
                continue
            if isinstance(entry, dict):
                source = (entry.get("source") or "").strip()
                if not source:
                    continue
                playlist_entries.append(
                    PlaylistTrack(
                        source=source,
                        title=entry.get("title") or "",
                        duration_seconds=float(entry.get("duration_seconds") or 0.0),
                        fade_in_seconds=float(entry.get("fade_in_seconds") or 0.0),
                        fade_out_seconds=float(entry.get("fade_out_seconds") or 0.0),
                    )
                )

        slide = SlideData(
            title=data.get("title") or "Unbenannte Folie",
            subtitle=data.get("subtitle") or "",
            group=data.get("group") or "",
            layout=layout,
            audio=SlideAudioPayload(
                playlist=playlist_entries,
                effects=list(audio_data.get("effects") or []),
            ),
            notes=SlideNotesPayload(
                notebooks=list(notes_data.get("notebooks") or []),
            ),
        )
        return slide

    def _slide_to_payload(self, slide: SlideData) -> dict[str, Any]:
        return {
            "title": slide.title,
            "subtitle": slide.subtitle,
            "group": slide.group,
            "layout": {
                "active_layout": slide.layout.active_layout,
                "thumbnail_url": slide.layout.thumbnail_url,
                "content": list(slide.layout.content),
            },
            "audio": {
                "playlist": [
                    {
                        "source": track.source,
                        "title": track.title,
                        "duration_seconds": track.duration_seconds,
                        "fade_in_seconds": track.fade_in_seconds,
                        "fade_out_seconds": track.fade_out_seconds,
                    }
                    for track in slide.audio.playlist
                ],
                "effects": list(slide.audio.effects),
            },
            "notes": {
                "notebooks": list(slide.notes.notebooks),
            },
        }

    def _seed_from_layouts(self) -> list[SlideData]:
        slides: list[SlideData] = []
        for layout in LAYOUT_ITEMS:
            slide = SlideData(
                title=layout.title,
                subtitle=layout.subtitle,
                group=layout.group,
                layout=SlideLayoutPayload(layout.layout, "", []),
                audio=SlideAudioPayload(),
                notes=SlideNotesPayload(),
            )
            slides.append(slide)
        return slides
