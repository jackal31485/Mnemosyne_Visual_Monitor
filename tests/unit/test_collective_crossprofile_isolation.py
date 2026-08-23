import unittest
from domain.collective import CollectiveDAO
from domain.collective_aggregate import CollectiveAggregator

class TestCollectiveCrossProfileIsolation(unittest.TestCase):
    def test_multiple_daos_still_retain_profiles(self):
        dao_a = CollectiveDAO('tmp/daoA.db')
        dao_a.reset(); dao_a.ensure_schema()
        dao_b = CollectiveDAO('tmp/daoB.db')
        dao_b.reset(); dao_b.ensure_schema()
        id_a = dao_a.insert_collective_entry("profileA", "mem1")
        id_b = dao_b.insert_collective_entry("profileB", "mem2")
        dao_a.update_entry_promoted(id_a)
        dao_b.update_entry_promoted(id_b)
        agg = CollectiveAggregator([dao_a, dao_b])
        promoted = agg.list_all_promoted()
        self.assertEqual(len(promoted), 2)
        srcs = {rec[1] for rec in promoted}
        self.assertSetEqual(srcs, {"profileA", "profileB"})

if __name__ == '__main__': unittest.main()
