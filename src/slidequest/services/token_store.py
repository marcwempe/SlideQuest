from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Protocol

try:  # pragma: no cover - optional dependency
    import keyring
except Exception:  # pragma: no cover
    keyring = None  # type: ignore[assignment]


class _KeyringLike(Protocol):
    def get_password(self, service_name: str, account_name: str) -> str | None: ...

    def set_password(self, service_name: str, account_name: str, password: str) -> None: ...

    def delete_password(self, service_name: str, account_name: str) -> None: ...


@dataclass
class SecureTokenStore:
    """Persists API-Tokens via OS keyring; falls back to env vars when unavailable."""

    keyring_service: str
    account_name: str
    env_var: str | None = None
    logger: logging.Logger = logging.getLogger("slidequest.auth")
    backend: _KeyringLike | None = keyring

    def load(self) -> str | None:
        token = self._load_from_keyring()
        if token:
            return token
        return self._load_from_env()

    def save(self, token: str) -> bool:
        normalized = token.strip()
        if not normalized:
            self.clear()
            return False
        if self._store_in_keyring(normalized):
            self._clear_env()
            return True
        return self._store_in_env(normalized)

    def clear(self) -> None:
        self._delete_from_keyring()
        self._clear_env()

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _load_from_keyring(self) -> str | None:
        backend = self.backend
        if backend is None:
            return None
        try:
            stored = backend.get_password(self.keyring_service, self.account_name)
            return stored.strip() if stored else None
        except Exception as exc:  # pragma: no cover - backend failure
            self.logger.warning("Keyring read failed: %s", exc)
            return None

    def _store_in_keyring(self, token: str) -> bool:
        backend = self.backend
        if backend is None:
            return False
        try:
            backend.set_password(self.keyring_service, self.account_name, token)
            return True
        except Exception as exc:  # pragma: no cover - backend failure
            self.logger.warning("Keyring write failed: %s", exc)
            return False

    def _delete_from_keyring(self) -> None:
        backend = self.backend
        if backend is None:
            return
        try:
            backend.delete_password(self.keyring_service, self.account_name)
        except Exception:
            return

    def _load_from_env(self) -> str | None:
        if not self.env_var:
            return None
        return os.environ.get(self.env_var, "").strip() or None

    def _store_in_env(self, token: str) -> bool:
        if not self.env_var:
            return False
        os.environ[self.env_var] = token
        return True

    def _clear_env(self) -> None:
        if not self.env_var:
            return
        os.environ.pop(self.env_var, None)
