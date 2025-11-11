from __future__ import annotations

from pathlib import Path
from typing import Callable
from uuid import uuid4

from slidequest.models.layouts import LAYOUT_ITEMS, LayoutItem
from slidequest.models.slide import (
    PlaylistTrack,
    SlideAudioPayload,
    SlideData,
    SlideLayoutPayload,
    SlideNotesPayload,
    SlideTokenPlacement,
)
from slidequest.services.project_service import ProjectStorageService
from slidequest.services.storage import SlideStorage
from slidequest.utils.media import normalize_media_path


class MasterViewModel:
    """Coordinates slide data and layout interactions for the views."""

    def __init__(
        self,
        storage: SlideStorage,
        project_service: ProjectStorageService | None = None,
    ) -> None:
        self._storage = storage
        resolved_service = project_service
        if resolved_service is None:
            resolved_service = getattr(
                storage,
                "project_service",
                ProjectStorageService(),
            )
        self._project_service = resolved_service
        self._slides: list[SlideData] = storage.load_slides()
        for slide in self._slides:
            if slide.layout.content:
                slide.images = self._content_to_images(slide.layout.content)
            elif not slide.images:
                defaults = self._default_images_for_layout(slide.layout.active_layout)
                if defaults:
                    slide.images = defaults.copy()
                    slide.layout.content = [path for _, path in sorted(defaults.items()) if path]
        self._current_index = 0 if self._slides else -1
        self._listeners: list[Callable[[], None]] = []

    # --- state helpers -------------------------------------------------
    @property
    def slides(self) -> list[SlideData]:
        return self._slides

    @property
    def current_index(self) -> int:
        return self._current_index

    @property
    def current_slide(self) -> SlideData | None:
        if 0 <= self._current_index < len(self._slides):
            return self._slides[self._current_index]
        return None

    @property
    def layout_items(self) -> tuple[LayoutItem, ...]:
        return LAYOUT_ITEMS

    def select_slide(self, index: int) -> SlideData | None:
        if 0 <= index < len(self._slides):
            self._current_index = index
            return self.current_slide
        return None

    # --- mutations -----------------------------------------------------
    def ensure_content_defaults(self) -> None:
        slide = self.current_slide
        if slide and not slide.layout.content:
            defaults = self._default_images_for_layout(slide.layout.active_layout)
            if defaults:
                slide.layout.content = [
                    path for _, path in sorted(defaults.items()) if path
                ]
            elif slide.images:
                slide.layout.content = [
                    image for _, image in sorted(slide.images.items()) if image
                ]

    def set_layout(self, layout_id: str) -> dict[int, str]:
        slide = self.current_slide
        if slide is None:
            return {}
        slide.layout.active_layout = layout_id
        self.ensure_content_defaults()
        slide.images = self._content_to_images(slide.layout.content)
        self.persist()
        return slide.images

    def update_area(self, area_id: int, source: str) -> dict[int, str]:
        slide = self.current_slide
        if slide is None or area_id <= 0:
            return {}
        normalized = self._import_layout_media(source)
        order_index = area_id - 1
        while len(slide.layout.content) <= order_index:
            slide.layout.content.append("")
        slide.layout.content[order_index] = normalized
        slide.images = self._content_to_images(slide.layout.content)
        self.persist()
        self._notify()
        return slide.images

    def update_metadata(self, title: str, subtitle: str, group: str) -> None:
        slide = self.current_slide
        if slide is None:
            return
        changed = False
        if title and title != slide.title:
            slide.title = title
            changed = True
        if subtitle and subtitle != slide.subtitle:
            slide.subtitle = subtitle
            changed = True
        if group and group != slide.group:
            slide.group = group
            changed = True
        if changed:
            self.persist()
            self._notify()

    def add_playlist_tracks(self, sources: list[str]) -> None:
        slide = self.current_slide
        if slide is None or not sources:
            return
        added = False
        for raw in sources:
            normalized = self._import_audio_media(raw)
            if not normalized:
                continue
            track = PlaylistTrack(
                source=normalized,
                title=Path(normalized).name,
            )
            slide.audio.playlist.append(track)
            added = True
        if added:
            self.persist()
            self._notify()

    def remove_playlist_track(self, index: int) -> None:
        slide = self.current_slide
        if slide is None:
            return
        if not (0 <= index < len(slide.audio.playlist)):
            return
        del slide.audio.playlist[index]
        self.persist()
        self._notify()

    def reorder_playlist_tracks(self, order: list[int]) -> None:
        slide = self.current_slide
        if slide is None or not slide.audio.playlist:
            return
        if len(order) != len(slide.audio.playlist):
            return
        seen = set(order)
        if len(seen) != len(order):
            return
        if min(order) < 0 or max(order) >= len(slide.audio.playlist):
            return
        reordered = [slide.audio.playlist[i] for i in order]
        slide.audio.playlist = reordered
        self.persist()
        self._notify()

    # --- notes --------------------------------------------------------
    def note_documents(self) -> list[str]:
        slide = self.current_slide
        if slide is None:
            return []
        return list(slide.notes.notebooks)

    def add_note_documents(self, sources: list[str]) -> list[str]:
        slide = self.current_slide
        if slide is None or not sources:
            return []
        added: list[str] = []
        for raw in sources:
            source = raw[7:] if raw.startswith("file://") else raw
            candidate = Path(source)
            if candidate.is_absolute():
                stored = self._project_service.import_file("notes", source)
            else:
                stored = source
            if not stored or stored in slide.notes.notebooks:
                continue
            slide.notes.notebooks.append(stored)
            added.append(stored)
        if added:
            self.persist()
            self._notify()
        return added

    def note_display_name(self, reference: str) -> str:
        stored = self._project_service.note_title(reference)
        if stored:
            return stored
        title = self._derive_note_title(reference)
        if title:
            self._project_service.set_note_title(reference, title)
        return title or Path(reference).stem

    def update_note_title_from_content(self, reference: str, content: str) -> str:
        title = self._derive_title_from_text(content, reference)
        current = self._project_service.note_title(reference)
        if title and title != current:
            self._project_service.set_note_title(reference, title)
        return title or current or Path(reference).stem

    # --- soundboard ---------------------------------------------------
    def soundboard_entries(self) -> list[dict[str, str]]:
        return self._project_service.soundboard_entries()

    def add_soundboard_entry(self, source: str, title: str | None = None, image: str | None = None) -> None:
        entries = self.soundboard_entries()
        entries.append(
            {
                "source": source,
                "title": title or Path(source).stem,
                "image": image or "",
            }
        )
        self._project_service.set_soundboard_entries(entries)
        self._notify()

    def update_soundboard_image(self, index: int, image: str) -> None:
        entries = self.soundboard_entries()
        if not (0 <= index < len(entries)):
            return
        entries[index]["image"] = image
        self._project_service.set_soundboard_entries(entries)
        self._notify()

    def play_soundboard_entry(self, index: int) -> str | None:
        entries = self.soundboard_entries()
        if not (0 <= index < len(entries)):
            return None
        return entries[index]["source"]

    def soundboard_state_map(self, slide: SlideData | None = None) -> dict[str, int]:
        target = slide or self.current_slide
        if target is None:
            return {}
        return dict(target.audio.soundboard_states)

    def set_soundboard_state(self, key: str, state: int, *, notify: bool = False) -> None:
        slide = self.current_slide
        if slide is None or not key:
            return
        normalized = max(0, int(state))
        changed = False
        if normalized > 0:
            if slide.audio.soundboard_states.get(key) != normalized:
                slide.audio.soundboard_states[key] = normalized
                changed = True
        elif key in slide.audio.soundboard_states:
            slide.audio.soundboard_states.pop(key, None)
            changed = True
        if changed:
            self.persist()
            if notify:
                self._notify()

    def prune_soundboard_states(self, valid_keys: set[str], *, notify: bool = False) -> None:
        slide = self.current_slide
        if slide is None:
            return
        keys = set(slide.audio.soundboard_states.keys())
        obsolete = keys - set(valid_keys)
        if not obsolete:
            return
        for key in obsolete:
            slide.audio.soundboard_states.pop(key, None)
        self.persist()
        if notify:
            self._notify()

    # --- token palette + placements ----------------------------------
    def token_palette(self) -> list[dict[str, str]]:
        return self._project_service.token_entries()

    def add_token_palette_entry(self, source: str, *, title: str | None = None) -> dict[str, str] | None:
        normalized = self._import_token_asset(source)
        if not normalized:
            return None
        entries = self._project_service.token_entries()
        token_id = uuid4().hex
        entry = {
            "id": token_id,
            "title": title or Path(source).stem,
            "source": normalized,
            "overlay": "",
            "mask": "",
        }
        entries.append(entry)
        self._project_service.set_token_entries(entries)
        self._notify()
        return entry

    def update_token_palette_overlay(self, token_id: str, overlay: str, mask: str = "") -> bool:
        entries = self._project_service.token_entries()
        updated = False
        normalized_overlay = self._import_token_asset(overlay) if overlay else ""
        normalized_mask = self._import_token_asset(mask) if mask else ""
        for entry in entries:
            if entry.get("id") != token_id:
                continue
            if entry.get("overlay") == normalized_overlay and entry.get("mask") == normalized_mask:
                return False
            entry["overlay"] = normalized_overlay
            entry["mask"] = normalized_mask
            updated = True
            break
        if not updated:
            return False
        self._project_service.set_token_entries(entries)
        self._notify()
        return True

    def remove_token_palette_entry(self, token_id: str) -> bool:
        entries = self._project_service.token_entries()
        new_entries = [entry for entry in entries if entry.get("id") != token_id]
        if len(new_entries) == len(entries):
            return False
        self._project_service.set_token_entries(new_entries)
        # Remove placements referencing this token
        changed = False
        for slide in self._slides:
            before = len(slide.tokens)
            slide.tokens = [placement for placement in slide.tokens if placement.token_id != token_id]
            if len(slide.tokens) != before:
                changed = True
        if changed:
            self.persist()
        self._notify()
        return True

    def token_placements(self, slide: SlideData | None = None) -> list[SlideTokenPlacement]:
        target = slide or self.current_slide
        if target is None:
            return []
        return list(target.tokens)

    def add_token_placement(
        self,
        token_id: str,
        *,
        position_x: float = 0.5,
        position_y: float = 0.5,
        scale: float = 1.0,
        rotation_deg: float = 0.0,
    ) -> SlideTokenPlacement | None:
        slide = self.current_slide
        if slide is None or not token_id:
            return None
        placement = SlideTokenPlacement(
            placement_id=uuid4().hex,
            token_id=token_id,
            position_x=position_x,
            position_y=position_y,
            scale=scale,
            rotation_deg=rotation_deg,
        )
        slide.tokens.append(placement)
        self.persist()
        self._notify()
        return placement

    def update_token_placement(
        self,
        placement_id: str,
        *,
        position_x: float | None = None,
        position_y: float | None = None,
        scale: float | None = None,
        rotation_deg: float | None = None,
        notify: bool = False,
    ) -> bool:
        slide = self.current_slide
        if slide is None:
            return False
        placement = self._find_token_placement(slide, placement_id)
        if placement is None:
            return False
        changed = False
        if position_x is not None and placement.position_x != position_x:
            placement.position_x = position_x
            changed = True
        if position_y is not None and placement.position_y != position_y:
            placement.position_y = position_y
            changed = True
        if scale is not None and placement.scale != scale:
            placement.scale = scale
            changed = True
        if rotation_deg is not None and placement.rotation_deg != rotation_deg:
            placement.rotation_deg = rotation_deg
            changed = True
        if not changed:
            return False
        self.persist()
        if notify:
            self._notify()
        return True

    def remove_token_placement(self, placement_id: str, *, notify: bool = True) -> bool:
        slide = self.current_slide
        if slide is None:
            return False
        placement = self._find_token_placement(slide, placement_id)
        if placement is None:
            return False
        slide.tokens.remove(placement)
        self.persist()
        if notify:
            self._notify()
        return True

    def _derive_note_title(self, reference: str) -> str:
        absolute = self._project_service.resolve_asset_path(reference)
        if absolute.exists():
            try:
                text = absolute.read_text(encoding="utf-8")
                return self._derive_title_from_text(text, reference)
            except OSError:
                pass
        return self._derive_title_from_text("", reference)

    @staticmethod
    def _derive_title_from_text(content: str, reference: str) -> str:
        candidate = ""
        for line in content.splitlines():
            clean = line.strip("# ").strip()
            if clean:
                candidate = clean
                break
        if not candidate:
            candidate = Path(reference).stem
        normalized = candidate.replace(" ", "_")
        return normalized[:40]

    def remove_note_document_by_path(self, reference: str, *, delete_file: bool = True) -> bool:
        slide = self.current_slide
        if slide is None or not slide.notes.notebooks:
            return False
        target_index: int | None = None
        for idx, entry in enumerate(slide.notes.notebooks):
            if entry == reference:
                target_index = idx
                break
            abs_entry = self._project_service.resolve_asset_path(entry)
            if abs_entry.as_posix() == reference:
                target_index = idx
                reference = entry
                break
        if target_index is None:
            return False
        stored = slide.notes.notebooks.pop(target_index)
        if delete_file:
            absolute = self._project_service.resolve_asset_path(stored)
            absolute.unlink(missing_ok=True)
        self.persist()
        self._notify()
        return True

    def prune_missing_note_documents(self) -> bool:
        slide = self.current_slide
        if slide is None or not slide.notes.notebooks:
            return False
        changed = False
        for entry in list(slide.notes.notebooks):
            absolute = self._project_service.resolve_asset_path(entry)
            if absolute.exists():
                continue
            slide.notes.notebooks.remove(entry)
            changed = True
        if changed:
            self.persist()
            self._notify()
        return changed

    def reorder_note_documents(self, ordered_refs: list[str]) -> None:
        slide = self.current_slide
        if slide is None or not ordered_refs:
            return
        if len(ordered_refs) != len(slide.notes.notebooks):
            return
        if set(ordered_refs) != set(slide.notes.notebooks):
            return
        slide.notes.notebooks = ordered_refs
        self.persist()
        self._notify()

    def attach_note_reference(self, slide_index: int, reference: str) -> bool:
        if not reference:
            return False
        if not (0 <= slide_index < len(self._slides)):
            return False
        slide = self._slides[slide_index]
        if reference in slide.notes.notebooks:
            return False
        slide.notes.notebooks.append(reference)
        self.persist()
        self._notify()
        return True

    def remove_note_document(self, index: int) -> bool:
        slide = self.current_slide
        if slide is None or not (0 <= index < len(slide.notes.notebooks)):
            return False
        del slide.notes.notebooks[index]
        self.persist()
        self._notify()
        return True

    # --- persistence ---------------------------------------------------
    def persist(self) -> None:
        self._storage.save_slides(self._slides)

    def create_slide(self, layout_id: str | None = None, group: str | None = None) -> SlideData:
        layout_id = layout_id or (LAYOUT_ITEMS[0].layout if LAYOUT_ITEMS else "1S|100/1R|100")
        group = group or (LAYOUT_ITEMS[0].group if LAYOUT_ITEMS else "All")
        slide = SlideData(
            title="Neue Folie",
            subtitle="",
            group=group,
            layout=SlideLayoutPayload(layout_id, "", []),
            audio=SlideAudioPayload(),
            notes=SlideNotesPayload(),
            images={},
        )
        defaults = self._default_images_for_layout(layout_id)
        if defaults:
            slide.images = defaults.copy()
            slide.layout.content = self._images_to_content(slide.images)
        self._slides.append(slide)
        self._current_index = len(self._slides) - 1
        self.persist()
        self._notify()
        return slide

    def delete_slide(self, index: int) -> SlideData | None:
        if len(self._slides) <= 1 or not (0 <= index < len(self._slides)):
            return None
        deleted = self._slides.pop(index)
        if self._current_index >= len(self._slides):
            self._current_index = len(self._slides) - 1
        self.persist()
        self._notify()
        return deleted

    def _import_layout_media(self, source: str) -> str:
        path = Path(source[7:] if source.startswith("file://") else source)
        if path.is_absolute() and path.exists():
            return self._project_service.import_file("layouts", str(path))
        return normalize_media_path(str(path))

    def _import_audio_media(self, source: str) -> str:
        path = Path(source[7:] if source.startswith("file://") else source)
        if path.is_absolute() and path.exists():
            return self._project_service.import_file("audio", str(path))
        return normalize_media_path(str(path))

    def _import_token_asset(self, source: str) -> str:
        if not source:
            return ""
        path = Path(source[7:] if source.startswith("file://") else source)
        if path.is_absolute() and path.exists():
            return self._project_service.import_file("tokens", str(path))
        return normalize_media_path(str(path))

    @staticmethod
    def _find_token_placement(slide: SlideData, placement_id: str) -> SlideTokenPlacement | None:
        for token in slide.tokens:
            if token.placement_id == placement_id:
                return token
        return None

    # --- utility -------------------------------------------------------
    @staticmethod
    def _content_to_images(content: list[str]) -> dict[int, str]:
        images: dict[int, str] = {}
        for index, path in enumerate(content):
            if path:
                images[index + 1] = path
        return images

    @staticmethod
    def _images_to_content(images: dict[int, str]) -> list[str]:
        if not images:
            return []
        max_area = max((area_id for area_id in images.keys() if area_id > 0), default=0)
        if max_area <= 0:
            return []
        content = ["" for _ in range(max_area)]
        for area_id, path in images.items():
            if area_id <= 0 or not path:
                continue
            index = area_id - 1
            if index >= len(content):
                content.extend([""] * (index + 1 - len(content)))
            content[index] = path
        return content

    @staticmethod
    def _default_images_for_layout(layout_id: str) -> dict[int, str]:
        for item in LAYOUT_ITEMS:
            if item.layout == layout_id:
                return item.images.copy()
        return {}

    def add_listener(self, listener: Callable[[], None]) -> None:
        if listener not in self._listeners:
            self._listeners.append(listener)

    def _notify(self) -> None:
        for listener in self._listeners:
            listener()
