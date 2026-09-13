from dataclasses import dataclass

import pytest

from src.domain.relationship_historical_state import (
    RelationshipHistoricalObservation,
)
from src.services.relationship_historical_state_service import (
    RelationshipHistoricalStateService,
)


@dataclass
class FakeCollective:
    lifecycle: dict
    entries: dict

    def get_lifecycle_state(self, entry_id):
        return self.lifecycle.get(entry_id)

    def get_by_id(self, entry_id):
        return self.entries.get(entry_id)


def observation(
    evidence_id,
    *,
    relation="works_with",
    profile="Horus",
    memory_id=100,
):
    return RelationshipHistoricalObservation(
        source_entity_id=1,
        target_entity_id=2,
        relation=relation,
        evidence_id=evidence_id,
        source_profile=profile,
        source_memory_id=memory_id,
        valid_from="2025-01-01",
        precision="day",
        confidence=0.9,
    )


def collective_for(
    entry_id=1,
    *,
    profile="Horus",
    memory_id=100,
    promoted=True,
    revoked=False,
    validated=True,
):
    return FakeCollective(
        lifecycle={
            entry_id: (
                "2025-01-02" if validated else None,
                revoked,
                "test" if revoked else None,
                promoted,
            )
        },
        entries={
            entry_id: (
                entry_id,
                profile,
                memory_id,
                "2025-01-01",
                "2025-01-02",
                1.0,
                "validator",
                revoked,
                "test" if revoked else None,
            )
        },
    )


def test_governed_relationship_is_included():
    result = RelationshipHistoricalStateService.build_governed(
        1,
        2,
        "works_with",
        [observation(1)],
        collective_for(),
    )

    assert result.observation_count == 1
    assert result.observations[0].evidence_id == 1


def test_unpromoted_relationship_evidence_is_excluded():
    result = RelationshipHistoricalStateService.build_governed(
        1,
        2,
        "works_with",
        [observation(1)],
        collective_for(promoted=False),
    )

    assert result.observation_count == 0


def test_revoked_relationship_evidence_is_excluded():
    result = RelationshipHistoricalStateService.build_governed(
        1,
        2,
        "works_with",
        [observation(1)],
        collective_for(revoked=True),
    )

    assert result.observation_count == 0


def test_unvalidated_relationship_evidence_is_excluded():
    result = RelationshipHistoricalStateService.build_governed(
        1,
        2,
        "works_with",
        [observation(1)],
        collective_for(validated=False),
    )

    assert result.observation_count == 0


def test_profile_mismatch_is_excluded():
    result = RelationshipHistoricalStateService.build_governed(
        1,
        2,
        "works_with",
        [observation(1, profile="Horus")],
        collective_for(profile="Odin"),
    )

    assert result.observation_count == 0


def test_source_memory_mismatch_is_excluded():
    result = RelationshipHistoricalStateService.build_governed(
        1,
        2,
        "works_with",
        [observation(1, memory_id=100)],
        collective_for(memory_id=999),
    )

    assert result.observation_count == 0


def test_temporal_evidence_identifier_is_not_assumed_to_be_collective_id():
    result = RelationshipHistoricalStateService.build_governed(
        1,
        2,
        "works_with",
        [observation("te-1")],
        collective_for(),
    )

    assert result.observation_count == 0


def test_wrong_relationship_is_excluded():
    result = RelationshipHistoricalStateService.build_governed(
        1,
        2,
        "works_with",
        [observation(1, relation="knows")],
        collective_for(),
    )

    assert result.observation_count == 0


def test_mapping_adapter_supports_temporal_evidence_id():
    result = RelationshipHistoricalStateService.from_mappings(
        1,
        2,
        "works_with",
        [
            {
                "source_entity_id": 1,
                "target_entity_id": 2,
                "relation": "works_with",
                "temporal_evidence_id": "te-10",
                "source_profile": "Horus",
                "source_memory_id": 10,
                "start": "2025-01-01",
                "precision": "day",
                "confidence": 0.8,
            }
        ],
    )

    assert result.observation_count == 1
    assert result.observations[0].evidence_id == "te-10"


def test_governance_does_not_mutate_observation():
    item = observation(1)
    collective = collective_for()

    result = RelationshipHistoricalStateService.build_governed(
        1,
        2,
        "works_with",
        [item],
        collective,
    )

    assert result.observations[0] == item
    assert item.relation == "works_with"
    assert item.source_profile == "Horus"
    assert item.source_memory_id == 100
