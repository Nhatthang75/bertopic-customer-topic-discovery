import unittest
from bertopic_poc.discovery import (
    build_routed_pool, generate_discovery_grid, build_cluster_candidates, validate_merge_dag
)
from bertopic_poc.contracts import validate


class DiscoveryTests(unittest.TestCase):
    def test_build_routed_pool_filtering(self):
        units = [
            {'evidence_unit_id': 'u1', 'content_status': 'non_need', 'decision': 'non_need'},
            {'evidence_unit_id': 'u2', 'content_status': 'insufficient_evidence', 'decision': 'insufficient_evidence'},
            {'evidence_unit_id': 'u3', 'content_status': 'analyzable', 'decision': 'accepted'},
            {'evidence_unit_id': 'u4', 'content_status': 'analyzable', 'decision': 'unmatched'},
            {'evidence_unit_id': 'u5', 'content_status': 'analyzable', 'decision': 'ambiguous'},
            {'evidence_unit_id': 'u6', 'content_status': 'analyzable', 'decision': 'unmatched'},
        ]
        pool = build_routed_pool(units)
        self.assertEqual(pool['status'], 'ready')
        self.assertEqual(pool['n_pool'], 3)
        # u4, u5, u6 are in pool
        u_ids = [u['evidence_unit_id'] for u in pool['pool_units']]
        self.assertEqual(u_ids, ['u4', 'u5', 'u6'])

        # Empty pool
        empty_pool = build_routed_pool([units[0]])
        self.assertEqual(empty_pool['status'], 'empty_pool')

        # Insufficient pool (<3)
        small_pool = build_routed_pool([units[3], units[4]])
        self.assertEqual(small_pool['status'], 'insufficient_pool')
        self.assertEqual(small_pool['n_pool'], 2)

    def test_discovery_grid_16(self):
        grid = generate_discovery_grid()
        self.assertEqual(len(grid), 16)
        # Check first and last
        self.assertEqual(grid[0], (5, 2, 5, 1))
        self.assertEqual(grid[-1], (15, 5, 10, 5))

    def test_build_cluster_candidates_support_and_keys(self):
        # 6 units in cluster 0 across 5 conversations (support=5 -> proposed)
        # 2 units in cluster 1 across 1 conversation (support=1 -> monitor)
        # 3 units in cluster -1 (outliers -> no candidate row)
        units = [
            {'evidence_unit_id': 'u0', 'conversation_id': 'c0'},
            {'evidence_unit_id': 'u1', 'conversation_id': 'c1'},
            {'evidence_unit_id': 'u2', 'conversation_id': 'c2'},
            {'evidence_unit_id': 'u3', 'conversation_id': 'c3'},
            {'evidence_unit_id': 'u4', 'conversation_id': 'c4'},
            {'evidence_unit_id': 'u5', 'conversation_id': 'c4'},  # same convo c4
            {'evidence_unit_id': 'u6', 'conversation_id': 'c5'},
            {'evidence_unit_id': 'u7', 'conversation_id': 'c5'},  # same convo c5
            {'evidence_unit_id': 'u8', 'conversation_id': 'c6'},
            {'evidence_unit_id': 'u9', 'conversation_id': 'c7'},
            {'evidence_unit_id': 'u10', 'conversation_id': 'c8'},
        ]
        labels = [0, 0, 0, 0, 0, 0, 1, 1, -1, -1, -1]

        candidates = build_cluster_candidates(
            labels=labels,
            pool_units=units,
            run_id='run_main',
            seed=42,
            top_keywords_map={0: ['billing', 'invoice'], 1: ['glitch']}
        )

        # Only 2 candidates (cluster 0 and 1), -1 is excluded
        self.assertEqual(len(candidates), 2)

        c0 = candidates[0]
        self.assertEqual(c0['cluster_key'], 'candidate:run_main:42:0')
        self.assertEqual(c0['conversation_support'], 5)
        self.assertEqual(c0['status'], 'proposed')
        self.assertEqual(c0['keywords'], ['billing', 'invoice'])
        validate('candidates', c0)

        c1 = candidates[1]
        self.assertEqual(c1['cluster_key'], 'candidate:run_main:42:1')
        self.assertEqual(c1['conversation_support'], 1)
        self.assertEqual(c1['status'], 'monitor')
        validate('candidates', c1)

    def test_merge_dag_validation(self):
        current_candidates = {'candidate:r1:42:0', 'candidate:r1:42:1', 'candidate:r1:42:2'}
        known_topics = {'flow:account_access', 'flow:product_defect'}

        # 1. Valid merge
        ok1, err1 = validate_merge_dag(
            [('candidate:r1:42:0', 'candidate:r1:42:1'), ('candidate:r1:42:1', 'flow:account_access')],
            current_candidates, known_topics
        )
        self.assertTrue(ok1)
        self.assertIsNone(err1)

        # 2. Self merge (A -> A)
        ok2, err2 = validate_merge_dag(
            [('candidate:r1:42:0', 'candidate:r1:42:0')],
            current_candidates, known_topics
        )
        self.assertFalse(ok2)
        self.assertIn('self_merge', err2)

        # 3. Cycle (A -> B -> A)
        ok3, err3 = validate_merge_dag(
            [('candidate:r1:42:0', 'candidate:r1:42:1'), ('candidate:r1:42:1', 'candidate:r1:42:0')],
            current_candidates, known_topics
        )
        self.assertFalse(ok3)
        self.assertIn('cycle_detected', err3)

        # 4. Cross run target
        ok4, err4 = validate_merge_dag(
            [('candidate:r1:42:0', 'candidate:other_run:42:0')],
            current_candidates, known_topics
        )
        self.assertFalse(ok4)
        self.assertIn('invalid_target', err4)


if __name__ == '__main__':
    unittest.main()
