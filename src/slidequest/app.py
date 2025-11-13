from __future__ import annotations

import logging
import os
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
        log_level = os.environ.get("PYTHONLOGLEVEL", "INFO").upper()
        resolved_level = getattr(logging, log_level, logging.INFO)
        root_logger = logging.getLogger()
        if not root_logger.handlers:
            logging.basicConfig(
                level=resolved_level,
                format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
            )
        else:
            root_logger.setLevel(resolved_level)

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
