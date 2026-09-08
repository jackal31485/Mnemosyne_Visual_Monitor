from __future__ import annotations

import numpy as np
import pytest

from src.retrieval.cross_encoder import LocalCrossEncoder


class FakeModel:
    def __init__(self, scores):
        self.scores = scores
        self.calls = []

    def predict(self, pairs, **kwargs):
        self.calls.append((list(pairs), kwargs))
        return np.asarray(self.scores)


def make_encoder(tmp_path, monkeypatch, scores):
    model_dir = tmp_path / "cross-encoder"
    model_dir.mkdir()

    import sentence_transformers

    fake_model = FakeModel(scores)

    monkeypatch.setattr(
        sentence_transformers,
        "CrossEncoder",
        lambda *args, **kwargs: fake_model,
    )

    encoder = LocalCrossEncoder(
        model_dir,
        device="cpu",
        batch_size=8,
    )

    return encoder, fake_model


def test_loads_model_local_only(tmp_path, monkeypatch) -> None:
    encoder, fake_model = make_encoder(
        tmp_path,
        monkeypatch,
        [1.0],
    )

    assert encoder.device == "cpu"
    assert encoder.batch_size == 8
    assert encoder.model is fake_model


def test_predict_returns_float_scores(tmp_path, monkeypatch) -> None:
    encoder, _ = make_encoder(
        tmp_path,
        monkeypatch,
        [2.5, -0.75],
    )

    scores = encoder.predict(
        [
            ("query one", "document one"),
            ("query two", "document two"),
        ]
    )

    assert scores == pytest.approx([2.5, -0.75])
    assert all(isinstance(score, float) for score in scores)


def test_predict_passes_batch_configuration(tmp_path, monkeypatch) -> None:
    encoder, fake_model = make_encoder(
        tmp_path,
        monkeypatch,
        [1.0],
    )

    pairs = [("query", "document")]

    encoder.predict(pairs)

    received_pairs, kwargs = fake_model.calls[0]

    assert received_pairs == pairs
    assert kwargs["batch_size"] == 8
    assert kwargs["show_progress_bar"] is False
    assert kwargs["convert_to_numpy"] is True


def test_empty_pairs_return_empty_list(tmp_path, monkeypatch) -> None:
    encoder, fake_model = make_encoder(
        tmp_path,
        monkeypatch,
        [],
    )

    assert encoder.predict([]) == []
    assert fake_model.calls == []


def test_invalid_model_directory_is_rejected(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        LocalCrossEncoder(tmp_path / "missing")


@pytest.mark.parametrize(
    "batch_size",
    [0, -1, True, False],
)
def test_invalid_batch_size_is_rejected(tmp_path, batch_size) -> None:
    model_dir = tmp_path / "cross-encoder"
    model_dir.mkdir()

    with pytest.raises(ValueError):
        LocalCrossEncoder(
            model_dir,
            batch_size=batch_size,
        )


@pytest.mark.parametrize(
    "pairs",
    [
        [("query", "")],
        [("", "document")],
        [(" ", "document")],
        [("query", " ")],
        [("query",)],
        ["not-a-pair"],
    ],
)
def test_invalid_pairs_are_rejected(
    tmp_path,
    monkeypatch,
    pairs,
) -> None:
    encoder, fake_model = make_encoder(
        tmp_path,
        monkeypatch,
        [1.0],
    )

    with pytest.raises(ValueError):
        encoder.predict(pairs)

    assert fake_model.calls == []


def test_score_count_must_match_pairs(tmp_path, monkeypatch) -> None:
    encoder, _ = make_encoder(
        tmp_path,
        monkeypatch,
        [1.0],
    )

    with pytest.raises(ValueError, match="different number"):
        encoder.predict(
            [
                ("query one", "document one"),
                ("query two", "document two"),
            ]
        )


def test_non_finite_scores_are_rejected(tmp_path, monkeypatch) -> None:
    encoder, _ = make_encoder(
        tmp_path,
        monkeypatch,
        [float("nan")],
    )

    with pytest.raises(ValueError, match="non-finite"):
        encoder.predict(
            [("query", "document")]
        )
