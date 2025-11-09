from __future__ import annotations

from PySide6.QtCore import QPoint, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from slidequest.models.layouts import LayoutCell, LayoutItem, parse_layout_description


class LayoutPreviewCanvas(QFrame):
    """Visualises a layout description and optionally accepts drops for each area."""

    areaDropped = Signal(int, str)

    def __init__(
        self,
        layout_description: str,
        parent: QWidget | None = None,
        accepts_drop: bool = False,
    ) -> None:
        super().__init__(parent)
        self._layout_description = layout_description or "1S|100/1R|100"
        self._accepts_drop = accepts_drop
        self._cells: list[LayoutCell] = []
        self._area_rects: list[tuple[int, QRectF]] = []
        self._image_paths: dict[int, str] = {}
        self._pixmaps: dict[int, QPixmap] = {}
        self._highlight_area: int = -1
        self._padding = 8

        self.setMinimumSize(200, 140)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        if accepts_drop:
            self.setAcceptDrops(True)

        self._parse_layout()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def set_layout_description(self, layout_description: str) -> None:
        layout_description = layout_description or "1S|100/1R|100"
        if layout_description == self._layout_description:
            return
        self._layout_description = layout_description
        self._parse_layout()
        self.update()

    def layout_description(self) -> str:
        return self._layout_description

    def set_area_images(self, images: dict[int, str] | None) -> None:
        self._image_paths.clear()
        self._pixmaps.clear()
        if images:
            for area_id, path in images.items():
                normalized = str(path).strip()
                if not normalized:
                    continue
                pixmap = QPixmap(normalized)
                if pixmap.isNull():
                    continue
                self._image_paths[area_id] = normalized
                self._pixmaps[area_id] = pixmap
        self.update()

    # ------------------------------------------------------------------ #
    # QWidget overrides
    # ------------------------------------------------------------------ #
    def paintEvent(self, event) -> None:  # type: ignore[override]
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), self.palette().color(self.backgroundRole()))
        self._area_rects = self._compute_area_rects()

        pen = QPen(QColor("#000000"))
        pen.setWidthF(1.0)
        painter.setPen(pen)

        for area_id, rect in self._area_rects:
            if area_id in self._pixmaps:
                self._draw_pixmap(painter, rect, self._pixmaps[area_id])
            if area_id == self._highlight_area:
                painter.fillRect(rect, QColor(255, 255, 255, 32))
            painter.drawRect(rect)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._area_rects = self._compute_area_rects()

    def dragEnterEvent(self, event) -> None:  # type: ignore[override]
        if not self._accepts_drop:
            event.ignore()
            return
        if self._extract_drop_path(event.mimeData()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:  # type: ignore[override]
        if not self._accepts_drop:
            event.ignore()
            return
        area_id = self._hit_test_area(event.position().toPoint())
        self._set_highlight_area(area_id)
        if area_id > 0:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:  # type: ignore[override]
        if self._highlight_area != -1:
            self._set_highlight_area(-1)
        event.accept()

    def dropEvent(self, event) -> None:  # type: ignore[override]
        if not self._accepts_drop:
            event.ignore()
            return
        area_id = self._hit_test_area(event.position().toPoint())
        source = self._extract_drop_path(event.mimeData())
        self._set_highlight_area(-1)
        if area_id > 0 and source:
            event.acceptProposedAction()
            self.areaDropped.emit(area_id, source)
        else:
            event.ignore()

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _parse_layout(self) -> None:
        self._cells = parse_layout_description(self._layout_description)
        self._area_rects = self._compute_area_rects()

    def _compute_area_rects(self) -> list[tuple[int, QRectF]]:
        rects: list[tuple[int, QRectF]] = []
        bounds = self.rect().adjusted(self._padding, self._padding, -self._padding, -self._padding)
        width = max(bounds.width(), 1.0)
        height = max(bounds.height(), 1.0)
        for index, cell in enumerate(self._cells):
            area_id = cell.area_id if cell.area_id > 0 else (index + 1)
            cell_rect = QRectF(
                bounds.x() + cell.x * width,
                bounds.y() + cell.y * height,
                cell.width * width,
                cell.height * height,
            )
            rects.append((area_id, cell_rect))
        return rects

    def _draw_pixmap(self, painter: QPainter, rect: QRectF, pixmap: QPixmap) -> None:
        if pixmap.isNull():
            return
        target_size = rect.size().toSize()
        if target_size.width() <= 0 or target_size.height() <= 0:
            return
        scaled = pixmap.scaled(
            target_size,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        offset_x = max((scaled.width() - rect.width()) / 2, 0)
        offset_y = max((scaled.height() - rect.height()) / 2, 0)
        source_rect = QRectF(offset_x, offset_y, rect.width(), rect.height())
        painter.drawPixmap(rect.topLeft(), scaled, source_rect)

    def _hit_test_area(self, point: QPoint) -> int:
        for area_id, rect in self._area_rects:
            if rect.contains(point):
                return area_id
        return -1

    def _set_highlight_area(self, area_id: int) -> None:
        if self._highlight_area == area_id:
            return
        self._highlight_area = area_id
        self.update()

    @staticmethod
    def _extract_drop_path(mime) -> str | None:
        if mime.hasUrls():
            for url in mime.urls():
                if url.isLocalFile():
                    return url.toLocalFile()
                if url.toString():
                    return url.toString()
        if mime.hasText():
            text = mime.text().strip()
            if text:
                return text
        return None


class LayoutPreviewCard(QFrame):
    """Compact card with preview + metadata for quick layout selection."""

    clicked = Signal(LayoutItem)

    def __init__(self, layout_item: LayoutItem, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.layout_item = layout_item
        self.layout_id = layout_item.layout
        self._selected = False

        self.setObjectName("LayoutPreviewCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        wrapper = QVBoxLayout(self)
        wrapper.setContentsMargins(12, 12, 12, 12)
        wrapper.setSpacing(8)

        self._preview = LayoutPreviewCanvas(layout_item.layout, self, accepts_drop=False)
        self._preview.setEnabled(False)
        self._preview.setFixedSize(180, 110)

        self._title = QLabel(layout_item.title, self)
        self._title.setObjectName("LayoutPreviewCardTitle")
        self._title.setWordWrap(True)

        self._subtitle = QLabel(layout_item.subtitle, self)
        self._subtitle.setObjectName("LayoutPreviewCardSubtitle")
        self._subtitle.setWordWrap(True)
        self._subtitle.setStyleSheet("color: rgba(255,255,255,0.65); font-size: 11px;")

        wrapper.addWidget(self._preview, alignment=Qt.AlignmentFlag.AlignHCenter)
        wrapper.addWidget(self._title)
        wrapper.addWidget(self._subtitle)

        self._apply_styles()

    def setSelected(self, selected: bool) -> None:
        if self._selected == selected:
            return
        self._selected = selected
        self._apply_styles()

    # ------------------------------------------------------------------ #
    # QWidget overrides
    # ------------------------------------------------------------------ #
    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.layout_item)
        super().mouseReleaseEvent(event)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _apply_styles(self) -> None:
        border = "#7fb0ff" if self._selected else "rgba(255,255,255,0.25)"
        self.setStyleSheet(
            f"QFrame#LayoutPreviewCard {{"
            f"border: 1px solid {border};"
            f"border-radius: 8px;"
            f"background-color: transparent;"
            f"}}"
        )
