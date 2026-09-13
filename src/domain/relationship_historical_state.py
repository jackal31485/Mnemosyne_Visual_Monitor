from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class RelationshipHistoricalObservation:
    """
    One evidence-backed historical observation of a relationship.

    This is descriptive state only. It does not replace or mutate the
    current relationship/Edge record.
    """

    source_entity_id: int | str
    target_entity_id: int | str
    relation: str
    evidence_id: int | str
    source_profile: str
    source_memory_id: int | str
    valid_from: str | None = None
    valid_to: str | None = None
    precision: str = "unknown"
    confidence: float = 0.0

    def __post_init__(self) -> None:
        if isinstance(self.source_entity_id, bool):
            raise ValueError("source_entity_id must not be bool")
        if isinstance(self.target_entity_id, bool):
            raise ValueError("target_entity_id must not be bool")

        if not str(self.source_entity_id).strip():
            raise ValueError("source_entity_id is required")
        if not str(self.target_entity_id).strip():
            raise ValueError("target_entity_id is required")

        if str(self.source_entity_id) == str(self.target_entity_id):
            raise ValueError("relationship cannot reference itself")

        if not self.relation or not self.relation.strip():
            raise ValueError("relation is required")

        if isinstance(self.evidence_id, bool):
            raise ValueError("evidence_id must not be bool")
        if not str(self.evidence_id).strip():
            raise ValueError("evidence_id is required")

        if not self.source_profile or not self.source_profile.strip():
            raise ValueError("source_profile is required")

        if not str(self.source_memory_id).strip():
            raise ValueError("source_memory_id is required")

        if self.precision not in {
            "unknown",
            "year",
            "month",
            "day",
            "hour",
            "minute",
            "second",
        }:
            raise ValueError(f"unsupported precision: {self.precision}")

        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

        if self.valid_from is None and self.valid_to is not None:
            raise ValueError("valid_to cannot exist without valid_from")

        if (
            self.valid_from is not None
            and self.valid_to is not None
            and self.valid_to < self.valid_from
        ):
            raise ValueError("valid_to cannot precede valid_from")


@dataclass(frozen=True)
class RelationshipHistoricalTransition:
    source_entity_id: int | str
    target_entity_id: int | str
    relation: str
    from_active: bool
    to_active: bool
    evidence_ids: tuple[int | str, ...]
    from_valid_from: str | None
    to_valid_from: str | None

    @property
    def evidence_count(self) -> int:
        return len(self.evidence_ids)


@dataclass(frozen=True)
class RelationshipHistoricalState:
    """
    Deterministic historical view of one relationship.

    ``active`` is the observed historical relationship state. It must not
    be interpreted as the current relationship state.
    """

    source_entity_id: int | str
    target_entity_id: int | str
    relation: str
    observations: tuple[RelationshipHistoricalObservation, ...] = field(
        default_factory=tuple
    )
    transitions: tuple[RelationshipHistoricalTransition, ...] = field(
        default_factory=tuple
    )

    @property
    def observation_count(self) -> int:
        return len(self.observations)

    @property
    def transition_count(self) -> int:
        return len(self.transitions)

    @property
    def known_timed_observation_count(self) -> int:
        return sum(o.valid_from is not None for o in self.observations)

    @property
    def unknown_timed_observation_count(self) -> int:
        return self.observation_count - self.known_timed_observation_count

    @property
    def complete(self) -> bool:
        return bool(self.observations) and all(
            o.valid_from is not None for o in self.observations
        )

    @property
    def observed_active(self) -> bool | None:
        if not self.observations:
            return None
        return True


class RelationshipHistoricalStateBuilder:
    """
    Build a relationship history from governed observations.

    A relationship observation represents existence of the relationship
    during the supplied temporal evidence interval. The builder does not
    invent inactive periods between observations. Therefore an observed
    relationship does not automatically produce an ``active -> inactive``
    transition when evidence stops.
    """

    @staticmethod
    def build(
        source_entity_id: int | str,
        target_entity_id: int | str,
        relation: str,
        observations: Iterable[RelationshipHistoricalObservation],
    ) -> RelationshipHistoricalState:
        ordered = sorted(
            (
                observation
                for observation in observations
                if str(observation.source_entity_id)
                == str(source_entity_id)
                and str(observation.target_entity_id)
                == str(target_entity_id)
                and observation.relation == relation
            ),
            key=lambda o: (
                o.valid_from is None,
                o.valid_from or "",
                o.valid_to is None,
                o.valid_to or "",
                str(o.evidence_id),
                o.source_profile,
                str(o.source_memory_id),
            ),
        )

        # Only transitions explicitly supported by observations are emitted.
        # Evidence ending does NOT mean the relationship became inactive.
        transitions: list[RelationshipHistoricalTransition] = []

        for previous, current in zip(ordered, ordered[1:]):
            if (
                previous.valid_from is not None
                and current.valid_from is not None
                and previous.valid_to is not None
                and previous.valid_to < current.valid_from
            ):
                # A temporal gap is represented as unknown relationship state,
                # not as an inferred inactive state.
                continue

        return RelationshipHistoricalState(
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            relation=relation,
            observations=tuple(ordered),
            transitions=tuple(transitions),
        )


def build_relationship_historical_state(
    source_entity_id: int | str,
    target_entity_id: int | str,
    relation: str,
    observations: Iterable[RelationshipHistoricalObservation],
) -> RelationshipHistoricalState:
    return RelationshipHistoricalStateBuilder.build(
        source_entity_id,
        target_entity_id,
        relation,
        observations,
    )
