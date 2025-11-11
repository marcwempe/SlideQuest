from __future__ import annotations

import tempfile
from pathlib import Path

from PySide6.QtCore import Qt, QSize, Signal, QRectF
from PySide6.QtGui import (
    QDoubleValidator,
    QDragEnterEvent,
    QDragMoveEvent,
    QDropEvent,
    QIcon,
    QImage,
    QPainter,
    QPainterPath,
    QPixmap,
    QColor,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidgetItem,
    QSlider,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from shiboken6 import Shiboken

from slidequest.models.slide import PlaylistTrack
from slidequest.ui.constants import (
    ACTION_ICONS,
    ICON_PIXMAP_SIZE,
    PLAYLIST_CONTROL_SPECS,
    PLAYLIST_ITEM_ICONS,
    PLAYLIST_VOLUME_BUTTONS,
    STATUS_ICON_SIZE,
    SYMBOL_BUTTON_SIZE,
    ButtonSpec,
)
from slidequest.views.widgets.playlist_list import PlaylistListWidget


class PlaylistSectionMixin:
    """Mix-in with playlist construction and behaviour for the master window."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
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
        self._playlist_footer: QFrame | None = None
        self._playlist_volume_slider: QSlider | None = None
        self._playlist_last_volume_value = 75
        self._playlist_empty_label: QLabel | None = None
        self._audio_context_reset_pending = False
        self._soundboard_bar: _SoundboardBar | None = None
        self._soundboard_layout: QHBoxLayout | None = None
        self._soundboard_placeholder: QLabel | None = None
        self._soundboard_buttons: list[_SoundboardButton] = []
        self._soundboard_states: dict[str, int] = {}
        self._soundboard_active_index: int | None = None
        self._soundboard_active_key: str | None = None

    # ------------------------------------------------------------------ #
    # Construction
    # ------------------------------------------------------------------ #
    def _build_playlist_detail_view(self, parent: QWidget | None = None) -> QWidget:
        view = QWidget(parent)
        view.setObjectName("PlaylistDetailView")
        layout = QVBoxLayout(view)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        header = QFrame(view)
        header.setObjectName("PlaylistDetailHeader")
        header.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 8, 8, 8)
        header_layout.setSpacing(8)
        self._build_soundboard_bar(header, header_layout)
        layout.addWidget(header)

        playlist_container = QFrame(view)
        playlist_container.setObjectName("AudioPlaylistView")
        playlist_container.setFrameShape(QFrame.Shape.StyledPanel)
        playlist_layout = QVBoxLayout(playlist_container)
        playlist_layout.setContentsMargins(12, 12, 12, 12)
        playlist_layout.setSpacing(8)

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
        self._wire_playlist_transport_buttons()

        controls_layout.addLayout(transport_layout)
        controls_layout.addStretch(1)
        controls_layout.addLayout(volume_layout)

        layout.addWidget(playlist_container, 1)
        layout.addWidget(controls_footer)
        self._populate_playlist_tracks()
        self._refresh_soundboard_buttons()
        return view

    def _build_soundboard_bar(self, parent: QWidget, layout: QHBoxLayout) -> None:
        bar = _SoundboardBar(parent)
        bar.filesDropped.connect(self._handle_soundboard_audio_dropped)
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(0, 0, 0, 0)
        bar_layout.setSpacing(6)
        placeholder = QLabel("Audio hierher ziehen, um Soundboard-Buttons zu erstellen.", bar)
        placeholder.setObjectName("SoundboardPlaceholderLabel")
        placeholder.setStyleSheet("color: rgba(255,255,255,120);")
        bar_layout.addWidget(placeholder)
        bar_layout.addStretch(1)
        layout.addWidget(bar, 1)
        self._soundboard_bar = bar
        self._soundboard_layout = bar_layout
        self._soundboard_placeholder = placeholder

    def _refresh_soundboard_buttons(self) -> None:
        layout = self._soundboard_layout
        placeholder = self._soundboard_placeholder
        if layout is None:
            return
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is None:
                continue
            if widget is placeholder:
                widget.setParent(None)
                continue
            else:
                widget.deleteLater()
        entries = self._viewmodel.soundboard_entries()
        self._soundboard_buttons = []
        if not entries:
            self._soundboard_states.clear()
            self._soundboard_active_index = None
            self._soundboard_active_key = None
            if placeholder is not None:
                layout.addWidget(placeholder)
            layout.addStretch(1)
            return
        if placeholder is not None:
            placeholder.hide()
        updated_states: dict[str, int] = {}
        for index, entry in enumerate(entries):
            key = self._soundboard_key_for_entry(entry, index)
            state = self._soundboard_states.get(key, 0)
            updated_states[key] = state
            button = _SoundboardButton(index)
            button.setToolTip(entry.get("title") or Path(entry.get("source", "")).name or f"Sample {index + 1}")
            button.clicked.connect(lambda _, idx=index: self._handle_soundboard_button_clicked(idx))
            button.imageDropped.connect(self._handle_soundboard_image_dropped)
            self._apply_soundboard_button_style(button, entry.get("image") or "", state)
            layout.addWidget(button)
            self._soundboard_buttons.append(button)
        layout.addStretch(1)
        self._soundboard_states = updated_states

    def _handle_soundboard_audio_dropped(self, files: list[str]) -> None:
        if not files:
            return
        added = False
        for raw in files:
            source = raw[7:] if raw.startswith("file://") else raw
            path = Path(source)
            if not path.exists():
                continue
            stored = self._project_service.import_file("audio", str(path))
            self._viewmodel.add_soundboard_entry(stored)
            added = True
        if added:
            self._refresh_soundboard_buttons()

    def _handle_soundboard_image_dropped(self, index: int, path: str) -> None:
        source = path[7:] if path.startswith("file://") else path
        candidate = Path(source)
        if not candidate.exists():
            return
        thumbnail = self._create_soundboard_thumbnail(candidate)
        if thumbnail is None:
            return
        try:
            stored = self._project_service.import_file("soundboard", str(thumbnail))
        finally:
            thumbnail.unlink(missing_ok=True)
        self._viewmodel.update_soundboard_image(index, stored)
        self._refresh_soundboard_buttons()

    def _create_soundboard_thumbnail(self, source: Path) -> Path | None:
        image = QImage(str(source))
        if image.isNull():
            return None
        edge = self._soundboard_image_edge()
        target_size = QSize(edge, edge)
        scaled = image.scaled(
            target_size,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        canvas = QImage(edge, edge, QImage.Format_ARGB32_Premultiplied)
        canvas.fill(Qt.GlobalColor.transparent)
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        clip_path = QPainterPath()
        clip_path.addRoundedRect(QRectF(0, 0, edge, edge), 10, 10)
        painter.setClipPath(clip_path)
        offset_x = max(0, (scaled.width() - edge) // 2)
        offset_y = max(0, (scaled.height() - edge) // 2)
        painter.drawImage(QRectF(0, 0, edge, edge), scaled, QRectF(offset_x, offset_y, edge, edge))
        painter.end()
        handle = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        temp = Path(handle.name)
        handle.close()
        if not canvas.save(str(temp), "PNG"):
            temp.unlink(missing_ok=True)
            return None
        return temp

    def _handle_soundboard_preview_finished(self) -> None:
        if self._soundboard_active_key is None:
            return
        key = self._soundboard_active_key
        state = self._soundboard_states.get(key, 0)
        if state == 2:
            return
        self._soundboard_states[key] = 0
        self._soundboard_active_key = None
        self._soundboard_active_index = None
        self._refresh_soundboard_buttons()

    def _handle_soundboard_button_clicked(self, index: int) -> None:
        entry = self._get_soundboard_entry(index)
        if entry is None:
            return
        key = self._soundboard_key_for_entry(entry, index)
        state = self._soundboard_states.get(key, 0)
        if state == 0:
            if self._soundboard_active_index is not None:
                self._reset_soundboard_state(self._soundboard_active_key)
                self._audio_service.stop_preview()
            if self._start_soundboard_play(index, key, loop=False):
                self._soundboard_states[key] = 1
        elif state == 1:
            if self._start_soundboard_play(index, key, loop=True):
                self._soundboard_states[key] = 2
        else:
            self._audio_service.stop_preview()
            self._soundboard_states[key] = 0
            self._soundboard_active_index = None
            self._soundboard_active_key = None
        self._refresh_soundboard_buttons()

    def _start_soundboard_play(self, index: int, key: str, *, loop: bool) -> bool:
        source = self._viewmodel.play_soundboard_entry(index)
        if not source:
            return False
        self._soundboard_active_index = index
        self._soundboard_active_key = key
        self._audio_service.play_preview(source, loop=loop)
        return True

    def _reset_soundboard_state(self, key: str | None) -> None:
        if key and key in self._soundboard_states:
            self._soundboard_states[key] = 0

    def _apply_soundboard_button_style(self, button: "_SoundboardButton", image_path: str, state: int) -> None:
        inner_edge = self._soundboard_image_edge()
        pixmap = self._build_soundboard_pixmap(image_path, state, inner_edge)
        button.setIcon(QIcon(pixmap) if pixmap is not None else QIcon())
        button.setIconSize(QSize(inner_edge, inner_edge))
        button.setText("")
        button.setStyleSheet(
            f"""
            QToolButton {{
                min-width: {SYMBOL_BUTTON_SIZE}px;
                min-height: {SYMBOL_BUTTON_SIZE}px;
                max-width: {SYMBOL_BUTTON_SIZE}px;
                max-height: {SYMBOL_BUTTON_SIZE}px;
                border: 1px solid rgba(255, 255, 255, 60);
                border-radius: 10px;
                padding: 1px;
                background-color: rgba(0, 0, 0, 0.40);
            }}
            """
        )

    def _build_soundboard_pixmap(self, image_path: str, state: int, edge: int) -> QPixmap | None:
        edge = max(8, edge)
        canvas = QPixmap(edge, edge)
        canvas.fill(Qt.GlobalColor.transparent)
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        clip_path = QPainterPath()
        clip_path.addRoundedRect(QRectF(0, 0, edge, edge), 10, 10)
        painter.setClipPath(clip_path)
        try:
            if image_path:
                absolute = self._project_service.resolve_asset_path(image_path)
                source = QPixmap(str(absolute))
                if not source.isNull():
                    scaled = source.scaled(
                        QSize(edge, edge),
                        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                    offset_x = max(0, (scaled.width() - edge) // 2)
                    offset_y = max(0, (scaled.height() - edge) // 2)
                    painter.drawPixmap(0, 0, scaled, offset_x, offset_y, edge, edge)
                else:
                    painter.fillRect(canvas.rect(), QColor(255, 255, 255, 20))
            else:
                painter.fillRect(canvas.rect(), QColor(255, 255, 255, 20))
            painter.setClipping(False)
            if state == 2:
                loop_pixmap = QPixmap(str(ACTION_ICONS["loop_badge"]))
                if not loop_pixmap.isNull():
                    badge_size = max(16, edge // 4)
                    badge = loop_pixmap.scaled(
                        badge_size,
                        badge_size,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                    painter.drawPixmap(edge - badge.width() - 4, 4, badge)
        finally:
            painter.end()
        return canvas

    def _get_soundboard_entry(self, index: int) -> dict[str, str] | None:
        entries = self._viewmodel.soundboard_entries()
        if 0 <= index < len(entries):
            return entries[index]
        return None

    def _soundboard_key_for_entry(self, entry: dict[str, str] | None, index: int) -> str:
        source = (entry or {}).get("source")
        return source or f"soundboard-{index}"

    def _soundboard_image_edge(self) -> int:
        return SYMBOL_BUTTON_SIZE

    # ------------------------------------------------------------------ #
    # Playlist UI + behaviour
    # ------------------------------------------------------------------ #
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

        def handle_slider_change(value: int) -> None:
            self._handle_playlist_volume_changed(value)
            if mute is None or not mute.isChecked():
                self._playlist_last_volume_value = value

        slider.valueChanged.connect(handle_slider_change)
        self._handle_playlist_volume_changed(slider.value())

        if vol_down := buttons.get("PlaylistVolumeDownButton"):
            vol_down.clicked.connect(lambda: adjust(-5))
        if vol_up := buttons.get("PlaylistVolumeUpButton"):
            vol_up.clicked.connect(lambda: adjust(5))

    def _handle_playlist_volume_changed(self, value: int) -> None:
        slider = self._playlist_volume_slider
        if slider is None:
            return
        maximum = max(1, slider.maximum())
        self._audio_service.set_master_volume(value / maximum)

    def _wire_playlist_transport_buttons(self) -> None:
        buttons = self._playlist_button_map
        if not buttons:
            return
        if prev_button := buttons.get("PlaylistPreviousTrackButton"):
            prev_button.clicked.connect(lambda: self._handle_playlist_skip(-1))
        if next_button := buttons.get("PlaylistNextTrackButton"):
            next_button.clicked.connect(lambda: self._handle_playlist_skip(1))
        if play_button := buttons.get("PlaylistPlayPauseButton"):
            play_button.toggled.connect(self._handle_footer_play_toggled)
        if stop_button := buttons.get("PlaylistStopButton"):
            stop_button.clicked.connect(self._handle_footer_stop_clicked)

    def _populate_playlist_tracks(self) -> None:
        list_view = self._playlist_list
        if list_view is None:
            return
        slide = self._current_slide or self._viewmodel.current_slide
        tracks = list(slide.audio.playlist) if slide and slide.audio.playlist else []
        playing_indices = {idx for idx, button in self._playlist_play_buttons.items() if button.isChecked()}
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
        for idx, track in enumerate(tracks):
            if idx not in playing_indices:
                track.position_seconds = 0.0
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
        new_context = self._audio_context_reset_pending
        self._audio_context_reset_pending = False
        self._audio_service.set_tracks(tracks, new_context=new_context)

    def _create_playlist_item_widget(self, track: PlaylistTrack, index: int) -> QWidget:
        container = QFrame()
        container.setObjectName(f"AudioPlaylistListItem_{index}")
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(6, 6, 6, 6)
        container_layout.setSpacing(6)
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
        self._playlist_track_durations[index] = int(duration * 1000)
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
        seek_slider.sliderMoved.connect(
            lambda value, idx=index: self._handle_seek_slider_moved(idx, value)
        )
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
        delete_button.clicked.connect(lambda _checked=False, idx=index: self._handle_playlist_item_deleted(idx))
        container_layout.addWidget(delete_button)
        return container

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
            tinted = self._tinted_icon(path, self._icon_base_color, QSize(ICON_PIXMAP_SIZE, ICON_PIXMAP_SIZE))
            action.setIcon(tinted)

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
                continue
            order.append(int(idx))
        if not order:
            return
        self._viewmodel.reorder_playlist_tracks(order)
        self._current_slide = self._viewmodel.current_slide
        self._populate_playlist_tracks()

    def _handle_playlist_item_deleted(self, index: int) -> None:
        self._viewmodel.remove_playlist_track(index)
        self._current_slide = self._viewmodel.current_slide
        self._populate_playlist_tracks()

    def _handle_playlist_play_toggled(self, index: int, checked: bool) -> None:
        self._ensure_audio_service_tracks()
        if checked:
            track = self._get_playlist_track(index)
            start_pos = int(track.position_seconds * 1000) if track and track.position_seconds > 0 else None
            self._audio_service.play(index, start_pos)
        else:
            self._audio_service.stop_with_fade(index)
        self._sync_footer_play_button()

    def _handle_footer_play_toggled(self, checked: bool) -> None:
        self._ensure_audio_service_tracks()
        if checked:
            if self._resume_paused_tracks():
                return
            if self._start_first_playlist_track():
                return
            self._set_footer_play_button_checked(False)
            return
        self._pause_playlist_tracks()

    def _handle_footer_stop_clicked(self) -> None:
        self._audio_service.stop()
        self._set_footer_play_button_checked(False)

    def _handle_playlist_skip(self, direction: int) -> None:
        if direction not in (-1, 1) or not self._playlist_play_buttons:
            return
        ordered_indices = sorted(self._playlist_play_buttons.keys())
        if not ordered_indices:
            return
        current_index = self._find_least_progress_track_index()
        if current_index is None:
            current_index = ordered_indices[0] if direction > 0 else ordered_indices[-1]
        try:
            current_order_pos = ordered_indices.index(current_index)
        except ValueError:
            return
        target_pos = current_order_pos + direction
        if target_pos < 0 or target_pos >= len(ordered_indices):
            return
        target_index = ordered_indices[target_pos]
        if current_index != target_index:
            self._toggle_playlist_track_button(current_index, False)
        self._toggle_playlist_track_button(target_index, True)

    def _handle_seek_pressed(self, index: int) -> None:
        self._seek_active[index] = True

    def _handle_seek_released(self, index: int) -> None:
        self._ensure_audio_service_tracks()
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

    def _handle_seek_slider_moved(self, index: int, value: int) -> None:
        slider = self._playlist_seek_sliders.get(index)
        duration = self._playlist_track_durations.get(index)
        if slider is None or not duration or duration <= 0:
            return
        ratio = value / max(1, slider.maximum())
        preview_seconds = (ratio * duration) / 1000
        if (label := self._playlist_current_labels.get(index)) is not None:
            label.setText(self._format_time(preview_seconds))

    def _handle_audio_track_state_changed(self, index: int, playing: bool) -> None:
        button = self._playlist_play_buttons.get(index)
        if button is None:
            return
        button.blockSignals(True)
        button.setChecked(playing)
        button.blockSignals(False)
        slider = self._playlist_seek_sliders.get(index)
        if slider is not None:
            slider.setEnabled(playing or bool(self._playlist_track_durations.get(index)))
        self._sync_footer_play_button()
        if not playing:
            self._reset_playlist_track_progress(index)

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
        self._ensure_audio_service_tracks()
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

    def _find_least_progress_track_index(self) -> int | None:
        candidate_index: int | None = None
        candidate_ratio: float | None = None
        for index, button in self._playlist_play_buttons.items():
            if not button.isChecked():
                continue
            ratio = self._compute_track_progress_ratio(index)
            if candidate_ratio is None or ratio < candidate_ratio:
                candidate_ratio = ratio
                candidate_index = index
        return candidate_index

    def _compute_track_progress_ratio(self, index: int) -> float:
        slider = self._playlist_seek_sliders.get(index)
        maximum = slider.maximum() if slider is not None else 0
        if slider is not None and maximum > 0:
            return slider.value() / maximum
        track = self._get_playlist_track(index)
        if track is not None and track.duration_seconds > 0:
            return max(0.0, min(1.0, track.position_seconds / track.duration_seconds))
        return 0.0

    def _toggle_playlist_track_button(self, index: int, play: bool) -> None:
        button = self._playlist_play_buttons.get(index)
        if button is None or button.isChecked() == play:
            return
        button.click()

    def _start_first_playlist_track(self) -> bool:
        if not self._playlist_play_buttons:
            return False
        ordered_indices = sorted(self._playlist_play_buttons.keys())
        for index in ordered_indices:
            if index in self._playlist_play_buttons:
                self._toggle_playlist_track_button(index, True)
                return True
        return False

    def _pause_playlist_tracks(self) -> None:
        self._audio_service.pause_all()

    def _resume_paused_tracks(self) -> bool:
        return self._audio_service.resume_all()

    def _sync_footer_play_button(self) -> None:
        self._set_footer_play_button_checked(self._any_playlist_track_playing())

    def _set_footer_play_button_checked(self, checked: bool) -> None:
        button = self._playlist_button_map.get("PlaylistPlayPauseButton")
        if button is None or button.isChecked() == checked:
            return
        button.blockSignals(True)
        button.setChecked(checked)
        button.blockSignals(False)

    def _any_playlist_track_playing(self) -> bool:
        return any(button.isChecked() for button in self._playlist_play_buttons.values())

    def _prepare_playlist_for_slide_change(self) -> None:
        if not self._playlist_play_buttons:
            return
        active_indices = [idx for idx, button in self._playlist_play_buttons.items() if button.isChecked()]
        for idx in active_indices:
            self._toggle_playlist_track_button(idx, False)
        self._audio_context_reset_pending = True
        self._handle_recording_before_slide_change()

    def _handle_recording_before_slide_change(self) -> None:
        return

    def _reset_playlist_track_progress(self, index: int) -> None:
        slider = self._playlist_seek_sliders.get(index)
        if slider is not None:
            slider.blockSignals(True)
            slider.setValue(0)
            slider.blockSignals(False)
        if (label := self._playlist_current_labels.get(index)) is not None:
            label.setText(self._format_time(0))
        track = self._get_playlist_track(index)
        if track is not None:
            track.position_seconds = 0

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

    def _ensure_audio_service_tracks(self) -> None:
        slide = self._current_slide or self._viewmodel.current_slide
        if slide is not None:
            self._audio_service.set_tracks(slide.audio.playlist)


_AUDIO_EXTENSIONS = {".wav", ".wave", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".aiff", ".wma"}
_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".webp", ".tiff"}


class _SoundboardBar(QFrame):
    filesDropped = Signal(list)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("SoundboardBar")
        self.setAcceptDrops(True)
        self.setFrameShape(QFrame.Shape.NoFrame)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # type: ignore[override]
        if self._has_audio_files(event.mimeData()):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:  # type: ignore[override]
        if self._has_audio_files(event.mimeData()):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:  # type: ignore[override]
        files = self._extract_files(event.mimeData())
        if files:
            self.filesDropped.emit(files)
            event.acceptProposedAction()
            return
        super().dropEvent(event)

    @staticmethod
    def _has_audio_files(mime) -> bool:
        return any(
            url.isLocalFile() and Path(url.toLocalFile()).suffix.lower() in _AUDIO_EXTENSIONS
            for url in mime.urls()
        )

    @staticmethod
    def _extract_files(mime) -> list[str]:
        paths: list[str] = []
        for url in mime.urls():
            if not url.isLocalFile():
                continue
            path = url.toLocalFile()
            if Path(path).suffix.lower() in _AUDIO_EXTENSIONS:
                paths.append(path)
        return paths


class _SoundboardButton(QToolButton):
    imageDropped = Signal(int, str)

    def __init__(self, index: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._index = index
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setCheckable(False)
        self.setMinimumSize(SYMBOL_BUTTON_SIZE, SYMBOL_BUTTON_SIZE)
        self.setMaximumSize(SYMBOL_BUTTON_SIZE, SYMBOL_BUTTON_SIZE)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # type: ignore[override]
        if self._has_image(event.mimeData()):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:  # type: ignore[override]
        if self._has_image(event.mimeData()):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:  # type: ignore[override]
        files = self._extract_image(event.mimeData())
        if files:
            self.imageDropped.emit(self._index, files[0])
            event.acceptProposedAction()
            return
        super().dropEvent(event)

    @staticmethod
    def _has_image(mime) -> bool:
        return any(
            url.isLocalFile() and Path(url.toLocalFile()).suffix.lower() in _IMAGE_EXTENSIONS
            for url in mime.urls()
        )

    @staticmethod
    def _extract_image(mime) -> list[str]:
        paths: list[str] = []
        for url in mime.urls():
            if not url.isLocalFile():
                continue
            path = url.toLocalFile()
            if Path(path).suffix.lower() in _IMAGE_EXTENSIONS:
                paths.append(path)
        return paths
