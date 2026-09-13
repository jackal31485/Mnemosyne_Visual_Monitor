from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from src.domain.relationship_historical_state import (
    RelationshipHistoricalObservation,
    RelationshipHistoricalState,
    build_relationship_historical_state,
)


class RelationshipHistoricalStateService:
    """
    Build a descriptive historical state for an existing relationship.

    The current relationship/Edge remains authoritative for present state.
    Historical state is derived only from eligible evidence.
    """

    @staticmethod
    def build(
        source_entity_id: int | str,
        target_entity_id: int | str,
        relation: str,
        observations: Iterable[RelationshipHistoricalObservation],
    ) -> RelationshipHistoricalState:
        return build_relationship_historical_state(
            source_entity_id,
            target_entity_id,
            relation,
            observations,
        )

    @staticmethod
    def build_governed(
        source_entity_id: int | str,
        target_entity_id: int | str,
        relation: str,
        observations: Iterable[RelationshipHistoricalObservation],
        collective: Any,
    ) -> RelationshipHistoricalState:
        eligible = [
            observation
            for observation in observations
            if RelationshipHistoricalStateService._matches_relationship(
                observation,
                source_entity_id,
                target_entity_id,
                relation,
            )
            and RelationshipHistoricalStateService._is_governed(
                observation,
                collective,
            )
        ]

        return build_relationship_historical_state(
            source_entity_id,
            target_entity_id,
            relation,
            eligible,
        )

    @staticmethod
    def _matches_relationship(
        observation: RelationshipHistoricalObservation,
        source_entity_id: int | str,
        target_entity_id: int | str,
        relation: str,
    ) -> bool:
        return (
            str(observation.source_entity_id) == str(source_entity_id)
            and str(observation.target_entity_id) == str(target_entity_id)
            and observation.relation == relation
        )

    @staticmethod
    def _is_governed(
        observation: RelationshipHistoricalObservation,
        collective: Any,
    ) -> bool:
        entry_id = RelationshipHistoricalStateService._numeric_entry_id(
            observation.evidence_id
        )

        if entry_id is None:
            return False

        lifecycle = collective.get_lifecycle_state(entry_id)

        if lifecycle is None:
            return False

        validated_at, is_revoked, _reason, is_promoted = lifecycle

        if validated_at is None or is_revoked or not is_promoted:
            return False

        entry = collective.get_by_id(entry_id)

        if entry is None:
            return False

        source_profile = entry[1]
        origin_memory_id = entry[2]

        return (
            source_profile == observation.source_profile
            and str(origin_memory_id) == str(observation.source_memory_id)
        )

    @staticmethod
    def _numeric_entry_id(evidence_id: int | str) -> int | None:
        if isinstance(evidence_id, bool):
            return None

        if isinstance(evidence_id, int):
            return evidence_id

        value = str(evidence_id)

        if value.isdigit():
            return int(value)

        return None

    @staticmethod
    def from_mappings(
        source_entity_id: int | str,
        target_entity_id: int | str,
        relation: str,
        observations: Iterable[Mapping[str, Any]],
    ) -> RelationshipHistoricalState:
        normalized = [
            RelationshipHistoricalObservation(
                source_entity_id=item["source_entity_id"],
                target_entity_id=item["target_entity_id"],
                relation=item["relation"],
                evidence_id=item.get(
                    "evidence_id",
                    item.get("temporal_evidence_id"),
                ),
                source_profile=item["source_profile"],
                source_memory_id=item["source_memory_id"],
                valid_from=item.get("valid_from", item.get("start")),
                valid_to=item.get("valid_to", item.get("end")),
                precision=item.get("precision", "unknown"),
                confidence=float(item.get("confidence", 0.0)),
            )
            for item in observations
        ]

        return RelationshipHistoricalStateService.build(
            source_entity_id,
            target_entity_id,
            relation,
            normalized,
        )
