"""Phase 10J derived entity and relationship intelligence rebuild.

This module orchestrates the derived-intelligence pipeline while preserving
the authoritative collective memory and provenance layer.

Pipeline:

    promoted collective entries
        -> entity mentions
        -> canonical entity bootstrap
        -> explicit entity resolutions
        -> entity evidence
        -> relationship extraction
        -> relationship evidence

Only derived tables are rebuilt. Source Hermes databases and the authoritative
collective lifecycle/provenance records are never modified.
"""

from __future__ import annotations

from dataclasses import dataclass
import sqlite3
import uuid

from src.domain.collective import CollectiveDAO
from src.domain.entities import EntityDAO
from src.domain.entity_evidence import EntityEvidenceDAO
from src.domain.entity_mentions import EntityMentionDAO
from src.domain.entity_resolutions import EntityResolutionDAO
from src.domain.memory_gateway import MemoryGateway
from src.domain.relationship_evidence import RelationshipEvidenceDAO
from src.domain.relationships import RelationshipDAO
from src.services.entity_extraction_service import (
    EntityExtractionReport,
    extract_entities,
)
from src.services.entity_resolution import normalize_entity_name, resolve_and_record
from src.services.relationship_extraction_service import (
    RelationshipExtractionReport,
    extract_and_record_relationships,
)


ENTITY_NAMESPACE = uuid.UUID("6e6d8c6d-6f6a-4a0f-9d20-2e7f4d5a10a1")
EVIDENCE_NAMESPACE = uuid.UUID("c7a0d8f1-1b35-4e0c-a0f4-7f3d1a9b2c11")


@dataclass(frozen=True)
class EntityBootstrapReport:
    """Summary of canonical entities bootstrapped from unresolved mentions."""

    mentions_examined: int
    entities_created: int
    entities_existing: int
    resolutions_created: int
    resolutions_existing: int
    ambiguous: int
    failures: tuple[str, ...]


@dataclass(frozen=True)
class EntityRelationshipRebuildReport:
    """Complete deterministic derived-intelligence rebuild report."""

    entity_extraction: EntityExtractionReport
    entity_bootstrap: EntityBootstrapReport
    relationship_extraction: RelationshipExtractionReport


def _stable_entity_id(
    canonical_name: str,
    entity_type: str,
) -> str:
    """Return a stable entity ID for normalized name/type identity."""
    key = f"{entity_type.casefold()}|{normalize_entity_name(canonical_name)}"
    return str(uuid.uuid5(ENTITY_NAMESPACE, key))


def _stable_evidence_id(
    entity_id: str,
    collective_entry_id: int,
    source_memory_id: str,
    source_profile: str,
    original_mention: str,
    extraction_method: str,
) -> str:
    """Return a stable identifier for one entity evidence record."""
    key = "|".join(
        (
            entity_id,
            str(collective_entry_id),
            source_memory_id,
            source_profile,
            original_mention,
            extraction_method,
        )
    )
    return str(uuid.uuid5(EVIDENCE_NAMESPACE, key))


def _clear_derived_tables(
    collective_dao: CollectiveDAO,
) -> None:
    """Remove only rebuildable derived intelligence.

    The authoritative collective entries, provenance, promotion state, and
    revocation state are deliberately untouched.
    """
    conn = collective_dao.conn

    # Evidence is removed before the records it describes.
    for table in (
        "relationship_evidence",
        "relationships",
        "entity_evidence",
        "entity_resolutions",
        "entity_mentions",
        "entities",
    ):
        conn.execute(f"DELETE FROM {table}")

    conn.commit()


def _bootstrap_entities(
    *,
    mention_dao: EntityMentionDAO,
    entity_dao: EntityDAO,
    resolution_dao: EntityResolutionDAO,
    evidence_dao: EntityEvidenceDAO,
) -> EntityBootstrapReport:
    """Bootstrap canonical entities and explicitly resolve their mentions.

    The existing resolver remains unchanged: it never creates entities.
    This orchestration layer creates a canonical entity only for a mention
    whose exact normalized name/type has no active canonical match.

    Existing ambiguous decisions remain ambiguous; no silent merge occurs.
    """
    mentions = mention_dao.list()

    mentions_examined = 0
    entities_created = 0
    entities_existing = 0
    resolutions_created = 0
    resolutions_existing = 0
    ambiguous = 0
    failures: list[str] = []

    for mention in mentions:
        mention_id = str(mention["mention_id"])
        mentions_examined += 1

        existing_resolution = resolution_dao.get_for_mention(mention_id)
        if existing_resolution is not None:
            resolutions_existing += 1

            if existing_resolution["decision"] == "ambiguous":
                ambiguous += 1

            continue

        try:
            normalized_name = normalize_entity_name(
                mention["mention_text"]
            )
            entity_type = str(mention["entity_type"])

            candidates = [
                entity
                for entity in entity_dao.list(
                    entity_type=entity_type,
                    status="active",
                )
                if normalize_entity_name(entity["canonical_name"])
                == normalized_name
            ]

            if len(candidates) > 1:
                result = resolve_and_record(
                    mention_dao,
                    entity_dao,
                    resolution_dao,
                    mention_id=mention_id,
                )
                resolutions_created += 1
                ambiguous += 1
                continue

            if len(candidates) == 1:
                entity_id = candidates[0]["entity_id"]
                entities_existing += 1
            else:
                entity_id = _stable_entity_id(
                    mention["mention_text"],
                    entity_type,
                )

                entity_dao.create(
                    mention["mention_text"].strip(),
                    entity_type,
                    entity_id=entity_id,
                    confidence=mention["confidence"],
                    metadata={
                        "bootstrap_method": "phase-10j-deterministic-v1",
                        "normalized_name": normalized_name,
                        "original_mention": mention["mention_text"],
                    },
                )
                entities_created += 1

            result = resolve_and_record(
                mention_dao,
                entity_dao,
                resolution_dao,
                mention_id=mention_id,
            )

            resolutions_created += 1

            if result.decision == "ambiguous":
                ambiguous += 1
                continue

            if result.decision != "same_entity":
                failures.append(
                    f"{mention_id}: expected same_entity, "
                    f"got {result.decision}"
                )
                continue

            resolved_entity_id = result.proposed_entity_id
            if not isinstance(resolved_entity_id, str):
                failures.append(
                    f"{mention_id}: resolution has no entity ID"
                )
                continue

            evidence_id = _stable_evidence_id(
                resolved_entity_id,
                int(mention["collective_entry_id"]),
                str(mention["source_memory_id"]),
                str(mention["source_profile"]),
                str(mention["mention_text"]),
                str(mention["extraction_method"]),
            )

            evidence_dao.add(
                evidence_id=evidence_id,
                entity_id=resolved_entity_id,
                collective_entry_id=int(
                    mention["collective_entry_id"]
                ),
                source_memory_id=str(mention["source_memory_id"]),
                source_profile=str(mention["source_profile"]),
                original_mention=str(mention["mention_text"]),
                extraction_method=str(mention["extraction_method"]),
                confidence=mention["confidence"],
            )

        except (KeyError, ValueError, TypeError, sqlite3.Error) as exc:
            failures.append(f"{mention_id}: {exc}")

    return EntityBootstrapReport(
        mentions_examined=mentions_examined,
        entities_created=entities_created,
        entities_existing=entities_existing,
        resolutions_created=resolutions_created,
        resolutions_existing=resolutions_existing,
        ambiguous=ambiguous,
        failures=tuple(failures),
    )


def rebuild_entity_relationship_intelligence(
    *,
    collective_dao: CollectiveDAO,
    entity_dao: EntityDAO,
    mention_dao: EntityMentionDAO,
    resolution_dao: EntityResolutionDAO,
    entity_evidence_dao: EntityEvidenceDAO,
    relationship_dao: RelationshipDAO,
    relationship_evidence_dao: RelationshipEvidenceDAO,
    gateway: MemoryGateway,
) -> EntityRelationshipRebuildReport:
    """Rebuild all Phase 10 derived entity/relationship intelligence.

    The operation is destructive only to derived tables. It does not modify
    collective entries, collective provenance, promotion/revocation state, or
    source profile databases.

    The resulting entity identities are deterministic for normalized
    name/type pairs, allowing repeated rebuilds to reproduce canonical IDs.
    """
    collective_dao.ensure_schema()
    entity_dao.ensure_schema()
    mention_dao.ensure_schema()
    resolution_dao.ensure_schema()
    entity_evidence_dao.ensure_schema()
    relationship_dao.ensure_schema()
    relationship_evidence_dao.ensure_schema()

    _clear_derived_tables(collective_dao)

    extraction_report = extract_entities(
        collective_dao,
        mention_dao,
        gateway,
    )

    bootstrap_report = _bootstrap_entities(
        mention_dao=mention_dao,
        entity_dao=entity_dao,
        resolution_dao=resolution_dao,
        evidence_dao=entity_evidence_dao,
    )

    relationship_report = extract_and_record_relationships(
        mention_dao=mention_dao,
        resolution_dao=resolution_dao,
        relationship_dao=relationship_dao,
        evidence_dao=relationship_evidence_dao,
        gateway=gateway,
    )

    return EntityRelationshipRebuildReport(
        entity_extraction=extraction_report,
        entity_bootstrap=bootstrap_report,
        relationship_extraction=relationship_report,
    )
