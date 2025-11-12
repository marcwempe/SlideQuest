from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QSize, Qt, QMimeData, QUrl, Signal
from PySide6.QtGui import QDrag, QIcon, QPixmap
from PySide6.QtWidgets import QLabel, QAbstractItemView, QListWidget, QListWidgetItem


class ReplicateGalleryWidget(QListWidget):
    """Grid-based gallery for Replicate results with drag support."""

    entryActivated = Signal(str)

    def __init__(
        self,
        parent=None,
        *,
        show_labels: bool = True,
        vertical: bool = False,
        thumbnail: QSize | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("ReplicateGalleryWidget")
        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setMovement(QListWidget.Movement.Static)
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(False)
        self.setSpacing(6 if show_labels else 2)
        self._thumb_size = thumbnail or QSize(120, 120)
        self.setIconSize(self._thumb_size)
        self.itemActivated.connect(self._emit_activation)
        self._entry_map: dict[str, dict[str, str]] = {}
        self._show_labels = show_labels
        if vertical:
            self.setFlow(QListWidget.Flow.TopToBottom)
            self.setWrapping(False)
        else:
            self.setFlow(QListWidget.Flow.LeftToRight)
        self.setStyleSheet(
            """
            QListWidget#ReplicateGalleryWidget {
                background: transparent;
                border: none;
            }
            QListWidget#ReplicateGalleryWidget::item {
                color: rgba(255, 255, 255, 0.85);
                border: none;
                margin: 0px;
                padding: 0px;
            }
            QListWidget#ReplicateGalleryWidget::item:selected {
                border: 1px solid rgba(120, 190, 255, 0.9);
                border-radius: 10px;
            }
            """
        )

    def setThumbnailSize(self, size: QSize) -> None:  # noqa: N802 - Qt naming consistency
        self.setIconSize(size)

    def set_entries(self, entries: list[dict[str, str]], resolver: Callable[[str], str]) -> None:
        self.clear()
        self._entry_map.clear()
        use_thumbnails = not self._show_labels
        for entry in entries:
            entry_id = entry.get("id") or entry.get("path") or ""
            path = entry.get("path") or ""
            if not entry_id or not path:
                continue
            absolute = resolver(path)
            if not absolute:
                continue
            prompt = entry.get("prompt") or "Seedream-Ausgabe"
            display_text = prompt.splitlines()[0][:42] if self._show_labels else ""
            pixmap = QPixmap(absolute)
            if pixmap.isNull():
                continue
            scaled = pixmap.scaled(
                self.iconSize(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            icon = QIcon(scaled)
            item = QListWidgetItem(icon, display_text)
            item.setData(Qt.ItemDataRole.UserRole, entry_id)
            item.setData(Qt.ItemDataRole.UserRole + 1, absolute)
            item.setSizeHint(QSize(self.iconSize().width(), self.iconSize().height()))
            self.addItem(item)
            if use_thumbnails:
                label = QLabel()
                label.setFixedSize(self.iconSize())
                label.setPixmap(scaled)
                label.setScaledContents(True)
                label.setContentsMargins(0, 0, 0, 0)
                self.setItemWidget(item, label)
            self._entry_map[entry_id] = entry

    def startDrag(self, supportedActions: Qt.DropActions) -> None:  # type: ignore[override]
        item = self.currentItem()
        if item is None:
            return
        path = item.data(Qt.ItemDataRole.UserRole + 1)
        if not isinstance(path, str) or not path:
            return
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(path)])
        drag = QDrag(self)
        drag.setMimeData(mime)
        pixmap = item.icon().pixmap(self.iconSize())
        if not pixmap.isNull():
            drag.setPixmap(pixmap)
            drag.setHotSpot(pixmap.rect().center())
        drag.exec(supportedActions or Qt.DropAction.CopyAction)

    def _emit_activation(self, item: QListWidgetItem) -> None:
        entry_id = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(entry_id, str):
            self.entryActivated.emit(entry_id)
