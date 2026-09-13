from src.domain.entity_historical_state import (
    EntityHistoricalObservation,
    EntityHistoricalStateBuilder,
)
from src.domain.relationship_historical_state import (
    RelationshipHistoricalObservation,
    RelationshipHistoricalStateBuilder,
)
from src.services.temporal_historical_summary_service import (
    TemporalHistoricalSummaryService,
)


def test_entity_service_delegates_to_summary_builder():
    history = EntityHistoricalStateBuilder.build(
        1,
        [
            EntityHistoricalObservation(
                entity_id=1,
                state="active",
                evidence_id="te-1",
                source_profile="Horus",
                source_memory_id=1,
                valid_from="2025-01-01",
                precision="day",
                confidence=0.9,
            )
        ],
    )

    result = TemporalHistoricalSummaryService.summarize_entity(history)

    assert result.entity_id == 1
    assert result.observation_count == 1
    assert result.evidence_count == 1


def test_relationship_service_delegates_to_summary_builder():
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
                precision="day",
                confidence=0.9,
            )
        ],
    )

    result = TemporalHistoricalSummaryService.summarize_relationship(history)

    assert result.source_entity_id == 1
    assert result.target_entity_id == 2
    assert result.evidence_count == 1
