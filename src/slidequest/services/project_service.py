from __future__ import annotations

import hashlib
import json
import os
import shutil
import uuid
from pathlib import Path
from typing import Any

try:  # pragma: no cover - Qt is optional in tests
    from PySide6.QtCore import QStandardPaths
except Exception:  # pragma: no cover - fallback when Qt unavailable
    QStandardPaths = None  # type: ignore[assignment]

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _default_appdata_dir() -> Path:
    """Resolve a writable base directory for project data."""
    if QStandardPaths is not None:
        location = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        if location:
            return Path(location)
    # Fallback for headless/test environments
    return PROJECT_ROOT / ".appdata"


class ProjectStorageService:
    """Manages project directories, project.json payloads, and deduplicated assets."""

    _active_project_dir: Path | None = None

    def __init__(self, project_id: str | None = None, base_dir: Path | None = None) -> None:
        self._base_dir = Path(base_dir) if base_dir else _default_appdata_dir() / "SlideQuest"
        self._project_id = project_id or "default"
        self._project_payload: dict[str, Any] | None = None
        ProjectStorageService._active_project_dir = self.project_dir

    # ------------------------------------------------------------------ #
    # Paths
    # ------------------------------------------------------------------ #
    @property
    def project_id(self) -> str:
        return self._project_id

    @property
    def projects_root(self) -> Path:
        return self._base_dir / "projects"

    @property
    def project_dir(self) -> Path:
        return self.projects_root / self._project_id

    @property
    def project_file(self) -> Path:
        return self.project_dir / "project.json"

    @property
    def base_dir(self) -> Path:
        return self._base_dir

    @classmethod
    def active_project_dir(cls) -> Path | None:
        return cls._active_project_dir

    def resolve_asset_path(self, relative_path: str) -> Path:
        candidate = Path(relative_path)
        if candidate.is_absolute():
            return candidate
        return (self.project_dir / candidate).resolve()

    def list_projects(self) -> list[str]:
        root = self.projects_root
        if not root.exists():
            return []
        return sorted(entry.name for entry in root.iterdir() if entry.is_dir())

    # ------------------------------------------------------------------ #
    # Project payload
    # ------------------------------------------------------------------ #
    def load_project(self) -> dict[str, Any]:
        if self._project_payload is None:
            self._project_payload = self._read_project()
        return self._project_payload

    def save_project(self, payload: dict[str, Any] | None = None) -> None:
        if payload is not None:
            self._project_payload = payload
        if self._project_payload is None:
            return
        self.project_dir.mkdir(parents=True, exist_ok=True)
        tmp = self.project_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._project_payload, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.project_file)

    def _read_project(self) -> dict[str, Any]:
        path = self.project_file
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass
        return {
            "id": self._project_id,
            "meta": {},
            "files": {},
            "slides": [],
        }

    # ------------------------------------------------------------------ #
    # Asset management
    # ------------------------------------------------------------------ #
    def import_file(self, kind: str, source: str) -> str:
        """Copy a file into the project folder with hash-deduplicated UUID naming."""
        source_path = Path(source)
        if not source_path.exists():
            raise FileNotFoundError(source)
        project = self.load_project()
        file_index: dict[str, Any] = project.setdefault("files", {})

        digest, size = self._hash_file(source_path)
        for file_id, info in file_index.items():
            if info.get("hash") == digest and info.get("size") == size and info.get("kind") == kind:
                return info.get("path", "")

        restored_path = self.restore_from_trash(kind, digest, size)
        if restored_path:
            file_id = uuid.uuid4().hex
            file_index[file_id] = {
                "kind": kind,
                "path": restored_path,
                "hash": digest,
                "size": size,
                "original_name": source_path.name,
            }
            self.save_project(project)
            return restored_path

        file_id = uuid.uuid4().hex
        extension = source_path.suffix.lower()
        relative_path = Path(kind) / f"{file_id}{extension}"
        target = self.project_dir / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target)

        file_index[file_id] = {
            "kind": kind,
            "path": relative_path.as_posix(),
            "hash": digest,
            "size": size,
            "original_name": source_path.name,
        }
        self.save_project(project)
        return relative_path.as_posix()

    def set_note_title(self, relative_path: str, title: str) -> None:
        project = self.load_project()
        updated = False
        for info in project.get("files", {}).values():
            if info.get("path") == relative_path:
                if title:
                    info["note_title"] = title
                else:
                    info.pop("note_title", None)
                updated = True
                break
        if updated:
            self.save_project(project)

    def note_title(self, relative_path: str) -> str:
        project = self.load_project()
        for info in project.get("files", {}).values():
            if info.get("path") == relative_path:
                return info.get("note_title") or ""
        return ""

    def soundboard_entries(self) -> list[dict[str, str]]:
        project = self.load_project()
        board = project.setdefault("soundboard", [])
        return [entry for entry in board if isinstance(entry, dict)]

    def set_soundboard_entries(self, entries: list[dict[str, str]]) -> None:
        project = self.load_project()
        project["soundboard"] = entries
        self.save_project(project)

    def trash_path(self) -> Path:
        path = self.project_dir / ".trash"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def move_to_trash(self, relative_path: str) -> None:
        if not relative_path:
            return
        source = self.resolve_asset_path(relative_path)
        if not source.exists():
            return
        trash = self.trash_path() / relative_path
        trash.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(trash))

    def restore_from_trash(self, kind: str, digest: str, size: int) -> str | None:
        trash = self.trash_path() / kind
        if not trash.exists():
            return None
        for entry in trash.iterdir():
            candidate = trash / entry.name
            if not candidate.is_file():
                continue
            file_hash, file_size = self._hash_file(candidate)
            if file_hash == digest and file_size == size:
                target = self.project_dir / kind / entry.name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(candidate), str(target))
                return (Path(kind) / entry.name).as_posix()
        return None

    def trash_size(self) -> int:
        trash = self.trash_path()
        total = 0
        for root, _dirs, files in os.walk(trash):
            for name in files:
                total += (Path(root) / name).stat().st_size
        return total

    @staticmethod
    def _hash_file(path: Path) -> tuple[str, int]:
        hasher = hashlib.sha256()
        size = 0
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(8192), b""):
                size += len(chunk)
                hasher.update(chunk)
        return hasher.hexdigest(), size
