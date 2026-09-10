"""
Athena’s read‑only interface to the collective knowledge base.

The design (Phase 4A) requires Athena to see only promoted, non‑revoked
references and their provenance metadata.  It must never return or modify private
Mnemosyne memory content.

Implementation notes:
* A thin wrapper around :class:`src.domain.collective.CollectiveDAO` is used.
* No mutating helpers are exposed – any attempt to alter data would have to use the underlying DAO directly.
* The interface mirrors only the read surface needed by the specification.
"""

from __future__ import annotations

from .collective import CollectiveDAO

__all__ = ["AthenaCollectiveInterface"]

class AthenaCollectiveInterface:
    """Read‑only API for Athena.
    The class lazily initialises a :class:`CollectiveDAO` instance and
    forwards read operations.  All methods are intentionally immutable – no
    mutation helpers are exposed.
    """

    def __init__(self) -> None:
        self._dao = CollectiveDAO()
        self._dao.ensure_schema()

    # ------------------------------------------------------------------
    # Primitive query helpers mirroring the DAO API – no write methods.
    # ------------------------------------------------------------------

    def list_promoted(self):
        """Return a list of IDs of promoted entries that are not revoked."""
        cur = self._dao.conn.execute(
            "SELECT id FROM collective_entries WHERE is_promoted=1 AND is_revoked=0 ORDER BY id"
        )
        return [row["id"] for row in cur.fetchall()]

    def resolve_source_profile(self, profile: str) -> list[str]:
        """Resolve a Browser/local profile name to governed collective identities.

        Qualified identities such as ``agent-id:athena`` are returned unchanged.
        Short local profile names such as ``athena`` resolve to all matching
        promoted, non-revoked collective source identities.
        """
        value = str(profile or "").strip()
        if not value:
            return []

        if ":" in value:
            cur = self._dao.conn.execute(
                """
                SELECT source_profile
                FROM collective_entries
                WHERE source_profile = ?
                  AND is_promoted = 1
                  AND is_revoked = 0
                GROUP BY source_profile
                """,
                (value,),
            )
        else:
            cur = self._dao.conn.execute(
                """
                SELECT source_profile
                FROM collective_entries
                WHERE source_profile LIKE ?
                  AND is_promoted = 1
                  AND is_revoked = 0
                GROUP BY source_profile
                ORDER BY source_profile
                """,
                (f"%:{value}",),
            )

        return [str(row["source_profile"]) for row in cur.fetchall()]

    def get_by_id(self, entry_id: int):
        """Return the 9‑field tuple **only** when promoted and NOT revoked.

        Visibility check is performed on the promotion/revocation flags before exposing
        the data. Raw SQLite rows are returned to callers unchanged except for
        filtering.
        """
        record = self._dao.get_by_id(entry_id)
        if not record:
            return None
        cur = self._dao.conn.execute(
            "SELECT is_promoted, is_revoked FROM collective_entries WHERE id = ?", (entry_id,)
        )
        row = cur.fetchone()
        if not row or not bool(row["is_promoted"]):
            return None
        if bool(row["is_revoked"]):
            return None
        return record

    def find_by_source(self, src: str, orig_mem: str):
        """Return the first matching entry **if** promoted and NOT revoked.

        The DAO returns a 9‑field tuple.  Visibility logic mirrors :meth:`get_by_id`.
        """
        record = self._dao.get_by_source(src, orig_mem)
        if not record:
            return None
        entry_id = int(record[0])
        cur = self._dao.conn.execute(
            "SELECT is_promoted, is_revoked FROM collective_entries WHERE id = ?", (entry_id,)
        )
        row = cur.fetchone()
        if not row or not bool(row["is_promoted"]):
            return None
        if bool(row["is_revoked"]):
            return None
        return record

    # No mutating methods exposed – the interface remains read‑only.
