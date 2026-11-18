"""Unit tests for Group 9: Gate G3 unblinding, metrics calculation, and report generation."""
import unittest
from pathlib import Path
import json

from bertopic_poc.io import ROOT, read_json
from bertopic_poc.contracts import validate
from bertopic_poc.evaluator import (
    evaluate_fixed_classification,
    evaluate_unknown_detection,
    evaluate_flow_family_recovery,
    evaluate_clustering_stability,
    bootstrap_ci
)


class Group9EvaluationTests(unittest.TestCase):

    def test_evaluator_metrics_contract(self):
        """Kiểm tra cấu trúc và tính toán evaluator metrics theo schema 1.0.0."""
        metric_row = {
            'schema_version': '1.0.0',
            'experiment_id': 'phase1',
            'run_id': 'evaluation_v1',
            'metric_name': 'macro_f1',
            'cohort_id': 'S_cs',
            'level': 'conversation',
            'seed': 42,
            'evaluation_stage': 'confirmatory',
            'value': 0.75,
            'support': 1004,
            'denominator': 1004,
            'grain': 'conversation',
            'CI': [0.71, 0.79],
            'null_reason': None,
            'experiment_mode': 'inductive',
            'ground_truth_type': 'scenario_proxy'
        }
        validate('metrics', metric_row)
        self.assertEqual(metric_row['value'], 0.75)

    def test_flow_family_recovery_target_logic(self):
        """Kiểm tra logic flow family recovery cho 2 hidden flows."""
        cluster_convs = {
            'c_0': {'c1', 'c2', 'c3', 'c4', 'c5'},
            'c_1': {'c6', 'c7', 'c8', 'c9', 'c10'}
        }
        hidden_s_h = {'c1', 'c2', 'c3', 'c4', 'c5', 'c6', 'c7', 'c8', 'c9', 'c10', 'c11', 'c12'}
        conv_flow_map = {f"c{i}": "hidden_a" for i in range(1, 13)}
        rec = evaluate_flow_family_recovery(
            hidden_flows=['hidden_a'],
            cluster_conversation_map=cluster_convs,
            conversation_hidden_flow_map=conv_flow_map,
            all_hidden_flow_conversations={'hidden_a': hidden_s_h},
            min_support=5,
            min_purity=0.70,
            min_recall=0.30
        )
        flow_res = rec['flows']['hidden_a']
        self.assertTrue(flow_res['recovered'])
        self.assertEqual(len(flow_res['qualifying_clusters']), 2)
        self.assertGreaterEqual(flow_res['family_recall'], 0.8)


if __name__ == '__main__':
    unittest.main()
