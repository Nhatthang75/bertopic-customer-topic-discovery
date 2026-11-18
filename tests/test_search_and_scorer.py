import unittest
from bertopic_poc.scorer import (
    score_evidence_unit, aggregate_windows_max_score, roll_up_conversation_status, EvidenceUnitScore
)
from bertopic_poc.baseline import BaselineClassifier, search_baseline_grid


class SearchAndScorerTests(unittest.TestCase):
    def test_scorer_decision_table_and_offsets(self):
        # 1. Accepted: s1=0.80, s2=0.55, tau=0.50, delta=0.10
        scores1 = {'flow:account_access': 0.80, 'flow:manage_account': 0.55}
        u1 = score_evidence_unit('u1', 'c1', 0, 10, 35, 'analyzable', scores1, tau=0.50, delta=0.10)
        self.assertEqual(u1.decision, 'accepted')
        self.assertEqual(u1.top1_topic, 'flow:account_access')
        self.assertEqual(u1.span_start, 10)
        self.assertEqual(u1.span_end, 35)

        # 2. Ambiguous: s1=0.76, s2=0.73 (margin=0.03 < 0.10)
        scores2 = {'flow:shipping_issue': 0.76, 'flow:order_issue': 0.73}
        u2 = score_evidence_unit('u2', 'c1', 1, 40, 65, 'analyzable', scores2, tau=0.50, delta=0.10)
        self.assertEqual(u2.decision, 'ambiguous')
        self.assertEqual(u2.top1_topic, 'flow:shipping_issue')
        self.assertEqual(u2.top2_topic, 'flow:order_issue')

        # 3. Unmatched: s1=0.49 < tau=0.50
        scores3 = {'flow:product_defect': 0.49, 'flow:single_item_query': 0.20}
        u3 = score_evidence_unit('u3', 'c1', 2, 70, 90, 'analyzable', scores3, tau=0.50, delta=0.10)
        self.assertEqual(u3.decision, 'unmatched')

        # 4. Non-need and Insufficient
        u_non = score_evidence_unit('u4', 'c1', 3, 0, 5, 'non_need', {'flow:order_issue': 0.99})
        self.assertEqual(u_non.decision, 'non_need')

        u_ins = score_evidence_unit('u5', 'c1', 4, 6, 9, 'insufficient_evidence', {'flow:order_issue': 0.99})
        self.assertEqual(u_ins.decision, 'insufficient_evidence')

    def test_windows_aggregation(self):
        w1 = {'flow:account_access': 0.60, 'flow:order_issue': 0.40}
        w2 = {'flow:account_access': 0.75, 'flow:order_issue': 0.30}
        agg = aggregate_windows_max_score([w1, w2])
        # Max per topic, does not sum
        self.assertEqual(agg['flow:account_access'], 0.75)
        self.assertEqual(agg['flow:order_issue'], 0.40)

    def test_conversation_rollup_statuses(self):
        # Fixture 1: Non-need only
        u_nn = EvidenceUnitScore('u1', 'c1', 0, 0, 5, 'non_need', 0.0, 0.0, '', None, 'non_need')
        res1 = roll_up_conversation_status([u_nn])
        self.assertEqual(res1['conversation_status'], 'non_need')
        self.assertFalse(res1['residual_flag'])
        self.assertIsNone(res1['primary_topic'])

        # Fixture 2: Insufficient only
        u_in = EvidenceUnitScore('u2', 'c1', 0, 0, 3, 'insufficient_evidence', 0.0, 0.0, '', None, 'insufficient_evidence')
        res2 = roll_up_conversation_status([u_in])
        self.assertEqual(res2['conversation_status'], 'insufficient_evidence')
        self.assertFalse(res2['residual_flag'])

        # Fixture 3: Known only (1 accepted unit)
        u_acc1 = EvidenceUnitScore('u3', 'c1', 0, 0, 20, 'analyzable', 0.85, 0.50, 'flow:account_access', 'flow:order_issue', 'accepted')
        res3 = roll_up_conversation_status([u_acc1])
        self.assertEqual(res3['conversation_status'], 'known')
        self.assertFalse(res3['residual_flag'])
        self.assertEqual(res3['primary_topic'], 'flow:account_access')

        # Fixture 4: Unknown candidate only (1 unmatched or ambiguous unit)
        u_unm = EvidenceUnitScore('u4', 'c1', 0, 0, 20, 'analyzable', 0.40, 0.20, 'flow:order_issue', None, 'unmatched')
        res4 = roll_up_conversation_status([u_unm])
        self.assertEqual(res4['conversation_status'], 'unknown_candidate')
        self.assertTrue(res4['residual_flag'])
        self.assertIsNone(res4['primary_topic'])  # abstain

        # Fixture 5: Mixed (1 accepted known + 1 ambiguous/unmatched residual)
        res5 = roll_up_conversation_status([u_acc1, u_unm])
        self.assertEqual(res5['conversation_status'], 'mixed')
        self.assertTrue(res5['residual_flag'])
        self.assertEqual(res5['primary_topic'], 'flow:account_access')

        # Fixture 6: Multi-span Multi-label (2 independent accepted spans)
        u_acc2 = EvidenceUnitScore('u5', 'c1', 1, 25, 50, 'analyzable', 0.82, 0.45, 'flow:product_defect', None, 'accepted')
        res6 = roll_up_conversation_status([u_acc1, u_acc2])
        self.assertEqual(res6['conversation_status'], 'known')
        self.assertEqual(res6['accepted_topics'], {'flow:account_access', 'flow:product_defect'})
        # Primary topic is flow:account_access (s1=0.85 > 0.82)
        self.assertEqual(res6['primary_topic'], 'flow:account_access')

    def test_baseline_classifier_and_search_grid(self):
        train_texts = [
            "I cannot log into my account, please reset password",
            "Login failed username password recovery",
            "Where is my package and delivery tracking status",
            "Track order shipping carrier status delayed",
            "I want a refund for defective damaged shirt",
            "Return refund item defective stain",
        ] * 10
        train_labels = [
            "flow:account_access", "flow:account_access",
            "flow:shipping_issue", "flow:shipping_issue",
            "flow:product_defect", "flow:product_defect",
        ] * 10

        clf = BaselineClassifier(C=1.0)
        self.assertTrue(clf.fit(train_texts, train_labels))

        preds, res_flags, rej_scores = clf.predict_with_rejection(
            ["I cannot login password", "completely strange text from alien planet"],
            q=0.50
        )
        self.assertEqual(preds[0], "flow:account_access")
        self.assertFalse(res_flags[0])

        # Strange text should be rejected or have low probability
        self.assertTrue(res_flags[1] or rej_scores[1] > 0.3)

        # Search grid on synthetic dev
        dev_texts = train_texts[:12]
        dev_labels = train_labels[:12]
        known_classes = ["flow:account_access", "flow:product_defect"]
        res_grid = search_baseline_grid(
            train_texts=train_texts,
            train_labels=train_labels,
            dev_texts=dev_texts,
            dev_labels=dev_labels,
            known_classes=known_classes,
            hidden_dev_class="flow:shipping_issue",
            c_grid=(0.1, 1.0),
            q_grid=(0.35, 0.50)
        )
        self.assertIn('best_configuration', res_grid)
        self.assertTrue(len(res_grid['all_evaluations']) > 0)


    def test_search_similarity_grid_and_fallback(self):
        from bertopic_poc.search import generate_parent_grid, search_similarity_grid
        grid = generate_parent_grid()
        self.assertEqual(len(grid), 52)
        self.assertEqual(grid[0], (0.20, 0.0))
        self.assertEqual(grid[-1], (0.80, 0.15))

        # Synthetic dev scores for 4 conversations: 2 known, 2 hidden
        dev_scores = [
            # Conv 0: strong known
            [{'flow:account_access': 0.85, 'flow:order_issue': 0.40}],
            # Conv 1: weak/ambiguous known
            [{'flow:account_access': 0.52, 'flow:order_issue': 0.50}],
            # Conv 2: hidden flow (unmatched against known)
            [{'flow:account_access': 0.30, 'flow:order_issue': 0.25}],
            # Conv 3: hidden flow
            [{'flow:account_access': 0.35, 'flow:order_issue': 0.20}],
        ]
        dev_meta = [
            [{'evidence_unit_id': f'u_{i}', 'conversation_id': f'c_{i}', 'customer_turn_index': 0,
              'span_start': 0, 'span_end': 10, 'content_status': 'analyzable'}]
            for i in range(4)
        ]
        dev_labels = [
            'flow:account_access', 'flow:account_access',
            'flow:shipping_issue', 'flow:shipping_issue'
        ]
        known_classes = ['flow:account_access', 'flow:order_issue']

        res = search_similarity_grid(
            dev_units_scores=dev_scores,
            dev_unit_metadata=dev_meta,
            dev_labels=dev_labels,
            known_classes=known_classes,
            hidden_dev_flow='flow:shipping_issue',
            grid=grid
        )
        self.assertIn('best_configuration', res)
        self.assertIn('tau', res['best_configuration'])
        self.assertIn('delta', res['best_configuration'])
        self.assertEqual(len(res['all_evaluations']), 52)


if __name__ == '__main__':
    unittest.main()
