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


def test_promotion_after_validation(manager):
    proposal_id = manager.propose("athena", "memory-123")

    manager.validate(proposal_id, "hawk", score=0.95)
    manager.promote(proposal_id)

    state = manager.dao.get_lifecycle_state(proposal_id)

    assert state is not None
    validated_at, revoked, reason, promoted = state
    assert validated_at is not None
    assert revoked == 0
    assert reason is None
    assert promoted == 1


def test_promotion_before_validation_fails(manager):
    proposal_id = manager.propose("athena", "memory-123")

    with pytest.raises(ValueError, match="validated"):
        manager.promote(proposal_id)


def test_rejected_proposal_cannot_be_promoted(manager):
    proposal_id = manager.propose("athena", "memory-123")

    manager.reject(proposal_id, "Insufficient confidence")

    with pytest.raises(ValueError, match="rejected"):
        manager.promote(proposal_id)


def test_double_promotion_fails(manager):
    proposal_id = manager.propose("athena", "memory-123")

    manager.validate(proposal_id, "hawk", score=0.9)
    manager.promote(proposal_id)

    with pytest.raises(ValueError, match="already promoted"):
        manager.promote(proposal_id)


def test_list_promoted_returns_only_promoted_ids(manager):
    first = manager.propose("athena", "memory-1")
    second = manager.propose("hawk", "memory-2")
    third = manager.propose("pope", "memory-3")

    manager.validate(first, "hawk", score=0.9)
    manager.promote(first)

    manager.validate(third, "athena", score=0.95)
    manager.promote(third)

    assert manager.dao.list_promoted() == [first, third]
    assert second not in manager.dao.list_promoted()


def test_get_by_source_returns_reference(manager):
    proposal_id = manager.propose("athena", "memory-123")

    entry = manager.dao.get_by_source("athena", "memory-123")

    assert entry is not None
    assert entry[0] == proposal_id
    assert entry[1] == "athena"
    assert entry[2] == "memory-123"
    assert len(entry) == 9


def test_get_by_source_returns_none_when_missing(manager):
    assert manager.dao.get_by_source("athena", "does-not-exist") is None


def test_provenance_preserved_after_promotion(manager):
    proposal_id = manager.propose("athena", "memory-123")

    before = manager.dao.get_by_id(proposal_id)

    manager.validate(proposal_id, "hawk", score=0.95)
    manager.promote(proposal_id)

    after = manager.dao.get_by_id(proposal_id)

    assert before is not None
    assert after is not None

    assert after[1] == before[1] == "athena"
    assert after[2] == before[2] == "memory-123"
    assert after[3] == before[3]


def test_raw_private_memory_content_is_not_stored(manager):
    private_content = "PRIVATE RAW MNEMOSYNE MEMORY CONTENT"

    proposal_id = manager.propose("athena", "memory-123")
    manager.validate(proposal_id, "hawk", score=0.95)
    manager.promote(proposal_id)

    row = manager.dao.conn.execute(
        "SELECT * FROM collective_entries WHERE id = ?",
        (proposal_id,),
    ).fetchone()

    assert row is not None
    assert private_content not in str(tuple(row))
    assert row["origin_memory_id"] == "memory-123"
