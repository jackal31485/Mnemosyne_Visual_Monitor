import tempfile
import unittest
from pathlib import Path

from src.domain import collective
from src.domain.athena_api import AthenaAPI


class TestAthenaAPI(unittest.TestCase):

    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()

        self.db_path = (
            Path(self.tmpdir.name) / "collective.db"
        )

        # AthenaAPI -> AthenaInterface -> CollectiveDAO()
        # must use an isolated test database.
        self._original_db_path = collective.DB_PATH
        collective.DB_PATH = self.db_path

        self.api = AthenaAPI()
        self.dao = self.api._iface._dao

        self.dao.ensure_schema()

    def tearDown(self) -> None:
        self.dao.close()
        collective.DB_PATH = self._original_db_path
        self.tmpdir.cleanup()

    def test_resolve_memory_visible(self):
        entry_id = self.dao.insert_collective_entry(
            "s3",
            "originXYZ",
        )

        self.dao.update_entry_promoted(entry_id)

        sm = self.api.resolve_memory("originXYZ")

        self.assertIsNotNone(sm)
        self.assertEqual(sm.id, str(entry_id))

    def test_resolve_memory_unpromoted(self):
        self.dao.insert_collective_entry(
            "s5",
            "oriNP",
        )

        sm = self.api.resolve_memory("oriNP")

        self.assertIsNone(sm)