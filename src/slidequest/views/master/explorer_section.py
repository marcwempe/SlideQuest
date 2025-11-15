from __future__ import annotations

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QFont, QPainter, QPalette, QPixmap, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from slidequest.models.layouts import LAYOUT_ITEMS, LayoutItem
from slidequest.models.slide import SlideData
from slidequest.services.storage import DATA_DIR, PROJECT_ROOT, THUMBNAIL_DIR
from slidequest.ui.constants import ACTION_ICONS
from slidequest.utils.media import normalize_media_path, resolve_media_path, slugify
from slidequest.views.master.explorer_controller import ExplorerController
from slidequest.views.widgets.layout_preview import LayoutPreviewCard
from slidequest.views.widgets.slide_item_widget import SlideListItemWidget


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
        dialog = QDialog(self)
        dialog.setWindowTitle("Neue Folie")
        form = QFormLayout(dialog)
        title_input = QLineEdit(dialog)
        subtitle_input = QLineEdit(dialog)
        group_input = QLineEdit(dialog)
        form.addRow("Titel", title_input)
        form.addRow("Untertitel", subtitle_input)
        form.addRow("Gruppe", group_input)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, dialog)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        title = title_input.text().strip() or "Neue Folie"
        subtitle = subtitle_input.text().strip()
        group = group_input.text().strip() or "All"
        self._prepare_playlist_for_slide_change()
        controller = self._get_explorer_controller()
        if controller is None:
            return
        layout_id = (
            self._current_slide.layout.active_layout
            if self._current_slide
            else (self._slides[0].layout.active_layout if self._slides else "1S|100/1R|100")
        )
        slide = controller.create_slide(layout_id, group=group)
        slide.title = title
        slide.subtitle = subtitle
        self._slides = self._viewmodel.slides
        self._current_slide = slide
        self._populate_slide_list(preserve_selection=True)
        self._sync_preview_with_current_slide()

    def _handle_delete_slide(self) -> None:
        if not self._slide_list or self._slide_list.count() <= 1:
            return
        current_row = self._slide_list.currentRow()
        if current_row < 0:
            return
        self._prepare_playlist_for_slide_change()
        controller = self._get_explorer_controller()
        if controller is None:
            return
        controller.delete_slide(current_row)
        self._slides = self._viewmodel.slides
        self._populate_slide_list()
        if current_row >= self._slide_list.count():
            current_row = self._slide_list.count() - 1
        self._slide_list.setCurrentRow(max(0, current_row))

    def _handle_edit_slide(self) -> None:
        slide = self._current_slide
        if slide is None:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Folie bearbeiten")
        form = QFormLayout(dialog)
        title_input = QLineEdit(dialog)
        title_input.setText(slide.title)
        subtitle_input = QLineEdit(dialog)
        subtitle_input.setText(slide.subtitle)
        group_input = QLineEdit(dialog)
        group_input.setText(slide.group)
        form.addRow("Titel", title_input)
        form.addRow("Untertitel", subtitle_input)
        form.addRow("Gruppe", group_input)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, dialog)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        title = title_input.text().strip() or slide.title or "Neue Folie"
        subtitle = subtitle_input.text().strip()
        group = group_input.text().strip() or slide.group or "All"
        controller = self._get_explorer_controller()
        if controller is None:
            return
        controller.update_metadata(title, subtitle, group)
        self._populate_slide_list(preserve_selection=True)

    def _on_slide_selected(self, item: QListWidgetItem | None) -> None:
        if self._slide_list is not None:
            drag_row = getattr(self._slide_list, "_drag_active_row", None)
            if drag_row is not None:
                return
        slide = item.data(Qt.ItemDataRole.UserRole) if item else None
        if slide is not None and slide is not self._current_slide:
            self._prepare_playlist_for_slide_change()
        controller = self._get_explorer_controller()
        if slide and self._slide_list and controller is not None:
            row = self._slide_list.row(item)
            slide = controller.select(row)
        elif slide and self._slide_list:
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
        self._populate_note_documents()
        self._update_slide_item_states()
        self._handle_slide_selection_completed(slide)
        sync_ai_prompt = getattr(self, "_sync_ai_prompt_editor", None)
        if callable(sync_ai_prompt):
            sync_ai_prompt()

    def _handle_slide_selection_completed(self, _slide: SlideData | None) -> None:
        return

    def _handle_slide_order_changed(self) -> None:
        list_view = self._slide_list
        if list_view is None or not self._slides:
            return
        order: list[int] = []
        for row in range(list_view.count()):
            item = list_view.item(row)
            slide = item.data(Qt.ItemDataRole.UserRole)
            if slide in self._slides:
                order.append(self._slides.index(slide))
        if len(order) != len(self._slides):
            return
        controller = self._get_explorer_controller()
        if controller is None:
            return
        controller.reorder(order)
        self._slides = self._viewmodel.slides
        self._current_slide = self._viewmodel.current_slide
        self._populate_slide_list(preserve_selection=True)
        self._sync_preview_with_current_slide()

    def _move_slide(self, slide: SlideData, offset: int) -> None:
        controller = self._get_explorer_controller()
        if controller is None or self._viewmodel is None:
            return
        if not self._slides or slide not in self._slides or offset == 0:
            return
        current_index = self._slides.index(slide)
        target_index = current_index + offset
        if not (0 <= target_index < len(self._slides)):
            return
        order = list(range(len(self._slides)))
        order[current_index], order[target_index] = order[target_index], order[current_index]
        controller.reorder(order)
        self._slides = self._viewmodel.slides
        self._current_slide = self._viewmodel.current_slide
        self._populate_slide_list(preserve_selection=True)

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
        if isinstance(widget, SlideListItemWidget):
            widget.set_slide(slide, self._build_preview_pixmap(slide))

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
        refresher = getattr(self, "_refresh_token_overlays", None)
        if callable(refresher):
            refresher()

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
        widget = None
        window = self._presentation_window
        if window is not None and window.centralWidget() is not None:
            widget = window.centralWidget()
        if (widget is None or widget.size().isEmpty()) and self._detail_preview_canvas is not None:
            widget = self._detail_preview_canvas
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

    def _populate_slide_list(self, *, preserve_selection: bool = False) -> None:
        if self._slide_list is None:
            return
        slides = getattr(self, "_filtered_slides", None)
        slide_source = slides if slides is not None else self._slides
        previous_slide = self._current_slide if preserve_selection else None
        previous_block = self._slide_list.blockSignals(True)
        self._slide_list.clear()
        for slide in slide_source:
            widget = self._create_slide_list_widget(slide)
            list_item = QListWidgetItem()
            list_item.setSizeHint(widget.sizeHint())
            list_item.setData(Qt.ItemDataRole.UserRole, slide)
            self._slide_list.addItem(list_item)
            self._slide_list.setItemWidget(list_item, widget)
        selection_target = None
        if previous_slide and previous_slide in slide_source:
            selection_target = previous_slide
        elif slide_source:
            selection_target = slide_source[0]
        self._slide_list.blockSignals(previous_block)
        if selection_target is not None and self._slide_list.count():
            for row in range(self._slide_list.count()):
                item = self._slide_list.item(row)
                if item.data(Qt.ItemDataRole.UserRole) is selection_target:
                    self._slide_list.setCurrentRow(row)
                    break
        else:
            self._slide_list.setCurrentRow(-1)
        self._refresh_slide_item_styles()
        self._update_slide_item_states()

    def _create_slide_list_widget(self, slide: SlideData) -> QWidget:
        pixmap = self._build_preview_pixmap(slide)
        widget = SlideListItemWidget(slide, pixmap, self)
        widget.moveRequested.connect(self._move_slide)
        widget.setStyleSheet(self._build_slide_item_stylesheet())
        return widget

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

    def _slide_matches_query(self, slide: SlideData, query: str) -> bool:
        query = query.lower()
        candidates = [slide.title or "", slide.subtitle or "", slide.group or ""]
        for text in candidates:
            if text and self._fuzzy_match(text.lower(), query):
                return True
        return False

    @staticmethod
    def _fuzzy_match(text: str, pattern: str) -> bool:
        if not pattern:
            return True
        it = iter(text)
        return all(char in it for char in pattern)

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
                pass
            else:
                widget.setProperty("active", is_active)
                widget.style().unpolish(widget)
                widget.style().polish(widget)
                widget.update()
            if isinstance(widget, SlideListItemWidget):
                widget.set_move_enabled(row > 0, row < self._slide_list.count() - 1)

    @staticmethod
    def _color_with_alpha(color: QColor, alpha: int) -> str:
        clone = QColor(color)
        clone.setAlpha(max(0, min(255, alpha)))
        return clone.name(QColor.HexArgb)

    def _get_explorer_controller(self) -> ExplorerController | None:
        controller = getattr(self, "_explorer_controller", None)
        if controller is not None:
            return controller
        viewmodel = getattr(self, "_viewmodel", None)
        if viewmodel is None:
            return None
        controller = ExplorerController(viewmodel)
        self._explorer_controller = controller
        return controller
