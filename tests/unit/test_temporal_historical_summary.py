import pytest

from src.domain.entity_historical_state import (
    EntityHistoricalObservation,
    EntityHistoricalStateBuilder,
)
from src.domain.relationship_historical_state import (
    RelationshipHistoricalObservation,
    RelationshipHistoricalStateBuilder,
)
from src.domain.temporal_historical_summary import (
    TemporalHistoricalSummaryBuilder,
)


def entity_observation(
    evidence_id,
    state,
    valid_from,
):
    return EntityHistoricalObservation(
        entity_id=1,
        state=state,
        evidence_id=evidence_id,
        source_profile="Horus",
        source_memory_id=evidence_id,
        valid_from=valid_from,
        precision="day",
        confidence=0.9,
    )


def relationship_observation(
    evidence_id,
    valid_from,
):
    return RelationshipHistoricalObservation(
        source_entity_id=1,
        target_entity_id=2,
        relation="works_with",
        evidence_id=evidence_id,
        source_profile="Horus",
        source_memory_id=evidence_id,
        valid_from=valid_from,
        precision="day",
        confidence=0.9,
    )


def test_entity_summary_reports_observed_states():
    history = EntityHistoricalStateBuilder.build(
        1,
        [
            entity_observation("te-1", "active", "2025-01-01"),
            entity_observation("te-2", "inactive", "2025-02-01"),
        ],
    )

    summary = TemporalHistoricalSummaryBuilder.entity(history)

    assert summary.entity_id == 1
    assert summary.observed_states == ("active", "inactive")
    assert summary.observation_count == 2
    assert summary.transition_count == 1


def test_entity_summary_contains_evidence_for_state_claim():
    history = EntityHistoricalStateBuilder.build(
        1,
        [entity_observation("te-1", "active", "2025-01-01")],
    )

    summary = TemporalHistoricalSummaryBuilder.entity(history)

    state_statement = next(
        statement
        for statement in summary.statements
        if "'active'" in statement.statement
    )

    assert state_statement.evidence_count == 1
    assert state_statement.evidence[0].evidence_id == "te-1"
    assert state_statement.evidence[0].source_profile == "Horus"


def test_entity_transition_summary_is_evidence_backed():
    history = EntityHistoricalStateBuilder.build(
        1,
        [
            entity_observation("te-1", "active", "2025-01-01"),
            entity_observation("te-2", "inactive", "2025-02-01"),
        ],
    )

    summary = TemporalHistoricalSummaryBuilder.entity(history)

    transition_statement = next(
        statement
        for statement in summary.statements
        if "transition" in statement.statement
    )

    assert transition_statement.evidence_count == 2
    assert {
        evidence.evidence_id
        for evidence in transition_statement.evidence
    } == {"te-1", "te-2"}


def test_entity_summary_preserves_unknown_timing():
    history = EntityHistoricalStateBuilder.build(
        1,
        [
            EntityHistoricalObservation(
                entity_id=1,
                state="active",
                evidence_id="te-unknown",
                source_profile="Horus",
                source_memory_id=99,
                precision="unknown",
                confidence=0.5,
            )
        ],
    )

    summary = TemporalHistoricalSummaryBuilder.entity(history)

    assert summary.known_timed_observations == 0
    assert summary.unknown_timed_observations == 1
    assert summary.complete is False


def test_entity_summary_is_deterministic():
    history_a = EntityHistoricalStateBuilder.build(
        1,
        [
            entity_observation("te-2", "inactive", "2025-02-01"),
            entity_observation("te-1", "active", "2025-01-01"),
        ],
    )

    history_b = EntityHistoricalStateBuilder.build(
        1,
        [
            entity_observation("te-1", "active", "2025-01-01"),
            entity_observation("te-2", "inactive", "2025-02-01"),
        ],
    )

    assert (
        TemporalHistoricalSummaryBuilder.entity(history_a)
        == TemporalHistoricalSummaryBuilder.entity(history_b)
    )


def test_relationship_summary_reports_observation():
    history = RelationshipHistoricalStateBuilder.build(
        1,
        2,
        "works_with",
        [relationship_observation("te-1", "2025-01-01")],
    )

    summary = TemporalHistoricalSummaryBuilder.relationship(history)

    assert summary.source_entity_id == 1
    assert summary.target_entity_id == 2
    assert summary.relation == "works_with"
    assert summary.observation_count == 1
    assert summary.evidence_count == 1


def test_relationship_summary_contains_provenance():
    history = RelationshipHistoricalStateBuilder.build(
        1,
        2,
        "works_with",
        [
            relationship_observation("te-1", "2025-01-01"),
            relationship_observation("te-2", "2025-02-01"),
        ],
    )

    summary = TemporalHistoricalSummaryBuilder.relationship(history)

    statement = summary.statements[0]

    assert statement.evidence_count == 2
    assert [e.evidence_id for e in statement.evidence] == [
        "te-1",
        "te-2",
    ]


def test_relationship_gap_is_not_summarized_as_ended():
    history = RelationshipHistoricalStateBuilder.build(
        1,
        2,
        "works_with",
        [
            RelationshipHistoricalObservation(
                source_entity_id=1,
                target_entity_id=2,
                relation="works_with",
                evidence_id="te-1",
                source_profile="Horus",
                source_memory_id=1,
                valid_from="2025-01-01",
                valid_to="2025-01-31",
                precision="day",
                confidence=0.9,
            ),
            relationship_observation("te-2", "2025-03-01"),
        ],
    )

    summary = TemporalHistoricalSummaryBuilder.relationship(history)

    assert all(
        "ended" not in statement.statement.lower()
        for statement in summary.statements
    )


def test_invalid_summary_statement_is_rejected():
    from src.domain.temporal_historical_summary import TemporalSummaryStatement

    with pytest.raises(ValueError, match="statement"):
        TemporalSummaryStatement(statement="")
