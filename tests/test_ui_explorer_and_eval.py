"""Unit tests for Pages 4 & 5: Explorer, Offset Highlights, and Evaluation metrics."""
import unittest
from bertopic_poc.ui.data_loader import (
    get_default_artifacts_root,
    load_conversation_index,
    load_evaluation_metrics,
    load_report_markdown,
)
from bertopic_poc.ui.utils import highlight_evidence_span


class TestUIExplorerAndEval(unittest.TestCase):
    def setUp(self):
        self.artifacts_root = str(get_default_artifacts_root())

    def test_highlight_evidence_span_offsets(self):
        text = "Hello, I want to cancel my subscription please."
        # span for "cancel my subscription" is [17, 39]
        span_start = 17
        span_end = 39
        target = text[span_start:span_end]
        self.assertEqual(target, "cancel my subscription")

        highlighted = highlight_evidence_span(text, span_start, span_end, "human_verified")
        self.assertIn("<mark", highlighted)
        self.assertIn("cancel my subscription", highlighted)
        self.assertIn("Hello, I want to ", highlighted)
        self.assertIn(" please.", highlighted)
        self.assertIn("Human Verified", highlighted)

    def test_highlight_edge_cases(self):
        # Empty text
        self.assertEqual(highlight_evidence_span("", 0, 5), "")

        # None spans
        self.assertEqual(highlight_evidence_span("hello world", None, None), "hello world")

        # Invalid start/end
        self.assertEqual(highlight_evidence_span("hello world", 5, 2), "hello world")
        self.assertEqual(highlight_evidence_span("hello world", 20, 25), "hello world")

        # End beyond length clamps cleanly
        clamped = highlight_evidence_span("abc", 0, 10, "model_supported")
        self.assertIn("abc", clamped)

    def test_conversation_index_pagination_math(self):
        conv_idx = load_conversation_index(self.artifacts_root)
        total = len(conv_idx)
        self.assertGreater(total, 0)

        for page_size in [10, 25, 50]:
            total_pages = (total + page_size - 1) // page_size
            self.assertGreater(total_pages, 0)
            
            # First page slice
            p1 = conv_idx.iloc[0:min(page_size, total)]
            self.assertEqual(len(p1), min(page_size, total))

    def test_evaluation_confirmatory_kpis(self):
        metrics = load_evaluation_metrics(self.artifacts_root)
        
        # Macro F1
        self.assertAlmostEqual(metrics.get("closed_macro_f1"), 0.5553, places=3)
        # Unknown F1
        self.assertAlmostEqual(metrics.get("unknown_f1"), 0.3618, places=3)
        # Routing Recall
        self.assertEqual(metrics.get("routing_recall"), 1.0)
        # Recovered flows proxy
        self.assertEqual(metrics.get("recovered_flows_proxy"), 2)

    def test_flow_family_recovery_matrix(self):
        metrics = load_evaluation_metrics(self.artifacts_root)
        sem_rec = metrics.get("semantic_recovery", {})
        
        self.assertIn("subscription_inquiry", sem_rec)
        self.assertIn("troubleshoot_site", sem_rec)
        
        sub = sem_rec["subscription_inquiry"]
        site = sem_rec["troubleshoot_site"]
        
        self.assertTrue(sub.get("proxy_recovered"))
        self.assertTrue(sub.get("semantic_supported"))
        self.assertGreater(len(sub.get("qualifying_clusters", [])), 0)

        self.assertTrue(site.get("proxy_recovered"))
        self.assertTrue(site.get("semantic_supported"))
        self.assertGreater(len(site.get("qualifying_clusters", [])), 0)

    def test_clustering_stability_ari_ranges(self):
        metrics = load_evaluation_metrics(self.artifacts_root)
        stability = metrics.get("stability", {})
        
        s42_13 = stability.get("seed42_vs_13", {})
        s42_73 = stability.get("seed42_vs_73", {})
        
        # ARI ~ 0.21 - 0.24
        self.assertAlmostEqual(s42_13.get("ARI_all"), 0.2105, places=3)
        self.assertAlmostEqual(s42_73.get("ARI_all"), 0.2354, places=3)
        self.assertFalse(s42_13.get("degenerate"))
        self.assertFalse(s42_73.get("degenerate"))

    def test_report_markdown_content(self):
        report = load_report_markdown(self.artifacts_root)
        self.assertIn("Báo Cáo Đánh Giá Chất Lượng BERTopic Customer Conversation PoC", report)
        self.assertIn("Tóm Tắt Trạng Thái Nghiệm Thu", report)
        self.assertIn("PASS", report)
        self.assertIn("HUMAN_VERIFIED", report)
        self.assertIn("VALID", report)


if __name__ == "__main__":
    unittest.main()
