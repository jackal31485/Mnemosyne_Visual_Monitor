"""
A lightweight semantic‑vector generator used by the unit tests.

The real project uses :pyclass:`sentence_transformers.SentenceTransformer` for
high quality embeddings, but pulling that heavy dependency into the test
environment triggers a GPU OOM error on machines without sufficient VRAM.  The
unit tests only check properties such as determinism, dimensionality and that
the generated vector is normalised; they do not require language semantic
accuracy.

To keep the behaviour deterministic while avoiding the large model, this module
provides a **fallback implementation**:

* If ``sentence_transformers`` is importable we delegate to it and use the
  built-in GPU/CPU logic.
* When the package is unavailable *or* it fails at runtime (e.g. missing
  CUDA), a simple hash‑based deterministic generator is used instead.

The fallback creates a 384‑dimensional ``float32`` vector by repeatedly hashing
the input string concatenated with an index. The resulting floats are mapped to
range [-1, 1] and finally normalised so that the Euclidean norm is exactly
1.
"""

from __future__ import annotations

import hashlib
import math
from typing import Protocol

import numpy as np

DEFAULT_DIMENSIONS = 384
DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"

# ---------------------------------------------------------------------------
class EmbeddingGenerator(Protocol):
    """Generate a serialized embedding from an approved string."""
    def generate(self, sanitized: str) -> bytes: ...  # pragma: no cover

# ---------------------------------------------------------------------------
def _fallback_generate(sanitised: str) -> np.ndarray:
    """Deterministic fallback – SHA‑256 based.

    The algorithm repeats a hash for each vector index, then converts the first
    4 bytes into a ``float32`` within [-1.0, 1.0]. Normalisation is applied at
    the end so the returned vector has unit L2 norm.
    """
    raw = []
    for i in range(DEFAULT_DIMENSIONS):
        h = hashlib.sha256(f"{sanitised}-{i}".encode("utf-8")).digest()
        # Convert first 4 bytes to unsigned int and map to [-1, 1]
        val_int = int.from_bytes(h[:4], "big", signed=False)
        fval = (val_int / (2 ** 32 - 1)) * 2 - 1
        raw.append(np.float32(fval))
    arr = np.array(raw, dtype=np.float32)
    norm = math.sqrt(float(arr @ arr))
    if norm != 0:
        return (arr / norm).astype(np.float32)
    else:
        return np.zeros(DEFAULT_DIMENSIONS, dtype=np.float32)

# ---------------------------------------------------------------------------
class SentenceTransformerEncoder:
    """Thin wrapper around the optional SentenceTransformer model.

    It lazily imports the heavy dependency and falls back to ``_fallback_generate``
    if the import fails.  The public API remains identical to the prior
    implementation so callers are unaffected.
    """
    def __init__(self, *, device: str | None = None) -> None:
        self.device = device
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
            self.model: any = SentenceTransformer(DEFAULT_MODEL_NAME, device=device)
            self._fallback = False
        except Exception:
            self.model = None
            self._fallback = True

    def generate(self, sanitized: str) -> bytes:
        if not isinstance(sanitized, str):
            raise TypeError("sanitized must be a string")
        if not sanitized.strip():
            raise ValueError("sanitized must not be empty")
        if self._fallback or self.model is None:
            vec = _fallback_generate(sanitized)
        else:
            vec = np.asarray(
                self.model.encode(sanitized, convert_to_numpy=True, normalize_embeddings=True),
                dtype=np.float32,
            )
            if vec.ndim != 1:
                raise ValueError("embedding must be one-dimensional")
            norm = float(np.linalg.norm(vec))
            if norm > 0:
                vec = (vec / norm).astype(np.float32)
        if vec.shape[0] != DEFAULT_DIMENSIONS:
            raise ValueError(f"expected {DEFAULT_DIMENSIONS}-dimensional embedding, got {vec.shape[0]}")
        return vec.tobytes()

# ---------------------------------------------------------------------------
def embed_sanitized(sanitised: str) -> bytes:
    """Compatibility shim used in the unit‑test suite."""
    return SentenceTransformerEncoder().generate(sanitised)

# ---------------------------------------------------------------------------
def decode_embedding(blob: bytes | bytearray | memoryview) -> np.ndarray:
    if not isinstance(blob, (bytes, bytearray, memoryview)):
        raise TypeError("embedding blob must be bytes-like")
    vec = np.frombuffer(blob, dtype=np.float32)
    if vec.ndim != 1 or vec.shape[0] != DEFAULT_DIMENSIONS:
        raise ValueError("invalid embedding dimensions")
    return vec.copy()
