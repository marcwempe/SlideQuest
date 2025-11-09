from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QPointF, Qt, QMimeData, QUrl
from PySide6.QtGui import QDropEvent

from slidequest.views.widgets.playlist_list import PlaylistListWidget


@pytest.mark.usefixtures("qt_app")
def test_files_dropped_emits_paths(tmp_path: Path) -> None:
    widget = PlaylistListWidget()
    widget.show()  # Ensure widget has a window handle for events

    dropped = []

    def capture(paths: list[str]) -> None:
        dropped.append(paths)

    widget.filesDropped.connect(capture)

    file_path = tmp_path / "track.mp3"
    file_path.write_bytes(b"test")

    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(file_path))])

    event = QDropEvent(
        QPointF(5, 5),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    widget.dropEvent(event)

    assert dropped, "filesDropped signal should emit at least once"
    assert str(file_path) in dropped[0]
