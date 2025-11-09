from __future__ import annotations
from pathlib import Path
from typing import Callable, Iterable

from PySide6.QtCore import QPoint, QRect, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (
    QAction,
    QColor,
    QDoubleValidator,
    QIcon,
    QMouseEvent,
    QPalette,
    QPainter,
    QPixmap,
    QPen,
)
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
    QStackedWidget,
    QToolButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from slidequest.models.layouts import LAYOUT_ITEMS, LayoutItem
from slidequest.models.slide import PlaylistTrack, SlideData
from slidequest.services.storage import DATA_DIR, PROJECT_ROOT, THUMBNAIL_DIR, SlideStorage
from slidequest.services.audio_service import AudioService
from slidequest.ui.constants import (
    ACTION_ICONS,
    DETAIL_FOOTER_HEIGHT,
    DETAIL_HEADER_HEIGHT,
    EXPLORER_CRUD_SPECS,
    EXPLORER_FOOTER_HEIGHT,
    EXPLORER_HEADER_HEIGHT,
    ICON_PIXMAP_SIZE,
    PLAYLIST_ITEM_ICONS,
    PLAYLIST_CONTROL_SPECS,
    PLAYLIST_VOLUME_BUTTONS,
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
from slidequest.views.widgets.playlist_list import PlaylistListWidget
from shiboken6 import Shiboken


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
        self._playlist_buttons: list[QToolButton] = []
        self._playlist_button_map: dict[str, QToolButton] = {}
        self._playlist_list: PlaylistListWidget | None = None
        self._playlist_icon_labels: list[tuple[QLabel, Path]] = []
        self._playlist_play_buttons: dict[int, QToolButton] = {}
        self._playlist_seek_sliders: dict[int, QSlider] = {}
        self._playlist_current_labels: dict[int, QLabel] = {}
        self._playlist_duration_labels: dict[int, QLabel] = {}
        self._seek_active: dict[int, bool] = {}
        self._playlist_track_durations: dict[int, int] = {}
        self._header_views: list[QFrame] = []
        self._detail_container: QWidget | None = None
        self._detail_stack: QStackedWidget | None = None
        self._detail_view_widgets: dict[str, QWidget] = {}
        self._detail_mode_buttons: dict[str, QToolButton | None] = {}
        self._detail_active_mode: str | None = None
        self._line_edit_actions: list[tuple[QAction, Path]] = []
        self._search_input: QLineEdit | None = None
        self._filter_button: QToolButton | None = None
        self._crud_buttons: list[QToolButton] = []
        self._crud_button_map: dict[str, QToolButton] = {}
        self._volume_slider: QSlider | None = None
        self._playlist_footer: QFrame | None = None
        self._playlist_volume_slider: QSlider | None = None
        self._playlist_last_volume_value = 75
        self._volume_button_map: dict[str, QToolButton] = {}
        self._last_volume_value = 75
        self._icon_bindings: list[IconBinding] = []
        self._playlist_accent_color = QColor("#389BA6")
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#152126"))
        self.setPalette(palette)
        self._audio_service = AudioService()
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
        self._playlist_empty_label: QLabel | None = None
        self._current_layout_id: str = ""
        self._icon_base_color = QColor("#A7D0D9")
        self._icon_accent_color = QColor("#A7D0D9")
        self._container_color = QColor("#152126")
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
        splitter.splitterMoved.connect(self._enforce_splitter_ratio)
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

        detail_stack = QStackedWidget(detail_container)
        detail_stack.setObjectName("DetailStack")
        detail_layout.addWidget(detail_stack, 1)
        self._detail_stack = detail_stack

        layout_detail = QWidget(detail_stack)
        layout_detail.setObjectName("LayoutDetailView")
        layout_detail_layout = QVBoxLayout(layout_detail)
        layout_detail_layout.setContentsMargins(0, 0, 0, 0)
        layout_detail_layout.setSpacing(0)

        detail_header = QFrame(layout_detail)
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

        detail_footer = QFrame(layout_detail)
        detail_footer.setObjectName("DetailFooter")
        detail_footer.setMinimumHeight(220)
        detail_footer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        detail_footer.setVisible(True)

        detail_main_scroll = QScrollArea(layout_detail)
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

        layout_detail_layout.addWidget(detail_header)
        layout_detail_layout.addWidget(detail_main_scroll, 1)
        layout_detail_layout.addWidget(detail_footer)
        detail_stack.addWidget(layout_detail)
        self._detail_view_widgets["layout"] = layout_detail

        playlist_detail = self._build_playlist_detail_view(detail_stack)
        detail_stack.addWidget(playlist_detail)
        self._detail_view_widgets["audio"] = playlist_detail

        splitter.addWidget(explorer_container)
        splitter.addWidget(detail_container)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        self._apply_splitter_sizes()

        viewport_layout.addWidget(symbol_view)
        viewport_layout.addWidget(splitter, 1)

        layout.addWidget(status_bar)
        layout.addWidget(viewport, 1)
        central.setLayout(layout)
        self.setCentralWidget(central)
        self._apply_surface_theme()
        self._wire_symbol_launchers()
        self._wire_audio_service()

    def _build_status_bar(self, status_bar: QFrame) -> None:
        layout = QHBoxLayout(status_bar)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(16)

        left_container = QWidget(status_bar)
        left_layout = QHBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)
        left_container.setStyleSheet("QWidget { background-color: #293940; border-radius: 8px; }")

        title_container = QWidget(left_container)
        title_container_layout = QVBoxLayout(title_container)

        logo_label = QLabel(left_container)
        logo_label.setObjectName("StatusLogoLabel")
        logo_pix = QPixmap(str(PROJECT_ROOT / "assets" / "others" / "SlideQuestLogo_small.png"))
        logo_label.setPixmap(logo_pix)
        logo_label.setFixedSize(STATUS_ICON_SIZE, STATUS_ICON_SIZE)
        logo_label.setScaledContents(True)
        left_layout.addWidget(logo_label)

        title_container_layout.setContentsMargins(4, 4, 4, 4)
        title_container_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        title = QLabel("SideQuest", title_container)
        title.setObjectName("StatusTitleLabel")
        title.setStyleSheet("font-weight: 600; color: #6DF2F2;")
        subtitle = QLabel("Live Session", title_container)
        subtitle.setStyleSheet("font-size: 10px; color: #A7D0D9;")
        title_container_layout.addWidget(subtitle)
        title_container_layout.addWidget(title)
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
        playlist_accent = QColor(highlight)
        playlist_accent = playlist_accent.lighter(120) if is_dark else playlist_accent.darker(110)
        self._playlist_accent_color = playlist_accent

        self._style_symbol_buttons(highlight)
        self._style_status_buttons()
        self._style_playlist_buttons()
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

    def _style_playlist_buttons(self) -> None:
        if not self._playlist_buttons:
            return
        style = """
        QToolButton {
            background-color: transparent;
            border: none;
            border-radius: 6px;
            padding: 4px;
        }
        """
        for button in self._playlist_buttons:
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
        playlist_list = self._playlist_list
        if playlist_list is not None:
            playlist_list.setSpacing(6)
            playlist_list.setStyleSheet(
                """
                QListWidget { background: transparent; border: none; }
                QListWidget::item:selected {
                    background-color: rgba(167, 208, 217, 0.08);
                    border: 1px dashed rgba(167, 208, 217, 0.25);
                    border-radius: 8px;
                    color: inherit;
                }
                """
            )

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
        alive_bindings: list[IconBinding] = []
        for binding in self._icon_bindings:
            button = binding.button
            if button is None or not Shiboken.isValid(button):
                continue
            alive_bindings.append(binding)
            path = (
                binding.checked_icon_path
                if binding.checked_icon_path and button.isChecked()
                else binding.icon_path
            )
            if binding.accent_on_checked and button.isChecked():
                if button.objectName().startswith("Playlist") and self._playlist_accent_color is not None:
                    color = self._playlist_accent_color
                else:
                    color = self._icon_accent_color
            else:
                color = self._icon_base_color
            if isinstance(button, IconToolButton) and button.is_hovered:
                color = color.lighter(150)
            tinted = self._tinted_icon(path, color, button.iconSize())
            button.setIcon(tinted)
        self._icon_bindings = alive_bindings
        self._refresh_playlist_icon_labels()

    def _refresh_playlist_icon_labels(self) -> None:
        alive: list[tuple[QLabel, Path]] = []
        for label, path in self._playlist_icon_labels:
            if label is None or not Shiboken.isValid(label):
                continue
            icon = self._tinted_icon(path, self._icon_base_color, QSize(ICON_PIXMAP_SIZE, ICON_PIXMAP_SIZE))
            label.setPixmap(icon.pixmap(QSize(ICON_PIXMAP_SIZE, ICON_PIXMAP_SIZE)))
            alive.append((label, path))
        self._playlist_icon_labels = alive
        for action, path in self._line_edit_actions:
            tinted = self._tinted_icon(
                path, self._icon_base_color, QSize(ICON_PIXMAP_SIZE, ICON_PIXMAP_SIZE)
            )
            action.setIcon(tinted)

    def _on_viewmodel_changed(self) -> None:
        self._slides = self._viewmodel.slides
        self._populate_playlist_tracks()

    def attach_presentation_window(self, window: PresentationWindow) -> None:
        """Register an external presentation window instance."""
        self._presentation_window = window
        window.closed.connect(self._on_presentation_closed)
        self._sync_preview_with_current_slide()

    def _wire_symbol_launchers(self) -> None:
        layout_button = self._symbol_button_map.get("LayoutExplorerLauncher")
        audio_button = self._symbol_button_map.get("AudioExplorerLauncher")
        self._detail_mode_buttons = {
            "layout": layout_button,
            "audio": audio_button,
        }
        handlers_connected = False
        for mode, button in self._detail_mode_buttons.items():
            if button is None:
                continue
            handlers_connected = True
            button.toggled.connect(lambda checked, mode=mode: self._handle_detail_launcher_toggled(mode, checked))
        if handlers_connected:
            self._initialize_detail_view_state()

    def _initialize_detail_view_state(self) -> None:
        active_mode = self._resolve_checked_detail_mode()
        if active_mode:
            self._activate_detail_mode(active_mode)
        else:
            self._set_detail_views_visible(False)
        self._apply_splitter_sizes()

    def _wire_audio_service(self) -> None:
        service = self._audio_service
        service.track_state_changed.connect(self._handle_audio_track_state_changed)
        service.position_changed.connect(self._handle_audio_position_changed)
        service.duration_changed.connect(self._handle_audio_duration_changed)

    def _handle_detail_launcher_toggled(self, mode: str, checked: bool) -> None:
        if checked:
            self._activate_detail_mode(mode)
            return
        replacement_mode = self._resolve_checked_detail_mode(exclude=mode)
        if replacement_mode:
            self._activate_detail_mode(replacement_mode)
            return
        if self._detail_active_mode == mode:
            self._detail_active_mode = None
            self._set_detail_views_visible(False)

    def _resolve_checked_detail_mode(self, exclude: str | None = None) -> str | None:
        for mode, button in self._detail_mode_buttons.items():
            if exclude and mode == exclude:
                continue
            if button is not None and button.isChecked():
                return mode
        return None

    def _activate_detail_mode(self, mode: str) -> None:
        stack = self._detail_stack
        widget = self._detail_view_widgets.get(mode)
        if stack is None or widget is None:
            return
        stack.setCurrentWidget(widget)
        self._detail_active_mode = mode
        self._set_detail_views_visible(True)

    def _set_detail_views_visible(self, visible: bool) -> None:
        detail = self._detail_container
        splitter = self._content_splitter
        if detail is None:
            return
        if visible:
            detail.show()
            if splitter:
                if len(self._detail_last_sizes) >= 2:
                    splitter.setSizes(self._detail_last_sizes)
                else:
                    self._apply_splitter_sizes()
        else:
            if splitter:
                sizes = splitter.sizes()
                if sizes:
                    self._detail_last_sizes = sizes
                    if len(sizes) >= 2:
                        explorer_total = sizes[0] + sizes[1]
                        splitter.setSizes([explorer_total, 0])
            detail.hide()

    def _apply_splitter_sizes(self) -> None:
        splitter = self._content_splitter
        explorer = self._explorer_container
        if splitter is None or explorer is None:
            return
        total = splitter.width() or self.width()
        if total <= 0:
            return
        desired = min(max(explorer.sizeHint().width(), explorer.minimumWidth()), int(total * 0.2))
        detail_width = max(total - desired, int(total * 0.5))
        splitter.blockSignals(True)
        splitter.setSizes([desired, detail_width])
        splitter.blockSignals(False)

    def _enforce_splitter_ratio(self, _pos: int, _index: int) -> None:
        self._apply_splitter_sizes()

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

    def _wire_playlist_volume_buttons(self) -> None:
        slider = self._playlist_volume_slider
        buttons = self._playlist_button_map
        if slider is None or not buttons:
            return

        def adjust(delta: int) -> None:
            slider.setValue(max(0, min(100, slider.value() + delta)))

        mute = buttons.get("PlaylistMuteButton")
        if mute is not None:
            def handle_mute(checked: bool) -> None:
                if checked:
                    self._playlist_last_volume_value = slider.value()
                    slider.setValue(0)
                else:
                    slider.setValue(self._playlist_last_volume_value)

            mute.toggled.connect(handle_mute)

        def remember_volume(value: int) -> None:
            if mute is None or not mute.isChecked():
                self._playlist_last_volume_value = value

        slider.valueChanged.connect(remember_volume)

        if vol_down := buttons.get("PlaylistVolumeDownButton"):
            vol_down.clicked.connect(lambda: adjust(-5))
        if vol_up := buttons.get("PlaylistVolumeUpButton"):
            vol_up.clicked.connect(lambda: adjust(5))

    def _populate_playlist_tracks(self) -> None:
        list_view = self._playlist_list
        if list_view is None:
            return
        slide = self._current_slide or self._viewmodel.current_slide
        tracks = list(slide.audio.playlist) if slide and slide.audio.playlist else []
        placeholder = self._playlist_empty_label
        list_view.blockSignals(True)
        list_view.clear()
        self._playlist_icon_labels = []
        self._playlist_play_buttons.clear()
        self._playlist_seek_sliders.clear()
        self._playlist_current_labels.clear()
        self._playlist_duration_labels.clear()
        self._seek_active.clear()
        self._playlist_track_durations.clear()
        if not tracks:
            if placeholder is not None:
                placeholder.show()
        else:
            if placeholder is not None:
                placeholder.hide()
        for index, track in enumerate(tracks):
            widget = self._create_playlist_item_widget(track, index)
            item = QListWidgetItem()
            item.setSizeHint(widget.sizeHint())
            item.setData(Qt.ItemDataRole.UserRole, index)
            item.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsDragEnabled
                | Qt.ItemFlag.ItemIsDropEnabled
            )
            list_view.addItem(item)
            list_view.setItemWidget(item, widget)
        list_view.blockSignals(False)
        self._refresh_playlist_icon_labels()
        self._update_icon_colors()
        self._audio_service.set_tracks(tracks)

    def _create_playlist_item_widget(self, track: PlaylistTrack, index: int) -> QWidget:
        container = QFrame()
        container.setObjectName(f"AudioPlaylistListItem_{index}")
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(6, 6, 6, 6)
        container_layout.setSpacing(6)
        container.setStyleSheet(
            """
            QFrame {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
            }
            QToolButton, QLabel, QLineEdit {
                background-color: transparent;
                border: none;
            }
            QToolButton {
                border-radius: 4px;
                padding: 2px;
            }
            QToolButton:hover,
            QToolButton:checked {
                background-color: transparent;
                border: none;
            }
            """
        )

        drag_handle = self._create_icon_label(
            container,
            f"PlaylistItemDragHandle_{index}",
            PLAYLIST_ITEM_ICONS["drag"],
            f"PlaylistItemDragHandle_{index}",
        )
        drag_handle.setCursor(Qt.CursorShape.OpenHandCursor)
        drag_handle.setFixedSize(ICON_PIXMAP_SIZE + 4, ICON_PIXMAP_SIZE + 4)
        drag_handle.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        container_layout.addWidget(drag_handle)

        play_button = self._create_icon_button(
            container,
            f"PlaylistItemPlayButton_{index}",
            PLAYLIST_ITEM_ICONS["play"],
            f"PlaylistItemPlayButton_{index}",
            checkable=True,
            accent_on_checked=True,
            checked_icon_path=PLAYLIST_ITEM_ICONS["stop"],
        )
        container_layout.addWidget(play_button)
        play_button.toggled.connect(lambda checked, idx=index: self._handle_playlist_play_toggled(idx, checked))
        self._playlist_play_buttons[index] = play_button

        title_source = Path(track.source).name if track.source else ""
        title_text = track.title.strip() or title_source or "Unbenannter Track"
        title_label = QLabel(title_text, container)
        title_label.setObjectName(f"PlaylistItemTitleLabel_{index}")
        title_label.setToolTip(f"PlaylistItemTitleLabel_{index}")
        title_label.setMinimumWidth(140)
        container_layout.addWidget(title_label, 1)

        current_time_label = QLabel(self._format_time(track.position_seconds), container)
        current_time_label.setObjectName(f"PlaylistItemCurrentTimeLabel_{index}")
        current_time_label.setToolTip(f"PlaylistItemCurrentTimeLabel_{index}")
        current_time_label.setFixedWidth(56)
        current_time_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        container_layout.addWidget(current_time_label)
        self._playlist_current_labels[index] = current_time_label

        seek_slider = QSlider(Qt.Orientation.Horizontal, container)
        seek_slider.setObjectName(f"PlaylistItemSeekSlider_{index}")
        seek_slider.setToolTip(f"PlaylistItemSeekSlider_{index}")
        seek_slider.setRange(0, 10_000)
        seek_slider.setFixedHeight(STATUS_ICON_SIZE - 12)
        duration = max(track.duration_seconds, 0.0)
        position = max(min(track.position_seconds, duration), 0.0)
        if duration > 0:
            ratio = position / duration if duration else 0.0
            seek_slider.setValue(int(ratio * seek_slider.maximum()))
            seek_slider.setEnabled(True)
        else:
            seek_slider.setValue(0)
            seek_slider.setEnabled(False)
        seek_shell = self._wrap_slider(seek_slider, container)
        seek_shell.setObjectName(f"PlaylistItemSeekShell_{index}")
        container_layout.addWidget(seek_shell, 2)
        seek_slider.sliderPressed.connect(lambda idx=index: self._handle_seek_pressed(idx))
        seek_slider.sliderReleased.connect(lambda idx=index: self._handle_seek_released(idx))
        self._playlist_seek_sliders[index] = seek_slider

        duration_label = QLabel(self._format_time(duration), container)
        duration_label.setObjectName(f"PlaylistItemDurationLabel_{index}")
        duration_label.setToolTip(f"PlaylistItemDurationLabel_{index}")
        duration_label.setFixedWidth(56)
        duration_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        container_layout.addWidget(duration_label)
        self._playlist_duration_labels[index] = duration_label

        fade_in_icon = self._create_icon_label(
            container,
            f"PlaylistItemFadeInIcon_{index}",
            PLAYLIST_ITEM_ICONS["fade_in"],
            f"PlaylistItemFadeInIcon_{index}",
        )
        container_layout.addWidget(fade_in_icon)

        fade_in_input = QLineEdit(container)
        fade_in_input.setObjectName(f"PlaylistItemFadeInInput_{index}")
        fade_in_input.setToolTip(f"PlaylistItemFadeInInput_{index}")
        fade_in_input.setFixedWidth(46)
        fade_in_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fade_in_input.setStyleSheet("color: palette(window-text);")
        fade_in_input.setPlaceholderText("0.0")
        fade_in_validator = QDoubleValidator(0.0, 9999.0, 1, fade_in_input)
        fade_in_input.setValidator(fade_in_validator)
        if track.fade_in_seconds > 0:
            fade_in_input.setText(f"{track.fade_in_seconds:.1f}")
        container_layout.addWidget(fade_in_input)
        fade_in_input.editingFinished.connect(
            lambda idx=index, field=fade_in_input: self._handle_fade_value_changed(idx, field, "in")
        )

        fade_out_input = QLineEdit(container)
        fade_out_input.setObjectName(f"PlaylistItemFadeOutInput_{index}")
        fade_out_input.setToolTip(f"PlaylistItemFadeOutInput_{index}")
        fade_out_input.setFixedWidth(46)
        fade_out_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fade_out_input.setStyleSheet("color: palette(window-text);")
        fade_out_input.setPlaceholderText("0.0")
        fade_out_validator = QDoubleValidator(0.0, 9999.0, 1, fade_out_input)
        fade_out_input.setValidator(fade_out_validator)
        if track.fade_out_seconds > 0:
            fade_out_input.setText(f"{track.fade_out_seconds:.1f}")
        container_layout.addWidget(fade_out_input)
        fade_out_input.editingFinished.connect(
            lambda idx=index, field=fade_out_input: self._handle_fade_value_changed(idx, field, "out")
        )

        fade_out_icon = self._create_icon_label(
            container,
            f"PlaylistItemFadeOutIcon_{index}",
            PLAYLIST_ITEM_ICONS["fade_out"],
            f"PlaylistItemFadeOutIcon_{index}",
        )
        container_layout.addWidget(fade_out_icon)

        delete_button = self._create_icon_button(
            container,
            f"PlaylistItemDeleteButton_{index}",
            PLAYLIST_ITEM_ICONS["delete"],
            f"PlaylistItemDeleteButton_{index}",
        )
        container_layout.addWidget(delete_button)
        delete_button.clicked.connect(lambda _checked=False, idx=index: self._handle_playlist_item_deleted(idx))
        return container

    @staticmethod
    def _format_time(seconds: float) -> str:
        if seconds <= 0:
            return "00:00"
        minutes = int(seconds) // 60
        remainder = int(seconds) % 60
        return f"{minutes:02d}:{remainder:02d}"

    def _handle_playlist_files_dropped(self, paths: list[str]) -> None:
        if not paths:
            return
        self._viewmodel.add_playlist_tracks(paths)
        self._current_slide = self._viewmodel.current_slide
        self._populate_playlist_tracks()

    def _handle_playlist_order_changed(self) -> None:
        list_view = self._playlist_list
        if list_view is None or list_view.count() == 0:
            return
        order: list[int] = []
        for row in range(list_view.count()):
            item = list_view.item(row)
            idx = item.data(Qt.ItemDataRole.UserRole)
            if idx is None:
                return
            order.append(int(idx))
        self._viewmodel.reorder_playlist_tracks(order)
        self._current_slide = self._viewmodel.current_slide
        self._populate_playlist_tracks()

    def _handle_playlist_item_deleted(self, index: int) -> None:
        self._viewmodel.remove_playlist_track(index)
        self._current_slide = self._viewmodel.current_slide
        self._populate_playlist_tracks()

    def _handle_playlist_play_toggled(self, index: int, checked: bool) -> None:
        if checked:
            track = self._get_playlist_track(index)
            start_pos = int(track.position_seconds * 1000) if track and track.position_seconds > 0 else None
            self._audio_service.play(index, start_pos)
        else:
            self._audio_service.stop_with_fade(index)

    def _handle_seek_pressed(self, index: int) -> None:
        self._seek_active[index] = True

    def _handle_seek_released(self, index: int) -> None:
        slider = self._playlist_seek_sliders.get(index)
        duration = self._playlist_track_durations.get(index)
        self._seek_active[index] = False
        if slider is None or not duration or duration <= 0:
            return
        ratio = slider.value() / max(1, slider.maximum())
        position = int(ratio * duration)
        self._audio_service.seek(index, position)
        track = self._get_playlist_track(index)
        if track is not None:
            track.position_seconds = position / 1000
        if (label := self._playlist_current_labels.get(index)) is not None:
            label.setText(self._format_time(position / 1000))

    def _handle_audio_track_state_changed(self, index: int, playing: bool) -> None:
        if playing:
            for idx, other in self._playlist_play_buttons.items():
                if idx == index:
                    continue
                other.blockSignals(True)
                other.setChecked(False)
                other.blockSignals(False)
        button = self._playlist_play_buttons.get(index)
        if button is None:
            return
        button.blockSignals(True)
        button.setChecked(playing)
        button.blockSignals(False)
        slider = self._playlist_seek_sliders.get(index)
        if slider is not None:
            slider.setEnabled(playing or bool(self._playlist_track_durations.get(index)))

    def _handle_audio_position_changed(self, index: int, position: int) -> None:
        if self._seek_active.get(index):
            return
        slider = self._playlist_seek_sliders.get(index)
        duration = self._playlist_track_durations.get(index)
        if slider is not None and duration and duration > 0:
            self._set_slider_value(slider, position, duration)
        label = self._playlist_current_labels.get(index)
        if label is not None:
            label.setText(self._format_time(position / 1000))
        track = self._get_playlist_track(index)
        if track is not None:
            track.position_seconds = position / 1000

    def _handle_audio_duration_changed(self, index: int, duration: int) -> None:
        self._playlist_track_durations[index] = duration
        label = self._playlist_duration_labels.get(index)
        if label is not None:
            label.setText(self._format_time(duration / 1000))
        slider = self._playlist_seek_sliders.get(index)
        if slider is not None:
            slider.setEnabled(duration > 0)
        track = self._get_playlist_track(index)
        if track is not None:
            track.duration_seconds = duration / 1000

    def _set_slider_value(self, slider: QSlider, position: int, duration: int) -> None:
        maximum = max(1, slider.maximum())
        value = int(position / max(1, duration) * maximum)
        slider.blockSignals(True)
        slider.setValue(max(0, min(maximum, value)))
        slider.blockSignals(False)

    def _get_playlist_track(self, index: int) -> PlaylistTrack | None:
        slide = self._current_slide or self._viewmodel.current_slide
        if slide and 0 <= index < len(slide.audio.playlist):
            return slide.audio.playlist[index]
        return None

    def _handle_fade_value_changed(self, index: int, field: QLineEdit, kind: str) -> None:
        text = field.text().strip().replace(",", ".")
        try:
            value = max(0.0, float(text)) if text else 0.0
        except ValueError:
            value = 0.0
        track = self._get_playlist_track(index)
        if track is None:
            return
        if kind == "in":
            track.fade_in_seconds = value
        else:
            track.fade_out_seconds = value
        if value <= 0:
            field.blockSignals(True)
            field.clear()
            field.blockSignals(False)
        else:
            field.blockSignals(True)
            field.setText(f"{value:.1f}")
            field.blockSignals(False)
        slide = self._current_slide
        if slide is not None:
            self._audio_service.set_tracks(slide.audio.playlist)
            self._viewmodel.persist()

    def _build_playlist_detail_view(self, parent: QWidget | None = None) -> QWidget:
        view = QWidget(parent)
        view.setObjectName("PlaylistDetailView")
        layout = QVBoxLayout(view)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        header = QFrame(view)
        header.setObjectName("PlaylistDetailHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 8, 8, 8)
        header_layout.setSpacing(8)
        title = QLabel("Playlist-Steuerung", header)
        title.setObjectName("PlaylistDetailTitleLabel")
        title.setStyleSheet("font-weight: 600;")
        header_layout.addWidget(title)
        header_layout.addStretch(1)
        layout.addWidget(header)

        playlist_container = QFrame(view)
        playlist_container.setObjectName("AudioPlaylistView")
        playlist_container.setFrameShape(QFrame.Shape.StyledPanel)
        playlist_layout = QVBoxLayout(playlist_container)
        playlist_layout.setContentsMargins(12, 12, 12, 12)
        playlist_layout.setSpacing(8)

        playlist_title = QLabel("Playlist", playlist_container)
        playlist_title.setObjectName("AudioPlaylistTitleLabel")
        playlist_title.setStyleSheet("font-size: 14px; font-weight: 600;")
        playlist_layout.addWidget(playlist_title)

        playlist_body = QWidget(playlist_container)
        playlist_body_layout = QVBoxLayout(playlist_body)
        playlist_body_layout.setContentsMargins(0, 0, 0, 0)
        playlist_body_layout.setSpacing(4)

        playlist_placeholder = QLabel(
            "Noch keine Audiodateien in der Playlist. Ziehe Dateien hierher oder füge sie über die Toolbar hinzu.",
            playlist_body,
        )
        playlist_placeholder.setObjectName("AudioPlaylistPlaceholderLabel")
        playlist_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        playlist_placeholder.setWordWrap(True)
        playlist_placeholder.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        playlist_body_layout.addWidget(playlist_placeholder)
        self._playlist_empty_label = playlist_placeholder

        playlist_list = PlaylistListWidget(playlist_body)
        playlist_list.setObjectName("AudioPlaylistListView")
        playlist_list.setMinimumHeight(140)
        playlist_body_layout.addWidget(playlist_list, 1)
        playlist_layout.addWidget(playlist_body, 1)
        self._playlist_list = playlist_list
        playlist_list.filesDropped.connect(self._handle_playlist_files_dropped)
        playlist_list.orderChanged.connect(self._handle_playlist_order_changed)

        controls_footer = QFrame(view)
        controls_footer.setObjectName("PlaylistDetailFooter")
        controls_footer.setFrameShape(QFrame.Shape.NoFrame)
        self._playlist_footer = controls_footer
        controls_layout = QHBoxLayout(controls_footer)
        controls_layout.setContentsMargins(8, 6, 8, 6)
        controls_layout.setSpacing(12)

        transport_layout = QHBoxLayout()
        transport_layout.setContentsMargins(0, 0, 0, 0)
        transport_layout.setSpacing(4)
        transport_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        volume_layout = QHBoxLayout()
        volume_layout.setContentsMargins(0, 0, 0, 0)
        volume_layout.setSpacing(4)
        volume_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        def layout_selector(spec: ButtonSpec) -> QHBoxLayout:
            return volume_layout if spec.name in PLAYLIST_VOLUME_BUTTONS else transport_layout

        playlist_button_map = self._build_buttons(
            controls_footer,
            transport_layout,
            PLAYLIST_CONTROL_SPECS,
            size=STATUS_ICON_SIZE,
            registry=self._playlist_buttons,
            layout_getter=layout_selector,
        )
        self._playlist_button_map = playlist_button_map

        playlist_volume_slider = QSlider(Qt.Orientation.Horizontal, controls_footer)
        playlist_volume_slider.setObjectName("PlaylistVolumeSlider")
        playlist_volume_slider.setRange(0, 100)
        playlist_volume_slider.setValue(75)
        playlist_volume_slider.setFixedWidth(140)
        playlist_volume_slider.setFixedHeight(STATUS_ICON_SIZE - 8)
        self._playlist_volume_slider = playlist_volume_slider
        playlist_volume_shell = self._wrap_slider(playlist_volume_slider, controls_footer)
        if (shell_layout := playlist_volume_shell.layout()) is not None:
            shell_layout.setContentsMargins(4, 5, 4, 0)
        volume_layout.insertWidget(2, playlist_volume_shell)
        self._wire_playlist_volume_buttons()

        controls_layout.addLayout(transport_layout)
        controls_layout.addStretch(1)
        controls_layout.addLayout(volume_layout)

        layout.addWidget(playlist_container, 1)
        layout.addWidget(controls_footer)
        self._populate_playlist_tracks()
        return view

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
        self._populate_playlist_tracks()

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

    def _create_icon_label(
        self,
        parent: QWidget,
        object_name: str,
        icon_path: Path,
        tooltip: str,
    ) -> QLabel:
        label = QLabel(parent)
        label.setObjectName(object_name)
        label.setToolTip(tooltip)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setFixedSize(ICON_PIXMAP_SIZE + 4, ICON_PIXMAP_SIZE + 4)
        self._playlist_icon_labels.append((label, icon_path))
        return label

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
