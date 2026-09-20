from types import SimpleNamespace

import pytest

from src.retrieval.retrieval_evaluation import (
    evaluate_retrieval,
    mean_reciprocal_rank,
    precision_at_k,
    recall_at_k,
)


def test_precision_at_k_counts_relevant_results():
    assert precision_at_k(
        [1, 2, 3, 4],
        [2, 4],
        4,
    ) == 0.5


def test_precision_at_k_respects_k():
    assert precision_at_k(
        [1, 2, 3, 4],
        [2, 4],
        2,
    ) == 0.5


def test_recall_at_k_counts_relevant_results():
    assert recall_at_k(
        [1, 2, 3, 4],
        [2, 4],
        4,
    ) == 1.0


def test_recall_at_k_respects_k():
    assert recall_at_k(
        [1, 2, 3, 4],
        [2, 4],
        2,
    ) == 0.5


def test_mean_reciprocal_rank_uses_first_relevant_result():
    assert mean_reciprocal_rank(
        [7, 8, 3, 2],
        [2, 3],
    ) == pytest.approx(1 / 3)


def test_mean_reciprocal_rank_is_zero_without_relevant_result():
    assert mean_reciprocal_rank(
        [7, 8, 9],
        [2, 3],
    ) == 0.0


def test_empty_relevant_set_is_zero():
    assert precision_at_k([1, 2], [], 2) == 0.0
    assert recall_at_k([1, 2], [], 2) == 0.0
    assert mean_reciprocal_rank([1, 2], []) == 0.0


def test_evaluate_retrieval_consumes_ranked_entry_ids_only():
    results = [
        SimpleNamespace(
            entry_id=7,
            source_profile="Athena",
            origin_memory_id="private-7",
            provenance=(("Athena", "private-7", "2026-09-07"),),
        ),
        SimpleNamespace(
            entry_id=3,
            source_profile="Horus",
            origin_memory_id="private-3",
            provenance=(("Horus", "private-3", "2026-09-08"),),
        ),
        SimpleNamespace(
            entry_id=9,
            source_profile="Odin",
            origin_memory_id="private-9",
            provenance=(("Odin", "private-9", "2026-09-09"),),
        ),
    ]

    evaluation = evaluate_retrieval(
        results,
        [3, 9],
        k=2,
    )

    assert evaluation.retrieved_entry_ids == (7, 3, 9)
    assert evaluation.relevant_entry_ids == (3, 9)
    assert evaluation.evaluated_k == 2
    assert evaluation.precision_at_k == 0.5
    assert evaluation.recall_at_k == 0.5
    assert evaluation.mean_reciprocal_rank == pytest.approx(0.5)

    assert results[0].provenance == (
        ("Athena", "private-7", "2026-09-07"),
    )


@pytest.mark.parametrize(
    "function,args",
    [
        (precision_at_k, ([1], [1], 0)),
        (recall_at_k, ([1], [1], 0)),
    ],
)
def test_metrics_reject_non_positive_k(function, args):
    with pytest.raises(ValueError, match="k"):
        function(*args)


def test_evaluate_retrieval_rejects_duplicate_relevant_ids():
    with pytest.raises(ValueError, match="duplicates"):
        evaluate_retrieval(
            [SimpleNamespace(entry_id=1)],
            [1, 1],
            k=1,
        )


def test_evaluate_retrieval_preserves_order():
    results = [
        SimpleNamespace(entry_id=4),
        SimpleNamespace(entry_id=2),
        SimpleNamespace(entry_id=8),
    ]

    evaluation = evaluate_retrieval(
        results,
        [8],
        k=2,
    )

    assert evaluation.retrieved_entry_ids == (4, 2, 8)
    assert evaluation.evaluated_k == 2
    assert evaluation.recall_at_k == 0.0
    assert evaluation.mean_reciprocal_rank == pytest.approx(1 / 3)


def test_multilingual_lexical_fallback_case_is_evaluable():
    results = [
        SimpleNamespace(entry_id=21),
        SimpleNamespace(entry_id=42),
    ]

    evaluation = evaluate_retrieval(
        results,
        [42],
        k=2,
    )

    assert evaluation.precision_at_k == 0.5
    assert evaluation.recall_at_k == 1.0
    assert evaluation.mean_reciprocal_rank == pytest.approx(0.5)


def test_latin_script_non_english_case_has_no_special_semantic_claim():
    results = [
        SimpleNamespace(entry_id=5),
        SimpleNamespace(entry_id=6),
    ]

    evaluation = evaluate_retrieval(
        results,
        [6],
        k=1,
    )

    assert evaluation.evaluated_k == 1
    assert evaluation.precision_at_k == 0.0
    assert evaluation.recall_at_k == 0.0
