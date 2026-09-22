from __future__ import annotations

from pathlib import Path

from src.discovery import hermes_runtime
from src.discovery.hermes_runtime import (
    HermesRuntimeSnapshot,
    get_hermes_runtime_snapshot,
)


class _FakeClient:
    def status(self):
        return {"version": "0.21.4"}

    def profiles(self):
        return {
            "profiles": [
                {"name": "jeeves"},
                {"name": "default"},
            ]
        }

    def active_profile(self):
        return {
            "active": {"name": "jeeves"},
            "current": "jeeves",
        }


def _local_snapshot():
    return HermesRuntimeSnapshot(
        executable_path=Path("/opt/hermes/.venv/bin/hermes"),
        version="local-version",
        installation_path=Path("/opt/hermes/.venv/bin"),
        venv_path=Path("/opt/hermes/.venv"),
        site_packages_paths=[Path("/opt/hermes/.venv/lib/python3.13/site-packages")],
        profile_names=["local"],
        current_profile="local",
        config_path=Path("/home/test/.hermes/config.yaml"),
    )


def test_remote_runtime_enriches_snapshot(monkeypatch):
    monkeypatch.setattr(
        hermes_runtime,
        "_discover_runtime",
        lambda: _local_snapshot(),
    )
    monkeypatch.setattr(
        hermes_runtime.HermesRuntimeClient,
        "from_environment",
        classmethod(lambda cls: _FakeClient()),
    )

    snap = get_hermes_runtime_snapshot()

    assert snap.version == "0.21.4"
    assert snap.profile_names == ["default", "jeeves"]
    assert snap.current_profile == "jeeves"
    assert snap.executable_path == Path("/opt/hermes/.venv/bin/hermes")


def test_missing_remote_configuration_preserves_local_snapshot(monkeypatch):
    local = _local_snapshot()

    monkeypatch.setattr(
        hermes_runtime,
        "_discover_runtime",
        lambda: local,
    )
    monkeypatch.setattr(
        hermes_runtime.HermesRuntimeClient,
        "from_environment",
        classmethod(lambda cls: None),
    )

    snap = get_hermes_runtime_snapshot()

    assert snap is local
    assert snap.version == "local-version"
    assert snap.profile_names == ["local"]
    assert snap.current_profile == "local"


def test_remote_failure_preserves_local_snapshot(monkeypatch):
    local = _local_snapshot()

    class FailingClient:
        def status(self):
            raise RuntimeError("connection failed")

    monkeypatch.setattr(
        hermes_runtime,
        "_discover_runtime",
        lambda: local,
    )
    monkeypatch.setattr(
        hermes_runtime.HermesRuntimeClient,
        "from_environment",
        classmethod(lambda cls: FailingClient()),
    )

    snap = get_hermes_runtime_snapshot()

    assert snap is local
    assert snap.version == "local-version"
    assert snap.profile_names == ["local"]
    assert snap.current_profile == "local"


def test_remote_profile_names_ignore_malformed_entries(monkeypatch):
    client = _FakeClient()

    class CustomClient(_FakeClient):
        def profiles(self):
            return {
                "profiles": [
                    {"name": "jeeves"},
                    {"name": ""},
                    {"name": None},
                    {},
                    "invalid",
                    {"name": "jeeves"},
                ]
            }

    monkeypatch.setattr(
        hermes_runtime,
        "_discover_runtime",
        _local_snapshot,
    )

    result = hermes_runtime._enrich_from_remote(
        _local_snapshot(),
        CustomClient(),
    )

    assert result.profile_names == ["jeeves"]


def test_snapshot_does_not_store_runtime_token(monkeypatch):
    monkeypatch.setattr(
        hermes_runtime,
        "_discover_runtime",
        _local_snapshot,
    )
    monkeypatch.setattr(
        hermes_runtime.HermesRuntimeClient,
        "from_environment",
        classmethod(lambda cls: _FakeClient()),
    )
    monkeypatch.setenv("HERMES_RUNTIME_TOKEN", "super-secret-token")

    snap = get_hermes_runtime_snapshot()

    assert "super-secret-token" not in repr(snap)
    assert not hasattr(snap, "token")
    assert not hasattr(snap, "runtime_token")
