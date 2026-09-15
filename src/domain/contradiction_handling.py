"""Phase 12F contradiction analysis and preservation contract.

This module determines how contradictory consolidation evidence should be
represented without mutating observations, evidence, candidates, or weighting
results.

Contradiction handling is deliberately separate from:
- observation similarity;
- near-duplicate detection;
- candidate construction;
- evidence validation;
- evidence weighting;
- persistence;
- governed consolidation.

Core invariants:
- stronger evidence never silently erases contradictory evidence;
- contradictory evidence remains traceable;
- source-profile identity is preserved;
- temporal distinctions are preserved;
- temporal separation may explain an apparent contradiction, but only when
  explicitly supplied;
- temporal bounds are never invented;
- contradiction analysis does not authorize consolidation;
- contradiction analysis does not mutate its inputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from .consolidation_candidate import (
    ConsolidationCandidate,
    ConsolidationOutcome,
)
from .evidence_validation import (
    EvidenceValidationResult,
)
from .evidence_weighting import (
    EvidenceWeightingResult,
)


class ContradictionKind(str, Enum):
    """Classification of a detected contradiction."""

    NONE = "none"
    DIRECT = "direct"
    TEMPORAL = "temporal"
    EVIDENCE = "evidence"
    UNKNOWN = "unknown"


class ContradictionOutcome(str, Enum):
    """Governed result of contradiction analysis."""

    NO_CONTRADICTION = "no_contradiction"
    PRESERVE_SEPARATELY = "preserve_separately"
    TEMPORALLY_SEPARATE = "temporally_separate"
    CONFLICT = "conflict"
    REVIEW_REQUIRED = "review_required"


@dataclass(frozen=True, slots=True)
class ContradictionPair:
    """Explicit contradiction between two evidence references.

    ``left_evidence_id`` and ``right_evidence_id`` identify evidence already
    present in the Phase 12 evidence-validation/weighting pipeline.

    ``temporal_resolution`` is intentionally optional.  ``True`` means the
    caller has explicit temporal evidence that separates the two states.
    ``False`` means temporal analysis explicitly does not resolve the
    contradiction.  ``None`` means temporal resolution is unknown and must
    not be inferred.
    """

    left_evidence_id: str
    right_evidence_id: str
    kind: ContradictionKind = ContradictionKind.DIRECT
    temporal_resolution: bool | None = None
    reason: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.left_evidence_id, str) or not self.left_evidence_id.strip():
            raise ValueError("left_evidence_id must be non-empty text")
        if not isinstance(self.right_evidence_id, str) or not self.right_evidence_id.strip():
            raise ValueError("right_evidence_id must be non-empty text")
        if self.left_evidence_id == self.right_evidence_id:
            raise ValueError("contradiction pair requires distinct evidence IDs")
        if not isinstance(self.kind, ContradictionKind):
            raise TypeError("kind must be a ContradictionKind")
        if self.temporal_resolution not in (None, True, False):
            raise TypeError("temporal_resolution must be True, False, or None")
        if not isinstance(self.reason, str):
            raise TypeError("reason must be text")

    @property
    def evidence_ids(self) -> tuple[str, str]:
        """Return the pair in deterministic order."""

        return tuple(sorted((self.left_evidence_id, self.right_evidence_id)))


@dataclass(frozen=True, slots=True)
class ContradictionPolicy:
    """Policy controlling contradiction analysis.

    The policy never grants authorization to consolidate.  It only controls
    how contradiction signals are classified and surfaced.
    """

    preserve_all_contradictory_evidence: bool = True
    require_explicit_temporal_resolution: bool = True
    independent_profiles_require_conflict: bool = True
    unknown_temporal_state_requires_review: bool = True
    weighting_cannot_resolve_contradiction: bool = True

    def __post_init__(self) -> None:
        for name in (
            "preserve_all_contradictory_evidence",
            "require_explicit_temporal_resolution",
            "independent_profiles_require_conflict",
            "unknown_temporal_state_requires_review",
            "weighting_cannot_resolve_contradiction",
        ):
            if not isinstance(getattr(self, name), bool):
                raise TypeError(f"{name} must be bool")


@dataclass(frozen=True, slots=True)
class ContradictionAnalysisResult:
    """Immutable explanation of contradiction handling for one candidate."""

    candidate_id: str
    contradiction_pairs: tuple[ContradictionPair, ...]
    contradictory_evidence_ids: tuple[str, ...]
    contradictory_profiles: tuple[str, ...]
    kind: ContradictionKind
    outcome: ContradictionOutcome
    proposed_consolidation_outcome: ConsolidationOutcome
    temporal_resolution_explicit: bool
    requires_review: bool
    preservation_required: bool
    weighting_was_not_used_to_suppress_conflict: bool
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.candidate_id, str) or not self.candidate_id.strip():
            raise ValueError("candidate_id must be non-empty text")

        if not isinstance(self.contradiction_pairs, tuple):
            raise TypeError("contradiction_pairs must be a tuple")
        if not isinstance(self.contradictory_evidence_ids, tuple):
            raise TypeError("contradictory_evidence_ids must be a tuple")
        if not isinstance(self.contradictory_profiles, tuple):
            raise TypeError("contradictory_profiles must be a tuple")
        if not isinstance(self.reasons, tuple):
            raise TypeError("reasons must be a tuple")

        if not isinstance(self.kind, ContradictionKind):
            raise TypeError("kind must be a ContradictionKind")
        if not isinstance(self.outcome, ContradictionOutcome):
            raise TypeError("outcome must be a ContradictionOutcome")
        if not isinstance(
            self.proposed_consolidation_outcome,
            ConsolidationOutcome,
        ):
            raise TypeError(
                "proposed_consolidation_outcome must be a ConsolidationOutcome"
            )

        for value in (
            self.temporal_resolution_explicit,
            self.requires_review,
            self.preservation_required,
            self.weighting_was_not_used_to_suppress_conflict,
        ):
            if not isinstance(value, bool):
                raise TypeError("result flags must be bool")

        pair_ids: set[str] = set()
        for pair in self.contradiction_pairs:
            if not isinstance(pair, ContradictionPair):
                raise TypeError("contradiction_pairs must contain ContradictionPair")
            pair_ids.update(pair.evidence_ids)

        if not pair_ids.issubset(set(self.contradictory_evidence_ids)):
            raise ValueError(
                "all contradiction-pair evidence must be preserved in "
                "contradictory_evidence_ids"
            )

        if self.preservation_required and not self.contradictory_evidence_ids:
            raise ValueError(
                "preservation_required requires contradictory evidence IDs"
            )

    @property
    def has_contradiction(self) -> bool:
        """Whether at least one contradiction was detected."""

        return bool(self.contradiction_pairs)

    @property
    def is_temporally_resolved(self) -> bool:
        """Whether every contradiction has explicit temporal resolution."""

        return bool(self.contradiction_pairs) and all(
            pair.temporal_resolution is True
            for pair in self.contradiction_pairs
        )

    @property
    def is_conflict(self) -> bool:
        """Whether the candidate remains an unresolved conflict."""

        return self.outcome == ContradictionOutcome.CONFLICT


class ContradictionHandler:
    """Analyze and preserve contradiction signals.

    The handler consumes the already-established Phase 12 candidate,
    validation, and weighting contracts.  It does not alter any of them and
    never performs consolidation.
    """

    def __init__(
        self,
        policy: ContradictionPolicy | None = None,
    ) -> None:
        self.policy = policy or ContradictionPolicy()

    @staticmethod
    def _validate_pairs(
        pairs: Iterable[ContradictionPair],
    ) -> tuple[ContradictionPair, ...]:
        materialized = tuple(pairs)

        for pair in materialized:
            if not isinstance(pair, ContradictionPair):
                raise TypeError(
                    "contradiction_pairs must contain ContradictionPair objects"
                )

        seen: set[tuple[str, str]] = set()
        for pair in materialized:
            key = pair.evidence_ids
            if key in seen:
                raise ValueError(
                    f"duplicate contradiction pair: {key[0]} / {key[1]}"
                )
            seen.add(key)

        return tuple(
            sorted(
                materialized,
                key=lambda pair: (
                    pair.evidence_ids,
                    pair.kind.value,
                    pair.reason,
                ),
            )
        )

    @staticmethod
    def _validate_evidence_alignment(
        candidate: ConsolidationCandidate,
        validation: EvidenceValidationResult,
        weighting: EvidenceWeightingResult,
    ) -> None:
        if validation.candidate_id != candidate.candidate_id:
            raise ValueError("validation result does not match candidate")

        if weighting.candidate_id != candidate.candidate_id:
            raise ValueError("weighting result does not match candidate")

        candidate_ids = set(candidate.supporting_evidence_ids)
        validation_ids = {item.evidence_id for item in validation.evidence}
        weighting_ids = {item.evidence_id for item in weighting.evidence}

        if candidate_ids != validation_ids:
            raise ValueError(
                "candidate supporting evidence must exactly match validation evidence"
            )

        if candidate_ids != weighting_ids:
            raise ValueError(
                "candidate supporting evidence must exactly match weighting evidence"
            )

    @staticmethod
    def _profiles_for_evidence(
        validation: EvidenceValidationResult,
        evidence_ids: set[str],
    ) -> tuple[str, ...]:
        profiles = {
            reference.source_profile
            for reference in validation.evidence
            if reference.evidence_id in evidence_ids
        }
        return tuple(sorted(profiles))

    def analyze(
        self,
        *,
        candidate: ConsolidationCandidate,
        validation: EvidenceValidationResult,
        weighting: EvidenceWeightingResult,
        contradiction_pairs: Iterable[ContradictionPair],
    ) -> ContradictionAnalysisResult:
        """Analyze explicit contradiction pairs without mutating inputs."""

        if not isinstance(candidate, ConsolidationCandidate):
            raise TypeError("candidate must be a ConsolidationCandidate")
        if not isinstance(validation, EvidenceValidationResult):
            raise TypeError("validation must be an EvidenceValidationResult")
        if not isinstance(weighting, EvidenceWeightingResult):
            raise TypeError("weighting must be an EvidenceWeightingResult")

        pairs = self._validate_pairs(contradiction_pairs)
        self._validate_evidence_alignment(candidate, validation, weighting)

        candidate_evidence = set(candidate.supporting_evidence_ids)

        for pair in pairs:
            if pair.left_evidence_id not in candidate_evidence:
                raise ValueError(
                    f"contradiction evidence not present in candidate: "
                    f"{pair.left_evidence_id}"
                )
            if pair.right_evidence_id not in candidate_evidence:
                raise ValueError(
                    f"contradiction evidence not present in candidate: "
                    f"{pair.right_evidence_id}"
                )

        contradictory_ids = tuple(
            sorted(
                {
                    evidence_id
                    for pair in pairs
                    for evidence_id in pair.evidence_ids
                }
            )
        )

        contradictory_profiles = self._profiles_for_evidence(
            validation,
            set(contradictory_ids),
        )

        reasons: list[str] = []

        if not pairs:
            return ContradictionAnalysisResult(
                candidate_id=candidate.candidate_id,
                contradiction_pairs=(),
                contradictory_evidence_ids=(),
                contradictory_profiles=(),
                kind=ContradictionKind.NONE,
                outcome=ContradictionOutcome.NO_CONTRADICTION,
                proposed_consolidation_outcome=candidate.proposed_outcome,
                temporal_resolution_explicit=False,
                requires_review=False,
                preservation_required=False,
                weighting_was_not_used_to_suppress_conflict=True,
                reasons=("no_contradiction_detected",),
            )

        kinds = {pair.kind for pair in pairs}

        all_temporally_resolved = all(
            pair.temporal_resolution is True
            for pair in pairs
        )

        any_temporal_unknown = any(
            pair.temporal_resolution is None
            for pair in pairs
        )

        any_temporal_unresolved = any(
            pair.temporal_resolution is False
            for pair in pairs
        )

        if self.policy.preserve_all_contradictory_evidence:
            reasons.append("contradictory_evidence_preserved")

        if len(contradictory_profiles) > 1:
            reasons.append("contradictory_evidence_from_independent_profiles")

        if all_temporally_resolved and self.policy.require_explicit_temporal_resolution:
            reasons.append("contradiction_resolved_by_explicit_temporal_evidence")

            return ContradictionAnalysisResult(
                candidate_id=candidate.candidate_id,
                contradiction_pairs=pairs,
                contradictory_evidence_ids=contradictory_ids,
                contradictory_profiles=contradictory_profiles,
                kind=(
                    ContradictionKind.TEMPORAL
                    if ContradictionKind.TEMPORAL in kinds
                    else ContradictionKind.DIRECT
                ),
                outcome=ContradictionOutcome.TEMPORALLY_SEPARATE,
                proposed_consolidation_outcome=ConsolidationOutcome.KEEP_SEPARATE,
                temporal_resolution_explicit=True,
                requires_review=False,
                preservation_required=True,
                weighting_was_not_used_to_suppress_conflict=True,
                reasons=tuple(reasons),
            )

        if any_temporal_unknown and self.policy.unknown_temporal_state_requires_review:
            reasons.append("temporal_resolution_unknown")
            reasons.append("temporal_bounds_not_invented")

            return ContradictionAnalysisResult(
                candidate_id=candidate.candidate_id,
                contradiction_pairs=pairs,
                contradictory_evidence_ids=contradictory_ids,
                contradictory_profiles=contradictory_profiles,
                kind=(
                    ContradictionKind.TEMPORAL
                    if ContradictionKind.TEMPORAL in kinds
                    else ContradictionKind.UNKNOWN
                ),
                outcome=ContradictionOutcome.REVIEW_REQUIRED,
                proposed_consolidation_outcome=ConsolidationOutcome.REVIEW_REQUIRED,
                temporal_resolution_explicit=False,
                requires_review=True,
                preservation_required=True,
                weighting_was_not_used_to_suppress_conflict=True,
                reasons=tuple(reasons),
            )

        if any_temporal_unresolved:
            reasons.append("temporal_evidence_does_not_resolve_contradiction")

        if (
            len(contradictory_profiles) > 1
            and self.policy.independent_profiles_require_conflict
        ):
            reasons.append("independent_profile_conflict_requires_preservation")

        if (
            self.policy.weighting_cannot_resolve_contradiction
            and pairs
        ):
            reasons.append("evidence_weighting_cannot_suppress_contradiction")

        if ContradictionKind.DIRECT in kinds:
            result_kind = ContradictionKind.DIRECT
        elif ContradictionKind.EVIDENCE in kinds:
            result_kind = ContradictionKind.EVIDENCE
        elif ContradictionKind.TEMPORAL in kinds:
            result_kind = ContradictionKind.TEMPORAL
        else:
            result_kind = ContradictionKind.UNKNOWN

        return ContradictionAnalysisResult(
            candidate_id=candidate.candidate_id,
            contradiction_pairs=pairs,
            contradictory_evidence_ids=contradictory_ids,
            contradictory_profiles=contradictory_profiles,
            kind=result_kind,
            outcome=ContradictionOutcome.CONFLICT,
            proposed_consolidation_outcome=ConsolidationOutcome.CONFLICT,
            temporal_resolution_explicit=False,
            requires_review=True,
            preservation_required=True,
            weighting_was_not_used_to_suppress_conflict=True,
            reasons=tuple(reasons),
        )


__all__ = [
    "ContradictionAnalysisResult",
    "ContradictionHandler",
    "ContradictionKind",
    "ContradictionOutcome",
    "ContradictionPair",
    "ContradictionPolicy",
]
