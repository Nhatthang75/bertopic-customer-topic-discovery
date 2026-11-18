"""Unit tests for bertopic_poc.ui.data_loader."""
import unittest
from pathlib import Path
import tempfile
import json
import pandas as pd

from bertopic_poc.ui.data_loader import (
    get_default_artifacts_root,
    load_manifest_bundle,
    load_topic_statistics,
    load_candidates,
    load_reviews_map,
    load_evaluation_metrics,
    load_report_markdown,
    load_conversation_index,
    get_conversation_segments_and_assignments,
)


class TestUIDataLoader(unittest.TestCase):
    def setUp(self):
        self.artifacts_root = str(get_default_artifacts_root())

    def test_load_manifest_bundle(self):
        bundle = load_manifest_bundle(self.artifacts_root)
        self.assertIn("manifest", bundle)
        self.assertIn("gates", bundle)
        self.assertEqual(bundle["experiment_id"], "phase1")
        self.assertEqual(bundle["winning_model"], "sentence-transformers/all-MiniLM-L6-v2")
        self.assertIn("valid", bundle["benchmark_validity"])
        # Verify 4 gates present
        for g in ["G0", "G1", "G2", "G3"]:
            self.assertIn(g, bundle["gates"])

    def test_load_topic_statistics(self):
        df = load_topic_statistics(self.artifacts_root)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertGreater(len(df), 0)
        self.assertIn("scope_id", df.columns)
        self.assertIn("topic_id", df.columns)
        self.assertIn("conversation_count", df.columns)
        self.assertIn("conversation_share", df.columns)

    def test_load_candidates(self):
        cands = load_candidates(self.artifacts_root)
        self.assertIsInstance(cands, list)
        self.assertEqual(len(cands), 1552)
        sample = cands[0]
        self.assertIn("cluster_key", sample)
        self.assertIn("seed", sample)
        self.assertIn("keywords", sample)

    def test_load_reviews_map(self):
        reviews = load_reviews_map(self.artifacts_root)
        self.assertIsInstance(reviews, dict)
        self.assertGreater(len(reviews), 0)
        # Check first review format
        first_key = next(iter(reviews.keys()))
        review = reviews[first_key]
        self.assertIn("adjudication", review)
        self.assertIn("rubric_scores", review)

    def test_load_evaluation_metrics(self):
        metrics = load_evaluation_metrics(self.artifacts_root)
        self.assertIn("closed_macro_f1", metrics)
        self.assertIn("unknown_f1", metrics)
        self.assertIn("routing_recall", metrics)
        self.assertEqual(metrics["recovered_flows_proxy"], 2)

    def test_load_report_markdown(self):
        report = load_report_markdown(self.artifacts_root)
        self.assertIsInstance(report, str)
        self.assertIn("Báo Cáo Đánh Giá Chất Lượng BERTopic Customer Conversation PoC", report)

    def test_load_conversation_index(self):
        conv_idx = load_conversation_index(self.artifacts_root)
        self.assertIsInstance(conv_idx, pd.DataFrame)
        self.assertGreater(len(conv_idx), 0)
        self.assertIn("conversation_id", conv_idx.columns)
        self.assertIn("topic_id", conv_idx.columns)
        self.assertIn("evidence_status", conv_idx.columns)

    def test_missing_files_error_handling(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Calling on empty directory should raise FileNotFoundError cleanly
            with self.assertRaises(FileNotFoundError):
                load_manifest_bundle(tmp_dir)
            with self.assertRaises(FileNotFoundError):
                load_topic_statistics(tmp_dir)
            with self.assertRaises(FileNotFoundError):
                load_candidates(tmp_dir)
            with self.assertRaises(FileNotFoundError):
                load_reviews_map(tmp_dir)
            with self.assertRaises(FileNotFoundError):
                load_evaluation_metrics(tmp_dir)
            with self.assertRaises(FileNotFoundError):
                load_report_markdown(tmp_dir)
            with self.assertRaises(FileNotFoundError):
                load_conversation_index(tmp_dir)

    def test_get_conversation_segments_and_assignments(self):
        # Pick one valid conversation id from conversation index
        conv_idx = load_conversation_index(self.artifacts_root)
        sample_cid = conv_idx.iloc[0]["conversation_id"]
        segments, assignments = get_conversation_segments_and_assignments(sample_cid, self.artifacts_root)
        self.assertIsInstance(segments, list)
        self.assertIsInstance(assignments, list)
        if segments:
            # Masked text exists and does not leak unmasked customer identity
            self.assertIn("masked_customer_text", segments[0])


if __name__ == "__main__":
    unittest.main()
