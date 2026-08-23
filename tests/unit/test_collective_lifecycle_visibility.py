import unittest
from domain.collective import CollectiveDAO
from domain.collective_aggregate import CollectiveAggregator

class TestCollectiveLifecycleVisibility(unittest.TestCase):
    def test_proposed_not_visible(self):
        dao = CollectiveDAO('tmp/lifecycle.db')
        dao.reset()
        dao.ensure_schema()
        id0 = dao.insert_collective_entry("srcP", "memP")  # proposed only
        agg = CollectiveAggregator([dao])
        self.assertEqual(agg.list_all_promoted(), [])
    def test_prompted_visible_when_promoted(self):
        dao = CollectiveDAO('tmp/lifecycle2.db')
        dao.reset()
        dao.ensure_schema()
        id1 = dao.insert_collective_entry("srcV", "memV")
        dao.update_entry_promoted(id1)
        agg = CollectiveAggregator([dao])
        self.assertEqual(len(agg.list_all_promoted()), 1)
    def test_revoked_hides_from_aggregation(self):
        dao = CollectiveDAO('tmp/lifecycle3.db')
        dao.reset()
        dao.ensure_schema()
        id2 = dao.insert_collective_entry("srcR", "memR")
        dao.update_entry_promoted(id2)
        dao.update_entry_revoked(id2, "policy")
        agg = CollectiveAggregator([dao])
        self.assertEqual(agg.list_all_promoted(), [])

if __name__ == '__main__': unittest.main()
