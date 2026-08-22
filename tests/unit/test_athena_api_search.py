import numpy as np
import unittest

from src.domain.athena_api import AthenaAPI


class TestAthenaSearch(unittest.TestCase):
    def setUp(self) -> None:
        self.api = AthenaAPI()
        self.dao = self.api._iface._dao

        self.dao.conn.execute("DELETE FROM collective_entries")
        self.dao.conn.commit()

        self.vec_a = [1.0, 0.0]
        self.vec_b = [0.0, 1.0]
        self.vec_common = [1.0, 1.0]

    def _promote_and_embed(self, src: str, mem_id: str, vec) -> int:
        entry_id = self.dao.insert_collective_entry(src, mem_id)
        self.dao.update_entry_promoted(entry_id)
        self.dao.conn.execute(
            "UPDATE collective_entries SET embedding=? WHERE id=?",
            (np.asarray(vec, dtype=np.float32).tobytes(), entry_id),
        )
        self.dao.conn.commit()
        return entry_id

    def test_exact_match_orders_first(self):
        a_id = self._promote_and_embed("srcA", "mem1", self.vec_a)
        self._promote_and_embed("srcB", "mem2", self.vec_b)

        results = self.api.search_by_embedding(self.vec_a, 10)

        self.assertEqual(results[0], a_id)

    def test_non_promoted_excluded(self):
        entry_id = self.dao.insert_collective_entry("srcX", "memx")
        self.dao.conn.execute(
            "UPDATE collective_entries SET embedding=? WHERE id=?",
            (np.asarray(self.vec_a, dtype=np.float32).tobytes(), entry_id),
        )
        self.dao.conn.commit()

        results = self.api.search_by_embedding(self.vec_a, 10)

        self.assertNotIn(entry_id, results)

    def test_revoked_excluded(self):
        entry_id = self._promote_and_embed("srcY", "memy", self.vec_a)

        self.dao.conn.execute(
            "UPDATE collective_entries SET is_revoked=1 WHERE id=?",
            (entry_id,),
        )
        self.dao.conn.commit()

        results = self.api.search_by_embedding(self.vec_a, 10)

        self.assertNotIn(entry_id, results)

    def test_top_n_limited(self):
        for i in range(5):
            self._promote_and_embed(
                f"src{i}",
                f"mem{i}",
                self.vec_common,
            )

        results = self.api.search_by_embedding(self.vec_common, 3)

        self.assertEqual(len(results), 3)

    def test_missing_embedding_ignored(self):
        entry_id = self._promote_and_embed("srcA", "mem1", self.vec_a)

        self.dao.conn.execute(
            "UPDATE collective_entries SET embedding=NULL WHERE id=?",
            (entry_id,),
        )
        self.dao.conn.commit()

        results = self.api.search_by_embedding(self.vec_a, 10)

        self.assertNotIn(entry_id, results)

    def test_malformed_embedding_ignored(self):
        entry_id = self.dao.insert_collective_entry("srcA", "mem1")
        self.dao.update_entry_promoted(entry_id)

        self.dao.conn.execute(
            "UPDATE collective_entries SET embedding=? WHERE id=?",
            (b"not-a-valid-embedding", entry_id),
        )
        self.dao.conn.commit()

        results = self.api.search_by_embedding(self.vec_a, 10)

        self.assertNotIn(entry_id, results)

    def test_zero_vector_returns_all_valid_entries_zero_first(self):
        nonzero_id = self._promote_and_embed(
            "srcA",
            "mem1",
            self.vec_a,
        )
        zero_id = self._promote_and_embed(
            "srcB",
            "mem2",
            [0.0, 0.0],
        )

        results = self.api.search_by_embedding([0.0, 0.0], 10)

        self.assertEqual(results[0], zero_id)
        self.assertIn(nonzero_id, results)
        self.assertIn(zero_id, results)
        self.assertEqual(set(results), {nonzero_id, zero_id})

    def test_zero_vector_ignores_null_and_malformed_embeddings(self):
        valid_id = self._promote_and_embed(
            "srcA",
            "mem1",
            self.vec_a,
        )

        null_id = self.dao.insert_collective_entry("srcB", "mem2")
        self.dao.update_entry_promoted(null_id)

        malformed_id = self.dao.insert_collective_entry("srcC", "mem3")
        self.dao.update_entry_promoted(malformed_id)

        self.dao.conn.execute(
            "UPDATE collective_entries SET embedding=NULL WHERE id=?",
            (null_id,),
        )
        self.dao.conn.execute(
            "UPDATE collective_entries SET embedding=? WHERE id=?",
            (b"not-a-valid-embedding", malformed_id),
        )
        self.dao.conn.commit()

        results = self.api.search_by_embedding([0.0, 0.0], 10)

        self.assertIn(valid_id, results)
        self.assertNotIn(null_id, results)
        self.assertNotIn(malformed_id, results)


if __name__ == "__main__":
    unittest.main()
