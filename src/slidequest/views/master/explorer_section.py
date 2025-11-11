from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPalette, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from slidequest.models.layouts import LAYOUT_ITEMS, LayoutItem
from slidequest.models.slide import SlideData
from slidequest.services.storage import DATA_DIR, PROJECT_ROOT, THUMBNAIL_DIR
from slidequest.utils.media import normalize_media_path, resolve_media_path, slugify
from slidequest.views.widgets.layout_preview import LayoutPreviewCard


class ExplorerSectionMixin:
    """Encapsulates slide explorer population, layout handling, and preview helpers."""

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
        if slide in self._slides:
            self._viewmodel.select_slide(self._slides.index(slide))
        images = self._viewmodel.set_layout(layout_item.layout)
        self._current_slide = self._viewmodel.current_slide
        self._set_current_layout(layout_item.layout, images)
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
        normalized = normalize_media_path(source)
        if not normalized:
            return
        if slide in self._slides:
            self._viewmodel.select_slide(self._slides.index(slide))
        images = self._viewmodel.update_area(area_id, normalized)
        self._current_slide = self._viewmodel.current_slide
        self._set_current_layout(slide.layout.active_layout, images)
        self._refresh_slide_widget(slide)
        self._regenerate_current_slide_thumbnail()

    def _handle_create_slide(self) -> None:
        self._prepare_playlist_for_slide_change()
        layout_id = (
            self._current_slide.layout.active_layout
            if self._current_slide
            else (self._slides[0].layout.active_layout if self._slides else "1S|100/1R|100")
        )
        slide = self._viewmodel.create_slide(layout_id)
        self._slides = self._viewmodel.slides
        self._current_slide = slide
        self._populate_slide_list()
        self._sync_preview_with_current_slide()

    def _handle_delete_slide(self) -> None:
        if not self._slide_list or self._slide_list.count() <= 1:
            return
        current_row = self._slide_list.currentRow()
        if current_row < 0:
            return
        self._prepare_playlist_for_slide_change()
        self._viewmodel.delete_slide(current_row)
        self._slides = self._viewmodel.slides
        self._populate_slide_list()
        if current_row >= self._slide_list.count():
            current_row = self._slide_list.count() - 1
        self._slide_list.setCurrentRow(max(0, current_row))

    def _on_slide_selected(self, item: QListWidgetItem | None) -> None:
        slide = item.data(Qt.ItemDataRole.UserRole) if item else None
        if slide is not None and slide is not self._current_slide:
            self._prepare_playlist_for_slide_change()
        if slide and self._slide_list:
            row = self._slide_list.row(item)
            self._viewmodel.select_slide(row)
            slide = self._viewmodel.current_slide
        self._current_slide = slide

        if slide:
            layout_id = slide.layout.active_layout
            images = slide.images.copy()
        else:
            layout_id = ""
            images = {}
        self._set_current_layout(layout_id, images)
        self._populate_playlist_tracks()
        self._update_slide_item_states()
        self._handle_slide_selection_completed(slide)

    def _handle_slide_selection_completed(self, _slide: SlideData | None) -> None:
        return

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
        if title := widget.findChild(QLabel, "SlideItemTitle"):
            title.setText(slide.title)
        if subtitle := widget.findChild(QLabel, "SlideItemSubtitle"):
            subtitle.setText(slide.subtitle)
        if group := widget.findChild(QLabel, "SlideItemGroup"):
            group.setText(slide.group)
        if preview := widget.findChild(QLabel, "SlideItemPreview"):
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

    def _resolve_image_paths(self, images: dict[int, str]) -> dict[int, str]:
        resolved: dict[int, str] = {}
        project_service = getattr(self, "_project_service", None)
        for area_id, path in images.items():
            if path:
                if project_service is not None:
                    resolved[area_id] = str(project_service.resolve_asset_path(path))
                else:
                    resolved[area_id] = resolve_media_path(path)
        return resolved

    def _regenerate_current_slide_thumbnail(self) -> None:
        slide = self._current_slide
        if slide is None:
            return
        if not self._capture_presentation_thumbnail_path(slide):
            return
        self._viewmodel.persist()
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
        target_name = f"{slugify(slide.title)}-{self._slides.index(slide) + 1}"
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
        self._refresh_slide_item_styles()
        self._update_slide_item_states()

    def _create_slide_list_widget(self, slide: SlideData) -> QWidget:
        container = QFrame()
        container.setObjectName("SlideListViewItem")
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(8, 8, 8, 8)
        container_layout.setSpacing(12)
        container.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        container.setProperty("active", False)

        preview_label = QLabel(container)
        preview_label.setObjectName("SlideItemPreview")
        preview_label.setFixedSize(96, 72)
        preview_label.setPixmap(self._build_preview_pixmap(slide))
        preview_label.setScaledContents(True)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)
        title = QLabel(slide.title, container)
        title.setObjectName("SlideItemTitle")
        title_font = QFont(title.font())
        title_font.setPointSize(max(12, title_font.pointSize()))
        title_font.setWeight(QFont.Weight.DemiBold)
        title.setFont(title_font)
        subtitle = QLabel(slide.subtitle, container)
        subtitle.setObjectName("SlideItemSubtitle")
        group = QLabel(slide.group, container)
        group.setObjectName("SlideItemGroup")
        group_font = QFont(group.font())
        group_font.setPointSize(max(10, group_font.pointSize() - 2))
        group.setFont(group_font)
        text_layout.addWidget(title)
        text_layout.addWidget(subtitle)
        text_layout.addWidget(group)

        container_layout.addWidget(preview_label)
        container_layout.addLayout(text_layout, 1)
        container.setStyleSheet(self._build_slide_item_stylesheet())
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

    def _refresh_slide_item_styles(self) -> None:
        if not self._slide_list:
            return
        stylesheet = self._build_slide_item_stylesheet()
        for row in range(self._slide_list.count()):
            item = self._slide_list.item(row)
            widget = self._slide_list.itemWidget(item)
            if widget is None:
                continue
            widget.setStyleSheet(stylesheet)
        self._update_slide_item_states()

    def _build_slide_item_stylesheet(self) -> str:
        palette = self.palette()
        base_border = self._color_with_alpha(palette.color(QPalette.ColorRole.Mid), 90)
        hover_border = self._color_with_alpha(self._icon_accent_color, 210)
        hover_bg = self._color_with_alpha(palette.color(QPalette.ColorRole.AlternateBase), 70)
        active_bg = self._color_with_alpha(self._icon_accent_color, 80)
        active_border = self._icon_accent_color.name()
        return f"""
        QFrame#SlideListViewItem {{
            border: 1px solid {base_border};
            border-radius: 10px;
            background-color: transparent;
        }}
        QFrame#SlideListViewItem:hover {{
            border-color: {hover_border};
            background-color: {hover_bg};
        }}
        QFrame#SlideListViewItem[active="true"] {{
            border-color: {active_border};
            background-color: {active_bg};
        }}
        """

    def _update_slide_item_states(self) -> None:
        if not self._slide_list:
            return
        active_row = self._slide_list.currentRow()
        for row in range(self._slide_list.count()):
            item = self._slide_list.item(row)
            widget = self._slide_list.itemWidget(item)
            if widget is None:
                continue
            is_active = row == active_row and active_row >= 0
            if widget.property("active") == is_active:
                continue
            widget.setProperty("active", is_active)
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.update()

    @staticmethod
    def _color_with_alpha(color: QColor, alpha: int) -> str:
        clone = QColor(color)
        clone.setAlpha(max(0, min(255, alpha)))
        return clone.name(QColor.HexArgb)
