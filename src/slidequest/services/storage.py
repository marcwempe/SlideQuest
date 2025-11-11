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
from slidequest.services.project_service import ProjectStorageService

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"
SLIDES_FILE = DATA_DIR / "slides.json"
THUMBNAIL_DIR = PROJECT_ROOT / "assets" / "thumbnails"


class SlideStorage:
    def __init__(self, project_service: ProjectStorageService | None = None) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)
        self._project_service = project_service or ProjectStorageService()

    def load_slides(self) -> list[SlideData]:
        project = self._project_service.load_project()
        if not project.get("slides"):
            legacy = self._load_legacy_slides()
            if legacy:
                project["slides"] = legacy
                project.setdefault("files", {})
                self._project_service.save_project(project)
        entries = project.get("slides") or []
        slides: list[SlideData] = []
        migrated = False
        for entry in entries:
            slide = self._slide_from_payload(entry)
            if self._migrate_slide_assets(slide):
                migrated = True
            slides.append(slide)
        if migrated:
            project["slides"] = [self._slide_to_payload(slide) for slide in slides]
            self._project_service.save_project(project)
        if slides:
            return slides
        return self._seed_from_layouts()

    def save_slides(self, slides: list[SlideData]) -> None:
        project = self._project_service.load_project()
        project["slides"] = [self._slide_to_payload(slide) for slide in slides]
        files = project.setdefault("files", project.get("files") or {})
        used_paths = self._collect_asset_paths(slides)
        for file_id, info in list(files.items()):
            path = info.get("path") or ""
            if path not in used_paths:
                self._project_service.move_to_trash(path)
                files.pop(file_id, None)
        self._project_service.save_project(project)

    @property
    def project_service(self) -> ProjectStorageService:
        return self._project_service

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

    def _load_legacy_slides(self) -> list[dict[str, Any]]:
        if not SLIDES_FILE.exists():
            return []
        try:
            payload = json.loads(SLIDES_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        return list(payload.get("slides") or [])

    @staticmethod
    def _content_to_images(content: list[str]) -> dict[int, str]:
        images: dict[int, str] = {}
        for index, entry in enumerate(content):
            if entry:
                images[index + 1] = entry
        return images

    def _migrate_slide_assets(self, slide: SlideData) -> bool:
        changed = False
        new_content: list[str] = []
        for path in slide.layout.content:
            normalized, migrated = self._ensure_asset_registered("layouts", path)
            new_content.append(normalized)
            changed = changed or migrated
        slide.layout.content = new_content
        slide.images = self._content_to_images(new_content)

        for track in slide.audio.playlist:
            normalized, migrated = self._ensure_asset_registered("audio", track.source)
            if migrated:
                track.source = normalized
                changed = True

        new_notes: list[str] = []
        for path in slide.notes.notebooks:
            normalized, migrated = self._ensure_asset_registered("notes", path)
            new_notes.append(normalized)
            changed = changed or migrated
        slide.notes.notebooks = new_notes
        return changed

    def _ensure_asset_registered(self, kind: str, path: str) -> tuple[str, bool]:
        if not path:
            return path, False
        candidate = Path(path)
        if candidate.is_absolute():
            try:
                candidate.relative_to(self._project_service.project_dir)
                return path, False
            except ValueError:
                pass
            relative = self._project_service.import_file(kind, str(candidate))
            return relative, True
        return path, False

    @staticmethod
    def _collect_asset_paths(slides: list[SlideData]) -> set[str]:
        used: set[str] = set()
        for slide in slides:
            used.update(entry for entry in slide.layout.content if entry)
            for track in slide.audio.playlist:
                if track.source:
                    used.add(track.source)
            used.update(entry for entry in slide.notes.notebooks if entry)
        return used
