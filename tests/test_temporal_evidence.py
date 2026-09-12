from datetime import datetime
import sqlite3

import pytest

from src.domain.temporal_evidence import TemporalEvidenceDAO


@pytest.fixture
def dao(tmp_path):
    dao = TemporalEvidenceDAO(tmp_path / "collective.db")
    dao.ensure_schema()
    yield dao
    dao.close()


def test_schema_is_idempotent(dao):
    dao.ensure_schema()
    tables = {
        row["name"]
        for row in dao.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    assert "temporal_evidence" in tables


def test_observed_event_evidence_round_trips(dao):
    evidence_id = dao.add(
        collective_entry_id=7,
        subject_type="memory",
        subject_id="memory-7",
        temporal_relation="at",
        precision="day",
        start_time=datetime(2026, 9, 10),
        extraction_method="explicit_date",
        source_memory_id="memory-7",
        source_profile="athena",
        confidence=0.98,
        evidence_kind="observed",
        temporal_evidence_id="te-1",
        created_at="2026-09-10T12:00:00+00:00",
    )

    assert evidence_id == "te-1"
    assert dao.get(evidence_id) == {
        "temporal_evidence_id": "te-1",
        "collective_entry_id": 7,
        "subject_type": "memory",
        "subject_id": "memory-7",
        "object_type": None,
        "object_id": None,
        "temporal_relation": "at",
        "start_time": "2026-09-10T00:00:00",
        "end_time": None,
        "precision": "day",
        "confidence": 0.98,
        "evidence_kind": "observed",
        "extraction_method": "explicit_date",
        "source_memory_id": "memory-7",
        "source_profile": "athena",
        "created_at": "2026-09-10T12:00:00+00:00",
    }


def test_entity_and_relationship_temporal_assertions_are_supported(dao):
    entity_id = dao.add(
        collective_entry_id=8,
        subject_type="entity",
        subject_id="entity-project",
        temporal_relation="ongoing",
        precision="month",
        start_time="2026-01",
        extraction_method="explicit_statement",
        source_memory_id="memory-8",
        source_profile="horus",
    )
    relationship_id = dao.add(
        collective_entry_id=9,
        subject_type="entity",
        subject_id="entity-a",
        object_type="entity",
        object_id="entity-b",
        temporal_relation="before",
        precision="day",
        start_time="2026-08-01",
        end_time="2026-08-02",
        extraction_method="explicit_ordering",
        source_memory_id="memory-9",
        source_profile="odin",
    )

    assert {row["temporal_evidence_id"] for row in dao.list()} == {
        entity_id,
        relationship_id,
    }


def test_inferred_evidence_remains_distinct(dao):
    evidence_id = dao.add(
        collective_entry_id=10,
        subject_type="relationship",
        subject_id="relationship-1",
        object_type="entity",
        object_id="entity-2",
        temporal_relation="after",
        precision="day",
        start_time="2026-08-20",
        extraction_method="temporal_reasoner",
        source_memory_id="memory-10",
        source_profile="athena",
        evidence_kind="inferred",
    )

    result = dao.get(evidence_id)
    assert result["evidence_kind"] == "inferred"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("subject_type", "profile"),
        ("temporal_relation", "yesterday"),
        ("precision", "exact"),
        ("evidence_kind", "fact"),
    ],
)
def test_invalid_enums_are_rejected(dao, field, value):
    kwargs = dict(
        collective_entry_id=1,
        subject_type="memory",
        subject_id="memory-1",
        temporal_relation="at",
        precision="day",
        extraction_method="test",
        source_memory_id="memory-1",
        source_profile="athena",
    )
    kwargs[field] = value

    with pytest.raises(ValueError):
        dao.add(**kwargs)


def test_object_type_and_id_must_be_paired(dao):
    with pytest.raises(ValueError):
        dao.add(
            collective_entry_id=1,
            subject_type="entity",
            subject_id="entity-1",
            object_type="entity",
            temporal_relation="before",
            precision="day",
            extraction_method="test",
            source_memory_id="memory-1",
            source_profile="athena",
        )


def test_unknown_precision_cannot_claim_explicit_bounds(dao):
    with pytest.raises(ValueError):
        dao.add(
            collective_entry_id=1,
            subject_type="memory",
            subject_id="memory-1",
            temporal_relation="at",
            precision="unknown",
            start_time="2026-09-10",
            extraction_method="test",
            source_memory_id="memory-1",
            source_profile="athena",
        )


def test_invalid_interval_is_rejected(dao):
    with pytest.raises(ValueError):
        dao.add(
            collective_entry_id=1,
            subject_type="memory",
            subject_id="memory-1",
            temporal_relation="during",
            precision="day",
            start_time="2026-09-12",
            end_time="2026-09-10",
            extraction_method="test",
            source_memory_id="memory-1",
            source_profile="athena",
        )


def test_duplicate_evidence_is_rejected(dao):
    kwargs = dict(
        collective_entry_id=1,
        subject_type="memory",
        subject_id="memory-1",
        temporal_relation="at",
        precision="day",
        start_time="2026-09-10",
        extraction_method="test",
        source_memory_id="memory-1",
        source_profile="athena",
        evidence_kind="observed",
    )

    dao.add(**kwargs)

    with pytest.raises(sqlite3.IntegrityError):
        dao.add(**kwargs)


def test_listing_is_deterministic_and_filterable(dao):
    dao.add(
        collective_entry_id=2,
        subject_type="entity",
        subject_id="entity-b",
        temporal_relation="ongoing",
        precision="year",
        extraction_method="test",
        source_memory_id="memory-b",
        source_profile="horus",
    )
    dao.add(
        collective_entry_id=1,
        subject_type="entity",
        subject_id="entity-a",
        temporal_relation="ongoing",
        precision="year",
        extraction_method="test",
        source_memory_id="memory-a",
        source_profile="athena",
    )

    rows = dao.list(subject_type="entity", source_profile="athena")
    assert len(rows) == 1
    assert rows[0]["collective_entry_id"] == 1
