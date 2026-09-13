from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.domain.temporal_reasoning import TemporalRelationship
from src.services.temporal_relationship_service import (
    TemporalRelationshipResult,
    TemporalRelationshipService,
)


def evidence(
    evidence_id: int,
    start: str | None,
    end: str | None = None,
    precision: str = "day",
):
    return SimpleNamespace(
        temporal_evidence_id=evidence_id,
        start_time=start,
        end_time=end,
        precision=precision,
    )


@pytest.fixture
def service() -> TemporalRelationshipService:
    return TemporalRelationshipService()


def test_derive_returns_canonical_relationships(service):
    result = service.derive(
        [
            evidence(1, "2026-09-10T00:00:00"),
            evidence(2, "2026-09-12T00:00:00"),
        ]
    )

    assert isinstance(result, TemporalRelationshipResult)
    assert result.count == 1
    assert result.relationships[0] == TemporalRelationship(
        subject_evidence_id=1,
        object_evidence_id=2,
        relation="before",
    )


def test_derive_preserves_canonical_pair_order(service):
    result = service.derive(
        [
            evidence(1, "2026-09-10T00:00:00"),
            evidence(2, "2026-09-12T00:00:00"),
            evidence(3, "2026-09-15T00:00:00"),
        ]
    )

    assert [
        (
            relationship.subject_evidence_id,
            relationship.object_evidence_id,
        )
        for relationship in result.relationships
    ] == [
        (1, 2),
        (1, 3),
        (2, 3),
    ]


def test_derive_preserves_interval_relationship_semantics(service):
    result = service.derive(
        [
            evidence(
                1,
                "2026-09-10T00:00:00",
                "2026-09-20T00:00:00",
            ),
            evidence(
                2,
                "2026-09-12T00:00:00",
                "2026-09-15T00:00:00",
            ),
        ]
    )

    assert result.relationships[0].relation == "contains"


def test_derive_excludes_unbounded_evidence(service):
    result = service.derive(
        [
            evidence(1, None),
            evidence(2, "2026-09-12T00:00:00"),
        ]
    )

    assert result.relationships == ()
    assert result.count == 0


def test_derive_excludes_unknown_precision(service):
    result = service.derive(
        [
            evidence(
                1,
                "2026-09-10T00:00:00",
                precision="unknown",
            ),
            evidence(
                2,
                "2026-09-12T00:00:00",
                precision="day",
            ),
        ]
    )

    assert result.relationships == ()


def test_derive_does_not_persist_relationships(service, tmp_path):
    db_path = tmp_path / "collective.db"

    result = service.derive(
        [
            evidence(1, "2026-09-10T00:00:00"),
            evidence(2, "2026-09-12T00:00:00"),
        ]
    )

    assert result.count == 1
    assert not db_path.exists()


def test_derive_many_returns_one_result_per_group(service):
    results = service.derive_many(
        [
            [
                evidence(1, "2026-09-10T00:00:00"),
                evidence(2, "2026-09-12T00:00:00"),
            ],
            [
                evidence(3, "2026-09-15T00:00:00"),
                evidence(4, "2026-09-16T00:00:00"),
            ],
        ]
    )

    assert len(results) == 2
    assert results[0].count == 1
    assert results[1].count == 1


def test_derive_accepts_iterators(service):
    result = service.derive(
        iter(
            [
                evidence(1, "2026-09-10T00:00:00"),
                evidence(2, "2026-09-12T00:00:00"),
            ]
        )
    )

    assert result.count == 1


def test_derive_does_not_create_second_relationship_type(service):
    result = service.derive(
        [
            evidence(1, "2026-09-10T00:00:00"),
            evidence(2, "2026-09-12T00:00:00"),
        ]
    )

    assert type(result.relationships[0]).__module__ == (
        "src.domain.temporal_reasoning"
    )


def test_result_is_immutable(service):
    result = service.derive(
        [
            evidence(1, "2026-09-10T00:00:00"),
            evidence(2, "2026-09-12T00:00:00"),
        ]
    )

    with pytest.raises(AttributeError):
        result.relationships = ()
