from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from src.domain.temporal_reasoning import (
    TemporalEvidenceRecord,
    TemporalRelationship,
    reason_over_evidence,
)


@dataclass(frozen=True, slots=True)
class TemporalRelationshipResult:
    """Deterministically derived relationships between temporal evidence."""

    relationships: tuple[TemporalRelationship, ...]

    @property
    def count(self) -> int:
        return len(self.relationships)


class TemporalRelationshipService:
    """Derive temporal relationships from governed temporal evidence.

    This service performs deterministic interval comparison only.

    It does not:
      - persist relationships;
      - create entity relationships;
      - perform NLP;
      - infer missing dates;
      - resolve entities;
      - promote derived relationships;
      - modify source memory or evidence.
    """

    def derive(
        self,
        evidence: Iterable[TemporalEvidenceRecord],
    ) -> TemporalRelationshipResult:
        relationships = reason_over_evidence(evidence)

        return TemporalRelationshipResult(
            relationships=relationships,
        )

    def derive_many(
        self,
        evidence_groups: Iterable[Iterable[TemporalEvidenceRecord]],
    ) -> tuple[TemporalRelationshipResult, ...]:
        return tuple(
            self.derive(evidence_group)
            for evidence_group in evidence_groups
        )
