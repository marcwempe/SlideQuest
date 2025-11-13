from __future__ import annotations

import json
import os
import threading
import logging
from dataclasses import dataclass, field
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from PySide6.QtCore import QObject, Signal

try:  # pragma: no cover - optional dependency
    from dotenv import find_dotenv, load_dotenv
except Exception:  # pragma: no cover - fallback stubs
    def find_dotenv(*_args, **_kwargs) -> str:
        return ""

    def load_dotenv(*_args, **_kwargs) -> bool:
        return False


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class GoveeDevice:
    sku: str
    device_id: str
    name: str
    device_type: str
    room_name: str | None = None
    capabilities: list[dict[str, Any]] = field(default_factory=list)
    power_state: bool | None = None

    @property
    def short_label(self) -> str:
        label = (self.name or "").strip()
        if label:
            return label
        if self.room_name:
            return self.room_name
        if self.device_id:
            return f"#{self.device_id[-4:]}"
        return "Gerät"


class GoveeService(QObject):
    """Thin wrapper for the Govee OpenAPI device endpoints."""

    sync_started = Signal()
    sync_finished = Signal(object)  # list[GoveeDevice]
    sync_failed = Signal(str)

    API_BASE = "https://openapi.api.govee.com/router/api/v1"

    def __init__(self) -> None:
        super().__init__()
        self._api_key = self._load_env_key()
        self._devices: list[GoveeDevice] = []
        self._lock = threading.Lock()
        self._active_thread: threading.Thread | None = None

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def has_api_key(self) -> bool:
        return bool(self._api_key)

    def set_api_key(self, token: str) -> None:
        normalized = token.strip()
        self._api_key = normalized or None
        if normalized:
            os.environ["GOVEE_API_KEY"] = normalized

    def devices(self) -> list[GoveeDevice]:
        return list(self._devices)

    def sync_devices(self, *, force: bool = False) -> bool:
        if not self._api_key:
            self.sync_failed.emit("Kein Govee API-Key hinterlegt.")
            return False
        with self._lock:
            thread = self._active_thread
            if thread and thread.is_alive() and not force:
                return False
            worker = threading.Thread(target=self._sync_worker, daemon=True)
            self._active_thread = worker
        self.sync_started.emit()
        worker.start()
        return True

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _sync_worker(self) -> None:
        try:
            devices = self._fetch_devices()
        except Exception as exc:  # pragma: no cover - network errors
            self.sync_failed.emit(str(exc))
        else:
            self._devices = devices
            self.sync_finished.emit(devices)
        finally:
            with self._lock:
                self._active_thread = None

    def _fetch_devices(self) -> list[GoveeDevice]:
        endpoint = f"{self.API_BASE}/user/devices"
        masked_key = self._mask_key(self._api_key)
        logger.debug("Govee request: %s (key=%s)", endpoint, masked_key)
        request = Request(endpoint)
        request.add_header("Content-Type", "application/json")
        request.add_header("Govee-API-Key", self._api_key or "")
        logger.debug(
            "Govee HTTP request headers=%s",
            {k: ("<hidden>" if "key" in k.lower() else v) for k, v in request.header_items()},
        )
        status = None
        payload_bytes = b""
        try:
            with urlopen(request, timeout=20) as response:  # nosec - trusted upstream
                status = getattr(response, "status", None) or getattr(response, "code", None)
                payload_bytes = response.read()
                logger.debug(
                    "Govee HTTP response status=%s headers=%s",
                    status,
                    dict(response.headers.items()),
                )
        except HTTPError as err:
            logger.error("Govee HTTP error %s while fetching devices", err.code, exc_info=True)
            raise RuntimeError(f"Govee Sync fehlgeschlagen ({err.code}).") from err
        except URLError as err:
            logger.error("Govee URL error while fetching devices", exc_info=True)
            raise RuntimeError("Keine Verbindung zur Govee API möglich.") from err
        payload = (payload_bytes or b"{}").decode("utf-8", errors="ignore")
        logger.debug(
            "Govee response status=%s bytes=%s preview=%r",
            status,
            len(payload_bytes or b""),
            payload[:200],
        )
        data = json.loads(payload or "{}")
        if isinstance(data, dict):
            logger.debug(
                "Govee payload keys=%s data.keys=%s payload.devices=%s",
                list(data.keys()),
                list((data.get("data") or {}).keys()) if isinstance(data.get("data"), dict) else type(data.get("data")).__name__,
                type(data.get("devices")).__name__,
            )
        else:
            logger.debug("Govee payload type=%s", type(data).__name__)
        devices = self._normalize_devices(data)
        if not devices:
            summary = data.keys() if isinstance(data, dict) else type(data).__name__
            try:
                raw_snapshot = json.dumps(data, ensure_ascii=False)[:400]
            except TypeError:
                raw_snapshot = repr(data)[:400]
            logger.warning(
                "Govee API returned zero devices (status=%s, payload=%s, raw_data=%s)",
                status,
                summary,
                raw_snapshot,
            )
            raise RuntimeError("Keine Geräte in der Govee API gefunden.")
        logger.debug("Govee normalized %d devices", len(devices))
        self._hydrate_device_states(devices)
        self._log_device_capabilities(devices)
        return devices

    def _log_device_capabilities(self, devices: list[GoveeDevice]) -> None:
        for device in devices:
            caps = device.capabilities or []
            cap_summary = ", ".join(
                f"{cap.get('instance', '---')}[{cap.get('type', '')}]"
                for cap in caps
            ) or "keine Capabilities"
            logger.info(
                "Govee Gerät: %s (%s) – Typ=%s – Status=%s – Capabilities=%s",
                device.name,
                device.device_id,
                device.device_type,
                "AN" if device.power_state else ("AUS" if device.power_state is False else "UNBEKANNT"),
                cap_summary,
            )

    def _hydrate_device_states(self, devices: list[GoveeDevice]) -> None:
        for device in devices:
            state = self._fetch_power_state(device)
            if state is None:
                continue
            device.power_state = state

    def fetch_device_power(self, device_id: str, sku: str) -> bool | None:
        device = GoveeDevice(
            sku=sku,
            device_id=device_id,
            name="",
            device_type="",
            capabilities=[],
        )
        return self._fetch_power_state(device)

    def _fetch_power_state(self, device: GoveeDevice) -> bool | None:
        endpoint = f"{self.API_BASE}/device/state"
        payload = {
            "requestId": uuid4().hex,
            "payload": {
                "device": device.device_id,
                "sku": device.sku,
            },
        }
        data = json.dumps(payload).encode("utf-8")
        request = Request(endpoint, data=data, method="POST")
        request.add_header("Content-Type", "application/json")
        request.add_header("Govee-API-Key", self._api_key or "")
        logger.debug(
            "Govee state request device=%s headers=%s",
            device.device_id,
            {k: ("<hidden>" if "key" in k.lower() else v) for k, v in request.header_items()},
        )
        try:
            with urlopen(request, timeout=15) as response:  # nosec - trusted upstream
                payload_bytes = response.read()
                logger.debug(
                    "Govee state response device=%s status=%s",
                    device.device_id,
                    getattr(response, "status", None) or getattr(response, "code", None),
                )
        except Exception as exc:  # pragma: no cover - network errors
            logger.debug("Govee state für %s fehlgeschlagen: %s", device.device_id, exc)
            return None
        response_text = (payload_bytes or b"{}").decode("utf-8", errors="ignore")
        try:
            data = json.loads(response_text or "{}")
        except json.JSONDecodeError:
            return None
        caps = data.get("payload", {}).get("capabilities")
        if not isinstance(caps, list):
            return None
        return self._derive_power_state({"capabilities": caps})

    def _normalize_devices(self, payload: Any) -> list[GoveeDevice]:
        raw_devices: list[dict[str, Any]] = []

        def candidate_from_dict(data: dict[str, Any] | None) -> bool:
            nonlocal raw_devices
            if not isinstance(data, dict):
                return False
            devices = data.get("devices")
            if isinstance(devices, list) and devices:
                raw_devices = devices
                return True
            return False

        if isinstance(payload, dict):
            for container in (payload.get("data"), payload.get("payload"), payload):
                if candidate_from_dict(container):
                    break
            if not raw_devices:
                data_obj = payload.get("data")
                if isinstance(data_obj, list) and data_obj:
                    raw_devices = data_obj
        elif isinstance(payload, list):
            first = payload[0] if payload else None
            if isinstance(first, dict) and "devices" in first:
                devices = first.get("devices")
                if isinstance(devices, list):
                    raw_devices = devices
            elif payload and isinstance(payload[0], dict):
                raw_devices = payload  # already a device list
        devices: list[GoveeDevice] = []
        for entry in raw_devices:
            if not isinstance(entry, dict):
                continue
            sku = str(entry.get("sku") or "").strip()
            device_id = str(entry.get("device") or "").strip()
            name = str(entry.get("deviceName") or "").strip()
            device_type = str(entry.get("type") or "").strip()
            room_name = entry.get("roomName")
            capabilities = entry.get("capabilities") or []
            if not sku or not device_id:
                continue
            power_state = self._derive_power_state(entry)
            devices.append(
                GoveeDevice(
                    sku=sku,
                    device_id=device_id,
                    name=name or device_type or sku,
                    device_type=device_type or "devices.types.light",
                    room_name=str(room_name).strip() if isinstance(room_name, str) else None,
                    capabilities=capabilities if isinstance(capabilities, list) else [],
                    power_state=power_state,
                )
            )
        return devices

    def control_device_power(self, device_id: str, sku: str, turn_on: bool) -> tuple[bool, str, bool | None]:
        success, message, response_data = self._execute_capability_command(
            device_id,
            sku,
            {
                "type": "devices.capabilities.on_off",
                "instance": "powerSwitch",
                "value": 1 if turn_on else 0,
            },
        )
        reported_state = self._parse_control_state(response_data) if response_data else None
        if success:
            logger.info(
                "Govee power toggle device=%s sku=%s turn_on=%s state=%s",
                device_id,
                sku,
                turn_on,
                reported_state,
            )
        return success, message, reported_state

    def set_device_color(
        self,
        device_id: str,
        sku: str,
        red: int,
        green: int,
        blue: int,
        brightness: int | None = None,
    ) -> tuple[bool, str]:
        color_value = ((red & 0xFF) << 16) | ((green & 0xFF) << 8) | (blue & 0xFF)
        success, message, _ = self._execute_capability_command(
            device_id,
            sku,
            {
                "type": "devices.capabilities.color_setting",
                "instance": "colorRgb",
                "value": color_value,
            },
        )
        if not success:
            return success, message
        if brightness is not None:
            brightness_value = max(1, min(int(brightness), 100))
            success, message, _ = self._execute_capability_command(
                device_id,
                sku,
                {
                    "type": "devices.capabilities.range",
                    "instance": "brightness",
                    "value": brightness_value,
                },
            )
        return success, message

    def _parse_control_state(self, response: dict[str, Any]) -> bool | None:
        payload = response.get("payload")
        if not isinstance(payload, dict):
            return None
        capability = payload.get("capability")
        if not isinstance(capability, dict):
            return None
        value = capability.get("value")
        if isinstance(value, (int, float)):
            return value == 1
        return None

    def _load_env_key(self) -> str | None:
        dotenv_path = find_dotenv(usecwd=True)
        if dotenv_path:
            load_dotenv(dotenv_path, override=False)
        token = os.environ.get("GOVEE_API_KEY", "").strip()
        return token or None

    @staticmethod
    def _mask_key(token: str | None) -> str:
        if not token:
            return "none"
        if len(token) <= 4:
            return f"...{token}"
        return f"...{token[-4:]}"

    @staticmethod
    def _derive_power_state(entry: dict[str, Any]) -> bool | None:
        capabilities = entry.get("capabilities")
        if not isinstance(capabilities, list):
            return None
        for capability in capabilities:
            if not isinstance(capability, dict):
                continue
            if capability.get("type") != "devices.capabilities.on_off":
                continue
            state = capability.get("state")
            if isinstance(state, dict):
                value = state.get("value")
                if isinstance(value, (int, float)):
                    return value == 1
            elif isinstance(state, list) and state:
                item = state[0]
                if isinstance(item, dict) and isinstance(item.get("value"), (int, float)):
                    return item["value"] == 1
        return None

    def _execute_capability_command(
        self,
        device_id: str,
        sku: str,
        capability: dict[str, Any],
    ) -> tuple[bool, str, dict[str, Any]]:
        if not self._api_key:
            raise RuntimeError("Kein Govee API-Key hinterlegt.")
        if not device_id or not sku:
            raise ValueError("Ungültiges Gerät oder SKU.")
        endpoint = f"{self.API_BASE}/device/control"
        request_id = uuid4().hex
        payload = {
            "requestId": request_id,
            "payload": {
                "device": device_id,
                "sku": sku,
                "capability": capability,
            },
        }
        data = json.dumps(payload).encode("utf-8")
        request = Request(endpoint, data=data, method="POST")
        request.add_header("Content-Type", "application/json")
        request.add_header("Govee-API-Key", self._api_key or "")
        logger.debug(
            "Govee control request endpoint=%s device=%s sku=%s headers=%s body=%s",
            endpoint,
            device_id,
            sku,
            {k: ("<hidden>" if "key" in k.lower() else v) for k, v in request.header_items()},
            capability,
        )
        status = None
        payload_bytes = b""
        try:
            with urlopen(request, timeout=20) as response:  # nosec - trusted upstream
                status = getattr(response, "status", None) or getattr(response, "code", None)
                payload_bytes = response.read()
                logger.debug(
                    "Govee control response status=%s headers=%s",
                    status,
                    dict(response.headers.items()),
                )
        except HTTPError as err:
            logger.error("Govee control HTTP error %s", err.code, exc_info=True)
            return False, f"HTTP {err.code}", {}
        except URLError as err:
            logger.error("Govee control URL error", exc_info=True)
            return False, "Netzwerkfehler", {}
        response_text = (payload_bytes or b"{}").decode("utf-8", errors="ignore")
        try:
            response_data = json.loads(response_text or "{}")
        except json.JSONDecodeError:
            response_data = {"raw": response_text}
        success = bool(response_data.get("code") == 200)
        message = response_data.get("message") or response_data.get("msg") or ("OK" if success else response_text[:80])
        if success:
            logger.info(
                "Govee control success device=%s sku=%s capability=%s requestId=%s",
                device_id,
                sku,
                capability.get("instance"),
                request_id,
            )
        else:
            logger.warning(
                "Govee control failed device=%s sku=%s status=%s response=%s",
                device_id,
                sku,
                status,
                response_text[:200],
            )
        return success, message, response_data
