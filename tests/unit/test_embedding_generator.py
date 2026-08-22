import tempfile
import unittest
from pathlib import Path

import numpy as np

from src.domain.collective import CollectiveDAO
from src.domain.embedding_generator import (
    DEFAULT_DIMENSIONS,
    decode_embedding,
    embed_sanitized,
)


class TestEmbeddingGenerator(unittest.TestCase):

    def test_deterministic_output(self):
        first = embed_sanitized("Hello world")
        second = embed_sanitized("Hello world")

        self.assertEqual(first, second)

    def test_different_input_produces_different_output(self):
        first = embed_sanitized("Hello world")
        second = embed_sanitized("Goodbye world")

        self.assertNotEqual(first, second)

    def test_vector_has_expected_dimensions(self):
        encoded = embed_sanitized("Hello world")
        vector = decode_embedding(encoded)

        self.assertEqual(len(vector), DEFAULT_DIMENSIONS)
        self.assertEqual(vector.dtype, np.float32)

    def test_vector_has_expected_binary_size(self):
        encoded = embed_sanitized("Hello world")

        self.assertEqual(
            len(encoded),
            DEFAULT_DIMENSIONS * 4,
        )

    def test_vector_is_normalized(self):
        vector = decode_embedding(
            embed_sanitized("Hello world")
        )

        norm = float(np.linalg.norm(vector))

        self.assertAlmostEqual(norm, 1.0, places=5)

    def test_semantically_related_text_is_closer(self):
        reference = decode_embedding(
            embed_sanitized(
                "The cat is sleeping on the sofa."
            )
        )

        related = decode_embedding(
            embed_sanitized(
                "A cat is resting on a couch."
            )
        )

        unrelated = decode_embedding(
            embed_sanitized(
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

    def test_non_string_input_rejected(self):
        with self.assertRaises(TypeError):
            embed_sanitized(None)  # type: ignore[arg-type]

    def test_empty_input_rejected(self):
        with self.assertRaises(ValueError):
            embed_sanitized("   ")

    def test_embedding_can_be_stored_by_collective_dao(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "embedding.db"
            dao = CollectiveDAO(db_path)

            try:
                dao.ensure_schema()

                entry_id = dao.insert_collective_entry(
                    "test-profile",
                    "test-memory",
                )

                embedding = embed_sanitized(
                    "Approved sanitized summary"
                )

                dao.update_entry_embedding(
                    entry_id,
                    embedding,
                )

                row = dao.conn.execute(
                    """
                    SELECT embedding
                    FROM collective_entries
                    WHERE id = ?
                    """,
                    (entry_id,),
                ).fetchone()

                self.assertIsNotNone(row)
                self.assertIsNotNone(row["embedding"])

                stored = bytes(row["embedding"])

                self.assertEqual(
                    stored,
                    embedding,
                )

                decoded = decode_embedding(stored)

                self.assertEqual(
                    len(decoded),
                    DEFAULT_DIMENSIONS,
                )

            finally:
                dao.close()


if __name__ == "__main__":
    unittest.main()
