"""Unit tests for Page 1 Overview logic."""
import unittest
from pathlib import Path
from bertopic_poc.ui.data_loader import (
    get_default_artifacts_root,
    load_manifest_bundle,
    load_candidates,
    load_topic_statistics,
)


class TestUIOverview(unittest.TestCase):
    def setUp(self):
        self.artifacts_root = str(get_default_artifacts_root())

    def test_overview_data_completeness(self):
        bundle = load_manifest_bundle(self.artifacts_root)
        self.assertIn("manifest", bundle)
        self.assertIn("gates", bundle)
        self.assertIn("data_quality", bundle)

        dq = bundle["data_quality"]
        counts = dq.get("counts", {})
        self.assertEqual(counts.get("eligible"), 10042)

        unresolved = dq.get("unresolved_counts", {}).get("content_status", {})
        total_segments = sum(unresolved.values())
        self.assertEqual(total_segments, 103901)

    def test_gates_progression_structure(self):
        bundle = load_manifest_bundle(self.artifacts_root)
        gates = bundle["gates"]
        for gid in ["G0", "G1", "G2", "G3"]:
            self.assertIn(gid, gates)
            self.assertEqual(gates[gid].get("gate"), gid)

        # G1 locked configuration
        g1_cfg = gates["G1"].get("locked_configuration", {})
        self.assertEqual(g1_cfg.get("model_id"), "sentence-transformers/all-MiniLM-L6-v2")
        self.assertIn("discovery_configuration", g1_cfg)
        self.assertIn("parent_thresholds", g1_cfg)
        self.assertIn("child_thresholds", g1_cfg)

        # G2 locked outputs
        self.assertIn("locked_outputs", gates["G2"])

        # G3 unblind status
        self.assertEqual(gates["G3"].get("status"), "unblind_authorized_for_evaluator")

    def test_candidate_counts(self):
        candidates = load_candidates(self.artifacts_root)
        self.assertEqual(len(candidates), 1552)

    def test_topic_statistics_scopes(self):
        df = load_topic_statistics(self.artifacts_root)
        scopes = set(df["scope_id"].unique())
        self.assertIn("scope:test_open", scopes)
        self.assertIn("scope:test_closed", scopes)


if __name__ == "__main__":
    unittest.main()
