"""Back-fill missing embeddings for collective entries.

This service retrieves source memory through the MemoryGateway, generates
embeddings through the established domain embedding abstraction, and stores
only the resulting embedding in the collective database.

Raw source memory content is never persisted to the collective database.
"""

from __future__ import annotations

from src.domain.collective import CollectiveDAO
from src.domain.embedding_generator import (
    SentenceTransformerEncoder,
    embed_sanitized,
)
from src.domain.memory_gateway import MemoryGateway


# Backward-compatible name retained for existing callers/tests.
# The implementation remains the established domain embed_sanitized()
# helper; this is deliberately an alias, not a second embedding path.
_embed_text = embed_sanitized


def backfill(
    dao: CollectiveDAO,
    gateway: MemoryGateway,
) -> list[tuple[int, str, str]]:
    """Generate embeddings for collective entries that do not have one.

    Entries whose source memory cannot be retrieved are skipped and returned
    in the failure list. Already-embedded entries are left untouched.

    Returns
    -------
    list[tuple[int, str, str]]
        ``(entry_id, source_profile, origin_memory_id)`` for memories that
        could not be retrieved.
    """
    failures: list[tuple[int, str, str]] = []

    # Load the local embedding model exactly once for the complete backfill.
    # SentenceTransformerEncoder uses local_files_only=True, so this never
    # downloads from Hugging Face during normal operation.
    encoder = SentenceTransformerEncoder()

    cursor = dao.conn.execute(
        """
        SELECT id, source_profile, origin_memory_id
        FROM collective_entries
        WHERE embedding IS NULL
        ORDER BY id
        """
    )

    for row in cursor:
        entry_id = int(row["id"])
        source_profile = row["source_profile"]
        origin_memory_id = row["origin_memory_id"]

        try:
            sanitized_content = gateway.get_memory(
                source_profile,
                origin_memory_id,
            )
        except KeyError:
            failures.append(
                (entry_id, source_profile, origin_memory_id)
            )
            print(
                f"Skipping entry {entry_id}: "
                f"missing memo ({source_profile}, {origin_memory_id})"
            )
            continue

        embedding = encoder.generate(sanitized_content)
        dao.update_entry_embedding(entry_id, embedding)

    return failures
