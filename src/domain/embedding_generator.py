"""
Semantic embedding generation for Mnemosyne.

Embeddings use the locally cached ``all-MiniLM-L6-v2`` SentenceTransformer
model. The model is loaded in CPU mode and local-files-only mode so embedding
generation never depends on Hugging Face network availability at runtime.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

import numpy as np

DEFAULT_DIMENSIONS = 384
DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"

# The embedding model is deliberately stored inside the project so normal
# embedding generation never depends on the Hugging Face cache or network.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_PATH = PROJECT_ROOT / "models" / DEFAULT_MODEL_NAME


class EmbeddingGenerator(Protocol):
    """Generate a serialized embedding from approved text."""

    def generate(self, sanitized: str) -> bytes:
        ...


class SentenceTransformerEncoder:
    """Generate normalized semantic embeddings using MiniLM.

    The model must already exist in the project's local ``models/``
    directory. Network access is deliberately disabled so runtime behavior is
    deterministic and suitable for the project's local/offline architecture.
    """

    def __init__(self, *, device: str = "cpu") -> None:
        self.device = device

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise ImportError(
                "sentence-transformers is required for semantic embeddings"
            ) from exc

        if not DEFAULT_MODEL_PATH.is_dir():
            raise RuntimeError(
                f"Local embedding model not found: {DEFAULT_MODEL_PATH}. "
                "Run the model setup procedure before generating embeddings."
            )

        try:
            self.model = SentenceTransformer(
                str(DEFAULT_MODEL_PATH),
                device=device,
                local_files_only=True,
            )
        except Exception as exc:
            raise RuntimeError(
                f"Unable to load local embedding model "
                f"{DEFAULT_MODEL_NAME!r} from {DEFAULT_MODEL_PATH}. "
                "The local model may be incomplete or corrupted."
            ) from exc

    def generate(self, sanitized: str) -> bytes:
        """Generate a normalized 384-dimensional float32 embedding."""

        if not isinstance(sanitized, str):
            raise TypeError("sanitized must be a string")

        if not sanitized.strip():
            raise ValueError("sanitized must not be empty")

        vec = np.asarray(
            self.model.encode(
                sanitized,
                convert_to_numpy=True,
                normalize_embeddings=True,
            ),
            dtype=np.float32,
        )

        if vec.ndim != 1:
            raise ValueError("embedding must be one-dimensional")

        if vec.shape[0] != DEFAULT_DIMENSIONS:
            raise ValueError(
                f"expected {DEFAULT_DIMENSIONS}-dimensional embedding, "
                f"got {vec.shape[0]}"
            )

        # Enforce normalization even if the model implementation changes.
        norm = float(np.linalg.norm(vec))
        if norm == 0.0:
            raise ValueError("embedding has zero norm")

        vec = (vec / norm).astype(np.float32)

        return vec.tobytes()


def embed_sanitized(sanitized: str) -> bytes:
    """Compatibility helper used by the embedding/backfill code."""

    return SentenceTransformerEncoder().generate(sanitized)


def decode_embedding(
    blob: bytes | bytearray | memoryview,
) -> np.ndarray:
    """Decode a stored float32 embedding and validate its dimensions."""

    if not isinstance(blob, (bytes, bytearray, memoryview)):
        raise TypeError("embedding blob must be bytes-like")

    vec = np.frombuffer(blob, dtype=np.float32)

    if vec.ndim != 1 or vec.shape[0] != DEFAULT_DIMENSIONS:
        raise ValueError("invalid embedding dimensions")

    return vec.copy()
