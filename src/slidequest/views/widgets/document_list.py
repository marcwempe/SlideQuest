from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QMimeData
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
from PySide6.QtWidgets import QListWidget


class DocumentListWidget(QListWidget):
    """Horizontal list widget that accepts drops for document paths."""

    filesDropped = Signal(list)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("NoteDocumentList")
        self.setFlow(QListWidget.Flow.LeftToRight)
        self.setWrapping(False)
        self.setSpacing(8)
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.setHorizontalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setDragEnabled(False)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # type: ignore[override]
        if self._has_supported_files(event.mimeData()):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:  # type: ignore[override]
        if self._has_supported_files(event.mimeData()):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:  # type: ignore[override]
        files = self._extract_files(event.mimeData())
        if files:
            self.filesDropped.emit(files)
            event.acceptProposedAction()
            return
        super().dropEvent(event)

    @staticmethod
    def _has_supported_files(mime: QMimeData) -> bool:
        return bool(mime.urls())

    @staticmethod
    def _extract_files(mime: QMimeData) -> list[str]:
        paths: list[str] = []
        for url in mime.urls():
            if url.isLocalFile():
                paths.append(url.toLocalFile())
        return paths
