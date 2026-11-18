import unittest
from bertopic_poc.taxonomy import (
    FLOW_SUBFLOW_CANONICAL, KNOWN_K_FLOWS, HIDDEN_DEV_FLOWS, HIDDEN_FINAL_FLOWS,
    flow_id, subflow_id, resolve_alias, get_known_taxonomy, get_full_taxonomy
)
from bertopic_poc.cohorts import StatisticsScope, build_topic_statistics, roll_up_flow_statistics
from bertopic_poc.policy import AccessPolicy, LeakageError
from bertopic_poc.contracts import validate


class TaxonomyAndCohortsTests(unittest.TestCase):
    def test_taxonomy_10_55_structure(self):
        self.assertEqual(len(FLOW_SUBFLOW_CANONICAL), 10)
        total_subflows = sum(len(subs) for subs in FLOW_SUBFLOW_CANONICAL.values())
        self.assertEqual(total_subflows, 55)

        # Check unique subflow IDs with namespace
        all_sub_ids = set()
        for flow, subs in FLOW_SUBFLOW_CANONICAL.items():
            f_id = flow_id(flow)
            self.assertTrue(f_id.startswith('flow:'))
            for sub in subs:
                s_id = subflow_id(flow, sub)
                self.assertTrue(s_id.startswith(f"subflow:{flow}/"))
                self.assertNotIn(s_id, all_sub_ids)
                all_sub_ids.add(s_id)
        self.assertEqual(len(all_sub_ids), 55)

    def test_alias_resolution(self):
        # Valid canonical
        sub, rule, status = resolve_alias('product_defect', 'refund_initiate')
        self.assertEqual((sub, status), ('refund_initiate', 'resolved'))

        # single_item_query alias: <item>_how_<n>
        sub, rule, status = resolve_alias('single_item_query', 'jacket_how_2')
        self.assertEqual((sub, rule, status), ('jacket', 'ontology_item_alias', 'resolved'))

        # storewide_query alias: <category>_<n>
        sub, rule, status = resolve_alias('storewide_query', 'timing_4')
        self.assertEqual((sub, rule, status), ('timing', 'ontology_category_alias', 'resolved'))

        # Invalid/unrecognized suffix
        sub, rule, status = resolve_alias('storewide_query', 'timing_99')
        self.assertEqual(status, 'unresolved')

        # Wrong flow for alias
        sub, rule, status = resolve_alias('order_issue', 'jacket_how_2')
        self.assertEqual(status, 'unresolved')

        # Ambiguous ontology labels
        sub, rule, status = resolve_alias('subscription_inquiry', 'status_questions')
        self.assertEqual((sub, status), (None, 'unresolved'))
        self.assertEqual(rule, 'ambiguous_ontology_label')

        sub, rule, status = resolve_alias('order_issue', 'status_delivery_date')
        self.assertEqual((sub, status), (None, 'unresolved'))
        self.assertEqual(rule, 'ambiguous_ontology_label')

    def test_known_vs_full_isolation(self):
        known = get_known_taxonomy()
        self.assertEqual(len(known['flows']), 7)
        self.assertEqual(set(known['flows'].keys()), set(KNOWN_K_FLOWS))
        for hidden in HIDDEN_DEV_FLOWS + HIDDEN_FINAL_FLOWS:
            self.assertNotIn(hidden, known['flows'])

        # Policy checks for full taxonomy
        policy = AccessPolicy()
        with self.assertRaises(LeakageError):
            get_full_taxonomy(policy)

        # After gate G2 with fresh authorized policy
        policy_g2 = AccessPolicy(gate=2)
        full = get_full_taxonomy(policy_g2)
        self.assertEqual(len(full['flows']), 10)

    def test_four_counting_units(self):
        # Fixture: 1 conversation, 3 customer turns: Hi (0), I need a refund (1), Thanks (2)
        scope = StatisticsScope(
            scope_id='scope_test',
            eligible_conversation_ids={'c1'},
            total_customer_messages=3
        )
        assignments = [
            {
                'conversation_id': 'c1',
                'topic_id': 'flow:product_defect',
                'source': 'fixed',
                'segment_ids': ['s1'],
                'evidence_spans': [{'turn_index': 1, 'start': 0, 'end': 15}],
                'evidence_status': 'model_supported'
            }
        ]

        stats = build_topic_statistics(
            scope=scope,
            topic_id='flow:product_defect',
            source='fixed',
            evidence_basis='predicted',
            assignments=assignments
        )
        validate('topic_statistics', stats)

        self.assertEqual(stats['customer_message_count'], 3)
        self.assertEqual(stats['source_messages_with_assignment'], 1)
        self.assertEqual(stats['segment_count'], 1)
        self.assertEqual(stats['mention_count'], 1)
        self.assertEqual(stats['conversation_count'], 1)
        self.assertEqual(stats['eligible_conversations'], 1)
        self.assertEqual(stats['conversation_share'], 1.0)

    def test_topic_filter_and_null_rules(self):
        # 100 eligible conversations, 20 with topic X
        all_convs = {f'c{i}' for i in range(100)}
        scope = StatisticsScope(
            scope_id='test_100',
            eligible_conversation_ids=all_convs,
            total_customer_messages=300
        )
        assignments = [
            {
                'conversation_id': f'c{i}',
                'topic_id': 'flow:order_issue',
                'source': 'fixed',
                'segment_ids': [f'seg_{i}'],
                'evidence_spans': [{'turn_index': 0, 'start': 0, 'end': 10}],
                'evidence_status': 'model_supported'
            }
            for i in range(20)
        ]

        stats = build_topic_statistics(
            scope=scope,
            topic_id='flow:order_issue',
            source='fixed',
            evidence_basis='predicted',
            assignments=assignments
        )
        validate('topic_statistics', stats)

        # Share must be 20/100 = 0.20, NOT 20/20
        self.assertEqual(stats['conversation_count'], 20)
        self.assertEqual(stats['eligible_conversations'], 100)
        self.assertEqual(stats['conversation_share'], 0.20)

        # cluster_membership basis must have mention_count = None
        stats_cluster = build_topic_statistics(
            scope=scope,
            topic_id='candidate:run1:seed42:0',
            source='discovery',
            evidence_basis='cluster_membership',
            assignments=assignments
        )
        validate('topic_statistics', stats_cluster)
        self.assertIsNone(stats_cluster['mention_count'])
        self.assertEqual(stats_cluster['null_reason'], 'missing_localized_evidence')

        # partial verified scope must have mention_count = None
        stats_partial = build_topic_statistics(
            scope=scope,
            topic_id='flow:order_issue',
            source='fixed',
            evidence_basis='verified',
            assignments=assignments,
            reviewed_scope_conversation_ids={'c0', 'c1'}  # only 2 of 100 reviewed
        )
        validate('topic_statistics', stats_partial)
        self.assertIsNone(stats_partial['mention_count'])
        self.assertEqual(stats_partial['null_reason'], 'unreviewed_scope')

        # Empty scope
        empty_scope = StatisticsScope('empty', set(), 0)
        stats_empty = build_topic_statistics(
            scope=empty_scope,
            topic_id='flow:order_issue',
            source='fixed',
            evidence_basis='predicted',
            assignments=[]
        )
        validate('topic_statistics', stats_empty)
        self.assertIsNone(stats_empty['conversation_share'])
        self.assertEqual(stats_empty['null_reason'], 'empty_scope')

    def test_roll_up_distinct_union(self):
        # 1 conversation with 2 subflows under same flow
        scope = StatisticsScope('scope_rollup', {'c1'}, 2)
        child_assignments = [
            {
                'conversation_id': 'c1',
                'topic_id': 'subflow:single_item_query/boots',
                'source': 'fixed',
                'segment_ids': ['s1'],
                'evidence_spans': [{'turn_index': 0, 'start': 0, 'end': 5}],
                'evidence_status': 'model_supported'
            },
            {
                'conversation_id': 'c1',
                'topic_id': 'subflow:single_item_query/shirt',
                'source': 'fixed',
                'segment_ids': ['s2'],
                'evidence_spans': [{'turn_index': 1, 'start': 0, 'end': 5}],
                'evidence_status': 'model_supported'
            }
        ]
        flow_stats = roll_up_flow_statistics(
            scope=scope,
            flow_id='flow:single_item_query',
            source='fixed',
            evidence_basis='predicted',
            child_assignments=child_assignments
        )
        validate('topic_statistics', flow_stats)
        # Conversation count must be 1 (distinct union), not 2
        self.assertEqual(flow_stats['conversation_count'], 1)
        self.assertEqual(flow_stats['conversation_share'], 1.0)


if __name__ == '__main__':
    unittest.main()
