"""Batch service for governed relationship extraction.

Phase 10F.3 connects deterministic relationship extraction to resolved
collective entities while preserving provenance, qualified profile identity,
lifecycle governance, and rebuildability.

This service never modifies source memories and never creates canonical
entities.
"""

from __future__ import annotations

from dataclasses import dataclass
import sqlite3
import uuid

from src.domain.entity_mentions import EntityMentionDAO
from src.domain.entity_resolutions import EntityResolutionDAO
from src.domain.relationship_evidence import RelationshipEvidenceDAO
from src.domain.relationships import RelationshipDAO
from src.services.relationship_classification import classify_relationship
from src.services.relationship_extraction import (
    EntityMentionInput,
    RelationshipCandidate,
    extract_relationships,
)
from src.domain.memory_gateway import MemoryGateway


RELATIONSHIP_NAMESPACE = uuid.UUID(
    "7a1e5c93-42d8-4f6b-b9e7-1c3d8a5f2046"
)

RELATIONSHIP_EVIDENCE_NAMESPACE = uuid.UUID(
    "9d4e7b21-6c53-4a8f-b2e1-5f9c3d7a1846"
)


def _stable_relationship_id(
    *,
    subject_entity_id: str,
    predicate: str,
    object_entity_id: str,
    relationship_kind: str,
) -> str:
    """Return a deterministic identity for a relationship tuple."""
    key = "|".join(
        (
            subject_entity_id,
            predicate,
            object_entity_id,
            relationship_kind,
        )
    )
    return str(uuid.uuid5(RELATIONSHIP_NAMESPACE, key))


def _stable_relationship_evidence_id(
    *,
    relationship_id: str,
    collective_entry_id: int,
    source_memory_id: str,
    source_profile: str,
    evidence_reference: str,
    extraction_method: str,
) -> str:
    """Return a deterministic identity for relationship evidence."""
    key = "|".join(
        (
            relationship_id,
            str(collective_entry_id),
            source_memory_id,
            source_profile,
            evidence_reference,
            extraction_method,
        )
    )
    return str(uuid.uuid5(RELATIONSHIP_EVIDENCE_NAMESPACE, key))


@dataclass(frozen=True)
class RelationshipExtractionFailure:
    collective_entry_id: int
    source_memory_id: str
    source_profile: str
    error: str


@dataclass(frozen=True)
class RelationshipExtractionReport:
    processed: int
    relationships_created: int
    relationships_existing: int
    evidence_created: int
    evidence_existing: int
    skipped: int
    failures: tuple[RelationshipExtractionFailure, ...]


def _group_mentions(
    mentions: list[dict],
) -> dict[int, list[dict]]:
    grouped: dict[int, list[dict]] = {}

    for mention in mentions:
        grouped.setdefault(
            int(mention["collective_entry_id"]),
            [],
        ).append(mention)

    return grouped


def _resolved_entity_id(
    mention: dict,
    resolution_dao: EntityResolutionDAO,
) -> str | None:
    resolution = resolution_dao.get_for_mention(mention["mention_id"])

    if resolution is None:
        return None

    if resolution["decision"] != "same_entity":
        return None

    entity_id = resolution["proposed_entity_id"]

    if not isinstance(entity_id, str) or not entity_id.strip():
        return None

    return entity_id


def _evidence_reference(
    candidate: RelationshipCandidate,
    *,
    subject_entity_id: str,
    object_entity_id: str,
) -> str:
    """Build a deterministic metadata-only evidence reference."""
    return (
        f"relationship-v1:"
        f"{subject_entity_id}|"
        f"{candidate.predicate}|"
        f"{object_entity_id}|"
        f"{candidate.relationship_kind}"
    )


def extract_and_record_relationships(
    *,
    mention_dao: EntityMentionDAO,
    resolution_dao: EntityResolutionDAO,
    relationship_dao: RelationshipDAO,
    evidence_dao: RelationshipEvidenceDAO,
    gateway: MemoryGateway,
) -> RelationshipExtractionReport:
    """Extract and persist governed relationships from resolved mentions.

    Only promoted/non-revoked source memories should have corresponding
    mentions, because entity extraction already enforces that boundary.
    Existing relationships and evidence are preserved, making repeated runs
    idempotent.

    Canonical entities are never created or modified. Source memories are
    read-only through the gateway.
    """
    processed = 0
    relationships_created = 0
    relationships_existing = 0
    evidence_created = 0
    evidence_existing = 0
    skipped = 0
    failures: list[RelationshipExtractionFailure] = []

    mentions = mention_dao.list()
    grouped = _group_mentions(mentions)

    for collective_entry_id in sorted(grouped):
        entry_mentions = grouped[collective_entry_id]

        # Relationship extraction requires a single source identity and
        # memory for the grouped mention set.
        source_profiles = {
            mention["source_profile"]
            for mention in entry_mentions
        }
        source_memory_ids = {
            mention["source_memory_id"]
            for mention in entry_mentions
        }

        if len(source_profiles) != 1 or len(source_memory_ids) != 1:
            failures.append(
                RelationshipExtractionFailure(
                    collective_entry_id=collective_entry_id,
                    source_memory_id="",
                    source_profile="",
                    error="mentions for one collective entry have mixed sources",
                )
            )
            skipped += 1
            continue

        source_profile = next(iter(source_profiles))
        source_memory_id = next(iter(source_memory_ids))

        processed += 1

        try:
            text = gateway.get_memory(
                source_profile,
                source_memory_id,
            )

            mention_inputs = [
                EntityMentionInput(
                    mention_text=mention["mention_text"],
                    entity_type=mention["entity_type"],
                )
                for mention in entry_mentions
            ]

            candidates = extract_relationships(
                text,
                mention_inputs,
            )

            for candidate in candidates:
                classified = classify_relationship(candidate)

                subject_mention = next(
                    (
                        mention
                        for mention in entry_mentions
                        if mention["mention_text"].casefold()
                        == classified.subject_mention.casefold()
                    ),
                    None,
                )
                object_mention = next(
                    (
                        mention
                        for mention in entry_mentions
                        if mention["mention_text"].casefold()
                        == classified.object_mention.casefold()
                    ),
                    None,
                )

                if subject_mention is None or object_mention is None:
                    skipped += 1
                    continue

                subject_entity_id = _resolved_entity_id(
                    subject_mention,
                    resolution_dao,
                )
                object_entity_id = _resolved_entity_id(
                    object_mention,
                    resolution_dao,
                )

                # Never guess unresolved entity identity.
                if subject_entity_id is None or object_entity_id is None:
                    skipped += 1
                    continue

                existing = relationship_dao.list(
                    subject_entity_id=subject_entity_id,
                    object_entity_id=object_entity_id,
                    predicate=classified.predicate,
                    relationship_kind=classified.relationship_kind,
                )

                if existing:
                    relationship_id = existing[0]["relationship_id"]
                    relationships_existing += 1
                else:
                    relationship_id = relationship_dao.create(
                        subject_entity_id=subject_entity_id,
                        predicate=classified.predicate,
                        object_entity_id=object_entity_id,
                        confidence=classified.confidence,
                        relationship_kind=classified.relationship_kind,
                        relationship_id=_stable_relationship_id(
                            subject_entity_id=subject_entity_id,
                            predicate=classified.predicate,
                            object_entity_id=object_entity_id,
                            relationship_kind=classified.relationship_kind,
                        ),
                        metadata={
                            "extraction_method": classified.extraction_method,
                            "classification_method": (
                                classified.classification_method
                            ),
                            "source_profile": source_profile,
                            "source_memory_id": source_memory_id,
                            "collective_entry_id": collective_entry_id,
                        },
                    )
                    relationships_created += 1

                evidence_reference = _evidence_reference(
                    candidate,
                    subject_entity_id=subject_entity_id,
                    object_entity_id=object_entity_id,
                )

                existing_evidence = evidence_dao.list(
                    relationship_id=relationship_id,
                )

                duplicate_evidence = any(
                    evidence["collective_entry_id"] == collective_entry_id
                    and evidence["source_memory_id"] == source_memory_id
                    and evidence["source_profile"] == source_profile
                    and evidence["evidence_reference"]
                    == evidence_reference
                    and evidence["extraction_method"]
                    == classified.extraction_method
                    for evidence in existing_evidence
                )

                if duplicate_evidence:
                    evidence_existing += 1
                else:
                    evidence_dao.add(
                        relationship_id=relationship_id,
                        collective_entry_id=collective_entry_id,
                        source_memory_id=source_memory_id,
                        source_profile=source_profile,
                        evidence_reference=evidence_reference,
                        extraction_method=classified.extraction_method,
                        confidence=classified.confidence,
                        evidence_id=_stable_relationship_evidence_id(
                            relationship_id=relationship_id,
                            collective_entry_id=collective_entry_id,
                            source_memory_id=source_memory_id,
                            source_profile=source_profile,
                            evidence_reference=evidence_reference,
                            extraction_method=classified.extraction_method,
                        ),
                    )
                    evidence_created += 1

        except (KeyError, ValueError, TypeError, sqlite3.Error, OSError) as exc:
            failures.append(
                RelationshipExtractionFailure(
                    collective_entry_id=collective_entry_id,
                    source_memory_id=source_memory_id,
                    source_profile=source_profile,
                    error=str(exc),
                )
            )
            skipped += 1

    return RelationshipExtractionReport(
        processed=processed,
        relationships_created=relationships_created,
        relationships_existing=relationships_existing,
        evidence_created=evidence_created,
        evidence_existing=evidence_existing,
        skipped=skipped,
        failures=tuple(failures),
    )
