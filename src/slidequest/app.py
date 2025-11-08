from __future__ import annotations

import sys

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QScrollArea,
    QSplitter,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


STATUS_BAR_SIZE = 48
EXPLORER_HEADER_HEIGHT = 60
EXPLORER_FOOTER_HEIGHT = EXPLORER_HEADER_HEIGHT
DETAIL_HEADER_HEIGHT = 60
DETAIL_FOOTER_HEIGHT = DETAIL_HEADER_HEIGHT


class ViewLabel(QLabel):
    """Utility label that can rotate text when used in vertical regions."""

    def __init__(self, text: str, rotate: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self._rotate = rotate
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("font-weight: 600; color: #0f0f0f;")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def sizeHint(self) -> QSize:
        hint = super().sizeHint()
        if not self._rotate:
            return hint
        return hint.transposed()

    def minimumSizeHint(self) -> QSize:
        hint = super().minimumSizeHint()
        if not self._rotate:
            return hint
        return hint.transposed()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        if not self._rotate:
            super().paintEvent(event)
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        painter.translate(self.width() / 2, self.height() / 2)
        painter.rotate(-90)
        rect = QRect(-self.height() // 2, -self.width() // 2, self.height(), self.width())
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text())
        painter.end()


class MasterWindow(QMainWindow):
    """Top-level control surface for SlideQuest."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SlideQuest – Master")
        self.setMinimumSize(960, 600)
        self._setup_placeholder()

    def _stamp_label(self, host: QWidget, text: str, rotate: bool = False) -> None:
        layout = host.layout()
        if layout is None:
            layout = QVBoxLayout(host)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
        label = ViewLabel(text, rotate, host)
        layout.addWidget(label)

    def _setup_placeholder(self) -> None:
        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        status_bar = QFrame(central)
        status_bar.setObjectName("statusBar")
        status_bar.setFixedHeight(STATUS_BAR_SIZE)
        self._stamp_label(status_bar, "StatusBar")

        viewport = QFrame(central)
        viewport.setObjectName("appViewport")
        viewport_layout = QHBoxLayout(viewport)
        viewport_layout.setContentsMargins(0, 0, 0, 0)
        viewport_layout.setSpacing(0)

        symbol_view = QFrame(viewport)
        symbol_view.setObjectName("symbolView")
        symbol_view.setFixedWidth(STATUS_BAR_SIZE)
        self._stamp_label(symbol_view, "SymbolView", rotate=True)

        splitter = QSplitter(Qt.Orientation.Horizontal, viewport)
        splitter.setObjectName("contentSplitter")
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(8)

        explorer_container = QWidget(splitter)
        explorer_container.setObjectName("explorerView")
        explorer_layout = QVBoxLayout(explorer_container)
        explorer_layout.setContentsMargins(0, 0, 0, 0)
        explorer_layout.setSpacing(0)

        explorer_header = QFrame(explorer_container)
        explorer_header.setObjectName("explorerHeaderView")
        explorer_header.setFixedHeight(EXPLORER_HEADER_HEIGHT)
        self._stamp_label(explorer_header, "ExplorerHeaderView")

        explorer_footer = QFrame(explorer_container)
        explorer_footer.setObjectName("explorerFooterView")
        explorer_footer.setFixedHeight(EXPLORER_FOOTER_HEIGHT)
        self._stamp_label(explorer_footer, "ExplorerFooterView")

        explorer_main_scroll = QScrollArea(explorer_container)
        explorer_main_scroll.setObjectName("explorerMainScroll")
        explorer_main_scroll.setWidgetResizable(True)
        explorer_main_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        explorer_main_scroll.setFrameShape(QFrame.Shape.NoFrame)

        explorer_main = QWidget()
        explorer_main.setObjectName("explorerMainView")
        self._stamp_label(explorer_main, "ExplorerMainView")
        explorer_main_scroll.setWidget(explorer_main)

        explorer_layout.addWidget(explorer_header)
        explorer_layout.addWidget(explorer_main_scroll, 1)
        explorer_layout.addWidget(explorer_footer)

        detail_container = QWidget(splitter)
        detail_container.setObjectName("detailView")
        detail_layout = QVBoxLayout(detail_container)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.setSpacing(0)

        detail_header = QFrame(detail_container)
        detail_header.setObjectName("detailHeaderView")
        detail_header.setFixedHeight(DETAIL_HEADER_HEIGHT)
        self._stamp_label(detail_header, "DetailHeaderView")

        detail_footer = QFrame(detail_container)
        detail_footer.setObjectName("detailFooterView")
        detail_footer.setFixedHeight(DETAIL_FOOTER_HEIGHT)
        self._stamp_label(detail_footer, "DetailFooterView")

        detail_main_scroll = QScrollArea(detail_container)
        detail_main_scroll.setObjectName("detailMainScroll")
        detail_main_scroll.setWidgetResizable(True)
        detail_main_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        detail_main_scroll.setFrameShape(QFrame.Shape.NoFrame)

        detail_main = QWidget()
        detail_main.setObjectName("detailMainView")
        self._stamp_label(detail_main, "DetailMainView")
        detail_main_scroll.setWidget(detail_main)

        detail_layout.addWidget(detail_header)
        detail_layout.addWidget(detail_main_scroll, 1)
        detail_layout.addWidget(detail_footer)

        splitter.addWidget(explorer_container)
        splitter.addWidget(detail_container)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)

        viewport_layout.addWidget(symbol_view)
        viewport_layout.addWidget(splitter, 1)

        layout.addWidget(status_bar)
        layout.addWidget(viewport, 1)
        central.setLayout(layout)

        self.setCentralWidget(central)
        self._apply_debug_palette()

    def _apply_debug_palette(self) -> None:
        self.setStyleSheet(
            """
            #statusBar {
                background-color: #ff4d4f;
            }
            #appViewport {
                background-color: #36cfc9;
            }
            #symbolView {
                background-color: #fadb14;
            }
            #explorerView {
                background-color: #13c2c2;
            }
            #explorerHeaderView {
                background-color: #ff7a45;
            }
            #explorerMainView {
                background-color: #bae637;
            }
            #explorerFooterView {
                background-color: #40a9ff;
            }
            #detailView {
                background-color: #722ed1;
            }
            #detailHeaderView {
                background-color: #ff85c0;
            }
            #detailMainView {
                background-color: #ffd666;
            }
            #detailFooterView {
                background-color: #69c0ff;
            }
            QSplitter#contentSplitter::handle {
                background-color: #000000;
            }
        """
        )


class PresentationWindow(QMainWindow):
    """Second window dedicated to rendering slides."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SlideQuest – Presentation")
        self.setMinimumSize(1280, 720)
        self._setup_placeholder()

    def _setup_placeholder(self) -> None:
        self.setCentralWidget(QWidget(self))


def main() -> None:
    """Launch the PySide6 GUI."""
    app = QApplication.instance()
    owns_event_loop = app is None
    if owns_event_loop:
        app = QApplication(sys.argv)
    master = MasterWindow()
    presentation = PresentationWindow()
    master.show()
    presentation.show()
    if owns_event_loop:
        assert app is not None
        sys.exit(app.exec())
