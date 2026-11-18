"""Thực thi Group 8: Closed-set độc lập trên 10 flows, chọn ngưỡng trên Dev K, suy luận Test closed-set, và hợp nhất Schema 1.0.0 artifacts."""
import gzip
import json
import shutil
from pathlib import Path
import sys
import time
from collections import Counter, defaultdict
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bertopic_poc.io import ROOT, read_json, write_json, sha256
from bertopic_poc.taxonomy import (
    KNOWN_K_FLOWS, FLOW_SUBFLOW_CANONICAL, FLOW_DESCRIPTIONS_EN, flow_id
)
from bertopic_poc.text import Masker, spans, content_status
from bertopic_poc.scorer import score_evidence_unit, roll_up_conversation_status, EvidenceUnitScore
from bertopic_poc.cohorts import StatisticsScope, build_topic_statistics
from bertopic_poc.contracts import validate, csv_dump, BASE, FIELDS
from bertopic_poc.evaluator import round8, evaluate_fixed_classification
import datetime


def now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def dump_csv_file(kind: str, rows: list, path: Path):
    fieldnames = list(BASE.keys()) + list(FIELDS[kind].keys())
    text = csv_dump(rows, fieldnames)
    path.write_text(text, encoding='utf-8', newline='')


def run_group8():
    print("=== [TASK 8.1] Independent Closed-Set 10-Flow Baseline ===")
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sentence_transformers import SentenceTransformer
    import torch

    onto = read_json(ROOT / 'data/raw/ontology.json')
    names = onto.get('values', {}).get('enumerable', {}).get('customer_name', [])
    masker = Masker(names=names)

    all_10_flows = list(FLOW_SUBFLOW_CANONICAL.keys())
    print(f"Full 10 flows available after G2: {all_10_flows}")

    # Load Train conversations across all 10 flows for independent baseline fit
    with gzip.open(ROOT / 'data/raw/abcd_v1.1.json.gz', 'rt', encoding='utf-8') as f:
        data = json.load(f)

    train_texts = []
    train_labels = []
    for row in data['train']:
        flow = row.get('scenario', {}).get('flow')
        if flow in FLOW_SUBFLOW_CANONICAL:
            c_texts = []
            for role, text in row.get('original', []):
                if role == 'customer':
                    c_texts.append(masker(text))
            if c_texts:
                train_texts.append(' '.join(c_texts))
                train_labels.append(flow)

    print(f"Fitting independent TF-IDF + LogisticRegression baseline on {len(train_texts)} train conversations...")
    closed_vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2))
    X_train = closed_vectorizer.fit_transform(train_texts)
    closed_clf = LogisticRegression(C=1.0, max_iter=200, random_state=42)
    closed_clf.fit(X_train, train_labels)

    # Save baseline artifacts
    baseline_out = ROOT / 'artifacts/phase1/closed_baseline.json'
    write_json(baseline_out, {
        'schema_version': '1.0.0',
        'experiment_id': 'phase1',
        'run_id': 'closed_v1',
        'n_train_samples': len(train_texts),
        'classes': list(closed_clf.classes_),
        'vectorizer_features': len(closed_vectorizer.vocabulary_)
    })

    print("\n=== [TASK 8.2] Selecting Closed-Set Thresholds on Dev K ===")
    model_sel = read_json(ROOT / 'artifacts/phase1/model_selection.json')
    winning_model_id = model_sel['winning_model']
    model = SentenceTransformer(winning_model_id, device='cpu')
    torch.set_num_threads(4)

    # Encode 10 flow descriptions
    desc_10_texts = [FLOW_DESCRIPTIONS_EN[f] for f in all_10_flows]
    desc_10_embs = model.encode(desc_10_texts, normalize_embeddings=True, show_progress_bar=False)

    # Load Dev K conversations
    dev_k_units = []
    dev_k_convs = {}
    for row in data['dev']:
        flow = row.get('scenario', {}).get('flow')
        if flow in KNOWN_K_FLOWS:
            cid = str(row['convo_id'])
            dev_k_convs[cid] = flow
            for t_idx, (role, text) in enumerate(row.get('original', [])):
                if role == 'customer':
                    m_text = masker(text)
                    for a, b in spans(m_text):
                        span_text = m_text[a:b]
                        c_stat = content_status(span_text)
                        dev_k_units.append({
                            'conversation_id': cid,
                            'turn_index': t_idx,
                            'span_start': a,
                            'span_end': b,
                            'text': span_text,
                            'content_status': c_stat,
                            'evidence_unit_id': f"{cid}_t{t_idx}_s{a}_{b}"
                        })

    print(f"Loaded {len(dev_k_units)} units across {len(dev_k_convs)} Dev K conversations.")

    # Encode Dev K units
    dev_k_texts = [u['text'] for u in dev_k_units]
    dev_k_embs = model.encode(dev_k_texts, batch_size=32, normalize_embeddings=True, show_progress_bar=False)
    sims_10 = np.dot(dev_k_embs, desc_10_embs.T)

    # Grid search for closed thresholds (tau, delta)
    tau_grid = [0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50]
    delta_grid = [0.00, 0.05, 0.10]

    best_macro = -1.0
    best_tau = 0.20
    best_delta = 0.05

    for tau_c in tau_grid:
        for delta_c in delta_grid:
            conv_preds = {}
            for cid in dev_k_convs:
                # Find matching units
                matching_indices = [i for i, u in enumerate(dev_k_units) if u['conversation_id'] == cid]
                unit_scores = []
                for idx in matching_indices:
                    u = dev_k_units[idx]
                    scores_for_u = {
                        flow_id(f): float(sims_10[idx, i])
                        for i, f in enumerate(all_10_flows)
                    }
                    scored = score_evidence_unit(
                        unit_id=u['evidence_unit_id'],
                        conversation_id=u['conversation_id'],
                        turn_index=u['turn_index'],
                        span_start=u['span_start'],
                        span_end=u['span_end'],
                        content_status=u['content_status'],
                        topic_scores=scores_for_u,
                        tau=tau_c,
                        delta=delta_c
                    )
                    unit_scores.append(scored)

                roll = roll_up_conversation_status(unit_scores)
                # Primary topic or None
                prim = roll['primary_topic']
                if prim and prim.startswith('flow:'):
                    conv_preds[cid] = prim.split('flow:')[1]
                else:
                    conv_preds[cid] = 'abstain'

            # Compute macro F1 on Dev K
            y_true = [dev_k_convs[cid] for cid in dev_k_convs]
            y_pred = [conv_preds.get(cid, 'abstain') for cid in dev_k_convs]
            eval_res = evaluate_fixed_classification(y_pred, y_true, classes=KNOWN_K_FLOWS)
            f1 = eval_res['macro_f1']
            if f1 > best_macro:
                best_macro = f1
                best_tau = tau_c
                best_delta = delta_c

    print(f"Closed-set threshold selection complete: tau={best_tau}, delta={best_delta}, Dev K Macro-F1 = {best_macro:.4f}")

    closed_sel_path = ROOT / 'artifacts/phase1/closed_selection.json'
    write_json(closed_sel_path, {
        'schema_version': '1.0.0',
        'experiment_id': 'phase1',
        'run_id': 'closed_v1',
        'tau_closed': best_tau,
        'delta_closed': best_delta,
        'dev_k_macro_f1': round8(best_macro)
    })

    print("\n=== [TASK 8.3] Closed-Set Test Inference ===")
    test_10_units = []
    test_10_convs = {}
    for row in data['test']:
        flow = row.get('scenario', {}).get('flow')
        if flow in FLOW_SUBFLOW_CANONICAL:
            cid = str(row['convo_id'])
            test_10_convs[cid] = flow
            for t_idx, (role, text) in enumerate(row.get('original', [])):
                if role == 'customer':
                    m_text = masker(text)
                    for a, b in spans(m_text):
                        span_text = m_text[a:b]
                        c_stat = content_status(span_text)
                        test_10_units.append({
                            'conversation_id': cid,
                            'turn_index': t_idx,
                            'span_start': a,
                            'span_end': b,
                            'text': span_text,
                            'content_status': c_stat,
                            'evidence_unit_id': f"{cid}_t{t_idx}_s{a}_{b}"
                        })

    print(f"Loaded {len(test_10_units)} test units across {len(test_10_convs)} S_cs test conversations.")

    # Encode test units for 10 flows
    test_10_texts = [u['text'] for u in test_10_units]
    test_10_embs = model.encode(test_10_texts, batch_size=32, normalize_embeddings=True, show_progress_bar=False)
    test_sims_10 = np.dot(test_10_embs, desc_10_embs.T)

    closed_scored_units = []
    for idx, u in enumerate(test_10_units):
        scores_for_u = {
            flow_id(f): float(test_sims_10[idx, i])
            for i, f in enumerate(all_10_flows)
        }
        scored = score_evidence_unit(
            unit_id=u['evidence_unit_id'],
            conversation_id=u['conversation_id'],
            turn_index=u['turn_index'],
            span_start=u['span_start'],
            span_end=u['span_end'],
            content_status=u['content_status'],
            topic_scores=scores_for_u,
            tau=best_tau,
            delta=best_delta
        )
        closed_scored_units.append({
            'evidence_unit_id': u['evidence_unit_id'],
            'conversation_id': u['conversation_id'],
            'turn_index': u['turn_index'],
            'span_start': u['span_start'],
            'span_end': u['span_end'],
            'text': u['text'],
            'content_status': u['content_status'],
            'decision': scored.decision,
            'top_topic': scored.top1_topic,
            'margin': round8(scored.s1 - scored.s2) if scored.top2_topic else round8(scored.s1),
            'accepted_topics': [scored.top1_topic] if scored.decision == 'accepted' else [],
            'topic_scores': scores_for_u,
            'evidence_score_obj': scored
        })

    # Closed conversation rollups
    conv_to_c_units = defaultdict(list)
    conv_to_c_dicts = defaultdict(list)
    for csu in closed_scored_units:
        conv_to_c_units[csu['conversation_id']].append(csu['evidence_score_obj'])
        conv_to_c_dicts[csu['conversation_id']].append(csu)

    closed_conversation_rollups = {}
    for cid, u_list in conv_to_c_units.items():
        roll = roll_up_conversation_status(u_list)
        prim = roll['primary_topic']
        max_s = None
        ev_cnt = 0
        if prim:
            for csu in conv_to_c_dicts[cid]:
                if csu['decision'] == 'accepted' and prim in csu['accepted_topics']:
                    ev_cnt += 1
                    s = csu['topic_scores'].get(prim, 0.0)
                    if max_s is None or s > max_s:
                        max_s = s
        roll['max_score'] = round8(max_s) if max_s is not None else None
        roll['evidence_count'] = ev_cnt if prim else None
        closed_conversation_rollups[cid] = roll

    closed_status_counts = Counter(r['conversation_status'] for r in closed_conversation_rollups.values())
    print(f"Closed-set test conversation statuses: {dict(closed_status_counts)}")

    # Save closed-set outputs
    closed_dir = ROOT / 'artifacts/phase1/closed_test'
    closed_dir.mkdir(parents=True, exist_ok=True)

    closed_assignments_rows = []
    for csu in closed_scored_units:
        if csu['decision'] == 'accepted':
            for top in csu['accepted_topics']:
                row = {
                    'schema_version': '1.0.0',
                    'experiment_id': 'phase1',
                    'run_id': 'closed_v1',
                    'evidence_unit_id': csu['evidence_unit_id'],
                    'topic_id': top,
                    'source': 'fixed',
                    'conversation_id': csu['conversation_id'],
                    'segment_ids': [f"seg_{csu['evidence_unit_id']}"],
                    'score': float(csu['topic_scores'].get(top, 0.0)),
                    'score_type': 'cosine',
                    'assignment_status': 'accepted',
                    'evidence_spans': [{'span_start': csu['span_start'], 'span_end': csu['span_end']}],
                    'evidence_status': 'model_supported',
                    'cluster_key': None
                }
                validate('assignments', row)
                closed_assignments_rows.append(row)

    with open(closed_dir / 'assignments.jsonl', 'w', encoding='utf-8') as f:
        for r in closed_assignments_rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')

    closed_conv_topics = []
    for cid, roll in closed_conversation_rollups.items():
        if roll['conversation_status'] == 'known' and roll['primary_topic']:
            row = {
                'schema_version': '1.0.0',
                'experiment_id': 'phase1',
                'run_id': 'closed_v1',
                'conversation_id': cid,
                'topic_id': roll['primary_topic'],
                'source': 'fixed',
                'evidence_basis': 'predicted',
                'primary_topic': True,
                'max_score': roll['max_score'],
                'evidence_count': roll['evidence_count'],
                'taxonomy_version': '1.0.0'
            }
            validate('conversation_topics', row)
            closed_conv_topics.append(row)

    dump_csv_file('conversation_topics', closed_conv_topics, closed_dir / 'conversation_topics.csv')

    # Save closed test metadata for evaluator
    write_json(closed_dir / 'closed_test_metadata.json', {
        'schema_version': '1.0.0',
        'experiment_id': 'phase1',
        'run_id': 'closed_v1',
        'n_test_conversations': len(test_10_convs),
        'ground_truth_flows': test_10_convs,
        'conversation_rollups': {
            cid: {
                'status': r['conversation_status'],
                'primary_topic': r['primary_topic'],
                'max_score': r['max_score']
            }
            for cid, r in closed_conversation_rollups.items()
        }
    })

    print("\n=== [TASK 8.4] Consolidating Schema 1.0.0 Producer Artifacts ===")
    cons_dir = ROOT / 'artifacts/phase1/consolidated'
    cons_dir.mkdir(parents=True, exist_ok=True)

    # 1. Consolidated assignments.jsonl
    open_dir = ROOT / 'artifacts/phase1/open_test'
    all_assignments = []
    with open(open_dir / 'assignments.jsonl', 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                all_assignments.append(json.loads(line))
    for r in closed_assignments_rows:
        all_assignments.append(r)

    with open(cons_dir / 'assignments.jsonl', 'w', encoding='utf-8') as f:
        for r in all_assignments:
            validate('assignments', r)
            f.write(json.dumps(r, ensure_ascii=False) + '\n')

    # 2. Consolidated conversation_topics.csv
    from bertopic_poc.contracts import csv_load
    open_conv_topics = csv_load((open_dir / 'conversation_topics.csv').read_text(encoding='utf-8'))
    for row in open_conv_topics:
        # Cast boolean and int/float fields
        row['primary_topic'] = (row['primary_topic'] == 'True' or row['primary_topic'] is True)
        row['max_score'] = float(row['max_score']) if row.get('max_score') is not None else None
        row['evidence_count'] = int(row['evidence_count']) if row.get('evidence_count') is not None else None
        validate('conversation_topics', row)

    all_conv_topics = open_conv_topics + closed_conv_topics
    dump_csv_file('conversation_topics', all_conv_topics, cons_dir / 'conversation_topics.csv')

    # 3. Mirror candidates.jsonl and reviews.jsonl
    shutil.copy2(open_dir / 'candidates.jsonl', cons_dir / 'candidates.jsonl')
    shutil.copy2(open_dir / 'reviews.jsonl', cons_dir / 'reviews.jsonl')
    shutil.copy2(ROOT / 'artifacts/phase1/preparation_v1/data_quality.json', cons_dir / 'data_quality.json')

    # 4. Generate topic_statistics.csv for scopes: test_open and test_closed
    print("Generating consolidated topic_statistics.csv...")
    stats_rows = []

    # Scope 1: test_open
    open_meta = read_json(open_dir / 'test_inference_metadata.json')
    open_scope = StatisticsScope(
        scope_id='scope:test_open',
        eligible_conversation_ids=set(open_meta['conversation_rollups'].keys()),
        total_customer_messages=open_meta['n_test_units'],
        experiment_id='phase1',
        run_id='phase1_open_test'
    )
    # Build stats for 7 known flows in open_test
    open_assignments = [r for r in all_assignments if r['run_id'] == 'phase1_open_test']
    for f in KNOWN_K_FLOWS:
        tid = flow_id(f)
        s_row = build_topic_statistics(
            scope=open_scope,
            topic_id=tid,
            source='fixed',
            evidence_basis='predicted',
            assignments=open_assignments
        )
        validate('topic_statistics', s_row)
        stats_rows.append(s_row)

    # Scope 2: test_closed
    closed_scope = StatisticsScope(
        scope_id='scope:test_closed',
        eligible_conversation_ids=set(test_10_convs.keys()),
        total_customer_messages=len(test_10_units),
        experiment_id='phase1',
        run_id='closed_v1'
    )
    for f in all_10_flows:
        tid = flow_id(f)
        s_row = build_topic_statistics(
            scope=closed_scope,
            topic_id=tid,
            source='fixed',
            evidence_basis='predicted',
            assignments=closed_assignments_rows
        )
        validate('topic_statistics', s_row)
        stats_rows.append(s_row)

    dump_csv_file('topic_statistics', stats_rows, cons_dir / 'topic_statistics.csv')

    print("\n=== [TASK 8.5] Finalizing Run Manifest & Gate Logs Before G3 ===")
    g0_snap = read_json(ROOT / 'artifacts/phase1/bootstrap/g0_snapshot.json')
    g1_snap = read_json(ROOT / 'artifacts/phase1/g1_snapshot.json')
    g2_snap = read_json(ROOT / 'artifacts/phase1/g2_snapshot.json')

    manifest_path = ROOT / 'artifacts/phase1/run_manifest.json'
    tracked_artifacts = [
        ROOT / 'config/experiment_registry.json',
        ROOT / 'artifacts/phase1/bootstrap/g0_snapshot.json',
        ROOT / 'artifacts/phase1/g1_snapshot.json',
        ROOT / 'artifacts/phase1/g2_snapshot.json',
        ROOT / 'artifacts/phase1/model_selection.json',
        ROOT / 'artifacts/phase1/discovery_selection.json',
        ROOT / 'artifacts/phase1/closed_selection.json',
        cons_dir / 'assignments.jsonl',
        cons_dir / 'candidates.jsonl',
        cons_dir / 'reviews.jsonl',
        cons_dir / 'conversation_topics.csv',
        cons_dir / 'topic_statistics.csv',
        cons_dir / 'data_quality.json'
    ]

    artifact_hashes = {str(p.relative_to(ROOT)): sha256(p) for p in tracked_artifacts if p.exists()}

    raw_abcd_hash = sha256(ROOT / 'data/raw/abcd_v1.1.json.gz')
    raw_onto_hash = sha256(ROOT / 'data/raw/ontology.json')

    run_manifest = {
        'schema_version': '1.0.0',
        'experiment_id': 'phase1',
        'run_id': 'phase1_consolidated',
        'config_hash': sha256(ROOT / 'config/experiment_registry.json'),
        'source_hashes': {
            'data/raw/abcd_v1.1.json.gz': raw_abcd_hash,
            'data/raw/ontology.json': raw_onto_hash
        },
        'model_revisions': {
            'winning_model': winning_model_id,
            'revision': 'main'
        },
        'split_manifest_hash': sha256(ROOT / 'artifacts/phase1/preparation_v1/exclusion_manifest.json'),
        'taxonomy_version': '1.0.0',
        'mapping_version': '1.0.0',
        'preprocessing_version': '1.0.0',
        'seed': 42,
        'fit_scopes': ['train_k', 'dev_routed_pool', 'test_routed_pool', 'train_10_flows'],
        'search_registry_hash': sha256(ROOT / 'config/experiment_registry.json'),
        'gate_events': [
            {'gate': 'G0', 'timestamp': g0_snap.get('locked_at', now_iso()), 'status': 'locked'},
            {'gate': 'G1', 'timestamp': g1_snap.get('locked_at', now_iso()), 'status': 'locked'},
            {'gate': 'G2', 'timestamp': g2_snap.get('locked_at', now_iso()), 'status': 'locked'}
        ],
        'artifact_hashes': artifact_hashes,
        'benchmark_validity': 'valid_prior_to_g3',
        'resource_usage': {
            'cpu_threads': 4,
            'device': 'cpu'
        }
    }

    validate('run_manifest', run_manifest)
    write_json(manifest_path, run_manifest)
    print(f"Run manifest locked at {manifest_path}")
    print("Group 8 execution completed successfully!")


if __name__ == '__main__':
    run_group8()
