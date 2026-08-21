# validator.py
from __future__ import annotations

import random
from typing import Dict

from .models import Proposal, ValidationOutcome


class PrivacyFilterValidatorProtocol:
    """Protocol for validating content after privacy filtering."""

    def validate(
        self,
        content: Dict[str, str],
        proposal: Proposal,
    ) -> ValidationOutcome:
        ...


class SimpleValidator:
    """Simple in-memory validator used for Phase 2 tests."""

    def __init__(self, threshold: float = 0.75):
        self.threshold = threshold

    def validate(
        self,
        content: Dict[str, str],
        proposal: Proposal,
    ) -> ValidationOutcome:
        if (
            "source_profile" not in content
            or content["source_profile"] != proposal.source_profile
        ):
            return ValidationOutcome(
                source_profile=proposal.source_profile,
                source_record_reference=proposal.source_reference,
                validation_score=0.0,
                is_validated=False,
                reason_for_rejection="Source profile mismatch",
            )

        if "text" not in content:
            return ValidationOutcome(
                source_profile=proposal.source_profile,
                source_record_reference=proposal.source_reference,
                validation_score=0.0,
                is_validated=False,
                reason_for_rejection="Missing text field",
            )

        score = random.uniform(0.5, 1.0)
        approved = score >= self.threshold

        return ValidationOutcome(
            source_profile=proposal.source_profile,
            source_record_reference=proposal.source_reference,
            validation_score=score,
            is_validated=approved,
            reason_for_rejection=None if approved else f"Score {score:.2f} too low",
        )
