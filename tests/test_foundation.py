import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from bertopic_poc.io import ROOT, canonical_hash, output_path, read_json
from bertopic_poc.policy import AccessPolicy, LeakageError, model_text
from bertopic_poc.contracts import SchemaError, csv_dump, csv_load, validate, validate_rows


class FoundationTests(unittest.TestCase):
    def test_registry_targets_grid(self):
        r=read_json(ROOT/'config/experiment_registry.json')
        self.assertEqual(r['hidden_final'],['subscription_inquiry','troubleshoot_site'])
        self.assertEqual(r['hidden_dev'],['shipping_issue'])
        self.assertEqual(len(r['known_flows']),7)
        self.assertEqual(r['targets'],dict(closed_macro_f1=.7,unknown_f1=.6,routing_recall=.7,recovered_flows=2,family_precision=.7,family_recall=.3,cluster_support=5))
        self.assertEqual(len(r['search']['tau'])*len(r['search']['delta']),52)
        self.assertFalse(r['model_selection_performed'])
        self.assertEqual(len(r['models']),2)

    def test_role_boundaries(self):
        for role,resource,purpose in [('inference','sealed_labels','inference'),('evaluator','sealed_labels','scoring'),('reviewer','taxonomy_full','review'),('custodian','sealed_labels','scoring')]:
            p=AccessPolicy()
            with self.assertRaises(LeakageError):p.authorize(role,resource,purpose)
            self.assertFalse(p.valid)
        p=AccessPolicy();p.authorize('custodian','sealed_labels','membership_only')
        self.assertTrue(p.valid)
        p.gate=3;p.authorize('evaluator','sealed_labels','scoring')

    def test_blinded_and_snapshot(self):
        p=AccessPolicy()
        with self.assertRaises(LeakageError):p.authorize('reviewer','features','review',blinded=False)
        p=AccessPolicy();p.lock('G0',{'version':1});p.check('G0',{'version':1})
        with self.assertRaises(LeakageError):p.check('G0',{'version':2})

    def test_gates_cannot_skip(self):
        with self.assertRaises(LeakageError):AccessPolicy().advance(2,evidence_complete=True)
        with self.assertRaises(LeakageError):AccessPolicy().advance(1)

    def test_feature_allowlist(self):
        f={'masked_customer_text':'I need help','conversation_id':'opaque'}
        self.assertEqual(model_text(f),'I need help')
        for k in ['scenario','targets','candidates','action','flow','subflow']:
            with self.assertRaises(LeakageError):model_text(f|{k:'answer'})

    def test_workspace_raw_guard(self):
        with self.assertRaises(ValueError):output_path(ROOT.parent/'escape.json')
        with self.assertRaises(ValueError):output_path(ROOT/'data/raw/new.json')

    def segment(self):
        return dict(schema_version='1.0.0',experiment_id='fixture',run_id='r',segment_id='s',conversation_id='c',source_split='train',evidence_unit_id='u',customer_turn_index=0,span_start=0,span_end=2,masked_customer_text='Hi',content_status='non_need',preprocessing_version='1.0.0')

    def test_contract_types_versions_and_keys(self):
        r=self.segment();validate('segments',r)
        for change in [{'schema_version':'2.0.0'},{'span_start':True},{'source_split':'future'},{'span_end':0}]:
            with self.assertRaises(SchemaError):validate('segments',r|change)
        with self.assertRaises(SchemaError):validate_rows('segments',[r,r])
        with self.assertRaises(SchemaError):validate_rows('segments',[r],references={'conversation_id':{'other'}})

    def test_csv_round_trip(self):
        rows=[{'text':'Tiếng Việt,\n"quoted"','missing':None,'empty':''}]
        self.assertEqual(csv_load(csv_dump(rows,list(rows[0]))),rows)
        with self.assertRaises(SchemaError):csv_dump([{'text':'\\N'}],['text'])

    def test_quality_conservation(self):
        r=dict(schema_version='1.0.0',experiment_id='fixture',run_id='r',counts=dict(read=3,quarantine=1,excluded=1,eligible=1),reason_counts={},unresolved_counts={},metadata_availability={},alignment_ablation_failures=0)
        validate('data_quality',r)
        r['counts']['read']=4
        with self.assertRaises(SchemaError):validate('data_quality',r)


if __name__=='__main__':unittest.main()

class ModelLockTests(unittest.TestCase):
    def test_metadata_and_tokenizers(self):
        from bertopic_poc.evidence import EvidenceTokenizer
        from bertopic_poc.io import sha256
        registry=read_json(ROOT/'config/experiment_registry.json')
        for entry in registry['models']:
            self.assertEqual(entry['status'],'metadata_locked')
            self.assertEqual(entry['license'],'apache-2.0')
            self.assertRegex(entry['revision'],r'^[a-f0-9]{40}$')
            self.assertFalse(entry['weights_downloaded'])
            for filename,digest in entry['file_sha256'].items():
                self.assertEqual(sha256(ROOT/entry['tokenizer_directory']/filename),digest)
            self.assertTrue(entry['remote_weights_sha256'])
            self.assertTrue(all(len(v)==64 for v in entry['remote_weights_sha256'].values()))
            tokenizer=EvidenceTokenizer(entry)
            offsets=tokenizer.offsets('Hello world!')
            self.assertEqual(len(offsets),3)
            self.assertEqual(offsets,[(0,5),(6,11),(11,12)])

    def test_schema_document_and_docs(self):
        from bertopic_poc.contracts import BASE,FIELDS,KEYS
        doc=read_json(ROOT/'schemas/artifacts-1.0.0.json')
        self.assertEqual(doc['required_base'],BASE)
        self.assertEqual(set(doc['artifacts']),set(FIELDS))
        for kind in FIELDS:
            self.assertEqual(doc['artifacts'][kind]['required_fields'],FIELDS[kind])
            self.assertEqual(doc['artifacts'][kind]['unique_key'],['experiment_id','run_id']+KEYS[kind])
        content=(ROOT/'docs/phase1.md').read_text(encoding='utf-8-sig')
        for term in ['G0','G1','G2','G3','reviewer','raw','200','overlap20']:
            self.assertIn(term,content)
