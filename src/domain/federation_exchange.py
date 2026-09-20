from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from src.domain.federation_identity import FederationParticipant


class FederationExchangeState(str, Enum):
    """Governed lifecycle state of a received federation exchange."""

    RECEIVED = "RECEIVED"
    VALIDATED = "VALIDATED"
    REJECTED = "REJECTED"


class FederationExchangeKind(str, Enum):
    """Kinds of knowledge that may cross the federation boundary."""

    OBSERVATION = "OBSERVATION"
    RELATIONSHIP = "RELATIONSHIP"
    TEMPORAL_EVIDENCE = "TEMPORAL_EVIDENCE"


@dataclass(frozen=True)
class FederationProvenance:
    """
    Immutable provenance for remotely received knowledge.

    Raw private memory content is deliberately not represented here.
    """

    source_participant_id: str
    source_memory_id: str
    source_profile_id: str
    originating_exchange_id: str

    def __post_init__(self) -> None:
        for field_name, value in (
            ("source_participant_id", self.source_participant_id),
            ("source_memory_id", self.source_memory_id),
            ("source_profile_id", self.source_profile_id),
            ("originating_exchange_id", self.originating_exchange_id),
        ):
            if not isinstance(value, str):
                raise TypeError(f"{field_name} must be a string")

            if not value.strip():
                raise ValueError(f"{field_name} must not be empty")


@dataclass(frozen=True)
class FederationExchangeEnvelope:
    """
    Governed envelope crossing the federation boundary.

    The envelope carries metadata and derived knowledge payloads, not
    arbitrary private memory content.
    """

    exchange_id: str
    sender: FederationParticipant
    recipient: FederationParticipant
    kind: FederationExchangeKind
    provenance: FederationProvenance
    payload: dict[str, object]

    def __post_init__(self) -> None:
        if not isinstance(self.exchange_id, str):
            raise TypeError("exchange_id must be a string")

        if not self.exchange_id.strip():
            raise ValueError("exchange_id must not be empty")

        if not isinstance(self.sender, FederationParticipant):
            raise TypeError("sender must be a FederationParticipant")

        if not isinstance(self.recipient, FederationParticipant):
            raise TypeError(
                "recipient must be a FederationParticipant"
            )

        if not isinstance(self.kind, FederationExchangeKind):
            raise TypeError(
                "kind must be a FederationExchangeKind"
            )

        if not isinstance(self.provenance, FederationProvenance):
            raise TypeError(
                "provenance must be a FederationProvenance"
            )

        if not isinstance(self.payload, dict):
            raise TypeError("payload must be a dictionary")

        if (
            self.provenance.originating_exchange_id
            != self.exchange_id
        ):
            raise ValueError(
                "provenance exchange ID must match envelope exchange ID"
            )

        if (
            self.provenance.source_participant_id
            != self.sender.participant_id
        ):
            raise ValueError(
                "provenance source participant must match sender"
            )


@dataclass(frozen=True)
class FederationKnowledgeReceipt:
    """
    Immutable record that a remote exchange was received.

    Receipt does not imply adoption, promotion, or retrieval eligibility.
    """

    exchange_id: str
    recipient: FederationParticipant
    state: FederationExchangeState
    provenance: FederationProvenance
    rejection_reason: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.exchange_id, str):
            raise TypeError("exchange_id must be a string")

        if not self.exchange_id.strip():
            raise ValueError("exchange_id must not be empty")

        if not isinstance(
            self.recipient,
            FederationParticipant,
        ):
            raise TypeError(
                "recipient must be a FederationParticipant"
            )

        if not isinstance(
            self.state,
            FederationExchangeState,
        ):
            raise TypeError(
                "state must be a FederationExchangeState"
            )

        if not isinstance(
            self.provenance,
            FederationProvenance,
        ):
            raise TypeError(
                "provenance must be a FederationProvenance"
            )

        if self.rejection_reason is not None and not isinstance(
            self.rejection_reason,
            str,
        ):
            raise TypeError(
                "rejection_reason must be a string or None"
            )

        if (
            self.state is FederationExchangeState.REJECTED
            and not self.rejection_reason
        ):
            raise ValueError(
                "rejected receipts require a rejection reason"
            )

    @property
    def is_validated(self) -> bool:
        return self.state is FederationExchangeState.VALIDATED

    @property
    def is_adoptable(self) -> bool:
        """Receipt alone never grants adoption eligibility."""

        return False


def validate_exchange_envelope(
    envelope: FederationExchangeEnvelope,
    *,
    recipient: FederationParticipant,
) -> FederationKnowledgeReceipt:
    """
    Validate the structural/provenance boundary of an exchange.

    This function deliberately does not perform:
    - transport authentication
    - capability authorization
    - synchronization
    - consolidation
    - adoption
    """

    if not isinstance(
        envelope,
        FederationExchangeEnvelope,
    ):
        raise TypeError(
            "envelope must be a FederationExchangeEnvelope"
        )

    if not isinstance(
        recipient,
        FederationParticipant,
    ):
        raise TypeError(
            "recipient must be a FederationParticipant"
        )

    if envelope.recipient.participant_id != recipient.participant_id:
        return FederationKnowledgeReceipt(
            exchange_id=envelope.exchange_id,
            recipient=recipient,
            state=FederationExchangeState.REJECTED,
            provenance=envelope.provenance,
            rejection_reason="recipient mismatch",
        )

    return FederationKnowledgeReceipt(
        exchange_id=envelope.exchange_id,
        recipient=recipient,
        state=FederationExchangeState.VALIDATED,
        provenance=envelope.provenance,
    )


def receive_remote_knowledge(
    envelope: FederationExchangeEnvelope,
    *,
    recipient: FederationParticipant,
) -> FederationKnowledgeReceipt:
    """Receive remote knowledge through the governed validation boundary."""

    return validate_exchange_envelope(
        envelope,
        recipient=recipient,
    )
