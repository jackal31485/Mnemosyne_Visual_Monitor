"""Phase 13A governed mental-model contract.

A mental model is derived knowledge.  This contract deliberately keeps it
separate from source memories, observations, and evidence while preserving
the identifiers required to trace the derivation.

The contract is persistence-agnostic.  Candidate generation, validation,
confidence calculation, lifecycle persistence, and synthesis belong to later
Phase 13 stages.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Iterable


def _required_text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    return value.strip()


def _identifier_tuple(name: str, values: Iterable[str]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise TypeError(f"{name} must be an iterable of identifiers, not text")

    materialized = tuple(values)
    if any(not isinstance(value, str) or not value.strip() for value in materialized):
        raise ValueError(f"{name} must contain non-empty text")

    normalized = tuple(value.strip() for value in materialized)
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{name} must not contain duplicates")

    return tuple(sorted(normalized))


def _confidence(value: float) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise TypeError("confidence must be numeric")
    value = float(value)
    if not 0.0 <= value <= 1.0:
        raise ValueError("confidence must be between 0.0 and 1.0")
    return value


class MentalModelType(str, Enum):
    """Constrained Phase 13 mental-model categories."""

    CONCEPT = "concept"
    PATTERN = "pattern"
    RELATIONSHIP = "relationship"
    TEMPORAL = "temporal"
    EXPECTATION = "expectation"


class MentalModelStatus(str, Enum):
    """Governed lifecycle states for a mental-model version."""

    CANDIDATE = "candidate"
    VALIDATED = "validated"
    ACTIVE = "active"
    STALE = "stale"
    SUPERSEDED = "superseded"
    REVOKED = "revoked"


_ALLOWED_TRANSITIONS: dict[MentalModelStatus, frozenset[MentalModelStatus]] = {
    MentalModelStatus.CANDIDATE: frozenset(
        {MentalModelStatus.VALIDATED, MentalModelStatus.REVOKED}
    ),
    MentalModelStatus.VALIDATED: frozenset(
        {MentalModelStatus.ACTIVE, MentalModelStatus.REVOKED}
    ),
    MentalModelStatus.ACTIVE: frozenset(
        {
            MentalModelStatus.STALE,
            MentalModelStatus.SUPERSEDED,
            MentalModelStatus.REVOKED,
        }
    ),
    MentalModelStatus.STALE: frozenset(
        {MentalModelStatus.ACTIVE, MentalModelStatus.SUPERSEDED, MentalModelStatus.REVOKED}
    ),
    MentalModelStatus.SUPERSEDED: frozenset(),
    MentalModelStatus.REVOKED: frozenset(),
}


@dataclass(frozen=True, slots=True)
class MentalModelProvenance:
    """Explicit derivation lineage for one mental-model version.

    The IDs point to governed lower-level records.  This object contains no
    source-memory content and therefore cannot replace the underlying records.
    """

    derivation_method: str
    observation_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    memory_ids: tuple[str, ...]
    source_profiles: tuple[str, ...]
    entity_ids: tuple[str, ...] = ()
    relationship_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "derivation_method",
            _required_text("derivation_method", self.derivation_method),
        )
        for name in (
            "observation_ids",
            "evidence_ids",
            "memory_ids",
            "source_profiles",
            "entity_ids",
            "relationship_ids",
        ):
            object.__setattr__(
                self,
                name,
                _identifier_tuple(name, getattr(self, name)),
            )

        if not self.evidence_ids:
            raise ValueError("provenance must contain at least one evidence ID")
        if not self.memory_ids:
            raise ValueError("provenance must contain at least one source memory ID")
        if not self.source_profiles:
            raise ValueError("provenance must contain at least one source profile")



@dataclass(frozen=True, slots=True)
class MentalModel:
    """Immutable, versioned representation of derived knowledge."""

    model_id: str
    model_type: MentalModelType
    title: str
    description: str
    entity_ids: tuple[str, ...]
    relationship_ids: tuple[str, ...]
    supporting_observation_ids: tuple[str, ...]
    supporting_evidence_ids: tuple[str, ...]
    supporting_memory_ids: tuple[str, ...]
    source_profiles: tuple[str, ...]
    temporal_scope: tuple[str, ...]
    confidence: float
    status: MentalModelStatus
    version: int
    created_at: datetime
    updated_at: datetime
    provenance: MentalModelProvenance
    derivation_method: str
    contradictory_evidence_ids: tuple[str, ...]
    staleness_state: str = "current"

    def __post_init__(self) -> None:
        object.__setattr__(self, "model_id", _required_text("model_id", self.model_id))
        object.__setattr__(self, "title", _required_text("title", self.title))
        object.__setattr__(
            self,
            "description",
            _required_text("description", self.description),
        )

        if not isinstance(self.model_type, MentalModelType):
            raise TypeError("model_type must be a MentalModelType")
        if not isinstance(self.status, MentalModelStatus):
            raise TypeError("status must be a MentalModelStatus")

        if not isinstance(self.version, int) or isinstance(self.version, bool):
            raise TypeError("version must be an int")
        if self.version < 1:
            raise ValueError("version must be at least 1")

        if not isinstance(self.created_at, datetime):
            raise TypeError("created_at must be a datetime")
        if not isinstance(self.updated_at, datetime):
            raise TypeError("updated_at must be a datetime")
        if self.updated_at < self.created_at:
            raise ValueError("updated_at must not be earlier than created_at")

        object.__setattr__(self, "confidence", _confidence(self.confidence))

        for name in (
            "entity_ids",
            "relationship_ids",
            "supporting_observation_ids",
            "supporting_evidence_ids",
            "supporting_memory_ids",
            "source_profiles",
            "temporal_scope",
            "contradictory_evidence_ids",
        ):
            object.__setattr__(
                self,
                name,
                _identifier_tuple(name, getattr(self, name)),
            )

        if not isinstance(self.provenance, MentalModelProvenance):
            raise TypeError("provenance must be a MentalModelProvenance")

        object.__setattr__(
            self,
            "derivation_method",
            _required_text("derivation_method", self.derivation_method),
        )
        object.__setattr__(
            self,
            "staleness_state",
            _required_text("staleness_state", self.staleness_state),
        )

        if self.status is MentalModelStatus.ACTIVE:
            if not self.supporting_observation_ids:
                raise ValueError("active model requires supporting observations")
            if not self.supporting_evidence_ids:
                raise ValueError("active model requires supporting evidence")
            if not self.supporting_memory_ids:
                raise ValueError("active model requires supporting memories")
            if not self.source_profiles:
                raise ValueError("active model requires source profiles")

        if not set(self.contradictory_evidence_ids).issubset(
            set(self.supporting_evidence_ids)
        ):
            raise ValueError(
                "contradictory evidence must be drawn from supporting evidence"
            )

        if set(self.provenance.observation_ids) != set(
            self.supporting_observation_ids
        ):
            raise ValueError("provenance observation IDs must match model support")

        if set(self.provenance.evidence_ids) != set(self.supporting_evidence_ids):
            raise ValueError("provenance evidence IDs must match model support")

        if set(self.provenance.memory_ids) != set(self.supporting_memory_ids):
            raise ValueError("provenance memory IDs must match model support")

        if set(self.provenance.source_profiles) != set(self.source_profiles):
            raise ValueError("provenance profiles must match model source profiles")

        if set(self.provenance.entity_ids) != set(self.entity_ids):
            raise ValueError("provenance entity IDs must match model entities")

        if set(self.provenance.relationship_ids) != set(self.relationship_ids):
            raise ValueError(
                "provenance relationship IDs must match model relationships"
            )

        if self.provenance.derivation_method != self.derivation_method:
            raise ValueError(
                "provenance derivation method must match model derivation method"
            )

    @property
    def is_currently_retrievable(self) -> bool:
        """Return whether this model version is eligible for current retrieval."""

        return self.status in {
            MentalModelStatus.VALIDATED,
            MentalModelStatus.ACTIVE,
        }

    @property
    def is_derived(self) -> bool:
        """Explicitly distinguish the record from source memories/observations."""

        return True

    def can_transition_to(self, new_status: MentalModelStatus) -> bool:
        """Return whether the lifecycle transition is explicitly allowed."""

        if not isinstance(new_status, MentalModelStatus):
            raise TypeError("new_status must be a MentalModelStatus")
        return new_status in _ALLOWED_TRANSITIONS[self.status]

    def transition_to(self, new_status: MentalModelStatus) -> "MentalModel":
        """Return a new version-level record with the requested lifecycle state.

        The historical instance is never mutated.
        """

        if not self.can_transition_to(new_status):
            raise ValueError(
                f"invalid mental-model transition: "
                f"{self.status.value} -> {new_status.value}"
            )

        return MentalModel(
            model_id=self.model_id,
            model_type=self.model_type,
            title=self.title,
            description=self.description,
            entity_ids=self.entity_ids,
            relationship_ids=self.relationship_ids,
            supporting_observation_ids=self.supporting_observation_ids,
            supporting_evidence_ids=self.supporting_evidence_ids,
            supporting_memory_ids=self.supporting_memory_ids,
            source_profiles=self.source_profiles,
            temporal_scope=self.temporal_scope,
            confidence=self.confidence,
            status=new_status,
            version=self.version,
            created_at=self.created_at,
            updated_at=self.updated_at,
            provenance=self.provenance,
            derivation_method=self.derivation_method,
            contradictory_evidence_ids=self.contradictory_evidence_ids,
            staleness_state=(
                "stale"
                if new_status is MentalModelStatus.STALE
                else self.staleness_state
            ),
        )


__all__ = [
    "MentalModel",
    "MentalModelProvenance",
    "MentalModelStatus",
    "MentalModelType",
]
