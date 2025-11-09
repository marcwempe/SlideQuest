from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QFont, QIcon, QPalette, QPainter, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSlider,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from shiboken6 import Shiboken

from slidequest.services.storage import PROJECT_ROOT
from slidequest.ui.constants import (
    ACTION_ICONS,
    ICON_PIXMAP_SIZE,
    STATUS_BAR_SIZE,
    STATUS_BUTTON_SPECS,
    STATUS_ICON_SIZE,
    STATUS_VOLUME_BUTTONS,
    SYMBOL_BUTTON_SIZE,
    SYMBOL_BUTTON_SPECS,
    ButtonSpec,
)
from slidequest.views.widgets.common import IconBinding, IconToolButton


class ThemeAndControlsMixin:
    """Provides reusable status bar construction, theming and icon helpers."""

    def _build_status_bar(self, status_bar: QFrame) -> None:
        layout = QHBoxLayout(status_bar)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(16)

        left_container = QWidget(status_bar)
        left_layout = QHBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

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
        title = QLabel("SlideQuest", title_container)
        title.setObjectName("StatusTitleLabel")
        title_font = QFont(title.font())
        title_font.setWeight(QFont.Weight.DemiBold)
        title.setFont(title_font)
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

    # ------------------------------------------------------------------ #
    # Theming
    # ------------------------------------------------------------------ #
    def _apply_surface_theme(self) -> None:
        palette = self.palette()
        window_color = palette.color(QPalette.ColorRole.Window)
        is_dark = window_color.value() < 128

        highlight = palette.color(QPalette.ColorRole.Highlight)

        darker_ratio = 135 if is_dark else 120
        darker_surface = window_color.darker(darker_ratio)
        for widget in (self._status_bar, self._symbol_view):
            if widget is not None:
                self._apply_surface_tint(widget, darker_surface)

        icon_base_role = QPalette.ColorRole.BrightText if is_dark else QPalette.ColorRole.Text
        icon_base = palette.color(icon_base_role)
        if is_dark:
            icon_base = self._boost_color_value(icon_base, 45)
        self._icon_base_color = icon_base
        accent_color = highlight
        if is_dark:
            accent_color = self._boost_color_value(accent_color, 30)
        self._icon_accent_color = accent_color

        playlist_accent = palette.color(QPalette.ColorRole.Link)
        if not playlist_accent.isValid() or playlist_accent == highlight:
            playlist_accent = palette.color(QPalette.ColorRole.AlternateBase)
        if not playlist_accent.isValid():
            playlist_accent = highlight
        if is_dark:
            playlist_accent = self._boost_color_value(playlist_accent, 30)
        self._playlist_accent_color = playlist_accent

        self._style_symbol_buttons()
        self._style_status_buttons()
        self._style_playlist_buttons()
        border_color = palette.color(QPalette.ColorRole.Mid)
        self._style_view_borders(border_color)
        self._style_explorer_controls(border_color)
        self._style_detail_inputs(border_color)
        self._update_icon_colors()

    def _style_symbol_buttons(self) -> None:
        style = """
        QToolButton {
            background-color: transparent;
            border: none;
            padding: 0;
        }
        QToolButton:hover,
        QToolButton:pressed,
        QToolButton:checked {
            background-color: transparent;
            border: none;
        }
        """
        for button in self._symbol_buttons:
            button.setStyleSheet(style)

    def _style_status_buttons(self) -> None:
        style = """
        QToolButton {
            background-color: transparent;
            border: none;
            padding: 4px;
        }
        QToolButton:hover,
        QToolButton:pressed,
        QToolButton:checked {
            background-color: transparent;
            border: none;
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
            padding: 4px;
        }
        QToolButton:hover,
        QToolButton:pressed,
        QToolButton:checked {
            background-color: transparent;
            border: none;
        }
        """
        for button in self._playlist_buttons:
            button.setStyleSheet(style)

    def _style_view_borders(self, color: QColor) -> None:
        return

    def _style_explorer_controls(self, border_color: QColor) -> None:
        return

    def _style_detail_inputs(self, border_color: QColor) -> None:
        return

    # ------------------------------------------------------------------ #
    # Icons + helpers
    # ------------------------------------------------------------------ #
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
            color = self._icon_base_color
            if button.isCheckable() and button.isChecked():
                color = self._resolve_button_accent(button)
            elif binding.accent_on_checked and button.isChecked():
                color = self._resolve_button_accent(button)
            if isinstance(button, IconToolButton) and button.is_hovered:
                color = self._boost_color_value(color, 30)
            tinted = self._tinted_icon(path, color, button.iconSize())
            button.setIcon(tinted)
        self._icon_bindings = alive_bindings
        self._refresh_playlist_icon_labels()

    def _resolve_button_accent(self, button: QToolButton) -> QColor:
        if button.objectName().startswith("Playlist") and self._playlist_accent_color is not None:
            return self._playlist_accent_color
        return self._icon_accent_color

    @staticmethod
    def _apply_surface_tint(widget: QWidget, color: QColor) -> None:
        palette = widget.palette()
        palette.setColor(QPalette.ColorRole.Window, color)
        widget.setAutoFillBackground(True)
        widget.setPalette(palette)

    @staticmethod
    def _boost_color_value(color: QColor, boost: int) -> QColor:
        hue, saturation, value, alpha = color.getHsv()
        if hue == -1:
            hue = 0
        value = max(0, min(255, value + boost))
        boosted = QColor()
        boosted.setHsv(hue, saturation, value, alpha)
        return boosted

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
        button.setStyleSheet(
            """
            QToolButton {
                background-color: transparent;
                border: none;
            }
            QToolButton:hover,
            QToolButton:pressed,
            QToolButton:checked {
                background-color: transparent;
                border: none;
            }
            """
        )
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

