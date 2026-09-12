from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.domain.temporal_assertion import TemporalAssertion
from src.domain.temporal_change import TemporalChangeAssertion


class TemporalEvidenceWriter(Protocol):
    """Minimal persistence contract required by temporal promotion."""

    def add(
        self,
        *,
        collective_entry_id: int,
        subject_type: str,
        subject_id: str,
        object_type: str | None = None,
        object_id: str | None = None,
        temporal_relation: str,
        start_time: str | None = None,
        end_time: str | None = None,
        precision: str = "unknown",
        confidence: float | None = None,
        evidence_kind: str = "observed",
        extraction_method: str,
        source_memory_id: str,
        source_profile: str,
    ) -> object:
        ...


@dataclass(frozen=True, slots=True)
class TemporalPromotionResult:
    """Result of promoting one extracted temporal assertion."""

    evidence: object
    assertion_kind: str


class TemporalPromotionService:
    """Promote validated temporal assertions into governed evidence.

    This service deliberately does not perform NLP, inference, chronology
    resolution, entity resolution, or retrieval. It translates an already
    extracted assertion into the governed temporal-evidence DAO contract.
    """

    def __init__(self, dao: TemporalEvidenceWriter) -> None:
        self.dao = dao

    def promote(
        self,
        assertion: TemporalAssertion,
    ) -> TemporalPromotionResult:
        if not isinstance(assertion, TemporalAssertion):
            raise TypeError(
                "promote expects a TemporalAssertion"
            )

        evidence = self.dao.add(
            collective_entry_id=assertion.collective_entry_id,
            subject_type=assertion.subject_type,
            subject_id=assertion.subject_id,
            object_type=assertion.object_type,
            object_id=assertion.object_id,
            temporal_relation=assertion.temporal_relation,
            start_time=assertion.start_time,
            end_time=assertion.end_time,
            precision=assertion.precision,
            confidence=assertion.confidence,
            evidence_kind=assertion.evidence_kind,
            extraction_method=assertion.extraction_method,
            source_memory_id=assertion.source_memory_id,
            source_profile=assertion.source_profile,
        )

        return TemporalPromotionResult(
            evidence=evidence,
            assertion_kind="temporal",
        )

    def promote_change(
        self,
        assertion: TemporalChangeAssertion,
    ) -> TemporalPromotionResult:
        if not isinstance(assertion, TemporalChangeAssertion):
            raise TypeError(
                "promote_change expects a TemporalChangeAssertion"
            )

        # State changes are represented as temporal "during" evidence
        # anchored to the source assertion. This stage does not invent
        # start/end timestamps or chronology.
        evidence = self.dao.add(
            collective_entry_id=assertion.collective_entry_id,
            subject_type=assertion.subject_type,
            subject_id=assertion.subject_id,
            temporal_relation="during",
            start_time=None,
            end_time=None,
            precision="unknown",
            confidence=None,
            evidence_kind="observed",
            extraction_method=assertion.extraction_method,
            source_memory_id=assertion.source_memory_id,
            source_profile=assertion.source_profile,
        )

        return TemporalPromotionResult(
            evidence=evidence,
            assertion_kind="state_change",
        )

    def promote_many(
        self,
        assertions: list[TemporalAssertion],
    ) -> list[TemporalPromotionResult]:
        if not isinstance(assertions, list):
            raise TypeError("assertions must be a list")

        return [
            self.promote(assertion)
            for assertion in assertions
        ]

    def promote_changes(
        self,
        assertions: list[TemporalChangeAssertion],
    ) -> list[TemporalPromotionResult]:
        if not isinstance(assertions, list):
            raise TypeError("assertions must be a list")

        return [
            self.promote_change(assertion)
            for assertion in assertions
        ]
