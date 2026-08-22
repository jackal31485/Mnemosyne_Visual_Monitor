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


def test_list_by_state_returns_sorted_ids(manager):
    proposed_a = manager.propose("athena", "memory-a")
    proposed_b = manager.propose("hawk", "memory-b")
    proposed_c = manager.propose("pope", "memory-c")

    assert manager.dao.list_by_state("proposed") == [
        proposed_a,
        proposed_b,
        proposed_c,
    ]

    manager.validate(proposed_b, "athena", score=0.9)

    assert manager.dao.list_validated() == [proposed_b]
    assert manager.dao.list_proposed() == [proposed_a, proposed_c]


def test_rejected_and_revoked_states(manager):
    first = manager.propose("athena", "memory-1")
    second = manager.propose("hawk", "memory-2")

    manager.reject(first, "Insufficient confidence")
    manager.revoke(second, "Source retracted reference")

    # REJECTED is a subset of REVOKED: both are is_revoked=1 and unvalidated.
    assert manager.dao.list_rejected() == [first, second]
    assert manager.dao.list_revoked() == [first, second]


def test_revoke_entry_sets_flags_and_reason(manager):
    proposal_id = manager.propose("athena", "memory-123")

    before = manager.dao.get_by_id(proposal_id)

    manager.dao.revoke_entry(
        proposal_id,
        "Source requested removal",
    )

    after = manager.dao.get_by_id(proposal_id)

    assert before is not None
    assert after is not None

    assert after[0] == before[0]
    assert after[1] == before[1]
    assert after[2] == before[2]
    assert after[3] == before[3]
    assert after[4] == before[4]
    assert after[5] == before[5]
    assert after[6] == before[6]
    assert after[7] == 1
    assert after[8] == "Source requested removal"


def test_revoke_existing_revoked_fails(manager):
    proposal_id = manager.propose("athena", "memory-123")

    manager.revoke(proposal_id, "First revocation")

    with pytest.raises(ValueError, match="already revoked"):
        manager.revoke(proposal_id, "Second revocation")


def test_revoke_missing_entry_fails(manager):
    with pytest.raises(KeyError):
        manager.revoke(99999, "Missing")


def test_revoke_requires_reason(manager):
    proposal_id = manager.propose("athena", "memory-123")

    with pytest.raises(ValueError, match="rejection reason"):
        manager.revoke(proposal_id, "")


def test_revoke_cannot_promote_after_revocation(manager):
    proposal_id = manager.propose("athena", "memory-123")

    manager.revoke(proposal_id, "Source retracted")

    with pytest.raises(ValueError, match="rejected"):
        manager.promote(proposal_id)


def test_promoted_entry_can_be_revoked(manager):
    proposal_id = manager.propose("athena", "memory-123")

    manager.validate(proposal_id, "hawk", score=0.95)
    manager.promote(proposal_id)
    manager.revoke(proposal_id, "Source retracted promoted reference")

    state = manager.dao.get_lifecycle_state(proposal_id)

    assert state is not None
    validated_at, revoked, reason, promoted = state

    assert validated_at is not None
    assert revoked == 1
    assert reason == "Source retracted promoted reference"
    assert promoted == 1

    assert manager.dao.list_promoted() == [proposal_id]
    assert manager.dao.list_revoked() == [proposal_id]


def test_provenance_preserved_after_revocation(manager):
    proposal_id = manager.propose("athena", "memory-123")

    before = manager.dao.get_by_id(proposal_id)

    manager.validate(proposal_id, "hawk", score=0.95)
    manager.promote(proposal_id)
    manager.revoke(proposal_id, "Source retracted")

    after = manager.dao.get_by_id(proposal_id)

    assert before is not None
    assert after is not None

    assert after[1] == before[1] == "athena"
    assert after[2] == before[2] == "memory-123"
    assert after[3] == before[3]
    assert after[4] is not None
    assert after[5] == pytest.approx(0.95)
    assert after[6] == "hawk"


def test_double_validation_still_fails(manager):
    proposal_id = manager.propose("athena", "memory-123")

    manager.validate(proposal_id, "hawk", score=0.9)

    with pytest.raises(ValueError, match="already validated"):
        manager.validate(proposal_id, "pope", score=0.8)


def test_raw_private_memory_content_is_not_stored(manager):
    private_content = "PRIVATE RAW MNEMOSYNE MEMORY CONTENT"

    proposal_id = manager.propose("athena", "memory-123")
    manager.validate(proposal_id, "hawk", score=0.95)
    manager.promote(proposal_id)
    manager.revoke(proposal_id, "Source retracted")

    row = manager.dao.conn.execute(
        "SELECT * FROM collective_entries WHERE id = ?",
        (proposal_id,),
    ).fetchone()

    assert row is not None
    assert private_content not in str(tuple(row))
    assert row["origin_memory_id"] == "memory-123"
