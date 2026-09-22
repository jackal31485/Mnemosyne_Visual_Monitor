from __future__ import annotations

from fastapi import APIRouter

from src.discovery.hermes_runtime import get_hermes_runtime_snapshot

router = APIRouter()


def _path_value(value):
    return str(value) if value is not None else None


@router.get("/api/runtime/hermes")
def get_hermes_runtime() -> dict:
    """Return non-sensitive Hermes runtime discovery information."""

    snapshot = get_hermes_runtime_snapshot()

    return {
        "executable_path": _path_value(snapshot.executable_path),
        "version": snapshot.version,
        "installation_path": _path_value(snapshot.installation_path),
        "venv_path": _path_value(snapshot.venv_path),
        "site_packages_paths": [
            str(path) for path in snapshot.site_packages_paths
        ],
        "profile_names": list(snapshot.profile_names),
        "current_profile": snapshot.current_profile,
        "config_path": _path_value(snapshot.config_path),
    }
