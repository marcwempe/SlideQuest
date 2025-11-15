from __future__ import annotations

from pathlib import Path

import pytest

from slidequest.views.master.ai_reference_store import ReferenceImageStore


class _DummyProjectService:
    def __init__(self, root: Path, *, fail_on: set[str] | None = None) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)
        self._fail_on = fail_on or set()

    def import_file(self, bucket: str, file_path: str) -> str:
        src = Path(file_path)
        if not src.exists():
            raise FileNotFoundError(file_path)
        if src.name in self._fail_on:
            raise FileNotFoundError(file_path)
        dest = self._root / f"{bucket}-{src.name}"
        dest.write_bytes(src.read_bytes())
        return f"{bucket}/{dest.name}"

    def resolve_asset_path(self, asset_id: str) -> Path:
        return self._root / asset_id.split("/", 1)[1]


def _create_image(path: Path, *, content: bytes = b"data") -> None:
    path.write_bytes(content)


def test_add_files_returns_stats_and_deduplicates(tmp_path: Path) -> None:
    storage = _DummyProjectService(tmp_path)
    store = ReferenceImageStore(storage)
    img1 = tmp_path / "img1.png"
    img2 = tmp_path / "img2.png"
    _create_image(img1)
    _create_image(img2, content=b"other")

    stats = store.add_files([str(img1), str(img2)])
    assert stats.attempted == 2
    assert stats.added == 2
    assert len(store.ids()) == 2

    stats_second = store.add_files([str(img1), str(img2)])
    assert stats_second.attempted == 2
    assert stats_second.added == 0


def test_add_files_reports_progress(tmp_path: Path) -> None:
    storage = _DummyProjectService(tmp_path)
    store = ReferenceImageStore(storage)
    images = []
    for idx in range(3):
        img = tmp_path / f"img{idx}.png"
        _create_image(img, content=bytes([idx]))
        images.append(str(img))

    ticks: list[tuple[int, int]] = []

    def on_progress(done: int, total: int) -> None:
        ticks.append((done, total))

    stats = store.add_files(images, on_progress=on_progress)
    assert stats.added == 3
    assert ticks[0] == (1, 3)
    assert ticks[-1] == (3, 3)
    # ensure monotonic progress
    assert [done for done, _ in ticks] == sorted(done for done, _ in ticks)


def test_add_files_collects_failures(tmp_path: Path) -> None:
    storage = _DummyProjectService(tmp_path, fail_on={"bad.png"})
    store = ReferenceImageStore(storage)
    good = tmp_path / "good.png"
    bad = tmp_path / "bad.png"
    _create_image(good)
    _create_image(bad)
    missing = tmp_path / "missing.png"

    stats = store.add_files([str(good), str(bad), str(missing)])
    assert stats.added == 1
    assert len(stats.failed) == 2
    failed_paths = {path for path, _ in stats.failed}
    assert str(missing) in failed_paths
    assert str(bad) in failed_paths
    # reason strings present
    reasons = {path: reason for path, reason in stats.failed}
    assert "Datei nicht gefunden" in reasons[str(missing)]
    assert "Import fehlgeschlagen" in reasons[str(bad)]
