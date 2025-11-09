from __future__ import annotations

import re
from pathlib import Path

from slidequest.services.storage import PROJECT_ROOT


def slugify(value: str) -> str:
    """Convert arbitrary titles into filesystem-friendly slugs."""
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return value or "slide"


def resolve_media_path(path: str) -> str:
    """Return an absolute path for user-selected media."""
    candidate = Path(path)
    if candidate.is_absolute():
        return str(candidate)
    return str((PROJECT_ROOT / candidate).resolve())


def normalize_media_path(source: str) -> str:
    """Strip URL schemes and return project-relative paths when possible."""
    if source.startswith("file://"):
        source = source[7:]
    path = Path(source)
    if path.is_absolute():
        try:
            return str(path.relative_to(PROJECT_ROOT))
        except ValueError:
            return str(path)
    return source
