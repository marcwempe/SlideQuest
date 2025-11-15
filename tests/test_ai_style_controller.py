from __future__ import annotations

from PySide6.QtWidgets import QApplication, QTextEdit, QToolButton

from slidequest.views.master.ai_style_controller import StylePromptController


def _ensure_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class _DummyViewModel:
    def __init__(self, value: str = "") -> None:
        self._value = value
        self.calls: list[str] = []

    def style_prompt(self) -> str:
        return self._value

    def set_style_prompt(self, value: str) -> None:
        self._value = value
        self.calls.append(value)


def test_style_prompt_controller_syncs_editor_and_toggle() -> None:
    _ensure_app()
    editor = QTextEdit()
    toggle = QToolButton()
    toggle.setCheckable(True)
    vm = _DummyViewModel("Initial")

    controller = StylePromptController(editor=editor, toggle=toggle, viewmodel=vm)
    assert editor.toPlainText() == "Initial"
    assert toggle.isChecked() is False

    editor.setPlainText("")
    assert vm.style_prompt() == ""
    assert toggle.isChecked() is True

    vm.set_style_prompt("Filled")
    controller.sync()
    assert editor.toPlainText() == "Filled"
    assert toggle.isChecked() is False
