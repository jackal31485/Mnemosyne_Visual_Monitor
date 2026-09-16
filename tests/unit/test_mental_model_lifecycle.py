"""Phase 13E lifecycle tests."""

from datetime import datetime, timezone

import pytest

from src.domain.mental_model import (
    MentalModel,
    MentalModelProvenance,
    MentalModelStatus,
    MentalModelType,
)
from src.domain.mental_model_lifecycle import (
    DependencyRevocation,
    MentalModelDependencySnapshot,
    MentalModelLifecycle,
    MentalModelLifecycleError,
)


def make_model(
    *,
    status: MentalModelStatus = MentalModelStatus.ACTIVE,
    version: int = 1,
) -> MentalModel:
    provenance = MentalModelProvenance(
        derivation_method="phase-13-test",
        observation_ids=("obs-1", "obs-2"),
        evidence_ids=("ev-1", "ev-2"),
        memory_ids=("mem-1", "mem-2"),
        source_profiles=("profile-a",),
        entity_ids=("entity-1",),
        relationship_ids=("rel-1",),
    )

    return MentalModel(
        model_id="mm-test",
        model_type=MentalModelType.CONCEPT,
        title="Test model",
        description="Governed test mental model",
        entity_ids=("entity-1",),
        relationship_ids=("rel-1",),
        supporting_observation_ids=("obs-1", "obs-2"),
        supporting_evidence_ids=("ev-1", "ev-2"),
        supporting_memory_ids=("mem-1", "mem-2"),
        source_profiles=("profile-a",),
        temporal_scope=("ongoing",),
        confidence=0.8,
        status=status,
        version=version,
        created_at=datetime(2026, 9, 16, tzinfo=timezone.utc),
        updated_at=datetime(2026, 9, 16, tzinfo=timezone.utc),
        provenance=provenance,
        derivation_method="phase-13-test",
        contradictory_evidence_ids=(),
        staleness_state="current",
    )


def snapshot(model: MentalModel) -> MentalModelDependencySnapshot:
    return MentalModelDependencySnapshot.from_model(model)


def test_dependency_snapshot_matches_model():
    model = make_model()

    result = snapshot(model)

    assert result.observation_ids == ("obs-1", "obs-2")
    assert result.evidence_ids == ("ev-1", "ev-2")
    assert result.memory_ids == ("mem-1", "mem-2")
    assert result.relationship_ids == ("rel-1",)
    assert result.source_profiles == ("profile-a",)


def test_unchanged_dependencies_are_current():
    model = make_model()

    result = MentalModelLifecycle.evaluate_staleness(
        model,
        snapshot(model),
    )

    assert result.stale is False
    assert result.is_current
    assert result.reasons == ()
    assert result.dependency_changes == {}


def test_removed_dependency_marks_model_stale():
    model = make_model()

    current = MentalModelDependencySnapshot(
        observation_ids=("obs-1",),
        evidence_ids=("ev-1", "ev-2"),
        memory_ids=("mem-1", "mem-2"),
        relationship_ids=("rel-1",),
        source_profiles=("profile-a",),
    )

    result = MentalModelLifecycle.evaluate_staleness(
        model,
        current,
    )

    assert result.stale is True
    assert "dependency_changed" in result.reasons
    assert result.dependency_changes["observation_ids_removed"] == ("obs-2",)


def test_added_dependency_is_detected():
    model = make_model()

    current = MentalModelDependencySnapshot(
        observation_ids=("obs-1", "obs-2", "obs-3"),
        evidence_ids=("ev-1", "ev-2", "ev-3"),
        memory_ids=("mem-1", "mem-2", "mem-3"),
        relationship_ids=("rel-1", "rel-2"),
        source_profiles=("profile-a",),
    )

    result = MentalModelLifecycle.evaluate_staleness(
        model,
        current,
    )

    assert result.stale is True
    assert result.dependency_changes["observation_ids_added"] == ("obs-3",)
    assert result.dependency_changes["evidence_ids_added"] == ("ev-3",)


def test_revoked_dependency_marks_model_stale():
    model = make_model()

    revocation = DependencyRevocation(
        dependency_type="evidence",
        dependency_id="ev-1",
        reason="source evidence revoked",
    )

    result = MentalModelLifecycle.evaluate_staleness(
        model,
        snapshot(model),
        revoked_dependencies=(revocation,),
    )

    assert result.stale is True
    assert "dependency_revoked" in result.reasons
    assert result.revoked_dependencies == (revocation,)


def test_revocation_propagates_to_model():
    model = make_model()

    revocation = DependencyRevocation(
        dependency_type="evidence",
        dependency_id="ev-1",
        reason="revoked",
    )

    revoked = MentalModelLifecycle.propagate_revocation(
        model,
        (revocation,),
    )

    assert revoked.status is MentalModelStatus.REVOKED
    assert revoked.staleness_state == "revoked"
    assert revoked.version == model.version
    assert revoked.model_id == model.model_id

    # Source dependency identifiers remain intact for auditability.
    assert revoked.supporting_evidence_ids == model.supporting_evidence_ids
    assert revoked.supporting_memory_ids == model.supporting_memory_ids


def test_revocation_does_not_mutate_original_model():
    model = make_model()

    revocation = DependencyRevocation(
        dependency_type="memory",
        dependency_id="mem-1",
        reason="source revoked",
    )

    revoked = MentalModelLifecycle.propagate_revocation(
        model,
        (revocation,),
    )

    assert model.status is MentalModelStatus.ACTIVE
    assert model.staleness_state == "current"
    assert revoked is not model


def test_refresh_creates_next_version():
    model = make_model()

    current = MentalModelDependencySnapshot(
        observation_ids=("obs-1", "obs-2", "obs-3"),
        evidence_ids=("ev-1", "ev-2", "ev-3"),
        memory_ids=("mem-1", "mem-2", "mem-3"),
        relationship_ids=("rel-1",),
        source_profiles=("profile-a",),
    )

    refreshed_at = datetime(
        2026,
        9,
        16,
        18,
        0,
        tzinfo=timezone.utc,
    )

    result = MentalModelLifecycle.refresh(
        model,
        current,
        refreshed_at=refreshed_at,
    )

    assert result.previous_model.status is MentalModelStatus.SUPERSEDED
    assert result.previous_model.version == 1

    assert result.refreshed_model.version == 2
    assert result.refreshed_model.status is MentalModelStatus.ACTIVE
    assert result.refreshed_model.staleness_state == "current"
    assert result.refreshed_model.updated_at == refreshed_at

    assert result.refreshed_model.supporting_observation_ids == (
        "obs-1",
        "obs-2",
        "obs-3",
    )
    assert result.refreshed_model.supporting_evidence_ids == (
        "ev-1",
        "ev-2",
        "ev-3",
    )


def test_refresh_does_not_mutate_original_model():
    model = make_model()

    current = MentalModelDependencySnapshot(
        observation_ids=("obs-1", "obs-2", "obs-3"),
        evidence_ids=("ev-1", "ev-2", "ev-3"),
        memory_ids=("mem-1", "mem-2", "mem-3"),
        relationship_ids=("rel-1",),
        source_profiles=("profile-a",),
    )

    MentalModelLifecycle.refresh(
        model,
        current,
        refreshed_at=datetime(
            2026,
            9,
            16,
            18,
            0,
            tzinfo=timezone.utc,
        ),
    )

    assert model.version == 1
    assert model.status is MentalModelStatus.ACTIVE
    assert model.supporting_evidence_ids == ("ev-1", "ev-2")


def test_refresh_requires_dependency_change():
    model = make_model()

    with pytest.raises(MentalModelLifecycleError, match="stale"):
        MentalModelLifecycle.refresh(
            model,
            snapshot(model),
            refreshed_at=datetime(
                2026,
                9,
                16,
                18,
                0,
                tzinfo=timezone.utc,
            ),
        )


def test_revoked_dependency_cannot_be_refreshed():
    model = make_model()

    revocation = DependencyRevocation(
        dependency_type="evidence",
        dependency_id="ev-1",
        reason="revoked",
    )

    current = MentalModelDependencySnapshot(
        observation_ids=("obs-1", "obs-2", "obs-3"),
        evidence_ids=("ev-1", "ev-2", "ev-3"),
        memory_ids=("mem-1", "mem-2", "mem-3"),
        relationship_ids=("rel-1",),
        source_profiles=("profile-a",),
    )

    with pytest.raises(
        MentalModelLifecycleError,
        match="revoked dependencies",
    ):
        MentalModelLifecycle.refresh(
            model,
            current,
            refreshed_at=datetime(
                2026,
                9,
                16,
                18,
                0,
                tzinfo=timezone.utc,
            ),
            revoked_dependencies=(revocation,),
        )


def test_terminal_revoked_model_is_not_changed_by_repeated_revocation():
    model = make_model(status=MentalModelStatus.REVOKED)

    revocation = DependencyRevocation(
        dependency_type="evidence",
        dependency_id="ev-1",
        reason="already revoked",
    )

    result = MentalModelLifecycle.propagate_revocation(
        model,
        (revocation,),
    )

    assert result is model
    assert result.status is MentalModelStatus.REVOKED


def test_terminal_superseded_model_is_not_changed_by_revocation():
    model = make_model(status=MentalModelStatus.SUPERSEDED)

    revocation = DependencyRevocation(
        dependency_type="evidence",
        dependency_id="ev-1",
        reason="later revocation",
    )

    result = MentalModelLifecycle.propagate_revocation(
        model,
        (revocation,),
    )

    assert result is model
    assert result.status is MentalModelStatus.SUPERSEDED


def test_dependency_snapshot_rejects_duplicate_identifiers():
    with pytest.raises(ValueError, match="must not contain duplicates"):
        MentalModelDependencySnapshot(
            observation_ids=("obs-1", "obs-1"),
            evidence_ids=("ev-1",),
            memory_ids=("mem-1",),
            relationship_ids=(),
            source_profiles=("profile-a",),
        )


def test_cross_profile_dependency_change_is_visible():
    model = make_model()

    current = MentalModelDependencySnapshot(
        observation_ids=("obs-1", "obs-2"),
        evidence_ids=("ev-1", "ev-2"),
        memory_ids=("mem-1", "mem-2"),
        relationship_ids=("rel-1",),
        source_profiles=("profile-b",),
    )

    result = MentalModelLifecycle.evaluate_staleness(
        model,
        current,
    )

    assert result.stale is True
    assert result.dependency_changes["source_profiles_removed"] == (
        "profile-a",
    )
    assert result.dependency_changes["source_profiles_added"] == (
        "profile-b",
    )
