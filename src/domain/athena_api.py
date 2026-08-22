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

    # ------------------------------------------------------------------
    # Phase 5C – similarity search by embedding.
    # ------------------------------------------------------------------
    def search_by_embedding(self, vector: List[float], top_n: int) -> List[int]:
        """Return promoted, non‑revoked entries whose embedded vectors
        are nearest to ``vector`` using cosine similarity.

        The method filters out entries with a NULL or invalid embedding.  It
        does not expose the raw embedding in its output -- callers receive only IDs
        sorted from highest to lowest similarity.
        """
        import math, pickle

        # Ensure list-like and compute query norm.
        try:
            q = [float(v) for v in vector]
        except Exception as e:  # pragma: no cover - defensive
            raise ValueError("query vector must be iterable of numbers")
        denom_q_sq = sum(x * x for x in q)
        if denom_q_sq == 0:
            # Zero query vector: consider all promoted & non‑revoked entries that
            # have a *valid* embedding.  Entries whose embedding is a zero
            # vector rank before those with any non‑zero vector.
            cur = self._iface._dao.conn.execute(
                "SELECT id, embedding FROM collective_entries WHERE is_promoted=1 AND is_revoked=0"
            )
            zero_ids: List[int] = []
            other_ids: List[int] = []
            for row in cur.fetchall():
                eid = int(row["id"] if isinstance(row, dict) else row[0])
                blob = row["embedding"] if isinstance(row, dict) else row[1]
                if blob is None:
                    continue
                try:
                    emb_vec = pickle.loads(blob)
                except Exception:
                    continue  # malformed or unreadable embedding
                # skip entries with mismatched dimensionality
                if len(emb_vec) != len(q):
                    continue
                if all(float(v) == 0.0 for v in emb_vec):
                    zero_ids.append(eid)
                else:
                    other_ids.append(eid)

            # No valid entries → empty result
            if not zero_ids and not other_ids:
                return []
            # Sort each group for deterministic output
            zero_ids.sort()
            other_ids.sort()
            combined = zero_ids + other_ids
            return combined[:top_n]
        denom_q = math.sqrt(denom_q_sq)

        # Gather non‑zero query candidates
        cur = self._iface._dao.conn.execute(
            "SELECT id, embedding FROM collective_entries WHERE is_promoted=1 AND is_revoked=0",
        )
        candidates: List[tuple[int, float]] = []
        for row in cur.fetchall():
            eid = int(row["id"])
            blob = row["embedding"]
            if blob is None:
                continue
            try:
                r = pickle.loads(blob)
                # Normalize vector type; accept list/tuple of floats.
                r_vec = [float(v) for v in r]
            except Exception:  # pragma: no cover
                continue  # malformed encoding – skip silently
            if len(r_vec) != len(q):
                continue
            denom_r_sq = sum(x * x for x in r_vec)
            if denom_r_sq == 0:
                continue
            denom_r = math.sqrt(denom_r_sq)
            dot = sum(a * b for a, b in zip(q, r_vec))
            similarity = dot / (denom_q * denom_r)
            candidates.append((eid, similarity))

        # Sort and slice
        candidates.sort(key=lambda x: -x[1])
        return [cid for cid, _ in candidates[:top_n]]

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
