from __future__ import annotations

from PySide6.QtCore import Qt, QMimeData, Signal
from PySide6.QtGui import QDrag, QDragEnterEvent, QDragMoveEvent, QDropEvent, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QListWidget,
)


class PlaylistListWidget(QListWidget):
    """List widget that supports internal reordering and external file drops."""

    filesDropped = Signal(list)
    orderChanged = Signal()

    def __init__(self, parent: QFrame | None = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setSpacing(8)
        self.setAlternatingRowColors(False)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setDropIndicatorShown(True)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.viewport().setAcceptDrops(True)
        self._drag_active_row: int | None = None

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # type: ignore[override]
        if self._has_external_files(event.mimeData()):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:  # type: ignore[override]
        if self._has_external_files(event.mimeData()):
            event.acceptProposedAction()
            return
        if event.source() == self:
            target_row = self.indexAt(event.position().toPoint()).row()
            if target_row < 0:
                target_row = self.count()
            self._preview_drag_move(target_row)
            event.accept()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:  # type: ignore[override]
        if event.source() == self and not self._has_external_files(event.mimeData()):
            self._drag_active_row = None
            self.orderChanged.emit()
            event.acceptProposedAction()
            return

        files = self._extract_files(event.mimeData())
        if files:
            self.filesDropped.emit(files)
            event.acceptProposedAction()
            return
        super().dropEvent(event)

    def startDrag(self, supportedActions: Qt.DropActions) -> None:  # type: ignore[override]
        indexes = self.selectedIndexes()
        if not indexes:
            return
        mime = self.model().mimeData(indexes)
        if mime is None:
            return
        drag = QDrag(self)
        drag.setMimeData(mime)
        item = self.currentItem()
        if item is not None:
            widget = self.itemWidget(item)
            if widget is not None:
                pixmap = QPixmap(widget.size())
                pixmap.fill(Qt.GlobalColor.transparent)
                widget.render(pixmap)
                drag.setPixmap(pixmap)
                drag.setHotSpot(widget.rect().topLeft())
        self._drag_active_row = self.currentRow()
        drag.exec(supportedActions)
        self._drag_active_row = None
        self.clearSelection()

    @staticmethod
    def _has_external_files(mime: QMimeData) -> bool:
        return bool(mime.urls())

    @staticmethod
    def _extract_files(mime: QMimeData) -> list[str]:
        paths: list[str] = []
        for url in mime.urls():
            if url.isLocalFile():
                paths.append(url.toLocalFile())
        return paths

    def _preview_drag_move(self, target_row: int) -> None:
        if self._drag_active_row is None:
            return
        if target_row < 0:
            target_row = 0
        if target_row > self.count():
            target_row = self.count()
        if target_row == self._drag_active_row or self.count() == 0:
            return

        item = self.item(self._drag_active_row)
        if item is None:
            return
        widget = self.itemWidget(item)
        if widget is not None:
            self.setItemWidget(item, None)
        take = self.takeItem(self._drag_active_row)
        if target_row > self._drag_active_row:
            target_row -= 1
        target_row = max(0, min(target_row, self.count()))
        self.insertItem(target_row, take)
        if widget is not None:
            self.setItemWidget(take, widget)
        self._drag_active_row = target_row
        self.setCurrentRow(target_row)
