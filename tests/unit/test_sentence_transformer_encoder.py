import unittest
from pathlib import Path

import numpy as np

from src.domain.embedding_generator import (
    DEFAULT_DIMENSIONS,
    SentenceTransformerEncoder,
    decode_embedding,
)


class TestSentenceTransformerEncoder(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.model_path = Path("models/all-MiniLM-L6-v2")

        cls.encoder = SentenceTransformerEncoder(
            model_path=cls.model_path,
            device="cpu",
        )

    def test_model_has_expected_dimension(self):
        self.assertEqual(
            self.encoder.dimensions,
            DEFAULT_DIMENSIONS,
        )

    def test_generate_returns_expected_embedding(self):
        encoded = self.encoder.generate(
            "The cat is sleeping on the sofa."
        )

        vector = decode_embedding(encoded)

        self.assertEqual(
            vector.shape,
            (DEFAULT_DIMENSIONS,),
        )
        self.assertEqual(
            vector.dtype,
            np.float32,
        )

    def test_generate_returns_normalized_embedding(self):
        vector = decode_embedding(
            self.encoder.generate(
                "The cat is sleeping on the sofa."
            )
        )

        norm = float(np.linalg.norm(vector))

        self.assertAlmostEqual(
            norm,
            1.0,
            places=5,
        )

    def test_generate_produces_semantically_meaningful_similarity(self):
        reference = decode_embedding(
            self.encoder.generate(
                "The cat is sleeping on the sofa."
            )
        )

        related = decode_embedding(
            self.encoder.generate(
                "A cat is resting on a couch."
            )
        )

        unrelated = decode_embedding(
            self.encoder.generate(
                "The spacecraft launched into orbit."
            )
        )

        related_similarity = float(
            np.dot(reference, related)
        )

        unrelated_similarity = float(
            np.dot(reference, unrelated)
        )

        self.assertGreater(
            related_similarity,
            unrelated_similarity,
        )

    def test_generate_is_deterministic(self):
        first = self.encoder.generate(
            "The cat is sleeping on the sofa."
        )
        second = self.encoder.generate(
            "The cat is sleeping on the sofa."
        )

        self.assertEqual(first, second)

    def test_generate_rejects_non_string(self):
        with self.assertRaises(TypeError):
            self.encoder.generate(None)  # type: ignore[arg-type]

    def test_generate_rejects_empty_input(self):
        with self.assertRaises(ValueError):
            self.encoder.generate("   ")


if __name__ == "__main__":
    unittest.main()
