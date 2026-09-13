from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable


@dataclass(frozen=True)
class EntityHistoricalObservation:
    """
    One evidence-backed historical observation about an entity.

    This is a derived/descriptive record. It never mutates the current
    entity record and never rewrites temporal evidence.
    """

    entity_id: int | str
    state: str
    evidence_id: int | str
    source_profile: str
    source_memory_id: int | str
    valid_from: str | None = None
    valid_to: str | None = None
    precision: str = "unknown"
    confidence: float = 0.0

    def __post_init__(self) -> None:
        if isinstance(self.entity_id, bool):
            raise ValueError("entity_id must not be bool")
        if not str(self.entity_id).strip():
            raise ValueError("entity_id is required")

        if not self.state or not self.state.strip():
            raise ValueError("state is required")

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
class EntityHistoricalTransition:
    entity_id: int | str
    from_state: str
    to_state: str
    evidence_ids: tuple[int | str, ...]
    from_valid_from: str | None
    to_valid_from: str | None

    @property
    def evidence_count(self) -> int:
        return len(self.evidence_ids)


@dataclass(frozen=True)
class EntityHistoricalState:
    """
    Deterministic historical view of an entity.

    The current Entity record remains authoritative for current state.
    This object describes what the temporal evidence says was observed
    historically.
    """

    entity_id: int | str
    observations: tuple[EntityHistoricalObservation, ...] = field(
        default_factory=tuple
    )
    transitions: tuple[EntityHistoricalTransition, ...] = field(
        default_factory=tuple
    )

    @property
    def observation_count(self) -> int:
        return len(self.observations)

    @property
    def transition_count(self) -> int:
        return len(self.transitions)

    @property
    def states(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(o.state for o in self.observations))

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


class EntityHistoricalStateBuilder:
    """
    Builds an entity's historical state from already-governed observations.

    Input observations must already have passed temporal evidence governance.
    This class deliberately does not perform promotion, revocation, or
    provenance decisions.
    """

    @staticmethod
    def build(
        entity_id: int | str,
        observations: Iterable[EntityHistoricalObservation],
    ) -> EntityHistoricalState:
        ordered = sorted(
            observations,
            key=lambda o: (
                o.valid_from is None,
                o.valid_from or "",
                o.valid_to is None,
                o.valid_to or "",
                str(o.state),
                str(o.evidence_id),
                o.source_profile,
                str(o.source_memory_id),
            ),
        )

        transitions: list[EntityHistoricalTransition] = []

        previous: EntityHistoricalObservation | None = None

        for observation in ordered:
            if previous is not None and previous.state != observation.state:
                transitions.append(
                    EntityHistoricalTransition(
                        entity_id=entity_id,
                        from_state=previous.state,
                        to_state=observation.state,
                        evidence_ids=(
                            previous.evidence_id,
                            observation.evidence_id,
                        ),
                        from_valid_from=previous.valid_from,
                        to_valid_from=observation.valid_from,
                    )
                )

            previous = observation

        return EntityHistoricalState(
            entity_id=entity_id,
            observations=tuple(ordered),
            transitions=tuple(transitions),
        )


def build_entity_historical_state(
    entity_id: int | str,
    observations: Iterable[EntityHistoricalObservation],
) -> EntityHistoricalState:
    return EntityHistoricalStateBuilder.build(entity_id, observations)
