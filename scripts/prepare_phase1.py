"""Chuẩn bị dữ liệu Phase 1: đọc ABCD, mask PII, dedup và trích xuất evidence units."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bertopic_poc.io import ROOT, read_json, write_json, sha256, canonical_hash
from bertopic_poc.reader import read_abcd, read_ontology
from bertopic_poc.text import Masker
from bertopic_poc.dedup import exclusions
from bertopic_poc.evidence import EvidenceTokenizer, evidence_rows, opaque_id
from bertopic_poc.contracts import validate, validate_rows, SchemaError


EXPECTED_HASHES = {
    'abcd': '2bdf53ac359543dcdc38d55bc6513e78df120363f8f44870716e909f4606de15',
    'ontology': '2e1c1d763518ba084ada7f7bc8b54f0b489c81da3b170875cf9340891e06524c'
}


def main():
    parser = argparse.ArgumentParser(description="Prepare Phase 1 data artifacts")
    parser.add_argument('--run-id', default='preparation_v1', help='Run ID')
    parser.add_argument('--experiment-id', default='phase1', help='Experiment ID')
    parser.add_argument('--limit', type=int, default=None, help='Optional limit for smoke testing')
    args = parser.parse_args()

    start_time = time.time()
    out_dir = ROOT / 'artifacts' / args.experiment_id / args.run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Verify raw hashes before
    abcd_path = ROOT / 'data/raw/abcd_v1.1.json.gz'
    onto_path = ROOT / 'data/raw/ontology.json'
    if sha256(abcd_path) != EXPECTED_HASHES['abcd']:
        raise ValueError("raw_abcd_hash_mismatch")
    if sha256(onto_path) != EXPECTED_HASHES['ontology']:
        raise ValueError("raw_ontology_hash_mismatch")

    # 2. Read dataset & ontology
    print("Reading ABCD dataset and ontology...")
    valid, bad, summary = read_abcd(abcd_path)
    onto = read_ontology(onto_path)

    if args.limit:
        valid = valid[:args.limit]

    # Check for empty corpus
    if not valid:
        raise ValueError("empty_scope: no valid conversations to process")

    # 3. PII Masker
    masker = Masker(names=onto['pii_name_lexicon'])

    # 4. Mask customer turns
    masked_records = []
    customer_texts = []
    alignment_failures = 0
    for conv in valid:
        if not conv.alignment_ok:
            alignment_failures += 1
        masked_turns = []
        cust_turns = []
        for role, text in conv.turns:
            if role == 'customer':
                m_text = masker(text)
                masked_turns.append((role, m_text))
                cust_turns.append(m_text)
            else:
                masked_turns.append((role, text))
        masked_records.append(masked_turns)
        customer_texts.append(" ".join(cust_turns))

    # 5. Dedup & Cross-split Exclusions
    print("Auditing duplicates and cross-split exclusions...")
    excluded_map, audit_groups, comparisons = exclusions(valid, customer_texts)
    print(f"Comparisons: {comparisons}, Excluded cross-split: {len(excluded_map)}")

    exclusion_manifest = [
        {
            'conversation_id': opaque_id(valid[idx].source_id),
            'source_split': valid[idx].split,
            'reason': reason
        }
        for idx, reason in sorted(excluded_map.items())
    ]
    write_json(out_dir / 'exclusion_manifest.json', exclusion_manifest)

    quarantine_manifest = bad
    write_json(out_dir / 'quarantine_manifest.json', quarantine_manifest)

    # 6. Build evidence segments for eligible conversations
    eligible_indices = [i for i in range(len(valid)) if i not in excluded_map]
    print(f"Eligible conversations: {len(eligible_indices)}")

    registry = read_json(ROOT / 'config/experiment_registry.json')
    tokenizer = EvidenceTokenizer(registry['models'][0])

    segments_path = out_dir / 'segments.jsonl'
    segment_count = 0
    seen_segment_keys = set()
    content_status_counts = Counter()

    print("Extracting evidence units and windows...")
    with open(segments_path, 'w', encoding='utf-8') as f_seg:
        for idx in eligible_indices:
            conv = valid[idx]
            c_id = opaque_id(conv.source_id)
            masked_turns = masked_records[idx]
            for row in evidence_rows(c_id, conv.split, masked_turns, tokenizer,
                                     experiment_id=args.experiment_id, run_id=args.run_id):
                validate('segments', row)
                seg_key = row['segment_id']
                if seg_key in seen_segment_keys:
                    raise SchemaError(f"duplicate_segment_key: {seg_key}")
                seen_segment_keys.add(seg_key)
                content_status_counts[row['content_status']] += 1
                f_seg.write(json.dumps(row, ensure_ascii=False) + '\n')
                segment_count += 1

    print(f"Wrote {segment_count} segments. Content statuses: {dict(content_status_counts)}")

    # 7. Data Quality Artifact
    counts = {
        'read': summary['read'] if not args.limit else len(valid) + len(bad),
        'quarantine': len(bad),
        'excluded': len(excluded_map),
        'eligible': len(eligible_indices)
    }
    # Verify count conservation
    if counts['read'] != counts['quarantine'] + counts['excluded'] + counts['eligible']:
        raise ValueError(f"Conservation violated: {counts}")

    reason_counts = dict(Counter(b['reason'] for b in bad))
    reason_counts.update(dict(Counter(excluded_map.values())))

    data_quality = {
        'schema_version': '1.0.0',
        'experiment_id': args.experiment_id,
        'run_id': args.run_id,
        'counts': counts,
        'reason_counts': reason_counts,
        'unresolved_counts': {
            'content_status': dict(content_status_counts)
        },
        'metadata_availability': {
            'customer_id': False,
            'timestamp': False,
            'channel': False
        },
        'alignment_ablation_failures': alignment_failures
    }
    validate('data_quality', data_quality)
    write_json(out_dir / 'data_quality.json', data_quality)

    # 8. Run Manifest
    files_to_hash = {
        'data_quality': out_dir / 'data_quality.json',
        'exclusion_manifest': out_dir / 'exclusion_manifest.json',
        'quarantine_manifest': out_dir / 'quarantine_manifest.json',
        'segments': out_dir / 'segments.jsonl'
    }
    artifact_hashes = {k: sha256(p) for k, p in files_to_hash.items()}

    run_manifest = {
        'schema_version': '1.0.0',
        'experiment_id': args.experiment_id,
        'run_id': args.run_id,
        'config_hash': sha256(ROOT / 'config/experiment_registry.json'),
        'source_hashes': {
            'abcd': EXPECTED_HASHES['abcd'],
            'ontology': EXPECTED_HASHES['ontology']
        },
        'model_revisions': {
            m['model_id']: m['revision'] for m in registry['models']
        },
        'split_manifest_hash': artifact_hashes['exclusion_manifest'],
        'taxonomy_version': '1.0.0',
        'mapping_version': '1.0.0',
        'preprocessing_version': '1.0.0',
        'seed': 42,
        'fit_scopes': ['train'],
        'search_registry_hash': sha256(ROOT / 'config/experiment_registry.json'),
        'gate_events': [
            {
                'gate': 'G0',
                'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
            }
        ],
        'artifact_hashes': artifact_hashes,
        'benchmark_validity': 'valid_with_declared_test_exposure',
        'resource_usage': {
            'duration_seconds': round(time.time() - start_time, 2),
            'total_segments': segment_count
        }
    }
    validate('run_manifest', run_manifest)
    write_json(out_dir / 'run_manifest.json', run_manifest)

    # 9. Verify raw hashes after
    if sha256(abcd_path) != EXPECTED_HASHES['abcd']:
        raise ValueError("raw_abcd_mutated_after_run")
    if sha256(onto_path) != EXPECTED_HASHES['ontology']:
        raise ValueError("raw_ontology_mutated_after_run")

    print(f"Preparation complete for {args.run_id}. Duration: {round(time.time() - start_time, 2)}s.")


if __name__ == '__main__':
    main()
