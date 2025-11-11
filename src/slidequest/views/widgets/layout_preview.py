from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from slidequest.models.layouts import LayoutCell, LayoutItem, parse_layout_description


TOKEN_MIME_TYPE = "application/x-slidequest-token"
TOKEN_MIN_SIZE = 24.0
TOKEN_BASE_RATIO = 0.18
TOKEN_HANDLE_SIZE = 10.0


@dataclass
class CanvasTokenInstance:
    placement_id: str
    token_id: str
    pixmap: QPixmap
    position_x: float
    position_y: float
    scale: float
    rotation_deg: float = 0.0


class LayoutPreviewCanvas(QFrame):
    """Visualises a layout description and optionally accepts drops for each area."""

    areaDropped = Signal(int, str)
    tokenDropped = Signal(str, float, float)
    tokenTransformChanged = Signal(str, float, float, float)
    tokenDeleteRequested = Signal(str)

    def __init__(
        self,
        layout_description: str,
        parent: QWidget | None = None,
        accepts_drop: bool = False,
        supports_tokens: bool = False,
    ) -> None:
        super().__init__(parent)
        self._layout_description = layout_description or "1S|100/1R|100"
        self._accepts_drop = accepts_drop
        self._supports_tokens = supports_tokens
        self._cells: list[LayoutCell] = []
        self._area_rects: list[tuple[int, QRectF]] = []
        self._image_paths: dict[int, str] = {}
        self._pixmaps: dict[int, QPixmap] = {}
        self._highlight_area: int = -1
        self._padding = 8
        self._token_instances: dict[str, CanvasTokenInstance] = {}
        self._token_order: list[str] = []
        self._token_rects: dict[str, QRectF] = {}
        self._token_handles: dict[str, dict[str, QRectF]] = {}
        self._selected_token: str | None = None
        self._drag_mode: str | None = None
        self._drag_token_id: str | None = None
        self._drag_handle: str | None = None
        self._drag_start_pos = QPoint()
        self._drag_start_center = QPointF()
        self._drag_start_scale = 1.0

        self.setMinimumSize(200, 140)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        if accepts_drop or supports_tokens:
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

    def set_tokens(self, instances: list[CanvasTokenInstance] | None) -> None:
        if not self._supports_tokens:
            return
        self._token_instances = {}
        self._token_order = []
        if instances:
            for instance in instances:
                self._token_instances[instance.placement_id] = instance
                self._token_order.append(instance.placement_id)
        if self._selected_token and self._selected_token not in self._token_instances:
            self._selected_token = None
        self._token_rects.clear()
        self._token_handles.clear()
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
        bounds = self._canvas_bounds()

        pen = QPen(QColor("#000000"))
        pen.setWidthF(1.0)
        painter.setPen(pen)

        for area_id, rect in self._area_rects:
            if area_id in self._pixmaps:
                self._draw_pixmap(painter, rect, self._pixmaps[area_id])
            if area_id == self._highlight_area:
                painter.fillRect(rect, QColor(255, 255, 255, 32))
            painter.drawRect(rect)

        if self._supports_tokens and self._token_order:
            self._draw_tokens(painter, bounds)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._area_rects = self._compute_area_rects()

    def dragEnterEvent(self, event) -> None:  # type: ignore[override]
        if self._supports_tokens and self._has_token_payload(event.mimeData()):
            if self._highlight_area != -1:
                self._set_highlight_area(-1)
            event.acceptProposedAction()
            return
        if not self._accepts_drop:
            event.ignore()
            return
        if self._extract_drop_path(event.mimeData()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:  # type: ignore[override]
        if self._supports_tokens and self._has_token_payload(event.mimeData()):
            if self._highlight_area != -1:
                self._set_highlight_area(-1)
            event.acceptProposedAction()
            return
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
        if self._supports_tokens and self._has_token_payload(event.mimeData()):
            token_id = self._read_token_id(event.mimeData())
            if token_id:
                normalized = self._normalize_to_bounds(event.position().toPoint())
                event.acceptProposedAction()
                self.tokenDropped.emit(token_id, normalized.x(), normalized.y())
            else:
                event.ignore()
            return
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

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if not self._supports_tokens:
            super().mousePressEvent(event)
            return
        if event.button() not in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton):
            super().mousePressEvent(event)
            return
        token_id, handle = self._hit_test_token(event.position().toPoint())
        if event.button() == Qt.MouseButton.RightButton:
            if token_id:
                self._selected_token = token_id
                self.tokenDeleteRequested.emit(token_id)
                self.update()
            return
        if not token_id:
            self._selected_token = None
            self._drag_mode = None
            self.update()
            return
        self._selected_token = token_id
        self._drag_token_id = token_id
        self._drag_handle = handle
        self._drag_start_pos = event.position().toPoint()
        instance = self._token_instances[token_id]
        rect = self._token_rects.get(token_id, QRectF())
        self._drag_start_center = rect.center()
        self._drag_start_scale = instance.scale
        if handle:
            self._drag_mode = "resize"
        else:
            self._drag_mode = "move"
        self.update()

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        if not self._supports_tokens or not self._drag_mode or not self._drag_token_id:
            super().mouseMoveEvent(event)
            return
        if event.buttons() & Qt.MouseButton.LeftButton == 0:
            return
        instance = self._token_instances.get(self._drag_token_id)
        if instance is None:
            return
        bounds = self._canvas_bounds()
        if self._drag_mode == "move":
            self._update_token_position(instance, bounds, event)
        elif self._drag_mode == "resize" and self._drag_handle:
            self._update_token_scale(instance, bounds, event)
        self.update()

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        if not self._supports_tokens or not self._drag_mode or not self._drag_token_id:
            super().mouseReleaseEvent(event)
            return
        instance = self._token_instances.get(self._drag_token_id)
        if instance is not None:
            self.tokenTransformChanged.emit(
                instance.placement_id,
                instance.position_x,
                instance.position_y,
                instance.scale,
            )
        self._drag_mode = None
        self._drag_token_id = None
        self._drag_handle = None
        self.update()

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

    def _draw_tokens(self, painter: QPainter, bounds: QRectF) -> None:
        self._token_rects.clear()
        self._token_handles.clear()
        for token_id in self._token_order:
            instance = self._token_instances.get(token_id)
            if instance is None or instance.pixmap.isNull():
                continue
            rect = self._token_rect(instance, bounds)
            self._token_rects[token_id] = rect
            painter.save()
            center = rect.center()
            painter.translate(center)
            if instance.rotation_deg:
                painter.rotate(instance.rotation_deg)
            draw_rect = QRectF(-rect.width() / 2, -rect.height() / 2, rect.width(), rect.height())
            scaled = instance.pixmap.scaled(
                rect.size().toSize(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            painter.drawPixmap(draw_rect.topLeft(), scaled)
            painter.restore()
            if token_id == self._selected_token:
                self._draw_token_outline(painter, rect)

    def _draw_token_outline(self, painter: QPainter, rect: QRectF) -> None:
        painter.save()
        outline = QPen(QColor(255, 255, 255, 190))
        outline.setStyle(Qt.PenStyle.DashLine)
        outline.setWidth(2)
        painter.setPen(outline)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(rect)
        handle_map: dict[str, QRectF] = {}
        for name, corner in self._token_handle_points(rect).items():
            handle_rect = QRectF(
                corner.x() - TOKEN_HANDLE_SIZE / 2,
                corner.y() - TOKEN_HANDLE_SIZE / 2,
                TOKEN_HANDLE_SIZE,
                TOKEN_HANDLE_SIZE,
            )
            painter.fillRect(handle_rect, QColor(255, 255, 255, 210))
            painter.drawRect(handle_rect)
            handle_map[name] = handle_rect
        if self._drag_token_id == self._selected_token and self._drag_handle and self._drag_handle in handle_map:
            painter.fillRect(handle_map[self._drag_handle], QColor(255, 200, 120, 220))
        painter.restore()
        self._token_handles[self._selected_token] = handle_map

    def _token_rect(self, instance: CanvasTokenInstance, bounds: QRectF) -> QRectF:
        base_size = self._token_base_size(bounds)
        size = max(TOKEN_MIN_SIZE, base_size * max(instance.scale, 0.1))
        center_x = bounds.x() + instance.position_x * bounds.width()
        center_y = bounds.y() + instance.position_y * bounds.height()
        return QRectF(center_x - size / 2, center_y - size / 2, size, size)

    def _canvas_bounds(self) -> QRectF:
        return self.rect().adjusted(self._padding, self._padding, -self._padding, -self._padding)

    @staticmethod
    def _has_token_payload(mime) -> bool:
        return mime.hasFormat(TOKEN_MIME_TYPE)

    @staticmethod
    def _read_token_id(mime) -> str:
        if not mime.hasFormat(TOKEN_MIME_TYPE):
            return ""
        data = mime.data(TOKEN_MIME_TYPE)
        try:
            return bytes(data).decode("utf-8").strip()
        except Exception:
            return ""

    def _normalize_to_bounds(self, point: QPoint) -> QPointF:
        bounds = self._canvas_bounds()
        x = (point.x() - bounds.x()) / max(bounds.width(), 1.0)
        y = (point.y() - bounds.y()) / max(bounds.height(), 1.0)
        return QPointF(max(0.0, min(1.0, x)), max(0.0, min(1.0, y)))

    def _hit_test_token(self, point: QPoint) -> tuple[str | None, str | None]:
        # prioritize handles
        for token_id, handles in self._token_handles.items():
            for name, rect in handles.items():
                if rect.contains(point):
                    return token_id, name
        for token_id in reversed(self._token_order):
            rect = self._token_rects.get(token_id)
            if rect and rect.contains(point):
                return token_id, None
        return None, None

    def _update_token_position(self, instance: CanvasTokenInstance, bounds: QRectF, event) -> None:
        delta = event.position().toPoint() - self._drag_start_pos
        norm_dx = delta.x() / max(bounds.width(), 1.0)
        norm_dy = delta.y() / max(bounds.height(), 1.0)
        new_x = self._drag_start_center.x() + norm_dx * bounds.width()
        new_y = self._drag_start_center.y() + norm_dy * bounds.height()
        clamped = self._clamp_point_to_bounds(QPointF(new_x, new_y), bounds, instance.scale)
        instance.position_x = (clamped.x() - bounds.x()) / max(bounds.width(), 1.0)
        instance.position_y = (clamped.y() - bounds.y()) / max(bounds.height(), 1.0)

    def _update_token_scale(self, instance: CanvasTokenInstance, bounds: QRectF, event) -> None:
        pointer = self._clamp_point_to_bounds(event.position(), bounds, instance.scale)
        modifiers = event.modifiers()
        if self._drag_handle is None:
            return
        start_rect = self._token_rects.get(instance.placement_id, QRectF(self._drag_start_center.x(), self._drag_start_center.y(), 0, 0))
        if start_rect.isNull():
            start_rect = QRectF(
                self._drag_start_center.x() - TOKEN_MIN_SIZE / 2,
                self._drag_start_center.y() - TOKEN_MIN_SIZE / 2,
                TOKEN_MIN_SIZE,
                TOKEN_MIN_SIZE,
            )
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            center = self._drag_start_center
            half_size = max(abs(pointer.x() - center.x()), abs(pointer.y() - center.y()))
            size = max(TOKEN_MIN_SIZE, half_size * 2)
            new_center = center
        else:
            anchor = self._anchor_point(start_rect, self._drag_handle)
            width = abs(anchor.x() - pointer.x())
            height = abs(anchor.y() - pointer.y())
            size = max(TOKEN_MIN_SIZE, width if width >= height else height)
            new_center = QPointF((anchor.x() + pointer.x()) / 2, (anchor.y() + pointer.y()) / 2)
        base_size = self._token_base_size(bounds)
        scale = max(0.1, size / max(base_size, 1.0))
        if not (modifiers & Qt.KeyboardModifier.AltModifier):
            scale = max(0.5, round(scale / 0.5) * 0.5)
        clamped_center = self._clamp_point_to_bounds(new_center, bounds, scale)
        instance.scale = scale
        instance.position_x = (clamped_center.x() - bounds.x()) / max(bounds.width(), 1.0)
        instance.position_y = (clamped_center.y() - bounds.y()) / max(bounds.height(), 1.0)

    def _token_handle_points(self, rect: QRectF) -> dict[str, QPointF]:
        return {
            "top_left": rect.topLeft(),
            "top_right": rect.topRight(),
            "bottom_left": rect.bottomLeft(),
            "bottom_right": rect.bottomRight(),
        }

    @staticmethod
    def _anchor_point(rect: QRectF, handle: str) -> QPointF:
        mapping = {
            "top_left": rect.bottomRight(),
            "top_right": rect.bottomLeft(),
            "bottom_left": rect.topRight(),
            "bottom_right": rect.topLeft(),
        }
        return mapping.get(handle, rect.center())

    def _clamp_point_to_bounds(self, point: QPointF, bounds: QRectF, scale: float) -> QPointF:
        size = max(TOKEN_MIN_SIZE, self._token_base_size(bounds) * max(scale, 0.1))
        half = size / 2
        x = max(bounds.left() + half, min(bounds.right() - half, point.x()))
        y = max(bounds.top() + half, min(bounds.bottom() - half, point.y()))
        return QPointF(x, y)

    def _token_base_size(self, bounds: QRectF) -> float:
        return max(TOKEN_MIN_SIZE, min(bounds.width(), bounds.height()) * TOKEN_BASE_RATIO)

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
