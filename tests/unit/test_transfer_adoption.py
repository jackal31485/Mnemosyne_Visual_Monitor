"""Phase 14E controlled adoption tests."""

from datetime import datetime, timedelta

import pytest

from src.domain.mental_model import (
    MentalModel,
    MentalModelProvenance,
    MentalModelStatus,
    MentalModelType,
)
from src.domain.transfer_adoption import (
    DestinationLearnedRepresentation,
    TransferAdoptionError,
    adopt_transfer,
)
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
from src.domain.transfer_contract import (
    TransferCandidate,
    TransferProvenance,
    TransferStatus,
)


NOW = datetime(2026, 9, 18, 12, 0, 0)


def _candidate() -> TransferCandidate:
    provenance = TransferProvenance(
        source_profile="jeeves",
        destination_profile="boss",
        source_knowledge_id="knowledge-001",
        transfer_candidate_id="candidate-001",
        transfer_record_id="transfer-001",
        evidence_ids=("evidence-001",),
        source_memory_ids=("memory-001",),
        observation_ids=("observation-001",),
        mental_model_id="model-001",
    )

    return TransferCandidate(
        candidate_id="candidate-001",
        source_profile="jeeves",
        destination_profile="boss",
        source_knowledge_id="knowledge-001",
        proposed_applicability="applicable",
        provenance=provenance,
        supporting_evidence_ids=("evidence-001",),
        source_memory_ids=("memory-001",),
        observation_ids=("observation-001",),
        mental_model_id="model-001",
        entity_ids=("entity-sqlite",),
        relationship_ids=("relationship-authoritative",),
        temporal_scope=("2026-09",),
        benefit_signals=("destination_gap",),
        created_at=NOW,
    )


def _analysis(
    *,
    decision=ApplicabilityDecision.APPLICABLE,
) -> TransferApplicabilityAnalysis:
    signals = TransferApplicabilitySignals(
        evidence_quality=0.95,
        novelty=0.8,
        entity_overlap=0.9,
        relationship_overlap=0.8,
        temporal_compatibility=1.0,
        destination_knowledge_gap=0.9,
        contradiction=ContradictionSignal.NONE,
        prior_transfer_redundancy=0.0,
    )

    return TransferApplicabilityAnalysis(
        candidate_id="candidate-001",
        source_profile="jeeves",
        destination_profile="boss",
        source_knowledge_id="knowledge-001",
        signals=signals,
        benefit_score=0.87,
        applicability_score=0.88,
        decision=decision,
        reasons=("strong destination applicability",),
        derivation_method="phase-14c-applicability",
    )


def _authorization(
    *,
    expires_at=None,
    mechanism=AuthorizationMechanism.HUMAN,
    revoked=False,
):
    authorization, _ = authorize_transfer(
        _candidate(),
        _analysis(),
        AuthorizationRequest(
            actor="operator",
            scope="knowledge-001",
            authorized_at=NOW,
            mechanism=mechanism,
            expires_at=expires_at,
        ),
    )

    if revoked:
        authorization = type(authorization)(
            authorization_id=authorization.authorization_id,
            candidate_id=authorization.candidate_id,
            source_profile=authorization.source_profile,
            destination_profile=authorization.destination_profile,
            actor=authorization.actor,
            authorized_at=authorization.authorized_at,
            scope=authorization.scope,
            mechanism=authorization.mechanism,
            expires_at=authorization.expires_at,
            revoked=True,
        )

    return authorization


def _mental_model() -> MentalModel:
    provenance = MentalModelProvenance(
        derivation_method="phase-13f-synthesis",
        observation_ids=("observation-001",),
        evidence_ids=("evidence-001",),
        memory_ids=("memory-001",),
        source_profiles=("jeeves",),
        entity_ids=("entity-sqlite",),
        relationship_ids=("relationship-authoritative",),
    )

    return MentalModel(
        model_id="model-001",
        model_type=MentalModelType.CONCEPT,
        title="SQLite is authoritative",
        description="SQLite is the authoritative local store.",
        entity_ids=("entity-sqlite",),
        relationship_ids=("relationship-authoritative",),
        supporting_observation_ids=("observation-001",),
        supporting_evidence_ids=("evidence-001",),
        supporting_memory_ids=("memory-001",),
        source_profiles=("jeeves",),
        temporal_scope=("2026-09",),
        confidence=0.95,
        status=MentalModelStatus.ACTIVE,
        version=1,
        created_at=NOW,
        updated_at=NOW,
        provenance=provenance,
        derivation_method="phase-13f-synthesis",
        contradictory_evidence_ids=(),
    )


def _adopt(**kwargs):
    kwargs.setdefault("mental_model", _mental_model())
    return adopt_transfer(
        _candidate(),
        _analysis(),
        _authorization(),
        adopted_at=NOW + timedelta(minutes=5),
        **kwargs,
    )


def test_explicit_adoption_creates_destination_representation():
    result = _adopt()

    assert result.adopted_transfer_record.status is TransferStatus.ADOPTED
    assert result.adopted_transfer_record.adopted_at == NOW + timedelta(minutes=5)

    learned = result.learned_representation

    assert isinstance(learned, DestinationLearnedRepresentation)
    assert learned.destination_profile == "boss"
    assert learned.source_profile == "jeeves"
    assert learned.source_knowledge_id == "knowledge-001"


def test_adoption_preserves_complete_provenance_chain():
    result = _adopt()
    learned = result.learned_representation

    assert learned.destination_profile == "boss"
    assert learned.transfer_id == "transfer-001"
    assert learned.candidate_id == "candidate-001"
    assert learned.authorization_id == result.adopted_transfer_record.authorization_id
    assert learned.source_knowledge_id == "knowledge-001"
    assert learned.source_memory_ids == ("memory-001",)
    assert learned.observation_ids == ("observation-001",)
    assert learned.evidence_ids == ("evidence-001",)
    assert learned.source_profile == "jeeves"


def test_adoption_preserves_authorization_metadata():
    authorization = _authorization(
        expires_at=NOW + timedelta(hours=1),
        mechanism=AuthorizationMechanism.POLICY,
    )

    result = adopt_transfer(
        _candidate(),
        _analysis(),
        authorization,
        adopted_at=NOW + timedelta(minutes=5),
        mental_model=_mental_model(),
    )

    learned = result.learned_representation

    assert learned.authorization_actor == "operator"
    assert learned.authorization_mechanism is AuthorizationMechanism.POLICY
    assert learned.authorization_scope == "knowledge-001"
    assert learned.authorized_at == NOW
    assert learned.authorization_expires_at == NOW + timedelta(hours=1)


def test_adoption_requires_explicit_applicable_analysis():
    with pytest.raises(TransferAdoptionError, match="APPLICABLE"):
        adopt_transfer(
            _candidate(),
            _analysis(decision=ApplicabilityDecision.REVIEW_REQUIRED),
            _authorization(),
            adopted_at=NOW + timedelta(minutes=5),
            mental_model=_mental_model(),
        )


def test_not_applicable_cannot_be_adopted():
    with pytest.raises(TransferAdoptionError, match="APPLICABLE"):
        adopt_transfer(
            _candidate(),
            _analysis(decision=ApplicabilityDecision.NOT_APPLICABLE),
            _authorization(),
            adopted_at=NOW + timedelta(minutes=5),
            mental_model=_mental_model(),
        )


def test_revoked_authorization_cannot_be_adopted():
    with pytest.raises(TransferAdoptionError, match="not active"):
        adopt_transfer(
            _candidate(),
            _analysis(),
            _authorization(revoked=True),
            adopted_at=NOW + timedelta(minutes=5),
            mental_model=_mental_model(),
        )


def test_expired_authorization_cannot_be_adopted():
    with pytest.raises(TransferAdoptionError, match="not active|expired"):
        adopt_transfer(
            _candidate(),
            _analysis(),
            _authorization(expires_at=NOW + timedelta(minutes=1)),
            adopted_at=NOW + timedelta(minutes=5),
            mental_model=_mental_model(),
        )


def test_adoption_before_authorization_is_rejected():
    with pytest.raises(TransferAdoptionError, match="not active"):
        adopt_transfer(
            _candidate(),
            _analysis(),
            _authorization(),
            adopted_at=NOW - timedelta(minutes=1),
            mental_model=_mental_model(),
        )


def test_mismatched_authorization_is_rejected():
    authorization = _authorization()

    mismatched = type(authorization)(
        authorization_id=authorization.authorization_id,
        candidate_id=authorization.candidate_id,
        source_profile="other-source",
        destination_profile=authorization.destination_profile,
        actor=authorization.actor,
        authorized_at=authorization.authorized_at,
        scope=authorization.scope,
        mechanism=authorization.mechanism,
        expires_at=authorization.expires_at,
        revoked=False,
    )

    with pytest.raises(TransferAdoptionError, match="source profile"):
        adopt_transfer(
            _candidate(),
            _analysis(),
            mismatched,
            adopted_at=NOW + timedelta(minutes=5),
            mental_model=_mental_model(),
        )


def test_source_and_destination_are_not_mutated():
    candidate = _candidate()
    analysis = _analysis()
    authorization = _authorization()
    model = _mental_model()

    result = adopt_transfer(
        candidate,
        analysis,
        authorization,
        adopted_at=NOW + timedelta(minutes=5),
        mental_model=model,
    )

    assert candidate.status is TransferStatus.CANDIDATE
    assert analysis.decision is ApplicabilityDecision.APPLICABLE
    assert authorization.revoked is False
    assert model.status is MentalModelStatus.ACTIVE
    assert result.previous_transfer_record.status is TransferStatus.AUTHORIZED


def test_adoption_does_not_rewrite_source_memory():
    result = _adopt()

    assert result.learned_representation.source_memory_ids == ("memory-001",)
    assert result.learned_representation.mental_model.supporting_memory_ids == (
        "memory-001",
    )


def test_temporal_scope_is_preserved():
    result = _adopt()

    assert result.learned_representation.temporal_scope == ("2026-09",)
    assert result.learned_representation.mental_model.temporal_scope == ("2026-09",)


def test_adoption_has_deterministic_learned_identity():
    first = _adopt()
    second = _adopt()

    assert (
        first.learned_representation.learned_id
        == second.learned_representation.learned_id
    )


def test_adoption_creates_version_one():
    result = _adopt()

    assert result.learned_representation.version == 1
    assert result.adopted_transfer_record.version == 1


def test_previous_transfer_record_remains_authorized():
    result = _adopt()

    assert result.previous_transfer_record.status is TransferStatus.AUTHORIZED
    assert result.previous_transfer_record.adopted_at is None


def test_adopted_transfer_record_is_distinct_immutable_state():
    result = _adopt()

    assert result.previous_transfer_record is not result.adopted_transfer_record
    assert result.adopted_transfer_record.status is TransferStatus.ADOPTED


def test_adoption_requires_supported_mental_model_status():
    model = _mental_model().transition_to(MentalModelStatus.STALE)

    with pytest.raises(TransferAdoptionError, match="VALIDATED or ACTIVE"):
        adopt_transfer(
            _candidate(),
            _analysis(),
            _authorization(),
            adopted_at=NOW + timedelta(minutes=5),
            mental_model=model,
        )


def test_adoption_requires_matching_mental_model_identity():
    model = _mental_model()

    mismatched_model = MentalModel(
        model_id="different-model",
        model_type=model.model_type,
        title=model.title,
        description=model.description,
        entity_ids=model.entity_ids,
        relationship_ids=model.relationship_ids,
        supporting_observation_ids=model.supporting_observation_ids,
        supporting_evidence_ids=model.supporting_evidence_ids,
        supporting_memory_ids=model.supporting_memory_ids,
        source_profiles=model.source_profiles,
        temporal_scope=model.temporal_scope,
        confidence=model.confidence,
        status=model.status,
        version=model.version,
        created_at=model.created_at,
        updated_at=model.updated_at,
        provenance=MentalModelProvenance(
            derivation_method=model.derivation_method,
            observation_ids=model.supporting_observation_ids,
            evidence_ids=model.supporting_evidence_ids,
            memory_ids=model.supporting_memory_ids,
            source_profiles=model.source_profiles,
            entity_ids=model.entity_ids,
            relationship_ids=model.relationship_ids,
        ),
        derivation_method=model.derivation_method,
        contradictory_evidence_ids=model.contradictory_evidence_ids,
    )

    with pytest.raises(TransferAdoptionError, match="mental model ID"):
        adopt_transfer(
            _candidate(),
            _analysis(),
            _authorization(),
            adopted_at=NOW + timedelta(minutes=5),
            mental_model=mismatched_model,
        )


def test_adoption_requires_matching_evidence():
    model = _mental_model()

    with pytest.raises(TransferAdoptionError, match="evidence"):
        adopt_transfer(
            _candidate(),
            _analysis(),
            _authorization(),
            adopted_at=NOW + timedelta(minutes=5),
            mental_model=MentalModel(
                model_id=model.model_id,
                model_type=model.model_type,
                title=model.title,
                description=model.description,
                entity_ids=model.entity_ids,
                relationship_ids=model.relationship_ids,
                supporting_observation_ids=model.supporting_observation_ids,
                supporting_evidence_ids=("different-evidence",),
                supporting_memory_ids=model.supporting_memory_ids,
                source_profiles=model.source_profiles,
                temporal_scope=model.temporal_scope,
                confidence=model.confidence,
                status=model.status,
                version=model.version,
                created_at=model.created_at,
                updated_at=model.updated_at,
                provenance=MentalModelProvenance(
                    derivation_method=model.derivation_method,
                    observation_ids=model.supporting_observation_ids,
                    evidence_ids=("different-evidence",),
                    memory_ids=model.supporting_memory_ids,
                    source_profiles=model.source_profiles,
                    entity_ids=model.entity_ids,
                    relationship_ids=model.relationship_ids,
                ),
                derivation_method=model.derivation_method,
                contradictory_evidence_ids=model.contradictory_evidence_ids,
            ),
        )


def test_adoption_requires_matching_temporal_scope():
    model = _mental_model()

    mismatched_model = MentalModel(
        model_id=model.model_id,
        model_type=model.model_type,
        title=model.title,
        description=model.description,
        entity_ids=model.entity_ids,
        relationship_ids=model.relationship_ids,
        supporting_observation_ids=model.supporting_observation_ids,
        supporting_evidence_ids=model.supporting_evidence_ids,
        supporting_memory_ids=model.supporting_memory_ids,
        source_profiles=model.source_profiles,
        temporal_scope=("2027-01",),
        confidence=model.confidence,
        status=model.status,
        version=model.version,
        created_at=model.created_at,
        updated_at=model.updated_at,
        provenance=MentalModelProvenance(
            derivation_method=model.derivation_method,
            observation_ids=model.supporting_observation_ids,
            evidence_ids=model.supporting_evidence_ids,
            memory_ids=model.supporting_memory_ids,
            source_profiles=model.source_profiles,
            entity_ids=model.entity_ids,
            relationship_ids=model.relationship_ids,
        ),
        derivation_method=model.derivation_method,
        contradictory_evidence_ids=model.contradictory_evidence_ids,
    )

    with pytest.raises(TransferAdoptionError, match="temporal scope"):
        _adopt(mental_model=mismatched_model)

def test_legacy_authorization_without_explicit_mechanism_cannot_be_adopted():
    authorization = type(_authorization())(
        authorization_id="auth-legacy",
        candidate_id="candidate-001",
        source_profile="jeeves",
        destination_profile="boss",
        actor="operator",
        authorized_at=NOW,
        scope="knowledge-001",
        mechanism="legacy",
        expires_at=None,
        revoked=False,
    )

    with pytest.raises(TransferAdoptionError, match="mechanism"):
        adopt_transfer(
            _candidate(),
            _analysis(),
            authorization,
            adopted_at=NOW + timedelta(minutes=5),
            mental_model=_mental_model(),
        )
