from dataclasses import dataclass

from src.domain.entity_historical_state import EntityHistoricalObservation
from src.services.entity_historical_state_service import (
    EntityHistoricalStateService,
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
    state,
    *,
    entity_id=1,
    profile="Horus",
    memory_id=100,
):
    return EntityHistoricalObservation(
        entity_id=entity_id,
        state=state,
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


def test_promoted_non_revoked_matching_provenance_is_included():
    collective = collective_for()

    result = EntityHistoricalStateService.build_governed(
        1,
        [observation(1, "active")],
        collective,
    )

    assert result.observation_count == 1
    assert result.observations[0].evidence_id == 1


def test_unpromoted_evidence_is_excluded():
    collective = collective_for(promoted=False)

    result = EntityHistoricalStateService.build_governed(
        1,
        [observation(1, "active")],
        collective,
    )

    assert result.observation_count == 0


def test_revoked_evidence_is_excluded():
    collective = collective_for(revoked=True)

    result = EntityHistoricalStateService.build_governed(
        1,
        [observation(1, "active")],
        collective,
    )

    assert result.observation_count == 0


def test_unvalidated_evidence_is_excluded():
    collective = collective_for(validated=False)

    result = EntityHistoricalStateService.build_governed(
        1,
        [observation(1, "active")],
        collective,
    )

    assert result.observation_count == 0


def test_profile_mismatch_is_excluded():
    collective = collective_for(profile="Odin")

    result = EntityHistoricalStateService.build_governed(
        1,
        [observation(1, "active", profile="Horus")],
        collective,
    )

    assert result.observation_count == 0


def test_source_memory_mismatch_is_excluded():
    collective = collective_for(memory_id=999)

    result = EntityHistoricalStateService.build_governed(
        1,
        [observation(1, "active", memory_id=100)],
        collective,
    )

    assert result.observation_count == 0


def test_missing_collective_entry_is_excluded():
    collective = FakeCollective(lifecycle={}, entries={})

    result = EntityHistoricalStateService.build_governed(
        1,
        [observation(1, "active")],
        collective,
    )

    assert result.observation_count == 0


def test_canonical_temporal_evidence_id_is_not_treated_as_collective_entry_id():
    collective = collective_for()

    result = EntityHistoricalStateService.build_governed(
        1,
        [observation("te-1", "active")],
        collective,
    )

    assert result.observation_count == 0


def test_other_entity_is_excluded_before_governance():
    collective = collective_for()

    result = EntityHistoricalStateService.build_governed(
        1,
        [observation(1, "active", entity_id=2)],
        collective,
    )

    assert result.observation_count == 0


def test_governance_does_not_mutate_observations():
    collective = collective_for()
    item = observation(1, "active")

    result = EntityHistoricalStateService.build_governed(
        1,
        [item],
        collective,
    )

    assert result.observations[0] == item
    assert item.state == "active"
    assert item.evidence_id == 1
    assert item.source_profile == "Horus"
    assert item.source_memory_id == 100
