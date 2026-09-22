from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from src.discovery.hermes_runtime import HermesRuntimeSnapshot


def test_hermes_runtime_route_returns_snapshot(monkeypatch):
    snapshot = HermesRuntimeSnapshot(
        executable_path=Path("/opt/hermes/.venv/bin/hermes"),
        version="0.21.4",
        installation_path=Path("/opt/hermes/.venv/bin"),
        venv_path=Path("/opt/hermes/.venv"),
        site_packages_paths=[
            Path("/opt/hermes/.venv/lib/python3.13/site-packages")
        ],
        profile_names=["default", "jeeves"],
        current_profile="jeeves",
        config_path=Path("/home/hermes/.hermes/config.yaml"),
    )

    monkeypatch.setattr(
        "app.routes.runtime.get_hermes_runtime_snapshot",
        lambda: snapshot,
    )

    client = TestClient(create_app())
    response = client.get("/api/runtime/hermes")

    assert response.status_code == 200
    assert response.json() == {
        "executable_path": "/opt/hermes/.venv/bin/hermes",
        "version": "0.21.4",
        "installation_path": "/opt/hermes/.venv/bin",
        "venv_path": "/opt/hermes/.venv",
        "site_packages_paths": [
            "/opt/hermes/.venv/lib/python3.13/site-packages"
        ],
        "profile_names": ["default", "jeeves"],
        "current_profile": "jeeves",
        "config_path": "/home/hermes/.hermes/config.yaml",
    }


def test_hermes_runtime_route_does_not_expose_token(monkeypatch):
    snapshot = HermesRuntimeSnapshot(
        version="0.21.4",
        profile_names=["jeeves"],
        current_profile="jeeves",
    )

    monkeypatch.setenv("HERMES_RUNTIME_TOKEN", "super-secret-token")
    monkeypatch.setattr(
        "app.routes.runtime.get_hermes_runtime_snapshot",
        lambda: snapshot,
    )

    client = TestClient(create_app())
    response = client.get("/api/runtime/hermes")

    assert response.status_code == 200
    assert "super-secret-token" not in response.text
    assert "token" not in response.json()
