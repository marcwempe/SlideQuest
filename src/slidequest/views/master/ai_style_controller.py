from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from PySide6.QtWidgets import QTextEdit, QToolButton

from slidequest.views.master.ai_prompt_binding import TextBinding


class StylePromptViewModel(Protocol):
    def style_prompt(self) -> str: ...

    def set_style_prompt(self, value: str) -> None: ...


@dataclass
class StylePromptController:
    editor: QTextEdit
    toggle: QToolButton | None
    viewmodel: StylePromptViewModel

    def __post_init__(self) -> None:
        self._binding = TextBinding(
            self.editor,
            read=self.viewmodel.style_prompt,
            write=self.viewmodel.set_style_prompt,
            on_change=self._handle_text_changed,
        )
        self.sync()

    def sync(self) -> None:
        self._binding.sync()
        self._handle_text_changed(self.editor.toPlainText())

    def _handle_text_changed(self, text: str) -> None:
        desired_expanded = not bool(text.strip())
        if self.toggle is None:
            return
        if self.toggle.isChecked() != desired_expanded:
            self.toggle.blockSignals(True)
            self.toggle.setChecked(desired_expanded)
            self.toggle.blockSignals(False)
