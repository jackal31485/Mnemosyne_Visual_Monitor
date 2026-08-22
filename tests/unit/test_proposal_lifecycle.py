import pytest

from src.domain.collective import CollectiveDAO
from src.domain.proposal_lifecycle import ProposalManager


@pytest.fixture
def manager(tmp_path, monkeypatch):
    db_path = tmp_path / "collective.db"

    monkeypatch.setattr(
        "src.domain.collective.DB_PATH",
        db_path,
    )

    dao = CollectiveDAO()
    dao.ensure_schema()
    yield ProposalManager(dao)
    dao.close()


def test_propose_creates_reference_only_entry(manager):
    proposal_id = manager.propose("athena", "memory-123")

    entry = manager.dao.get_by_id(proposal_id)

    assert entry is not None
    assert entry[1] == "athena"
    assert entry[2] == "memory-123"
    assert entry[4] is None
    assert entry[8] is None


def test_propose_rejects_empty_source_profile(manager):
    with pytest.raises(ValueError, match="source_profile"):
        manager.propose("", "memory-123")


def test_propose_rejects_empty_memory_reference(manager):
    with pytest.raises(ValueError, match="origin_memory_id"):
        manager.propose("athena", "")


def test_validate_proposal(manager):
    proposal_id = manager.propose("athena", "memory-123")

    manager.validate(proposal_id, "hawk", score=0.95)

    state = manager.dao.get_lifecycle_state(proposal_id)

    assert state is not None
    validated_at, revoked, reason, promoted = state
    assert validated_at is not None
    assert revoked == 0
    assert reason is None
    assert promoted == 0

    entry = manager.dao.get_by_id(proposal_id)
    assert entry[6] == "hawk"
    assert entry[5] == pytest.approx(0.95)


def test_validate_rejects_empty_validator(manager):
    proposal_id = manager.propose("athena", "memory-123")

    with pytest.raises(ValueError, match="validator_profile"):
        manager.validate(proposal_id, "")


def test_validate_rejects_missing_proposal(manager):
    with pytest.raises(KeyError):
        manager.validate(99999, "hawk")


def test_duplicate_validation_is_rejected(manager):
    proposal_id = manager.propose("athena", "memory-123")

    manager.validate(proposal_id, "hawk")

    with pytest.raises(ValueError, match="already validated"):
        manager.validate(proposal_id, "pope")


def test_reject_proposal(manager):
    proposal_id = manager.propose("athena", "memory-123")

    manager.reject(proposal_id, "Insufficient confidence")

    state = manager.dao.get_lifecycle_state(proposal_id)

    assert state is not None
    validated_at, revoked, reason, promoted = state
    assert revoked == 1
    assert reason == "Insufficient confidence"
    assert validated_at is None
    assert promoted == 0


def test_reject_requires_reason(manager):
    proposal_id = manager.propose("athena", "memory-123")

    with pytest.raises(ValueError, match="rejection reason"):
        manager.reject(proposal_id, "")


def test_rejected_proposal_cannot_be_validated(manager):
    proposal_id = manager.propose("athena", "memory-123")

    manager.reject(proposal_id, "Rejected")

    with pytest.raises(ValueError, match="rejected"):
        manager.validate(proposal_id, "hawk")


def test_rejected_proposal_cannot_be_promoted(manager):
    proposal_id = manager.propose("athena", "memory-123")

    manager.reject(proposal_id, "Rejected")

    with pytest.raises(ValueError, match="rejected"):
        manager.promote(proposal_id)


def test_unvalidated_proposal_cannot_be_promoted(manager):
    proposal_id = manager.propose("athena", "memory-123")

    with pytest.raises(ValueError, match="validated"):
        manager.promote(proposal_id)


def test_validated_proposal_can_be_promoted(manager):
    proposal_id = manager.propose("athena", "memory-123")

    manager.validate(proposal_id, "hawk", score=0.9)
    manager.promote(proposal_id)

    state = manager.dao.get_lifecycle_state(proposal_id)

    assert state is not None
    validated_at, revoked, reason, promoted = state
    assert validated_at is not None
    assert revoked == 0
    assert reason is None
    assert promoted == 1


def test_promoted_proposal_cannot_be_promoted_again(manager):
    proposal_id = manager.propose("athena", "memory-123")

    manager.validate(proposal_id, "hawk")
    manager.promote(proposal_id)

    with pytest.raises(ValueError, match="already promoted"):
        manager.promote(proposal_id)


def test_promoted_proposal_cannot_be_validated(manager):
    proposal_id = manager.propose("athena", "memory-123")

    manager.validate(proposal_id, "hawk")
    manager.promote(proposal_id)

    with pytest.raises(ValueError, match="promoted"):
        manager.validate(proposal_id, "pope")


def test_promoted_proposal_cannot_be_rejected(manager):
    proposal_id = manager.propose("athena", "memory-123")

    manager.validate(proposal_id, "hawk")
    manager.promote(proposal_id)

    with pytest.raises(ValueError, match="finalized"):
        manager.reject(proposal_id, "Too late")


def test_private_memory_content_is_not_stored(manager):
    private_content = "PRIVATE RAW MNEMOSYNE MEMORY CONTENT"

    proposal_id = manager.propose(
        "athena",
        "memory-123",
    )

    row = manager.dao.conn.execute(
        "SELECT * FROM collective_entries WHERE id = ?",
        (proposal_id,),
    ).fetchone()

    assert private_content not in str(tuple(row))
    assert row["origin_memory_id"] == "memory-123"
