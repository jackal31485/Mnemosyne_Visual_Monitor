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
    # Query helpers mirroring the DAO API – no write methods.
    # ------------------------------------------------------------------

    def list_promoted(self):
        """Return a list of IDs of promoted entries that are not revoked."""
        conn = self._dao.conn
        cur = conn.execute(
            "SELECT id FROM collective_entries WHERE is_promoted=1 AND is_revoked=0 ORDER BY id"
        )
        return [row["id"] for row in cur.fetchall()]

    def get_by_id(self, entry_id: int):  # pragma: no cover – thin wrapper
        """Return the record tuple for ``entry_id``.

        The DAO’s :meth:`CollectiveDAO.get_by_id` already returns a 9‑field tuple matching the legacy tests; we simply forward it.
        """
        return self._dao.get_by_id(entry_id)

    def find_by_source(self, src: str, orig_mem: str):
        """Return the first matching entry for ``src`` and ``orig_mem``.
        Mirrors :meth:`CollectiveDAO.get_by_source`.
        """
        return self._dao.get_by_source(src, orig_mem)

    # ------------------------------------------------------------------
    # Ensure interface is *read‑only* by not exposing any mutating methods.
    # The DAO instance can be wrapped if needed in the future.
    # ------------------------------------------------------------------
