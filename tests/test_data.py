import gzip
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from bertopic_poc.io import ROOT, read_json, sha256
from bertopic_poc.reader import Conversation, read_abcd, read_ontology
from bertopic_poc.text import Masker, content_status, normalize, spans
from bertopic_poc.dedup import duplicate_components, exclusions, words
from bertopic_poc.evidence import EvidenceTokenizer, evidence_rows, opaque_id
from bertopic_poc.policy import AccessPolicy, LeakageError, model_text
from bertopic_poc.contracts import SchemaError, validate, validate_rows


class DataPreparationTests(unittest.TestCase):
    def test_full_abcd_counts_and_hashes(self):
        abcd_path = ROOT / 'data/raw/abcd_v1.1.json.gz'
        self.assertEqual(sha256(abcd_path), '2bdf53ac359543dcdc38d55bc6513e78df120363f8f44870716e909f4606de15')
        valid, bad, summary = read_abcd(abcd_path)
        self.assertEqual(summary['read'], 10042)
        self.assertEqual(summary['split_read'], {'train': 8034, 'dev': 1004, 'test': 1004})
        self.assertEqual(summary['role_turn_counts'], {'agent': 95129, 'customer': 89372, 'action': 36482})
        # Check raw hash unchanged after read
        self.assertEqual(sha256(abcd_path), '2bdf53ac359543dcdc38d55bc6513e78df120363f8f44870716e909f4606de15')

    def test_read_ontology_and_hashes(self):
        onto_path = ROOT / 'data/raw/ontology.json'
        self.assertEqual(sha256(onto_path), '2e1c1d763518ba084ada7f7bc8b54f0b489c81da3b170875cf9340891e06524c')
        onto = read_ontology(onto_path)
        self.assertEqual(onto['flow_count'], 10)
        self.assertEqual(onto['subflow_count'], 55)
        self.assertTrue(len(onto['pii_name_lexicon']) > 0)
        # Check raw hash unchanged after read
        self.assertEqual(sha256(onto_path), '2e1c1d763518ba084ada7f7bc8b54f0b489c81da3b170875cf9340891e06524c')

    def test_reader_quarantine_fixtures(self):
        with TemporaryDirectory() as tmpdir:
            bad_data = {
                'train': [
                    {'convo_id': '', 'original': [['customer', 'Hi']]},  # missing_id
                    {'convo_id': 1, 'original': []},  # missing_turns
                    {'convo_id': 2, 'original': [['unknown_role', 'Text']]},  # unknown_role
                    {'convo_id': 3, 'original': [['agent', 'Hello!']]},  # no_customer_text
                    {'convo_id': 4, 'original': [['customer', '']]},  # missing_text
                    {'convo_id': 5, 'original': [['customer', 'Valid']], 'delexed': [{'speaker': 'agent'}]},  # bad alignment
                ],
                'dev': [
                    {'convo_id': 6, 'original': [['customer', 'Dev valid']]},
                    {'convo_id': 6, 'original': [['customer', 'Duplicate ID']]},  # duplicate_id
                ],
                'test': [
                    {'convo_id': 7, 'original': [['customer', 'Test valid']]}
                ]
            }
            tmp_path = Path(tmpdir) / 'test_abcd.json.gz'
            with gzip.open(tmp_path, 'wt', encoding='utf-8') as f:
                json.dump(bad_data, f)

            valid, bad, summary = read_abcd(tmp_path)
            self.assertEqual(summary['read'], 9)
            reasons = {b['reason'] for b in bad}
            self.assertIn('missing_id', reasons)
            self.assertIn('missing_turns', reasons)
            self.assertIn('unknown_role', reasons)
            self.assertIn('no_customer_text', reasons)
            self.assertIn('missing_text', reasons)
            self.assertIn('duplicate_id', reasons)
            self.assertEqual(len(bad), 6)
            self.assertEqual(len(valid), 3)
            # Check alignment_ok is false for misaligned delexed, but record remains valid
            cid_5 = [v for v in valid if v.source_id == '5'][0]
            self.assertFalse(cid_5.alignment_ok)

    def test_masker_pii_and_semantic_preservation(self):
        onto = read_ontology(ROOT / 'data/raw/ontology.json')
        masker = Masker(names=onto['pii_name_lexicon'])

        # Email & phone
        text1 = "Contact me at user@example.com or +1 (555) 123-4567 regarding my refund."
        masked1 = masker(text1)
        self.assertIn('<EMAIL>', masked1)
        self.assertIn('<PHONE>', masked1)
        self.assertIn('refund', masked1)

        # Address & ID
        text2 = "I live at 123 Main Street and my order number is #987654321."
        masked2 = masker(text2)
        self.assertIn('<ADDRESS>', masked2)
        self.assertIn('<ID>', masked2)

        # Name masking from ontology lexicon
        if onto['pii_name_lexicon']:
            sample_name = onto['pii_name_lexicon'][0]
            masked_name = masker(f"My name is {sample_name} and I want help.")
            self.assertIn('<PERSON>', masked_name)

        # Preserve negations, prices, and products
        text_biz = "I do not want boots for $20.50, I cannot accept this order."
        masked_biz = masker(text_biz)
        self.assertIn('not', masked_biz)
        self.assertIn('boots', masked_biz)
        self.assertIn('$20.50', masked_biz)
        self.assertIn('cannot', masked_biz)

    def test_content_status_rules(self):
        # non_need whitelist exact
        self.assertEqual(content_status("Hi"), "non_need")
        self.assertEqual(content_status("Hello!"), "non_need")
        self.assertEqual(content_status("Thank you very much."), "non_need")
        self.assertEqual(content_status("<PERSON> <ID>"), "non_need")

        # Mixed greeting with real need -> analyzable
        self.assertEqual(content_status("Hello, I need a refund"), "analyzable")
        self.assertEqual(content_status("Hi I want to cancel order"), "analyzable")

        # insufficient_evidence
        self.assertEqual(content_status("Yes"), "insufficient_evidence")
        self.assertEqual(content_status("no"), "insufficient_evidence")
        self.assertEqual(content_status("that one!"), "insufficient_evidence")
        self.assertEqual(content_status("OK"), "insufficient_evidence")

        # Short unseen need -> analyzable
        self.assertEqual(content_status("lost my password"), "analyzable")
        self.assertEqual(content_status("wrong address delivered"), "analyzable")

    def test_spans_sentence_and_semicolon(self):
        # Two needs separated by semicolon in a single turn
        turn = "I need a refund; I forgot my password"
        sp = list(spans(turn))
        self.assertEqual(len(sp), 2)
        span_texts = [turn[a:b] for a, b in sp]
        self.assertEqual(span_texts, ["I need a refund;", "I forgot my password"])

        # Decimal and abbreviation handling
        text_with_dec_abbr = "Dr. Smith paid $20.50 for jeans. Then left."
        sp2 = list(spans(text_with_dec_abbr))
        self.assertEqual(len(sp2), 2)
        self.assertEqual(text_with_dec_abbr[sp2[0][0]:sp2[0][1]], "Dr. Smith paid $20.50 for jeans.")
        self.assertEqual(text_with_dec_abbr[sp2[1][0]:sp2[1][1]], "Then left.")

    def test_dedup_cross_split_priority(self):
        # Test exact and near-duplicates cross-split: test > dev > train
        texts = [
            "This is a common customer message that is long enough to meet the near duplicate threshold exactly twenty tokens.",  # 0: train
            "This is a common customer message that is long enough to meet the near duplicate threshold exactly twenty tokens.",  # 1: dev
            "This is a common customer message that is long enough to meet the near duplicate threshold exactly twenty tokens.",  # 2: test
            "Unique train message here without any duplicate.",  # 3: train
        ]
        records = [
            Conversation('c0', 'train', (), True),
            Conversation('c1', 'dev', (), True),
            Conversation('c2', 'test', (), True),
            Conversation('c3', 'train', (), True),
        ]
        excluded, audit, comparisons = exclusions(records, texts)
        self.assertIn(0, excluded)  # train excluded
        self.assertIn(1, excluded)  # dev excluded
        self.assertNotIn(2, excluded)  # test kept
        self.assertNotIn(3, excluded)  # unique kept
        self.assertEqual(excluded[0], 'cross_split_duplicate')
        self.assertEqual(excluded[1], 'cross_split_duplicate')

    def test_evidence_tokenizer_and_windows(self):
        registry = read_json(ROOT / 'config/experiment_registry.json')
        model_entry = registry['models'][0]
        tok = EvidenceTokenizer(model_entry)
        text = "Hello world! This is a test."
        offsets = tok.offsets(text)
        self.assertTrue(len(offsets) > 0)

        # Windowing on long text
        long_text = "word " * 300
        windows = tok.windows(long_text, max_tokens=200, overlap=20)
        self.assertTrue(len(windows) > 1)
        # Windows must cover start to end
        self.assertEqual(windows[0][0], 0)
        self.assertEqual(windows[-1][1], len(long_text))

    def test_feature_allowlist_and_leakage(self):
        feat = {
            'conversation_id': 'c123',
            'source_split': 'train',
            'masked_customer_text': 'I need a refund',
            'preprocessing_version': '1.0.0'
        }
        # Allowed access
        self.assertEqual(model_text(feat), 'I need a refund')

        # Forbidden fields
        for forbidden in ['scenario', 'targets', 'candidates', 'action', 'flow', 'subflow']:
            bad_feat = dict(feat)
            bad_feat[forbidden] = 'forbidden_value'
            with self.assertRaises(LeakageError):
                model_text(bad_feat)


if __name__ == '__main__':
    unittest.main()
