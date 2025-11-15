from __future__ import annotations

from slidequest.views.master.ai_reference_store import ReferenceImportStats
from slidequest.views.master.ai_reference_worker import _ReferenceImportRunnable


class _DummyStore:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def add_files(self, raw_paths, *, on_progress=None):
        stats = ReferenceImportStats(attempted=len(raw_paths), added=len(raw_paths))
        for idx, _path in enumerate(raw_paths, start=1):
            if on_progress:
                on_progress(idx, len(raw_paths))
        self.calls.append(list(raw_paths))
        return stats


class _SignalCollector:
    def __init__(self) -> None:
        self.emitted: list = []

    def emit(self, *args):
        self.emitted.append(args if len(args) > 1 else args[0])


def test_reference_import_runnable_emits_progress_and_finished() -> None:
    store = _DummyStore()
    finished = _SignalCollector()
    progress = _SignalCollector()

    runnable = _ReferenceImportRunnable(store, ["a", "b"], finished, progress)
    runnable.run()

    assert store.calls == [["a", "b"]]
    assert progress.emitted[-1] == (2, 2)
    stats = finished.emitted[0]
    assert stats.attempted == 2
    assert stats.added == 2
