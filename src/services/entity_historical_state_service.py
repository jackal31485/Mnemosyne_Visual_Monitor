from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from src.domain.entity_historical_state import (
    EntityHistoricalObservation,
    EntityHistoricalState,
    build_entity_historical_state,
)


class EntityHistoricalStateService:
    """
    Build a descriptive historical state view from governed temporal
    observations.

    Governance boundary:

      temporal evidence
            |
            v
      collective lifecycle
            |
            +-- promoted
            +-- not revoked
            +-- source profile matches
            +-- source memory matches
            |
            v
      EntityHistoricalState

    This service never mutates entity records or temporal evidence.
    """

    @staticmethod
    def build(
        entity_id: int | str,
        observations: Iterable[EntityHistoricalObservation],
    ) -> EntityHistoricalState:
        eligible = [
            observation
            for observation in observations
            if str(observation.entity_id) == str(entity_id)
        ]

        return build_entity_historical_state(entity_id, eligible)

    @staticmethod
    def build_governed(
        entity_id: int | str,
        observations: Iterable[EntityHistoricalObservation],
        collective: Any,
    ) -> EntityHistoricalState:
        """
        Build historical state using the existing Collective lifecycle
        contract.

        An observation is eligible only when:
          * its collective entry exists;
          * it is promoted;
          * it is not revoked;
          * its source profile matches the collective entry;
          * its source memory matches the collective entry.

        Ineligible observations are excluded rather than rewritten.
        """

        eligible: list[EntityHistoricalObservation] = []

        for observation in observations:
            if str(observation.entity_id) != str(entity_id):
                continue

            if EntityHistoricalStateService._is_governed(
                observation,
                collective,
            ):
                eligible.append(observation)

        return build_entity_historical_state(entity_id, eligible)

    @staticmethod
    def _is_governed(
        observation: EntityHistoricalObservation,
        collective: Any,
    ) -> bool:
        entry_id = EntityHistoricalStateService._numeric_entry_id(
            observation.evidence_id
        )

        if entry_id is None:
            return False

        lifecycle = collective.get_lifecycle_state(entry_id)

        if lifecycle is None:
            return False

        validated_at, is_revoked, _reason, is_promoted = lifecycle

        if validated_at is None:
            return False

        if is_revoked:
            return False

        if not is_promoted:
            return False

        entry = collective.get_by_id(entry_id)

        if entry is None:
            return False

        source_profile = entry[1]
        origin_memory_id = entry[2]

        if source_profile != observation.source_profile:
            return False

        if str(origin_memory_id) != str(observation.source_memory_id):
            return False

        return True

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
        entity_id: int | str,
        observations: Iterable[Mapping[str, Any]],
    ) -> EntityHistoricalState:
        normalized = [
            EntityHistoricalObservation(
                entity_id=item["entity_id"],
                state=item["state"],
                evidence_id=item["evidence_id"],
                source_profile=item["source_profile"],
                source_memory_id=item["source_memory_id"],
                valid_from=item.get("valid_from"),
                valid_to=item.get("valid_to"),
                precision=item.get("precision", "unknown"),
                confidence=float(item.get("confidence", 0.0)),
            )
            for item in observations
        ]

        return EntityHistoricalStateService.build(entity_id, normalized)

    @staticmethod
    def from_timeline(
        entity_id: int | str,
        timeline: Any,
    ) -> EntityHistoricalState:
        if isinstance(timeline, Mapping):
            raw_items = timeline.get("observations")
            if raw_items is None:
                raw_items = timeline.get("entries", ())
        else:
            raw_items = getattr(timeline, "observations", None)
            if raw_items is None:
                raw_items = getattr(timeline, "entries", ())

        observations = [
            EntityHistoricalStateService._normalize_observation(item, entity_id)
            for item in raw_items
        ]

        return EntityHistoricalStateService.build(entity_id, observations)

    @staticmethod
    def from_timeline_governed(
        entity_id: int | str,
        timeline: Any,
        collective: Any,
    ) -> EntityHistoricalState:
        if isinstance(timeline, Mapping):
            raw_items = timeline.get("observations")
            if raw_items is None:
                raw_items = timeline.get("entries", ())
        else:
            raw_items = getattr(timeline, "observations", None)
            if raw_items is None:
                raw_items = getattr(timeline, "entries", ())

        observations = [
            EntityHistoricalStateService._normalize_observation(item, entity_id)
            for item in raw_items
        ]

        return EntityHistoricalStateService.build_governed(
            entity_id,
            observations,
            collective,
        )

    @staticmethod
    def _normalize_observation(
        item: Any,
        requested_entity_id: int | str,
    ) -> EntityHistoricalObservation:
        if isinstance(item, EntityHistoricalObservation):
            return item

        if isinstance(item, Mapping):
            get = item.get
        else:
            get = lambda key, default=None: getattr(item, key, default)

        entity_id = get("entity_id", requested_entity_id)

        state = get("state")
        if state is None:
            state = get("state_value")
        if state is None:
            state = get("value")

        evidence_id = get("evidence_id")
        if evidence_id is None:
            evidence_id = get("temporal_evidence_id")

        source_profile = get("source_profile")
        source_memory_id = get("source_memory_id")

        valid_from = get("valid_from")
        if valid_from is None:
            valid_from = get("start")

        valid_to = get("valid_to")
        if valid_to is None:
            valid_to = get("end")

        precision = get("precision", "unknown")
        confidence = float(get("confidence", 0.0))

        if state is None:
            raise ValueError("timeline observation is missing state")

        if evidence_id is None:
            raise ValueError("timeline observation is missing evidence_id")

        if source_profile is None:
            raise ValueError("timeline observation is missing source_profile")

        if source_memory_id is None:
            raise ValueError("timeline observation is missing source_memory_id")

        return EntityHistoricalObservation(
            entity_id=entity_id,
            state=str(state),
            evidence_id=evidence_id,
            source_profile=str(source_profile),
            source_memory_id=source_memory_id,
            valid_from=valid_from,
            valid_to=valid_to,
            precision=precision,
            confidence=confidence,
        )
