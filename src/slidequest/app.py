from __future__ import annotations

import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from slidequest.views.master_window import MasterWindow
from slidequest.views.presentation_window import PresentationWindow
from slidequest.views.launcher import LauncherWindow


def main() -> None:
    """Launch the SlideQuest UI with master + presentation windows."""
    app = QApplication.instance()
    owns_event_loop = app is None
    if owns_event_loop:
        app = QApplication(sys.argv)
        app.setApplicationName("SlideQuest")
        app.setOrganizationName("SlideQuest")

    launcher = LauncherWindow()
    launcher.show()

    def bootstrap() -> None:
        master = MasterWindow()
        presentation = PresentationWindow()
        presentation.hide()
        master.attach_presentation_window(presentation)

        elapsed = launcher.elapsed()
        remaining = max(0, 3000 - elapsed)

        def finish() -> None:
            master.show()
            launcher.close()

        QTimer.singleShot(remaining, finish)

    QTimer.singleShot(50, bootstrap)

    if owns_event_loop:
        assert app is not None
        sys.exit(app.exec())
