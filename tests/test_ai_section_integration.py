from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget

from slidequest.views.master.ai_reference_store import ReferenceImportStats
from slidequest.views.master.ai_section import AISectionMixin


class _FakeReferenceStore:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def add_files(self, raw_paths, *, on_progress=None) -> ReferenceImportStats:
        stats = ReferenceImportStats(attempted=len(raw_paths), added=len(raw_paths))
        for idx, _ in enumerate(raw_paths, start=1):
            if on_progress:
                on_progress(idx, len(raw_paths))
        self.calls.append(list(raw_paths))
        return stats


class _TestSection(QWidget, AISectionMixin):
    result_ready = Signal()

    def __init__(self) -> None:
        QWidget.__init__(self)
        AISectionMixin.__init__(self)
        self._fake_store = _FakeReferenceStore()
        self._project_service = None
        self._viewmodel = None
        self._last_stats: ReferenceImportStats | None = None

    def _get_reference_store(self):  # type: ignore[override]
        return self._fake_store

    def _handle_reference_import_result(self, stats: ReferenceImportStats | None) -> None:  # type: ignore[override]
        self._last_stats = stats
        self.result_ready.emit()


def test_reference_import_signal_flow(qtbot) -> None:
    section = _TestSection()
    qtbot.addWidget(section)

    importer = section._get_reference_importer()
    assert importer is not None

    stats = ReferenceImportStats(attempted=2, added=2)
    importer.finished.emit(stats)

    qtbot.waitSignal(section.result_ready, timeout=1000)

    assert section._last_stats is stats
