from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.domain.temporal_assertion import TemporalAssertion
from src.domain.temporal_change import TemporalChangeAssertion
from src.domain.temporal_change_extractor import TemporalChangeExtractor
from src.domain.temporal_extractor import TemporalExtractor
from src.domain.temporal_promotion import (
    TemporalPromotionResult,
    TemporalPromotionService,
)


class TemporalAssertionExtractor(Protocol):
    def extract(
        self,
        text: str,
        *,
        collective_entry_id: int,
        source_memory_id: str,
        source_profile: str,
    ) -> list[TemporalAssertion]:
        ...


class TemporalChangeAssertionExtractor(Protocol):
    def extract(
        self,
        text: str,
        *,
        collective_entry_id: int,
        source_memory_id: str,
        source_profile: str,
    ) -> list[TemporalChangeAssertion]:
        ...


@dataclass(frozen=True, slots=True)
class TemporalPipelineResult:
    """Results produced by one deterministic temporal processing pass."""

    temporal_assertions: tuple[TemporalAssertion, ...]
    change_assertions: tuple[TemporalChangeAssertion, ...]
    temporal_evidence: tuple[TemporalPromotionResult, ...]
    change_evidence: tuple[TemporalPromotionResult, ...]

    @property
    def total_assertions(self) -> int:
        return len(self.temporal_assertions) + len(self.change_assertions)

    @property
    def total_evidence(self) -> int:
        return len(self.temporal_evidence) + len(self.change_evidence)


class TemporalExtractionPromotionPipeline:
    """Extract and promote explicit temporal information.

    This is intentionally an orchestration boundary only.

    The pipeline:
      1. receives caller-supplied source text;
      2. performs explicit temporal extraction;
      3. performs explicit state-change extraction;
      4. promotes those immutable assertions through the governed
         TemporalPromotionService.

    It does not infer chronology, resolve entities, detect conflicts,
    rewrite source memories, or perform retrieval.
    """

    def __init__(
        self,
        *,
        temporal_extractor: TemporalAssertionExtractor | None = None,
        change_extractor: TemporalChangeAssertionExtractor | None = None,
        promotion_service: TemporalPromotionService,
    ) -> None:
        self.temporal_extractor = (
            temporal_extractor
            if temporal_extractor is not None
            else TemporalExtractor()
        )
        self.change_extractor = (
            change_extractor
            if change_extractor is not None
            else TemporalChangeExtractor()
        )
        self.promotion_service = promotion_service

    def process(
        self,
        text: str,
        *,
        collective_entry_id: int,
        source_memory_id: str,
        source_profile: str,
    ) -> TemporalPipelineResult:
        if not isinstance(text, str):
            raise TypeError("text must be a string")

        if not isinstance(collective_entry_id, int):
            raise TypeError("collective_entry_id must be an integer")

        if not isinstance(source_memory_id, str):
            raise TypeError("source_memory_id must be a string")

        if not isinstance(source_profile, str):
            raise TypeError("source_profile must be a string")

        temporal_assertions = self.temporal_extractor.extract(
            text,
            collective_entry_id=collective_entry_id,
            source_memory_id=source_memory_id,
            source_profile=source_profile,
        )

        change_assertions = self.change_extractor.extract(
            text,
            collective_entry_id=collective_entry_id,
            source_memory_id=source_memory_id,
            source_profile=source_profile,
        )

        temporal_evidence = self.promotion_service.promote_many(
            temporal_assertions
        )

        change_evidence = self.promotion_service.promote_changes(
            change_assertions
        )

        return TemporalPipelineResult(
            temporal_assertions=tuple(temporal_assertions),
            change_assertions=tuple(change_assertions),
            temporal_evidence=tuple(temporal_evidence),
            change_evidence=tuple(change_evidence),
        )
