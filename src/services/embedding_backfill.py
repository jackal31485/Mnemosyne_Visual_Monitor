"""Back‑fill missing embeddings for collective entries.

This module depends on `src.domain.embedding_generator` for a deterministic
*canonical* embedding function.  No runtime fallback that uses Python's random
hashing is present – any failure to import the generator raises an explicit
``ImportError``.

Only the public ``backfill`` function is exported, mirroring the legacy
API used in unit tests and integration flows.
"""

from __future__ import annotations

import logging
from typing import List, Tuple

from src.domain.collective import CollectiveDAO
from src.domain.embedding_generator import embed_sanitized  # guaranteed deterministic
from src.domain.memory_gateway import MemoryGateway

logger = logging.getLogger(__name__)

# Backward‑compatible alias used by older callers
_embed_text = embed_sanitized

def backfill(dao: CollectiveDAO, gateway: MemoryGateway) -> List[Tuple[int, str, str]]:
    """Generate embeddings for collective entries that lack them.

    Parameters
    ----------
    dao:
        Data access object providing read/write on the collective table.
    gateway:
        Reads raw memory content by (profile, id).

    Returns
    -------
    list[tuple[int,str,str]]
        The list of entries that could not be processed due to missing
        background memory.  Each tuple contains ``(id,
        source_profile, origin_memory_id)``.
    """
    failures: List[Tuple[int, str, str]] = []
    cursor = dao.conn.execute(
        """
        SELECT id, source_profile, origin_memory_id
        FROM collective_entries
        WHERE embedding IS NULL
        ORDER BY id
        """
    )
    for row in cursor:
        entry_id: int = int(row["id"])
        source_profile: str = row["source_profile"]
        origin_memory_id: str = row["origin_memory_id"]
        try:
            sanitized_content = gateway.get_memory(source_profile, origin_memory_id)
        except KeyError as exc:
            failures.append((entry_id, source_profile, origin_memory_id))
            logger.warning(
                "Skipping entry %s: missing memo (%s, %s) – %s",
                entry_id,
                source_profile,
                origin_memory_id,
                exc,
            )
            continue
        embedding = _embed_text(sanitized_content)
        dao.update_entry_embedding(entry_id, embedding)
    return failures
