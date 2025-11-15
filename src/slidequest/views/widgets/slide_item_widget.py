from __future__ import annotations

from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QFont, QPixmap, QIcon
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QToolButton, QVBoxLayout

from slidequest.ui.constants import ACTION_ICONS


class SlideListItemWidget(QFrame):
    moveRequested = Signal(object, int)

    def __init__(self, slide, preview: QPixmap, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("SlideListViewItem")
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self._slide = slide

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        self._preview = QLabel(self)
        self._preview.setObjectName("SlideItemPreview")
        self._preview.setFixedSize(96, 72)
        self._preview.setScaledContents(True)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        self._title = QLabel(self)
        self._title.setObjectName("SlideItemTitle")
        title_font = QFont(self._title.font())
        title_font.setPointSize(max(12, title_font.pointSize()))
        title_font.setWeight(QFont.Weight.DemiBold)
        self._title.setFont(title_font)

        self._subtitle = QLabel(self)
        self._subtitle.setObjectName("SlideItemSubtitle")

        self._group = QLabel(self)
        self._group.setObjectName("SlideItemGroup")
        group_font = QFont(self._group.font())
        group_font.setPointSize(max(10, group_font.pointSize() - 2))
        self._group.setFont(group_font)

        text_layout.addWidget(self._title)
        text_layout.addWidget(self._subtitle)
        text_layout.addWidget(self._group)

        layout.addWidget(self._preview)
        layout.addLayout(text_layout, 1)

        controls = QVBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(4)

        self._move_up = QToolButton(self)
        self._move_up.setObjectName("SlideItemMoveUp")
        self._move_up.setIcon(QIcon(str(ACTION_ICONS["move_up"])))
        self._move_up.setIconSize(QSize(16, 16))
        self._move_up.setAutoRaise(True)
        self._move_up.setCursor(Qt.CursorShape.PointingHandCursor)
        self._move_up.setToolTip("Folie nach oben verschieben")
        self._move_up.clicked.connect(lambda: self.moveRequested.emit(self._slide, -1))

        self._move_down = QToolButton(self)
        self._move_down.setObjectName("SlideItemMoveDown")
        self._move_down.setIcon(QIcon(str(ACTION_ICONS["move_down"])))
        self._move_down.setIconSize(QSize(16, 16))
        self._move_down.setAutoRaise(True)
        self._move_down.setCursor(Qt.CursorShape.PointingHandCursor)
        self._move_down.setToolTip("Folie nach unten verschieben")
        self._move_down.clicked.connect(lambda: self.moveRequested.emit(self._slide, 1))

        controls.addWidget(self._move_up)
        controls.addWidget(self._move_down)
        controls.addStretch(1)

        layout.addLayout(controls)

        self.set_slide(slide, preview)

    def set_slide(self, slide, preview: QPixmap) -> None:
        self._slide = slide
        self._title.setText(slide.title)
        self._subtitle.setText(slide.subtitle)
        self._group.setText(slide.group)
        self._preview.setPixmap(preview)

    def set_move_enabled(self, up_enabled: bool, down_enabled: bool) -> None:
        self._move_up.setEnabled(up_enabled)
        self._move_down.setEnabled(down_enabled)
