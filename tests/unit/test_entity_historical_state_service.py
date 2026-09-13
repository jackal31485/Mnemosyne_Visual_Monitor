from dataclasses import dataclass

import pytest

from src.domain.entity_historical_state import EntityHistoricalObservation
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


def test_from_timeline_adapts_observations_without_mutating_timeline():
    timeline = {
        "observations": [
            {
                "entity_id": 1,
                "state": "active",
                "evidence_id": "te-2",
                "source_profile": "Horus",
                "source_memory_id": 22,
                "valid_from": "2025-02-01",
                "precision": "day",
                "confidence": 0.8,
            },
            {
                "entity_id": 1,
                "state": "inactive",
                "evidence_id": "te-1",
                "source_profile": "Horus",
                "source_memory_id": 11,
                "valid_from": "2025-01-01",
                "precision": "day",
                "confidence": 0.9,
            },
        ]
    }

    original = repr(timeline)

    result = EntityHistoricalStateService.from_timeline(1, timeline)

    assert repr(timeline) == original
    assert result.observation_count == 2
    assert [o.evidence_id for o in result.observations] == [
        "te-1",
        "te-2",
    ]
    assert result.transition_count == 1


def test_from_timeline_accepts_entries_collection():
    timeline = {
        "entries": [
            {
                "entity_id": 1,
                "state": "active",
                "temporal_evidence_id": "te-10",
                "source_profile": "Odin",
                "source_memory_id": 100,
                "start": "2024-01-01",
                "end": "2024-12-31",
                "precision": "day",
                "confidence": 0.75,
            }
        ]
    }

    result = EntityHistoricalStateService.from_timeline(1, timeline)

    assert result.observation_count == 1
    assert result.observations[0].evidence_id == "te-10"
    assert result.observations[0].valid_from == "2024-01-01"
    assert result.observations[0].valid_to == "2024-12-31"


@dataclass
class TimelineObservation:
    entity_id: int
    state: str
    temporal_evidence_id: str
    source_profile: str
    source_memory_id: int
    start: str | None
    end: str | None
    precision: str
    confidence: float


@dataclass
class Timeline:
    observations: list[TimelineObservation]


def test_from_timeline_accepts_existing_style_objects():
    timeline = Timeline(
        observations=[
            TimelineObservation(
                entity_id=7,
                state="active",
                temporal_evidence_id="te-7",
                source_profile="Thoth",
                source_memory_id=77,
                start="2025-03-01",
                end=None,
                precision="day",
                confidence=0.95,
            )
        ]
    )

    result = EntityHistoricalStateService.from_timeline(7, timeline)

    assert result.entity_id == 7
    assert result.observation_count == 1
    assert result.observations[0].evidence_id == "te-7"
    assert result.observations[0].source_profile == "Thoth"


def test_from_timeline_preserves_unknown_timing():
    timeline = {
        "observations": [
            {
                "entity_id": 1,
                "state": "active",
                "evidence_id": "te-unknown",
                "source_profile": "Horus",
                "source_memory_id": 55,
                "valid_from": None,
                "valid_to": None,
                "precision": "unknown",
                "confidence": 0.5,
            }
        ]
    }

    result = EntityHistoricalStateService.from_timeline(1, timeline)

    assert result.observation_count == 1
    assert result.known_timed_observation_count == 0
    assert result.unknown_timed_observation_count == 1
    assert result.complete is False


def test_from_timeline_rejects_missing_state():
    timeline = {
        "observations": [
            {
                "entity_id": 1,
                "evidence_id": "te-1",
                "source_profile": "Horus",
                "source_memory_id": 1,
            }
        ]
    }

    with pytest.raises(ValueError, match="state"):
        EntityHistoricalStateService.from_timeline(1, timeline)


def test_from_timeline_rejects_missing_evidence():
    timeline = {
        "observations": [
            {
                "entity_id": 1,
                "state": "active",
                "source_profile": "Horus",
                "source_memory_id": 1,
            }
        ]
    }

    with pytest.raises(ValueError, match="evidence_id"):
        EntityHistoricalStateService.from_timeline(1, timeline)


def test_from_timeline_rejects_missing_provenance():
    timeline = {
        "observations": [
            {
                "entity_id": 1,
                "state": "active",
                "evidence_id": "te-1",
            }
        ]
    }

    with pytest.raises(ValueError, match="source_profile"):
        EntityHistoricalStateService.from_timeline(1, timeline)


def test_service_filters_other_entities():
    timeline = {
        "observations": [
            {
                "entity_id": 1,
                "state": "active",
                "evidence_id": "te-1",
                "source_profile": "Horus",
                "source_memory_id": 1,
                "valid_from": "2025-01-01",
                "precision": "day",
                "confidence": 0.9,
            },
            {
                "entity_id": 2,
                "state": "inactive",
                "evidence_id": "te-2",
                "source_profile": "Horus",
                "source_memory_id": 2,
                "valid_from": "2025-02-01",
                "precision": "day",
                "confidence": 0.9,
            },
        ]
    }

    result = EntityHistoricalStateService.from_timeline(1, timeline)

    assert result.observation_count == 1
    assert result.observations[0].entity_id == 1
