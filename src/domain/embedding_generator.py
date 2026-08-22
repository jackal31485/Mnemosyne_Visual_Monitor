from __future__ import annotations

from typing import Protocol

import numpy as np
from sentence_transformers import SentenceTransformer


DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"
DEFAULT_DIMENSIONS = 384


class EmbeddingGenerator(Protocol):
    """Generate an embedding from an approved sanitized string only."""

    def generate(self, sanitized: str) -> bytes:
        ...


class SentenceTransformerEncoder:
    """Local semantic embedding generator.

    Only approved sanitized text may be supplied to this encoder.
    The underlying Mnemosyne memory object and private-memory fields are
    deliberately not accepted by this API.

    Embeddings are stored as raw little-endian float32 bytes.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        *,
        device: str | None = None,
    ) -> None:
        self.model_name = model_name
        self.device = device
        self._model: SentenceTransformer | None = None

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            if self.device is None:
                self._model = SentenceTransformer(self.model_name)
            else:
                self._model = SentenceTransformer(
                    self.model_name,
                    device=self.device,
                )

            self._model.eval()

        return self._model

    def generate(self, sanitized: str) -> bytes:
        if not isinstance(sanitized, str):
            raise TypeError("sanitized must be a string")

        if not sanitized.strip():
            raise ValueError("sanitized must not be empty")

        vector = self.model.encode(
            sanitized,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        vector = np.asarray(vector, dtype=np.float32)

        if vector.ndim != 1:
            raise ValueError("embedding must be one-dimensional")

        if vector.shape[0] != DEFAULT_DIMENSIONS:
            raise ValueError(
                f"expected {DEFAULT_DIMENSIONS}-dimensional embedding, "
                f"got {vector.shape[0]}"
            )

        if not np.all(np.isfinite(vector)):
            raise ValueError("embedding contains non-finite values")

        return vector.tobytes()


def embed_sanitized(sanitized: str) -> bytes:
    """Generate a deterministic semantic embedding from sanitized text."""
    return SentenceTransformerEncoder().generate(sanitized)


def decode_embedding(blob: bytes) -> np.ndarray:
    """Decode a stored float32 embedding BLOB."""

    if not isinstance(blob, (bytes, bytearray, memoryview)):
        raise TypeError("embedding blob must be bytes-like")

    vector = np.frombuffer(blob, dtype=np.float32)

    if vector.ndim != 1:
        raise ValueError("embedding must be one-dimensional")

    if vector.shape[0] != DEFAULT_DIMENSIONS:
        raise ValueError(
            f"expected {DEFAULT_DIMENSIONS}-dimensional embedding, "
            f"got {vector.shape[0]}"
        )

    if not np.all(np.isfinite(vector)):
        raise ValueError("embedding contains non-finite values")

    return vector.copy()
