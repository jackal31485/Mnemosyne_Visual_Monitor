from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from src.domain.entity_historical_state import EntityHistoricalState
from src.domain.relationship_historical_state import RelationshipHistoricalState


@dataclass(frozen=True)
class TemporalSummaryEvidence:
    """
    Provenance attached to one summary statement.

    A summary statement must remain traceable to its underlying temporal
    evidence and source memory/profile.
    """

    evidence_id: int | str
    source_profile: str
    source_memory_id: int | str
    confidence: float

    def __post_init__(self) -> None:
        if isinstance(self.evidence_id, bool):
            raise ValueError("evidence_id must not be bool")
        if not str(self.evidence_id).strip():
            raise ValueError("evidence_id is required")

        if not self.source_profile or not self.source_profile.strip():
            raise ValueError("source_profile is required")

        if not str(self.source_memory_id).strip():
            raise ValueError("source_memory_id is required")

        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("confidence must be between 0 and 1")


@dataclass(frozen=True)
class TemporalSummaryStatement:
    """
    One descriptive temporal statement.

    ``statement`` is generated only from supplied historical observations.
    """

    statement: str
    evidence: tuple[TemporalSummaryEvidence, ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        if not self.statement or not self.statement.strip():
            raise ValueError("statement is required")

    @property
    def evidence_count(self) -> int:
        return len(self.evidence)


@dataclass(frozen=True)
class EntityTemporalSummary:
    entity_id: int | str
    statements: tuple[TemporalSummaryStatement, ...] = field(
        default_factory=tuple
    )
    observed_states: tuple[str, ...] = field(default_factory=tuple)
    observation_count: int = 0
    transition_count: int = 0
    known_timed_observations: int = 0
    unknown_timed_observations: int = 0
    complete: bool = False

    @property
    def evidence_count(self) -> int:
        return sum(statement.evidence_count for statement in self.statements)


@dataclass(frozen=True)
class RelationshipTemporalSummary:
    source_entity_id: int | str
    target_entity_id: int | str
    relation: str
    statements: tuple[TemporalSummaryStatement, ...] = field(
        default_factory=tuple
    )
    observation_count: int = 0
    known_timed_observations: int = 0
    unknown_timed_observations: int = 0
    complete: bool = False

    @property
    def evidence_count(self) -> int:
        return sum(statement.evidence_count for statement in self.statements)


class TemporalHistoricalSummaryBuilder:
    """
    Produce deterministic, evidence-backed descriptive summaries.

    No temporal inference is performed here.
    """

    @staticmethod
    def entity(
        history: EntityHistoricalState,
    ) -> EntityTemporalSummary:
        statements: list[TemporalSummaryStatement] = []

        for state in history.states:
            observations = tuple(
                item
                for item in history.observations
                if item.state == state
            )

            evidence = tuple(
                TemporalSummaryEvidence(
                    evidence_id=item.evidence_id,
                    source_profile=item.source_profile,
                    source_memory_id=item.source_memory_id,
                    confidence=item.confidence,
                )
                for item in observations
            )

            statements.append(
                TemporalSummaryStatement(
                    statement=(
                        f"Entity {history.entity_id} was observed in "
                        f"state '{state}'."
                    ),
                    evidence=evidence,
                )
            )

        if history.transition_count:
            for transition in history.transitions:
                evidence = tuple(
                    TemporalSummaryEvidence(
                        evidence_id=evidence_id,
                        source_profile=next(
                            (
                                item.source_profile
                                for item in history.observations
                                if item.evidence_id == evidence_id
                            ),
                            "unknown",
                        ),
                        source_memory_id=next(
                            (
                                item.source_memory_id
                                for item in history.observations
                                if item.evidence_id == evidence_id
                            ),
                            evidence_id,
                        ),
                        confidence=next(
                            (
                                item.confidence
                                for item in history.observations
                                if item.evidence_id == evidence_id
                            ),
                            0.0,
                        ),
                    )
                    for evidence_id in transition.evidence_ids
                )

                statements.append(
                    TemporalSummaryStatement(
                        statement=(
                            f"Entity {history.entity_id} has an "
                            f"evidence-backed observed transition from "
                            f"'{transition.from_state}' to "
                            f"'{transition.to_state}'."
                        ),
                        evidence=evidence,
                    )
                )

        statements.sort(
            key=lambda item: (
                item.statement,
                tuple(str(e.evidence_id) for e in item.evidence),
            )
        )

        return EntityTemporalSummary(
            entity_id=history.entity_id,
            statements=tuple(statements),
            observed_states=history.states,
            observation_count=history.observation_count,
            transition_count=history.transition_count,
            known_timed_observations=history.known_timed_observation_count,
            unknown_timed_observations=history.unknown_timed_observation_count,
            complete=history.complete,
        )

    @staticmethod
    def relationship(
        history: RelationshipHistoricalState,
    ) -> RelationshipTemporalSummary:
        evidence = tuple(
            TemporalSummaryEvidence(
                evidence_id=item.evidence_id,
                source_profile=item.source_profile,
                source_memory_id=item.source_memory_id,
                confidence=item.confidence,
            )
            for item in history.observations
        )

        statements: tuple[TemporalSummaryStatement, ...] = ()

        if history.observation_count:
            statements = (
                TemporalSummaryStatement(
                    statement=(
                        f"Relationship "
                        f"{history.source_entity_id} -> "
                        f"{history.target_entity_id} "
                        f"('{history.relation}') was observed."
                    ),
                    evidence=evidence,
                ),
            )

        return RelationshipTemporalSummary(
            source_entity_id=history.source_entity_id,
            target_entity_id=history.target_entity_id,
            relation=history.relation,
            statements=statements,
            observation_count=history.observation_count,
            known_timed_observations=history.known_timed_observation_count,
            unknown_timed_observations=history.unknown_timed_observation_count,
            complete=history.complete,
        )


def summarize_entity_history(
    history: EntityHistoricalState,
) -> EntityTemporalSummary:
    return TemporalHistoricalSummaryBuilder.entity(history)


def summarize_relationship_history(
    history: RelationshipHistoricalState,
) -> RelationshipTemporalSummary:
    return TemporalHistoricalSummaryBuilder.relationship(history)
