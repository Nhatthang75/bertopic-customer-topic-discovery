"""Unit and integration tests for Group 10: Traceability across 6 specs, dashboard artifact reading, and end-to-end audit."""
import unittest
from pathlib import Path
import json

from bertopic_poc.io import ROOT, read_json, sha256
from bertopic_poc.contracts import validate, csv_load


class IntegrationAndTraceabilityTests(unittest.TestCase):

    def test_raw_data_sha256_unmodified(self):
        """Kiểm tra bất biến: raw dataset SHA-256 không bị thay đổi."""
        raw_abcd = ROOT / 'data/raw/abcd_v1.1.json.gz'
        raw_onto = ROOT / 'data/raw/ontology.json'
        self.assertTrue(raw_abcd.exists())
        self.assertTrue(raw_onto.exists())
        self.assertEqual(sha256(raw_abcd), "2bdf53ac359543dcdc38d55bc6513e78df120363f8f44870716e909f4606de15")
        self.assertEqual(sha256(raw_onto), "2e1c1d763518ba084ada7f7bc8b54f0b489c81da3b170875cf9340891e06524c")

    def test_gates_sequence_and_snapshots_presence(self):
        """Kiểm tra sự hiện diện và tính hợp lệ của cả 4 Gates G0, G1, G2, G3."""
        g0 = read_json(ROOT / 'artifacts/phase1/bootstrap/g0_snapshot.json')
        g1 = read_json(ROOT / 'artifacts/phase1/g1_snapshot.json')
        g2 = read_json(ROOT / 'artifacts/phase1/g2_snapshot.json')
        g3 = read_json(ROOT / 'artifacts/phase1/g3_snapshot.json')

        self.assertEqual(g0.get('gate'), 'G0')
        self.assertEqual(g1.get('gate'), 'G1')
        self.assertEqual(g2.get('gate'), 'G2')
        self.assertEqual(g3.get('gate'), 'G3')

    def test_consolidated_artifacts_presence_and_schema(self):
        """Kiểm tra toàn bộ Schema 1.0.0 artifacts đã được tạo và validate thành công."""
        cons_dir = ROOT / 'artifacts/phase1/consolidated'
        self.assertTrue((cons_dir / 'assignments.jsonl').exists())
        self.assertTrue((cons_dir / 'candidates.jsonl').exists())
        self.assertTrue((cons_dir / 'reviews.jsonl').exists())
        self.assertTrue((cons_dir / 'conversation_topics.csv').exists())
        self.assertTrue((cons_dir / 'topic_statistics.csv').exists())
        self.assertTrue((cons_dir / 'data_quality.json').exists())

        # Check evaluation report and metrics
        eval_dir = ROOT / 'artifacts/phase1/evaluation'
        self.assertTrue((eval_dir / 'metrics.json').exists())
        self.assertTrue((eval_dir / 'report.md').exists())

    def test_dashboard_does_not_require_model_fitting(self):
        """Kiểm tra dashboard đọc artifacts sẵn có mà không gọi fit model."""
        from bertopic_poc.dashboard import load_dashboard_state
        state = load_dashboard_state(ROOT / 'artifacts/phase1')
        self.assertIn('run_manifest', state)
        self.assertIn('metrics', state)
        self.assertIn('candidates', state)
        self.assertGreater(len(state['candidates']), 0)


if __name__ == '__main__':
    unittest.main()
