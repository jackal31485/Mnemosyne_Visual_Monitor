import pytest

from src.domain.federation_sync import (
    FederationCheckpoint,
    FederationSyncRecord,
    FederationSyncStatus,
    evaluate_synchronization,
    record_retry,
)


@pytest.fixture
def checkpoint():
    return FederationCheckpoint(
        participant_id="remote-001",
        sequence=4,
        version=4,
    )


def test_next_contiguous_exchange_is_applied(checkpoint):
    decision = evaluate_synchronization(
        checkpoint=checkpoint,
        exchange_id="exchange-005",
        sequence=5,
        version=5,
    )

    assert decision.status is FederationSyncStatus.APPLIED
    assert decision.should_apply is True
    assert decision.checkpoint.sequence == 5
    assert decision.checkpoint.version == 5


def test_seen_exchange_is_duplicate(checkpoint):
    decision = evaluate_synchronization(
        checkpoint=checkpoint,
        exchange_id="exchange-004",
        sequence=5,
        version=5,
        seen_exchange_ids=frozenset({"exchange-004"}),
    )

    assert decision.is_duplicate is True
    assert decision.should_apply is False


def test_stale_sequence_is_duplicate(checkpoint):
    decision = evaluate_synchronization(
        checkpoint=checkpoint,
        exchange_id="exchange-old",
        sequence=3,
        version=3,
    )

    assert decision.status is FederationSyncStatus.DUPLICATE
    assert decision.should_apply is False


def test_sequence_gap_requires_retry(checkpoint):
    decision = evaluate_synchronization(
        checkpoint=checkpoint,
        exchange_id="exchange-006",
        sequence=6,
        version=6,
    )

    assert decision.status is FederationSyncStatus.RETRY
    assert decision.requires_retry is True
    assert decision.should_apply is False
    assert decision.checkpoint == checkpoint


def test_stale_version_is_duplicate(checkpoint):
    decision = evaluate_synchronization(
        checkpoint=checkpoint,
        exchange_id="exchange-005",
        sequence=5,
        version=3,
    )

    assert decision.status is FederationSyncStatus.DUPLICATE
    assert decision.should_apply is False


def test_large_version_jump_is_visible_as_divergence(checkpoint):
    decision = evaluate_synchronization(
        checkpoint=checkpoint,
        exchange_id="exchange-005",
        sequence=5,
        version=8,
    )

    assert decision.status is FederationSyncStatus.DIVERGED
    assert decision.is_diverged is True
    assert decision.should_apply is False


def test_retry_record_preserves_retry_metadata():
    record = record_retry(
        exchange_id="exchange-006",
        participant_id="remote-001",
        sequence=6,
        version=6,
        retry_count=2,
        reason="sequence gap",
    )

    assert isinstance(record, FederationSyncRecord)
    assert record.status is FederationSyncStatus.RETRY
    assert record.retry_count == 2
    assert record.reason == "sequence gap"


def test_checkpoint_rejects_negative_sequence():
    with pytest.raises(ValueError):
        FederationCheckpoint(
            participant_id="remote-001",
            sequence=-1,
            version=0,
        )


def test_checkpoint_rejects_negative_version():
    with pytest.raises(ValueError):
        FederationCheckpoint(
            participant_id="remote-001",
            sequence=0,
            version=-1,
        )


def test_sync_record_is_immutable():
    record = FederationSyncRecord(
        exchange_id="exchange-001",
        participant_id="remote-001",
        sequence=1,
        version=1,
        status=FederationSyncStatus.APPLIED,
    )

    with pytest.raises(AttributeError):
        record.status = FederationSyncStatus.DIVERGED  # type: ignore[misc]


def test_invalid_seen_exchange_collection_is_rejected(checkpoint):
    with pytest.raises(TypeError):
        evaluate_synchronization(
            checkpoint=checkpoint,
            exchange_id="exchange-005",
            sequence=5,
            version=5,
            seen_exchange_ids={"exchange-004"},  # type: ignore[arg-type]
        )


def test_invalid_retry_count_is_rejected():
    with pytest.raises(ValueError):
        record_retry(
            exchange_id="exchange-001",
            participant_id="remote-001",
            sequence=1,
            version=1,
            retry_count=-1,
            reason="temporary failure",
        )
