from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidget

from slidequest.views.widgets.playlist_list import PlaylistListWidget


class SlideListWidget(PlaylistListWidget):
    """Explorer list widget that supports internal drag/drop reordering."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("SlideExplorerList")
        self.setFlow(QListWidget.Flow.TopToBottom)
        self.setWrapping(False)
        self.setSpacing(6)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    @staticmethod
    def _has_external_files(_mime) -> bool:
        return False

    def dropEvent(self, event) -> None:  # type: ignore[override]
        if event.source() == self:
            super().dropEvent(event)
        else:
            event.ignore()
