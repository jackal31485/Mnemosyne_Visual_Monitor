import datetime
from typing import Optional

from .collective import CollectiveDAO


class ProposalManager:
    """Manage the Phase 3A collective proposal lifecycle."""

    def __init__(self, dao: CollectiveDAO | None = None) -> None:
        self.dao = dao or CollectiveDAO()
        self.dao.ensure_schema()

    def propose(
        self,
        source_profile: str,
        origin_memory_id: str,
        *,
        proposed_at: Optional[str] = None,
    ) -> int:
        if not source_profile:
            raise ValueError("source_profile cannot be empty")
        if not origin_memory_id:
            raise ValueError("origin_memory_id cannot be empty")

        if proposed_at is None:
            proposed_at = datetime.datetime.now(datetime.UTC).isoformat()

        return self.dao.insert_collective_entry(
            source_profile=source_profile,
            origin_memory_id=origin_memory_id,
            proposed_at=proposed_at,
        )

    def validate(
        self,
        proposal_id: int,
        validator_profile: str,
        *,
        score: Optional[float] = None,
    ) -> None:
        if not validator_profile:
            raise ValueError("validator_profile cannot be empty")

        entry = self.dao.get_by_id(proposal_id)
        if entry is None:
            raise KeyError(f"Proposal {proposal_id} not found")

        validated_at, revoked, _, promoted = self._state(proposal_id)

        if revoked:
            raise ValueError("Cannot validate a rejected proposal")

        if promoted:
            raise ValueError("Cannot validate a promoted proposal")

        if validated_at is not None:
            raise ValueError("Proposal already validated")

        now = datetime.datetime.now(datetime.UTC).isoformat()

        self.dao.conn.execute(
            """
            UPDATE collective_entries
            SET validator_profile = ?,
                validated_at = ?,
                validation_score = ?
            WHERE id = ?
            """,
            (validator_profile, now, score, proposal_id),
        )
        self.dao.conn.commit()

    def reject(self, proposal_id: int, reason: str) -> None:
        if not reason:
            raise ValueError("rejection reason cannot be empty")

        entry = self.dao.get_by_id(proposal_id)
        if entry is None:
            raise KeyError(f"Proposal {proposal_id} not found")

        validated_at, revoked, _, promoted = self._state(proposal_id)

        if revoked or promoted:
            raise ValueError("Cannot reject a finalized proposal")

        if validated_at is not None:
            raise ValueError("Cannot reject an already-validated proposal")

        self.dao.update_entry_revoked(
            entry_id=proposal_id,
            reason=reason,
        )

    def revoke(self, proposal_id: int, reason: str) -> None:
        """Revoke a proposal without altering its provenance or validation data."""
        entry = self.dao.get_by_id(proposal_id)
        if entry is None:
            raise KeyError(f"Proposal {proposal_id} not found")

        _, revoked, _, _ = self._state(proposal_id)

        if revoked:
            raise ValueError("Entry already revoked")

        if not reason:
            raise ValueError("rejection reason cannot be empty")

        self.dao.revoke_entry(
            entry_id=proposal_id,
            reason=reason,
        )

    def promote(self, proposal_id: int) -> None:
        entry = self.dao.get_by_id(proposal_id)
        if entry is None:
            raise KeyError(f"Proposal {proposal_id} not found")

        validated_at, revoked, _, promoted = self._state(proposal_id)

        if revoked:
            raise ValueError("Cannot promote a rejected proposal")

        if promoted:
            raise ValueError("Proposal is already promoted")

        if validated_at is None:
            raise ValueError("Proposal must be validated before promotion")

        self.dao.update_entry_promoted(proposal_id)

    def _state(self, proposal_id: int):
        state = self.dao.get_lifecycle_state(proposal_id)
        if state is None:
            raise KeyError(f"Proposal {proposal_id} not found")
        return state
