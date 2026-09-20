"""Phase 16I governed federation adoption and knowledge projections.

Federation receipt, transfer authorization, adoption, and projection are
separate governance boundaries.

This module only bridges a VALIDATED federation receipt into the existing
Phase 14 transfer-candidate contract and defines an explicit, destination-
scoped projection record. It never authorizes, adopts, persists, or copies
raw remote memory content.
"""

from __future__ import annotations

from dataclasses import dataclass

from .federation_exchange import (
    FederationExchangeEnvelope,
    FederationExchangeKind,
    FederationKnowledgeReceipt,
    FederationExchangeState,
)
from .transfer_candidate_generation import (
    TransferSource,
    generate_transfer_candidate,
)
from .transfer_contract import TransferCandidate


class FederationAdoptionError(ValueError):
    """Raised when a federation-to-transfer governance boundary is invalid."""


@dataclass(frozen=True, slots=True)
class FederationKnowledgeProjection:
    """Immutable destination-scoped projection of governed remote knowledge.

    The projection contains identifiers and governance metadata only. It does
    not contain raw source-memory content and does not imply adoption.
    """

    projection_id: str
    destination_profile: str
    source_participant_id: str
    source_profile: str
    source_knowledge_id: str
    source_memory_ids: tuple[str, ...]
    observation_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    transfer_candidate_id: str
    transfer_record_id: str
    status: str = "PROPOSED"

    def __post_init__(self) -> None:
        for name in (
            "projection_id",
            "destination_profile",
            "source_participant_id",
            "source_profile",
            "source_knowledge_id",
            "transfer_candidate_id",
            "transfer_record_id",
            "status",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty text")
            object.__setattr__(self, name, value.strip())

        if self.source_profile == self.destination_profile:
            raise ValueError("source_profile and destination_profile must differ")

        for name in (
            "source_memory_ids",
            "observation_ids",
            "evidence_ids",
        ):
            values = getattr(self, name)
            if isinstance(values, (str, bytes)):
                raise TypeError(
                    f"{name} must be an iterable of identifiers, not text"
                )

            normalized = tuple(value.strip() for value in values)
            if any(not value for value in normalized):
                raise ValueError(f"{name} must contain non-empty text")
            if len(normalized) != len(set(normalized)):
                raise ValueError(f"{name} must not contain duplicates")

            object.__setattr__(self, name, tuple(sorted(normalized)))

        if not self.evidence_ids:
            raise ValueError("evidence_ids must contain at least one identifier")

    @property
    def is_proposed(self) -> bool:
        return self.status == "PROPOSED"

    @property
    def is_adopted(self) -> bool:
        return self.status == "ADOPTED"


@dataclass(frozen=True, slots=True)
class FederationAdoptionProposal:
    """Explicit federation proposal awaiting normal Phase 14 governance."""

    candidate: TransferCandidate
    projection: FederationKnowledgeProjection

    @property
    def is_adopted(self) -> bool:
        return False


def propose_federation_adoption(
    envelope: FederationExchangeEnvelope,
    receipt: FederationKnowledgeReceipt,
    *,
    destination_profile: str,
    source_profile: str,
    source_knowledge_id: str,
    source_memory_ids: tuple[str, ...],
    observation_ids: tuple[str, ...],
    evidence_ids: tuple[str, ...],
    applicability: str,
    entity_ids: tuple[str, ...] = (),
    relationship_ids: tuple[str, ...] = (),
    temporal_scope: tuple[str, ...] = (),
    benefit_signals: tuple[str, ...] = (),
    contradiction_state: str = "none",
    mental_model_id: str | None = None,
) -> FederationAdoptionProposal:
    """Bridge validated federation knowledge into Phase 14 candidate governance.

    This creates only a transfer candidate and a PROPOSED projection.
    Authorization and adoption remain explicit Phase 14 operations.
    """

    if not isinstance(envelope, FederationExchangeEnvelope):
        raise TypeError("envelope must be a FederationExchangeEnvelope")

    if not isinstance(receipt, FederationKnowledgeReceipt):
        raise TypeError("receipt must be a FederationKnowledgeReceipt")

    if receipt.exchange_id != envelope.exchange_id:
        raise FederationAdoptionError(
            "receipt exchange ID does not match envelope"
        )

    if receipt.recipient != envelope.recipient:
        raise FederationAdoptionError(
            "receipt recipient does not match envelope"
        )

    if receipt.state is not FederationExchangeState.VALIDATED:
        raise FederationAdoptionError(
            "only VALIDATED federation receipts may enter adoption governance"
        )

    if envelope.kind not in {
        FederationExchangeKind.OBSERVATION,
        FederationExchangeKind.RELATIONSHIP,
        FederationExchangeKind.TEMPORAL_EVIDENCE,
    }:
        raise FederationAdoptionError("unsupported federation exchange kind")

    if receipt.provenance.source_participant_id != envelope.sender.participant_id:
        raise FederationAdoptionError(
            "receipt provenance participant does not match sender"
        )

    if receipt.provenance.source_profile_id != source_profile:
        raise FederationAdoptionError(
            "source profile does not match federation provenance"
        )

    if receipt.provenance.source_memory_id not in source_memory_ids:
        raise FederationAdoptionError(
            "federation source memory must be represented in transfer provenance"
        )

    source = TransferSource(
        source_profile=source_profile,
        knowledge_id=source_knowledge_id,
        applicability=applicability,
        evidence_ids=evidence_ids,
        source_memory_ids=source_memory_ids,
        observation_ids=observation_ids,
        mental_model_id=mental_model_id,
        entity_ids=entity_ids,
        relationship_ids=relationship_ids,
        temporal_scope=temporal_scope,
        benefit_signals=benefit_signals,
        contradiction_state=contradiction_state,
    )

    candidate = generate_transfer_candidate(
        source,
        destination_profile,
    )

    projection = FederationKnowledgeProjection(
        projection_id=f"projection-{candidate.candidate_id}",
        destination_profile=destination_profile,
        source_participant_id=envelope.sender.participant_id,
        source_profile=source_profile,
        source_knowledge_id=source_knowledge_id,
        source_memory_ids=source_memory_ids,
        observation_ids=observation_ids,
        evidence_ids=evidence_ids,
        transfer_candidate_id=candidate.candidate_id,
        transfer_record_id=candidate.provenance.transfer_record_id,
    )

    return FederationAdoptionProposal(
        candidate=candidate,
        projection=projection,
    )


__all__ = [
    "FederationAdoptionError",
    "FederationAdoptionProposal",
    "FederationKnowledgeProjection",
    "propose_federation_adoption",
]
