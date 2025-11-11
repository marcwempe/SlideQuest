from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QPoint, QSize, Qt, Signal, QMimeData
from PySide6.QtGui import QDrag, QIcon, QMouseEvent, QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMenu, QToolButton, QWidget

from slidequest.ui.constants import SYMBOL_BUTTON_SIZE

_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff"}
_TOKEN_MIME = "application/x-slidequest-token"


class TokenBar(QFrame):
    imageDropped = Signal(str)
    overlayRequested = Signal(str)
    overlayCleared = Signal(str)
    tokenDeleted = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("TokenBar")
        self.setAcceptDrops(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(8)
        self._placeholder = QLabel("Grafiken hierher ziehen, um Tokens zu erstellen.", self)
        self._placeholder.setObjectName("TokenBarPlaceholder")
        self._placeholder.setStyleSheet("color: rgba(255,255,255,120);")
        self._layout.addWidget(self._placeholder)
        self._layout.addStretch(1)
        self._buttons: list[_TokenButton] = []
        self._pixmap_provider: Callable[[dict[str, str], int], QPixmap | None] | None = None

    def set_tokens(
        self,
        entries: list[dict[str, str]] | None,
        pixmap_provider: Callable[[dict[str, str], int], QPixmap | None] | None,
    ) -> None:
        entries = [entry for entry in entries or [] if entry.get("source")]
        self._pixmap_provider = pixmap_provider
        for button in self._buttons:
            button.deleteLater()
        self._buttons.clear()
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
        self._placeholder.setParent(self)
        if not entries:
            self._placeholder.show()
            self._layout.addWidget(self._placeholder)
            self._layout.addStretch(1)
            return
        self._placeholder.hide()
        for entry in entries:
            token_id = entry.get("id") or ""
            if not token_id:
                continue
            pixmap = pixmap_provider(entry, SYMBOL_BUTTON_SIZE - 6) if pixmap_provider else None
            button = _TokenButton(token_id, pixmap, self)
            button.overlayRequested.connect(self.overlayRequested)
            button.overlayCleared.connect(self.overlayCleared)
            button.deleteRequested.connect(self.tokenDeleted)
            self._layout.addWidget(button)
            self._buttons.append(button)
        self._layout.addStretch(1)

    def dragEnterEvent(self, event) -> None:  # type: ignore[override]
        if self._has_image(event.mimeData()):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:  # type: ignore[override]
        if self._has_image(event.mimeData()):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:  # type: ignore[override]
        files = self._extract_files(event.mimeData())
        if files:
            self.imageDropped.emit(files[0])
            event.acceptProposedAction()
            return
        super().dropEvent(event)

    @staticmethod
    def _has_image(mime) -> bool:
        return any(url.isLocalFile() and Path(url.toLocalFile()).suffix.lower() in _IMAGE_EXTENSIONS for url in mime.urls())

    @staticmethod
    def _extract_files(mime) -> list[str]:
        paths: list[str] = []
        for url in mime.urls():
            if not url.isLocalFile():
                continue
            path = url.toLocalFile()
            if Path(path).suffix.lower() in _IMAGE_EXTENSIONS:
                paths.append(path)
        return paths


class _TokenButton(QToolButton):
    overlayRequested = Signal(str)
    overlayCleared = Signal(str)
    deleteRequested = Signal(str)

    def __init__(self, token_id: str, pixmap: QPixmap | None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._token_id = token_id
        self._thumbnail = pixmap
        self.setCheckable(False)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setFixedSize(SYMBOL_BUTTON_SIZE, SYMBOL_BUTTON_SIZE)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.setStyleSheet(
            """
            QToolButton {
                min-width: %(size)dpx;
                min-height: %(size)dpx;
                max-width: %(size)dpx;
                max-height: %(size)dpx;
                border: 1px solid rgba(255, 255, 255, 60);
                border-radius: 10px;
                padding: 1px;
                background-color: rgba(0, 0, 0, 0.40);
            }
            QToolButton:hover {
                background-color: rgba(255, 255, 255, 0.08);
            }
            QToolButton:pressed {
                background-color: rgba(255, 255, 255, 0.16);
            }
            """
            % {"size": SYMBOL_BUTTON_SIZE}
        )
        if pixmap and not pixmap.isNull():
            scaled = pixmap.scaled(
                SYMBOL_BUTTON_SIZE - 6,
                SYMBOL_BUTTON_SIZE - 6,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.setIcon(QIcon(scaled))
            self._thumbnail = scaled
        else:
            self._thumbnail = pixmap
        self.setIconSize(QSize(SYMBOL_BUTTON_SIZE - 6, SYMBOL_BUTTON_SIZE - 6))
        self._drag_start_pos = QPoint()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())
            return
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.position().toPoint()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        if event.buttons() & Qt.MouseButton.LeftButton == 0:
            super().mouseMoveEvent(event)
            return
        if (event.position().toPoint() - self._drag_start_pos).manhattanLength() < 6:
            super().mouseMoveEvent(event)
            return
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(_TOKEN_MIME, self._token_id.encode("utf-8"))
        drag.setMimeData(mime)
        if self._thumbnail and not self._thumbnail.isNull():
            drag.setPixmap(self._thumbnail.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        drag.exec(Qt.DropAction.CopyAction)

    def _show_context_menu(self, global_pos: QPoint) -> None:
        menu = QMenu(self)
        choose_action = menu.addAction("Overlay wählen …")
        clear_action = menu.addAction("Overlay entfernen")
        menu.addSeparator()
        delete_action = menu.addAction("Token löschen")
        action = menu.exec(global_pos)
        if action == choose_action:
            self.overlayRequested.emit(self._token_id)
        elif action == clear_action:
            self.overlayCleared.emit(self._token_id)
        elif action == delete_action:
            self.deleteRequested.emit(self._token_id)
