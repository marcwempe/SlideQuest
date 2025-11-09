from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QRect, QRectF, QSize, Qt, Signal
from PySide6.QtWidgets import (
    QLayout,
    QLayoutItem,
    QSpacerItem,
    QSizePolicy,
    QToolButton,
    QWidget,
)


@dataclass
class IconBinding:
    button: QToolButton
    icon_path: Path
    accent_on_checked: bool = False
    checked_icon_path: Path | None = None


class IconToolButton(QToolButton):
    hoverChanged = Signal(bool)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._hovered = False

    @property
    def is_hovered(self) -> bool:
        return self._hovered

    def enterEvent(self, event) -> None:  # type: ignore[override]
        if not self._hovered:
            self._hovered = True
            self.hoverChanged.emit(True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        if self._hovered:
            self._hovered = False
            self.hoverChanged.emit(False)
        super().leaveEvent(event)


class FlowLayout(QLayout):
    def __init__(self, parent: QWidget | None = None, margin: int = 0, spacing: int = -1) -> None:
        super().__init__(parent)
        self.item_list: list[QLayoutItem] = []
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing if spacing >= 0 else 8)

    def addItem(self, item) -> None:  # type: ignore[override]
        self.item_list.append(item)

    def addStretch(self, stretch: int = 0) -> None:
        spacer = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.addItem(spacer)

    def count(self) -> int:  # type: ignore[override]
        return len(self.item_list)

    def itemAt(self, index: int):  # type: ignore[override]
        if 0 <= index < len(self.item_list):
            return self.item_list[index]
        return None

    def takeAt(self, index: int):  # type: ignore[override]
        if 0 <= index < len(self.item_list):
            return self.item_list.pop(index)
        return None

    def expandingDirections(self):  # type: ignore[override]
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self) -> bool:  # type: ignore[override]
        return True

    def heightForWidth(self, width: int) -> int:  # type: ignore[override]
        return self._do_layout(QRectF(0, 0, width, 0), True)

    def setGeometry(self, rect) -> None:  # type: ignore[override]
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self) -> QSize:  # type: ignore[override]
        return self.minimumSize()

    def minimumSize(self) -> QSize:  # type: ignore[override]
        size = QSize()
        for item in self.item_list:
            size = size.expandedTo(item.minimumSize())
        left, top, right, bottom = self.getContentsMargins()
        size += QSize(left + right, top + bottom)
        return size

    def _do_layout(self, rect, test_only: bool) -> int:
        spacing = self.spacing()
        left, top, right, bottom = self.getContentsMargins()
        effective_rect = QRectF(
            rect.x() + left, rect.y() + top, rect.width() - left - right, rect.height() - top - bottom
        )
        x = effective_rect.x()
        y = effective_rect.y()
        line_height = 0

        for item in self.item_list:
            next_x = x + item.sizeHint().width() + spacing
            if next_x - spacing > effective_rect.right() and line_height > 0:
                x = effective_rect.x()
                y = y + line_height + spacing
                next_x = x + item.sizeHint().width() + spacing
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(int(x), int(y), item.sizeHint().width(), item.sizeHint().height()))

            x = next_x
            line_height = max(line_height, item.sizeHint().height())

        return int(y + line_height - rect.y() + bottom)
