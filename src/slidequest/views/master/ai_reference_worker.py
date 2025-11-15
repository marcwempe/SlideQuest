from __future__ import annotations

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

from slidequest.views.master.ai_reference_store import ReferenceImageStore, ReferenceImportStats


class ReferenceImageImporter(QObject):
    finished = Signal(object)
    progress = Signal(int, int)

    def __init__(self, store: ReferenceImageStore, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._store = store
        self._pool = QThreadPool.globalInstance()

    def import_async(self, paths: list[str]) -> None:
        if not paths:
            self.finished.emit(ReferenceImportStats())
            return
        runnable = _ReferenceImportRunnable(self._store, paths, self.finished, self.progress)
        self._pool.start(runnable)


class _ReferenceImportRunnable(QRunnable):
    def __init__(
        self,
        store: ReferenceImageStore,
        paths: list[str],
        finished_signal,
        progress_signal,
    ) -> None:
        super().__init__()
        self._store = store
        self._paths = paths
        self._finished_signal = finished_signal
        self._progress_signal = progress_signal

    def run(self) -> None:  # type: ignore[override]
        callback = None
        if self._progress_signal is not None:
            def _emit(processed: int, total: int) -> None:
                self._progress_signal.emit(processed, total)

            callback = _emit
        stats = self._store.add_files(self._paths, on_progress=callback)
        self._finished_signal.emit(stats)
