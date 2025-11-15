from __future__ import annotations

from PySide6.QtWidgets import QApplication, QLabel, QToolButton
from PySide6.QtGui import QPixmap

from slidequest.models.slide import (
    SlideAudioPayload,
    SlideData,
    SlideLayoutPayload,
    SlideNotesPayload,
)
from slidequest.views.widgets.slide_item_widget import SlideListItemWidget


def _ensure_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _make_slide(title: str = "Title", subtitle: str = "Sub", group: str = "Group") -> SlideData:
    layout = SlideLayoutPayload("1S|100/1R|100")
    audio = SlideAudioPayload()
    notes = SlideNotesPayload()
    return SlideData(title, subtitle, group, layout=layout, audio=audio, notes=notes)


def test_slide_item_widget_updates_content(qtbot) -> None:
    _ensure_app()
    slide = _make_slide()
    pixmap = QPixmap(10, 10)
    widget = SlideListItemWidget(slide, pixmap)
    qtbot.addWidget(widget)

    new_slide = _make_slide("New", "Sub2", "Group2")
    widget.set_slide(new_slide, pixmap)
    assert widget.findChild(QLabel, "SlideItemTitle").text() == "New"


def test_slide_item_widget_emits_move_requests(qtbot) -> None:
    _ensure_app()
    slide = _make_slide()
    pixmap = QPixmap(10, 10)
    widget = SlideListItemWidget(slide, pixmap)
    qtbot.addWidget(widget)

    received = []
    widget.moveRequested.connect(lambda s, offset: received.append((s, offset)))

    widget.findChild(QToolButton, "SlideItemMoveUp").click()
    widget.findChild(QToolButton, "SlideItemMoveDown").click()

    assert received == [(slide, -1), (slide, 1)]
