from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QMainWindow, QSizePolicy, QVBoxLayout, QWidget

from slidequest.utils.media import resolve_media_path
from slidequest.views.widgets.layout_preview import LayoutPreviewCanvas


class PresentationWindow(QMainWindow):
    """Secondary window that mirrors the current slide layout."""

    closed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SlideQuest – Presentation")
        self.setMinimumSize(1280, 720)
        self._current_layout = "1S|100/1R|100"
        self._source_images: dict[int, str] = {}
        self._resolved_images: dict[int, str] = {}

        self._canvas = LayoutPreviewCanvas(self._current_layout, self)
        self._canvas.setObjectName("PresentationCanvas")
        self._canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._canvas)
        self.setCentralWidget(container)

    def set_layout_description(self, layout_description: str) -> None:
        layout_description = layout_description or "1S|100/1R|100"
        self._current_layout = layout_description
        self._canvas.set_layout_description(layout_description)

    def set_area_images(self, images: dict[int, str] | None) -> None:
        self._source_images = images.copy() if images else {}
        self._resolved_images = {}
        for area_id, path in self._source_images.items():
            if path:
                self._resolved_images[area_id] = resolve_media_path(path)
        self._canvas.set_area_images(self._resolved_images)

    @property
    def current_layout(self) -> str:
        return self._current_layout

    def current_state(self) -> tuple[str, dict[int, str]]:
        return self._current_layout, self._source_images.copy()

    def resolved_images(self) -> dict[int, str]:
        return self._resolved_images.copy()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        super().closeEvent(event)
        self.closed.emit()
