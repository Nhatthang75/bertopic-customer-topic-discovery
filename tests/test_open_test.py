"""Unit tests for Gate G1, open test inference, discovery runs, and Gate G2."""
import unittest
from pathlib import Path
import json

from bertopic_poc.io import ROOT, read_json
from bertopic_poc.contracts import validate
from bertopic_poc.discovery import build_cluster_candidates, validate_merge_dag
from bertopic_poc.rubric import select_review_samples, evaluate_rubric_adjudication


class OpenTestAndGatesTests(unittest.TestCase):

    def test_g1_configuration_integrity(self):
        """Kiểm tra cấu hình G1 phải chứa đúng các tham số đã chọn từ dev search."""
        model_sel = read_json(ROOT / 'artifacts/phase1/model_selection.json')
        disc_sel = read_json(ROOT / 'artifacts/phase1/discovery_selection.json')

        self.assertEqual(model_sel['winning_model'], 'sentence-transformers/all-MiniLM-L6-v2')
        self.assertEqual(model_sel['parent_thresholds']['tau'], 0.20)
        self.assertEqual(model_sel['parent_thresholds']['delta'], 0.05)
        self.assertEqual(model_sel['child_thresholds']['tau_child'], 0.50)
        self.assertEqual(model_sel['child_thresholds']['delta_child'], 0.10)

        best_disc = disc_sel['best_configuration']
        self.assertEqual(best_disc['n_neighbors'], 5)
        self.assertEqual(best_disc['n_components'], 5)
        self.assertEqual(best_disc['min_cluster_size'], 5)
        self.assertEqual(best_disc['min_samples'], 1)

    def test_blinded_review_sampling_and_adjudication(self):
        """Kiểm tra việc lấy mẫu 5 representative + 5 random không trùng conversation và adjudication rubric."""
        units = []
        for i in range(12):
            units.append({
                'evidence_unit_id': f'u_{i}',
                'conversation_id': f'c_{i}',
                'text': f'Sample customer complaint text number {i}',
                'distance_to_centroid': 0.1 * i
            })
        samples = select_review_samples(units, seed=42)
        rep = samples['representative_unit_ids']
        rand = samples['random_unit_ids']
        self.assertLessEqual(len(rep), 5)
        self.assertLessEqual(len(rand), 5)
        # Check no conversation overlap between representative and random
        rep_convs = {u['conversation_id'] for u in units if u['evidence_unit_id'] in rep}
        rand_convs = {u['conversation_id'] for u in units if u['evidence_unit_id'] in rand}
        self.assertTrue(rep_convs.isdisjoint(rand_convs))

        # Test rubric scoring
        rev1 = {'coherence': 2, 'novelty': 2}
        rev2 = {'coherence': 2, 'novelty': 2}
        status, scores = evaluate_rubric_adjudication(
            support_conversations=10,
            reviewer1_scores=rev1,
            reviewer2_scores=rev2
        )
        self.assertEqual(status, 'accepted_novel')
        self.assertEqual(scores['coherence'], 2)
        self.assertEqual(scores['novelty'], 2)

    def test_merge_dag_prevents_cycles(self):
        """Kiểm tra merge DAG validator phát hiện cycle và target không hợp lệ."""
        current_candidates = {'cand_1', 'cand_2', 'cand_3'}
        known_topics = {'flow:refund_item'}
        merges = [('cand_1', 'cand_2')]
        is_valid, _ = validate_merge_dag(merges, current_candidates, known_topics)
        self.assertTrue(is_valid)

        # Cycle: cand_1 -> cand_2 -> cand_1
        cycle_merges = [('cand_1', 'cand_2'), ('cand_2', 'cand_1')]
        is_valid_cycle, reason = validate_merge_dag(cycle_merges, current_candidates, known_topics)
        self.assertFalse(is_valid_cycle)
        self.assertIn('cycle_detected', reason)


if __name__ == '__main__':
    unittest.main()
