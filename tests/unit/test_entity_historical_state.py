from src.domain.entity_historical_state import (
    EntityHistoricalObservation,
    EntityHistoricalStateBuilder,
)
from src.services.entity_historical_state_service import (
    EntityHistoricalStateService,
)


def observation(
    evidence_id,
    state,
    valid_from,
    *,
    entity_id=1,
    valid_to=None,
    precision="day",
    confidence=0.9,
):
    return EntityHistoricalObservation(
        entity_id=entity_id,
        state=state,
        evidence_id=evidence_id,
        source_profile="Horus",
        source_memory_id=evidence_id,
        valid_from=valid_from,
        valid_to=valid_to,
        precision=precision,
        confidence=confidence,
    )


def test_empty_history_is_valid():
    result = EntityHistoricalStateBuilder.build(1, [])

    assert result.entity_id == 1
    assert result.observation_count == 0
    assert result.transition_count == 0
    assert result.states == ()
    assert result.complete is False


def test_history_is_deterministically_ordered():
    result = EntityHistoricalStateBuilder.build(
        1,
        [
            observation("te-2", "active", "2025-02-01"),
            observation("te-1", "inactive", "2025-01-01"),
        ],
    )

    assert [item.evidence_id for item in result.observations] == [
        "te-1",
        "te-2",
    ]


def test_history_records_states_without_mutating_current_entity():
    result = EntityHistoricalStateBuilder.build(
        1,
        [
            observation("te-1", "active", "2025-01-01"),
            observation("te-2", "inactive", "2025-02-01"),
        ],
    )

    assert result.states == ("active", "inactive")
    assert result.observation_count == 2
    assert result.transition_count == 1


def test_state_transition_is_evidence_backed():
    result = EntityHistoricalStateBuilder.build(
        1,
        [
            observation("te-1", "active", "2025-01-01"),
            observation("te-2", "inactive", "2025-02-01"),
        ],
    )

    transition = result.transitions[0]

    assert transition.from_state == "active"
    assert transition.to_state == "inactive"
    assert transition.evidence_ids == ("te-1", "te-2")
    assert transition.from_valid_from == "2025-01-01"
    assert transition.to_valid_from == "2025-02-01"


def test_same_state_does_not_create_transition():
    result = EntityHistoricalStateBuilder.build(
        1,
        [
            observation("te-1", "active", "2025-01-01"),
            observation("te-2", "active", "2025-02-01"),
        ],
    )

    assert result.observation_count == 2
    assert result.transition_count == 0


def test_unknown_timing_is_preserved():
    result = EntityHistoricalStateBuilder.build(
        1,
        [
            observation(
                "te-1",
                "active",
                None,
                precision="unknown",
            ),
        ],
    )

    assert result.observation_count == 1
    assert result.known_timed_observation_count == 0
    assert result.unknown_timed_observation_count == 1
    assert result.complete is False


def test_mixed_known_and_unknown_timing_is_incomplete():
    result = EntityHistoricalStateBuilder.build(
        1,
        [
            observation("te-1", "active", "2025-01-01"),
            observation("te-2", "inactive", None, precision="unknown"),
        ],
    )

    assert result.known_timed_observation_count == 1
    assert result.unknown_timed_observation_count == 1
    assert result.complete is False


def test_service_filters_observations_to_requested_entity():
    result = EntityHistoricalStateService.build(
        1,
        [
            observation("te-1", "active", "2025-01-01", entity_id=1),
            observation("te-2", "inactive", "2025-02-01", entity_id=2),
        ],
    )

    assert result.observation_count == 1
    assert result.observations[0].entity_id == 1


def test_service_mapping_adapter_builds_history():
    result = EntityHistoricalStateService.from_mappings(
        1,
        [
            {
                "entity_id": 1,
                "state": "active",
                "evidence_id": "te-1",
                "source_profile": "Horus",
                "source_memory_id": 42,
                "valid_from": "2025-01-01",
                "precision": "day",
                "confidence": 0.95,
            }
        ],
    )

    assert result.observation_count == 1
    assert result.observations[0].evidence_id == "te-1"
    assert result.observations[0].confidence == 0.95


def test_invalid_confidence_is_rejected():
    try:
        observation("te-1", "active", "2025-01-01", confidence=1.1)
    except ValueError as exc:
        assert "confidence" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_invalid_precision_is_rejected():
    try:
        observation(
            "te-1",
            "active",
            "2025-01-01",
            precision="century",
        )
    except ValueError as exc:
        assert "precision" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_end_before_start_is_rejected():
    try:
        observation(
            "te-1",
            "active",
            "2025-02-01",
            valid_to="2025-01-01",
        )
    except ValueError as exc:
        assert "precede" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
