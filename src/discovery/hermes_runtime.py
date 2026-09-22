# Runtime discovery for Hermes.
#
# Public API:
#   - get_hermes_runtime_snapshot()
#   - HermesProfileInfo
#   - HermesRuntimeSnapshot

from __future__ import annotations

from typing import Any

try:
    from src.discovery.hermes_runtime_client import HermesRuntimeClient
    from src.discovery.utils import (
        HermesProfileInfo,
        HermesRuntimeSnapshot,
        _discover_runtime,
    )
except Exception:  # pragma: no cover
    from .hermes_runtime_client import HermesRuntimeClient
    from .utils import (
        HermesProfileInfo,
        HermesRuntimeSnapshot,
        _discover_runtime,
    )


def _remote_profile_names(data: dict[str, Any]) -> list[str]:
    profiles = data.get("profiles")
    if not isinstance(profiles, list):
        return []

    names = []
    for profile in profiles:
        if isinstance(profile, dict):
            name = profile.get("name")
            if isinstance(name, str) and name:
                names.append(name)

    return sorted(set(names))


def _remote_version(data: dict[str, Any]) -> str | None:
    version = data.get("version")
    return version if isinstance(version, str) and version else None


def _remote_current_profile(data: dict[str, Any]) -> str | None:
    current = data.get("current")
    if isinstance(current, str) and current:
        return current

    active = data.get("active")
    if isinstance(active, dict):
        name = active.get("name")
        if isinstance(name, str) and name:
            return name

    return None


def _enrich_from_remote(
    snapshot: HermesRuntimeSnapshot,
    client: HermesRuntimeClient,
) -> HermesRuntimeSnapshot:
    """Enrich an existing local snapshot from authenticated Hermes APIs."""

    try:
        status = client.status()
        profiles = client.profiles()
        active = client.active_profile()
    except Exception:
        # Local discovery remains the authoritative fallback.
        return snapshot

    version = _remote_version(status)
    if version:
        snapshot.version = version

    profile_names = _remote_profile_names(profiles)
    if profile_names:
        snapshot.profile_names = profile_names

    current_profile = _remote_current_profile(active)
    if current_profile:
        snapshot.current_profile = current_profile

    return snapshot


def get_hermes_runtime_snapshot() -> HermesRuntimeSnapshot:
    snapshot = _discover_runtime()

    client = HermesRuntimeClient.from_environment()
    if client is None:
        return snapshot

    return _enrich_from_remote(snapshot, client)


__all__ = [
    "HermesProfileInfo",
    "HermesRuntimeSnapshot",
    "get_hermes_runtime_snapshot",
]
