import tempfile
import unittest
from pathlib import Path

from src.domain.collective import CollectiveDAO


class TestCollectiveReferences(unittest.TestCase):
    """Test collective references without touching the real project database."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmpdir = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.tmpdir.name) / "collective.db"

        cls.dao = CollectiveDAO(db_path=cls.db_path)
        cls.dao.ensure_schema()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.dao.close()
        cls.tmpdir.cleanup()

    def test_valid_reference_insertion(self):
        row_id = self.dao.insert_collective_entry(
            source_profile="profile_a",
            origin_memory_id="memA-123",
        )

        entry = self.dao.get_by_id(row_id)

        self.assertIsNotNone(entry)
        self.assertEqual(entry[1], "profile_a")
        self.assertEqual(entry[2], "memA-123")

    def test_duplicate_reference_handling(self):
        id1 = self.dao.insert_collective_entry(
            "profile_a",
            "dup_mem",
        )

        id2 = self.dao.insert_collective_entry(
            "profile_a",
            "dup_mem",
        )

        self.assertNotEqual(id1, id2)

    def test_cross_profile_reference(self):
        a_id = self.dao.insert_collective_entry(
            "profile_a",
            "memA",
        )

        b_id = self.dao.insert_collective_entry(
            "profile_b",
            "memB",
        )

        a_ent = self.dao.get_by_id(a_id)
        b_ent = self.dao.get_by_id(b_id)

        self.assertEqual(a_ent[1], "profile_a")
        self.assertEqual(b_ent[1], "profile_b")

    def test_invalid_malformed_reference(self):
        with self.assertRaises(ValueError):
            self.dao.insert_collective_entry(
                "",
                "memX",
            )

        with self.assertRaises(ValueError):
            self.dao.insert_collective_entry(
                "profile",
                "",
            )

    def test_raw_memory_not_stored(self):
        row_id = self.dao.insert_collective_entry(
            source_profile="profile_a",
            origin_memory_id="mem1",
        )

        entry = self.dao.get_by_id(row_id)

        self.assertEqual(
            len(entry),
            9,
            "schema tuple length",
        )

    def test_provenance_integrity(self):
        row_id = self.dao.insert_collective_entry(
            source_profile="profile_a",
            origin_memory_id="memX",
            proposed_at="2026-08-21T12:00:00Z",
            validation_score=0.85,
        )

        entry = self.dao.get_by_id(row_id)

        ts = entry[3]

        self.assertTrue(
            "2026-08-21 12:00:00" in ts
            or "2026-08-21T12:00:00Z" == ts,
            f"proposed_at mismatch: got {ts}",
        )

        self.assertAlmostEqual(
            entry[5],
            0.85,
            places=2,
        )

    def test_revocation(self):
        row_id = self.dao.insert_collective_entry(
            "profile_a",
            "memR",
        )

        self.dao.update_entry_revoked(
            row_id,
            "user request",
        )

        entry = self.dao.get_by_id(row_id)

        self.assertTrue(entry[7])
        self.assertEqual(
            entry[8],
            "user request",
        )


if __name__ == "__main__":
    unittest.main()
