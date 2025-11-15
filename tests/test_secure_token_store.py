from __future__ import annotations

import os

from slidequest.services.token_store import SecureTokenStore


class _FakeKeyring:
    def __init__(self) -> None:
        self.storage: dict[tuple[str, str], str] = {}
        self.fail_next = False

    def get_password(self, service_name: str, account_name: str) -> str | None:
        if self.fail_next:
            self.fail_next = False
            raise RuntimeError("read-fail")
        return self.storage.get((service_name, account_name))

    def set_password(self, service_name: str, account_name: str, password: str) -> None:
        if self.fail_next:
            self.fail_next = False
            raise RuntimeError("write-fail")
        self.storage[(service_name, account_name)] = password

    def delete_password(self, service_name: str, account_name: str) -> None:
        self.storage.pop((service_name, account_name), None)


def test_store_and_load_from_keyring(monkeypatch) -> None:
    fake = _FakeKeyring()
    store = SecureTokenStore(
        keyring_service="slidequest",
        account_name="replicate",
        env_var="TEST_REPLICATE_TOKEN",
        backend=fake,
    )

    assert store.load() is None
    assert store.save(" secret ")
    assert fake.storage
    assert os.environ.get("TEST_REPLICATE_TOKEN") is None
    assert store.load() == "secret"

    store.clear()
    assert store.load() is None


def test_store_falls_back_to_env_when_keyring_unavailable(monkeypatch) -> None:
    store = SecureTokenStore(
        keyring_service="slidequest",
        account_name="replicate",
        env_var="TEST_REPLICATE_TOKEN",
        backend=None,
    )
    store.save("token123")
    assert os.environ["TEST_REPLICATE_TOKEN"] == "token123"
    assert store.load() == "token123"
    store.clear()
    assert "TEST_REPLICATE_TOKEN" not in os.environ


def test_keyring_failure_logs_and_falls_back(monkeypatch, caplog) -> None:
    fake = _FakeKeyring()
    fake.fail_next = True
    store = SecureTokenStore(
        keyring_service="slidequest",
        account_name="replicate",
        env_var="TEST_REPLICATE_TOKEN",
        backend=fake,
    )
    store.save("x")
    assert "TEST_REPLICATE_TOKEN" in os.environ
    assert ("slidequest", "replicate") not in fake.storage
