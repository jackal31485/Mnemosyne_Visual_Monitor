"""Deterministic evidence signals for governed retrieval results.

Phase 15C exposes evidence quality as descriptive retrieval metadata.
It never authorizes, promotes, revokes, rewrites, or mutates evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping


@dataclass(frozen=True)
class EvidenceSignal:
    """Inspectable evidence signal for one governed collective entry."""

    evidence_present: bool
    evidence_count: int
    observed_count: int
    inferred_count: int
    confidence: float | None
    evidence_quality: float


def build_evidence_signal(
    evidence: Iterable[Mapping[str, object]],
) -> EvidenceSignal:
    """Build a deterministic evidence signal from existing evidence records.

    The input is descriptive evidence already obtained through an
    authoritative evidence DAO. This function performs no governance
    authorization and never changes the supplied evidence.
    """

    records = tuple(evidence)

    observed_count = sum(
        1
        for record in records
        if record.get("evidence_kind") == "observed"
    )
    inferred_count = sum(
        1
        for record in records
        if record.get("evidence_kind") == "inferred"
    )

    confidences: list[float] = []

    for record in records:
        value = record.get("confidence")

        if value is None:
            continue

        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("evidence confidence must be numeric or None")

        confidence = float(value)

        if not 0.0 <= confidence <= 1.0:
            raise ValueError(
                "evidence confidence must be between 0.0 and 1.0"
            )

        confidences.append(confidence)

    evidence_count = len(records)

    if confidences:
        confidence_summary = sum(confidences) / len(confidences)
    else:
        confidence_summary = None

    if evidence_count == 0:
        quality = 0.0
    else:
        observed_ratio = observed_count / evidence_count
        confidence_component = (
            confidence_summary
            if confidence_summary is not None
            else 0.0
        )

        quality = (
            0.5 * observed_ratio
            + 0.5 * confidence_component
        )

    return EvidenceSignal(
        evidence_present=evidence_count > 0,
        evidence_count=evidence_count,
        observed_count=observed_count,
        inferred_count=inferred_count,
        confidence=confidence_summary,
        evidence_quality=quality,
    )
