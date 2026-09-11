from __future__ import annotations

import sqlite3

from src.domain.entity_mentions import EntityMentionDAO
from src.domain.entity_resolutions import EntityResolutionDAO
from src.domain.relationship_evidence import RelationshipEvidenceDAO
from src.domain.relationships import RelationshipDAO
from src.domain.memory_gateway import InMemoryMemoryGateway
from src.services.relationship_extraction_service import (
    extract_and_record_relationships,
)


def _setup(tmp_path):
    mentions = EntityMentionDAO(tmp_path / "mentions.db")
    resolutions = EntityResolutionDAO(tmp_path / "resolutions.db")
    relationships = RelationshipDAO(tmp_path / "relationships.db")
    evidence = RelationshipEvidenceDAO(tmp_path / "evidence.db")

    mentions.ensure_schema()
    resolutions.ensure_schema()
    relationships.ensure_schema()
    evidence.ensure_schema()

    return mentions, resolutions, relationships, evidence


def _mention(
    dao,
    *,
    mention_id,
    entry_id,
    memory_id,
    profile,
    text,
):
    dao.add(
        mention_id=mention_id,
        collective_entry_id=entry_id,
        source_memory_id=memory_id,
        source_profile=profile,
        mention_text=text,
        entity_type="technology",
        confidence=0.95,
        extraction_method="deterministic-v1",
    )


def _resolve(
    dao,
    *,
    mention_id,
    entity_id,
):
    dao.create(
        mention_id=mention_id,
        proposed_entity_id=entity_id,
        decision="same_entity",
        confidence=1.0,
        resolution_method="normalized-name-v1",
    )


def test_explicit_relationship_is_persisted_with_evidence(tmp_path):
    mentions, resolutions, relationships, evidence = _setup(tmp_path)

    _mention(
        mentions,
        mention_id="m1",
        entry_id=1,
        memory_id="mem-1",
        profile="athena",
        text="Mnemosyne",
    )
    _mention(
        mentions,
        mention_id="m2",
        entry_id=1,
        memory_id="mem-1",
        profile="athena",
        text="FastAPI",
    )

    _resolve(resolutions, mention_id="m1", entity_id="entity-mnemosyne")
    _resolve(resolutions, mention_id="m2", entity_id="entity-fastapi")

    gateway = InMemoryMemoryGateway(
        {
            ("athena", "mem-1"): "Mnemosyne uses FastAPI.",
        }
    )

    report = extract_and_record_relationships(
        mention_dao=mentions,
        resolution_dao=resolutions,
        relationship_dao=relationships,
        evidence_dao=evidence,
        gateway=gateway,
    )

    assert report.processed == 1
    assert report.relationships_created == 1
    assert report.relationships_existing == 0
    assert report.evidence_created == 1
    assert report.evidence_existing == 0
    assert report.failures == ()

    rows = relationships.list()
    assert len(rows) == 1
    assert rows[0]["subject_entity_id"] == "entity-mnemosyne"
    assert rows[0]["predicate"] == "uses"
    assert rows[0]["object_entity_id"] == "entity-fastapi"
    assert rows[0]["relationship_kind"] == "explicit"

    evidence_rows = evidence.list()
    assert len(evidence_rows) == 1
    assert evidence_rows[0]["collective_entry_id"] == 1
    assert evidence_rows[0]["source_memory_id"] == "mem-1"
    assert evidence_rows[0]["source_profile"] == "athena"


def test_unresolved_subject_is_skipped(tmp_path):
    mentions, resolutions, relationships, evidence = _setup(tmp_path)

    _mention(
        mentions,
        mention_id="m1",
        entry_id=1,
        memory_id="mem-1",
        profile="athena",
        text="Mnemosyne",
    )
    _mention(
        mentions,
        mention_id="m2",
        entry_id=1,
        memory_id="mem-1",
        profile="athena",
        text="FastAPI",
    )

    _resolve(resolutions, mention_id="m2", entity_id="entity-fastapi")

    gateway = InMemoryMemoryGateway(
        {
            ("athena", "mem-1"): "Mnemosyne uses FastAPI.",
        }
    )

    report = extract_and_record_relationships(
        mention_dao=mentions,
        resolution_dao=resolutions,
        relationship_dao=relationships,
        evidence_dao=evidence,
        gateway=gateway,
    )

    assert report.relationships_created == 0
    assert report.evidence_created == 0
    assert report.skipped == 1
    assert relationships.list() == []
    assert evidence.list() == []


def test_ambiguous_resolution_is_not_used(tmp_path):
    mentions, resolutions, relationships, evidence = _setup(tmp_path)

    _mention(
        mentions,
        mention_id="m1",
        entry_id=1,
        memory_id="mem-1",
        profile="athena",
        text="Mnemosyne",
    )
    _mention(
        mentions,
        mention_id="m2",
        entry_id=1,
        memory_id="mem-1",
        profile="athena",
        text="FastAPI",
    )

    resolutions.create(
        mention_id="m1",
        proposed_entity_id=None,
        decision="ambiguous",
        confidence=0.0,
        resolution_method="normalized-name-v1",
    )
    _resolve(resolutions, mention_id="m2", entity_id="entity-fastapi")

    gateway = InMemoryMemoryGateway(
        {
            ("athena", "mem-1"): "Mnemosyne uses FastAPI.",
        }
    )

    report = extract_and_record_relationships(
        mention_dao=mentions,
        resolution_dao=resolutions,
        relationship_dao=relationships,
        evidence_dao=evidence,
        gateway=gateway,
    )

    assert report.relationships_created == 0
    assert report.skipped == 1


def test_qualified_profile_is_preserved_in_evidence(tmp_path):
    mentions, resolutions, relationships, evidence = _setup(tmp_path)

    _mention(
        mentions,
        mention_id="m1",
        entry_id=1,
        memory_id="mem-1",
        profile="agent-a:athena",
        text="Hermes",
    )
    _mention(
        mentions,
        mention_id="m2",
        entry_id=1,
        memory_id="mem-1",
        profile="agent-a:athena",
        text="FastAPI",
    )

    _resolve(resolutions, mention_id="m1", entity_id="entity-hermes")
    _resolve(resolutions, mention_id="m2", entity_id="entity-fastapi")

    gateway = InMemoryMemoryGateway(
        {
            ("agent-a:athena", "mem-1"): "Hermes uses FastAPI.",
        }
    )

    report = extract_and_record_relationships(
        mention_dao=mentions,
        resolution_dao=resolutions,
        relationship_dao=relationships,
        evidence_dao=evidence,
        gateway=gateway,
    )

    assert report.relationships_created == 1
    assert evidence.list()[0]["source_profile"] == "agent-a:athena"


def test_repeated_run_is_idempotent(tmp_path):
    mentions, resolutions, relationships, evidence = _setup(tmp_path)

    _mention(
        mentions,
        mention_id="m1",
        entry_id=1,
        memory_id="mem-1",
        profile="athena",
        text="Mnemosyne",
    )
    _mention(
        mentions,
        mention_id="m2",
        entry_id=1,
        memory_id="mem-1",
        profile="athena",
        text="FastAPI",
    )

    _resolve(resolutions, mention_id="m1", entity_id="entity-mnemosyne")
    _resolve(resolutions, mention_id="m2", entity_id="entity-fastapi")

    gateway = InMemoryMemoryGateway(
        {
            ("athena", "mem-1"): "Mnemosyne uses FastAPI.",
        }
    )

    first = extract_and_record_relationships(
        mention_dao=mentions,
        resolution_dao=resolutions,
        relationship_dao=relationships,
        evidence_dao=evidence,
        gateway=gateway,
    )
    second = extract_and_record_relationships(
        mention_dao=mentions,
        resolution_dao=resolutions,
        relationship_dao=relationships,
        evidence_dao=evidence,
        gateway=gateway,
    )

    assert first.relationships_created == 1
    assert first.evidence_created == 1

    assert second.relationships_created == 0
    assert second.relationships_existing == 1
    assert second.evidence_created == 0
    assert second.evidence_existing == 1

    assert len(relationships.list()) == 1
    assert len(evidence.list()) == 1


def test_source_memory_content_is_not_persisted(tmp_path):
    mentions, resolutions, relationships, evidence = _setup(tmp_path)

    _mention(
        mentions,
        mention_id="m1",
        entry_id=1,
        memory_id="mem-1",
        profile="athena",
        text="Mnemosyne",
    )
    _mention(
        mentions,
        mention_id="m2",
        entry_id=1,
        memory_id="mem-1",
        profile="athena",
        text="FastAPI",
    )

    _resolve(resolutions, mention_id="m1", entity_id="entity-mnemosyne")
    _resolve(resolutions, mention_id="m2", entity_id="entity-fastapi")

    private_text = "Mnemosyne uses FastAPI. SECRET_PRIVATE_MEMORY"

    gateway = InMemoryMemoryGateway(
        {
            ("athena", "mem-1"): private_text,
        }
    )

    extract_and_record_relationships(
        mention_dao=mentions,
        resolution_dao=resolutions,
        relationship_dao=relationships,
        evidence_dao=evidence,
        gateway=gateway,
    )

    database_text = str(relationships.list()) + str(evidence.list())

    assert "SECRET_PRIVATE_MEMORY" not in database_text
    assert "Mnemosyne uses FastAPI" not in database_text


def test_source_gateway_failure_is_isolated(tmp_path):
    mentions, resolutions, relationships, evidence = _setup(tmp_path)

    _mention(
        mentions,
        mention_id="m1",
        entry_id=1,
        memory_id="missing",
        profile="athena",
        text="Mnemosyne",
    )
    _mention(
        mentions,
        mention_id="m2",
        entry_id=1,
        memory_id="missing",
        profile="athena",
        text="FastAPI",
    )

    _resolve(resolutions, mention_id="m1", entity_id="entity-mnemosyne")
    _resolve(resolutions, mention_id="m2", entity_id="entity-fastapi")

    gateway = InMemoryMemoryGateway({})

    report = extract_and_record_relationships(
        mention_dao=mentions,
        resolution_dao=resolutions,
        relationship_dao=relationships,
        evidence_dao=evidence,
        gateway=gateway,
    )

    assert report.relationships_created == 0
    assert report.evidence_created == 0
    assert report.skipped == 1
    assert len(report.failures) == 1
    assert relationships.list() == []
    assert evidence.list() == []


def test_rejected_resolution_is_not_used(tmp_path):
    mentions, resolutions, relationships, evidence = _setup(tmp_path)

    _mention(
        mentions,
        mention_id="m1",
        entry_id=1,
        memory_id="mem-1",
        profile="athena",
        text="Mnemosyne",
    )
    _mention(
        mentions,
        mention_id="m2",
        entry_id=1,
        memory_id="mem-1",
        profile="athena",
        text="FastAPI",
    )

    resolutions.create(
        mention_id="m1",
        proposed_entity_id=None,
        decision="rejected",
        confidence=0.0,
        resolution_method="normalized-name-v1",
    )
    _resolve(resolutions, mention_id="m2", entity_id="entity-fastapi")

    gateway = InMemoryMemoryGateway(
        {
            ("athena", "mem-1"): "Mnemosyne uses FastAPI.",
        }
    )

    report = extract_and_record_relationships(
        mention_dao=mentions,
        resolution_dao=resolutions,
        relationship_dao=relationships,
        evidence_dao=evidence,
        gateway=gateway,
    )

    assert report.relationships_created == 0
    assert report.skipped == 1


def test_no_relationship_is_created_for_unrelated_text(tmp_path):
    mentions, resolutions, relationships, evidence = _setup(tmp_path)

    _mention(
        mentions,
        mention_id="m1",
        entry_id=1,
        memory_id="mem-1",
        profile="athena",
        text="Mnemosyne",
    )
    _mention(
        mentions,
        mention_id="m2",
        entry_id=1,
        memory_id="mem-1",
        profile="athena",
        text="FastAPI",
    )

    _resolve(resolutions, mention_id="m1", entity_id="entity-mnemosyne")
    _resolve(resolutions, mention_id="m2", entity_id="entity-fastapi")

    gateway = InMemoryMemoryGateway(
        {
            ("athena", "mem-1"):
                "The evidence discusses a FastAPI route used by Mnemosyne.",
        }
    )

    report = extract_and_record_relationships(
        mention_dao=mentions,
        resolution_dao=resolutions,
        relationship_dao=relationships,
        evidence_dao=evidence,
        gateway=gateway,
    )

    assert report.relationships_created == 0
    assert report.evidence_created == 0
    assert report.skipped == 0
    assert relationships.list() == []
    assert evidence.list() == []
