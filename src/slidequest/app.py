from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QMainWindow, QWidget


class MasterWindow(QMainWindow):
    """Top-level control surface for SlideQuest."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SlideQuest – Master")
        self.setMinimumSize(960, 600)
        self._setup_placeholder()

    def _setup_placeholder(self) -> None:
        # Empty widget keeps the window visible without any layout yet.
        self.setCentralWidget(QWidget(self))


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
