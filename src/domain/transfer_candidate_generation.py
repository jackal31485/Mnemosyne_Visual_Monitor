"""Phase 14B deterministic cross-profile transfer-candidate generation.

This module operates only on already-governed derived references.  It does not
read private profile memory, write persistence, authorize transfers, or adopt
knowledge.

Candidate generation is intentionally deterministic:
the same governed references and source/destination profiles produce the same
candidate identity and candidate fields.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable

from .transfer_contract import (
    TransferCandidate,
    TransferProvenance,
)


@dataclass(frozen=True, slots=True)
class TransferSource:
    """Governed knowledge eligible for consideration as a transfer source.

    This is reference metadata only.  Raw memory content is intentionally not
    represented here.
    """

    knowledge_id: str
    source_profile: str
    evidence_ids: tuple[str, ...]
    source_memory_ids: tuple[str, ...] = ()
    observation_ids: tuple[str, ...] = ()
    mental_model_id: str | None = None
    entity_ids: tuple[str, ...] = ()
    relationship_ids: tuple[str, ...] = ()
    temporal_scope: tuple[str, ...] = ()
    benefit_signals: tuple[str, ...] = ()
    contradiction_state: str = "none"
    applicability: str = "eligible governed knowledge"

    def __post_init__(self) -> None:
        for name in (
            "knowledge_id",
            "source_profile",
            "contradiction_state",
            "applicability",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty text")

        if not self.evidence_ids:
            raise ValueError("evidence_ids must contain at least one identifier")

        for name in (
            "evidence_ids",
            "source_memory_ids",
            "observation_ids",
            "entity_ids",
            "relationship_ids",
            "temporal_scope",
            "benefit_signals",
        ):
            values = tuple(str(value).strip() for value in getattr(self, name))
            if any(not value for value in values):
                raise ValueError(f"{name} must contain non-empty identifiers")
            if len(values) != len(set(values)):
                raise ValueError(f"{name} must not contain duplicates")
            if values != tuple(sorted(values)):
                raise ValueError(f"{name} must be sorted deterministically")
            object.__setattr__(self, name, values)

        if self.mental_model_id is not None:
            if not isinstance(self.mental_model_id, str) or not self.mental_model_id.strip():
                raise ValueError("mental_model_id must be non-empty text")
            object.__setattr__(self, "mental_model_id", self.mental_model_id.strip())


def _candidate_id(source: TransferSource, destination_profile: str) -> str:
    """Return a stable identity for one source/destination pair."""
    material = "|".join(
        (
            source.source_profile,
            destination_profile,
            source.knowledge_id,
        )
    )
    digest = sha256(material.encode("utf-8")).hexdigest()[:24]
    return f"tc-{digest}"


def _record_id(candidate_id: str) -> str:
    """Return the deterministic audit-record identity reserved by the contract."""
    digest = sha256(candidate_id.encode("utf-8")).hexdigest()[:24]
    return f"tr-{digest}"


def generate_transfer_candidate(
    source: TransferSource,
    destination_profile: str,
) -> TransferCandidate:
    """Generate one deterministic transfer candidate.

    No authorization or adoption is performed.
    """
    if not isinstance(source, TransferSource):
        raise TypeError("source must be a TransferSource")

    if not isinstance(destination_profile, str) or not destination_profile.strip():
        raise ValueError("destination_profile must be non-empty text")

    destination_profile = destination_profile.strip()

    if source.source_profile == destination_profile:
        raise ValueError("source_profile and destination_profile must differ")

    candidate_id = _candidate_id(source, destination_profile)
    transfer_record_id = _record_id(candidate_id)

    provenance = TransferProvenance(
        source_profile=source.source_profile,
        destination_profile=destination_profile,
        source_knowledge_id=source.knowledge_id,
        transfer_candidate_id=candidate_id,
        transfer_record_id=transfer_record_id,
        evidence_ids=source.evidence_ids,
        source_memory_ids=source.source_memory_ids,
        observation_ids=source.observation_ids,
        mental_model_id=source.mental_model_id,
        derivation_method="phase-14b-deterministic-candidate-generation",
    )

    return TransferCandidate(
        candidate_id=candidate_id,
        source_profile=source.source_profile,
        destination_profile=destination_profile,
        source_knowledge_id=source.knowledge_id,
        proposed_applicability=source.applicability,
        provenance=provenance,
        supporting_evidence_ids=source.evidence_ids,
        source_memory_ids=source.source_memory_ids,
        observation_ids=source.observation_ids,
        mental_model_id=source.mental_model_id,
        entity_ids=source.entity_ids,
        relationship_ids=source.relationship_ids,
        temporal_scope=source.temporal_scope,
        benefit_signals=source.benefit_signals,
        contradiction_state=source.contradiction_state,
    )


def generate_transfer_candidates(
    sources: Iterable[TransferSource],
    destination_profile: str,
) -> tuple[TransferCandidate, ...]:
    """Generate deterministic, duplicate-free candidates in stable order."""
    if not isinstance(destination_profile, str) or not destination_profile.strip():
        raise ValueError("destination_profile must be non-empty text")

    candidates = [
        generate_transfer_candidate(source, destination_profile)
        for source in sources
    ]

    by_id = {candidate.candidate_id: candidate for candidate in candidates}

    return tuple(
        by_id[candidate_id]
        for candidate_id in sorted(by_id)
    )
