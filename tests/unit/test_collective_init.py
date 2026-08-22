import os
import unittest
from pathlib import Path
import sqlite3

# Import the DAO we just created
from src.domain.collective import CollectiveDAO

db_path = Path('data') / 'collective.db'

class TestCollectiveFoundation(unittest.TestCase):
    def setUp(self):
        # Ensure a clean slate: delete if it exists.
        if db_path.exists():
            db_path.unlink()
        self.dao = CollectiveDAO()
    
    def test_db_creation_and_schema(self):
        # Create the database and ensure tables exist.
        self.dao.ensure_schema()
        self.assertTrue(db_path.exists(), "Collective DB file not created")
        tables = self.dao.get_table_names()
        self.assertIn("collective_entries", tables, "Expected table missing")
    
    def test_basic_crud(self):
        # Table exists, perform simple CRUD.
        self.dao.ensure_schema()
        row_id = self.dao.add_entry('alice', 'mem001')
        entry = self.dao.get_by_id(row_id)
        self.assertIsNotNone(entry)
        self.assertEqual(entry[1], "alice")
        # Update revoked flag
        self.dao.update_entry_revoked(row_id, 'user requested deletion')
        updated = self.dao.get_by_id(row_id)
        self.assertTrue(updated[7])  # is_revoked
        # Delete and verify removal
        self.dao.delete_entry(row_id)
        after_del = self.dao.get_by_id(row_id)
        self.assertIsNone(after_del)
    
    def tearDown(self):
        self.dao.close()
        if db_path.exists():
            db_path.unlink()

if __name__ == "__main__":
    unittest.main()
