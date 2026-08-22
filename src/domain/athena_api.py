from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List, Tuple

from .athena_interface import AthenaCollectiveInterface

# ---------------------------------------------------------------------------
# Read‑only Athena API – thin wrapper around AthenaCollectiveInterface.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SanitizedMemory:
    """Placeholder for a sanitized summary of a private Mnemosyne memory.

    The real gateway will provide a meaningful title/abstract.  Until then the
    fields contain static markers so that callers can rely on a stable type.
    """
    id: str
    title: str
    abstract: str


class AthenaAPI:
    def __init__(self, interface: AthenaCollectiveInterface | None = None) -> None:
        # Dependency injection – default to the global singleton style used in tests.
        self._iface = interface or AthenaCollectiveInterface()

    def get_entry(self, entry_id: int) -> Tuple[int, ...] | None:
        """Return a promoted & not‑revoked collective tuple; otherwise ``None``."""
        return self._iface.get_by_id(entry_id)

    def list_entries(self, profile: str | None = None) -> List[int]:
        ids = self._iface.list_promoted()
        if profile is None:
            return ids
        # Filter by source_profile using the underlying DAO because the interface has no filter.
        filtered: List[int] = []
        for eid in ids:
            row = self._iface.get_by_id(eid)
            if row and row[1] == profile:
                filtered.append(eid)
        return filtered

    def find_by_source(self, src: str, orig_mem: str) -> Tuple[int, ...] | None:
        return self._iface.find_by_source(src, orig_mem)

    def resolve_memory(self, origin_memory_id: str) -> SanitizedMemory | None:
        # Find a promoted, non‑revoked entry that references this origin id.
        for eid in self._iface.list_promoted():
            row = self._iface.get_by_id(eid)
            if row and row[2] == origin_memory_id:
                # entry found – return placeholder payload
                return SanitizedMemory(
                    id=str(eid),
                    title="[placeholder title]",
                    abstract="[placeholder abstract]"
                )
        return None

# End of file
