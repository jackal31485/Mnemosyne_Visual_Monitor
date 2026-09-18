"""Phase 14B deterministic transfer-candidate generation tests."""

import pytest

from src.domain.transfer_candidate_generation import (
    TransferSource,
    generate_transfer_candidate,
    generate_transfer_candidates,
)
from src.domain.transfer_contract import TransferStatus


def make_source(**overrides):
    values = dict(
        knowledge_id="knowledge-001",
        source_profile="jeeves",
        evidence_ids=("ev-1", "ev-2"),
        source_memory_ids=("mem-1", "mem-2"),
        observation_ids=("obs-1", "obs-2"),
        mental_model_id="mm-001",
        entity_ids=("entity-sqlite",),
        relationship_ids=("rel-authoritative",),
        temporal_scope=("current",),
        benefit_signals=("destination_gap", "novelty"),
        applicability="destination lacks current knowledge",
        contradiction_state="none",
    )
    values.update(overrides)
    return TransferSource(**values)


def test_generates_candidate_for_different_profile():
    candidate = generate_transfer_candidate(make_source(), "boss")

    assert candidate.source_profile == "jeeves"
    assert candidate.destination_profile == "boss"
    assert candidate.source_knowledge_id == "knowledge-001"
    assert candidate.status is TransferStatus.CANDIDATE


def test_generation_is_deterministic():
    first = generate_transfer_candidate(make_source(), "boss")
    second = generate_transfer_candidate(make_source(), "boss")

    assert first == second
    assert first.candidate_id == second.candidate_id
    assert first.provenance == second.provenance


def test_candidate_identity_changes_when_destination_changes():
    boss = generate_transfer_candidate(make_source(), "boss")
    hawk = generate_transfer_candidate(make_source(), "hawk")

    assert boss.candidate_id != hawk.candidate_id
    assert boss.destination_profile == "boss"
    assert hawk.destination_profile == "hawk"


def test_candidate_identity_changes_when_source_knowledge_changes():
    first = generate_transfer_candidate(make_source(), "boss")
    second = generate_transfer_candidate(
        make_source(knowledge_id="knowledge-002"),
        "boss",
    )

    assert first.candidate_id != second.candidate_id


def test_provenance_is_complete_and_matches_candidate():
    candidate = generate_transfer_candidate(make_source(), "boss")

    assert candidate.provenance.transfer_candidate_id == candidate.candidate_id
    assert candidate.provenance.transfer_record_id.startswith("tr-")
    assert candidate.provenance.source_profile == candidate.source_profile
    assert candidate.provenance.destination_profile == candidate.destination_profile
    assert candidate.provenance.source_knowledge_id == candidate.source_knowledge_id
    assert candidate.provenance.evidence_ids == ("ev-1", "ev-2")
    assert candidate.provenance.source_memory_ids == ("mem-1", "mem-2")
    assert candidate.provenance.observation_ids == ("obs-1", "obs-2")


def test_no_raw_content_is_carried_into_candidate():
    candidate = generate_transfer_candidate(make_source(), "boss")

    assert not hasattr(candidate, "content")
    assert not hasattr(candidate, "raw_memory")
    assert not hasattr(candidate.provenance, "content")
    assert not hasattr(candidate.provenance, "raw_memory")


def test_same_profile_is_rejected():
    with pytest.raises(ValueError, match="must differ"):
        generate_transfer_candidate(make_source(), "jeeves")


def test_empty_evidence_is_rejected():
    with pytest.raises(ValueError, match="at least one"):
        make_source(evidence_ids=())


def test_duplicate_source_identifiers_are_rejected():
    with pytest.raises(ValueError, match="duplicates"):
        make_source(evidence_ids=("ev-1", "ev-1"))


def test_unsorted_source_identifiers_are_rejected():
    with pytest.raises(ValueError, match="sorted"):
        make_source(evidence_ids=("ev-2", "ev-1"))


def test_multiple_sources_have_stable_order():
    sources = [
        make_source(knowledge_id="knowledge-003"),
        make_source(knowledge_id="knowledge-001"),
        make_source(knowledge_id="knowledge-002"),
    ]

    candidates = generate_transfer_candidates(sources, "boss")

    assert [candidate.source_knowledge_id for candidate in candidates] == [
        "knowledge-001",
        "knowledge-002",
        "knowledge-003",
    ]


def test_duplicate_sources_are_collapsed_deterministically():
    source = make_source()

    candidates = generate_transfer_candidates(
        [source, source],
        "boss",
    )

    assert len(candidates) == 1


def test_generation_does_not_authorize_or_adopt():
    candidate = generate_transfer_candidate(make_source(), "boss")

    assert candidate.status is TransferStatus.CANDIDATE

    with pytest.raises(ValueError, match="authorization and adoption"):
        candidate.transition_to(TransferStatus.AUTHORIZED)
