import tempfile
import unittest
from pathlib import Path

from src.domain.collective import CollectiveDAO


class TestCollectiveFoundation(unittest.TestCase):
    """Test the collective DAO without touching the real project database."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "collective.db"
        self.dao = CollectiveDAO(db_path=self.db_path)

    def test_db_creation_and_schema(self):
        self.dao.ensure_schema()

        self.assertTrue(
            self.db_path.exists(),
            "Collective DB file not created",
        )

        tables = self.dao.get_table_names()

        self.assertIn(
            "collective_entries",
            tables,
            "Expected table missing",
        )

    def test_basic_crud(self):
        self.dao.ensure_schema()

        row_id = self.dao.add_entry("alice", "mem001")

        entry = self.dao.get_by_id(row_id)

        self.assertIsNotNone(entry)
        self.assertEqual(entry[1], "alice")

        self.dao.update_entry_revoked(
            row_id,
            "user requested deletion",
        )

        updated = self.dao.get_by_id(row_id)

        self.assertTrue(updated[7])

        self.dao.delete_entry(row_id)

        after_del = self.dao.get_by_id(row_id)

        self.assertIsNone(after_del)

    def tearDown(self):
        self.dao.close()
        self.tmpdir.cleanup()


if __name__ == "__main__":
    unittest.main()
