from __future__ import annotations

from src.domain.entity_historical_state import EntityHistoricalState
from src.domain.relationship_historical_state import RelationshipHistoricalState
from src.domain.temporal_historical_summary import (
    EntityTemporalSummary,
    RelationshipTemporalSummary,
    summarize_entity_history,
    summarize_relationship_history,
)


class TemporalHistoricalSummaryService:
    """
    Service boundary for evidence-backed temporal summaries.

    This layer is intentionally descriptive. It does not infer missing
    temporal states or convert absence of evidence into historical claims.
    """

    @staticmethod
    def summarize_entity(
        history: EntityHistoricalState,
    ) -> EntityTemporalSummary:
        return summarize_entity_history(history)

    @staticmethod
    def summarize_relationship(
        history: RelationshipHistoricalState,
    ) -> RelationshipTemporalSummary:
        return summarize_relationship_history(history)
