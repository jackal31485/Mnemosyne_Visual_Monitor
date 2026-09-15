"""Phase 12G evidence-preserving synthesis domain contract."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .consolidation_candidate import ConsolidationCandidate, ConsolidationOutcome
from .evidence_validation import EvidenceValidationResult
from .evidence_weighting import EvidenceWeightingResult
from .contradiction_handling import (
    ContradictionAnalysisResult,
    ContradictionOutcome,
)


class SynthesisOutcome(str, Enum):
    SYNTHESIZED = "synthesized"
    KEEP_SEPARATE = "keep_separate"
    CONFLICT = "conflict"
    REVIEW_REQUIRED = "review_required"
    INVALIDATED = "invalidated"


@dataclass(frozen=True, slots=True)
class SynthesizedMemory:
    synthesis_id: str
    candidate_id: str
    content: str
    supporting_evidence_ids: tuple[str, ...]
    contradictory_evidence_ids: tuple[str, ...]
    source_profiles: tuple[str, ...]
    temporal_context: tuple[str, ...]
    provenance_complete: bool
    current_evidence_ids: tuple[str, ...]
    historical_evidence_ids: tuple[str, ...]
    confidence: float
    outcome: SynthesisOutcome


class EvidencePreservingSynthesizer:
    """Create derived synthesis without replacing or mutating source evidence."""

    def synthesize(
        self,
        *,
        candidate: ConsolidationCandidate,
        validation: EvidenceValidationResult,
        weighting: EvidenceWeightingResult,
        contradiction: ContradictionAnalysisResult,
        content: str,
        temporal_context: tuple[str, ...] = (),
    ) -> SynthesizedMemory:
        if not isinstance(candidate, ConsolidationCandidate):
            raise TypeError("candidate must be ConsolidationCandidate")
        if not isinstance(validation, EvidenceValidationResult):
            raise TypeError("validation must be EvidenceValidationResult")
        if not isinstance(weighting, EvidenceWeightingResult):
            raise TypeError("weighting must be EvidenceWeightingResult")
        if not isinstance(contradiction, ContradictionAnalysisResult):
            raise TypeError("contradiction must be ContradictionAnalysisResult")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("content must be non-empty")
        if candidate.candidate_id != validation.candidate_id:
            raise ValueError("candidate and validation IDs must match")
        if candidate.candidate_id != weighting.candidate_id:
            raise ValueError("candidate and weighting IDs must match")
        if candidate.candidate_id != contradiction.candidate_id:
            raise ValueError("candidate and contradiction IDs must match")

        evidence_ids = tuple(sorted(
            {
                *candidate.supporting_evidence_ids,
                *candidate.contradictory_evidence_ids,
            }
        ))

        if set(validation.valid_evidence_ids) | set(validation.invalid_evidence_ids) != set(
            evidence_ids
        ):
            raise ValueError("validation evidence set must match candidate evidence")

        weighted_ids = {
            result.evidence_id
            for result in weighting.evidence
        }
        if weighted_ids != set(evidence_ids):
            raise ValueError("weighting evidence set must match candidate evidence")

        if contradiction.outcome in {
            ContradictionOutcome.CONFLICT,
            ContradictionOutcome.REVIEW_REQUIRED,
        }:
            outcome = (
                SynthesisOutcome.CONFLICT
                if contradiction.outcome == ContradictionOutcome.CONFLICT
                else SynthesisOutcome.REVIEW_REQUIRED
            )
        elif validation.outcome.value == "rejected":
            outcome = SynthesisOutcome.INVALIDATED
        elif contradiction.outcome == ContradictionOutcome.TEMPORALLY_SEPARATE:
            outcome = SynthesisOutcome.KEEP_SEPARATE
        else:
            outcome = SynthesisOutcome.SYNTHESIZED

        current_ids = tuple(
            sorted(
                result.evidence_id
                for result in weighting.evidence
                if result.status.value == "current"
            )
        )
        historical_ids = tuple(
            sorted(
                result.evidence_id
                for result in weighting.evidence
                if result.status.value == "historical"
            )
        )

        profiles = tuple(
            sorted(
                {
                    result.source_profile
                    for result in weighting.evidence
                    if result.evidence_id in set(evidence_ids)
                }
            )
        )

        confidence = (
            weighting.total_current_weight
            if outcome == SynthesisOutcome.SYNTHESIZED
            else 0.0
        )

        return SynthesizedMemory(
            synthesis_id=f"{candidate.candidate_id}:synthesis",
            candidate_id=candidate.candidate_id,
            content=content.strip(),
            supporting_evidence_ids=tuple(sorted(candidate.supporting_evidence_ids)),
            contradictory_evidence_ids=tuple(
                sorted(candidate.contradictory_evidence_ids)
            ),
            source_profiles=profiles,
            temporal_context=tuple(temporal_context),
            provenance_complete=validation.provenance_complete,
            current_evidence_ids=current_ids,
            historical_evidence_ids=historical_ids,
            confidence=confidence,
            outcome=outcome,
        )


__all__ = [
    "EvidencePreservingSynthesizer",
    "SynthesisOutcome",
    "SynthesizedMemory",
]
