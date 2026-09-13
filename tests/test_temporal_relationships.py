from __future__ import annotations

import pytest

from src.domain.temporal_reasoning import TemporalRelationship


def test_temporal_relationship_uses_canonical_evidence_ids():
    relationship = TemporalRelationship(
        subject_evidence_id=1,
        object_evidence_id=2,
        relation="before",
    )

    assert relationship.subject_evidence_id == 1
    assert relationship.object_evidence_id == 2
    assert relationship.relation == "before"


@pytest.mark.parametrize(
    "relation",
    [
        "before",
        "after",
        "meets",
        "overlaps",
        "during",
        "contains",
        "starts",
        "started_by",
        "ends",
        "ended_by",
        "at",
    ],
)
def test_canonical_temporal_relationship_accepts_supported_relations(relation):
    relationship = TemporalRelationship(
        subject_evidence_id=1,
        object_evidence_id=2,
        relation=relation,
    )

    assert relationship.relation == relation


def test_temporal_relationship_is_immutable():
    relationship = TemporalRelationship(
        subject_evidence_id=1,
        object_evidence_id=2,
        relation="before",
    )

    with pytest.raises(AttributeError):
        relationship.relation = "after"


def test_temporal_relationship_rejects_non_integer_subject():
    with pytest.raises(TypeError):
        TemporalRelationship(
            subject_evidence_id="1",
            object_evidence_id=2,
            relation="before",
        )


def test_temporal_relationship_rejects_non_integer_object():
    with pytest.raises(TypeError):
        TemporalRelationship(
            subject_evidence_id=1,
            object_evidence_id="2",
            relation="before",
        )


def test_temporal_relationship_rejects_self_reference():
    with pytest.raises(ValueError):
        TemporalRelationship(
            subject_evidence_id=1,
            object_evidence_id=1,
            relation="before",
        )


def test_temporal_relationship_rejects_unsupported_relation():
    with pytest.raises(ValueError):
        TemporalRelationship(
            subject_evidence_id=1,
            object_evidence_id=2,
            relation="continues",
        )


def test_temporal_relationship_is_canonical_class():
    relationship = TemporalRelationship(
        subject_evidence_id=1,
        object_evidence_id=2,
        relation="before",
    )

    assert type(relationship).__module__ == "src.domain.temporal_reasoning"
    assert type(relationship).__name__ == "TemporalRelationship"
