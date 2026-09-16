"""Phase 13B deterministic mental-model candidate detection.

Candidate detection proposes derived models from already-governed metadata.
It does not validate, activate, persist, mutate, consolidate, or authorize
anything.  Raw memory content is intentionally outside these contracts.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from typing import Iterable

from .mental_model import (
    MentalModel,
    MentalModelProvenance,
    MentalModelStatus,
    MentalModelType,
)


def _text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    return value.strip()


def _ids(name: str, values: Iterable[str]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise TypeError(f"{name} must be an iterable of identifiers")
    result = tuple(sorted({_text(name, value) for value in values}))
    return result


@dataclass(frozen=True, slots=True)
class CandidateObservation:
    """Governed observation metadata used by the detector.

    This is a reference contract, not an observation store.  It contains no
    source-memory content.
    """

    observation_id: str
    source_profile: str
    source_memory_id: str
    evidence_ids: tuple[str, ...]
    entity_ids: tuple[str, ...] = ()
    relationship_ids: tuple[str, ...] = ()
    temporal_scope: tuple[str, ...] = ()
    concept_key: str | None = None
    observation_type: str | None = None
    confidence: float = 0.0

    def __post_init__(self) -> None:
        for name in ("observation_id", "source_profile", "source_memory_id"):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        for name in (
            "evidence_ids",
            "entity_ids",
            "relationship_ids",
            "temporal_scope",
        ):
            object.__setattr__(self, name, _ids(name, getattr(self, name)))
        if self.concept_key is not None:
            object.__setattr__(self, "concept_key", _text("concept_key", self.concept_key))
        if self.observation_type is not None:
            object.__setattr__(
                self,
                "observation_type",
                _text("observation_type", self.observation_type),
            )
        if not isinstance(self.confidence, (int, float)) or isinstance(self.confidence, bool):
            raise TypeError("confidence must be numeric")
        confidence = float(self.confidence)
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        object.__setattr__(self, "confidence", confidence)
        if not self.evidence_ids:
            raise ValueError("candidate observations require evidence IDs")


@dataclass(frozen=True, slots=True)
class CandidateRelationship:
    """Governed relationship metadata used by relationship detection."""

    relationship_id: str
    source_profile: str
    source_memory_id: str
    supporting_observation_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    subject_entity_id: str
    object_entity_id: str
    relationship_type: str
    temporal_scope: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "relationship_id",
            "source_profile",
            "source_memory_id",
            "subject_entity_id",
            "object_entity_id",
            "relationship_type",
        ):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        for name in (
            "supporting_observation_ids",
            "evidence_ids",
            "temporal_scope",
        ):
            object.__setattr__(self, name, _ids(name, getattr(self, name)))
        if not self.supporting_observation_ids:
            raise ValueError("candidate relationships require observation IDs")
        if not self.evidence_ids:
            raise ValueError("candidate relationships require evidence IDs")


@dataclass(frozen=True, slots=True)
class CandidateDetectionPolicy:
    """Deterministic minimum-support policy for candidate generation."""

    minimum_observations: int = 2
    minimum_relationships: int = 2
    minimum_evidence: int = 2
    minimum_confidence: float = 0.0

    def __post_init__(self) -> None:
        if not isinstance(self.minimum_observations, int) or isinstance(
            self.minimum_observations, bool
        ) or self.minimum_observations < 2:
            raise ValueError("minimum_observations must be at least 2")
        if not isinstance(self.minimum_relationships, int) or isinstance(
            self.minimum_relationships, bool
        ) or self.minimum_relationships < 2:
            raise ValueError("minimum_relationships must be at least 2")
        if not isinstance(self.minimum_evidence, int) or isinstance(
            self.minimum_evidence, bool
        ) or self.minimum_evidence < 1:
            raise ValueError("minimum_evidence must be at least 1")
        if not 0.0 <= float(self.minimum_confidence) <= 1.0:
            raise ValueError("minimum_confidence must be between 0.0 and 1.0")
        object.__setattr__(self, "minimum_confidence", float(self.minimum_confidence))


@dataclass(frozen=True, slots=True)
class MentalModelCandidate:
    """Detection result explicitly fixed at CANDIDATE lifecycle state."""

    model: MentalModel
    signal_reasons: frozenset[str]

    def __post_init__(self) -> None:
        if self.model.status is not MentalModelStatus.CANDIDATE:
            raise ValueError("candidate detection must produce CANDIDATE models")
        if not isinstance(self.signal_reasons, frozenset):
            object.__setattr__(self, "signal_reasons", frozenset(self.signal_reasons))
        if not self.signal_reasons:
            raise ValueError("candidate detection requires at least one signal reason")


class MentalModelCandidateDetector:
    """Generate deterministic candidates from supplied governed references."""

    _DERIVATION_METHOD = "phase_13b_deterministic_candidate_detection"

    def __init__(self, policy: CandidateDetectionPolicy | None = None) -> None:
        self.policy = policy or CandidateDetectionPolicy()

    @staticmethod
    def _model_id(model_type: MentalModelType, key: str) -> str:
        digest = sha256(f"{model_type.value}:{key}".encode("utf-8")).hexdigest()[:24]
        return f"mm-candidate-{digest}"

    def detect(
        self,
        observations: Iterable[CandidateObservation],
        *,
        generated_at: datetime,
        relationships: Iterable[CandidateRelationship] = (),
    ) -> tuple[MentalModelCandidate, ...]:
        if not isinstance(generated_at, datetime):
            raise TypeError("generated_at must be a datetime")
        observations = tuple(observations)
        relationships = tuple(relationships)
        if any(not isinstance(item, CandidateObservation) for item in observations):
            raise TypeError("observations must contain CandidateObservation values")
        if any(not isinstance(item, CandidateRelationship) for item in relationships):
            raise TypeError("relationships must contain CandidateRelationship values")

        candidates: list[MentalModelCandidate] = []
        candidates.extend(self._concept_candidates(observations, generated_at))
        candidates.extend(self._pattern_candidates(observations, generated_at))
        candidates.extend(self._temporal_candidates(observations, generated_at))
        candidates.extend(self._expectation_candidates(observations, generated_at))
        candidates.extend(self._relationship_candidates(relationships, generated_at))
        return tuple(sorted(candidates, key=lambda candidate: candidate.model.model_id))

    def _build_model(
        self,
        *,
        model_type: MentalModelType,
        key: str,
        title: str,
        description: str,
        observations: tuple[CandidateObservation, ...],
        generated_at: datetime,
        reasons: frozenset[str],
        relationships: tuple[CandidateRelationship, ...] = (),
    ) -> MentalModelCandidate:
        evidence_ids = {item for observation in observations for item in observation.evidence_ids}
        memory_ids = {observation.source_memory_id for observation in observations}
        profiles = {observation.source_profile for observation in observations}
        entity_ids = {item for observation in observations for item in observation.entity_ids}
        relationship_ids = {item for observation in observations for item in observation.relationship_ids}
        temporal_scope = {item for observation in observations for item in observation.temporal_scope}

        for relationship in relationships:
            evidence_ids.update(relationship.evidence_ids)
            memory_ids.add(relationship.source_memory_id)
            profiles.add(relationship.source_profile)
            entity_ids.update((relationship.subject_entity_id, relationship.object_entity_id))
            relationship_ids.add(relationship.relationship_id)
            temporal_scope.update(relationship.temporal_scope)

        supporting_observation_ids = {item.observation_id for item in observations}
        for relationship in relationships:
            supporting_observation_ids.update(relationship.supporting_observation_ids)

        confidence_inputs = [item.confidence for item in observations]
        confidence = (
            sum(confidence_inputs) / len(confidence_inputs)
            if confidence_inputs
            else 0.0
        )
        if confidence < self.policy.minimum_confidence:
            raise ValueError("candidate confidence is below configured minimum")

        model = MentalModel(
            model_id=self._model_id(model_type, key),
            model_type=model_type,
            title=title,
            description=description,
            entity_ids=tuple(sorted(entity_ids)),
            relationship_ids=tuple(sorted(relationship_ids)),
            supporting_observation_ids=tuple(sorted(supporting_observation_ids)),
            supporting_evidence_ids=tuple(sorted(evidence_ids)),
            supporting_memory_ids=tuple(sorted(memory_ids)),
            source_profiles=tuple(sorted(profiles)),
            temporal_scope=tuple(sorted(temporal_scope)),
            confidence=confidence,
            status=MentalModelStatus.CANDIDATE,
            version=1,
            created_at=generated_at,
            updated_at=generated_at,
            provenance=MentalModelProvenance(
                derivation_method=self._DERIVATION_METHOD,
                observation_ids=tuple(sorted(supporting_observation_ids)),
                evidence_ids=tuple(sorted(evidence_ids)),
                memory_ids=tuple(sorted(memory_ids)),
                source_profiles=tuple(sorted(profiles)),
                entity_ids=tuple(sorted(entity_ids)),
                relationship_ids=tuple(sorted(relationship_ids)),
            ),
            derivation_method=self._DERIVATION_METHOD,
            contradictory_evidence_ids=(),
        )
        return MentalModelCandidate(model=model, signal_reasons=reasons)

    def _eligible_observation_group(
        self, values: Iterable[CandidateObservation]
    ) -> tuple[CandidateObservation, ...] | None:
        group = tuple(sorted(values, key=lambda item: item.observation_id))
        evidence_ids = {item for observation in group for item in observation.evidence_ids}
        if len(group) < self.policy.minimum_observations:
            return None
        if len(evidence_ids) < self.policy.minimum_evidence:
            return None
        if (
            sum(item.confidence for item in group) / len(group)
            < self.policy.minimum_confidence
        ):
            return None
        return group

    def _concept_candidates(self, observations, generated_at):
        groups: dict[str, list[CandidateObservation]] = {}
        for observation in observations:
            if observation.concept_key:
                groups.setdefault(observation.concept_key, []).append(observation)
        results = []
        for key in sorted(groups):
            group = self._eligible_observation_group(groups[key])
            if group is None:
                continue
            results.append(
                self._build_model(
                    model_type=MentalModelType.CONCEPT,
                    key=f"concept:{key}",
                    title=f"Recurring concept: {key}",
                    description=f"Candidate concept supported by {len(group)} governed observations.",
                    observations=group,
                    generated_at=generated_at,
                    reasons=frozenset({"repeated_observations", "corroborated_evidence"}),
                )
            )
        return results

    def _pattern_candidates(self, observations, generated_at):
        groups: dict[tuple, list[CandidateObservation]] = {}
        for observation in observations:
            if observation.relationship_ids and observation.entity_ids:
                key = (
                    observation.observation_type or "unknown",
                    observation.relationship_ids,
                    observation.entity_ids,
                )
                groups.setdefault(key, []).append(observation)
        results = []
        for key in sorted(groups, key=repr):
            group = self._eligible_observation_group(groups[key])
            if group is None:
                continue
            results.append(
                self._build_model(
                    model_type=MentalModelType.PATTERN,
                    key=f"pattern:{repr(key)}",
                    title="Recurring governed pattern",
                    description=f"Candidate pattern supported by {len(group)} governed observations.",
                    observations=group,
                    generated_at=generated_at,
                    reasons=frozenset({"repeated_observations", "recurring_relationship_structure"}),
                )
            )
        return results

    def _temporal_candidates(self, observations, generated_at):
        groups: dict[str, list[CandidateObservation]] = {}
        for observation in observations:
            if observation.temporal_scope:
                key = observation.concept_key or repr(
                    (observation.entity_ids, observation.relationship_ids, observation.observation_type)
                )
                groups.setdefault(key, []).append(observation)
        results = []
        for key in sorted(groups):
            group = self._eligible_observation_group(groups[key])
            if group is None:
                continue
            temporal_values = {item for observation in group for item in observation.temporal_scope}
            if len(temporal_values) < 2:
                continue
            results.append(
                self._build_model(
                    model_type=MentalModelType.TEMPORAL,
                    key=f"temporal:{key}",
                    title=f"Recurring temporal pattern: {key}",
                    description=f"Candidate temporal model supported by {len(group)} governed observations.",
                    observations=group,
                    generated_at=generated_at,
                    reasons=frozenset({"repeated_temporal_pattern", "corroborated_evidence"}),
                )
            )
        return results

    def _expectation_candidates(self, observations, generated_at):
        groups: dict[str, list[CandidateObservation]] = {}
        for observation in observations:
            if observation.observation_type == "expectation" and observation.concept_key:
                groups.setdefault(observation.concept_key, []).append(observation)
        results = []
        for key in sorted(groups):
            group = self._eligible_observation_group(groups[key])
            if group is None:
                continue
            results.append(
                self._build_model(
                    model_type=MentalModelType.EXPECTATION,
                    key=f"expectation:{key}",
                    title=f"Derived expectation candidate: {key}",
                    description=f"Confidence-qualified expectation candidate supported by {len(group)} governed observations; not a guarantee.",
                    observations=group,
                    generated_at=generated_at,
                    reasons=frozenset({"repeated_expectation_signal", "corroborated_evidence"}),
                )
            )
        return results

    def _relationship_candidates(self, relationships, generated_at):
        groups: dict[tuple[str, str, str], list[CandidateRelationship]] = {}
        for relationship in relationships:
            key = (
                relationship.subject_entity_id,
                relationship.relationship_type,
                relationship.object_entity_id,
            )
            groups.setdefault(key, []).append(relationship)
        results = []
        for key in sorted(groups):
            group = tuple(sorted(groups[key], key=lambda item: item.relationship_id))
            evidence_ids = {item for relationship in group for item in relationship.evidence_ids}
            if len(group) < self.policy.minimum_relationships:
                continue
            if len(evidence_ids) < self.policy.minimum_evidence:
                continue
            observation_ids = {
                item for relationship in group for item in relationship.supporting_observation_ids
            }
            if len(observation_ids) < self.policy.minimum_observations:
                continue
            observations = tuple(
                CandidateObservation(
                    observation_id=observation_id,
                    source_profile=next(
                        relationship.source_profile
                        for relationship in group
                        if observation_id in relationship.supporting_observation_ids
                    ),
                    source_memory_id=next(
                        relationship.source_memory_id
                        for relationship in group
                        if observation_id in relationship.supporting_observation_ids
                    ),
                    evidence_ids=tuple(sorted(evidence_ids)),
                    entity_ids=(key[0], key[2]),
                    relationship_ids=tuple(sorted(item.relationship_id for item in group)),
                    temporal_scope=tuple(sorted({t for item in group for t in item.temporal_scope})),
                    confidence=1.0,
                )
                for observation_id in sorted(observation_ids)
            )
            results.append(
                self._build_model(
                    model_type=MentalModelType.RELATIONSHIP,
                    key=f"relationship:{'|'.join(key)}",
                    title=f"Recurring relationship: {key[0]} {key[1]} {key[2]}",
                    description=f"Candidate relationship model supported by {len(group)} governed relationship records.",
                    observations=observations,
                    relationships=group,
                    generated_at=generated_at,
                    reasons=frozenset({"recurring_entity_relationship", "corroborated_evidence"}),
                )
            )
        return results


__all__ = [
    "CandidateDetectionPolicy",
    "CandidateObservation",
    "CandidateRelationship",
    "MentalModelCandidate",
    "MentalModelCandidateDetector",
]
