import pytest

from src.domain.relationship_historical_state import (
    RelationshipHistoricalObservation,
    RelationshipHistoricalStateBuilder,
)


def observation(
    evidence_id,
    relation="works_with",
    *,
    source=1,
    target=2,
    valid_from="2025-01-01",
    valid_to=None,
    precision="day",
    confidence=0.9,
):
    return RelationshipHistoricalObservation(
        source_entity_id=source,
        target_entity_id=target,
        relation=relation,
        evidence_id=evidence_id,
        source_profile="Horus",
        source_memory_id=evidence_id,
        valid_from=valid_from,
        valid_to=valid_to,
        precision=precision,
        confidence=confidence,
    )


def test_empty_relationship_history():
    result = RelationshipHistoricalStateBuilder.build(
        1,
        2,
        "works_with",
        [],
    )

    assert result.observation_count == 0
    assert result.transition_count == 0
    assert result.observed_active is None
    assert result.complete is False


def test_relationship_observations_are_deterministically_ordered():
    result = RelationshipHistoricalStateBuilder.build(
        1,
        2,
        "works_with",
        [
            observation("te-2", valid_from="2025-02-01"),
            observation("te-1", valid_from="2025-01-01"),
        ],
    )

    assert [o.evidence_id for o in result.observations] == [
        "te-1",
        "te-2",
    ]


def test_relationship_history_preserves_relation():
    result = RelationshipHistoricalStateBuilder.build(
        1,
        2,
        "works_with",
        [observation("te-1")],
    )

    assert result.relation == "works_with"
    assert result.observation_count == 1
    assert result.observed_active is True


def test_other_relationships_are_excluded():
    result = RelationshipHistoricalStateBuilder.build(
        1,
        2,
        "works_with",
        [
            observation("te-1"),
            observation("te-2", source=2, target=3),
            observation("te-3", relation="knows"),
        ],
    )

    assert result.observation_count == 1
    assert result.observations[0].evidence_id == "te-1"


def test_unknown_timing_is_preserved():
    result = RelationshipHistoricalStateBuilder.build(
        1,
        2,
        "works_with",
        [
            observation(
                "te-unknown",
                valid_from=None,
                precision="unknown",
            )
        ],
    )

    assert result.known_timed_observation_count == 0
    assert result.unknown_timed_observation_count == 1
    assert result.complete is False


def test_timeline_gap_does_not_infer_inactive_state():
    result = RelationshipHistoricalStateBuilder.build(
        1,
        2,
        "works_with",
        [
            observation(
                "te-1",
                valid_from="2025-01-01",
                valid_to="2025-01-31",
            ),
            observation(
                "te-2",
                valid_from="2025-03-01",
            ),
        ],
    )

    assert result.observation_count == 2
    assert result.transition_count == 0


def test_self_relationship_is_rejected():
    with pytest.raises(ValueError, match="itself"):
        observation("te-1", source=1, target=1)


def test_invalid_confidence_is_rejected():
    with pytest.raises(ValueError, match="confidence"):
        observation("te-1", confidence=1.1)


def test_invalid_precision_is_rejected():
    with pytest.raises(ValueError, match="precision"):
        observation("te-1", precision="century")


def test_invalid_interval_is_rejected():
    with pytest.raises(ValueError, match="precede"):
        observation(
            "te-1",
            valid_from="2025-02-01",
            valid_to="2025-01-01",
        )
