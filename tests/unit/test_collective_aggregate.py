import unittest
from domain.collective import CollectiveDAO
from domain.collective_aggregate import CollectiveAggregator

class TestCollectiveAggregator(unittest.TestCase):
    def setUp(self):
        self.dao1 = CollectiveDAO('tmp/db1.db')
        self.dao2 = CollectiveDAO('tmp/db2.db')
        for dao in (self.dao1, self.dao2):
            dao.reset()
            dao.ensure_schema()

    def test_list_all_promoted(self):
        id1 = self.dao1.insert_collective_entry("source1", "memA")
        id2 = self.dao2.insert_collective_entry("source2", "memB")
        self.dao1.update_entry_promoted(id1)
        self.dao2.update_entry_revoked(id2, "policy")

        agg = CollectiveAggregator([self.dao1, self.dao2])
        promoted = agg.list_all_promoted()
        self.assertEqual(len(promoted), 1)
        pid, src, memid = promoted[0][:3]
        self.assertEqual(src, "source1")
        self.assertEqual(memid, "memA")

    def test_get_by_source(self):
        id2 = self.dao2.insert_collective_entry("source2", "memB")
        agg = CollectiveAggregator([self.dao1, self.dao2])
        rec = agg.get_by_source_across_profiles("source2", "memB")
        self.assertIsNotNone(rec)
        self.assertEqual(rec[0], id2)

if __name__ == '__main__':
    unittest.main()
