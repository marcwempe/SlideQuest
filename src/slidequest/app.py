from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from slidequest.views.master_window import MasterWindow
from slidequest.views.presentation_window import PresentationWindow


def main() -> None:
    """Launch the SlideQuest UI with master + presentation windows."""
    app = QApplication.instance()
    owns_event_loop = app is None
    if owns_event_loop:
        app = QApplication(sys.argv)
        app.setApplicationName("SlideQuest")
        app.setOrganizationName("SlideQuest")

    master = MasterWindow()
    presentation = PresentationWindow()
    presentation.hide()
    master.attach_presentation_window(presentation)
    master.show()

    if owns_event_loop:
        assert app is not None
        sys.exit(app.exec())
