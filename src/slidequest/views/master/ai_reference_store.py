from __future__ import annotations

import base64
import mimetypes
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Callable, Iterable

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap

from slidequest.views.master.ai_models import ProjectServiceProtocol


@dataclass(slots=True)
class ReferenceImportStats:
    attempted: int = 0
    added: int = 0
    failed: list[tuple[str, str]] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return self.added > 0


class ReferenceImageStore:
    """Centralises reference-image bookkeeping and encoding."""

    def __init__(self, project_service: ProjectServiceProtocol) -> None:
        self._project_service = project_service
        self._image_ids: list[str] = []
        self._lock = Lock()

    def ids(self) -> list[str]:
        with self._lock:
            return list(self._image_ids)

    def add_files(
        self,
        raw_paths: Iterable[str],
        *,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> ReferenceImportStats:
        paths = list(raw_paths)
        total = len(paths)
        stats = ReferenceImportStats(attempted=total, added=0)
        processed = 0
        for raw in paths:
            source = raw[7:] if raw.startswith("file://") else raw
            file_path = Path(source)
            failed = False
            reason = ""
            if not file_path.exists():
                failed = True
                reason = "Datei nicht gefunden"
            else:
                try:
                    stored = self._project_service.import_file("replicate", str(file_path))
                except FileNotFoundError:
                    failed = True
                    reason = "Import fehlgeschlagen"
                else:
                    with self._lock:
                        if stored in self._image_ids:
                            stored = ""
                        else:
                            self._image_ids.append(stored)
                    if stored:
                        stats.added += 1
                    else:
                        failed = False  # duplicate handled silently
            if failed:
                stats.failed.append((raw, reason or "Unbekannter Fehler"))
            processed += 1
            if on_progress is not None and total:
                on_progress(processed, total)
        return stats

    def remove(self, asset_id: str) -> bool:
        with self._lock:
            try:
                self._image_ids.remove(asset_id)
            except ValueError:
                return False
            return True

    def clear_missing(self) -> None:
        valid: list[str] = []
        with self._lock:
            current = list(self._image_ids)
        for asset_id in current:
            absolute = self._project_service.resolve_asset_path(asset_id)
            if absolute.exists():
                valid.append(asset_id)
        with self._lock:
            self._image_ids = valid

    def encode_images(self) -> list[str]:
        encoded: list[str] = []
        with self._lock:
            asset_ids = list(self._image_ids)
        for asset_id in asset_ids:
            absolute = self._project_service.resolve_asset_path(asset_id)
            try:
                data = absolute.read_bytes()
            except OSError:
                continue
            mime, _ = mimetypes.guess_type(str(absolute))
            mime = mime or "image/png"
            b64 = base64.b64encode(data).decode("ascii")
            encoded.append(f"data:{mime};base64,{b64}")
        return encoded

    def iter_icons(self, icon_size: QSize):
        with self._lock:
            asset_ids = list(self._image_ids)
        for asset_id in asset_ids:
            absolute = self._project_service.resolve_asset_path(asset_id)
            pixmap = QPixmap(str(absolute))
            if pixmap.isNull():
                continue
            icon = QIcon(
                pixmap.scaled(
                    icon_size,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            yield asset_id, icon
