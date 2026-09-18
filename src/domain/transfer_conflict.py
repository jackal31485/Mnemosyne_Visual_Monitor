"""Phase 14F cross-profile conflict analysis.

This module translates established Phase 12 contradiction analysis into the
cross-profile transfer context and compares structured destination knowledge.

It does not detect contradictions independently.  ContradictionAnalysisResult
from Phase 12 remains the authoritative contradiction contract.

Core invariants:
- contradictory evidence is never silently discarded;
- source and destination provenance remain explicit;
- temporal separation is preserved;
- unknown temporal resolution is not inferred;
- source-profile identity alone never determines the outcome;
- conflict analysis does not authorize, adopt, supersede, reject, or revoke;
- no raw memory content is accepted;
- inputs are never mutated.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import hashlib

from .contradiction_handling import (
    ContradictionAnalysisResult,
    ContradictionOutcome,
)
from .transfer_contract import TransferCandidate


def _required_text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    return value.strip()


def _identifiers(name: str, values: tuple[str, ...]) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        values = tuple(values)

    normalized = []
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} cannot contain empty identifiers")
        normalized.append(value.strip())

    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{name} cannot contain duplicate identifiers")

    return tuple(normalized)


def _score(name: str, value: float) -> float:
    if not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric")

    value = float(value)

    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be between 0.0 and 1.0")

    return value


class TransferConflictOutcome(str, Enum):
    """Cross-profile classification produced by Phase 14F."""

    NO_CONFLICT = "no_conflict"
    ADOPT_ALONGSIDE = "adopt_alongside"
    KEEP_EXISTING = "keep_existing"
    TEMPORALLY_SEPARATE = "temporally_separate"
    REVIEW_REQUIRED = "review_required"
    CONFLICT = "conflict"


@dataclass(frozen=True, slots=True)
class DestinationKnowledgeState:
    """Structured destination knowledge used for conflict comparison.

    This deliberately contains identifiers and governance metadata only.
    Raw knowledge text, memory content, titles, and descriptions are excluded.
    """

    knowledge_id: str
    entity_ids: tuple[str, ...]
    relationship_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    observation_ids: tuple[str, ...]
    temporal_scope: tuple[str, ...]
    source_profiles: tuple[str, ...]
    contradictory_evidence_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _required_text("knowledge_id", self.knowledge_id)

        for name in (
            "entity_ids",
            "relationship_ids",
            "evidence_ids",
            "observation_ids",
            "temporal_scope",
            "source_profiles",
            "contradictory_evidence_ids",
        ):
            object.__setattr__(
                self,
                name,
                _identifiers(name, getattr(self, name)),
            )


@dataclass(frozen=True, slots=True)
class TransferConflictSignals:
    """Inspectable structured signals used by the conflict classifier."""

    evidence_overlap: float
    entity_overlap: float
    relationship_overlap: float
    temporal_compatibility: float
    provenance_compatible: bool
    destination_match: bool

    def __post_init__(self) -> None:
        for name in (
            "evidence_overlap",
            "entity_overlap",
            "relationship_overlap",
            "temporal_compatibility",
        ):
            object.__setattr__(
                self,
                name,
                _score(name, getattr(self, name)),
            )

        for name in (
            "provenance_compatible",
            "destination_match",
        ):
            if not isinstance(getattr(self, name), bool):
                raise TypeError(f"{name} must be bool")


@dataclass(frozen=True, slots=True)
class TransferConflictRecord:
    """Immutable Phase 14F conflict-analysis audit record."""

    conflict_id: str
    transfer_id: str
    candidate_id: str
    source_profile: str
    destination_profile: str
    source_knowledge_id: str
    destination_knowledge_id: str | None
    outcome: TransferConflictOutcome
    signals: TransferConflictSignals
    source_evidence_ids: tuple[str, ...]
    destination_evidence_ids: tuple[str, ...]
    source_observation_ids: tuple[str, ...]
    destination_observation_ids: tuple[str, ...]
    source_memory_ids: tuple[str, ...]
    source_temporal_scope: tuple[str, ...]
    destination_temporal_scope: tuple[str, ...]
    contradictory_evidence_ids: tuple[str, ...]
    contradictory_profiles: tuple[str, ...]
    reasons: tuple[str, ...]
    derivation_method: str
    analyzed_at: datetime

    def __post_init__(self) -> None:
        for name in (
            "conflict_id",
            "transfer_id",
            "candidate_id",
            "source_profile",
            "destination_profile",
            "source_knowledge_id",
            "derivation_method",
        ):
            _required_text(name, getattr(self, name))

        if self.destination_knowledge_id is not None:
            _required_text(
                "destination_knowledge_id",
                self.destination_knowledge_id,
            )

        if not isinstance(self.outcome, TransferConflictOutcome):
            raise TypeError("outcome must be TransferConflictOutcome")

        if not isinstance(self.signals, TransferConflictSignals):
            raise TypeError("signals must be TransferConflictSignals")

        for name in (
            "source_evidence_ids",
            "destination_evidence_ids",
            "source_observation_ids",
            "destination_observation_ids",
            "source_memory_ids",
            "source_temporal_scope",
            "destination_temporal_scope",
            "contradictory_evidence_ids",
            "contradictory_profiles",
        ):
            object.__setattr__(
                self,
                name,
                _identifiers(name, getattr(self, name)),
            )

        if not isinstance(self.reasons, tuple):
            object.__setattr__(
                self,
                "reasons",
                tuple(self.reasons),
            )

        if any(
            not isinstance(reason, str) or not reason.strip()
            for reason in self.reasons
        ):
            raise ValueError("reasons must contain non-empty text")

        if not isinstance(self.analyzed_at, datetime):
            raise TypeError("analyzed_at must be a datetime")

        if self.source_profile == self.destination_profile:
            raise ValueError("source and destination profiles must differ")


@dataclass(frozen=True, slots=True)
class TransferConflictAnalysis:
    """Immutable result containing classification and audit record."""

    record: TransferConflictRecord

    @property
    def outcome(self) -> TransferConflictOutcome:
        return self.record.outcome

    @property
    def requires_review(self) -> bool:
        return self.outcome is TransferConflictOutcome.REVIEW_REQUIRED


def _overlap(left: tuple[str, ...], right: tuple[str, ...]) -> float:
    left_set = set(left)
    right_set = set(right)

    if not left_set and not right_set:
        return 1.0
    if not left_set or not right_set:
        return 0.0

    return len(left_set & right_set) / len(left_set | right_set)


def _deterministic_conflict_id(
    *,
    transfer_id: str,
    candidate_id: str,
    destination_knowledge_id: str | None,
) -> str:
    payload = "\x1f".join(
        (
            transfer_id,
            candidate_id,
            destination_knowledge_id or "",
        )
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"conflict-{digest[:24]}"


def analyze_transfer_conflict(
    candidate: TransferCandidate,
    *,
    transfer_id: str,
    destination: DestinationKnowledgeState | None,
    contradiction_analysis: ContradictionAnalysisResult | None,
    analyzed_at: datetime,
) -> TransferConflictAnalysis:
    """Classify a transfer against destination knowledge.

    ``contradiction_analysis`` must be produced by the established Phase 12
    contradiction machinery.  This function never independently declares
    evidence contradictory.

    The function only classifies the relationship.  It performs no adoption,
    authorization, supersession, rejection, persistence, or revocation.
    """

    if not isinstance(candidate, TransferCandidate):
        raise TypeError("candidate must be a TransferCandidate")

    _required_text("transfer_id", transfer_id)

    if destination is not None and not isinstance(
        destination,
        DestinationKnowledgeState,
    ):
        raise TypeError(
            "destination must be DestinationKnowledgeState or None"
        )

    if contradiction_analysis is not None and not isinstance(
        contradiction_analysis,
        ContradictionAnalysisResult,
    ):
        raise TypeError(
            "contradiction_analysis must be ContradictionAnalysisResult or None"
        )

    if not isinstance(analyzed_at, datetime):
        raise TypeError("analyzed_at must be a datetime")

    if contradiction_analysis is not None:
        if contradiction_analysis.candidate_id != candidate.candidate_id:
            raise ValueError(
                "contradiction analysis does not match transfer candidate"
            )

    destination_knowledge_id = (
        destination.knowledge_id if destination is not None else None
    )

    if destination is None:
        signals = TransferConflictSignals(
            evidence_overlap=0.0,
            entity_overlap=0.0,
            relationship_overlap=0.0,
            temporal_compatibility=1.0,
            provenance_compatible=True,
            destination_match=False,
        )
        outcome = TransferConflictOutcome.NO_CONFLICT
        reasons = ("destination_knowledge_not_present",)
    else:
        source_evidence = candidate.supporting_evidence_ids
        evidence_overlap = _overlap(
            source_evidence,
            destination.evidence_ids,
        )
        entity_overlap = _overlap(
            candidate.entity_ids,
            destination.entity_ids,
        )
        relationship_overlap = _overlap(
            candidate.relationship_ids,
            destination.relationship_ids,
        )

        temporal_compatibility = (
            1.0
            if not candidate.temporal_scope
            or not destination.temporal_scope
            or bool(
                set(candidate.temporal_scope)
                & set(destination.temporal_scope)
            )
            else 0.0
        )

        provenance_compatible = (
            candidate.source_profile not in destination.source_profiles
        )

        destination_match = bool(
            entity_overlap > 0.0
            or relationship_overlap > 0.0
            or evidence_overlap > 0.0
        )

        signals = TransferConflictSignals(
            evidence_overlap=evidence_overlap,
            entity_overlap=entity_overlap,
            relationship_overlap=relationship_overlap,
            temporal_compatibility=temporal_compatibility,
            provenance_compatible=provenance_compatible,
            destination_match=destination_match,
        )

        reasons_list: list[str] = []

        if not destination_match:
            outcome = TransferConflictOutcome.NO_CONFLICT
            reasons_list.append("no_meaningful_destination_overlap")
        elif contradiction_analysis is not None:
            if (
                contradiction_analysis.outcome
                is ContradictionOutcome.TEMPORALLY_SEPARATE
            ):
                outcome = TransferConflictOutcome.TEMPORALLY_SEPARATE
                reasons_list.extend(
                    (
                        "phase_12_temporal_separation_preserved",
                        "contradictory_evidence_preserved",
                    )
                )
            elif (
                contradiction_analysis.outcome
                is ContradictionOutcome.REVIEW_REQUIRED
            ):
                outcome = TransferConflictOutcome.REVIEW_REQUIRED
                reasons_list.extend(
                    (
                        "phase_12_contradiction_requires_review",
                        "temporal_resolution_not_invented",
                    )
                )
            elif (
                contradiction_analysis.outcome
                is ContradictionOutcome.CONFLICT
            ):
                outcome = TransferConflictOutcome.CONFLICT
                reasons_list.extend(
                    (
                        "phase_12_unresolved_contradiction",
                        "contradictory_evidence_preserved",
                    )
                )
            else:
                outcome = TransferConflictOutcome.ADOPT_ALONGSIDE
                reasons_list.append(
                    "destination_overlap_without_contradiction"
                )
        elif (
            entity_overlap == 1.0
            and relationship_overlap == 1.0
            and temporal_compatibility == 1.0
        ):
            outcome = TransferConflictOutcome.KEEP_EXISTING
            reasons_list.append("destination_knowledge_is_redundant")
        else:
            outcome = TransferConflictOutcome.ADOPT_ALONGSIDE
            reasons_list.append("destination_knowledge_is_compatible")

        reasons = tuple(reasons_list)

    contradictory_evidence_ids = (
        contradiction_analysis.contradictory_evidence_ids
        if contradiction_analysis is not None
        else ()
    )

    contradictory_profiles = (
        contradiction_analysis.contradictory_profiles
        if contradiction_analysis is not None
        else ()
    )

    conflict_id = _deterministic_conflict_id(
        transfer_id=transfer_id,
        candidate_id=candidate.candidate_id,
        destination_knowledge_id=destination_knowledge_id,
    )

    record = TransferConflictRecord(
        conflict_id=conflict_id,
        transfer_id=transfer_id,
        candidate_id=candidate.candidate_id,
        source_profile=candidate.source_profile,
        destination_profile=candidate.destination_profile,
        source_knowledge_id=candidate.source_knowledge_id,
        destination_knowledge_id=destination_knowledge_id,
        outcome=outcome,
        signals=signals,
        source_evidence_ids=candidate.supporting_evidence_ids,
        destination_evidence_ids=(
            destination.evidence_ids if destination is not None else ()
        ),
        source_observation_ids=candidate.observation_ids,
        destination_observation_ids=(
            destination.observation_ids if destination is not None else ()
        ),
        source_memory_ids=candidate.source_memory_ids,
        source_temporal_scope=candidate.temporal_scope,
        destination_temporal_scope=(
            destination.temporal_scope if destination is not None else ()
        ),
        contradictory_evidence_ids=contradictory_evidence_ids,
        contradictory_profiles=contradictory_profiles,
        reasons=reasons,
        derivation_method="phase-14f-transfer-conflict",
        analyzed_at=analyzed_at,
    )

    return TransferConflictAnalysis(record=record)


__all__ = [
    "DestinationKnowledgeState",
    "TransferConflictAnalysis",
    "TransferConflictOutcome",
    "TransferConflictRecord",
    "TransferConflictSignals",
    "analyze_transfer_conflict",
]
