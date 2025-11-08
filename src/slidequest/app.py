from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

from PySide6.QtCore import QPoint, QRect, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QAction, QColor, QIcon, QPalette, QPainter, QPixmap, QPen
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLayout,
    QLayoutItem,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QComboBox,
    QScrollArea,
    QSpacerItem,
    QSizePolicy,
    QSplitter,
    QToolButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)


STATUS_BAR_SIZE = 48
SYMBOL_BUTTON_SIZE = STATUS_BAR_SIZE - 8
STATUS_ICON_SIZE = STATUS_BAR_SIZE - 12
ICON_PIXMAP_SIZE = 24
EXPLORER_HEADER_HEIGHT = 60
EXPLORER_FOOTER_HEIGHT = EXPLORER_HEADER_HEIGHT
DETAIL_HEADER_HEIGHT = 60
DETAIL_FOOTER_HEIGHT = DETAIL_HEADER_HEIGHT
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
SLIDES_FILE = DATA_DIR / "slides.json"
THUMBNAIL_DIR = PROJECT_ROOT / "assets" / "thumbnails"


def resolve_media_path(path: str) -> str:
    candidate = Path(path)
    if candidate.is_absolute():
        return str(candidate)
    return str((PROJECT_ROOT / candidate).resolve())
@dataclass(frozen=True)
class ButtonSpec:
    name: str
    icon: Path
    tooltip: str
    checkable: bool = False
    auto_exclusive: bool = False
    accent_on_checked: bool = False
    checked_icon: Path | None = None
    checked_by_default: bool = False


SYMBOL_BUTTON_SPECS: tuple[ButtonSpec, ...] = (
    ButtonSpec(
        "LayoutExplorerLauncher",
        PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "layouts" / "columns-gap.svg",
        "Layoutübersicht öffnen",
        checkable=True,
        auto_exclusive=True,
    ),
    ButtonSpec(
        "AudioExplorerLauncher",
        PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "audio" / "volume-up.svg",
        "Audio-Einstellungen öffnen",
        checkable=True,
        auto_exclusive=True,
    ),
    ButtonSpec(
        "NoteExplorerLauncher",
        PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "files" / "file-earmark.svg",
        "Notizübersicht öffnen",
        checkable=True,
        auto_exclusive=True,
    ),
    ButtonSpec(
        "FileExplorerLauncher",
        PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "files" / "folder.svg",
        "Dateiexplorer öffnen",
        checkable=True,
        auto_exclusive=True,
    ),
)

PRESENTATION_BUTTON_SPEC = ButtonSpec(
    "PresentationToggleButton",
    PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "window" / "window-fullscreen.svg",
    "Präsentationsfenster anzeigen",
)

STATUS_BUTTON_SPECS: tuple[ButtonSpec, ...] = (
    ButtonSpec(
        "StatusShuffleButton",
        PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "audio" / "shuffle.svg",
        "Shuffle aktivieren",
        checkable=True,
        accent_on_checked=True,
    ),
    ButtonSpec(
        "StatusPreviousTrackButton",
        PROJECT_ROOT
        / "assets"
        / "icons"
        / "bootstrap"
        / "audio"
        / "skip-backward-fill.svg",
        "Vorheriger Titel",
    ),
    ButtonSpec(
        "StatusPlayPauseButton",
        PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "audio" / "play-fill.svg",
        "Play/Pause",
        checkable=True,
        accent_on_checked=True,
        checked_icon=PROJECT_ROOT
        / "assets"
        / "icons"
        / "bootstrap"
        / "audio"
        / "pause-fill.svg",
    ),
    ButtonSpec(
        "StatusStopButton",
        PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "audio" / "stop-fill.svg",
        "Stopp",
    ),
    ButtonSpec(
        "StatusNextTrackButton",
        PROJECT_ROOT
        / "assets"
        / "icons"
        / "bootstrap"
        / "audio"
        / "skip-forward-fill.svg",
        "Nächster Titel",
    ),
    ButtonSpec(
        "StatusLoopButton",
        PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "audio" / "repeat.svg",
        "Loop aktivieren",
        checkable=True,
        accent_on_checked=True,
        checked_by_default=True,
    ),
    ButtonSpec(
        "StatusMuteButton",
        PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "audio" / "volume-mute.svg",
        "Stummschalten",
        checkable=True,
        accent_on_checked=True,
    ),
    ButtonSpec(
        "StatusVolumeDownButton",
        PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "audio" / "volume-down.svg",
        "Leiser",
    ),
    ButtonSpec(
        "StatusVolumeUpButton",
        PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "audio" / "volume-up.svg",
        "Lauter",
    ),
)

STATUS_VOLUME_BUTTONS = {
    "StatusMuteButton",
    "StatusVolumeDownButton",
    "StatusVolumeUpButton",
}

ACTION_ICONS = {
    "search": PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "actions" / "search.svg",
    "filter": PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "actions" / "filter.svg",
    "create": PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "actions" / "plus-square.svg",
    "edit": PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "actions" / "pencil-square.svg",
    "delete": PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "actions" / "trash.svg",
}

EXPLORER_CRUD_SPECS: tuple[ButtonSpec, ...] = (
    ButtonSpec("ExplorerCreateButton", ACTION_ICONS["create"], "Neuen Eintrag anlegen"),
    ButtonSpec("ExplorerDeleteButton", ACTION_ICONS["delete"], "Auswahl löschen"),
)


@dataclass
class LayoutItem:
    title: str
    subtitle: str
    layout: str
    group: str
    preview: Path | None = None
    images: dict[int, str] = field(default_factory=dict)


LAYOUT_ITEMS: tuple[LayoutItem, ...] = (
    LayoutItem("Einspaltig", "Vollflächige Anzeige", "1S|100/1R|100", "Standard"),
    LayoutItem("Zweispaltig", "Balance 60/40", "2S|60:40/1R:100/1R:100", "Standard"),
    LayoutItem("Dreispaltig", "Seitenleisten links/rechts", "3S|20:60:20/1R:100/1R:100/1R:100", "Standard"),
    LayoutItem("Moderator Panel", "Breite Bühne mit vier Slots", "2S|75:25/1R|100/4R|25:25:25:25", "Show"),
    LayoutItem("Fokus 3-1-3", "Zentrale Bühne mit Sidebars", "3S|20:60:20/2R|50:50/1R|100/2R|50:50", "Show"),
    LayoutItem("Matrix 3-1-3", "Drei Spalten mit 3/1/3 Reihen", "3S|12.5:75:12.5/3R|34:33:33/1R|100/3R|34:33:33", "Show"),
)


@dataclass
class SlideLayoutPayload:
    active_layout: str
    thumbnail_url: str = ""
    content: list[str] = field(default_factory=list)


@dataclass
class SlideAudioPayload:
    playlist: list[str] = field(default_factory=list)
    effects: list[str] = field(default_factory=list)


@dataclass
class SlideNotesPayload:
    notebooks: list[str] = field(default_factory=list)


@dataclass
class SlideData:
    title: str
    subtitle: str
    group: str
    layout: SlideLayoutPayload
    audio: SlideAudioPayload
    notes: SlideNotesPayload
    images: dict[int, str] = field(default_factory=dict)


@dataclass
class LayoutCell:
    x: float
    y: float
    width: float
    height: float
    area_id: int = 0


@dataclass
class RatioSpec:
    ratio: float = 0.0
    area_id: int = 0
    has_explicit_id: bool = False


def _slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return value or "slide"


def _parse_ratios(segment: str) -> list[float]:
    parts = [part.strip() for part in segment.split(':') if part.strip()]
    if not parts:
        return []
    ratios: list[float] = []
    wildcard_indices: list[int] = []
    remaining = 1.0
    for index, component in enumerate(parts):
        if component == '*':
            ratios.append(0.0)
            wildcard_indices.append(index)
            continue
        try:
            value = float(component)
        except ValueError:
            return []
        value /= 100.0
        ratios.append(value)
        remaining -= value
    if remaining < 0:
        remaining = 0.0
    if wildcard_indices:
        per = remaining / len(wildcard_indices) if wildcard_indices else 0.0
        for idx in wildcard_indices:
            ratios[idx] = per
    total = sum(ratios)
    if total <= 0:
        return []
    ratios = [value / total for value in ratios]
    return ratios


def _parse_ratio_specs(segment: str) -> list[RatioSpec]:
    parts = [part.strip() for part in segment.split(':') if part.strip()]
    if not parts:
        return []
    specs: list[RatioSpec] = []
    wildcard_indices: list[int] = []
    remaining = 1.0
    for index, component in enumerate(parts):
        spec = RatioSpec()
        if '#' in component:
            before, _, after = component.partition('#')
            after = after.strip()
            try:
                spec.area_id = int(after)
            except ValueError:
                return []
            spec.has_explicit_id = True
            component = before.strip()
        if component == '*':
            if spec.has_explicit_id:
                return []
            specs.append(spec)
            wildcard_indices.append(index)
            continue
        try:
            value = float(component)
        except ValueError:
            return []
        spec.ratio = value / 100.0
        remaining -= spec.ratio
        specs.append(spec)
    if remaining < 0:
        remaining = 0.0
    if wildcard_indices:
        per = remaining / len(wildcard_indices) if wildcard_indices else 0.0
        for idx in wildcard_indices:
            specs[idx].ratio = per
    total = sum(spec.ratio for spec in specs)
    if total <= 0:
        return []
    for spec in specs:
        spec.ratio /= total
    return specs


def parse_layout_description(layout_description: str) -> list[LayoutCell]:
    layout_description = layout_description.strip()
    if not layout_description:
        return [LayoutCell(0.0, 0.0, 1.0, 1.0, 1)]

    segments = [segment.strip() for segment in layout_description.split('/') if segment.strip()]
    if not segments:
        return []

    header_parts = [part.strip() for part in segments[0].split('|')]
    if len(header_parts) < 2:
        return []

    columns_token = header_parts[0]
    if not columns_token.endswith('S'):
        return []
    try:
        column_count = int(columns_token[:-1])
    except ValueError:
        return []
    if column_count <= 0:
        return []

    column_ratios = _parse_ratios(header_parts[1])
    if len(column_ratios) != column_count:
        return []

    columns: list[dict[str, list]] = [
        {"ratios": [], "specs": []} for _ in range(column_count)
    ]

    column_index = 0
    for segment in segments[1:]:
        if column_index >= column_count:
            break
        parts = [part.strip() for part in segment.split('|')]
        if len(parts) == 2:
            rows_token, ratios_token = parts
        else:
            sep_index = segment.find(':')
            if sep_index <= 0:
                return []
            rows_token = segment[:sep_index].strip()
            ratios_token = segment[sep_index + 1 :].strip()
        if not rows_token.endswith('R'):
            return []
        try:
            row_count = int(rows_token[:-1])
        except ValueError:
            return []
        if row_count <= 0:
            return []
        row_specs = _parse_ratio_specs(ratios_token)
        if len(row_specs) != row_count:
            return []
        columns[column_index]["ratios"] = [spec.ratio for spec in row_specs]
        columns[column_index]["specs"] = row_specs
        column_index += 1

    cells: list[LayoutCell] = []
    x = 0.0
    for col in range(column_count):
        column_width = column_ratios[col]
        if column_width <= 0:
            continue
        row_ratios: list[float] = columns[col]["ratios"] or [1.0]
        row_specs: list[RatioSpec] = columns[col]["specs"] or [RatioSpec(ratio=ratio) for ratio in row_ratios]
        y = 0.0
        for row, ratio in enumerate(row_ratios):
            if ratio <= 0:
                continue
            area_id = row_specs[row].area_id if row < len(row_specs) and row_specs[row].has_explicit_id else 0
            cells.append(LayoutCell(x, y, column_width, ratio, area_id))
            y += ratio
        x += column_width

    if not cells:
        return [LayoutCell(0.0, 0.0, 1.0, 1.0, 1)]

    used_ids = {cell.area_id for cell in cells if cell.area_id > 0}
    auto_indices = [index for index, cell in enumerate(cells) if cell.area_id <= 0]
    auto_indices.sort(key=lambda idx: cells[idx].width * cells[idx].height, reverse=True)
    candidate = 1
    for idx in auto_indices:
        while candidate in used_ids:
            candidate += 1
        cells[idx].area_id = candidate
        used_ids.add(candidate)
        candidate += 1
    return cells


@dataclass
class IconBinding:
    button: QToolButton
    icon_path: Path
    accent_on_checked: bool = False
    checked_icon_path: Path | None = None


class IconToolButton(QToolButton):
    hoverChanged = Signal(bool)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._hovered = False

    @property
    def is_hovered(self) -> bool:
        return self._hovered

    def enterEvent(self, event) -> None:  # type: ignore[override]
        if not self._hovered:
            self._hovered = True
            self.hoverChanged.emit(True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        if self._hovered:
            self._hovered = False
            self.hoverChanged.emit(False)
        super().leaveEvent(event)


class FlowLayout(QLayout):
    def __init__(self, parent: QWidget | None = None, margin: int = 0, spacing: int = -1) -> None:
        super().__init__(parent)
        self.item_list: list[QLayoutItem] = []
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing if spacing >= 0 else 8)

    def addItem(self, item) -> None:  # type: ignore[override]
        self.item_list.append(item)

    def addStretch(self, stretch: int = 0) -> None:
        spacer = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.addItem(spacer)

    def count(self) -> int:  # type: ignore[override]
        return len(self.item_list)

    def itemAt(self, index: int):  # type: ignore[override]
        if 0 <= index < len(self.item_list):
            return self.item_list[index]
        return None

    def takeAt(self, index: int):  # type: ignore[override]
        if 0 <= index < len(self.item_list):
            return self.item_list.pop(index)
        return None

    def expandingDirections(self):  # type: ignore[override]
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self) -> bool:  # type: ignore[override]
        return True

    def heightForWidth(self, width: int) -> int:  # type: ignore[override]
        return self._do_layout(QRectF(0, 0, width, 0), True)

    def setGeometry(self, rect) -> None:  # type: ignore[override]
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self) -> QSize:  # type: ignore[override]
        return self.minimumSize()

    def minimumSize(self) -> QSize:  # type: ignore[override]
        size = QSize()
        for item in self.item_list:
            size = size.expandedTo(item.minimumSize())
        left, top, right, bottom = self.getContentsMargins()
        size += QSize(left + right, top + bottom)
        return size

    def _do_layout(self, rect, test_only: bool) -> int:
        spacing = self.spacing()
        left, top, right, bottom = self.getContentsMargins()
        effective_rect = QRectF(rect.x() + left, rect.y() + top, rect.width() - left - right, rect.height() - top - bottom)
        x = effective_rect.x()
        y = effective_rect.y()
        line_height = 0

        for item in self.item_list:
            widget = item.widget()
            next_x = x + item.sizeHint().width() + spacing
            if next_x - spacing > effective_rect.right() and line_height > 0:
                x = effective_rect.x()
                y = y + line_height + spacing
                next_x = x + item.sizeHint().width() + spacing
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(int(x), int(y), item.sizeHint().width(), item.sizeHint().height()))

            x = next_x
            line_height = max(line_height, item.sizeHint().height())

        return int(y + line_height - rect.y() + bottom)


class LayoutPreviewCanvas(QWidget):
    areaDropped = Signal(int, str)

    def __init__(self, layout_description: str, parent: QWidget | None = None, *, accepts_drop: bool = False) -> None:
        super().__init__(parent)
        self._layout_description = layout_description
        self._cells = parse_layout_description(layout_description)
        self._selected = False
        self._area_images: dict[int, QPixmap] = {}
        self.setAcceptDrops(accepts_drop)

    def set_selected(self, selected: bool) -> None:
        if self._selected != selected:
            self._selected = selected
            self.update()

    def set_layout_description(self, layout_description: str) -> None:
        layout_description = layout_description or "1S|100/1R|100"
        if layout_description != self._layout_description:
            self._layout_description = layout_description
            self._cells = parse_layout_description(layout_description)
            self.update()

    def set_area_images(self, images: dict[int, str] | None) -> None:
        new_map: dict[int, QPixmap] = {}
        if images:
            for area_id, path in images.items():
                pix = QPixmap(path)
                if not pix.isNull():
                    new_map[area_id] = pix
        self._area_images = new_map
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), Qt.transparent)
        border_color = QColor("#000000")
        padding = 4
        available_width = max(self.width() - padding * 2, 1)
        available_height = max(self.height() - padding * 2, 1)
        for cell in self._cells:
            x = padding + cell.x * available_width
            y = padding + cell.y * available_height
            w = cell.width * available_width
            h = cell.height * available_height
            rect = QRectF(x, y, w, h)
            if pix := self._area_images.get(cell.area_id):
                pix_w = pix.width()
                pix_h = pix.height()
                if pix_w > 0 and pix_h > 0 and rect.width() > 0 and rect.height() > 0:
                    target_ratio = rect.width() / rect.height()
                    pix_ratio = pix_w / pix_h
                    if pix_ratio > target_ratio:
                        crop_width = int(pix_h * target_ratio)
                        x_offset = max((pix_w - crop_width) // 2, 0)
                        source = QRect(x_offset, 0, crop_width, pix_h)
                    else:
                        crop_height = int(pix_w / target_ratio)
                        y_offset = max((pix_h - crop_height) // 2, 0)
                        source = QRect(0, y_offset, pix_w, crop_height)
                    painter.drawPixmap(rect, pix, source)
            pen = QPen(border_color, 2 if self._selected else 1)
            painter.setPen(pen)
            painter.drawRect(rect)
        painter.end()

    def dragEnterEvent(self, event) -> None:  # type: ignore[override]
        if not self.acceptDrops():
            event.ignore()
            return
        if event.mimeData().hasUrls() or event.mimeData().hasImage() or event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:  # type: ignore[override]
        if self.acceptDrops():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:  # type: ignore[override]
        if not self.acceptDrops():
            event.ignore()
            return
        pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
        area_id = self._area_at_position(pos)
        if area_id <= 0:
            event.ignore()
            return
        source = ""
        mime = event.mimeData()
        if mime.hasUrls():
            url = mime.urls()[0]
            source = url.toLocalFile() or url.toString()
        elif mime.hasImage():
            image = QPixmap.fromImage(mime.imageData())
            temp_path = str(PROJECT_ROOT / "temp_drop_image.png")
            image.save(temp_path)
            source = temp_path
        elif mime.hasText():
            source = mime.text().strip()
        if not source:
            event.ignore()
            return
        self.areaDropped.emit(area_id, source)
        event.acceptProposedAction()

    def _area_at_position(self, pos) -> int:
        padding = 4
        available_width = max(self.width() - padding * 2, 1)
        available_height = max(self.height() - padding * 2, 1)
        for cell in self._cells:
            rect = QRectF(
                padding + cell.x * available_width,
                padding + cell.y * available_height,
                cell.width * available_width,
                cell.height * available_height,
            )
            if rect.contains(pos):
                return cell.area_id or 0
        return 0


class LayoutPreviewCard(QFrame):
    clicked = Signal(LayoutItem)

    def __init__(self, layout_item: LayoutItem, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._layout_item = layout_item
        self._selected = False
        self.setObjectName(f"layoutCard_{layout_item.title.replace(' ', '_')}")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(160, 140)

        frame_layout = QVBoxLayout(self)
        frame_layout.setContentsMargins(8, 8, 8, 8)
        frame_layout.setSpacing(6)

        self._canvas = LayoutPreviewCanvas(layout_item.layout, self)
        self._canvas.setFixedSize(140, 90)
        frame_layout.addWidget(self._canvas, alignment=Qt.AlignmentFlag.AlignHCenter)

        title_label = QLabel(layout_item.title, self)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 12px; color: #dbe3ff;")
        frame_layout.addWidget(title_label)

        self._update_styles()

    @property
    def layout_id(self) -> str:
        return self._layout_item.layout

    def setSelected(self, selected: bool) -> None:
        if self._selected != selected:
            self._selected = selected
            self._canvas.set_selected(selected)
            self._update_styles()

    def _update_styles(self) -> None:
        bg = "#2f3645" if self._selected else "#24262b"
        border = "#4c8bf5" if self._selected else "#3a3d42"
        self.setStyleSheet(
            f"QFrame#{self.objectName()} {{ background-color: {bg}; border: 1px solid {border}; border-radius: 10px; }}"
        )

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._layout_item)
        super().mousePressEvent(event)


class MasterWindow(QMainWindow):
    """Top-level control surface for SlideQuest."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SlideQuest – Master")
        self.setMinimumSize(960, 600)
        self._status_bar: QFrame | None = None
        self._symbol_view: QFrame | None = None
        self._presentation_button: QToolButton | None = None
        self._explorer_container: QWidget | None = None
        self._presentation_window: PresentationWindow | None = None
        self._symbol_buttons: list[QToolButton] = []
        self._symbol_button_map: dict[str, QToolButton] = {}
        self._status_buttons: list[QToolButton] = []
        self._status_button_map: dict[str, QToolButton] = {}
        self._header_views: list[QFrame] = []
        self._detail_container: QWidget | None = None
        self._line_edit_actions: list[tuple[QAction, Path]] = []
        self._search_input: QLineEdit | None = None
        self._filter_button: QToolButton | None = None
        self._crud_buttons: list[QToolButton] = []
        self._crud_button_map: dict[str, QToolButton] = {}
        self._volume_slider: QSlider | None = None
        self._volume_button_map: dict[str, QToolButton] = {}
        self._last_volume_value = 75
        self._icon_bindings: list[IconBinding] = []
        self._slides: list[SlideData] = []
        self._slide_list: QListWidget | None = None
        self._current_slide: SlideData | None = None
        self._detail_title_input: QLineEdit | None = None
        self._detail_subtitle_input: QLineEdit | None = None
        self._detail_group_combo: QComboBox | None = None
        self._detail_preview_canvas: LayoutPreviewCanvas | None = None
        self._related_layout_layout: QHBoxLayout | None = None
        self._related_layout_cards: list[LayoutPreviewCard] = []
        self._current_layout_id: str = ""
        self._icon_base_color = QColor("#ffffff")
        self._icon_accent_color = QColor("#ffffff")
        self._container_color = QColor("#222222")
        self._slides = self._load_slides()
        self._setup_placeholder()

    def _setup_placeholder(self) -> None:
        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        status_bar = QFrame(central)
        status_bar.setObjectName("statusBar")
        status_bar.setFixedHeight(STATUS_BAR_SIZE)
        self._status_bar = status_bar
        self._build_status_bar(status_bar)

        viewport = QFrame(central)
        viewport.setObjectName("appViewport")
        viewport_layout = QHBoxLayout(viewport)
        viewport_layout.setContentsMargins(0, 0, 0, 0)
        viewport_layout.setSpacing(0)

        symbol_view = QFrame(viewport)
        symbol_view.setObjectName("symbolView")
        symbol_view.setFixedWidth(STATUS_BAR_SIZE)
        self._symbol_view = symbol_view
        symbol_layout = QVBoxLayout(symbol_view)
        symbol_layout.setContentsMargins(4, 4, 4, 4)
        symbol_layout.setSpacing(8)
        self._symbol_button_map = self._build_buttons(
            symbol_view,
            symbol_layout,
            SYMBOL_BUTTON_SPECS,
            size=SYMBOL_BUTTON_SIZE,
            registry=self._symbol_buttons,
        )
        symbol_layout.addStretch(1)
        presentation_button = self._build_buttons(
            symbol_view,
            symbol_layout,
            (PRESENTATION_BUTTON_SPEC,),
            size=SYMBOL_BUTTON_SIZE,
            registry=self._symbol_buttons,
        )[PRESENTATION_BUTTON_SPEC.name]
        presentation_button.clicked.connect(self._show_presentation_window)
        self._presentation_button = presentation_button

        splitter = QSplitter(Qt.Orientation.Horizontal, viewport)
        splitter.setObjectName("contentSplitter")
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(8)

        explorer_container = QWidget(splitter)
        explorer_container.setObjectName("explorerView")
        self._explorer_container = explorer_container
        explorer_container.setMinimumWidth(282)
        explorer_layout = QVBoxLayout(explorer_container)
        explorer_layout.setContentsMargins(0, 0, 0, 0)
        explorer_layout.setSpacing(0)

        explorer_header = QFrame(explorer_container)
        explorer_header.setObjectName("explorerHeaderView")
        explorer_header.setFixedHeight(EXPLORER_HEADER_HEIGHT)
        self._header_views.append(explorer_header)
        explorer_header_layout = QHBoxLayout(explorer_header)
        explorer_header_layout.setContentsMargins(8, 4, 8, 4)
        explorer_header_layout.setSpacing(8)

        search_input = QLineEdit(explorer_header)
        search_input.setObjectName("ExplorerSearchInput")
        search_input.setPlaceholderText("Suche …")
        search_input.setToolTip("ExplorerSearchInput")
        search_input.setFixedHeight(SYMBOL_BUTTON_SIZE)
        search_action = search_input.addAction(
            QIcon(str(ACTION_ICONS["search"])),
            QLineEdit.ActionPosition.LeadingPosition,
        )
        self._line_edit_actions.append((search_action, ACTION_ICONS["search"]))
        self._search_input = search_input

        filter_button = self._create_icon_button(
            explorer_header,
            "ExplorerFilterButton",
            ACTION_ICONS["filter"],
            "Filter öffnen",
            checkable=True,
        )
        filter_button.setFixedSize(SYMBOL_BUTTON_SIZE, SYMBOL_BUTTON_SIZE)
        self._filter_button = filter_button

        explorer_header_layout.addWidget(search_input, 1)
        explorer_header_layout.addWidget(filter_button)

        explorer_footer = QFrame(explorer_container)
        explorer_footer.setObjectName("explorerFooterView")
        explorer_footer.setFixedHeight(EXPLORER_FOOTER_HEIGHT)

        explorer_main_scroll = QScrollArea(explorer_container)
        explorer_main_scroll.setObjectName("explorerMainScroll")
        explorer_main_scroll.setWidgetResizable(True)
        explorer_main_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        explorer_main_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        explorer_main_scroll.setStyleSheet("QScrollBar { width: 0px; }")
        explorer_main_scroll.setFrameShape(QFrame.Shape.NoFrame)

        explorer_main = QWidget()
        explorer_main.setObjectName("explorerMainView")
        explorer_main_layout = QVBoxLayout(explorer_main)
        explorer_main_layout.setContentsMargins(4, 4, 4, 4)
        explorer_main_layout.setSpacing(4)
        self._slide_list = QListWidget(explorer_main)
        self._slide_list.setObjectName("slideList")
        self._slide_list.setSpacing(6)
        self._slide_list.setStyleSheet("QListWidget { background: transparent; border: none; }")
        explorer_main_layout.addWidget(self._slide_list)
        explorer_main_scroll.setWidget(explorer_main)
        self._slide_list.currentItemChanged.connect(
            lambda current, _prev: self._on_slide_selected(current)
        )
        self._populate_slide_list()

        explorer_layout.addWidget(explorer_header)
        explorer_layout.addWidget(explorer_main_scroll, 1)
        explorer_layout.addWidget(explorer_footer)
        explorer_footer_layout = QHBoxLayout(explorer_footer)
        explorer_footer_layout.setContentsMargins(8, 4, 8, 4)
        explorer_footer_layout.setSpacing(8)
        explorer_footer_layout.addStretch(1)
        self._crud_button_map = self._build_buttons(
            explorer_footer,
            explorer_footer_layout,
            EXPLORER_CRUD_SPECS,
            size=SYMBOL_BUTTON_SIZE,
            registry=self._crud_buttons,
        )

        detail_container = QWidget(splitter)
        detail_container.setObjectName("detailView")
        self._detail_container = detail_container
        detail_container.setMinimumWidth(282)
        detail_layout = QVBoxLayout(detail_container)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.setSpacing(0)

        detail_header = QFrame(detail_container)
        detail_header.setObjectName("detailHeaderView")
        detail_header.setFixedHeight(DETAIL_HEADER_HEIGHT)
        self._header_views.append(detail_header)
        detail_header_layout = QHBoxLayout(detail_header)
        detail_header_layout.setContentsMargins(12, 6, 12, 6)
        detail_header_layout.setSpacing(8)

        self._detail_title_input = QLineEdit("Titel", detail_header)
        self._detail_title_input.setPlaceholderText("Titel")
        self._detail_title_input.setFixedHeight(SYMBOL_BUTTON_SIZE)
        self._detail_title_input.setObjectName("DetailTitleInput")
        self._detail_title_input.setToolTip("DetailTitleInput")
        self._detail_subtitle_input = QLineEdit("Untertitel", detail_header)
        self._detail_subtitle_input.setPlaceholderText("Untertitel")
        self._detail_subtitle_input.setFixedHeight(SYMBOL_BUTTON_SIZE)
        self._detail_subtitle_input.setObjectName("DetailSubtitleInput")
        self._detail_subtitle_input.setToolTip("DetailSubtitleInput")
        self._detail_group_combo = QComboBox(detail_header)
        self._detail_group_combo.setEditable(True)
        self._detail_group_combo.setFixedHeight(SYMBOL_BUTTON_SIZE)
        self._detail_group_combo.setObjectName("DetailGroupCombo")
        self._detail_group_combo.setToolTip("DetailGroupCombo")
        for item in sorted({layout.group for layout in LAYOUT_ITEMS}):
            self._detail_group_combo.addItem(item)

        detail_header_layout.addWidget(self._detail_title_input, 1)
        detail_header_layout.addWidget(self._detail_subtitle_input, 1)
        detail_header_layout.addWidget(self._detail_group_combo, 1)

        if self._detail_title_input:
            self._detail_title_input.textChanged.connect(lambda _text: self._save_detail_changes())
        if self._detail_subtitle_input:
            self._detail_subtitle_input.textChanged.connect(lambda _text: self._save_detail_changes())
        if self._detail_group_combo:
            self._detail_group_combo.editTextChanged.connect(lambda _text: self._save_detail_changes())

        detail_footer = QFrame(detail_container)
        detail_footer.setObjectName("detailFooterView")
        detail_footer.setMinimumHeight(220)
        detail_footer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        detail_footer.setVisible(True)

        detail_main_scroll = QScrollArea(detail_container)
        detail_main_scroll.setObjectName("detailMainScroll")
        detail_main_scroll.setWidgetResizable(True)
        detail_main_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        detail_main_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        detail_main_scroll.setStyleSheet("QScrollBar { width: 0px; }")
        detail_main_scroll.setFrameShape(QFrame.Shape.NoFrame)

        detail_main = QWidget()
        detail_main.setObjectName("detailMainView")
        detail_main_layout = QVBoxLayout(detail_main)
        detail_main_layout.setContentsMargins(12, 12, 12, 12)
        detail_main_layout.setSpacing(12)

        initial_layout = self._slides[0].layout.active_layout if self._slides else "1S|100/1R|100"
        initial_images = self._slides[0].images.copy() if self._slides else {}
        self._current_layout_id = initial_layout
        self._detail_preview_canvas = LayoutPreviewCanvas(initial_layout, detail_main, accepts_drop=True)
        self._detail_preview_canvas.setObjectName("detailPreview")
        self._detail_preview_canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._detail_preview_canvas.areaDropped.connect(self._handle_preview_drop)
        detail_main_layout.addWidget(self._detail_preview_canvas, 1)
        if initial_images:
            self._detail_preview_canvas.set_area_images(self._resolve_image_paths(initial_images))
        self._sync_preview_with_current_slide()

        detail_footer_layout = QVBoxLayout(detail_footer)
        detail_footer_layout.setContentsMargins(12, 8, 12, 12)
        detail_footer_layout.setSpacing(8)
        footer_label = QLabel("Layout Auswahl", detail_footer)
        footer_label.setStyleSheet("font-weight: 600; font-size: 14px; color: #dbe3ff;")
        detail_footer_layout.addWidget(footer_label)

        related_scroll = QScrollArea(detail_footer)
        related_scroll.setObjectName("relatedLayoutsScroll")
        related_scroll.setWidgetResizable(True)
        related_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        related_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        related_scroll.setStyleSheet("QScrollBar:horizontal { height: 0px; }")
        related_scroll.setFrameShape(QFrame.Shape.NoFrame)

        related_items_container = QWidget()
        related_items_container.setObjectName("relatedLayouts")
        horizontal_layout = QHBoxLayout(related_items_container)
        horizontal_layout.setContentsMargins(0, 0, 0, 0)
        horizontal_layout.setSpacing(8)
        related_scroll.setWidget(related_items_container)
        detail_footer_layout.addWidget(related_scroll)

        self._related_layout_layout = horizontal_layout
        self._populate_related_layouts()

        detail_main_scroll.setWidget(detail_main)

        detail_layout.addWidget(detail_header)
        detail_layout.addWidget(detail_main_scroll, 1)
        detail_layout.addWidget(detail_footer)

        splitter.addWidget(explorer_container)
        splitter.addWidget(detail_container)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)
        splitter.setSizes([160, max(self.width() - 160, 300)])

        viewport_layout.addWidget(symbol_view)
        viewport_layout.addWidget(splitter, 1)

        layout.addWidget(status_bar)
        layout.addWidget(viewport, 1)
        central.setLayout(layout)
        self.setCentralWidget(central)
        self._apply_surface_theme()

    def _build_status_bar(self, status_bar: QFrame) -> None:
        layout = QHBoxLayout(status_bar)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(16)

        left_container = QWidget(status_bar)
        left_layout = QHBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        artwork = QLabel(left_container)
        artwork.setObjectName("statusArtwork")
        artwork.setFixedSize(STATUS_ICON_SIZE, STATUS_ICON_SIZE)
        artwork.setStyleSheet(
            "background-color: rgba(255,255,255,0.05); border: 1px dashed rgba(255,255,255,0.2);"
        )

        title_container = QWidget(left_container)
        title_container_layout = QVBoxLayout(title_container)
        title_container_layout.setContentsMargins(4, 4, 4, 4)
        title_container_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        title = QLabel("Titel-Platzhalter", title_container)
        title.setObjectName("statusTitle")
        title.setStyleSheet("font-weight: 600;")
        title_container_layout.addWidget(title)
        left_layout.addWidget(artwork)
        left_layout.addWidget(title_container, 1)

        center_slider = QSlider(Qt.Orientation.Horizontal, status_bar)
        center_slider.setObjectName("audioSeekSlider")
        center_slider.setRange(0, 10_000)
        center_slider.setValue(0)
        center_slider.setFixedHeight(STATUS_ICON_SIZE - 8)

        right_container = QWidget(status_bar)
        right_layout = QHBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        transport_layout = QHBoxLayout()
        transport_layout.setContentsMargins(0, 0, 0, 0)
        transport_layout.setSpacing(4)
        transport_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        volume_layout = QHBoxLayout()
        volume_layout.setContentsMargins(0, 0, 0, 0)
        volume_layout.setSpacing(4)
        volume_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        def status_layout(spec: ButtonSpec) -> QHBoxLayout:
            return volume_layout if spec.name in STATUS_VOLUME_BUTTONS else transport_layout

        status_button_map = self._build_buttons(
            status_bar,
            transport_layout,
            STATUS_BUTTON_SPECS,
            size=STATUS_ICON_SIZE,
            registry=self._status_buttons,
            layout_getter=status_layout,
        )
        self._status_button_map = status_button_map
        self._volume_button_map = {
            name: btn for name, btn in status_button_map.items() if name in STATUS_VOLUME_BUTTONS
        }

        volume_slider = QSlider(Qt.Orientation.Horizontal, status_bar)
        volume_slider.setObjectName("StatusVolumeSlider")
        volume_slider.setRange(0, 100)
        volume_slider.setValue(75)
        volume_slider.setFixedWidth(120)
        volume_slider.setFixedHeight(STATUS_ICON_SIZE - 8)
        self._volume_slider = volume_slider
        volume_slider_shell = self._wrap_slider(volume_slider, status_bar)
        if (volume_shell_layout := volume_slider_shell.layout()) is not None:
            volume_shell_layout.setContentsMargins(4, 5, 4, 0)
        volume_layout.insertWidget(2, volume_slider_shell)

        self._wire_volume_buttons(self._volume_button_map)

        right_layout.addLayout(transport_layout)
        right_layout.addSpacing(16)
        right_layout.addLayout(volume_layout)

        center_slider_shell = self._wrap_slider(center_slider, status_bar)
        if (shell_layout := center_slider_shell.layout()) is not None:
            shell_layout.setContentsMargins(4, 5, 4, 0)

        layout.addWidget(left_container, 1)
        layout.addWidget(center_slider_shell, 1)
        layout.addWidget(right_container, 1)

    def _apply_surface_theme(self) -> None:
        palette = self.palette()
        window_color = palette.color(QPalette.ColorRole.Window)
        is_dark = window_color.value() < 128

        surface_color = window_color.darker(130 if is_dark else 115)

        highlight = palette.color(QPalette.ColorRole.Highlight)

        if self._status_bar is not None:
            self._tint_surface(self._status_bar, surface_color)
        if self._symbol_view is not None:
            self._tint_surface(self._symbol_view, surface_color)
        explorer_color = window_color.darker(120 if is_dark else 110)
        detail_color = window_color.darker(115 if is_dark else 108)
        if self._explorer_container is not None:
            self._tint_surface(self._explorer_container, explorer_color)
        if self._detail_container is not None:
            self._tint_surface(self._detail_container, detail_color)

        icon_base = palette.color(
            QPalette.ColorRole.BrightText if is_dark else QPalette.ColorRole.Text
        )
        base_color = icon_base.lighter(185) if is_dark else icon_base.darker(180)

        self._icon_base_color = base_color
        self._icon_accent_color = highlight

        self._style_symbol_buttons(highlight)
        self._style_status_buttons()
        border_color = palette.color(QPalette.ColorRole.Mid)
        if is_dark:
            border_color = border_color.lighter(150)
        else:
            border_color = border_color.darker(120)
        self._style_view_borders(border_color)
        self._style_explorer_controls(border_color)
        self._style_detail_inputs(border_color)
        self._update_icon_colors()

    @staticmethod
    def _tint_surface(widget: QFrame, color: QColor) -> None:
        palette = widget.palette()
        palette.setColor(QPalette.ColorRole.Window, color)
        widget.setAutoFillBackground(True)
        widget.setPalette(palette)

    def _style_symbol_buttons(self, accent_color: QColor) -> None:
        style = f"""
        QToolButton {{
            background-color: transparent;
            border: none;
            border-left: 3px solid transparent;
            padding: 0;
        }}
        QToolButton:checked {{
            border-left: 3px solid {accent_color.name()};
            background-color: transparent;
        }}
        """
        for button in self._symbol_buttons:
            button.setStyleSheet(style)

    def _style_status_buttons(self) -> None:
        style = """
        QToolButton {
            background-color: transparent;
            border: none;
            border-radius: 6px;
            padding: 4px;
        }
        """
        for button in self._status_buttons:
            button.setStyleSheet(style)

    def _style_view_borders(self, color: QColor) -> None:
        css_color = color.name(QColor.HexArgb)
        left_border = f"border-left: 1px solid {css_color};"
        explorer_css = left_border + f"border-right: 1px solid {css_color};"
        if self._explorer_container is not None:
            self._explorer_container.setStyleSheet(explorer_css)
        if self._detail_container is not None:
            self._detail_container.setStyleSheet(left_border)
        top_border = f"border-top: 1px solid {css_color};"
        for header in self._header_views:
            header.setStyleSheet(top_border)

    def _style_explorer_controls(self, border_color: QColor) -> None:
        css_color = border_color.name(QColor.HexArgb)
        if self._search_input is not None:
            self._search_input.setStyleSheet(
                f"QLineEdit {{ background: transparent; border: 1px solid {css_color};"
                "border-radius: 8px; padding: 0 10px; color: palette(text); }}"
            )
        button_style = """
        QToolButton {
            background-color: transparent;
            border: none;
            padding: 4px;
        }
        """
        if self._filter_button is not None:
            self._filter_button.setStyleSheet(button_style)
        for btn in self._crud_buttons:
            btn.setStyleSheet(button_style)

    def _style_detail_inputs(self, border_color: QColor) -> None:
        css_color = border_color.name(QColor.HexArgb)
        lineedit_style = (
            f"QLineEdit {{ background: transparent; border: 1px solid {css_color};"
            "border-radius: 8px; padding: 0 10px; color: palette(text); }}"
        )
        combo_style = (
            f"QComboBox {{ background: transparent; border: 1px solid {css_color};"
            "border-radius: 8px; padding: 0 10px; color: palette(text); }}"
            "QComboBox QAbstractItemView { background-color: palette(base); }"
        )
        if self._detail_title_input:
            self._detail_title_input.setStyleSheet(lineedit_style)
        if self._detail_subtitle_input:
            self._detail_subtitle_input.setStyleSheet(lineedit_style)
        if self._detail_group_combo:
            self._detail_group_combo.setStyleSheet(combo_style)

    def _update_icon_colors(self) -> None:
        for binding in self._icon_bindings:
            path = (
                binding.checked_icon_path
                if binding.checked_icon_path and binding.button.isChecked()
                else binding.icon_path
            )
            color = (
                self._icon_accent_color
                if binding.accent_on_checked and binding.button.isChecked()
                else self._icon_base_color
            )
            if isinstance(binding.button, IconToolButton) and binding.button.is_hovered:
                color = color.lighter(150)
            tinted = self._tinted_icon(path, color, binding.button.iconSize())
            binding.button.setIcon(tinted)
        for action, path in self._line_edit_actions:
            tinted = self._tinted_icon(
                path, self._icon_base_color, QSize(ICON_PIXMAP_SIZE, ICON_PIXMAP_SIZE)
            )
            action.setIcon(tinted)

    def _wire_volume_buttons(self, buttons: dict[str, QToolButton]) -> None:
        slider = self._volume_slider
        if slider is None:
            return

        def adjust(delta: int) -> None:
            slider.setValue(max(0, min(100, slider.value() + delta)))

        mute = buttons.get("StatusMuteButton")
        if mute is not None:
            def handle_mute(checked: bool) -> None:
                if checked:
                    self._last_volume_value = slider.value()
                    slider.setValue(0)
                else:
                    slider.setValue(self._last_volume_value)

            mute.toggled.connect(handle_mute)

        def remember_volume(value: int) -> None:
            if mute is None or not mute.isChecked():
                self._last_volume_value = value

        slider.valueChanged.connect(remember_volume)

        if vol_down := buttons.get("StatusVolumeDownButton"):
            vol_down.clicked.connect(lambda: adjust(-5))
        if vol_up := buttons.get("StatusVolumeUpButton"):
            vol_up.clicked.connect(lambda: adjust(5))

    def _populate_related_layouts(self) -> None:
        layout = self._related_layout_layout
        if layout is None:
            return
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._related_layout_cards.clear()
        for layout_item in LAYOUT_ITEMS:
            card = LayoutPreviewCard(layout_item)
            card.clicked.connect(self._on_related_layout_clicked)
            layout.addWidget(card)
            self._related_layout_cards.append(card)
        layout.addStretch(1)
        self._update_related_layout_selection()

    def _on_related_layout_clicked(self, layout_item: LayoutItem) -> None:
        slide = self._current_slide
        if slide is None:
            return
        slide.layout.active_layout = layout_item.layout
        if not slide.layout.content:
            defaults = self._default_images_for_layout(slide.layout.active_layout)
            if defaults:
                slide.layout.content = self._images_to_content(slide.layout.active_layout, defaults)
        slide.images = self._content_to_images(slide.layout.active_layout, slide.layout.content)
        self._set_current_layout(slide.layout.active_layout, slide.images)
        self._persist_slides()
        self._update_related_layout_selection()
        self._regenerate_current_slide_thumbnail()

    def _update_related_layout_selection(self) -> None:
        if not self._related_layout_cards:
            return
        active_layout = self._current_slide.layout.active_layout if self._current_slide else self._current_layout_id
        for card in self._related_layout_cards:
            card.setSelected(active_layout == card.layout_id)

    def _handle_preview_drop(self, area_id: int, source: str) -> None:
        slide = self._current_slide
        if slide is None or area_id <= 0:
            return
        source = source.strip()
        if not source:
            return
        normalized = self._normalize_media_path(source)
        if not normalized:
            return
        slot_index = max(area_id - 1, 0)
        while len(slide.layout.content) <= slot_index:
            slide.layout.content.append("")
        slide.layout.content[slot_index] = normalized
        slide.images = self._content_to_images(slide.layout.active_layout, slide.layout.content)
        self._set_current_layout(slide.layout.active_layout, slide.images)
        self._persist_slides()
        self._refresh_slide_widget(slide)
        self._regenerate_current_slide_thumbnail()

    def _save_detail_changes(self) -> None:
        slide = self._current_slide
        if slide is None:
            return
        title = self._detail_title_input.text().strip() if self._detail_title_input else slide.title
        subtitle = (
            self._detail_subtitle_input.text().strip()
            if self._detail_subtitle_input
            else slide.subtitle
        )
        group = (
            self._detail_group_combo.currentText().strip()
            if self._detail_group_combo
            else slide.group
        )
        title = title or slide.title
        subtitle = subtitle or slide.subtitle
        group = group or slide.group
        if (title, subtitle, group) == (slide.title, slide.subtitle, slide.group):
            return
        slide.title = title
        slide.subtitle = subtitle
        slide.group = group
        slide.layout.content = self._images_to_content(slide.layout.active_layout, slide.images)
        self._persist_slides()
        self._refresh_slide_widget(slide)

    def _refresh_slide_widget(self, slide: SlideData) -> None:
        if not self._slide_list:
            return
        for row in range(self._slide_list.count()):
            list_item = self._slide_list.item(row)
            item_data = list_item.data(Qt.ItemDataRole.UserRole)
            if item_data is slide:
                widget = self._slide_list.itemWidget(list_item)
                if widget is not None:
                    self._update_slide_item_widget(widget, slide)
                    list_item.setSizeHint(widget.sizeHint())
                break

    def _update_slide_item_widget(self, widget: QWidget, slide: SlideData) -> None:
        if title := widget.findChild(QLabel, "slideItemTitle"):
            title.setText(slide.title)
        if subtitle := widget.findChild(QLabel, "slideItemSubtitle"):
            subtitle.setText(slide.subtitle)
        if group := widget.findChild(QLabel, "slideItemGroup"):
            group.setText(slide.group)
        if preview := widget.findChild(QLabel, "slideItemPreview"):
            preview.setPixmap(self._build_preview_pixmap(slide))

    def _set_current_layout(self, layout_id: str, images: dict[int, str] | None = None) -> None:
        layout_id = layout_id or "1S|100/1R|100"
        self._current_layout_id = layout_id
        image_map = images.copy() if images else {}
        resolved_for_preview = self._resolve_image_paths(image_map)
        if self._presentation_window:
            self._presentation_window.set_layout_description(layout_id)
            self._presentation_window.set_area_images(image_map)
            resolved_for_preview = self._presentation_window.resolved_images()
            layout_id = self._presentation_window.current_layout
        if self._detail_preview_canvas:
            self._detail_preview_canvas.set_layout_description(layout_id)
            self._detail_preview_canvas.set_area_images(resolved_for_preview)
        self._update_related_layout_selection()

    def _sync_preview_with_current_slide(self) -> None:
        slide = self._current_slide
        if slide:
            self._set_current_layout(slide.layout.active_layout, slide.images.copy())
        else:
            self._set_current_layout(self._current_layout_id)

    def _normalize_media_path(self, source: str) -> str:
        if source.startswith("file://"):
            source = source[7:]
        path = Path(source)
        if path.is_absolute():
            try:
                return str(path.relative_to(PROJECT_ROOT))
            except ValueError:
                return str(path)
        return source

    def _resolve_image_paths(self, images: dict[int, str]) -> dict[int, str]:
        resolved: dict[int, str] = {}
        for area_id, path in images.items():
            if path:
                resolved[area_id] = resolve_media_path(path)
        return resolved

    def _regenerate_current_slide_thumbnail(self) -> None:
        slide = self._current_slide
        if slide is None:
            return
        if not self._capture_presentation_thumbnail_path(slide):
            return
        self._persist_slides()
        self._refresh_slide_widget(slide)

    def _capture_presentation_thumbnail_path(self, slide: SlideData) -> bool:
        window = self._presentation_window
        if window is None:
            return False
        widget = window.centralWidget()
        if widget is None or widget.size().isEmpty():
            return False
        app = QApplication.instance()
        if app is not None:
            app.processEvents()
        target_name = f"{_slugify(slide.title)}-{self._slides.index(slide) + 1}"
        target_path = THUMBNAIL_DIR / f"{target_name}.png"
        target_path.parent.mkdir(parents=True, exist_ok=True)
        pixmap = QPixmap(widget.size())
        widget.render(pixmap)
        scaled = pixmap.scaled(
            320,
            180,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        if not scaled.save(str(target_path), "PNG"):
            return False
        try:
            relative = target_path.relative_to(PROJECT_ROOT)
        except ValueError:
            relative = target_path
        slide.layout.thumbnail_url = str(relative)
        return True

    def _load_slides(self) -> list[SlideData]:
        if SLIDES_FILE.exists():
            try:
                payload = json.loads(SLIDES_FILE.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                payload = {}
            entries = payload.get("slides") or []
            slides = [self._slide_from_payload(entry) for entry in entries]
            if slides:
                return slides
        return self._initial_slides()

    def _slide_from_payload(self, data: dict[str, Any]) -> SlideData:
        layout_data = data.get("layout") or {}
        audio_data = data.get("audio") or {}
        notes_data = data.get("notes") or {}
        slide = SlideData(
            title=data.get("title") or "Unbenannte Folie",
            subtitle=data.get("subtitle") or "",
            group=data.get("group") or "",
            layout=SlideLayoutPayload(
                layout_data.get("active_layout") or "1S|100/1R|100",
                layout_data.get("thumbnail_url") or "",
                list(layout_data.get("content") or []),
            ),
            audio=SlideAudioPayload(
                playlist=list(audio_data.get("playlist") or []),
                effects=list(audio_data.get("effects") or []),
            ),
            notes=SlideNotesPayload(
                notebooks=list(notes_data.get("notebooks") or []),
            ),
        )
        slide.images = self._content_to_images(slide.layout.active_layout, slide.layout.content)
        if not slide.images:
            defaults = self._default_images_for_layout(slide.layout.active_layout)
            if defaults:
                slide.layout.content = self._images_to_content(slide.layout.active_layout, defaults)
                slide.images = defaults.copy()
        return slide

    def _slide_to_payload(self, slide: SlideData) -> dict[str, Any]:
        if not slide.layout.content and slide.images:
            slide.layout.content = self._images_to_content(slide.layout.active_layout, slide.images)
        content = list(slide.layout.content)
        return {
            "title": slide.title,
            "subtitle": slide.subtitle,
            "group": slide.group,
            "layout": {
                "active_layout": slide.layout.active_layout,
                "thumbnail_url": slide.layout.thumbnail_url,
                "content": content,
            },
            "audio": {
                "playlist": slide.audio.playlist,
                "effects": slide.audio.effects,
            },
            "notes": {
                "notebooks": slide.notes.notebooks,
            },
        }

    def _initial_slides(self) -> list[SlideData]:
        slides: list[SlideData] = []
        for layout in LAYOUT_ITEMS:
            slide = SlideData(
                title=layout.title,
                subtitle=layout.subtitle,
                group=layout.group,
                layout=SlideLayoutPayload(layout.layout, "", []),
                audio=SlideAudioPayload(),
                notes=SlideNotesPayload(),
                images=layout.images.copy(),
            )
            slide.layout.content = self._images_to_content(slide.layout.active_layout, slide.images)
            slides.append(slide)
        return slides

    def _persist_slides(self) -> None:
        self._ensure_data_dirs()
        payload = {"slides": [self._slide_to_payload(slide) for slide in self._slides]}
        SLIDES_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def _content_to_images(self, layout_id: str, content: list[str]) -> dict[int, str]:
        images: dict[int, str] = {}
        if not content:
            return images
        for index, path in enumerate(content):
            if path:
                images[index + 1] = path
        return images

    def _images_to_content(self, layout_id: str, images: dict[int, str]) -> list[str]:
        if not images:
            return []
        max_area = max((area_id for area_id in images.keys() if area_id > 0), default=0)
        if max_area <= 0:
            return []
        content = ["" for _ in range(max_area)]
        for area_id, path in images.items():
            if area_id <= 0 or not path:
                continue
            index = area_id - 1
            if index >= len(content):
                content.extend([""] * (index + 1 - len(content)))
            content[index] = path
        return content

    def _default_images_for_layout(self, layout_id: str) -> dict[int, str]:
        for item in LAYOUT_ITEMS:
            if item.layout == layout_id:
                return item.images.copy()
        return {}

    def _ensure_data_dirs(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)

    def _populate_slide_list(self) -> None:
        if self._slide_list is None:
            return
        self._slide_list.clear()
        for slide in self._slides:
            widget = self._create_slide_list_widget(slide)
            list_item = QListWidgetItem()
            list_item.setSizeHint(widget.sizeHint())
            list_item.setData(Qt.ItemDataRole.UserRole, slide)
            self._slide_list.addItem(list_item)
            self._slide_list.setItemWidget(list_item, widget)
        if self._slide_list.count():
            self._slide_list.setCurrentRow(0)

    def _create_slide_list_widget(self, slide: SlideData) -> QWidget:
        container = QFrame()
        container.setObjectName("slideListItem")
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(8, 8, 8, 8)
        container_layout.setSpacing(12)

        preview_label = QLabel(container)
        preview_label.setObjectName("slideItemPreview")
        preview_label.setFixedSize(96, 72)
        preview_label.setPixmap(self._build_preview_pixmap(slide))
        preview_label.setScaledContents(True)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)
        title = QLabel(slide.title, container)
        title.setObjectName("slideItemTitle")
        title.setStyleSheet("font-weight: 600; font-size: 16px;")
        subtitle = QLabel(slide.subtitle, container)
        subtitle.setObjectName("slideItemSubtitle")
        subtitle.setStyleSheet("color: palette(mid);")
        group = QLabel(slide.group, container)
        group.setObjectName("slideItemGroup")
        group.setStyleSheet("font-size: 12px; color: palette(dark);")
        text_layout.addWidget(title)
        text_layout.addWidget(subtitle)
        text_layout.addWidget(group)

        container_layout.addWidget(preview_label)
        container_layout.addLayout(text_layout, 1)
        return container

    def _build_preview_pixmap(self, slide: SlideData) -> QPixmap:
        preview_path = None
        if slide.layout.thumbnail_url:
            candidate = PROJECT_ROOT / slide.layout.thumbnail_url
            preview_path = candidate if candidate.exists() else None
        if preview_path and preview_path.exists():
            pix = QPixmap(str(preview_path)).scaled(
                96, 72, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            return pix
        pix = QPixmap(96, 72)
        base = QColor(60, 60, 60)
        pix.fill(base)
        painter = QPainter(pix)
        painter.setPen(QColor(120, 120, 120))
        painter.drawRect(1, 1, 94, 70)
        painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "Preview")
        painter.end()
        return pix

    def _on_slide_selected(self, item: QListWidgetItem | None) -> None:
        slide = item.data(Qt.ItemDataRole.UserRole) if item else None
        self._current_slide = slide
        self._update_detail_header(slide)
        if slide:
            slide.images = self._content_to_images(slide.layout.active_layout, slide.layout.content)
            layout_id = slide.layout.active_layout
            images = slide.images
        else:
            layout_id = ""
            images = {}
        self._set_current_layout(layout_id, images)

    def _update_detail_header(self, slide: SlideData | None) -> None:
        title = slide.title if slide else "Titel"
        subtitle = slide.subtitle if slide else "Untertitel"
        group = slide.group if slide else "Gruppe"
        if self._detail_title_input:
            self._detail_title_input.setText(title)
        if self._detail_subtitle_input:
            self._detail_subtitle_input.setText(subtitle)
        if self._detail_group_combo and group:
            index = self._detail_group_combo.findText(group)
            if index < 0:
                self._detail_group_combo.addItem(group)
                index = self._detail_group_combo.findText(group)
            self._detail_group_combo.setCurrentIndex(index)
        if slide is None and self._detail_group_combo:
            self._detail_group_combo.setEditText(group)

    @staticmethod
    def _tinted_icon(path: Path, color: QColor, size: QSize) -> QIcon:
        icon = QIcon(str(path))
        pixmap = icon.pixmap(size)
        if pixmap.isNull():
            return icon
        painter = QPainter(pixmap)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), color)
        painter.end()
        return QIcon(pixmap)

    def _wrap_slider(self, slider: QSlider, parent: QWidget) -> QWidget:
        shell = QWidget(parent)
        shell.setFixedHeight(STATUS_ICON_SIZE)
        layout = QVBoxLayout(shell)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(slider)
        return shell

    def _create_icon_button(
        self,
        parent: QWidget,
        object_name: str,
        icon_path: Path,
        tooltip: str,
        *,
        checkable: bool = False,
        auto_exclusive: bool = False,
        accent_on_checked: bool = False,
        checked_icon_path: Path | None = None,
    ) -> QToolButton:
        button = IconToolButton(parent)
        button.setObjectName(object_name)
        button.setCheckable(checkable)
        button.setAutoExclusive(auto_exclusive and checkable)
        button.setIconSize(QSize(ICON_PIXMAP_SIZE, ICON_PIXMAP_SIZE))
        button.setToolTip(tooltip)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setAutoRaise(True)
        binding = IconBinding(
            button=button,
            icon_path=icon_path,
            accent_on_checked=accent_on_checked,
            checked_icon_path=checked_icon_path,
        )
        self._icon_bindings.append(binding)
        if checkable:
            button.toggled.connect(lambda _=False: self._update_icon_colors())
        button.hoverChanged.connect(lambda _=False: self._update_icon_colors())
        return button

    def _build_buttons(
        self,
        parent: QWidget,
        layout: QHBoxLayout | QVBoxLayout,
        specs: Iterable[ButtonSpec],
        *,
        size: int,
        registry: list[QToolButton],
        layout_getter: Callable[[ButtonSpec], QHBoxLayout | QVBoxLayout] | None = None,
    ) -> dict[str, QToolButton]:
        created: dict[str, QToolButton] = {}
        for spec in specs:
            target_layout = layout_getter(spec) if layout_getter else layout
            button = self._create_icon_button(
                parent,
                spec.name,
                spec.icon,
                spec.tooltip,
                checkable=spec.checkable,
                auto_exclusive=spec.auto_exclusive,
                accent_on_checked=spec.accent_on_checked,
                checked_icon_path=spec.checked_icon,
            )
            button.setFixedSize(size, size)
            if spec.checked_by_default:
                button.setChecked(True)
            target_layout.addWidget(button)
            registry.append(button)
            created[spec.name] = button
        return created

    def _show_presentation_window(self) -> None:
        window = self._presentation_window
        if window is None:
            window = PresentationWindow()
            window.closed.connect(self._on_presentation_closed)
            self._presentation_window = window
            self._sync_preview_with_current_slide()
        if window.isVisible():
            return
        window.show()
        if self._presentation_button is not None:
            self._presentation_button.setEnabled(False)

    def _on_presentation_closed(self) -> None:
        if self._presentation_button is not None:
            self._presentation_button.setEnabled(True)
        self._presentation_window = None


class PresentationWindow(QMainWindow):
    """Second window dedicated to rendering slides."""

    closed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SlideQuest – Presentation")
        self.setMinimumSize(1280, 720)
        self._current_layout = "1S|100/1R|100"
        self._source_images: dict[int, str] = {}
        self._resolved_images: dict[int, str] = {}
        self._canvas = LayoutPreviewCanvas(self._current_layout, self)
        self._canvas.setObjectName("presentationCanvas")
        self._canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._canvas)
        self.setCentralWidget(container)

    def set_layout_description(self, layout_description: str) -> None:
        layout_description = layout_description or "1S|100/1R|100"
        self._current_layout = layout_description
        self._canvas.set_layout_description(layout_description)

    def set_area_images(self, images: dict[int, str] | None) -> None:
        self._source_images = images.copy() if images else {}
        self._resolved_images = {}
        for area_id, path in self._source_images.items():
            if path:
                self._resolved_images[area_id] = resolve_media_path(path)
        self._canvas.set_area_images(self._resolved_images)

    @property
    def current_layout(self) -> str:
        return self._current_layout

    def current_state(self) -> tuple[str, dict[int, str]]:
        return self._current_layout, self._source_images.copy()

    def resolved_images(self) -> dict[int, str]:
        return self._resolved_images.copy()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        super().closeEvent(event)
        self.closed.emit()


def main() -> None:
    """Launch the PySide6 GUI."""
    app = QApplication.instance()
    owns_event_loop = app is None
    if owns_event_loop:
        app = QApplication(sys.argv)
    master = MasterWindow()
    presentation = PresentationWindow()
    presentation.hide()
    master._presentation_window = presentation
    presentation.closed.connect(master._on_presentation_closed)
    master._sync_preview_with_current_slide()
    master.show()
    if owns_event_loop:
        assert app is not None
        sys.exit(app.exec())
