import unittest
from pathlib import Path

import sqlite3

# Import DAO and Athena interface
from src.domain.collective import CollectiveDAO
from src.domain.athena_interface import AthenaCollectiveInterface

class TestAthenaInterface(unittest.TestCase):
    def setUp(self) -> None:
        # Use DAO’s default DB (data/collective.db). Clear any previous file.
        db_file = Path("data") / "collective.db"
        if db_file.exists():
            db_file.unlink()
        self.dao = CollectiveDAO()
        self.dao.ensure_schema()
        self.athena = AthenaCollectiveInterface()
        # Point Athena’s DAO to the same underlying instance
        self.athena._dao = self.dao

    def tearDown(self) -> None:
        if self.athena._dao.conn is not None:  # pragma: no cover
            self.athena._dao.close()

    def test_promoted_entries_retrieval(self):
        entry_id = self.dao.insert_collective_entry("profile_a", "memA")
        # Promote the entry
        self.dao.update_entry_promoted(entry_id)
        promoted_ids = self.athena.list_promoted()
        self.assertIn(entry_id, promoted_ids)
        record = self.athena.get_by_id(entry_id)
        self.assertEqual(record[1], "profile_a")
        self.assertEqual(record[2], "memA")
        # Verify find_by_source returns same record
        src_record = self.athena.find_by_source("profile_a", "memA")
        self.assertEqual(src_record, record)

    def test_revoked_entries_excluded(self):
        entry_id = self.dao.insert_collective_entry("profile_b", "memB")
        # Promote then revoke
        self.dao.update_entry_promoted(entry_id)
        self.dao.update_entry_revoked(entry_id, "manual revocation")
        promoted_ids = self.athena.list_promoted()
        self.assertNotIn(entry_id, promoted_ids)

if __name__ == "__main__":
    unittest.main()
