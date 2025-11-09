from __future__ import annotations

import os
import pytest
from PySide6.QtWidgets import QApplication

# Ensure headless platform for CI/dev
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def qt_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    # Do not quit the global app to avoid PySide warnings between tests
