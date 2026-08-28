import tempfile
import unittest
from pathlib import Path

from src.domain.collective import CollectiveDAO
from src.domain.athena_interface import AthenaCollectiveInterface


class TestAthenaInterface(unittest.TestCase):
    def setUp(self) -> None:
        # Never allow tests to touch the project's real data/collective.db.
        self.tmpdir = tempfile.TemporaryDirectory()
        db_file = Path(self.tmpdir.name) / "collective.db"

        self.dao = CollectiveDAO(db_path=db_file)
        self.dao.ensure_schema()

        self.athena = AthenaCollectiveInterface()

        # Point Athena's DAO to the isolated test database.
        self.athena._dao = self.dao

    def tearDown(self) -> None:
        self.dao.close()
        self.tmpdir.cleanup()

    def test_promoted_entries_retrieval(self):
        entry_id = self.dao.insert_collective_entry("profile_a", "memA")

        self.dao.update_entry_promoted(entry_id)

        promoted_ids = self.athena.list_promoted()
        self.assertIn(entry_id, promoted_ids)

        record = self.athena.get_by_id(entry_id)
        self.assertEqual(record[1], "profile_a")
        self.assertEqual(record[2], "memA")

        src_record = self.athena.find_by_source("profile_a", "memA")
        self.assertEqual(src_record, record)

    def test_revoked_entries_excluded(self):
        entry_id = self.dao.insert_collective_entry("profile_b", "memB")

        self.dao.update_entry_promoted(entry_id)
        self.dao.update_entry_revoked(entry_id, "manual revocation")

        promoted_ids = self.athena.list_promoted()
        self.assertNotIn(entry_id, promoted_ids)

    def test_proposed_entry_invisible(self):
        """A proposed (not promoted) entry should not be returned."""
        entry_id = self.dao.insert_collective_entry("profile_p", "memP")

        record = self.athena.get_by_id(entry_id)
        self.assertIsNone(
            record,
            msg="Expected None for unpromoted entry via get_by_id",
        )

        src_record = self.athena.find_by_source("profile_p", "memP")
        self.assertIsNone(
            src_record,
            msg="Expected None for unpromoted entry via find_by_source",
        )

    def test_validated_not_promoted_invisible(self):
        """A validated but not promoted entry remains invisible."""
        entry_id = self.dao.insert_collective_entry(
            "profile_v",
            "memV",
            validated_at="2026-01-01T00:00:00",
        )

        record = self.athena.get_by_id(entry_id)
        self.assertIsNone(
            record,
            msg="Expected None for validated-nonpromoted via get_by_id",
        )

        src_record = self.athena.find_by_source("profile_v", "memV")
        self.assertIsNone(
            src_record,
            msg="Expected None for validated-nonpromoted via find_by_source",
        )

    def test_promoted_revoked_invisible(self):
        """A promoted but revoked entry should not appear in any Athena view."""
        entry_id = self.dao.insert_collective_entry("profile_r", "memR")

        self.dao.update_entry_promoted(entry_id)
        self.dao.update_entry_revoked(entry_id, "manual revocation")

        promoted_ids = self.athena.list_promoted()
        self.assertNotIn(
            entry_id,
            promoted_ids,
            msg="Revoked entry should not be in list_promoted",
        )

        record_by_id = self.athena.get_by_id(entry_id)
        self.assertIsNone(
            record_by_id,
            msg="Revoked entry should return None via get_by_id",
        )

        src_record = self.athena.find_by_source("profile_r", "memR")
        self.assertIsNone(
            src_record,
            msg="Revoked entry should return None via find_by_source",
        )


if __name__ == "__main__":
    unittest.main()
