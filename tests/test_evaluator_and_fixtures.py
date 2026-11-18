import unittest
from bertopic_poc.evaluator import (
    evaluate_decision_table, evaluate_fixed_classification, evaluate_unknown_detection,
    evaluate_flow_family_recovery, evaluate_clustering_stability, bootstrap_ci
)
from bertopic_poc.rubric import select_review_samples, evaluate_rubric_adjudication
from bertopic_poc.policy import AccessPolicy, LeakageError


class EvaluatorAndFixturesTests(unittest.TestCase):
    def test_decision_table_fixtures(self):
        # 1. Unmatched (s1 < tau=0.50)
        self.assertEqual(evaluate_decision_table(0.49, 0.20, tau=0.50, delta=0.10), 'unmatched')

        # 2. Ambiguous (s1 >= tau, but margin < delta=0.10)
        # e.g., shipping_issue=0.76, order_issue=0.73 (margin=0.03 < 0.10)
        self.assertEqual(evaluate_decision_table(0.76, 0.73, tau=0.50, delta=0.10), 'ambiguous')

        # 3. Accepted at boundary (s1=0.60, s2=0.50, margin=0.10 >= 0.10)
        self.assertEqual(evaluate_decision_table(0.60, 0.50, tau=0.50, delta=0.10), 'accepted')

        # 4. Accepted clear winner
        # e.g. account_access=0.80, top2=0.55
        self.assertEqual(evaluate_decision_table(0.80, 0.55, tau=0.50, delta=0.10), 'accepted')

    def test_fixed_classification_and_abstain_is_fn(self):
        classes = ['flow:account_access', 'flow:product_defect']
        # 2 samples: 1 correct, 1 abstain (None) for account_access
        preds = ['flow:account_access', None]
        gt = ['flow:account_access', 'flow:account_access']

        res = evaluate_fixed_classification(preds, gt, classes)
        # account_access has 1 TP, 1 FN -> recall=0.5, prec=1.0, f1=0.66666667
        self.assertEqual(res['per_class']['flow:account_access']['recall'], 0.5)
        self.assertEqual(res['per_class']['flow:account_access']['precision'], 1.0)
        self.assertEqual(res['accuracy'], 0.5)

    def test_unknown_detection_metrics(self):
        # residual_flags (prediction positive for unknown), is_hidden (ground truth)
        residual = [True, True, False, False]
        is_hidden = [True, False, True, False]
        # TP=1, FP=1, FN=1, TN=1
        res = evaluate_unknown_detection(residual, is_hidden, decision_scores=[0.8, 0.6, None, 0.2])
        self.assertEqual(res['precision'], 0.5)
        self.assertEqual(res['recall'], 0.5)
        self.assertEqual(res['f1'], 0.5)
        self.assertEqual(res['score_coverage'], 0.75)

    def test_flow_family_recovery_fixture(self):
        # Fixture from Design §8:
        # Two clusters, each support=10, purity=1.0 for flow h, overlapping 2 conversations.
        # S_h total conversations = 50.
        # Union size = 18. Precision = 18/18 = 1.0. Recall = 18/50 = 0.36.
        # Result: recovered_proxy=True even though each cluster alone only has recall = 10/50 = 0.20 (< 0.30)!
        hidden_flow = 'subscription_inquiry'
        s_h = {f"c_{i}" for i in range(50)}

        # Cluster 1: c_0 to c_9 (10 convs)
        c1 = {f"c_{i}" for i in range(10)}
        # Cluster 2: c_8 to c_17 (10 convs, c_8 and c_9 overlap with c1)
        c2 = {f"c_{i}" for i in range(8, 18)}

        cluster_map = {'cluster_1': c1, 'cluster_2': c2}
        conv_flow_map = {cid: hidden_flow for cid in s_h}

        res = evaluate_flow_family_recovery(
            hidden_flows=[hidden_flow],
            cluster_conversation_map=cluster_map,
            conversation_hidden_flow_map=conv_flow_map,
            all_hidden_flow_conversations={hidden_flow: s_h},
            min_support=5,
            min_purity=0.70,
            min_recall=0.30
        )

        flow_res = res['flows'][hidden_flow]
        self.assertTrue(flow_res['recovered'])
        self.assertEqual(flow_res['family_precision'], 1.0)
        self.assertEqual(flow_res['family_recall'], 0.36)
        self.assertEqual(len(flow_res['qualifying_clusters']), 2)

    def test_clustering_stability_and_degenerate(self):
        # 1. Normal stability
        a = [0, 0, 1, 1, -1]
        b = [1, 1, 0, 0, -1]
        res = evaluate_clustering_stability(a, b)
        self.assertFalse(res['degenerate'])
        self.assertEqual(res['ARI_shared'], 1.0)

        # 2. Degenerate all outliers
        all_outliers = [-1, -1, -1, -1]
        res_deg = evaluate_clustering_stability(all_outliers, all_outliers)
        self.assertTrue(res_deg['degenerate'])
        self.assertEqual(res_deg['null_reason'], 'degenerate_all_outliers')

    def test_bootstrap_ci_conversation_level(self):
        vals = [0.70, 0.72, 0.68, 0.75, 0.71, 0.69]
        ci = bootstrap_ci(vals, n_replicates=500, seed=42)
        self.assertIsNotNone(ci)
        low, high = ci
        self.assertTrue(low <= high)
        self.assertTrue(0.65 <= low <= 0.75)

    def test_rubric_and_sample_selection(self):
        units = [
            {'conversation_id': f'c_{i}', 'evidence_unit_id': f'u_{i}', 'distance_to_centroid': float(i)}
            for i in range(12)
        ]
        sel = select_review_samples(units, seed=42, run_id='r1', cluster_key='cl_0')
        # Representative takes closest 5 distinct conversations (c_0 to c_4)
        self.assertEqual(len(sel['representative_unit_ids']), 5)
        # Random takes next 5 from remaining (c_5 to c_9)
        self.assertEqual(len(sel['random_unit_ids']), 5)
        # Total distinct conversations sampled
        all_samples = sel['all_sample_ids']
        self.assertEqual(len(all_samples), 10)
        self.assertEqual(len(set(all_samples)), 10)

        # Adjudication
        status, scores = evaluate_rubric_adjudication(
            support_conversations=10,
            reviewer1_scores={'coherence': 2, 'novelty': 2},
            reviewer2_scores={'coherence': 2, 'novelty': 2}
        )
        self.assertEqual(status, 'accepted_novel')

        # Merged known
        status_m, _ = evaluate_rubric_adjudication(
            support_conversations=10,
            reviewer1_scores={'coherence': 2, 'novelty': 0},
            reviewer2_scores={'coherence': 2, 'novelty': 0},
            target_known_topic='flow:manage_account'
        )
        self.assertEqual(status_m, 'merged')

    def test_leakage_and_audit_fixtures(self):
        # 1. Early label access by inference -> LeakageError
        p1 = AccessPolicy()
        with self.assertRaises(LeakageError):
            p1.authorize('inference', 'sealed_labels', 'inference')

        # 2. Custodian scoring purpose -> LeakageError
        p2 = AccessPolicy()
        with self.assertRaises(LeakageError):
            p2.authorize('custodian', 'sealed_labels', 'scoring')

        # 3. Hidden full taxonomy before G2 -> LeakageError
        p3 = AccessPolicy(gate=1)
        with self.assertRaises(LeakageError):
            p3.authorize('reviewer', 'taxonomy_full', 'review')

        # 4. Reviewer not blinded -> LeakageError
        p4 = AccessPolicy(gate=2)
        with self.assertRaises(LeakageError):
            p4.authorize('reviewer', 'features', 'review', blinded=False)


if __name__ == '__main__':
    unittest.main()
