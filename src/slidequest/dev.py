from __future__ import annotations

import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Iterable

from watchfiles import Change, watch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
WATCH_PATHS: tuple[Path, ...] = (
    SRC_ROOT / "slidequest",
    PROJECT_ROOT / "pyproject.toml",
)


def _spawn_app() -> subprocess.Popen[bytes]:
    env = os.environ.copy()
    env.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    return subprocess.Popen(
        [sys.executable, "-m", "slidequest"],
        cwd=PROJECT_ROOT,
        env=env,
    )


def _stop_app(proc: subprocess.Popen[bytes]) -> None:
    if proc.poll() is not None:
        return
    proc.send_signal(signal.SIGINT)
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def _format_changes(changes: Iterable[tuple[Change, str]]) -> str:
    first = next(iter(changes), None)
    if first is None:
        return ""
    change, path = first
    resolved = Path(path).resolve()
    try:
        relative = resolved.relative_to(PROJECT_ROOT)
    except ValueError:
        relative = resolved
    return f"{change.name.lower()} {relative}"


def main() -> None:
    """Run SlideQuest in a watcher that restarts on file changes."""
    print("Starting SlideQuest dev watcher...")
    proc = _spawn_app()
    try:
        for changes in watch(*WATCH_PATHS, stop_event=None):
            readable = _format_changes(changes)
            if readable:
                print(f"Detected change: {readable}. Reloading...")
            _stop_app(proc)
            proc = _spawn_app()
    except KeyboardInterrupt:
        print("\nStopping watcher.")
    finally:
        _stop_app(proc)
