from __future__ import annotations
from pathlib import Path
from typing import Callable, Iterable

from PySide6.QtCore import QPoint, QRect, QRectF, QSize, Qt, Signal, QEvent, QTimer, QObject
from PySide6.QtGui import (
    QAction,
    QColor,
    QFont,
    QIcon,
    QMouseEvent,
    QPalette,
)
from PySide6.QtWidgets import (
    QMainWindow,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
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
from slidequest.models.slide import SlideData
from slidequest.services.storage import DATA_DIR, PROJECT_ROOT, THUMBNAIL_DIR, SlideStorage
from slidequest.services.audio_service import AudioService
from slidequest.ui.constants import (
    ACTION_ICONS,
    DETAIL_FOOTER_HEIGHT,
    DETAIL_HEADER_HEIGHT,
    EXPLORER_CRUD_SPECS,
    EXPLORER_FOOTER_HEIGHT,
    EXPLORER_HEADER_HEIGHT,
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
from slidequest.views.master.explorer_section import ExplorerSectionMixin
from slidequest.views.master.notes_section import NotesSectionMixin
from slidequest.views.master.playlist_section import PlaylistSectionMixin
from slidequest.views.master.theme_section import ThemeAndControlsMixin
from slidequest.views.presentation_window import PresentationWindow
from slidequest.views.widgets.common import IconBinding
from slidequest.views.widgets.layout_preview import LayoutPreviewCanvas, LayoutPreviewCard
from slidequest.views.widgets.playlist_list import PlaylistListWidget
from shiboken6 import Shiboken


STATUS_VOLUME_BUTTONS = {
    "StatusMuteButton",
    "StatusVolumeDownButton",
    "StatusVolumeUpButton",
}


class MasterWindow(PlaylistSectionMixin, NotesSectionMixin, ThemeAndControlsMixin, ExplorerSectionMixin, QMainWindow):
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
        self._volume_button_map: dict[str, QToolButton] = {}
        self._last_volume_value = 75
        self._icon_bindings: list[IconBinding] = []
        self._playlist_accent_color = self.palette().color(QPalette.ColorRole.Highlight)
        self._audio_service = AudioService()
        self._storage = SlideStorage()
        self._viewmodel = MasterViewModel(self._storage)
        self._viewmodel.add_listener(self._on_viewmodel_changed)
        self._slides: list[SlideData] = self._viewmodel.slides
        self._slide_list: QListWidget | None = None
        self._current_slide: SlideData | None = None
        self._detail_preview_canvas: LayoutPreviewCanvas | None = None
        self._related_layout_layout: QHBoxLayout | None = None
        self._related_layout_cards: list[LayoutPreviewCard] = []
        self._current_layout_id: str = ""
        self._icon_base_color = self.palette().color(QPalette.ColorRole.Text)
        self._icon_accent_color = self.palette().color(QPalette.ColorRole.Highlight)
        self._container_color = self.palette().color(QPalette.ColorRole.Window)
        self._content_splitter: QSplitter | None = None
        self._detail_last_sizes: list[int] = []
        self._setup_placeholder()

    def _apply_surface_theme(self) -> None:  # type: ignore[override]
        super()._apply_surface_theme()
        self._refresh_slide_item_styles()

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if obj is self._content_splitter and event.type() in {QEvent.Type.Resize, QEvent.Type.Show}:
            QTimer.singleShot(0, self._apply_splitter_sizes)
        return super().eventFilter(obj, event)


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
        self._slide_list.setFrameShape(QFrame.Shape.NoFrame)
        self._slide_list.viewport().setAutoFillBackground(False)
        self._slide_list.setStyleSheet(
            """
            QListWidget#SlideListView {
                background-color: transparent;
                border: none;
            }
            QListWidget#SlideListView::item {
                background-color: transparent;
                border: none;
            }
            """
        )
        self._slide_list.setSpacing(6)
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
        detail_header.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        detail_header.setFixedHeight(DETAIL_HEADER_HEIGHT)
        self._header_views.append(detail_header)
        detail_header_layout = QHBoxLayout(detail_header)
        detail_header_layout.setContentsMargins(12, 6, 12, 6)
        detail_header_layout.setSpacing(8)

        detail_header_layout.addStretch(1)

        detail_footer = QFrame(layout_detail)
        detail_footer.setObjectName("DetailFooter")
        detail_footer.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
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

        notes_detail = self._build_notes_detail_view(detail_stack)
        detail_stack.addWidget(notes_detail)
        self._detail_view_widgets["notes"] = notes_detail

        splitter.addWidget(explorer_container)
        splitter.addWidget(detail_container)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.installEventFilter(self)
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


    def _on_viewmodel_changed(self) -> None:
        self._slides = self._viewmodel.slides
        self._populate_playlist_tracks()
        self._populate_note_documents()

    def attach_presentation_window(self, window: PresentationWindow) -> None:
        """Register an external presentation window instance."""
        self._presentation_window = window
        window.closed.connect(self._on_presentation_closed)
        self._sync_preview_with_current_slide()

    def _wire_symbol_launchers(self) -> None:
        layout_button = self._symbol_button_map.get("LayoutExplorerLauncher")
        audio_button = self._symbol_button_map.get("AudioExplorerLauncher")
        note_button = self._symbol_button_map.get("NoteExplorerLauncher")
        self._detail_mode_buttons = {
            "layout": layout_button,
            "audio": audio_button,
            "notes": note_button,
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
        desired = max(300, min(explorer.sizeHint().width(), int(total * 0.2)))
        detail_width = max(total - desired, desired)
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


    @staticmethod
    def _format_time(seconds: float) -> str:
        if seconds <= 0:
            return "00:00"
        minutes = int(seconds) // 60
        remainder = int(seconds) % 60
        return f"{minutes:02d}:{remainder:02d}"




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
