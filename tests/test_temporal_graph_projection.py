from datetime import datetime

import pytest

from src.domain.collective import CollectiveDAO
from src.domain.temporal_evidence import TemporalEvidenceDAO
from src.services.temporal_graph_projection import (
    TemporalGraphProjector,
)


@pytest.fixture
def stores(tmp_path):
    collective = CollectiveDAO(tmp_path / "collective.db")
    collective.ensure_schema()

    temporal = TemporalEvidenceDAO(tmp_path / "collective.db")
    temporal.ensure_schema()

    yield collective, temporal

    collective.close()
    temporal.close()


def promote(dao, profile, memory_id):
    entry_id = dao.add_entry(profile, memory_id)
    dao.update_entry_promoted(entry_id)
    return entry_id


def add_temporal(
    dao,
    *,
    evidence_id,
    entry_id,
    profile,
    memory_id,
    start,
    end,
    relation="at",
):
    return dao.add(
        temporal_evidence_id=evidence_id,
        collective_entry_id=entry_id,
        subject_type="memory",
        subject_id=memory_id,
        temporal_relation=relation,
        precision="day",
        start_time=start,
        end_time=end,
        extraction_method="test",
        source_memory_id=memory_id,
        source_profile=profile,
    )


def test_projector_uses_existing_edge_model(stores):
    collective, temporal = stores

    first = promote(collective, "athena", "memory-1")
    second = promote(collective, "athena", "memory-2")

    add_temporal(
        temporal,
        evidence_id="te-1",
        entry_id=first,
        profile="athena",
        memory_id="memory-1",
        start=datetime(2026, 9, 1),
        end=datetime(2026, 9, 2),
    )
    add_temporal(
        temporal,
        evidence_id="te-2",
        entry_id=second,
        profile="athena",
        memory_id="memory-2",
        start=datetime(2026, 9, 3),
        end=datetime(2026, 9, 4),
    )

    result = TemporalGraphProjector(
        [collective],
        temporal,
    ).project()

    assert result.count == 1

    projection = result.projections[0]

    assert projection.edge.source_id == "athena:memory-1"
    assert projection.edge.target_id == "athena:memory-2"
    assert projection.edge.relationship_type == "temporal:before"
    assert projection.edge.similarity_score == 0.0
    assert projection.temporal_evidence_ids == ("te-1", "te-2")


def test_revoked_entries_are_not_projected(stores):
    collective, temporal = stores

    first = promote(collective, "athena", "memory-1")
    second = promote(collective, "athena", "memory-2")

    add_temporal(
        temporal,
        evidence_id="te-1",
        entry_id=first,
        profile="athena",
        memory_id="memory-1",
        start="2026-09-01",
        end="2026-09-02",
    )
    add_temporal(
        temporal,
        evidence_id="te-2",
        entry_id=second,
        profile="athena",
        memory_id="memory-2",
        start="2026-09-03",
        end="2026-09-04",
    )

    collective.revoke_entry(first, "test revocation")

    result = TemporalGraphProjector(
        [collective],
        temporal,
    ).project()

    assert result.projections == ()


def test_unpromoted_entries_are_not_projected(stores):
    collective, temporal = stores

    first = promote(collective, "athena", "memory-1")
    second = collective.add_entry("athena", "memory-2")

    add_temporal(
        temporal,
        evidence_id="te-1",
        entry_id=first,
        profile="athena",
        memory_id="memory-1",
        start="2026-09-01",
        end="2026-09-02",
    )
    add_temporal(
        temporal,
        evidence_id="te-2",
        entry_id=second,
        profile="athena",
        memory_id="memory-2",
        start="2026-09-03",
        end="2026-09-04",
    )

    result = TemporalGraphProjector(
        [collective],
        temporal,
    ).project()

    assert result.projections == ()


def test_provenance_mismatch_is_not_projected(stores):
    collective, temporal = stores

    first = promote(collective, "athena", "memory-1")
    second = promote(collective, "athena", "memory-2")

    add_temporal(
        temporal,
        evidence_id="te-1",
        entry_id=first,
        profile="athena",
        memory_id="memory-1",
        start="2026-09-01",
        end="2026-09-02",
    )
    add_temporal(
        temporal,
        evidence_id="te-2",
        entry_id=second,
        profile="athena",
        memory_id="wrong-memory",
        start="2026-09-03",
        end="2026-09-04",
    )

    result = TemporalGraphProjector(
        [collective],
        temporal,
    ).project()

    assert result.projections == ()


def test_unknown_precision_does_not_create_temporal_edge(stores):
    collective, temporal = stores

    first = promote(collective, "athena", "memory-1")
    second = promote(collective, "athena", "memory-2")

    temporal.add(
        temporal_evidence_id="te-1",
        collective_entry_id=first,
        subject_type="memory",
        subject_id="memory-1",
        temporal_relation="at",
        precision="unknown",
        extraction_method="test",
        source_memory_id="memory-1",
        source_profile="athena",
    )
    temporal.add(
        temporal_evidence_id="te-2",
        collective_entry_id=second,
        subject_type="memory",
        subject_id="memory-2",
        temporal_relation="at",
        precision="unknown",
        extraction_method="test",
        source_memory_id="memory-2",
        source_profile="athena",
    )

    result = TemporalGraphProjector(
        [collective],
        temporal,
    ).project()

    assert result.projections == ()


def test_projection_does_not_modify_temporal_evidence(stores):
    collective, temporal = stores

    first = promote(collective, "athena", "memory-1")
    second = promote(collective, "athena", "memory-2")

    add_temporal(
        temporal,
        evidence_id="te-1",
        entry_id=first,
        profile="athena",
        memory_id="memory-1",
        start="2026-09-01",
        end="2026-09-02",
    )
    add_temporal(
        temporal,
        evidence_id="te-2",
        entry_id=second,
        profile="athena",
        memory_id="memory-2",
        start="2026-09-03",
        end="2026-09-04",
    )

    before = temporal.list()

    TemporalGraphProjector(
        [collective],
        temporal,
    ).project()

    after = temporal.list()

    assert after == before


def test_projection_is_deterministic(stores):
    collective, temporal = stores

    first = promote(collective, "athena", "memory-1")
    second = promote(collective, "athena", "memory-2")
    third = promote(collective, "athena", "memory-3")

    add_temporal(
        temporal,
        evidence_id="te-1",
        entry_id=first,
        profile="athena",
        memory_id="memory-1",
        start="2026-09-01",
        end="2026-09-02",
    )
    add_temporal(
        temporal,
        evidence_id="te-2",
        entry_id=second,
        profile="athena",
        memory_id="memory-2",
        start="2026-09-03",
        end="2026-09-04",
    )
    add_temporal(
        temporal,
        evidence_id="te-3",
        entry_id=third,
        profile="athena",
        memory_id="memory-3",
        start="2026-09-05",
        end="2026-09-06",
    )

    projector = TemporalGraphProjector(
        [collective],
        temporal,
    )

    first_result = projector.project()
    second_result = projector.project()

    assert first_result == second_result
    assert first_result.count == 3


def test_project_all_matches_project(stores):
    collective, temporal = stores

    first = promote(collective, "athena", "memory-1")
    second = promote(collective, "athena", "memory-2")

    add_temporal(
        temporal,
        evidence_id="te-1",
        entry_id=first,
        profile="athena",
        memory_id="memory-1",
        start="2026-09-01",
        end="2026-09-02",
    )
    add_temporal(
        temporal,
        evidence_id="te-2",
        entry_id=second,
        profile="athena",
        memory_id="memory-2",
        start="2026-09-03",
        end="2026-09-04",
    )

    projector = TemporalGraphProjector(
        [collective],
        temporal,
    )

    assert projector.project_all() == projector.project()
