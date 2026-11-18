"""Unit tests for Page 3 New Topic Discovery."""
import unittest
from bertopic_poc.ui.data_loader import (
    get_default_artifacts_root,
    load_candidates,
    load_reviews_map,
)


class TestUIDiscovery(unittest.TestCase):
    def setUp(self):
        self.artifacts_root = str(get_default_artifacts_root())
        self.candidates = load_candidates(self.artifacts_root)
        self.reviews_map = load_reviews_map(self.artifacts_root)

    def test_candidates_total_and_seeds(self):
        self.assertEqual(len(self.candidates), 1552)

        seeds = {c.get("seed") for c in self.candidates}
        self.assertEqual(seeds, {13, 42, 73})

        cands_42 = [c for c in self.candidates if c.get("seed") == 42]
        cands_13 = [c for c in self.candidates if c.get("seed") == 13]
        cands_73 = [c for c in self.candidates if c.get("seed") == 73]

        self.assertEqual(len(cands_42), 505)
        self.assertEqual(len(cands_13), 530)
        self.assertEqual(len(cands_73), 517)

    def test_blinded_review_10_samples_and_rubric(self):
        self.assertGreater(len(self.reviews_map), 0)

        for cluster_key, rev in self.reviews_map.items():
            # Up to 10 sample ids (5 to 10 depending on cluster size)
            samples = rev.get("sample_ids", [])
            self.assertGreaterEqual(len(samples), 5)
            self.assertLessEqual(len(samples), 10)

            # Rubric 2 reviewers
            rubric = rev.get("rubric_scores", {})
            self.assertIn("reviewer_1", rubric)
            self.assertIn("reviewer_2", rubric)
            for rev_id in ["reviewer_1", "reviewer_2"]:
                self.assertIn("coherence", rubric[rev_id])
                self.assertIn("novelty", rubric[rev_id])

            # Adjudication
            adj = rev.get("adjudication", {})
            self.assertIn(adj.get("decision"), ["accepted_novel", "monitor"])

            # No ground-truth label leakage in review
            self.assertNotIn("ground_truth", rev)
            self.assertNotIn("true_flow", rev)

    def test_merge_dag_acyclicity(self):
        # Build adjacency list from reviews target_id
        adj = {}
        for k, rev in self.reviews_map.items():
            target = rev.get("target_id")
            if target:
                adj[k] = target

        # Verify no self-loops or cycles
        visited = set()
        for node in adj:
            curr = node
            path = []
            while curr in adj:
                self.assertNotIn(curr, path, f"Cycle detected involving {curr}")
                path.append(curr)
                curr = adj[curr]


if __name__ == "__main__":
    unittest.main()
