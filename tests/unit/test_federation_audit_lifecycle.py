"""Phase 16K end-to-end federation lifecycle audit coverage."""

from datetime import datetime, timezone

from src.domain.federation_adoption import propose_federation_adoption
from src.domain.federation_audit import (
    FederationAuditError,
    FederationAuditEventKind,
    FederationAuditStore,
)
from src.domain.federation_audit_recorder import FederationAuditRecorder
from src.domain.federation_authorization import (
    FederationCapability,
    authorize_participant,
)
from src.domain.federation_conflict import (
    FederationConflictKind,
    detect_federation_conflict,
)
from src.domain.federation_diagnostics import FederationDiagnostics
from src.domain.federation_exchange import (
    FederationExchangeEnvelope,
    FederationExchangeKind,
    FederationProvenance,
    validate_exchange_envelope,
)
from src.domain.federation_identity import (
    FederationParticipant,
    FederationParticipantType,
)
from src.domain.federation_peer_record import federation_peer_from_discovery
from src.domain.federation_session import authenticate_federation_session
from src.domain.federation_sync import (
    FederationCheckpoint,
    evaluate_synchronization,
)
from src.domain.federation_trust import establish_federation_trust
from src.domain.mental_model import (
    MentalModel,
    MentalModelProvenance,
    MentalModelStatus,
    MentalModelType,
)
from src.domain.transfer_adoption import adopt_transfer
from src.domain.transfer_applicability import (
    ApplicabilityDecision,
    ContradictionSignal,
    TransferApplicabilityAnalysis,
    TransferApplicabilitySignals,
)
from src.domain.transfer_authorization import (
    AuthorizationMechanism,
    AuthorizationRequest,
    authorize_transfer,
)
from src.domain.federation_revocation import (
    FederationRevocationSignal,
    propagate_federation_revocation,
)
from src.domain.transfer_revocation import TransferRevocationReason


NOW = datetime(2026, 9, 20, 18, 0, tzinfo=timezone.utc)
NOW_TS = int(NOW.timestamp())


def _participants():
    sender = FederationParticipant(
        participant_id="remote-node",
        participant_type=FederationParticipantType.REMOTE_MNEMOSYNE_INSTANCE,
    )
    recipient = FederationParticipant(
        participant_id="local-node",
        participant_type=FederationParticipantType.REMOTE_MNEMOSYNE_INSTANCE,
    )
    return sender, recipient


def _exchange(sender, recipient):
    provenance = FederationProvenance(
        source_participant_id=sender.participant_id,
        source_memory_id="memory-1",
        source_profile_id="remote-profile",
        originating_exchange_id="exchange-1",
    )

    return FederationExchangeEnvelope(
        exchange_id="exchange-1",
        sender=sender,
        recipient=recipient,
        kind=FederationExchangeKind.OBSERVATION,
        provenance=provenance,
        payload={"observation_id": "obs-1"},
    )


def _transfer_fixtures(candidate):
    analysis = TransferApplicabilityAnalysis(
        candidate_id=candidate.candidate_id,
        source_profile=candidate.source_profile,
        destination_profile=candidate.destination_profile,
        source_knowledge_id=candidate.source_knowledge_id,
        signals=TransferApplicabilitySignals(
            evidence_quality=0.95,
            novelty=0.8,
            entity_overlap=0.9,
            relationship_overlap=0.8,
            temporal_compatibility=1.0,
            destination_knowledge_gap=0.9,
            contradiction=ContradictionSignal.NONE,
            prior_transfer_redundancy=0.0,
        ),
        benefit_score=0.87,
        applicability_score=0.88,
        decision=ApplicabilityDecision.APPLICABLE,
        reasons=("strong destination applicability",),
        derivation_method="phase-14c-applicability",
    )

    authorization, _ = authorize_transfer(
        candidate,
        analysis,
        AuthorizationRequest(
            actor="operator",
            scope=candidate.source_knowledge_id,
            authorized_at=NOW,
            mechanism=AuthorizationMechanism.HUMAN,
        ),
    )

    mental_model = MentalModel(
        model_id=candidate.mental_model_id or "model-1",
        model_type=MentalModelType.CONCEPT,
        title="Federated concept",
        description="Test model for federation audit coverage.",
        entity_ids=candidate.entity_ids,
        relationship_ids=candidate.relationship_ids,
        supporting_observation_ids=candidate.observation_ids,
        supporting_evidence_ids=candidate.supporting_evidence_ids,
        supporting_memory_ids=candidate.source_memory_ids,
        source_profiles=(candidate.source_profile,),
        temporal_scope=candidate.temporal_scope,
        confidence=0.95,
        status=MentalModelStatus.ACTIVE,
        version=1,
        created_at=NOW,
        updated_at=NOW,
        provenance=MentalModelProvenance(
            derivation_method="phase-13f-synthesis",
            observation_ids=candidate.observation_ids,
            evidence_ids=candidate.supporting_evidence_ids,
            memory_ids=candidate.source_memory_ids,
            source_profiles=(candidate.source_profile,),
        ),
        derivation_method="phase-13f-synthesis",
        contradictory_evidence_ids=(),
    )

    adoption = adopt_transfer(
        candidate,
        analysis,
        authorization,
        adopted_at=NOW,
        mental_model=mental_model,
    )

    return (
        adoption,
        authorization,
        mental_model,
    )


def test_complete_federation_lifecycle_is_auditable(tmp_path):
    sender, recipient = _participants()

    store = FederationAuditStore(tmp_path)
    recorder = FederationAuditRecorder(
        store,
        actor_id="local-node",
    )

    # 1. Discovery.
    peer_record = federation_peer_from_discovery(
        client_id="remote-node",
        hostname="remote.example",
        address="192.168.2.50",
        api_port=8080,
        first_seen=NOW_TS,
        last_seen=NOW_TS,
        discovery_state="discovered",
    )
    recorder.record(
        FederationAuditEventKind.DISCOVERY,
        participant_id=sender.participant_id,
        occurred_at=NOW,
        outcome="discovered",
        event_key=peer_record.peer.participant_id,
        peer_id=peer_record.peer.participant_id,
    )

    # 2. Trust.
    trust = establish_federation_trust(
        participant=sender,
        established_at=NOW_TS,
    )
    recorder.record(
        FederationAuditEventKind.TRUST,
        participant_id=sender.participant_id,
        occurred_at=NOW,
        outcome=trust.state.value,
        event_key=f"{sender.participant_id}:trust",
        peer_id=sender.participant_id,
    )

    # 3. Authentication.
    session = authenticate_federation_session(
        participant=sender,
        session_id="session-1",
        authenticated_at=NOW_TS,
    )
    recorder.record(
        FederationAuditEventKind.AUTHENTICATION,
        participant_id=sender.participant_id,
        occurred_at=NOW,
        outcome=session.state.value,
        event_key=session.session_id,
        peer_id=sender.participant_id,
    )

    # 4. Authorization.
    authorization = authorize_participant(
        participant=sender,
        capabilities=frozenset(
            {
                FederationCapability.REQUEST_KNOWLEDGE,
                FederationCapability.RECEIVE_KNOWLEDGE,
            }
        ),
    )
    recorder.record(
        FederationAuditEventKind.AUTHORIZATION,
        participant_id=sender.participant_id,
        occurred_at=NOW,
        outcome="authorized",
        event_key=sender.participant_id,
        peer_id=sender.participant_id,
    )

    # 5. Exchange.
    envelope = _exchange(sender, recipient)
    receipt = validate_exchange_envelope(
        envelope,
        recipient=recipient,
    )
    recorder.record(
        FederationAuditEventKind.EXCHANGE,
        participant_id=sender.participant_id,
        occurred_at=NOW,
        outcome=receipt.state.value,
        event_key=envelope.exchange_id,
        peer_id=sender.participant_id,
        exchange_id=envelope.exchange_id,
        source_profile=receipt.provenance.source_profile_id,
    )

    # 6. Synchronization.
    sync = evaluate_synchronization(
        checkpoint=FederationCheckpoint(
            participant_id=sender.participant_id,
            sequence=0,
            version=0,
        ),
        exchange_id=envelope.exchange_id,
        sequence=0,
        version=1,
    )
    recorder.record(
        FederationAuditEventKind.SYNCHRONIZATION,
        participant_id=sender.participant_id,
        occurred_at=NOW,
        outcome=sync.status.value,
        event_key=f"{envelope.exchange_id}:0:1",
        exchange_id=envelope.exchange_id,
        peer_id=sender.participant_id,
    )

    # 7. Conflict.
    conflict = detect_federation_conflict(
        conflict_id="conflict-1",
        kind=FederationConflictKind.CONTENT,
        participant_ids=(sender.participant_id, recipient.participant_id),
        exchange_ids=(envelope.exchange_id,),
        source_memory_ids=("memory-1",),
        description="Test conflict visibility.",
    )
    recorder.record(
        FederationAuditEventKind.CONFLICT,
        participant_id=recipient.participant_id,
        occurred_at=NOW,
        outcome=conflict.state.value,
        event_key=conflict.conflict_id,
        peer_id=sender.participant_id,
        exchange_id=envelope.exchange_id,
    )

    # 8. Governed adoption proposal.
    proposal = propose_federation_adoption(
        envelope,
        receipt,
        destination_profile="local-profile",
        source_profile="remote-profile",
        source_knowledge_id="knowledge-1",
        source_memory_ids=("memory-1",),
        observation_ids=("observation-1",),
        evidence_ids=("evidence-1",),
        applicability="applicable",
        mental_model_id="model-1",
    )
    recorder.record(
        FederationAuditEventKind.ADOPTION,
        participant_id=recipient.participant_id,
        occurred_at=NOW,
        outcome="proposed",
        event_key=proposal.candidate.candidate_id,
        peer_id=sender.participant_id,
        exchange_id=envelope.exchange_id,
        candidate_id=proposal.candidate.candidate_id,
        source_profile=proposal.projection.source_profile,
        destination_profile=proposal.projection.destination_profile,
        details=(("status", proposal.projection.status),),
    )

    # 9. Phase 14 adoption + destination projection.
    adoption, transfer_authorization, mental_model = _transfer_fixtures(
        proposal.candidate
    )
    recorder.record(
        FederationAuditEventKind.PROJECTION,
        participant_id=recipient.participant_id,
        occurred_at=NOW,
        outcome=adoption.learned_representation.status.value,
        event_key=adoption.learned_representation.learned_id,
        peer_id=sender.participant_id,
        exchange_id=envelope.exchange_id,
        transfer_id=adoption.adopted_transfer_record.transfer_id,
        candidate_id=adoption.adopted_transfer_record.candidate_id,
        authorization_id=adoption.adopted_transfer_record.authorization_id,
        learned_id=adoption.learned_representation.learned_id,
        source_profile=adoption.learned_representation.source_profile,
        destination_profile=adoption.learned_representation.destination_profile,
    )

    # 10. Federation revocation propagation.
    record = adoption.adopted_transfer_record
    representation = adoption.learned_representation

    signal = FederationRevocationSignal(
        revocation_id="federation-revocation-1",
        source_participant_id=sender.participant_id,
        source_profile=representation.source_profile,
        destination_profile=representation.destination_profile,
        transfer_id=record.transfer_id,
        candidate_id=record.candidate_id,
        authorization_id=record.authorization_id,
        learned_id=representation.learned_id,
        source_knowledge_id=representation.source_knowledge_id,
        source_memory_ids=representation.source_memory_ids,
        reason=TransferRevocationReason.EXPLICIT_ROLLBACK,
        revoked_at=NOW,
        originating_exchange_id=envelope.exchange_id,
    )

    propagation = propagate_federation_revocation(
        signal,
        receipt=receipt,
        recipient=recipient,
        record=record,
        representation=representation,
        authorization=transfer_authorization,
        mental_model=mental_model,
    )

    recorder.record(
        FederationAuditEventKind.REVOCATION,
        participant_id=recipient.participant_id,
        occurred_at=NOW,
        outcome=propagation.result.revoked_record.status.value,
        event_key=signal.revocation_id,
        peer_id=sender.participant_id,
        exchange_id=signal.originating_exchange_id,
        transfer_id=signal.transfer_id,
        candidate_id=signal.candidate_id,
        authorization_id=signal.authorization_id,
        learned_id=signal.learned_id,
        source_profile=signal.source_profile,
        destination_profile=signal.destination_profile,
        details=(("reason", signal.reason.value),),
    )

    records = store.list_records()
    snapshot = FederationDiagnostics(records).snapshot()

    assert len(records) == 10
    assert snapshot.total_events == 10
    assert snapshot.exchange_events == 1
    assert snapshot.synchronization_events == 1
    assert snapshot.conflict_events == 1
    assert snapshot.adoption_events == 1
    assert snapshot.projection_events == 1
    assert snapshot.revocation_events == 1
    assert snapshot.attributable_events == 10
    assert snapshot.conflicts_visible is True
    assert snapshot.revocations_visible is True
    assert snapshot.audit_healthy is True

    assert {
        record.event_kind for record in records
    } == set(FederationAuditEventKind)

    assert all(
        not hasattr(record, "payload")
        and not hasattr(record, "raw_memory")
        and not hasattr(record, "memory_content")
        for record in records
    )


def test_audit_history_remains_immutable_after_lifecycle_recording(tmp_path):
    store = FederationAuditStore(tmp_path)
    recorder = FederationAuditRecorder(store, actor_id="local-node")

    record = recorder.record(
        FederationAuditEventKind.EXCHANGE,
        participant_id="remote-node",
        occurred_at=NOW,
        outcome="validated",
        event_key="exchange-immutable",
        exchange_id="exchange-immutable",
    )

    original = store.list_records()

    assert original == (record,)

    try:
        recorder.record(
            FederationAuditEventKind.EXCHANGE,
            participant_id="remote-node",
            occurred_at=NOW,
            outcome="changed",
            event_key="exchange-immutable",
            exchange_id="exchange-immutable",
        )
    except FederationAuditError:
        pass

    assert store.list_records() == original


def test_audit_recording_does_not_create_authority(tmp_path):
    store = FederationAuditStore(tmp_path)
    recorder = FederationAuditRecorder(store, actor_id="local-node")

    record = recorder.record(
        FederationAuditEventKind.AUTHORIZATION,
        participant_id="remote-node",
        occurred_at=NOW,
        outcome="observed",
        event_key="authorization-observed",
    )

    assert record.event_kind is FederationAuditEventKind.AUTHORIZATION
    assert record.outcome == "observed"
    assert not hasattr(record, "authorize")
    assert not hasattr(record, "adopt")
    assert not hasattr(record, "revoke")
