from __future__ import annotations

from PySide6.QtWidgets import QApplication, QLabel

from slidequest.views.master.ai_status import AIStatusIndicator


def _ensure_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_status_indicator_updates_label() -> None:
    _ensure_app()
    indicator = AIStatusIndicator()
    label = QLabel()
    indicator.attach_label(label)

    indicator.set_status("Working")
    assert label.text() == "Working"

    indicator.set_status("")
    assert label.text() == "Bereit"


def test_status_indicator_callback_called() -> None:
    _ensure_app()
    calls: list[str] = []
    indicator = AIStatusIndicator(on_change=calls.append)
    indicator.set_status("Hello")
    indicator.set_status("World")
    assert calls == ["Hello", "World"]
    indicator.set_status("")
    assert calls[-1] == "Bereit"
