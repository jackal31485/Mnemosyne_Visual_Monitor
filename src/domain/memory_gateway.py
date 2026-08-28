"""Memory gateway abstraction.

The gateway provides controlled access to source memory content.  The real
application supplies the concrete implementation that reads the source
Mnemosyne profile store.  The in-memory implementation exists for tests.

The gateway itself does not write to the collective database and does not
change the read-only status of source Mnemosyne databases.
"""

from __future__ import annotations

from typing import Protocol


class MemoryGateway(Protocol):
    """Interface for retrieving source memory content."""

    def get_memory(self, profile: str, memory_id: str) -> str:
        """Return the sanitized source content for a memory."""
        ...


class InMemoryMemoryGateway:
    """In-memory gateway used by unit and integration tests.

    Memories are keyed by ``(profile, memory_id)`` so profile identity remains
    part of the lookup boundary.
    """

    def __init__(
        self,
        store: dict[tuple[str, str], str] | None = None,
    ) -> None:
        self.store: dict[tuple[str, str], str] = (
            dict(store) if store is not None else {}
        )

    def add_memory(
        self,
        profile: str,
        memory_id: str,
        content: str,
    ) -> None:
        """Add or replace a test memory."""
        self.store[(profile, memory_id)] = content

    def get_memory(
        self,
        profile: str,
        memory_id: str,
    ) -> str:
        """Retrieve a test memory or raise ``KeyError`` if unavailable."""
        key = (profile, memory_id)

        if key not in self.store:
            raise KeyError(
                f"Memory {memory_id} not found for profile {profile}"
            )

        return self.store[key]
