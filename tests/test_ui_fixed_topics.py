"""Unit tests for Page 2 Fixed Topic Analytics."""
import unittest
import pandas as pd
from bertopic_poc.ui.data_loader import (
    get_default_artifacts_root,
    load_topic_statistics,
)


class TestUIFixedTopics(unittest.TestCase):
    def setUp(self):
        self.artifacts_root = str(get_default_artifacts_root())
        self.df = load_topic_statistics(self.artifacts_root)

    def test_scope_separation(self):
        df_open = self.df[self.df["scope_id"] == "scope:test_open"]
        df_closed = self.df[self.df["scope_id"] == "scope:test_closed"]

        # 7 flows in open test, 10 flows in closed test
        self.assertEqual(len(df_open), 7)
        self.assertEqual(len(df_closed), 10)

        # Denominators
        self.assertEqual(df_open["eligible_conversations"].iloc[0], 898)
        self.assertEqual(df_closed["eligible_conversations"].iloc[0], 1004)

    def test_conversation_share_formula(self):
        for _, row in self.df.iterrows():
            expected_share = row["conversation_count"] / row["eligible_conversations"]
            self.assertAlmostEqual(row["conversation_share"], expected_share, places=4)

    def test_fixed_denominator_when_filtering(self):
        # Filtering should not change the denominator eligible_conversations
        df_open = self.df[self.df["scope_id"] == "scope:test_open"]
        top_2_topics = df_open.head(2)

        for _, row in top_2_topics.iterrows():
            self.assertEqual(row["eligible_conversations"], 898)
            # Share should still be relative to 898, not sum of top 2
            self.assertAlmostEqual(row["conversation_share"], row["conversation_count"] / 898, places=4)

    def test_honest_null_metadata(self):
        # Verify unique_customers, time_bucket, channel are null or empty
        for col in ["unique_customers", "time_bucket", "channel"]:
            if col in self.df.columns:
                self.assertTrue(self.df[col].isna().all() or (self.df[col] == "\\N").all())


if __name__ == "__main__":
    unittest.main()
