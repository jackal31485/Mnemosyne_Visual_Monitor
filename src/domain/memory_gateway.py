"""
Memory Gateway protocol and an in‑memory test implementation.

The Mediation Plane must not perform any SQLite or filesystem access. This module defines the protocol used by the plane and provides a simple
`InMemoryMemoryGateway` for unit/ integration tests.
"""
from __future__ import annotations
from typing import Protocol, Dict, Any

class MemoryGateway(Protocol):
    """Protocol for retrieving a single memory entry belonging to a profile.

    The Mediation Plane will call ``get_memory(profile, memory_id)`` and expects a JSON‑serializable dictionary
    that represents the sanitized content of the source memory.  No database or file‑system access is performed by this interface.
    """

    def get_memory(self, profile: str, memory_id: str) -> Dict[str, Any]:
        ...

# ---------------------------------------------------------------------------
# In‑memory implementation for tests – not used in production code
# ---------------------------------------------------------------------------
class InMemoryMemoryGateway:
    """A simple gateway that stores memories in a nested dictionary.

    The internal store structure is ``_store[profile][memory_id]``.  Methods raise
    ``KeyError`` for unknown profiles or memory ids to mimic the behaviour
    expected by the tests.
    """

    def __init__(self, store: Dict[str, Dict[str, Dict[str, Any]]] | None = None):
        self._store = store if store is not None else {}

    def add_memory(self, profile: str, memory_id: str, content: Dict[str, Any]) -> None:
        self._store.setdefault(profile, {})[memory_id] = content

    def get_memory(self, profile: str, memory_id: str) -> Dict[str, Any]:
        try:
            return self._store[profile][memory_id]
        except KeyError as exc:
            # Provide a clear error message – the tests expect an exception for unknown data.
            raise KeyError(f"Memory {memory_id} not found for profile {profile}") from exc
