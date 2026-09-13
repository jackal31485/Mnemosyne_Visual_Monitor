"""Phase 11E temporal graph projection.

Projects governed temporal evidence into the existing graph model.

This layer is descriptive only:
- it never mutates source memories;
- it never mutates temporal evidence;
- it never promotes evidence;
- it only projects evidence whose collective entry is promoted and non-revoked;
- it preserves temporal evidence provenance;
- it does not replace the existing similarity graph.

Temporal relationships are represented through the existing graph Edge DTO
using ``relationship_type="temporal:<relation>"``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from src.domain.collective import CollectiveDAO
from src.domain.collective_graph import Edge
from src.domain.temporal_evidence import TemporalEvidenceDAO
from src.domain.temporal_reasoning import (
    TemporalEvidenceRecord,
    TemporalRelationship,
    reason_over_evidence,
)


@dataclass(frozen=True, slots=True)
class TemporalGraphProjection:
    """One projected temporal graph edge with preserved provenance."""

    edge: Edge
    temporal_evidence_ids: tuple[str, ...]
    source_profile: str
    source_memory_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.temporal_evidence_ids:
            raise ValueError("temporal_evidence_ids must not be empty")
        if not self.source_profile:
            raise ValueError("source_profile must not be empty")


@dataclass(frozen=True, slots=True)
class TemporalGraphProjectionResult:
    """Deterministic collection of projected temporal graph edges."""

    projections: tuple[TemporalGraphProjection, ...]

    @property
    def count(self) -> int:
        return len(self.projections)

    @property
    def edges(self) -> tuple[Edge, ...]:
        return tuple(projection.edge for projection in self.projections)


class _EvidenceRecord:
    """Adapter exposing DAO evidence through the reasoning protocol."""

    def __init__(self, record: dict[str, object]) -> None:
        self.temporal_evidence_id = str(record["temporal_evidence_id"])
        self.start_time = (
            str(record["start_time"])
            if record["start_time"] is not None
            else None
        )
        self.end_time = (
            str(record["end_time"])
            if record["end_time"] is not None
            else None
        )
        self.precision = str(record["precision"])


class TemporalGraphProjector:
    """Project governed temporal relationships into the graph.

    ``collective_daos`` are authoritative profile-scoped collective stores.
    The temporal evidence DAO supplies governed temporal assertions.

    A temporal evidence record is eligible only when:
    1. its collective entry exists;
    2. that entry is promoted;
    3. that entry is not revoked;
    4. its source provenance matches the collective entry;
    5. its temporal bounds are usable by the canonical temporal reasoner.

    The projector does not infer missing dates or relationships.
    """

    def __init__(
        self,
        collective_daos: Sequence[CollectiveDAO],
        temporal_evidence_dao: TemporalEvidenceDAO,
    ) -> None:
        if not collective_daos:
            raise ValueError("collective_daos must not be empty")

        self.collective_daos = tuple(collective_daos)
        self.temporal_evidence_dao = temporal_evidence_dao

    def project(
        self,
        evidence: Iterable[dict[str, object]] | None = None,
    ) -> TemporalGraphProjectionResult:
        """Project eligible temporal evidence deterministically."""

        records = (
            list(evidence)
            if evidence is not None
            else self.temporal_evidence_dao.list()
        )

        eligible = self._eligible_evidence(records)

        if not eligible:
            return TemporalGraphProjectionResult(projections=())

        eligible = sorted(
            eligible,
            key=lambda record: str(record["temporal_evidence_id"]),
        )

        reasoner_records = tuple(
            _EvidenceRecord(record)
            for record in eligible
        )

        relationships = reason_over_evidence(reasoner_records)

        evidence_by_id = {
            str(record["temporal_evidence_id"]): record
            for record in eligible
        }

        projections: list[TemporalGraphProjection] = []

        for relationship in relationships:
            projection = self._relationship_projection(
                relationship,
                evidence_by_id,
            )

            if projection is not None:
                projections.append(projection)

        projections.sort(
            key=lambda projection: (
                projection.edge.source_id,
                projection.edge.target_id,
                projection.edge.relationship_type,
                projection.temporal_evidence_ids,
            )
        )

        return TemporalGraphProjectionResult(
            projections=tuple(projections)
        )

    def project_all(self) -> TemporalGraphProjectionResult:
        """Explicit alias for projecting all governed temporal evidence."""

        return self.project()

    def _eligible_evidence(
        self,
        records: Iterable[dict[str, object]],
    ) -> list[dict[str, object]]:
        eligible: list[dict[str, object]] = []

        collective_index = self._build_collective_index()

        for record in records:
            try:
                entry_id = int(record["collective_entry_id"])
            except (KeyError, TypeError, ValueError):
                continue

            collective = collective_index.get(entry_id)

            if collective is None:
                continue

            (
                source_profile,
                origin_memory_id,
            ) = collective

            lifecycle = self._lifecycle(entry_id, source_profile)

            if lifecycle is None:
                continue

            if lifecycle[0] != "promoted" or lifecycle[1]:
                continue

            if str(record.get("source_profile", "")) != source_profile:
                continue

            if str(record.get("source_memory_id", "")) != origin_memory_id:
                continue

            eligible.append(record)

        return eligible

    def _build_collective_index(
        self,
    ) -> dict[int, tuple[str, str]]:
        index: dict[int, tuple[str, str]] = {}

        for dao in self.collective_daos:
            for promoted_id in dao.list_promoted():
                entry_id = int(promoted_id)
                record = dao.get_by_id(entry_id)

                if not record:
                    continue

                source_profile = str(record[1])
                origin_memory_id = str(record[2])
                index[entry_id] = (
                    source_profile,
                    origin_memory_id,
                )

        return index

    def _lifecycle(
        self,
        entry_id: int,
        source_profile: str,
    ) -> tuple[str, bool] | None:
        for dao in self.collective_daos:
            lifecycle = dao.get_lifecycle_state(entry_id)

            if lifecycle is None:
                continue

            validated_at, revoked, _reason, promoted = lifecycle

            if not promoted:
                return None

            state = "revoked" if revoked else "promoted"

            record = dao.get_by_id(entry_id)
            if record is None:
                return None

            if str(record[1]) != source_profile:
                return None

            return state, bool(revoked)

        return None

    def _relationship_projection(
        self,
        relationship: TemporalRelationship,
        evidence_by_id: dict[str, dict[str, object]],
    ) -> TemporalGraphProjection | None:
        left_id = str(relationship.subject_evidence_id)
        right_id = str(relationship.object_evidence_id)

        left = evidence_by_id.get(left_id)
        right = evidence_by_id.get(right_id)

        if left is None or right is None:
            return None

        left_entry = int(left["collective_entry_id"])
        right_entry = int(right["collective_entry_id"])

        left_graph_id = self._graph_id(left_entry, left)
        right_graph_id = self._graph_id(right_entry, right)

        if left_graph_id is None or right_graph_id is None:
            return None

        source_id, target_id = sorted(
            (left_graph_id, right_graph_id)
        )

        source_records = (
            left,
            right,
        )

        source_profiles = {
            str(record["source_profile"])
            for record in source_records
        }

        if len(source_profiles) != 1:
            return None

        source_memory_ids = tuple(
            sorted(
                {
                    str(record["source_memory_id"])
                    for record in source_records
                }
            )
        )

        edge = Edge(
            source_id=source_id,
            target_id=target_id,
            similarity_score=0.0,
            relationship_type=f"temporal:{relationship.relation}",
        )

        return TemporalGraphProjection(
            edge=edge,
            temporal_evidence_ids=tuple(
                sorted((left_id, right_id))
            ),
            source_profile=next(iter(source_profiles)),
            source_memory_ids=source_memory_ids,
        )

    def _graph_id(
        self,
        entry_id: int,
        evidence: dict[str, object],
    ) -> str | None:
        source_profile = str(evidence.get("source_profile", ""))
        source_memory_id = str(evidence.get("source_memory_id", ""))

        if not source_profile or not source_memory_id:
            return None

        for dao in self.collective_daos:
            record = dao.get_by_id(entry_id)

            if record is None:
                continue

            if (
                str(record[1]) == source_profile
                and str(record[2]) == source_memory_id
            ):
                return f"{source_profile}:{source_memory_id}"

        return None
