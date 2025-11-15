from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import QLabel


class AIStatusIndicator:
    """Keeps the Seedream status label in sync and emits optional callbacks."""

    def __init__(self, *, on_change: Callable[[str], None] | None = None) -> None:
        self._label: QLabel | None = None
        self._on_change = on_change
        self._message = "Bereit"

    def attach_label(self, label: QLabel) -> None:
        self._label = label
        self._label.setText(self._message)

    def set_status(self, message: str) -> None:
        cleaned = message.strip() if message else ""
        text = cleaned or "Bereit"
        self._message = text
        if self._label is not None:
            self._label.setText(text)
        if self._on_change is not None:
            self._on_change(text)

    @property
    def message(self) -> str:
        return self._message

