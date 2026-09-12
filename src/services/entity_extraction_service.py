"""Governed entity-mention extraction from collective memories.

Phase 10B.2 connects the deterministic entity extractor to the authoritative
collective memory layer.

Only promoted, non-revoked collective entries are eligible. Source memory
content is retrieved through MemoryGateway, and only derived entity-mention
metadata is persisted to collective.db.

This service does not resolve entities, create canonical entities, modify
source Mnemosyne databases, or bypass collective lifecycle governance.
"""

from __future__ import annotations

from dataclasses import dataclass
import sqlite3
import uuid

from src.domain.collective import CollectiveDAO
from src.domain.entity_mentions import EntityMentionDAO
from src.domain.memory_gateway import MemoryGateway
from src.services.entity_extraction import (
    DeterministicEntityExtractor,
)


MENTION_NAMESPACE = uuid.UUID(
    "b4f6f5e1-8f43-4d73-a5d9-6f4b2c91e7a2"
)


def _stable_mention_id(
    *,
    collective_entry_id: int,
    source_memory_id: str,
    source_profile: str,
    mention_text: str,
    entity_type: str,
    extraction_method: str,
) -> str:
    """Return a deterministic ID for one extracted mention."""
    key = "|".join(
        (
            str(collective_entry_id),
            source_memory_id,
            source_profile,
            mention_text,
            entity_type,
            extraction_method,
        )
    )
    return str(uuid.uuid5(MENTION_NAMESPACE, key))


@dataclass(frozen=True)
class EntityExtractionFailure:
    """A collective entry whose source memory could not be processed."""

    entry_id: int
    source_profile: str
    origin_memory_id: str
    reason: str


@dataclass(frozen=True)
class EntityExtractionReport:
    """Deterministic summary of an entity-mention extraction run."""

    processed: int
    mentions_created: int
    mentions_existing: int
    skipped: int
    failures: tuple[EntityExtractionFailure, ...]


def extract_entities(
    collective_dao: CollectiveDAO,
    mention_dao: EntityMentionDAO,
    gateway: MemoryGateway,
    extractor: DeterministicEntityExtractor | None = None,
) -> EntityExtractionReport:
    """Extract and persist entity mentions for eligible collective entries.

    Entries are processed in ascending collective-entry ID order.

    Eligibility is authoritative:
      * is_promoted = 1
      * is_revoked = 0

    Source content is retrieved only through ``gateway``. Missing source
    memories are recorded as failures and do not prevent other entries from
    being processed.

    Repeated extraction is idempotent because the mention table's uniqueness
    constraint prevents duplicate derived mentions.
    """

    extractor = extractor or DeterministicEntityExtractor()

    rows = collective_dao.conn.execute(
        """
        SELECT id, source_profile, origin_memory_id
        FROM collective_entries
        WHERE is_promoted = 1
          AND is_revoked = 0
        ORDER BY id ASC
        """
    ).fetchall()

    processed = 0
    mentions_created = 0
    mentions_existing = 0
    skipped = 0
    failures: list[EntityExtractionFailure] = []

    for row in rows:
        entry_id = int(row["id"])
        source_profile = str(row["source_profile"])
        origin_memory_id = str(row["origin_memory_id"])

        try:
            content = gateway.get_memory(
                source_profile,
                origin_memory_id,
            )
        except (KeyError, OSError, sqlite3.Error) as exc:
            failures.append(
                EntityExtractionFailure(
                    entry_id=entry_id,
                    source_profile=source_profile,
                    origin_memory_id=origin_memory_id,
                    reason=f"source memory unavailable: {exc}",
                )
            )
            continue

        mentions = extractor.extract(content)
        processed += 1

        if not mentions:
            skipped += 1
            continue

        for mention in mentions:
            try:
                mention_dao.add(
                    collective_entry_id=entry_id,
                    source_memory_id=origin_memory_id,
                    source_profile=source_profile,
                    mention_text=mention.mention_text,
                    entity_type=mention.entity_type,
                    confidence=mention.confidence,
                    extraction_method=mention.extraction_method,
                    mention_id=_stable_mention_id(
                        collective_entry_id=entry_id,
                        source_memory_id=origin_memory_id,
                        source_profile=source_profile,
                        mention_text=mention.mention_text,
                        entity_type=mention.entity_type,
                        extraction_method=mention.extraction_method,
                    ),
                )
            except sqlite3.IntegrityError:
                mentions_existing += 1
            else:
                mentions_created += 1

    return EntityExtractionReport(
        processed=processed,
        mentions_created=mentions_created,
        mentions_existing=mentions_existing,
        skipped=skipped,
        failures=tuple(failures),
    )
