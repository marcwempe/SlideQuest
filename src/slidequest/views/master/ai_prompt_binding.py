from __future__ import annotations

from typing import Callable

from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QTextEdit


class TextBinding:
    """Two-way binds a QTextEdit to arbitrary read/write callables."""

    def __init__(
        self,
        editor: QTextEdit,
        *,
        read: Callable[[], str],
        write: Callable[[str], None] | None = None,
        on_change: Callable[[str], None] | None = None,
    ) -> None:
        self._editor = editor
        self._read = read
        self._write = write
        self._on_change = on_change
        self._syncing = False
        editor.textChanged.connect(self._handle_text_changed)

    def sync(self) -> None:
        value = self._read()
        if self._editor.toPlainText() == value:
            return
        self._syncing = True
        self._editor.setPlainText(value)
        self._editor.moveCursor(QTextCursor.MoveOperation.End)
        self._syncing = False

    def _handle_text_changed(self) -> None:
        if self._syncing:
            return
        text = self._editor.toPlainText()
        if self._write is not None:
            self._write(text)
        if self._on_change is not None:
            self._on_change(text)

