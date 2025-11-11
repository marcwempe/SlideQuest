from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidget

from slidequest.views.widgets.playlist_list import PlaylistListWidget


class DocumentListWidget(PlaylistListWidget):
    """List widget for notes that mirrors playlist behavior."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("NoteDocumentList")
        self.setFlow(QListWidget.Flow.TopToBottom)
        self.setWrapping(False)
        self.setSpacing(10)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setMinimumHeight(220)
