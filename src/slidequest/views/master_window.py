from __future__ import annotations
from pathlib import Path
from typing import Callable, Iterable

from PySide6.QtCore import QPoint, QRect, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QAction, QColor, QIcon, QPalette, QPainter, QPixmap, QPen
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QComboBox,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QToolButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from slidequest.models.layouts import LAYOUT_ITEMS, LayoutItem
from slidequest.models.slide import SlideData
from slidequest.services.storage import DATA_DIR, PROJECT_ROOT, THUMBNAIL_DIR, SlideStorage
from slidequest.ui.constants import (
    ACTION_ICONS,
    DETAIL_FOOTER_HEIGHT,
    DETAIL_HEADER_HEIGHT,
    EXPLORER_CRUD_SPECS,
    EXPLORER_FOOTER_HEIGHT,
    EXPLORER_HEADER_HEIGHT,
    ICON_PIXMAP_SIZE,
    PRESENTATION_BUTTON_SPEC,
    STATUS_BAR_SIZE,
    STATUS_BUTTON_SPECS,
    STATUS_ICON_SIZE,
    SYMBOL_BUTTON_SIZE,
    SYMBOL_BUTTON_SPECS,
    ButtonSpec,
)
from slidequest.utils.media import normalize_media_path, resolve_media_path, slugify
from slidequest.viewmodels.master import MasterViewModel
from slidequest.views.presentation_window import PresentationWindow
from slidequest.views.widgets.common import FlowLayout, IconBinding, IconToolButton
from slidequest.views.widgets.layout_preview import LayoutPreviewCanvas, LayoutPreviewCard


STATUS_VOLUME_BUTTONS = {
    "StatusMuteButton",
    "StatusVolumeDownButton",
    "StatusVolumeUpButton",
}


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
        self._storage = SlideStorage()
        self._viewmodel = MasterViewModel(self._storage)
        self._viewmodel.add_listener(self._on_viewmodel_changed)
        self._slides: list[SlideData] = self._viewmodel.slides
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
        self._content_splitter: QSplitter | None = None
        self._detail_last_sizes: list[int] = []
        self._setup_placeholder()

    def _setup_placeholder(self) -> None:
        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        status_bar = QFrame(central)
        status_bar.setObjectName("StatusBar")
        status_bar.setFixedHeight(STATUS_BAR_SIZE)
        self._status_bar = status_bar
        self._build_status_bar(status_bar)

        viewport = QFrame(central)
        viewport.setObjectName("AppViewport")
        viewport_layout = QHBoxLayout(viewport)
        viewport_layout.setContentsMargins(0, 0, 0, 0)
        viewport_layout.setSpacing(0)

        symbol_view = QFrame(viewport)
        symbol_view.setObjectName("SymbolView")
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
        splitter.setObjectName("ContentSplitter")
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(8)
        self._content_splitter = splitter

        explorer_container = QWidget(splitter)
        explorer_container.setObjectName("ExplorerView")
        self._explorer_container = explorer_container
        explorer_container.setMinimumWidth(282)
        explorer_layout = QVBoxLayout(explorer_container)
        explorer_layout.setContentsMargins(0, 0, 0, 0)
        explorer_layout.setSpacing(0)

        explorer_header = QFrame(explorer_container)
        explorer_header.setObjectName("ExplorerHeader")
        explorer_header.setFixedHeight(EXPLORER_HEADER_HEIGHT)
        self._header_views.append(explorer_header)
        explorer_header_layout = QHBoxLayout(explorer_header)
        explorer_header_layout.setContentsMargins(8, 4, 8, 4)
        explorer_header_layout.setSpacing(8)

        search_input = QLineEdit(explorer_header)
        search_input.setObjectName("ExplorerSearchField")
        search_input.setPlaceholderText("Suche …")
        search_input.setToolTip("ExplorerSearchField")
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
        explorer_footer.setObjectName("ExplorerFooter")
        explorer_footer.setFixedHeight(EXPLORER_FOOTER_HEIGHT)

        explorer_main_scroll = QScrollArea(explorer_container)
        explorer_main_scroll.setObjectName("ExplorerMainScroll")
        explorer_main_scroll.setWidgetResizable(True)
        explorer_main_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        explorer_main_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        explorer_main_scroll.setStyleSheet("QScrollBar { width: 0px; }")
        explorer_main_scroll.setFrameShape(QFrame.Shape.NoFrame)

        explorer_main = QWidget()
        explorer_main.setObjectName("ExplorerMainView")
        explorer_main_layout = QVBoxLayout(explorer_main)
        explorer_main_layout.setContentsMargins(4, 4, 4, 4)
        explorer_main_layout.setSpacing(4)
        self._slide_list = QListWidget(explorer_main)
        self._slide_list.setObjectName("SlideListView")
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
        if create_button := self._crud_button_map.get("ExplorerCreateButton"):
            create_button.clicked.connect(self._handle_create_slide)
        if delete_button := self._crud_button_map.get("ExplorerDeleteButton"):
            delete_button.clicked.connect(self._handle_delete_slide)

        detail_container = QWidget(splitter)
        detail_container.setObjectName("DetailView")
        self._detail_container = detail_container
        detail_container.setMinimumWidth(282)
        detail_layout = QVBoxLayout(detail_container)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.setSpacing(0)

        detail_header = QFrame(detail_container)
        detail_header.setObjectName("DetailHeader")
        detail_header.setFixedHeight(DETAIL_HEADER_HEIGHT)
        self._header_views.append(detail_header)
        detail_header_layout = QHBoxLayout(detail_header)
        detail_header_layout.setContentsMargins(12, 6, 12, 6)
        detail_header_layout.setSpacing(8)

        self._detail_title_input = QLineEdit("Titel", detail_header)
        self._detail_title_input.setPlaceholderText("Titel")
        self._detail_title_input.setFixedHeight(SYMBOL_BUTTON_SIZE)
        self._detail_title_input.setObjectName("DetailTitleField")
        self._detail_title_input.setToolTip("DetailTitleField")
        self._detail_subtitle_input = QLineEdit("Untertitel", detail_header)
        self._detail_subtitle_input.setPlaceholderText("Untertitel")
        self._detail_subtitle_input.setFixedHeight(SYMBOL_BUTTON_SIZE)
        self._detail_subtitle_input.setObjectName("DetailSubtitleField")
        self._detail_subtitle_input.setToolTip("DetailSubtitleField")
        self._detail_group_combo = QComboBox(detail_header)
        self._detail_group_combo.setEditable(True)
        self._detail_group_combo.setFixedHeight(SYMBOL_BUTTON_SIZE)
        self._detail_group_combo.setObjectName("DetailGroupComboBox")
        self._detail_group_combo.setToolTip("DetailGroupComboBox")
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
        detail_footer.setObjectName("DetailFooter")
        detail_footer.setMinimumHeight(220)
        detail_footer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        detail_footer.setVisible(True)

        detail_main_scroll = QScrollArea(detail_container)
        detail_main_scroll.setObjectName("DetailMainScroll")
        detail_main_scroll.setWidgetResizable(True)
        detail_main_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        detail_main_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        detail_main_scroll.setStyleSheet("QScrollBar { width: 0px; }")
        detail_main_scroll.setFrameShape(QFrame.Shape.NoFrame)

        detail_main = QWidget()
        detail_main.setObjectName("DetailMainView")
        detail_main_layout = QVBoxLayout(detail_main)
        detail_main_layout.setContentsMargins(12, 12, 12, 12)
        detail_main_layout.setSpacing(12)

        initial_layout = self._slides[0].layout.active_layout if self._slides else "1S|100/1R|100"
        initial_images = self._slides[0].images.copy() if self._slides else {}
        self._current_layout_id = initial_layout
        self._detail_preview_canvas = LayoutPreviewCanvas(initial_layout, detail_main, accepts_drop=True)
        self._detail_preview_canvas.setObjectName("DetailPreviewCanvas")
        self._detail_preview_canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._detail_preview_canvas.areaDropped.connect(self._handle_preview_drop)
        detail_main_layout.addWidget(self._detail_preview_canvas, 1)
        if initial_images:
            self._detail_preview_canvas.set_area_images(self._resolve_image_paths(initial_images))
        self._sync_preview_with_current_slide()

        detail_footer_layout = QVBoxLayout(detail_footer)
        detail_footer_layout.setContentsMargins(12, 8, 12, 12)
        detail_footer_layout.setSpacing(8)
        related_scroll = QScrollArea(detail_footer)
        related_scroll.setObjectName("LayoutSelectorScroll")
        related_scroll.setWidgetResizable(True)
        related_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        related_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        related_scroll.setStyleSheet("QScrollBar:horizontal { height: 0px; }")
        related_scroll.setFrameShape(QFrame.Shape.NoFrame)

        related_items_container = QWidget()
        related_items_container.setObjectName("LayoutSelectorContainer")
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
        self._wire_symbol_launchers()

    def _build_status_bar(self, status_bar: QFrame) -> None:
        layout = QHBoxLayout(status_bar)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(16)

        left_container = QWidget(status_bar)
        left_layout = QHBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        artwork = QLabel(left_container)
        artwork.setObjectName("StatusArtwork")
        artwork.setFixedSize(STATUS_ICON_SIZE, STATUS_ICON_SIZE)
        artwork.setStyleSheet(
            "background-color: rgba(255,255,255,0.05); border: 1px dashed rgba(255,255,255,0.2);"
        )

        title_container = QWidget(left_container)
        title_container_layout = QVBoxLayout(title_container)
        title_container_layout.setContentsMargins(4, 4, 4, 4)
        title_container_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        title = QLabel("Titel-Platzhalter", title_container)
        title.setObjectName("StatusTitleLabel")
        title.setStyleSheet("font-weight: 600;")
        title_container_layout.addWidget(title)
        left_layout.addWidget(artwork)
        left_layout.addWidget(title_container, 1)

        center_slider = QSlider(Qt.Orientation.Horizontal, status_bar)
        center_slider.setObjectName("AudioSeekSlider")
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
        volume_slider.setObjectName("VolumeSlider")
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
        text_color = self.palette().color(QPalette.ColorRole.Text).name(QColor.HexArgb)
        if self._search_input is not None:
            self._search_input.setStyleSheet(
                f"QLineEdit {{ background: transparent; border: 1px solid {css_color};"
                f"border-radius: 8px; padding: 0 10px; color: {text_color}; }}"
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
        text_color = self.palette().color(QPalette.ColorRole.Text).name(QColor.HexArgb)
        base_color = self.palette().color(QPalette.ColorRole.Base).name(QColor.HexArgb)
        lineedit_style = (
            f"QLineEdit {{ background: transparent; border: 1px solid {css_color};"
            f"border-radius: 8px; padding: 0 10px; color: {text_color}; }}"
        )
        combo_style = (
            f"QComboBox {{ background: transparent; border: 1px solid {css_color};"
            f"border-radius: 8px; padding: 0 10px; color: {text_color}; }}"
            f"QComboBox QAbstractItemView {{ background-color: {base_color}; }}"
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

    def _on_viewmodel_changed(self) -> None:
        self._slides = self._viewmodel.slides

    def attach_presentation_window(self, window: PresentationWindow) -> None:
        """Register an external presentation window instance."""
        self._presentation_window = window
        window.closed.connect(self._on_presentation_closed)
        self._sync_preview_with_current_slide()

    def _wire_symbol_launchers(self) -> None:
        layout_button = self._symbol_button_map.get("LayoutExplorerLauncher")
        if layout_button is None:
            return
        layout_button.toggled.connect(self._handle_layout_explorer_toggled)
        self._handle_layout_explorer_toggled(layout_button.isChecked())

    def _handle_layout_explorer_toggled(self, checked: bool) -> None:
        self._set_detail_views_visible(checked)

    def _set_detail_views_visible(self, visible: bool) -> None:
        detail = self._detail_container
        splitter = self._content_splitter
        if detail is None:
            return
        if visible:
            detail.show()
            if splitter and len(self._detail_last_sizes) >= 2:
                splitter.setSizes(self._detail_last_sizes)
            elif splitter:
                sizes = splitter.sizes()
                total = sum(sizes) if sizes else self.width()
                explorer = int(total * 0.25)
                detail_size = max(total - explorer, 0)
                splitter.setSizes([explorer, detail_size])
        else:
            if splitter:
                sizes = splitter.sizes()
                if sizes:
                    self._detail_last_sizes = sizes
                    if len(sizes) >= 2:
                        explorer_total = sizes[0] + sizes[1]
                        splitter.setSizes([explorer_total, 0])
            detail.hide()

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
        layout_id = (
            self._current_slide.layout.active_layout
            if self._current_slide
            else (LAYOUT_ITEMS[0].layout if LAYOUT_ITEMS else "1S|100/1R|100")
        )
        group = (
            self._current_slide.group
            if self._current_slide
            else (LAYOUT_ITEMS[0].group if LAYOUT_ITEMS else "All")
        )
        new_slide = self._viewmodel.create_slide(layout_id, group)
        self._slides = self._viewmodel.slides
        self._populate_slide_list()
        if self._slide_list:
            self._slide_list.setCurrentRow(self._slide_list.count() - 1)

    def _handle_delete_slide(self) -> None:
        if not self._slides or not self._slide_list:
            return
        if len(self._slides) == 1:
            return
        row = self._slide_list.currentRow()
        if row < 0 or row >= len(self._slides):
            row = len(self._slides) - 1
        self._viewmodel.delete_slide(row)
        self._slides = self._viewmodel.slides
        self._populate_slide_list()
        new_index = min(row, len(self._slides) - 1)
        if self._slide_list.count():
            self._slide_list.setCurrentRow(new_index)

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
        if slide in self._slides:
            self._viewmodel.select_slide(self._slides.index(slide))
        self._viewmodel.update_metadata(title, subtitle, group)
        self._current_slide = self._viewmodel.current_slide
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

    def _create_slide_list_widget(self, slide: SlideData) -> QWidget:
        container = QFrame()
        container.setObjectName("SlideListViewItem")
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(8, 8, 8, 8)
        container_layout.setSpacing(12)

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
        title.setStyleSheet("font-weight: 600; font-size: 16px;")
        subtitle = QLabel(slide.subtitle, container)
        subtitle.setObjectName("SlideItemSubtitle")
        subtitle.setStyleSheet("color: palette(window-text);")
        group = QLabel(slide.group, container)
        group.setObjectName("SlideItemGroup")
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
        if slide and self._slide_list:
            row = self._slide_list.row(item)
            self._viewmodel.select_slide(row)
            slide = self._viewmodel.current_slide
        self._current_slide = slide
        self._update_detail_header(slide)
        if slide:
            layout_id = slide.layout.active_layout
            images = slide.images.copy()
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
            self.attach_presentation_window(window)
        if window.isVisible():
            return
        window.show()
        if self._presentation_button is not None:
            self._presentation_button.setEnabled(False)

    def _on_presentation_closed(self) -> None:
        if self._presentation_button is not None:
            self._presentation_button.setEnabled(True)
        self._presentation_window = None
