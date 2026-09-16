"""Phase 13E mental-model versioning and staleness lifecycle.

This module provides deterministic lifecycle operations for governed mental
models without synthesizing new model content.

Phase 13E responsibilities:
- version lineage
- dependency tracking
- staleness detection
- refresh into a new immutable version
- revocation propagation

The module never mutates source memories, observations, evidence, entities,
or relationships.  Historical mental-model versions remain auditable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from .mental_model import MentalModel, MentalModelProvenance, MentalModelStatus


class MentalModelLifecycleError(ValueError):
    """Raised when a mental-model lifecycle operation is invalid."""


@dataclass(frozen=True, slots=True)
class MentalModelDependencySnapshot:
    """Immutable governed dependency snapshot for one model version."""

    observation_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    memory_ids: tuple[str, ...]
    relationship_ids: tuple[str, ...]
    source_profiles: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "observation_ids",
            "evidence_ids",
            "memory_ids",
            "relationship_ids",
            "source_profiles",
        ):
            values = getattr(self, name)
            if isinstance(values, (str, bytes)):
                raise TypeError(f"{name} must be an iterable of identifiers")

            normalized = tuple(
                sorted(
                    value.strip()
                    for value in values
                    if isinstance(value, str) and value.strip()
                )
            )

            if len(normalized) != len(set(normalized)):
                raise ValueError(f"{name} must not contain duplicates")

            object.__setattr__(self, name, normalized)

    @classmethod
    def from_model(cls, model: MentalModel) -> "MentalModelDependencySnapshot":
        """Create a dependency snapshot from a governed mental-model version."""

        if not isinstance(model, MentalModel):
            raise TypeError("model must be a MentalModel")

        return cls(
            observation_ids=model.supporting_observation_ids,
            evidence_ids=model.supporting_evidence_ids,
            memory_ids=model.supporting_memory_ids,
            relationship_ids=model.relationship_ids,
            source_profiles=model.source_profiles,
        )

    def diff(
        self,
        current: "MentalModelDependencySnapshot",
    ) -> dict[str, tuple[str, ...]]:
        """Return deterministic dependency additions/removals."""

        if not isinstance(current, MentalModelDependencySnapshot):
            raise TypeError(
                "current must be a MentalModelDependencySnapshot"
            )

        differences: dict[str, tuple[str, ...]] = {}

        for name in (
            "observation_ids",
            "evidence_ids",
            "memory_ids",
            "relationship_ids",
            "source_profiles",
        ):
            previous = set(getattr(self, name))
            now = set(getattr(current, name))

            removed = tuple(sorted(previous - now))
            added = tuple(sorted(now - previous))

            if removed:
                differences[f"{name}_removed"] = removed

            if added:
                differences[f"{name}_added"] = added

        return differences

    def is_compatible_with(
        self,
        current: "MentalModelDependencySnapshot",
    ) -> bool:
        """Return whether the dependency set remains unchanged."""

        return not self.diff(current)


@dataclass(frozen=True, slots=True)
class DependencyRevocation:
    """A governed dependency invalidation event."""

    dependency_type: str
    dependency_id: str
    reason: str

    def __post_init__(self) -> None:
        for name in (
            "dependency_type",
            "dependency_id",
            "reason",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty text")

            object.__setattr__(self, name, value.strip())


@dataclass(frozen=True, slots=True)
class MentalModelStalenessResult:
    """Deterministic staleness evaluation."""

    stale: bool
    reasons: tuple[str, ...]
    dependency_changes: dict[str, tuple[str, ...]]
    revoked_dependencies: tuple[DependencyRevocation, ...]

    @property
    def is_current(self) -> bool:
        """Return whether the model remains current."""

        return not self.stale


@dataclass(frozen=True, slots=True)
class MentalModelRefreshResult:
    """Result of creating a new lifecycle version."""

    previous_model: MentalModel
    refreshed_model: MentalModel
    dependency_snapshot: MentalModelDependencySnapshot
    staleness: MentalModelStalenessResult


class MentalModelLifecycle:
    """Deterministic lifecycle manager for governed mental models."""

    _METHOD = "phase-13e-versioned-refresh"

    @staticmethod
    def snapshot(
        model: MentalModel,
    ) -> MentalModelDependencySnapshot:
        """Capture the dependencies represented by a model version."""

        return MentalModelDependencySnapshot.from_model(model)

    @staticmethod
    def evaluate_staleness(
        model: MentalModel,
        current_dependencies: MentalModelDependencySnapshot,
        *,
        revoked_dependencies: Iterable[DependencyRevocation] = (),
    ) -> MentalModelStalenessResult:
        """Determine whether a model version is stale.

        A model is stale when:
        - one or more dependencies disappear/change; or
        - a governed dependency is explicitly revoked.

        Adding a dependency alone does not automatically revoke a model;
        it is reported as a dependency change so refresh can be performed
        explicitly.
        """

        if not isinstance(model, MentalModel):
            raise TypeError("model must be a MentalModel")

        if not isinstance(
            current_dependencies,
            MentalModelDependencySnapshot,
        ):
            raise TypeError(
                "current_dependencies must be a "
                "MentalModelDependencySnapshot"
            )

        revocations = tuple(revoked_dependencies)

        if any(
            not isinstance(item, DependencyRevocation)
            for item in revocations
        ):
            raise TypeError(
                "revoked_dependencies must contain "
                "DependencyRevocation values"
            )

        previous = MentalModelDependencySnapshot.from_model(model)
        changes = previous.diff(current_dependencies)

        reasons: list[str] = []

        if changes:
            reasons.append("dependency_changed")

        if revocations:
            reasons.append("dependency_revoked")

        return MentalModelStalenessResult(
            stale=bool(reasons),
            reasons=tuple(sorted(set(reasons))),
            dependency_changes=changes,
            revoked_dependencies=tuple(
                sorted(
                    revocations,
                    key=lambda item: (
                        item.dependency_type,
                        item.dependency_id,
                        item.reason,
                    ),
                )
            ),
        )

    @staticmethod
    def propagate_revocation(
        model: MentalModel,
        revocations: Iterable[DependencyRevocation],
        *,
        occurred_at: datetime | None = None,
    ) -> MentalModel:
        """Propagate dependency revocation to a model version.

        The source records are never changed.  Only the derived model's
        lifecycle state changes.

        Historical terminal states remain terminal.  A revoked dependency
        causes current VALIDATED/ACTIVE/STALE versions to become REVOKED.
        """

        if not isinstance(model, MentalModel):
            raise TypeError("model must be a MentalModel")

        revocations = tuple(revocations)

        if not revocations:
            return model

        if any(
            not isinstance(item, DependencyRevocation)
            for item in revocations
        ):
            raise TypeError(
                "revocations must contain DependencyRevocation values"
            )

        timestamp = occurred_at or model.updated_at

        if not isinstance(timestamp, datetime):
            raise TypeError("occurred_at must be a datetime")

        if model.status in {
            MentalModelStatus.CANDIDATE,
            MentalModelStatus.VALIDATED,
            MentalModelStatus.ACTIVE,
            MentalModelStatus.STALE,
        }:
            return MentalModel(
                model_id=model.model_id,
                model_type=model.model_type,
                title=model.title,
                description=model.description,
                entity_ids=model.entity_ids,
                relationship_ids=model.relationship_ids,
                supporting_observation_ids=model.supporting_observation_ids,
                supporting_evidence_ids=model.supporting_evidence_ids,
                supporting_memory_ids=model.supporting_memory_ids,
                source_profiles=model.source_profiles,
                temporal_scope=model.temporal_scope,
                confidence=model.confidence,
                status=MentalModelStatus.REVOKED,
                version=model.version,
                created_at=model.created_at,
                updated_at=timestamp,
                provenance=model.provenance,
                derivation_method=model.derivation_method,
                contradictory_evidence_ids=model.contradictory_evidence_ids,
                staleness_state="revoked",
            )

        return model

    @classmethod
    def refresh(
        cls,
        model: MentalModel,
        current_dependencies: MentalModelDependencySnapshot,
        *,
        refreshed_at: datetime,
        revoked_dependencies: Iterable[DependencyRevocation] = (),
    ) -> MentalModelRefreshResult:
        """Create a new immutable version of a model.

        Refresh never mutates the supplied model.  The old version becomes
        SUPERSEDED and the returned model receives version + 1.

        Refresh does not synthesize or rewrite model content; content
        synthesis belongs to Phase 13F.
        """

        if not isinstance(model, MentalModel):
            raise TypeError("model must be a MentalModel")

        if not isinstance(
            current_dependencies,
            MentalModelDependencySnapshot,
        ):
            raise TypeError(
                "current_dependencies must be a "
                "MentalModelDependencySnapshot"
            )

        if not isinstance(refreshed_at, datetime):
            raise TypeError("refreshed_at must be a datetime")

        if model.status not in {
            MentalModelStatus.VALIDATED,
            MentalModelStatus.ACTIVE,
            MentalModelStatus.STALE,
        }:
            raise MentalModelLifecycleError(
                "only VALIDATED, ACTIVE, or STALE models may be refreshed"
            )

        revocations = tuple(revoked_dependencies)

        staleness = cls.evaluate_staleness(
            model,
            current_dependencies,
            revoked_dependencies=revocations,
        )

        if staleness.revoked_dependencies:
            raise MentalModelLifecycleError(
                "a model with revoked dependencies cannot be refreshed"
            )

        if not staleness.stale:
            raise MentalModelLifecycleError(
                "refresh requires a stale or changed dependency state"
            )

        previous = MentalModel(
            model_id=model.model_id,
            model_type=model.model_type,
            title=model.title,
            description=model.description,
            entity_ids=model.entity_ids,
            relationship_ids=model.relationship_ids,
            supporting_observation_ids=model.supporting_observation_ids,
            supporting_evidence_ids=model.supporting_evidence_ids,
            supporting_memory_ids=model.supporting_memory_ids,
            source_profiles=model.source_profiles,
            temporal_scope=model.temporal_scope,
            confidence=model.confidence,
            status=MentalModelStatus.SUPERSEDED,
            version=model.version,
            created_at=model.created_at,
            updated_at=refreshed_at,
            provenance=model.provenance,
            derivation_method=model.derivation_method,
            contradictory_evidence_ids=model.contradictory_evidence_ids,
            staleness_state="superseded",
        )

        refreshed_provenance = MentalModelProvenance(
            derivation_method=cls._METHOD,
            observation_ids=current_dependencies.observation_ids,
            evidence_ids=current_dependencies.evidence_ids,
            memory_ids=current_dependencies.memory_ids,
            source_profiles=current_dependencies.source_profiles,
            entity_ids=model.entity_ids,
            relationship_ids=model.relationship_ids,
        )

        refreshed = MentalModel(
            model_id=model.model_id,
            model_type=model.model_type,
            title=model.title,
            description=model.description,
            entity_ids=model.entity_ids,
            relationship_ids=model.relationship_ids,
            supporting_observation_ids=current_dependencies.observation_ids,
            supporting_evidence_ids=current_dependencies.evidence_ids,
            supporting_memory_ids=current_dependencies.memory_ids,
            source_profiles=current_dependencies.source_profiles,
            temporal_scope=model.temporal_scope,
            confidence=model.confidence,
            status=model.status,
            version=model.version + 1,
            created_at=model.created_at,
            updated_at=refreshed_at,
            provenance=refreshed_provenance,
            derivation_method=cls._METHOD,
            contradictory_evidence_ids=tuple(
                sorted(
                    set(model.contradictory_evidence_ids)
                    & set(current_dependencies.evidence_ids)
                )
            ),
            staleness_state="current",
        )

        return MentalModelRefreshResult(
            previous_model=previous,
            refreshed_model=refreshed,
            dependency_snapshot=current_dependencies,
            staleness=staleness,
        )


__all__ = [
    "DependencyRevocation",
    "MentalModelDependencySnapshot",
    "MentalModelLifecycle",
    "MentalModelLifecycleError",
    "MentalModelRefreshResult",
    "MentalModelStalenessResult",
]
