from __future__ import annotations

from typing import Callable

from slidequest.models.layouts import LAYOUT_ITEMS, LayoutItem
from slidequest.models.slide import (
    SlideAudioPayload,
    SlideData,
    SlideLayoutPayload,
    SlideNotesPayload,
)
from slidequest.services.storage import SlideStorage
from slidequest.utils.media import normalize_media_path


class MasterViewModel:
    """Coordinates slide data and layout interactions for the views."""

    def __init__(self, storage: SlideStorage) -> None:
        self._storage = storage
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
        normalized = normalize_media_path(source)
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
