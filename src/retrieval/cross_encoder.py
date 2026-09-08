"""Local CrossEncoder adapter for Phase 8F reranking."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import numpy as np

from src.retrieval.reranker import CrossEncoderProtocol


class LocalCrossEncoder(CrossEncoderProtocol):
    """Offline-capable sentence-transformers CrossEncoder adapter."""

    def __init__(
        self,
        model_path: str | Path = "models/cross-encoder-ms-marco-MiniLM-L6-v2",
        *,
        device: str = "cpu",
        batch_size: int = 32,
    ) -> None:
        if not isinstance(batch_size, int) or isinstance(batch_size, bool):
            raise ValueError("batch_size must be a positive integer")

        if batch_size < 1:
            raise ValueError("batch_size must be a positive integer")

        self.model_path = Path(model_path)
        self.device = device
        self.batch_size = batch_size

        if not self.model_path.is_dir():
            raise FileNotFoundError(
                f"CrossEncoder model directory does not exist: "
                f"{self.model_path}"
            )

        from sentence_transformers import CrossEncoder

        self.model = CrossEncoder(
            str(self.model_path),
            device=device,
            local_files_only=True,
            backend="torch",
        )

    def predict(
        self,
        pairs: Sequence[tuple[str, str]],
    ) -> list[float]:
        """Score query/document pairs using the local CrossEncoder."""

        if not pairs:
            return []

        for pair in pairs:
            if (
                not isinstance(pair, tuple)
                or len(pair) != 2
                or not isinstance(pair[0], str)
                or not isinstance(pair[1], str)
                or not pair[0].strip()
                or not pair[1].strip()
            ):
                raise ValueError(
                    "each CrossEncoder pair must contain two non-empty strings"
                )

        scores = self.model.predict(
            list(pairs),
            batch_size=self.batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
        )

        values = np.asarray(scores, dtype=np.float32).reshape(-1)

        if len(values) != len(pairs):
            raise ValueError(
                "CrossEncoder returned a different number of scores "
                "than input pairs"
            )

        if not np.all(np.isfinite(values)):
            raise ValueError("CrossEncoder returned non-finite scores")

        return [float(value) for value in values]
