import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from src.domain.collective import CollectiveDAO


class TestTimelineAPI(unittest.TestCase):
    """Test the collective timeline API against an isolated database."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmpdir = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.tmpdir.name) / "collective.db"

        # timeline.py imports domain.collective because src/ is added to sys.path
        # by the application. Redirect that module's default DB to our test DB.
        cls.db_path_patch = patch(
            "domain.collective.DB_PATH",
            cls.db_path,
        )
        cls.db_path_patch.start()

        cls.client = TestClient(app)

    def setUp(self) -> None:
        # Use the same physical database as the API, but give every test a
        # clean database so tests cannot affect one another.
        self.dao = CollectiveDAO(db_path=self.db_path)
        self.dao.reset()
        self.dao.ensure_schema()

    def tearDown(self) -> None:
        self.dao.close()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.db_path_patch.stop()
        cls.tmpdir.cleanup()

    def test_empty_events(self):
        response = self.client.get("/api/events")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"events": []})

    def test_events_are_returned_in_id_order(self):
        first_id = self.dao.insert_collective_entry(
            source_profile="profile_a",
            origin_memory_id="memory-1",
        )
        second_id = self.dao.insert_collective_entry(
            source_profile="profile_b",
            origin_memory_id="memory-2",
        )

        response = self.client.get("/api/events")

        self.assertEqual(response.status_code, 200)

        events = response.json()["events"]

        self.assertEqual(
            [event["id"] for event in events],
            [first_id, second_id],
        )
        self.assertEqual(events[0]["source_profile"], "profile_a")
        self.assertEqual(events[1]["source_profile"], "profile_b")

    def test_events_can_be_filtered_by_profile(self):
        self.dao.insert_collective_entry(
            source_profile="profile_a",
            origin_memory_id="memory-a",
        )
        self.dao.insert_collective_entry(
            source_profile="profile_b",
            origin_memory_id="memory-b",
        )

        response = self.client.get(
            "/api/events",
            params={"profile": "profile_b"},
        )

        self.assertEqual(response.status_code, 200)

        events = response.json()["events"]

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["source_profile"], "profile_b")
        self.assertEqual(events[0]["origin_memory_id"], "memory-b")

    def test_event_contains_timeline_fields(self):
        row_id = self.dao.insert_collective_entry(
            source_profile="profile_a",
            origin_memory_id="memory-123",
            proposed_at="2026-08-21T12:00:00Z",
            validation_score=0.85,
        )

        response = self.client.get("/api/events")

        self.assertEqual(response.status_code, 200)

        event = response.json()["events"][0]

        self.assertEqual(event["id"], row_id)
        self.assertEqual(event["source_profile"], "profile_a")
        self.assertEqual(event["origin_memory_id"], "memory-123")
        self.assertTrue(
            "2026-08-21 12:00:00" in event["proposed_at"]
            or event["proposed_at"] == "2026-08-21T12:00:00Z"
        )
        self.assertEqual(event["validation_score"], 0.85)
        self.assertFalse(event["is_revoked"])
        self.assertFalse(event["is_promoted"])


if __name__ == "__main__":
    unittest.main()
