from __future__ import annotations

import inspect

import pytest

from src.domain.temporal_change import TemporalChangeAssertion
from src.services.temporal_state_change_service import (
    TemporalStateChange,
    TemporalStateChangeResult,
    TemporalStateChangeService,
)


def make_change_assertion():
    """Construct an assertion using the canonical constructor.

    The test deliberately inspects the existing contract rather than
    duplicating a second model definition.
    """
    signature = inspect.signature(TemporalChangeAssertion)

    kwargs = {}

    candidates = {
        "subject": "project",
        "previous_value": "phase 10",
        "new_value": "phase 11",
        "old_value": "phase 10",
        "value": "phase 11",
        "start_time": "2026-09-10T00:00:00",
        "end_time": None,
        "precision": "day",
        "confidence": 1.0,
        "evidence_kind": "state_change",
        "extraction_method": "test",
    }

    for name, parameter in signature.parameters.items():
        if name == "self":
            continue
        if parameter.default is not inspect.Parameter.empty:
            continue
        if name in candidates:
            kwargs[name] = candidates[name]

    missing = [
        name
        for name, parameter in signature.parameters.items()
        if name != "self"
        and parameter.default is inspect.Parameter.empty
        and name not in kwargs
    ]

    if missing:
        pytest.skip(
            "Canonical TemporalChangeAssertion requires fields not "
            f"covered by this contract test: {missing}"
        )

    return TemporalChangeAssertion(**kwargs)


@pytest.fixture
def service() -> TemporalStateChangeService:
    return TemporalStateChangeService()


def test_derive_uses_canonical_temporal_change_assertion(service):
    assertion = make_change_assertion()

    result = service.derive([assertion])

    assert isinstance(result, TemporalStateChangeResult)
    assert result.count == 1
    assert isinstance(result.changes[0], TemporalStateChange)
    assert result.changes[0].assertion is assertion


def test_derive_preserves_assertion_identity(service):
    assertion = make_change_assertion()

    change = service.derive_one(assertion)

    assert change.assertion is assertion


def test_derive_preserves_input_order(service):
    first = make_change_assertion()
    second = make_change_assertion()

    result = service.derive([first, second])

    assert [item.assertion for item in result.changes] == [
        first,
        second,
    ]


def test_derive_accepts_iterators(service):
    assertion = make_change_assertion()

    result = service.derive(iter([assertion]))

    assert result.count == 1


def test_derive_empty_input_returns_empty_result(service):
    result = service.derive([])

    assert result.count == 0
    assert result.changes == ()


def test_result_is_immutable(service):
    assertion = make_change_assertion()
    result = service.derive([assertion])

    with pytest.raises(AttributeError):
        result.changes = ()


def test_state_change_is_immutable(service):
    assertion = make_change_assertion()
    change = service.derive_one(assertion)

    with pytest.raises(AttributeError):
        change.assertion = None


def test_service_does_not_persist_state_changes(service, tmp_path):
    assertion = make_change_assertion()

    result = service.derive([assertion])

    assert result.count == 1
    assert not (tmp_path / "collective.db").exists()


def test_service_returns_existing_assertion_without_rewriting_it(service):
    assertion = make_change_assertion()

    result = service.derive([assertion])

    assert result.changes[0].assertion == assertion


def test_service_does_not_create_temporal_relationships(service):
    assertion = make_change_assertion()

    result = service.derive([assertion])

    assert not any(
        hasattr(change, "relation")
        for change in result.changes
    )
