from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from src.domain.temporal_assertion import TemporalAssertion


def make_assertion(**overrides):
    values = dict(
        collective_entry_id=7,
        subject_type="memory",
        subject_id="memory-7",
        temporal_relation="at",
        precision="day",
        start_time=datetime(2026, 9, 10),
        extraction_method="explicit_date",
        source_memory_id="memory-7",
        source_profile="athena",
        confidence=0.98,
        evidence_kind="observed",
    )
    values.update(overrides)
    return TemporalAssertion(**values)


def test_assertion_round_trips_normalized_temporal_values():
    assertion = make_assertion()
    assert assertion.collective_entry_id == 7
    assert assertion.subject_type == "memory"
    assert assertion.temporal_relation == "at"
    assert assertion.precision == "day"
    assert assertion.start_time == "2026-09-10T00:00:00"
    assert assertion.end_time is None
    assert assertion.confidence == 0.98


def test_entity_and_relationship_assertions_are_supported():
    entity = make_assertion(
        subject_type="entity",
        subject_id="entity-project",
        temporal_relation="ongoing",
        precision="month",
        start_time="2026-01",
    )
    relationship = make_assertion(
        subject_type="relationship",
        subject_id="relationship-1",
        object_type="entity",
        object_id="entity-2",
        temporal_relation="before",
        precision="day",
        start_time="2026-08-01",
        end_time="2026-08-02",
    )
    assert entity.subject_type == "entity"
    assert relationship.subject_type == "relationship"
    assert relationship.object_type == "entity"


def test_assertions_are_immutable():
    assertion = make_assertion()
    with pytest.raises(FrozenInstanceError):
        assertion.subject_id = "changed"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("subject_type", "profile"),
        ("temporal_relation", "yesterday"),
        ("precision", "exact"),
        ("evidence_kind", "fact"),
    ],
)
def test_invalid_enums_are_rejected(field, value):
    with pytest.raises(ValueError):
        make_assertion(**{field: value})


@pytest.mark.parametrize(
    "field",
    ["subject_id", "extraction_method", "source_memory_id", "source_profile"],
)
def test_required_text_fields_are_rejected_when_empty(field):
    with pytest.raises(ValueError):
        make_assertion(**{field: ""})


@pytest.mark.parametrize("collective_entry_id", [0, -1, False, "7"])
def test_collective_entry_id_must_be_positive_integer(collective_entry_id):
    with pytest.raises(ValueError):
        make_assertion(collective_entry_id=collective_entry_id)


@pytest.mark.parametrize("confidence", [-0.01, 1.01, "0.5", True])
def test_confidence_must_be_between_zero_and_one(confidence):
    with pytest.raises(ValueError):
        make_assertion(confidence=confidence)


def test_confidence_may_be_none():
    assert make_assertion(confidence=None).confidence is None


def test_object_type_and_id_must_be_paired():
    with pytest.raises(ValueError):
        make_assertion(object_type="entity")
    with pytest.raises(ValueError):
        make_assertion(object_id="entity-1")


def test_object_type_must_use_supported_subject_types():
    with pytest.raises(ValueError):
        make_assertion(
            object_type="profile",
            object_id="profile-1",
        )


def test_unknown_precision_cannot_claim_explicit_bounds():
    with pytest.raises(ValueError):
        make_assertion(
            precision="unknown",
            start_time="2026-09-10",
        )
    with pytest.raises(ValueError):
        make_assertion(
            precision="unknown",
            end_time="2026-09-10",
        )


def test_one_sided_temporal_bounds_are_preserved():
    assertion = make_assertion(
        precision="month",
        start_time="2026-09",
    )
    assert assertion.start_time == "2026-09"
    assert assertion.end_time is None


def test_invalid_interval_is_rejected():
    with pytest.raises(ValueError):
        make_assertion(
            start_time="2026-09-12",
            end_time="2026-09-10",
        )


def test_inferred_evidence_remains_explicitly_distinct():
    assertion = make_assertion(
        evidence_kind="inferred",
        extraction_method="temporal_reasoner",
    )
    assert assertion.evidence_kind == "inferred"


def test_datetime_bounds_are_normalized_to_iso_strings():
    assertion = make_assertion(
        start_time=datetime(2026, 9, 10, 12, 30),
        end_time=datetime(2026, 9, 11, 8, 15),
    )
    assert assertion.start_time == "2026-09-10T12:30:00"
    assert assertion.end_time == "2026-09-11T08:15:00"


def test_confidence_is_normalized_to_float():
    assertion = make_assertion(confidence=1)
    assert assertion.confidence == 1.0
    assert isinstance(assertion.confidence, float)
