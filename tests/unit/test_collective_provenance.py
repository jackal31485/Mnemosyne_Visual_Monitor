import unittest
from domain.collective import CollectiveDAO
from domain.collective_aggregate import CollectiveAggregator

class TestCollectiveProvenance(unittest.TestCase):
    def test_source_and_origin_preserved(self):
        dao = CollectiveDAO('tmp/prov1.db')
        dao.reset()
        dao.ensure_schema()
        entry_id = dao.insert_collective_entry("sourceA", "memX")
        dao.update_entry_promoted(entry_id)
        agg = CollectiveAggregator([dao])
        promoted = agg.list_all_promoted()
        self.assertEqual(len(promoted), 1)
        pid, src, memid = promoted[0][:3]
        self.assertEqual(src, "sourceA")
        self.assertEqual(memid, "memX")

if __name__ == '__main__': unittest.main()
