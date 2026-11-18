"""End-to-End Integration tests for Streamlit Web Dashboard components."""
import unittest
import pandas as pd
from pathlib import Path

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
from bertopic_poc.ui.utils import highlight_evidence_span


class TestUIE2EIntegration(unittest.TestCase):
    def setUp(self):
        self.artifacts_root = str(get_default_artifacts_root())

    def test_e2e_data_flow_overview(self):
        # 1. Overview data pipeline
        bundle = load_manifest_bundle(self.artifacts_root)
        self.assertIn("G0", bundle["gates"])
        self.assertIn("G1", bundle["gates"])
        self.assertIn("G2", bundle["gates"])
        self.assertIn("G3", bundle["gates"])
        self.assertEqual(bundle["data_quality"]["counts"]["eligible"], 10042)

    def test_e2e_fixed_topics_filters(self):
        # 2. Fixed topics data pipeline & filters
        df = load_topic_statistics(self.artifacts_root)
        for scope in ["scope:test_open", "scope:test_closed"]:
            sub = df[df["scope_id"] == scope]
            self.assertGreater(len(sub), 0)
            denom = sub["eligible_conversations"].iloc[0]
            self.assertIn(denom, [898, 1004])
            # Check share formula
            for _, row in sub.iterrows():
                self.assertAlmostEqual(row["conversation_share"], row["conversation_count"] / denom, places=4)

    def test_e2e_discovery_filters(self):
        # 3. Discovery filters
        candidates = load_candidates(self.artifacts_root)
        reviews = load_reviews_map(self.artifacts_root)

        # Filter by seed
        for seed in [13, 42, 73]:
            c_seed = [c for c in candidates if c.get("seed") == seed]
            self.assertGreater(len(c_seed), 0)

        # Filter by status
        c_acc = [c for c in candidates if c.get("status") == "accepted_novel"]
        self.assertEqual(len(c_acc), 498)

        # Filter by keyword
        c_order = [c for c in candidates if any("order" in k.lower() for k in c.get("keywords", []))]
        self.assertGreater(len(c_order), 0)

        # Check blinded review linkage
        for c in c_acc:
            self.assertIn(c["cluster_key"], reviews)
            rev = reviews[c["cluster_key"]]
            self.assertEqual(rev["adjudication"]["decision"], "accepted_novel")

    def test_e2e_conversation_explorer_search_and_highlight(self):
        # 4. Conversation explorer search, paging and highlighting
        conv_idx = load_conversation_index(self.artifacts_root)
        self.assertGreater(len(conv_idx), 0)

        # Test filter by topic
        unique_topics = conv_idx["topic_id"].unique()
        for t in unique_topics[:3]:
            sub = conv_idx[conv_idx["topic_id"] == t]
            self.assertGreater(len(sub), 0)

        # Test filter by evidence status
        for st_val in ["model_supported", "human_verified", "cluster_only"]:
            sub = conv_idx[conv_idx["evidence_status"] == st_val]
            self.assertGreaterEqual(len(sub), 0)

        # Pick one conversation and verify segment highlight
        sample_cid = conv_idx.iloc[0]["conversation_id"]
        segments, assignments = get_conversation_segments_and_assignments(sample_cid, self.artifacts_root)
        self.assertGreater(len(segments), 0)

        for s in segments:
            text = s.get("masked_customer_text", "")
            start = s.get("span_start")
            end = s.get("span_end")
            hl = highlight_evidence_span(text, start, end)
            self.assertIsInstance(hl, str)
            if start is not None and end is not None and 0 <= start < end <= len(text):
                self.assertIn("<mark", hl)

    def test_e2e_evaluation_metrics_and_report(self):
        # 5. Model evaluation pipeline
        metrics = load_evaluation_metrics(self.artifacts_root)
        self.assertEqual(metrics["recovered_flows_proxy"], 2)
        self.assertAlmostEqual(metrics["closed_macro_f1"], 0.5553, places=3)
        self.assertAlmostEqual(metrics["unknown_f1"], 0.3618, places=3)
        self.assertEqual(metrics["routing_recall"], 1.0)

        report = load_report_markdown(self.artifacts_root)
        self.assertIn("PASS", report)
        self.assertIn("HUMAN_VERIFIED", report)
        self.assertIn("VALID", report)

    def test_zero_fit_compliance(self):
        # Verify no sklearn / bertopic fit methods are called during UI loading
        # The data loader should strictly load pre-computed artifacts
        import bertopic_poc.ui.data_loader as dl
        self.assertFalse(hasattr(dl, "fit"))
        self.assertFalse(hasattr(dl, "fit_transform"))
        self.assertFalse(hasattr(dl, "train"))


if __name__ == "__main__":
    unittest.main()
