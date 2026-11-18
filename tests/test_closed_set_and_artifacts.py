"""Unit tests for Group 8: Closed-set classification, threshold selection, and consolidated artifacts."""
import unittest
from pathlib import Path
import json

from bertopic_poc.io import ROOT, read_json
from bertopic_poc.contracts import validate, csv_dump, csv_load, BASE, FIELDS
from bertopic_poc.taxonomy import FLOW_SUBFLOW_CANONICAL, FLOW_DESCRIPTIONS_EN, flow_id
from bertopic_poc.cohorts import build_topic_statistics, StatisticsScope


class ClosedSetAndArtifactsTests(unittest.TestCase):

    def test_full_10_flow_taxonomy_and_descriptions(self):
        """Kiểm tra đủ 10 flows và mô tả cho closed-set sau Gate G2."""
        self.assertEqual(len(FLOW_SUBFLOW_CANONICAL), 10)
        self.assertEqual(len(FLOW_DESCRIPTIONS_EN), 10)
        for f in FLOW_SUBFLOW_CANONICAL:
            self.assertIn(f, FLOW_DESCRIPTIONS_EN)
            self.assertTrue(len(FLOW_DESCRIPTIONS_EN[f]) > 20)

    def test_topic_statistics_csv_schema_and_rfc4180(self):
        """Kiểm tra topic_statistics tuân thủ schema 1.0.0 và RFC4180 null token \\N."""
        scope = StatisticsScope(
            scope_id="test_scope",
            eligible_conversation_ids={f"conv_{i}" for i in range(100)},
            total_customer_messages=250
        )
        fake_assignments = [
            {
                'conversation_id': f"conv_{i}",
                'topic_id': 'flow:order_issue',
                'customer_turn_index': 0,
                'evidence_status': 'model_supported'
            }
            for i in range(20)
        ]
        row = build_topic_statistics(
            scope=scope,
            topic_id="flow:order_issue",
            source="fixed",
            evidence_basis="predicted",
            assignments=fake_assignments
        )
        validate('topic_statistics', row)
        self.assertEqual(row['conversation_share'], 0.2)

        # CSV serialization test
        fieldnames = list(BASE.keys()) + list(FIELDS['topic_statistics'].keys())
        csv_text = csv_dump([row], fieldnames)
        self.assertIn("\\N", csv_text)  # Optional null fields must be \N

        loaded = csv_load(csv_text)
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0]['topic_id'], 'flow:order_issue')
        self.assertIsNone(loaded[0]['time_bucket'])


if __name__ == '__main__':
    unittest.main()
