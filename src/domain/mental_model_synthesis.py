"""Phase 13F evidence-preserving mental-model synthesis.

This module turns an already-validated mental-model candidate into an
ACTIVE derived model while preserving the complete governed evidence chain.

Synthesis does not mutate source memories, observations, evidence, entities,
relationships, or the supplied model version.  The synthesized description
is supplied by the caller; this module does not generate unsupported facts.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .mental_model import (
    MentalModel,
    MentalModelProvenance,
    MentalModelStatus,
)


class MentalModelSynthesisError(ValueError):
    """Raised when governed mental-model synthesis is invalid."""


@dataclass(frozen=True, slots=True)
class MentalModelSynthesisResult:
    """Immutable result of evidence-preserving mental-model synthesis."""

    source_model: MentalModel
    synthesized_model: MentalModel
    evidence_preserved: bool
    provenance_preserved: bool
    source_immutable: bool

    @property
    def is_valid(self) -> bool:
        """Return whether all synthesis preservation checks succeeded."""

        return (
            self.evidence_preserved
            and self.provenance_preserved
            and self.source_immutable
        )


class MentalModelSynthesizer:
    """Create an active mental model without severing its evidence chain."""

    _METHOD = "phase-13f-evidence-preserving-synthesis"

    @classmethod
    def synthesize(
        cls,
        model: MentalModel,
        *,
        title: str,
        description: str,
        synthesized_at: datetime,
        confidence: float | None = None,
    ) -> MentalModelSynthesisResult:
        """Synthesize an ACTIVE model from a VALIDATED model.

        The source model remains untouched.  All governed identifiers are
        copied exactly, including observations, evidence, memories,
        profiles, entities, relationships, temporal scope, and contradictions.

        The caller supplies the derived description.  No new evidence or
        unsupported source identifiers may be introduced here.
        """

        if not isinstance(model, MentalModel):
            raise TypeError("model must be a MentalModel")

        if model.status is not MentalModelStatus.VALIDATED:
            raise MentalModelSynthesisError(
                "only VALIDATED mental models may be synthesized"
            )

        if not isinstance(synthesized_at, datetime):
            raise TypeError("synthesized_at must be a datetime")

        if not isinstance(title, str) or not title.strip():
            raise ValueError("title must be non-empty text")

        if not isinstance(description, str) or not description.strip():
            raise ValueError("description must be non-empty text")

        if not model.supporting_observation_ids:
            raise MentalModelSynthesisError(
                "synthesis requires supporting observations"
            )

        if not model.supporting_evidence_ids:
            raise MentalModelSynthesisError(
                "synthesis requires supporting evidence"
            )

        if not model.supporting_memory_ids:
            raise MentalModelSynthesisError(
                "synthesis requires supporting memories"
            )

        if not model.source_profiles:
            raise MentalModelSynthesisError(
                "synthesis requires source profiles"
            )

        if confidence is None:
            synthesized_confidence = model.confidence
        else:
            synthesized_confidence = confidence

        provenance = MentalModelProvenance(
            derivation_method=cls._METHOD,
            observation_ids=model.supporting_observation_ids,
            evidence_ids=model.supporting_evidence_ids,
            memory_ids=model.supporting_memory_ids,
            source_profiles=model.source_profiles,
            entity_ids=model.entity_ids,
            relationship_ids=model.relationship_ids,
        )

        synthesized = MentalModel(
            model_id=model.model_id,
            model_type=model.model_type,
            title=title.strip(),
            description=description.strip(),
            entity_ids=model.entity_ids,
            relationship_ids=model.relationship_ids,
            supporting_observation_ids=model.supporting_observation_ids,
            supporting_evidence_ids=model.supporting_evidence_ids,
            supporting_memory_ids=model.supporting_memory_ids,
            source_profiles=model.source_profiles,
            temporal_scope=model.temporal_scope,
            confidence=synthesized_confidence,
            status=MentalModelStatus.ACTIVE,
            version=model.version,
            created_at=model.created_at,
            updated_at=synthesized_at,
            provenance=provenance,
            derivation_method=cls._METHOD,
            contradictory_evidence_ids=model.contradictory_evidence_ids,
            staleness_state="current",
        )

        evidence_preserved = (
            synthesized.supporting_evidence_ids
            == model.supporting_evidence_ids
            and synthesized.supporting_observation_ids
            == model.supporting_observation_ids
            and synthesized.supporting_memory_ids
            == model.supporting_memory_ids
            and synthesized.source_profiles
            == model.source_profiles
        )

        provenance_preserved = (
            synthesized.provenance.observation_ids
            == synthesized.supporting_observation_ids
            and synthesized.provenance.evidence_ids
            == synthesized.supporting_evidence_ids
            and synthesized.provenance.memory_ids
            == synthesized.supporting_memory_ids
            and synthesized.provenance.source_profiles
            == synthesized.source_profiles
            and synthesized.provenance.entity_ids
            == synthesized.entity_ids
            and synthesized.provenance.relationship_ids
            == synthesized.relationship_ids
        )

        source_immutable = (
            model.status is MentalModelStatus.VALIDATED
            and model.version == synthesized.version
        )

        result = MentalModelSynthesisResult(
            source_model=model,
            synthesized_model=synthesized,
            evidence_preserved=evidence_preserved,
            provenance_preserved=provenance_preserved,
            source_immutable=source_immutable,
        )

        if not result.is_valid:
            raise MentalModelSynthesisError(
                "evidence-preservation invariant failed"
            )

        return result


__all__ = [
    "MentalModelSynthesisError",
    "MentalModelSynthesizer",
    "MentalModelSynthesisResult",
]
