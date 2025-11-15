from __future__ import annotations

from PySide6.QtWidgets import QApplication, QTextEdit

from slidequest.views.master.ai_prompt_binding import TextBinding


def _ensure_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_text_binding_sync_and_write() -> None:
    _ensure_app()
    editor = QTextEdit()
    state = {"value": "hello", "writes": []}

    def read() -> str:
        return state["value"]

    def write(val: str) -> None:
        state["value"] = val
        state["writes"].append(val)

    binding = TextBinding(editor, read=read, write=write)
    # initial sync pulls read value
    binding.sync()
    assert editor.toPlainText() == "hello"

    # user edits -> write called
    editor.setPlainText("world")
    assert state["value"] == "world"
    assert state["writes"][-1] == "world"

    # sync avoids redundant write
    state["value"] = "final"
    binding.sync()
    assert editor.toPlainText() == "final"
    assert state["writes"][-1] == "world"


def test_text_binding_on_change() -> None:
    _ensure_app()
    editor = QTextEdit()
    events: list[str] = []

    def read() -> str:
        return ""

    binding = TextBinding(editor, read=read, on_change=events.append)
    editor.setPlainText("foo")
    editor.setPlainText("bar")
    assert events == ["foo", "bar"]
