from __future__ import annotations

import logging
import threading
import time
from typing import Iterable

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QColorDialog,
)

from shiboken6 import Shiboken

from slidequest.services.govee_service import GoveeDevice, GoveeService
from slidequest.ui.constants import DETAIL_HEADER_HEIGHT, SYMBOL_BUTTON_SIZE


class LightControlSectionMixin:
    """Encapsulates the Govee-powered LightControl detail view."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[misc]
        self._govee_service: GoveeService | None = None
        self._light_device_layout: QHBoxLayout | None = None
        self._light_device_placeholder: QLabel | None = None
        self._light_status_label: QLabel | None = None
        self._light_sync_button: QPushButton | None = None
        self._light_has_synced_once = False
        self._light_section_error_shown = False
        self._light_pending_error: tuple[str, bool] | None = None
        self._light_active_device_id: str | None = None
        self._light_device_buttons: list[_LightDeviceBadge] = []
        self._light_device_map: dict[str, GoveeDevice] = {}
        self._light_device_states: dict[str, bool | None] = {}
        self._light_device_rows: dict[str, _LightDeviceRow] = {}
        self._light_color_memory: dict[str, tuple[int, int, int, int | None]] = {}
        self._light_device_list_layout: QVBoxLayout | None = None
        self._light_device_list_placeholder: QLabel | None = None
        self._light_logger = logging.getLogger("slidequest.light_control")

    # ------------------------------------------------------------------ #
    # Construction
    # ------------------------------------------------------------------ #
    def _build_light_detail_view(self, parent: QWidget | None = None) -> QWidget:
        view = QWidget(parent)
        view.setObjectName("LightControlDetailView")
        layout = QVBoxLayout(view)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame(view)
        header.setObjectName("LightControlHeader")
        header.setFixedHeight(DETAIL_HEADER_HEIGHT)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 6, 12, 6)
        header_layout.setSpacing(8)

        device_scroll = QScrollArea(header)
        device_scroll.setObjectName("LightControlDeviceScroll")
        device_scroll.setWidgetResizable(True)
        device_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        device_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        device_scroll.setFrameShape(QFrame.Shape.NoFrame)
        device_scroll.setStyleSheet("QScrollBar:vertical { width: 0px; }")

        device_strip = QWidget(device_scroll)
        device_strip.setObjectName("LightControlDeviceStrip")
        strip_layout = QHBoxLayout(device_strip)
        strip_layout.setContentsMargins(0, 0, 0, 0)
        strip_layout.setSpacing(6)
        placeholder = QLabel("Noch keine Geräte synchronisiert.", device_strip)
        placeholder.setObjectName("LightControlDevicePlaceholder")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("color: rgba(255, 255, 255, 120); font-size: 11px;")
        strip_layout.addWidget(placeholder)
        strip_layout.addStretch(1)
        device_scroll.setWidget(device_strip)
        header_layout.addWidget(device_scroll, 1)
        layout.addWidget(header)
        self._light_device_layout = strip_layout
        self._light_device_placeholder = placeholder

        main = QFrame(view)
        main.setObjectName("LightControlMain")
        main_layout = QVBoxLayout(main)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)
        list_scroll = QScrollArea(main)
        list_scroll.setObjectName("LightControlDeviceListScroll")
        list_scroll.setWidgetResizable(True)
        list_scroll.setFrameShape(QFrame.Shape.NoFrame)
        list_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        list_container = QWidget(list_scroll)
        list_container_layout = QVBoxLayout(list_container)
        list_container_layout.setContentsMargins(0, 0, 0, 0)
        list_container_layout.setSpacing(8)
        placeholder = QLabel("Noch keine Geräte geladen.", list_container)
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("color: rgba(255,255,255,120);")
        list_container_layout.addWidget(placeholder)
        list_container_layout.addStretch(1)
        list_scroll.setWidget(list_container)
        main_layout.addWidget(list_scroll, 1)
        self._light_device_list_layout = list_container_layout
        self._light_device_list_placeholder = placeholder

        layout.addWidget(main, 1)

        footer = QFrame(view)
        footer.setObjectName("LightControlFooter")
        footer.setFixedHeight(DETAIL_HEADER_HEIGHT)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(12, 6, 12, 6)
        footer_layout.setSpacing(12)
        status_label = QLabel("Bereit für Sync.", footer)
        status_label.setObjectName("LightControlStatusLabel")
        status_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        footer_layout.addWidget(status_label, 1)
        self._light_status_label = status_label

        sync_button = QPushButton("Geräte synchronisieren", footer)
        sync_button.setObjectName("LightControlSyncButton")
        sync_button.setCursor(Qt.CursorShape.PointingHandCursor)
        sync_button.setToolTip("SQ.LightControl.SyncDevices")
        sync_button.clicked.connect(self._handle_light_sync_clicked)
        footer_layout.addWidget(sync_button, 0)
        self._light_sync_button = sync_button

        layout.addWidget(footer)
        return view

    # ------------------------------------------------------------------ #
    # Service wiring
    # ------------------------------------------------------------------ #
    def _init_light_service(self) -> None:
        service = self._govee_service
        if service is None:
            return
        service.sync_started.connect(self._handle_light_sync_started)
        service.sync_finished.connect(self._handle_light_sync_finished)
        service.sync_failed.connect(self._handle_light_sync_failed)

    def _bootstrap_light_sync(self) -> None:
        service = self._govee_service
        if service is None or not service.has_api_key() or self._light_has_synced_once:
            return
        service.sync_devices()

    # ------------------------------------------------------------------ #
    # UI helpers
    # ------------------------------------------------------------------ #
    def _refresh_light_device_strip(self, devices: Iterable[GoveeDevice] | None = None) -> None:
        layout = self._light_device_layout
        if layout is None:
            return
        placeholder = self._light_device_placeholder
        if placeholder is not None and not Shiboken.isValid(placeholder):
            placeholder = None
            self._light_device_placeholder = None
        for button in self._light_device_buttons:
            if Shiboken.isValid(button):
                button.deleteLater()
        self._light_device_buttons.clear()
        if devices is None:
            service = self._govee_service
            devices = service.devices() if service else []
        device_list = [device for device in devices]
        self._light_device_map = {device.device_id: device for device in device_list}
        self._light_device_states.update({device.device_id: device.power_state for device in device_list})
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is None:
                continue
            if placeholder is not None and widget is placeholder:
                widget.hide()
                continue
            widget.deleteLater()
        if not device_list:
            self._light_active_device_id = None
            if placeholder is None:
                placeholder = QLabel("Noch keine Geräte synchronisiert.", layout.parentWidget())
                placeholder.setObjectName("LightControlDevicePlaceholder")
                placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
                placeholder.setStyleSheet("color: rgba(255, 255, 255, 120); font-size: 11px;")
                self._light_device_placeholder = placeholder
            if placeholder is not None:
                placeholder.show()
                layout.addWidget(placeholder)
            layout.addStretch(1)
            return
        for device in device_list:
            button = _LightDeviceBadge(device.short_label, device.device_id, parent=layout.parentWidget())
            button.setToolTip(f"SQ.LightControl.Device::{device.device_id or device.sku}")
            button.setChecked(device.device_id == self._light_active_device_id)
            button_state = self._light_device_states.get(device.device_id)
            if button_state is None:
                button_state = device.power_state
            button.set_power_state(button_state)
            button.clicked.connect(lambda _checked=False, dev=device: self._handle_light_device_button_clicked(dev))
            layout.addWidget(button)
            self._light_device_buttons.append(button)
        layout.addStretch(1)
        if device_list:
            self._ensure_light_selection(device_list)
        self._refresh_light_device_list(device_list)

    def _set_light_status(self, message: str) -> None:
        label = self._light_status_label
        if label is not None:
            label.setText(message)

    # ------------------------------------------------------------------ #
    # Event handlers
    # ------------------------------------------------------------------ #
    def _handle_light_sync_clicked(self) -> None:
        if not self._ensure_govee_api_key():
            return
        service = self._govee_service
        if service is not None:
            service.sync_devices(force=True)

    def _handle_light_sync_started(self) -> None:
        button = self._light_sync_button
        if button is not None:
            button.setEnabled(False)
        self._set_light_status("Synchronisiere Geräte …")

    def _handle_light_sync_finished(self, devices: list[GoveeDevice]) -> None:
        self._light_has_synced_once = True
        button = self._light_sync_button
        if button is not None:
            button.setEnabled(True)
        self._refresh_light_device_strip(devices)
        count = len(devices)
        suffix = "Gerät" if count == 1 else "Geräte"
        self._set_light_status(f"{count} {suffix} synchronisiert.")

    def _handle_light_sync_failed(self, message: str) -> None:
        button = self._light_sync_button
        if button is not None:
            button.setEnabled(True)
        normalized = (message or "Sync fehlgeschlagen.").strip()
        self._set_light_status(normalized)
        service = self._govee_service
        limited_case = bool(
            service and service.has_api_key() and "keine geräte" in normalized.lower()
        )
        is_section_active = getattr(self, "_detail_active_mode", None) == "lights"
        if limited_case and not is_section_active:
            self._light_pending_error = (normalized, True)
            return
        self._display_light_error_dialog(normalized, limited_case=limited_case)

    def _handle_light_mode_activated(self) -> None:
        self._light_section_error_shown = False
        pending_error = self._light_pending_error
        self._light_pending_error = None
        if pending_error:
            message, limited_case = pending_error
            self._display_light_error_dialog(message, limited_case=limited_case)
        self._refresh_light_device_strip()
        if not self._light_has_synced_once:
            self._bootstrap_light_sync()

    def _ensure_govee_api_key(self) -> bool:
        service = self._govee_service
        if service is None:
            return False
        if service.has_api_key():
            return True
        token, ok = QInputDialog.getText(
            self,
            "Govee API-Key",
            "Bitte Govee API-Key eingeben:",
            QLineEdit.EchoMode.Password,
        )
        if not ok or not token.strip():
            return False
        service.set_api_key(token.strip())
        return service.has_api_key()

    def _display_light_error_dialog(self, message: str, *, limited_case: bool) -> None:
        if limited_case:
            if self._light_section_error_shown:
                return
            self._light_section_error_shown = True
        QMessageBox.warning(self, "Govee Sync", message)

    def _handle_light_device_button_clicked(self, device: GoveeDevice) -> None:
        self._handle_light_power_toggle(device.device_id)

    def _handle_light_color_clicked(self, device_id: str) -> None:
        device = self._light_device_map.get(device_id)
        service = self._govee_service
        if device is None or service is None:
            self._set_light_status("Gerät oder Service nicht verfügbar.")
            return
        remembered = self._light_color_memory.get(device_id)
        if remembered is None:
            initial = QColor("white")
        else:
            r, g, b, _ = remembered
            initial = QColor(r, g, b)
        color = QColorDialog.getColor(
            initial,
            self,
            f"Farbe für {device.short_label}",
            QColorDialog.ColorDialogOption.ShowAlphaChannel,
        )
        if not color.isValid():
            return
        brightness = int(max(1, min(100, round(color.valueF() * 100))))
        self._light_color_memory[device_id] = (color.red(), color.green(), color.blue(), brightness)
        self._set_light_status(f"{device.short_label}: Farbe wird gesetzt …")

        def worker() -> None:
            try:
                success, message = service.set_device_color(
                    device.device_id,
                    device.sku,
                    color.red(),
                    color.green(),
                    color.blue(),
                    brightness,
                )
            except Exception as exc:  # pragma: no cover - network errors
                success, message = False, str(exc)

            def finalize() -> None:
                if success:
                    self._set_light_status(f"{device.short_label}: Farbe aktualisiert ({message}).")
                else:
                    self._set_light_status(f"{device.short_label}: Farbe fehlgeschlagen – {message}")

            QTimer.singleShot(0, finalize)

        threading.Thread(target=worker, daemon=True).start()

    def _handle_light_power_toggle(self, device_id: str) -> None:
        device = self._light_device_map.get(device_id)
        service = self._govee_service
        if device is None or service is None:
            self._set_light_status("Gerät oder Service nicht verfügbar.")
            return
        cached_state = self._light_device_states.get(device_id)
        if cached_state is None:
            cached_state = device.power_state
        if cached_state is None:
            self._set_light_status(f"{device.short_label}: Status wird abgefragt …")
        else:
            action = "einschalten" if not cached_state else "ausschalten"
            self._set_light_status(f"{device.short_label}: Versuche zu {action} …")

        pending_state = True
        if cached_state is None:
            pending_state = True
        else:
            pending_state = not cached_state
        # Optimistic update so subsequent toggles see the latest intent.
        self._light_device_states[device.device_id] = pending_state
        self._update_power_state_ui(device.device_id, pending_state)

        def worker() -> None:
            desired_state_local = pending_state
            baseline_state = cached_state
            try:
                actual_before = baseline_state
                if actual_before is None:
                    actual_before = device.power_state
                if actual_before is None:
                    actual_before = service.fetch_device_power(device.device_id, device.sku)
                self._light_logger.debug(
                    "LightControl: %s aktueller Status vor Toggle: %s",
                    device.short_label,
                    actual_before,
                )
                if actual_before is not None:
                    desired_state_local = not actual_before
                    self._light_device_states[device.device_id] = desired_state_local
                    self._update_power_state_ui(device.device_id, desired_state_local)
                if cached_state is None:
                    action_text = "einschalten" if desired_state_local else "ausschalten"
                    QTimer.singleShot(0, lambda text=action_text: self._set_light_status(f"{device.short_label}: Versuche zu {text} …"))
                success, message, reported_state = service.control_device_power(
                    device.device_id,
                    device.sku,
                    desired_state_local,
                )
                self._light_logger.debug(
                    "LightControl: Toggle request %s -> %s (reported=%s)",
                    desired_state_local,
                    device.short_label,
                    reported_state,
                )
            except Exception as exc:  # pragma: no cover - network errors
                success, message, reported_state = False, str(exc), None
                actual_before = cached_state
            if success:
                actual_state = reported_state
                if actual_state is None:
                    actual_state = service.fetch_device_power(device.device_id, device.sku)
                if actual_state is None or (actual_before is not None and actual_state == actual_before):
                    polled = self._poll_device_state(device, desired_state_local, actual_before)
                    if polled is not None:
                        actual_state = polled
            else:
                actual_state = None
            self._light_logger.debug(
                "LightControl: %s Erfolg=%s final server state=%s",
                device.short_label,
                success,
                actual_state,
            )

            def finalize() -> None:
                if success:
                    final_state = actual_state if actual_state is not None else desired_state_local
                    self._light_device_states[device.device_id] = final_state
                    device.power_state = final_state
                    if device.device_id in self._light_device_map:
                        self._light_device_map[device.device_id].power_state = final_state
                    service_devices = service.devices()
                    for entry in service_devices:
                        if entry.device_id == device.device_id:
                            entry.power_state = final_state
                            break
                    self._update_power_state_ui(device.device_id, final_state)
                    state_label = "eingeschaltet" if final_state else "ausgeschaltet"
                    if actual_state is not None and actual_state != desired_state_local:
                        self._set_light_status(
                            f"{device.short_label}: Zustand blieb {state_label} (Server meldet kein Umschalten)."
                        )
                    else:
                        self._set_light_status(f"{device.short_label}: {state_label} ({message})")
                else:
                    self._set_light_status(f"{device.short_label}: Fehler – {message}")
                    # revert optimistic state
                    previous = baseline_state if baseline_state is not None else device.power_state
                    self._light_device_states[device.device_id] = previous
                    self._update_power_state_ui(device.device_id, previous)

            QTimer.singleShot(0, finalize)

        threading.Thread(target=worker, daemon=True).start()

    def _ensure_light_selection(self, devices: list[GoveeDevice]) -> None:
        if not devices:
            self._light_active_device_id = None
            self._sync_light_button_checks()
            return
        for device in devices:
            if device.device_id == self._light_active_device_id:
                self._sync_light_button_checks()
                return
        self._light_active_device_id = devices[0].device_id
        self._sync_light_button_checks()

    def _sync_light_button_checks(self) -> None:
        for button in self._light_device_buttons:
            if not Shiboken.isValid(button):
                continue
            button.setChecked(button.device_id == self._light_active_device_id)
            button_state = self._light_device_states.get(button.device_id)
            if button_state is None:
                device = self._light_device_map.get(button.device_id)
                button_state = device.power_state if device else None
            button.set_power_state(button_state)

    def _update_power_state_ui(self, device_id: str, power_on: bool | None) -> None:
        for button in self._light_device_buttons:
            if not Shiboken.isValid(button):
                continue
            if button.device_id == device_id:
                button.set_power_state(power_on)
        row = self._light_device_rows.get(device_id)
        if row is not None:
            row.update_state(power_on)

    def _poll_device_state(
        self,
        device: GoveeDevice,
        desired_state: bool,
        baseline: bool | None,
        *,
        polls: int = 3,
        delay: float = 0.6,
    ) -> bool | None:
        service = self._govee_service
        if service is None:
            return None
        last_state: bool | None = None
        for _ in range(polls):
            time.sleep(delay)
            state = service.fetch_device_power(device.device_id, device.sku)
            if state is None:
                continue
            last_state = state
            if state != baseline or state == desired_state:
                break
        return last_state

    def _refresh_light_device_list(self, devices: list[GoveeDevice]) -> None:
        layout = self._light_device_list_layout
        if layout is None:
            return
        placeholder = self._light_device_list_placeholder
        existing_ids = set(self._light_device_rows.keys())
        incoming_ids = {device.device_id for device in devices}
        # Remove missing
        for device_id in existing_ids - incoming_ids:
            row = self._light_device_rows.pop(device_id, None)
            if row is not None:
                row.deleteLater()
        # Add / update
        parent_widget = layout.parentWidget()
        if devices and placeholder is not None:
            layout.removeWidget(placeholder)
            placeholder.hide()
        for idx, device in enumerate(devices):
            row = self._light_device_rows.get(device.device_id)
            if row is None:
                row = _LightDeviceRow(device, self, parent=parent_widget)
                self._light_device_rows[device.device_id] = row
                layout.insertWidget(idx, row)
            row.update_device(device)
            row.update_state(self._light_device_states.get(device.device_id))
        if not devices and placeholder is not None:
            if placeholder.parent() is None:
                parent_widget = layout.parentWidget()
                if parent_widget is not None:
                    placeholder.setParent(parent_widget)
            if layout.indexOf(placeholder) == -1:
                layout.insertWidget(0, placeholder)
            placeholder.show()


class _LightDeviceBadge(QToolButton):

    def __init__(self, label: str, device_id: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.device_id = device_id
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setText(label)
        badge_font = QFont(self.font())
        badge_font.setPointSizeF(max(8.0, badge_font.pointSizeF() - 2))
        badge_font.setBold(True)
        self.setFont(badge_font)
        self.setFixedSize(SYMBOL_BUTTON_SIZE, SYMBOL_BUTTON_SIZE)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.setCheckable(True)
        self.setAutoExclusive(False)
        self.setProperty("powerState", "unknown")
        self.setStyleSheet(
            """
            QToolButton {
                border: 1px solid rgba(255, 255, 255, 60);
                border-radius: 10px;
                background-color: rgba(0, 0, 0, 0.45);
                color: rgba(255, 255, 255, 200);
                padding: 4px;
                font-size: 10px;
                text-transform: uppercase;
            }
            QToolButton[powerState="true"] {
                border-color: rgba(74, 222, 128, 200);
                background-color: rgba(74, 222, 128, 0.35);
                color: rgba(0, 0, 0, 220);
            }
            QToolButton:hover {
                border-color: rgba(255, 255, 255, 120);
                background-color: rgba(255, 255, 255, 0.08);
            }
            QToolButton:pressed {
                background-color: rgba(255, 255, 255, 0.18);
            }
            QToolButton:checked {
                border-color: rgba(255, 255, 255, 180);
                background-color: rgba(255, 255, 255, 0.25);
                color: rgba(0, 0, 0, 220);
            }
            QToolButton:checked[powerState="true"] {
                border-color: rgba(74, 222, 128, 255);
                background-color: rgba(74, 222, 128, 0.55);
            }
            QToolButton[powerState="unknown"] {
                border-style: dashed;
            }
            """
        )

    def set_power_state(self, power_on: bool | None) -> None:
        state = "true" if power_on is True else "false" if power_on is False else "unknown"
        self.setProperty("powerState", state)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()


class _LightDeviceRow(QFrame):
    def __init__(self, device: GoveeDevice, controller: LightControlSectionMixin, parent: QWidget | None = None):
        super().__init__(parent)
        self._controller = controller
        self._device = device
        self.setObjectName("LightDeviceRow")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(12)
        name_label = QLabel(device.name, self)
        name_label.setObjectName("LightDeviceRowName")
        layout.addWidget(name_label, 1)
        power_button = QPushButton("Power", self)
        power_button.setCursor(Qt.CursorShape.PointingHandCursor)
        power_button.clicked.connect(self._handle_power_clicked)
        layout.addWidget(power_button)
        color_button = QPushButton("Farbe …", self)
        color_button.setCursor(Qt.CursorShape.PointingHandCursor)
        color_button.clicked.connect(self._handle_color_clicked)
        layout.addWidget(color_button)
        self._name_label = name_label
        self._power_button = power_button
        self._color_button = color_button
        self.update_device(device)

    def update_device(self, device: GoveeDevice) -> None:
        self._device = device
        self._name_label.setText(device.name)

    def update_state(self, power_on: bool | None) -> None:
        if power_on is True:
            self._power_button.setText("Ausschalten")
        elif power_on is False:
            self._power_button.setText("Einschalten")
        else:
            self._power_button.setText("Power …")
        self._power_button.setProperty("powerState", "true" if power_on else "false" if power_on is False else "unknown")
        self.style().unpolish(self._power_button)
        self.style().polish(self._power_button)

    def _handle_power_clicked(self) -> None:
        controller = self._controller
        if hasattr(controller, "_handle_light_device_button_clicked"):
            controller._handle_light_device_button_clicked(self._device)

    def _handle_color_clicked(self) -> None:
        controller = self._controller
        controller._handle_light_color_clicked(self._device.device_id)
