# Runtime discovery for Hermes.
# Public API:
#   - get_hermes_runtime_snapshot()
#   - HermesProfileInfo
#   - HermesRuntimeSnapshot

from __future__ import annotations

# Import the core utilities from the same package. They expose the data classes and helper function.
try:
    # The module may be imported as part of an installed package
    from src.discovery.utils import (
        HermesProfileInfo,
        HermesRuntimeSnapshot,
        get_hermes_runtime_snapshot as _core_get_snapshot,
    )
except Exception:  # pragma: no cover – fallback for standalone execution
    from .utils import (
        HermesProfileInfo,
        HermesRuntimeSnapshot,
        get_hermes_runtime_snapshot as _core_get_snapshot,
    )

# Wrapper that matches the name expected by tests and existing callers.
def get_hermes_runtime_snapshot():  # pragma: no cover – thin wrapper
    return _core_get_snapshot()

__all__ = ["HermesProfileInfo", "HermesRuntimeSnapshot", "get_hermes_runtime_snapshot"]
