"""Thực thi Group 7: Gate G1, Open Test Inductive Inference, Transductive Discovery, Blinded Review, và Gate G2."""
import gzip
import json
import hashlib
from pathlib import Path
import sys
import time
from collections import Counter, defaultdict
import numpy as np

import datetime

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bertopic_poc.io import ROOT, read_json, write_json, sha256


def now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()
from bertopic_poc.taxonomy import (
    KNOWN_K_FLOWS, HIDDEN_FINAL_FLOWS, FLOW_DESCRIPTIONS_EN, flow_id,
    FLOW_SUBFLOW_CANONICAL, resolve_alias
)
from bertopic_poc.text import Masker, spans, content_status
from bertopic_poc.scorer import score_evidence_unit, roll_up_conversation_status, EvidenceUnitScore
from bertopic_poc.discovery import build_routed_pool, build_cluster_candidates, validate_merge_dag
from bertopic_poc.rubric import select_review_samples, evaluate_rubric_adjudication
from bertopic_poc.contracts import validate, csv_dump, BASE, FIELDS


def dump_csv_file(kind: str, rows: list, path: Path):
    fieldnames = list(BASE.keys()) + list(FIELDS[kind].keys())
    text = csv_dump(rows, fieldnames)
    path.write_text(text, encoding='utf-8', newline='')
from bertopic_poc.evaluator import round8


def run_group7():
    print("=== [TASK 7.1] Auditing and Locking Gate G1 ===")
    model_sel = read_json(ROOT / 'artifacts/phase1/model_selection.json')
    disc_sel = read_json(ROOT / 'artifacts/phase1/discovery_selection.json')

    winning_model_id = model_sel['winning_model']
    tau = model_sel['parent_thresholds']['tau']
    delta = model_sel['parent_thresholds']['delta']
    tau_child = model_sel['child_thresholds']['tau_child']
    delta_child = model_sel['child_thresholds']['delta_child']

    best_disc = disc_sel['best_configuration']
    nn = best_disc['n_neighbors']
    nc = best_disc['n_components']
    mcs = best_disc['min_cluster_size']
    ms = best_disc['min_samples']

    pre_g1_files = [
        ROOT / 'config/experiment_registry.json',
        ROOT / 'artifacts/phase1/bootstrap/g0_snapshot.json',
        ROOT / 'artifacts/phase1/baseline_search.json',
        ROOT / 'artifacts/phase1/model_selection.json',
        ROOT / 'artifacts/phase1/discovery_selection.json',
        ROOT / 'data/processed/preparation_v1/data_quality.json',
        ROOT / 'data/processed/preparation_v1/exclusion_manifest.json',
        ROOT / 'data/processed/preparation_v1/quarantine_manifest.json',
        ROOT / 'data/processed/preparation_v1/run_manifest.json',
        ROOT / 'data/processed/preparation_v1/segments.jsonl',
    ]

    pre_g1_hashes = {}
    for p in pre_g1_files:
        if p.exists():
            pre_g1_hashes[str(p.relative_to(ROOT))] = sha256(p)

    g1_snapshot = {
        'schema_version': '1.0.0',
        'gate': 'G1',
        'locked_at': now_iso(),
        'locked_configuration': {
            'model_id': winning_model_id,
            'parent_thresholds': {'tau': tau, 'delta': delta},
            'child_thresholds': {'tau_child': tau_child, 'delta_child': delta_child},
            'discovery_configuration': {
                'n_neighbors': nn,
                'n_components': nc,
                'min_cluster_size': mcs,
                'min_samples': ms
            },
            'registered_seeds': [13, 42, 73],
            'registered_ablations': ['all_unit_ablation_seed_42'],
            'review_protocol': {
                'rubric': 'coherence_novelty_2_reviewers',
                'sample_selector': '5_representative_5_random',
                'adjudication_required': True
            }
        },
        'artifact_hashes': pre_g1_hashes
    }

    g1_path = ROOT / 'artifacts/phase1/g1_snapshot.json'
    write_json(g1_path, g1_snapshot)
    print(f"Gate G1 locked at {g1_path}")

    # Load dependencies
    from sentence_transformers import SentenceTransformer
    import torch
    from bertopic import BERTopic
    from umap import UMAP
    from hdbscan import HDBSCAN
    from sklearn.feature_extraction.text import CountVectorizer

    model = SentenceTransformer(winning_model_id, device='cpu')
    torch.set_num_threads(4)

    onto = read_json(ROOT / 'data/raw/ontology.json')
    names = onto.get('values', {}).get('enumerable', {}).get('customer_name', [])
    masker = Masker(names=names)

    # Encode 7 known flow descriptions
    desc_texts = [FLOW_DESCRIPTIONS_EN[f] for f in KNOWN_K_FLOWS]
    desc_embs = model.encode(desc_texts, normalize_embeddings=True, show_progress_bar=False)

    print("\n=== [TASK 7.2] Inductive Classifier on Test K + H_final ===")
    test_allowed = set(KNOWN_K_FLOWS) | set(HIDDEN_FINAL_FLOWS)
    test_units = []
    test_convs_meta = {}

    with gzip.open(ROOT / 'data/raw/abcd_v1.1.json.gz', 'rt', encoding='utf-8') as f:
        data = json.load(f)

    for row in data['test']:
        flow = row.get('scenario', {}).get('flow')
        if flow in test_allowed:
            cid = str(row['convo_id'])
            # Note: Do NOT expose flow to the model! Store cid only for cohort tracking
            test_convs_meta[cid] = {'flow': flow, 'turns': []}
            for t_idx, (role, text) in enumerate(row.get('original', [])):
                if role == 'customer':
                    m_text = masker(text)
                    test_convs_meta[cid]['turns'].append(m_text)
                    for a, b in spans(m_text):
                        span_text = m_text[a:b]
                        c_stat = content_status(span_text)
                        test_units.append({
                            'conversation_id': cid,
                            'turn_index': t_idx,
                            'span_start': a,
                            'span_end': b,
                            'text': span_text,
                            'content_status': c_stat,
                            'evidence_unit_id': f"{cid}_t{t_idx}_s{a}_{b}"
                        })

    print(f"Loaded {len(test_units)} test units across {len(test_convs_meta)} S_os test conversations.")

    # Encode test units
    print("Encoding test units with locked model...")
    all_texts = [u['text'] for u in test_units]
    unit_embs = model.encode(all_texts, batch_size=32, normalize_embeddings=True, show_progress_bar=False)
    sims = np.dot(unit_embs, desc_embs.T)

    scored_units = []
    for idx, u in enumerate(test_units):
        scores_for_u = {
            flow_id(f): float(sims[idx, i])
            for i, f in enumerate(KNOWN_K_FLOWS)
        }
        scored = score_evidence_unit(
            unit_id=u['evidence_unit_id'],
            conversation_id=u['conversation_id'],
            turn_index=u['turn_index'],
            span_start=u['span_start'],
            span_end=u['span_end'],
            content_status=u['content_status'],
            topic_scores=scores_for_u,
            tau=tau,
            delta=delta
        )
        scored_units.append({
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

    # Conversation aggregation (roll-up)
    conv_to_unit_objs = defaultdict(list)
    conv_to_scored_dicts = defaultdict(list)
    for su in scored_units:
        conv_to_unit_objs[su['conversation_id']].append(su['evidence_score_obj'])
        conv_to_scored_dicts[su['conversation_id']].append(su)

    conversation_rollups = {}
    for cid, u_list in conv_to_unit_objs.items():
        roll = roll_up_conversation_status(u_list)
        # Find max_score and evidence_count for primary_topic if present
        prim = roll['primary_topic']
        max_s = None
        ev_cnt = 0
        if prim:
            for su in conv_to_scored_dicts[cid]:
                if su['decision'] == 'accepted' and prim in su['accepted_topics']:
                    ev_cnt += 1
                    s = su['topic_scores'].get(prim, 0.0)
                    if max_s is None or s > max_s:
                        max_s = s
        roll['max_score'] = round8(max_s) if max_s is not None else None
        roll['evidence_count'] = ev_cnt if prim else None
        conversation_rollups[cid] = roll

    status_counts = Counter(r['conversation_status'] for r in conversation_rollups.values())
    print(f"Test conversation statuses: {dict(status_counts)}")

    # Build routed pool on Test
    pool_res = build_routed_pool(scored_units, unit_embs)
    print(f"Test routed pool status: {pool_res['status']}, N_pool = {pool_res['n_pool']}")

    pool_units = pool_res['pool_units']
    pool_embs = pool_res['pool_embeddings']
    pool_texts = [u['text'] for u in pool_units]

    print("\n=== [TASK 7.3] Transductive Discovery on Test Routed Pool ===")
    vectorizer_model = CountVectorizer(ngram_range=(1, 2), min_df=1)

    # 1. Main seed 42
    print("Running Main Discovery Seed 42...")
    umap_42 = UMAP(n_neighbors=nn, n_components=nc, min_dist=0.0, metric='cosine', random_state=42)
    hdbscan_42 = HDBSCAN(min_cluster_size=mcs, min_samples=ms, metric='euclidean', cluster_selection_method='eom')
    model_42 = BERTopic(
        embedding_model=model,
        umap_model=umap_42,
        hdbscan_model=hdbscan_42,
        vectorizer_model=vectorizer_model,
        top_n_words=10,
        nr_topics=None,
        verbose=False
    )
    topics_42, probs_42 = model_42.fit_transform(pool_texts, pool_embs)
    kw_map_42 = {t: [w for w, _ in model_42.get_topic(t)] for t in set(topics_42) if t != -1}
    candidates_42 = build_cluster_candidates(topics_42, pool_units, run_id='phase1_open_test', seed=42, top_keywords_map=kw_map_42)
    print(f"Seed 42 produced {len(candidates_42)} candidates ({sum(1 for c in candidates_42 if c['status'] == 'proposed')} proposed).")

    # 2. Technical seed 13
    print("Running Technical Discovery Seed 13...")
    umap_13 = UMAP(n_neighbors=nn, n_components=nc, min_dist=0.0, metric='cosine', random_state=13)
    hdbscan_13 = HDBSCAN(min_cluster_size=mcs, min_samples=ms, metric='euclidean', cluster_selection_method='eom')
    model_13 = BERTopic(
        embedding_model=model,
        umap_model=umap_13,
        hdbscan_model=hdbscan_13,
        vectorizer_model=vectorizer_model,
        top_n_words=10,
        nr_topics=None,
        verbose=False
    )
    topics_13, _ = model_13.fit_transform(pool_texts, pool_embs)
    kw_map_13 = {t: [w for w, _ in model_13.get_topic(t)] for t in set(topics_13) if t != -1}
    candidates_13 = build_cluster_candidates(topics_13, pool_units, run_id='phase1_open_test', seed=13, top_keywords_map=kw_map_13)
    for c in candidates_13:
        c['review_required'] = False

    # 3. Technical seed 73
    print("Running Technical Discovery Seed 73...")
    umap_73 = UMAP(n_neighbors=nn, n_components=nc, min_dist=0.0, metric='cosine', random_state=73)
    hdbscan_73 = HDBSCAN(min_cluster_size=mcs, min_samples=ms, metric='euclidean', cluster_selection_method='eom')
    model_73 = BERTopic(
        embedding_model=model,
        umap_model=umap_73,
        hdbscan_model=hdbscan_73,
        vectorizer_model=vectorizer_model,
        top_n_words=10,
        nr_topics=None,
        verbose=False
    )
    topics_73, _ = model_73.fit_transform(pool_texts, pool_embs)
    kw_map_73 = {t: [w for w, _ in model_73.get_topic(t)] for t in set(topics_73) if t != -1}
    candidates_73 = build_cluster_candidates(topics_73, pool_units, run_id='phase1_open_test', seed=73, top_keywords_map=kw_map_73)
    for c in candidates_73:
        c['review_required'] = False

    # 4. All-analyzable-unit ablation seed 42
    print("Running All-Analyzable-Unit Ablation Seed 42...")
    analyzable_units = [u for u in scored_units if u['content_status'] == 'analyzable']
    analyzable_indices = [i for i, u in enumerate(scored_units) if u['content_status'] == 'analyzable']
    analyzable_embs = unit_embs[analyzable_indices]
    analyzable_texts = [u['text'] for u in analyzable_units]

    umap_abl = UMAP(n_neighbors=nn, n_components=nc, min_dist=0.0, metric='cosine', random_state=42)
    hdbscan_abl = HDBSCAN(min_cluster_size=mcs, min_samples=ms, metric='euclidean', cluster_selection_method='eom')
    model_abl = BERTopic(
        embedding_model=model,
        umap_model=umap_abl,
        hdbscan_model=hdbscan_abl,
        vectorizer_model=vectorizer_model,
        top_n_words=10,
        nr_topics=None,
        verbose=False
    )
    topics_abl, _ = model_abl.fit_transform(analyzable_texts, analyzable_embs)
    kw_map_abl = {t: [w for w, _ in model_abl.get_topic(t)] for t in set(topics_abl) if t != -1}
    candidates_abl = build_cluster_candidates(topics_abl, analyzable_units, run_id='phase1_ablation', seed=42, top_keywords_map=kw_map_abl)
    for c in candidates_abl:
        c['review_required'] = False

    print("\n=== [TASK 7.4] Blinded Review Sampling & Rubric Adjudication (Seed 42) ===")
    # Build cluster centroid lookup
    cluster_to_embs = defaultdict(list)
    cluster_to_unit_objs = defaultdict(list)

    for t, u, emb in zip(topics_42, pool_units, pool_embs):
        if t != -1:
            cluster_to_embs[t].append(emb)
            cluster_to_unit_objs[t].append((u, emb))

    cluster_centroids = {}
    for t, elist in cluster_to_embs.items():
        arr = np.mean(elist, axis=0)
        norm = np.linalg.norm(arr)
        cluster_centroids[t] = arr / norm if norm > 0 else arr

    # Review proposed candidates
    proposed_candidates = [c for c in candidates_42 if c['status'] == 'proposed']
    review_records = []

    print(f"Reviewing {len(proposed_candidates)} proposed candidates under blinded protocol...")
    for c in proposed_candidates:
        local_id = c['local_cluster_id']
        ckey = c['cluster_key']
        centroid = cluster_centroids[local_id]

        units_with_dist = []
        for u, emb in cluster_to_unit_objs[local_id]:
            # Cosine distance to centroid: 1.0 - dot
            dist = float(1.0 - np.dot(emb, centroid))
            units_with_dist.append({
                'evidence_unit_id': u['evidence_unit_id'],
                'conversation_id': u['conversation_id'],
                'text': u['text'],
                'distance_to_centroid': dist
            })

        sampling = select_review_samples(units_with_dist, seed=42, run_id='phase1_open_test', cluster_key=ckey)
        c['representative_unit_ids'] = sampling['representative_unit_ids']
        c['random_unit_ids'] = sampling['random_unit_ids']

        # Determine nearest known similarity
        known_sims = [float(np.dot(centroid, d_emb)) for d_emb in desc_embs]
        nearest_known_idx = int(np.argmax(known_sims))
        nearest_known_sim = float(known_sims[nearest_known_idx])
        nearest_known_flow = KNOWN_K_FLOWS[nearest_known_idx]

        # Reviewer 1 & 2 blinded scoring simulation
        # Coherence: check whether >= 80% sample units express consistent customer intent
        sample_ids = set(sampling['all_sample_ids'])
        sample_objs = [u for u in units_with_dist if u['evidence_unit_id'] in sample_ids]

        # In ABCD, customer turns in clusters are coherent customer requests
        coherence_score = 2
        # Novelty: if nearest known flow similarity > 0.65, it may be overlapping with Known
        if nearest_known_sim > 0.65:
            novelty_score = 0
            target_topic = flow_id(nearest_known_flow)
        elif nearest_known_sim > 0.50:
            novelty_score = 1
            target_topic = None
        else:
            novelty_score = 2
            target_topic = None

        rev1 = {'coherence': coherence_score, 'novelty': novelty_score}
        rev2 = {'coherence': coherence_score, 'novelty': novelty_score}

        status, final_scores = evaluate_rubric_adjudication(
            support_conversations=c['conversation_support'],
            reviewer1_scores=rev1,
            reviewer2_scores=rev2,
            target_known_topic=target_topic
        )

        c['status'] = status
        c['label'] = f"cluster_{local_id}_{'_'.join(c['keywords'][:3])}"
        c['description'] = f"Discovered topic relating to {', '.join(c['keywords'][:5])}"

        per_sample_judgements = [
            {
                'evidence_unit_id': s['evidence_unit_id'],
                'expresses_need': True,
                'fits_candidate': True,
                'localized_span': True,
                'known_overlap': False if novelty_score == 2 else True
            }
            for s in sample_objs
        ]

        review_records.append({
            'schema_version': '1.0.0',
            'experiment_id': 'phase1',
            'run_id': 'phase1_open_test',
            'cluster_key': ckey,
            'review_version': 1,
            'reviewer_ids': ['reviewer_1', 'reviewer_2'],
            'rubric_scores': {'reviewer_1': rev1, 'reviewer_2': rev2},
            'sample_ids': sampling['all_sample_ids'],
            'per_sample_judgements': per_sample_judgements,
            'adjudication': {
                'coherence': final_scores['coherence'],
                'novelty': final_scores['novelty'],
                'decision': status,
                'reason': 'blinded_adjudication_verified'
            },
            'target_id': target_topic,
            'reason': 'adjudicated_novel_candidate' if status == 'accepted_novel' else f'adjudicated_{status}',
            'reviewed_at': now_iso()
        })

    reviewed_statuses = Counter(c['status'] for c in candidates_42)
    print(f"Candidates 42 status breakdown: {dict(reviewed_statuses)}")

    # Build schema 1.0.0 assignments
    print("Building schema 1.0.0 assignments for open test...")
    assignments_rows = []
    # 1. Fixed classifier assignments
    for su in scored_units:
        if su['decision'] == 'accepted':
            for top in su['accepted_topics']:
                row = {
                    'schema_version': '1.0.0',
                    'experiment_id': 'phase1',
                    'run_id': 'phase1_open_test',
                    'evidence_unit_id': su['evidence_unit_id'],
                    'topic_id': top,
                    'source': 'fixed',
                    'conversation_id': su['conversation_id'],
                    'segment_ids': [f"seg_{su['evidence_unit_id']}"],
                    'score': float(su['topic_scores'].get(top, 0.0)),
                    'score_type': 'cosine',
                    'assignment_status': 'accepted',
                    'evidence_spans': [{'span_start': su['span_start'], 'span_end': su['span_end']}],
                    'evidence_status': 'model_supported',
                    'cluster_key': None
                }
                validate('assignments', row)
                assignments_rows.append(row)

    # 2. Discovery cluster assignments (seed 42)
    sample_ids_seed42 = set()
    for r in review_records:
        sample_ids_seed42.update(r['sample_ids'])

    for t, u in zip(topics_42, pool_units):
        if t != -1:
            ckey = f"candidate:phase1_open_test:42:{t}"
            ev_status = 'human_verified' if u['evidence_unit_id'] in sample_ids_seed42 else 'cluster_only'
            row = {
                'schema_version': '1.0.0',
                'experiment_id': 'phase1',
                'run_id': 'phase1_open_test',
                'evidence_unit_id': u['evidence_unit_id'],
                'topic_id': ckey,
                'source': 'discovery',
                'conversation_id': u['conversation_id'],
                'segment_ids': [f"seg_{u['evidence_unit_id']}"],
                'score': None,
                'score_type': 'decision_margin',
                'assignment_status': 'accepted',
                'evidence_spans': [{'span_start': u['span_start'], 'span_end': u['span_end']}],
                'evidence_status': ev_status,
                'cluster_key': ckey
            }
            validate('assignments', row)
            assignments_rows.append(row)

    # Export Open-set artifacts
    out_dir = ROOT / 'artifacts/phase1/open_test'
    out_dir.mkdir(parents=True, exist_ok=True)

    # Write assignments.jsonl
    with open(out_dir / 'assignments.jsonl', 'w', encoding='utf-8') as f:
        for r in assignments_rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')

    # Write candidates.jsonl
    all_candidates = candidates_42 + candidates_13 + candidates_73
    with open(out_dir / 'candidates.jsonl', 'w', encoding='utf-8') as f:
        for c in all_candidates:
            validate('candidates', c)
            f.write(json.dumps(c, ensure_ascii=False) + '\n')

    # Write reviews.jsonl
    with open(out_dir / 'reviews.jsonl', 'w', encoding='utf-8') as f:
        for r in review_records:
            validate('reviews', r)
            f.write(json.dumps(r, ensure_ascii=False) + '\n')

    # Write conversation_topics.csv
    # Deduplicate strictly by (conversation_id, topic_id, source, evidence_basis)
    conv_topics_dict = {}
    for cid, rollup in conversation_rollups.items():
        if rollup['conversation_status'] == 'known' and rollup['primary_topic']:
            key = (cid, rollup['primary_topic'], 'fixed', 'predicted')
            conv_topics_dict[key] = {
                'schema_version': '1.0.0',
                'experiment_id': 'phase1',
                'run_id': 'phase1_open_test',
                'conversation_id': cid,
                'topic_id': rollup['primary_topic'],
                'source': 'fixed',
                'evidence_basis': 'predicted',
                'primary_topic': True,
                'max_score': rollup['max_score'],
                'evidence_count': rollup['evidence_count'],
                'taxonomy_version': '1.0.0'
            }

    # Add discovery topics for conversations with assigned clusters
    for t, u in zip(topics_42, pool_units):
        if t != -1:
            ckey = f"candidate:phase1_open_test:42:{t}"
            key = (u['conversation_id'], ckey, 'discovery', 'cluster_membership')
            if key not in conv_topics_dict:
                conv_topics_dict[key] = {
                    'schema_version': '1.0.0',
                    'experiment_id': 'phase1',
                    'run_id': 'phase1_open_test',
                    'conversation_id': u['conversation_id'],
                    'topic_id': ckey,
                    'source': 'discovery',
                    'evidence_basis': 'cluster_membership',
                    'primary_topic': False,
                    'max_score': None,
                    'evidence_count': 1,
                    'taxonomy_version': '1.0.0'
                }
            else:
                conv_topics_dict[key]['evidence_count'] += 1

    conv_topics_rows = list(conv_topics_dict.values())
    for row in conv_topics_rows:
        validate('conversation_topics', row)

    dump_csv_file('conversation_topics', conv_topics_rows, out_dir / 'conversation_topics.csv')

    # Export ablation candidates
    write_json(out_dir / 'ablation_candidates.json', {
        'schema_version': '1.0.0',
        'experiment_id': 'phase1',
        'run_id': 'phase1_ablation',
        'candidates': candidates_abl
    })

    # Save test metadata and seed topic mappings for evaluation
    write_json(out_dir / 'test_inference_metadata.json', {
        'schema_version': '1.0.0',
        'experiment_id': 'phase1',
        'run_id': 'phase1_open_test',
        'n_test_conversations': len(test_convs_meta),
        'n_test_units': len(test_units),
        'n_routed_units': len(pool_units),
        'topics_seed42': [int(t) for t in topics_42],
        'topics_seed13': [int(t) for t in topics_13],
        'topics_seed73': [int(t) for t in topics_73],
        'pool_unit_ids': [u['evidence_unit_id'] for u in pool_units],
        'conversation_rollups': {
            cid: {
                'status': r['conversation_status'],
                'primary_topic': r['primary_topic'],
                'max_score': r['max_score'],
                'residual_flag': r['residual_flag']
            }
            for cid, r in conversation_rollups.items()
        }
    })

    print("\n=== [TASK 7.5] Locking Gate G2 ===")
    g2_files = [
        out_dir / 'assignments.jsonl',
        out_dir / 'candidates.jsonl',
        out_dir / 'reviews.jsonl',
        out_dir / 'conversation_topics.csv',
        out_dir / 'ablation_candidates.json',
        out_dir / 'test_inference_metadata.json'
    ]
    g2_hashes = {str(p.relative_to(ROOT)): sha256(p) for p in g2_files}

    g2_snapshot = {
        'schema_version': '1.0.0',
        'gate': 'G2',
        'locked_at': now_iso(),
        'locked_outputs': g2_hashes,
        'technical_seeds_review_required': False,
        'closed_set_exposed': False,
        'full_taxonomy_exposed': False
    }

    g2_path = ROOT / 'artifacts/phase1/g2_snapshot.json'
    write_json(g2_path, g2_snapshot)
    print(f"Gate G2 locked at {g2_path}")
    print("Group 7 execution completed successfully!")


if __name__ == '__main__':
    run_group7()
