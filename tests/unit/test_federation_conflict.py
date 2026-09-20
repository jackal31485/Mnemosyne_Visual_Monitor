import pytest

from src.domain.federation_conflict import (
    FederationConflict,
    FederationConflictKind,
    FederationConflictState,
    detect_federation_conflict,
)


@pytest.fixture
def conflict():
    return detect_federation_conflict(
        conflict_id="conflict-001",
        kind=FederationConflictKind.CONTENT,
        participant_ids=("remote-001", "local-001"),
        exchange_ids=("exchange-001", "exchange-002"),
        source_memory_ids=("memory-001", "memory-002"),
        description="Two exchanges contain conflicting observations.",
    )


def test_detected_conflict_is_open(conflict):
    assert conflict.state is FederationConflictState.OPEN
    assert conflict.is_open is True
    assert conflict.is_resolved is False


def test_conflict_is_attributable(conflict):
    assert conflict.is_attributable is True
    assert conflict.participant_ids == (
        "remote-001",
        "local-001",
    )
    assert conflict.exchange_ids == (
        "exchange-001",
        "exchange-002",
    )
    assert conflict.source_memory_ids == (
        "memory-001",
        "memory-002",
    )


def test_detection_does_not_resolve_conflict(conflict):
    assert conflict.state is FederationConflictState.OPEN
    assert conflict.resolution is None


def test_conflict_can_be_acknowledged(conflict):
    acknowledged = conflict.acknowledge()

    assert acknowledged.state is FederationConflictState.ACKNOWLEDGED
    assert acknowledged.resolution is None
    assert conflict.state is FederationConflictState.OPEN


def test_conflict_can_be_explicitly_resolved(conflict):
    resolved = conflict.resolve(
        "Human review selected the authoritative source."
    )

    assert resolved.state is FederationConflictState.RESOLVED
    assert resolved.is_resolved is True
    assert resolved.resolution is not None
    assert conflict.state is FederationConflictState.OPEN


def test_resolved_conflict_requires_resolution(conflict):
    with pytest.raises(ValueError):
        FederationConflict(
            conflict_id=conflict.conflict_id,
            kind=conflict.kind,
            state=FederationConflictState.RESOLVED,
            participant_ids=conflict.participant_ids,
            exchange_ids=conflict.exchange_ids,
            source_memory_ids=conflict.source_memory_ids,
            description=conflict.description,
        )


def test_empty_attribution_is_rejected():
    with pytest.raises(ValueError):
        detect_federation_conflict(
            conflict_id="conflict-001",
            kind=FederationConflictKind.CONTENT,
            participant_ids=(),
            exchange_ids=("exchange-001",),
            source_memory_ids=("memory-001",),
            description="Conflict",
        )


def test_empty_description_is_rejected():
    with pytest.raises(ValueError):
        detect_federation_conflict(
            conflict_id="conflict-001",
            kind=FederationConflictKind.CONTENT,
            participant_ids=("remote-001",),
            exchange_ids=("exchange-001",),
            source_memory_ids=("memory-001",),
            description="",
        )


def test_invalid_conflict_kind_is_rejected():
    with pytest.raises(TypeError):
        FederationConflict(
            conflict_id="conflict-001",
            kind="CONTENT",  # type: ignore[arg-type]
            state=FederationConflictState.OPEN,
            participant_ids=("remote-001",),
            exchange_ids=("exchange-001",),
            source_memory_ids=("memory-001",),
            description="Conflict",
        )


def test_conflict_is_immutable(conflict):
    with pytest.raises(AttributeError):
        conflict.state = FederationConflictState.RESOLVED  # type: ignore[misc]


def test_resolution_requires_non_empty_text(conflict):
    with pytest.raises(ValueError):
        conflict.resolve("")


def test_resolution_requires_string(conflict):
    with pytest.raises(TypeError):
        conflict.resolve(None)  # type: ignore[arg-type]
