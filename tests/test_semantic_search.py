import math

import numpy as np
import pytest

from src.domain.collective import CollectiveDAO
from src.domain.athena_api import AthenaAPI
from src.domain.athena_interface import AthenaCollectiveInterface
from src.domain.embedding_generator import DEFAULT_DIMENSIONS
from src.retrieval.semantic_search import SemanticSearcher


def blob(values):
    return np.asarray(values, dtype=np.float32).tobytes()


@pytest.fixture
def setup(tmp_path):
    db = CollectiveDAO(tmp_path / "collective.db")
    db.ensure_schema()

    def add(profile, memory, vector, promoted=True, revoked=False, provenance=True):
        entry_id = db.add_entry(profile, memory)
        if promoted:
            db.update_entry_promoted(entry_id)
        if revoked:
            db.update_entry_revoked(entry_id, "test revocation")

        if vector is not None:
            db.update_entry_embedding(entry_id, blob(vector))

        if provenance:
            db.add_provenance(entry_id, profile, memory)

        return entry_id

    return db, add


def unit_vector(index):
    vector = np.zeros(DEFAULT_DIMENSIONS, dtype=np.float32)
    vector[index] = 1.0
    return vector


def test_returns_rich_scored_results(setup):
    db, add = setup

    query = unit_vector(0)
    first = add("athena", "memory-a", query)
    second_vector = unit_vector(1)
    second = add("athena", "memory-b", second_vector)

    results = SemanticSearcher(db).search(query, top_k=10)

    assert [r.entry_id for r in results] == [first, second]
    assert results[0].semantic_score == pytest.approx(1.0)
    assert results[0].source_profile == "athena"
    assert results[0].origin_memory_id == "memory-a"
    assert results[0].provenance == (
        ("athena", "memory-a", results[0].provenance[0][2]),
    )


def test_results_are_deterministic_for_equal_scores(setup):
    db, add = setup

    query = unit_vector(0)
    first = add("athena", "memory-a", query)
    second = add("athena", "memory-b", query)

    results = SemanticSearcher(db).search(query, top_k=10)

    assert [r.entry_id for r in results] == [first, second]


def test_unpromoted_and_revoked_are_excluded(setup):
    db, add = setup

    query = unit_vector(0)
    promoted = add("athena", "promoted", query)
    add("athena", "unpromoted", query, promoted=False)
    add("athena", "revoked", query, revoked=True)

    results = SemanticSearcher(db).search(query, top_k=10)

    assert [r.entry_id for r in results] == [promoted]


def test_invalid_stored_embeddings_are_skipped(setup):
    db, add = setup

    query = unit_vector(0)
    valid = add("athena", "valid", query)

    null_id = add("athena", "null", None)
    malformed_id = db.add_entry("athena", "malformed")
    db.update_entry_promoted(malformed_id)
    db.update_entry_embedding(malformed_id, b"bad")

    wrong_dim = db.add_entry("athena", "wrong-dimension")
    db.update_entry_promoted(wrong_dim)
    db.update_entry_embedding(wrong_dim, blob([1.0, 2.0]))

    nan_id = db.add_entry("athena", "nan")
    db.update_entry_promoted(nan_id)
    db.update_entry_embedding(
        nan_id,
        blob(np.full(DEFAULT_DIMENSIONS, np.nan)),
    )

    zero_id = db.add_entry("athena", "zero")
    db.update_entry_promoted(zero_id)
    db.update_entry_embedding(
        zero_id,
        blob(np.zeros(DEFAULT_DIMENSIONS)),
    )

    results = SemanticSearcher(db).search(query, top_k=10)

    assert [r.entry_id for r in results] == [valid]


def test_query_dimension_is_validated(setup):
    db, add = setup
    add("athena", "memory", unit_vector(0))

    with pytest.raises(ValueError, match="exactly"):
        SemanticSearcher(db).search([1.0, 2.0], top_k=10)


def test_query_nonfinite_is_rejected(setup):
    db, add = setup
    add("athena", "memory", unit_vector(0))

    query = unit_vector(0)
    query[1] = np.nan

    with pytest.raises(ValueError, match="finite"):
        SemanticSearcher(db).search(query, top_k=10)


def test_zero_query_is_rejected(setup):
    db, add = setup
    add("athena", "memory", unit_vector(0))

    with pytest.raises(ValueError, match="non-zero"):
        SemanticSearcher(db).search(
            np.zeros(DEFAULT_DIMENSIONS),
            top_k=10,
        )


def test_profile_filter(setup):
    db, add = setup

    query = unit_vector(0)
    athena = add("athena", "athena-memory", query)
    horus = add("horus", "horus-memory", query)

    results = SemanticSearcher(db).search(
        query,
        top_k=10,
        profile="horus",
    )

    assert [r.entry_id for r in results] == [horus]
    assert athena not in [r.entry_id for r in results]


def test_top_k_is_validated(setup):
    db, add = setup
    add("athena", "memory", unit_vector(0))

    with pytest.raises(ValueError):
        SemanticSearcher(db).search(unit_vector(0), top_k=0)

    with pytest.raises(ValueError):
        SemanticSearcher(db).search(unit_vector(0), top_k=True)


def test_athena_compatibility_wrapper(setup):
    db, add = setup

    query = unit_vector(0)
    first = add("athena", "memory-a", query)
    second = add("athena", "memory-b", unit_vector(1))

    interface = AthenaCollectiveInterface()
    interface._dao.close()

    api = AthenaAPI.__new__(AthenaAPI)
    api._iface = interface
    interface._dao = db

    assert api.search_by_embedding(query, 2) == [first, second]


def test_legacy_zero_vector_compatibility(setup):
    db, add = setup

    zero = np.zeros(DEFAULT_DIMENSIONS)
    first = add("athena", "zero", zero)
    second = add("athena", "normal", unit_vector(0))

    api = AthenaAPI.__new__(AthenaAPI)
    interface = AthenaCollectiveInterface()
    interface._dao.close()
    interface._dao = db
    api._iface = interface

    assert api.search_by_embedding(zero, 2) == [first, second]
