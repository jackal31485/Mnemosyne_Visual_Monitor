import unittest
from src.domain.athena_api import AthenaAPI, SanitizedMemory

class TestAthenaAPI(unittest.TestCase):
    def setUp(self) -> None:
        # Create DAO with fresh DB for isolation.
        self.api = AthenaAPI()

    def test_get_entry_promoted_non_revoked_visible(self):
        entry_id = self.api._iface._dao.insert_collective_entry("profile_a", "memA")
        self.api._iface._dao.update_entry_promoted(entry_id)
        record = self.api.get_entry(entry_id)
        self.assertIsNotNone(record)
        self.assertEqual(record[1], "profile_a")

    def test_get_entry_unpromoted_invisible(self):
        entry_id = self.api._iface._dao.insert_collective_entry("profile_b", "memB")
        record = self.api.get_entry(entry_id)
        self.assertIsNone(record)

    def test_get_entry_revoked_invisible(self):
        entry_id = self.api._iface._dao.insert_collective_entry("profile_c", "memC")
        self.api._iface._dao.update_entry_promoted(entry_id)
        self.api._iface._dao.update_entry_revoked(entry_id, "revoked manually")
        record = self.api.get_entry(entry_id)
        self.assertIsNone(record)

    def test_list_entries_only_visible(self):
        id1 = self.api._iface._dao.insert_collective_entry("p1", "m1")
        id2 = self.api._iface._dao.insert_collective_entry("p1", "m2")
        # promote only first
        self.api._iface._dao.update_entry_promoted(id1)
        ids = self.api.list_entries()
        self.assertIn(id1, ids)
        self.assertNotIn(id2, ids)

    def test_list_entries_profile_filter(self):
        id_a = self.api._iface._dao.insert_collective_entry("profileA", "memX")
        id_b = self.api._iface._dao.insert_collective_entry("profileB", "memY")
        self.api._iface._dao.update_entry_promoted(id_a)
        self.api._iface._dao.update_entry_promoted(id_b)
        ids_profileA = self.api.list_entries(profile="profileA")
        self.assertIn(id_a, ids_profileA)
        self.assertNotIn(id_b, ids_profileA)

    def test_find_by_source_visibility(self):
        entry_id = self.api._iface._dao.insert_collective_entry("src1", "mem123")
        self.api._iface._dao.update_entry_promoted(entry_id)
        rec = self.api.find_by_source("src1", "mem123")
        self.assertIsNotNone(rec)

    def test_resolve_memory_visible(self):
        entry_id = self.api._iface._dao.insert_collective_entry("s3", "originXYZ")
        self.api._iface._dao.update_entry_promoted(entry_id)
        sm = self.api.resolve_memory("originXYZ")
        self.assertIsNotNone(sm)
        self.assertEqual(sm.id, str(entry_id))

    def test_resolve_memory_revoked(self):
        entry_id = self.api._iface._dao.insert_collective_entry("s4", "oriRev")
        self.api._iface._dao.update_entry_promoted(entry_id)
        self.api._iface._dao.update_entry_revoked(entry_id, "revoked")
        sm = self.api.resolve_memory("oriRev")
        self.assertIsNone(sm)

    def test_resolve_memory_unpromoted(self):
        entry_id = self.api._iface._dao.insert_collective_entry("s5", "oriNP")
        sm = self.api.resolve_memory("oriNP")
        self.assertIsNone(sm)

    def test_api_no_mutation_methods_exposed(self):
        # The AthenaAPI should not have DAO mutation attributes.
        attrs = [a for a in dir(self.api) if a.startswith('_')]
        # Exclude the underlying interface
        attrs = [a for a in attrs if a != '_iface']
        for attr in attrs:
            method = getattr(self.api, attr)
            if callable(method):
                self.assertFalse(attr.endswith('update') or attr.endswith('delete'))

if __name__ == '__main__':
    unittest.main()
