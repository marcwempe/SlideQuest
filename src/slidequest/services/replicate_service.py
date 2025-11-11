from __future__ import annotations

import os
import tempfile
import threading
from pathlib import Path
from typing import Any
from uuid import uuid4

from PySide6.QtCore import QObject, Signal

try:  # pragma: no cover - optional dependency
    from dotenv import find_dotenv, load_dotenv
except Exception:  # pragma: no cover - fallback stubs
    def find_dotenv(*_args, **_kwargs) -> str:
        return ""

    def load_dotenv(*_args, **_kwargs) -> bool:
        return False

try:  # pragma: no cover - optional dependency
    import replicate
except Exception:  # pragma: no cover - degrade gracefully
    replicate = None  # type: ignore[assignment]


class ReplicateService(QObject):
    """Thin wrapper around the Replicate client with Qt-friendly signals."""

    generation_started = Signal(str)
    generation_progress = Signal(str)
    generation_failed = Signal(str, str)
    generation_finished = Signal(str, list)

    MODEL_IDENTIFIER = "bytedance/seedream-4"

    def __init__(self) -> None:
        super().__init__()
        self._api_token = self._load_env_token()
        self._client = self._build_client(self._api_token)
        self._lock = threading.Lock()
        self._active_thread: threading.Thread | None = None

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def has_api_token(self) -> bool:
        return bool(self._api_token)

    def set_api_token(self, token: str) -> None:
        normalized = token.strip()
        self._api_token = normalized or None
        if normalized:
            os.environ["REPLICATE_API_TOKEN"] = normalized
        self._client = self._build_client(self._api_token)

    def is_busy(self) -> bool:
        thread = self._active_thread
        return bool(thread and thread.is_alive())

    def generate_seedream(
        self,
        *,
        prompt: str,
        aspect_ratio: str,
        size: str,
        width: int,
        height: int,
        enhance_prompt: bool,
        max_images: int,
        image_inputs: list[str] | None = None,
    ) -> str:
        client = self._ensure_client()
        if client is None:
            raise RuntimeError("Kein Replicate-Client verfügbar. Bitte API-Key hinterlegen.")
        if not prompt.strip():
            raise ValueError("Prompt darf nicht leer sein.")
        if self.is_busy():
            raise RuntimeError("Es läuft bereits eine Generierung.")
        request_id = uuid4().hex
        payload = self._build_input_payload(
            prompt=prompt.strip(),
            aspect_ratio=aspect_ratio,
            size=size,
            width=width,
            height=height,
            enhance_prompt=enhance_prompt,
            max_images=max_images,
            image_inputs=image_inputs or [],
        )
        thread = threading.Thread(
            target=self._run_generation,
            args=(request_id, payload),
            daemon=True,
        )
        with self._lock:
            self._active_thread = thread
        self.generation_started.emit(request_id)
        thread.start()
        return request_id

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _run_generation(self, request_id: str, payload: dict[str, Any]) -> None:
        temp_paths: list[str] = []
        try:
            client = self._ensure_client()
            if client is None:
                raise RuntimeError("Replicate-Client nicht verfügbar.")
            self.generation_progress.emit("Seedream 4 wird ausgeführt …")
            output = client.run(self.MODEL_IDENTIFIER, input=payload)
            for index, item in enumerate(output or []):
                temp_paths.append(self._write_output_item(item, index))
        except Exception as exc:  # pragma: no cover - network errors
            self.generation_failed.emit(request_id, str(exc))
            for path in temp_paths:
                Path(path).unlink(missing_ok=True)
        else:
            self.generation_finished.emit(request_id, temp_paths)
        finally:
            with self._lock:
                self._active_thread = None

    def _write_output_item(self, item: Any, index: int) -> str:
        blob = getattr(item, "read", None)
        if isinstance(item, str):
            data = self._download_bytes(item)
        elif callable(blob):
            data = blob()
        else:
            data = bytes(item)
        extension = self._resolve_extension(item)
        handle = tempfile.NamedTemporaryFile(delete=False, suffix=extension)
        path = Path(handle.name)
        handle.write(data)
        handle.close()
        return str(path)

    @staticmethod
    def _download_bytes(url: str) -> bytes:
        from urllib.request import urlopen

        with urlopen(url) as response:  # nosec - trusted model output
            return response.read()

    @staticmethod
    def _resolve_extension(item: Any) -> str:
        name = getattr(item, "name", "") or getattr(item, "filename", "")
        if isinstance(name, str):
            suffix = Path(name).suffix
            if suffix:
                return suffix
        mime = getattr(item, "mime_type", "") or getattr(item, "content_type", "")
        if isinstance(mime, str):
            if "png" in mime:
                return ".png"
            if "jpeg" in mime or "jpg" in mime:
                return ".jpg"
            if "webp" in mime:
                return ".webp"
        return ".png"

    def _build_input_payload(
        self,
        *,
        prompt: str,
        aspect_ratio: str,
        size: str,
        width: int,
        height: int,
        enhance_prompt: bool,
        max_images: int,
        image_inputs: list[str],
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "size": size,
            "enhance_prompt": bool(enhance_prompt),
            "max_images": max(1, min(max_images, 15)),
        }
        if image_inputs:
            payload["image_input"] = image_inputs[:10]
        if size == "custom":
            payload["width"] = max(1024, min(width, 4096))
            payload["height"] = max(1024, min(height, 4096))
        return payload

    def _build_client(self, token: str | None):
        if not token or replicate is None:
            return None
        try:
            return replicate.Client(api_token=token)
        except Exception:  # pragma: no cover - invalid tokens
            return None

    def _ensure_client(self):
        if self._client is not None:
            return self._client
        if not self._api_token:
            return None
        self._client = self._build_client(self._api_token)
        return self._client

    def _load_env_token(self) -> str | None:
        dotenv_path = find_dotenv(usecwd=True)
        if dotenv_path:
            load_dotenv(dotenv_path, override=False)
        token = os.environ.get("REPLICATE_API_TOKEN", "").strip()
        return token or None
