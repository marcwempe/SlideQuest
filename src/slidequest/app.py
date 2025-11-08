from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPalette, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QScrollArea,
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
SYMBOL_BUTTONS: tuple[tuple[str, Path, str], ...] = (
    (
        "LayoutExplorerLauncher",
        PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "layouts" / "columns-gap.svg",
        "Layoutübersicht öffnen",
    ),
    (
        "AudioExplorerLauncher",
        PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "audio" / "volume-up.svg",
        "Audio-Einstellungen öffnen",
    ),
    (
        "NoteExplorerLauncher",
        PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "files" / "file-earmark.svg",
        "Notizübersicht öffnen",
    ),
    (
        "FileExplorerLauncher",
        PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "files" / "folder.svg",
        "Dateiexplorer öffnen",
    ),
)

STATUS_BUTTONS: tuple[
    tuple[str, Path, str, bool, bool, bool, Path | None]
] = (
    (
        "StatusShuffleButton",
        PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "audio" / "shuffle.svg",
        "Shuffle aktivieren",
        True,
        False,
        False,
        None,
    ),
    (
        "StatusPreviousTrackButton",
        PROJECT_ROOT
        / "assets"
        / "icons"
        / "bootstrap"
        / "audio"
        / "skip-backward-fill.svg",
        "Vorheriger Titel",
        False,
        False,
        False,
        None,
    ),
    (
        "StatusPlayPauseButton",
        PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "audio" / "play-fill.svg",
        "Play/Pause",
        True,
        False,
        False,
        PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "audio" / "pause-fill.svg",
    ),
    (
        "StatusStopButton",
        PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "audio" / "stop-fill.svg",
        "Stopp",
        False,
        False,
        False,
        None,
    ),
    (
        "StatusNextTrackButton",
        PROJECT_ROOT
        / "assets"
        / "icons"
        / "bootstrap"
        / "audio"
        / "skip-forward-fill.svg",
        "Nächster Titel",
        False,
        False,
        False,
        None,
    ),
    (
        "StatusLoopButton",
        PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "audio" / "repeat.svg",
        "Loop aktivieren",
        True,
        False,
        True,
        None,
    ),
    (
        "StatusMuteButton",
        PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "audio" / "volume-mute.svg",
        "Stummschalten",
        True,
        False,
        False,
        None,
    ),
    (
        "StatusVolumeDownButton",
        PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "audio" / "volume-down.svg",
        "Leiser",
        False,
        False,
        False,
        None,
    ),
    (
        "StatusVolumeUpButton",
        PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "audio" / "volume-up.svg",
        "Lauter",
        False,
        False,
        False,
        None,
    ),
)

ACTION_ICONS = {
    "search": PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "actions" / "search.svg",
    "filter": PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "actions" / "filter.svg",
    "create": PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "actions" / "plus-square.svg",
    "edit": PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "actions" / "pencil-square.svg",
    "delete": PROJECT_ROOT / "assets" / "icons" / "bootstrap" / "actions" / "trash.svg",
}


@dataclass
class IconBinding:
    button: QToolButton
    icon_path: Path
    accent_on_checked: bool = False
    checked_icon_path: Path | None = None


class MasterWindow(QMainWindow):
    """Top-level control surface for SlideQuest."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SlideQuest – Master")
        self.setMinimumSize(960, 600)
        self._status_bar: QFrame | None = None
        self._symbol_view: QFrame | None = None
        self._explorer_container: QWidget | None = None
        self._symbol_buttons: list[QToolButton] = []
        self._status_buttons: list[QToolButton] = []
        self._header_views: list[QFrame] = []
        self._detail_container: QWidget | None = None
        self._line_edit_actions: list[tuple[QAction, Path]] = []
        self._search_input: QLineEdit | None = None
        self._filter_button: QToolButton | None = None
        self._crud_buttons: list[QToolButton] = []
        self._icon_bindings: list[IconBinding] = []
        self._icon_base_color = QColor("#ffffff")
        self._icon_accent_color = QColor("#ffffff")
        self._container_color = QColor("#222222")
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
        for name, icon_path, tooltip in SYMBOL_BUTTONS:
            button = self._create_icon_button(
                parent=symbol_view,
                object_name=name,
                icon_path=icon_path,
                tooltip=tooltip,
                checkable=True,
                auto_exclusive=True,
                accent_on_checked=False,
            )
            button.setFixedSize(SYMBOL_BUTTON_SIZE, SYMBOL_BUTTON_SIZE)
            symbol_layout.addWidget(button)
            self._symbol_buttons.append(button)
        symbol_layout.addStretch(1)

        splitter = QSplitter(Qt.Orientation.Horizontal, viewport)
        splitter.setObjectName("contentSplitter")
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(8)

        explorer_container = QWidget(splitter)
        explorer_container.setObjectName("explorerView")
        self._explorer_container = explorer_container
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
        explorer_main_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        explorer_main_scroll.setFrameShape(QFrame.Shape.NoFrame)

        explorer_main = QWidget()
        explorer_main.setObjectName("explorerMainView")
        explorer_main_scroll.setWidget(explorer_main)

        explorer_layout.addWidget(explorer_header)
        explorer_layout.addWidget(explorer_main_scroll, 1)
        explorer_layout.addWidget(explorer_footer)
        explorer_footer_layout = QHBoxLayout(explorer_footer)
        explorer_footer_layout.setContentsMargins(8, 4, 8, 4)
        explorer_footer_layout.setSpacing(8)
        explorer_footer_layout.addStretch(1)
        for name, key, tooltip in (
            ("ExplorerCreateButton", "create", "Neuen Eintrag anlegen"),
            ("ExplorerEditButton", "edit", "Auswahl bearbeiten"),
            ("ExplorerDeleteButton", "delete", "Auswahl löschen"),
        ):
            btn = self._create_icon_button(
                explorer_footer,
                name,
                ACTION_ICONS[key],
                tooltip,
            )
            btn.setFixedSize(SYMBOL_BUTTON_SIZE, SYMBOL_BUTTON_SIZE)
            self._crud_buttons.append(btn)
            explorer_footer_layout.addWidget(btn)

        detail_container = QWidget(splitter)
        detail_container.setObjectName("detailView")
        self._detail_container = detail_container
        detail_layout = QVBoxLayout(detail_container)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.setSpacing(0)

        detail_header = QFrame(detail_container)
        detail_header.setObjectName("detailHeaderView")
        detail_header.setFixedHeight(DETAIL_HEADER_HEIGHT)
        self._header_views.append(detail_header)

        detail_footer = QFrame(detail_container)
        detail_footer.setObjectName("detailFooterView")
        detail_footer.setFixedHeight(DETAIL_FOOTER_HEIGHT)

        detail_main_scroll = QScrollArea(detail_container)
        detail_main_scroll.setObjectName("detailMainScroll")
        detail_main_scroll.setWidgetResizable(True)
        detail_main_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        detail_main_scroll.setFrameShape(QFrame.Shape.NoFrame)

        detail_main = QWidget()
        detail_main.setObjectName("detailMainView")
        detail_main_scroll.setWidget(detail_main)

        detail_layout.addWidget(detail_header)
        detail_layout.addWidget(detail_main_scroll, 1)
        detail_layout.addWidget(detail_footer)

        splitter.addWidget(explorer_container)
        splitter.addWidget(detail_container)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)
        splitter.setSizes([256, max(self.width() - 256, 300)])

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

        for (
            name,
            icon_path,
            tooltip,
            checkable,
            auto_exclusive,
            checked_by_default,
            checked_icon_path,
        ) in STATUS_BUTTONS:
            button = self._create_icon_button(
                parent=status_bar,
                object_name=name,
                icon_path=icon_path,
                tooltip=tooltip,
                checkable=checkable,
                auto_exclusive=auto_exclusive,
                accent_on_checked=True,
                checked_icon_path=checked_icon_path,
            )
            if checked_by_default:
                button.setChecked(True)
            button.setFixedSize(STATUS_ICON_SIZE, STATUS_ICON_SIZE)
            if name in {"MuteButton", "VolumeDownButton", "VolumeUpButton"}:
                volume_layout.addWidget(button)
            else:
                transport_layout.addWidget(button)
            self._status_buttons.append(button)

        volume_slider = QSlider(Qt.Orientation.Horizontal, status_bar)
        volume_slider.setObjectName("StatusVolumeSlider")
        volume_slider.setRange(0, 100)
        volume_slider.setValue(75)
        volume_slider.setFixedWidth(120)
        volume_slider.setFixedHeight(STATUS_ICON_SIZE - 8)
        volume_slider_shell = self._wrap_slider(volume_slider, status_bar)
        if (volume_shell_layout := volume_slider_shell.layout()) is not None:
            volume_shell_layout.setContentsMargins(4, 5, 4, 0)
        volume_layout.insertWidget(2, volume_slider_shell)

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
        if self._explorer_container is not None:
            explorer_color = window_color.darker(120 if is_dark else 110)
            self._tint_surface(self._explorer_container, explorer_color)
        if self._detail_container is not None:
            detail_color = window_color.darker(115 if is_dark else 108)
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
            tinted = self._tinted_icon(path, color, binding.button.iconSize())
            binding.button.setIcon(tinted)
        for action, path in self._line_edit_actions:
            tinted = self._tinted_icon(
                path, self._icon_base_color, QSize(ICON_PIXMAP_SIZE, ICON_PIXMAP_SIZE)
            )
            action.setIcon(tinted)

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
        button = QToolButton(parent)
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
        return button


class PresentationWindow(QMainWindow):
    """Second window dedicated to rendering slides."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SlideQuest – Presentation")
        self.setMinimumSize(1280, 720)
        self._setup_placeholder()

    def _setup_placeholder(self) -> None:
        self.setCentralWidget(QWidget(self))


def main() -> None:
    """Launch the PySide6 GUI."""
    app = QApplication.instance()
    owns_event_loop = app is None
    if owns_event_loop:
        app = QApplication(sys.argv)
    master = MasterWindow()
    presentation = PresentationWindow()
    master.show()
    presentation.show()
    if owns_event_loop:
        assert app is not None
        sys.exit(app.exec())
