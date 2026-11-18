"""Chạy tìm kiếm 16 cấu hình UMAP/HDBSCAN trên Dev routed pool để chọn cấu hình Discovery tối ưu."""
import gzip
import json
from pathlib import Path
import sys
import time
from collections import Counter, defaultdict
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bertopic_poc.io import ROOT, read_json, write_json
from bertopic_poc.taxonomy import KNOWN_K_FLOWS, HIDDEN_DEV_FLOWS, FLOW_DESCRIPTIONS_EN, flow_id
from bertopic_poc.text import Masker, spans, content_status
from bertopic_poc.scorer import score_evidence_unit, EvidenceUnitScore
from bertopic_poc.discovery import build_routed_pool, generate_discovery_grid, build_cluster_candidates
from bertopic_poc.evaluator import round8


def run_discovery_search():
    model_sel = read_json(ROOT / 'artifacts/phase1/model_selection.json')
    winning_model_id = model_sel['winning_model']
    tau = model_sel['parent_thresholds']['tau']
    delta = model_sel['parent_thresholds']['delta']

    print(f"Loading winning model {winning_model_id} (tau={tau}, delta={delta})...")
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

    # 1. Encode 7 known flow descriptions
    desc_texts = [FLOW_DESCRIPTIONS_EN[f] for f in KNOWN_K_FLOWS]
    desc_embs = model.encode(desc_texts, normalize_embeddings=True, show_progress_bar=False)

    # 2. Extract Dev K + H_dev conversations
    print("Reading Dev K + H_dev conversations...")
    dev_allowed = set(KNOWN_K_FLOWS) | set(HIDDEN_DEV_FLOWS)
    dev_units = []
    dev_h_convs = set()

    with gzip.open(ROOT / 'data/raw/abcd_v1.1.json.gz', 'rt', encoding='utf-8') as f:
        data = json.load(f)

    for row in data['dev']:
        flow = row.get('scenario', {}).get('flow')
        if flow in dev_allowed:
            cid = str(row['convo_id'])
            if flow in HIDDEN_DEV_FLOWS:
                dev_h_convs.add(cid)
            for t_idx, (role, text) in enumerate(row.get('original', [])):
                if role == 'customer':
                    m_text = masker(text)
                    for a, b in spans(m_text):
                        span_text = m_text[a:b]
                        c_stat = content_status(span_text)
                        dev_units.append({
                            'conversation_id': cid,
                            'turn_index': t_idx,
                            'span_start': a,
                            'span_end': b,
                            'text': span_text,
                            'content_status': c_stat,
                            'evidence_unit_id': f"{cid}_t{t_idx}_s{a}_{b}",
                            'scenario_flow': flow
                        })

    print(f"Loaded {len(dev_units)} dev units. Dev H_dev conversations: {len(dev_h_convs)}")

    # 3. Score units with winning classifier to identify routed pool
    print("Scoring dev units with winning classifier...")
    analyzable_texts = [u['text'] for u in dev_units]
    unit_embs = model.encode(analyzable_texts, batch_size=32, normalize_embeddings=True, show_progress_bar=False)
    sims = np.dot(unit_embs, desc_embs.T)

    scored_units = []
    for idx, u in enumerate(dev_units):
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
            'text': u['text'],
            'content_status': u['content_status'],
            'decision': scored.decision,
            'scenario_flow': u['scenario_flow']
        })

    # 4. Build Routed Pool
    pool_res = build_routed_pool(scored_units, unit_embs)
    print(f"Routed pool status: {pool_res['status']}, N_pool = {pool_res['n_pool']}")

    if pool_res['status'] != 'ready':
        out_path = ROOT / 'artifacts/phase1/discovery_selection.json'
        write_json(out_path, {
            'schema_version': '1.0.0',
            'experiment_id': 'phase1',
            'run_id': 'discovery_v1',
            'status': pool_res['status'],
            'n_pool': pool_res['n_pool'],
            'best_configuration': None
        })
        print(f"Discovery stopped: {pool_res['status']}.")
        return

    pool_units = pool_res['pool_units']
    pool_embs = pool_res['pool_embeddings']
    pool_texts = [u['text'] for u in pool_units]
    n_pool = pool_res['n_pool']

    # 5. Search 16 UMAP/HDBSCAN Configurations
    grid = generate_discovery_grid()
    print(f"Searching {len(grid)} UMAP + HDBSCAN configurations on Dev routed pool...")

    vectorizer_model = CountVectorizer(ngram_range=(1, 2), min_df=1)
    evaluations = []

    for nn, nc, mcs, ms in grid:
        eff_nn = min(nn, n_pool - 1)
        init_mode = 'random' if nc >= n_pool - 1 else 'spectral'

        t0 = time.time()
        try:
            umap_model = UMAP(
                n_neighbors=eff_nn,
                n_components=nc,
                min_dist=0.0,
                metric='cosine',
                random_state=42,
                init=init_mode
            )
            hdbscan_model = HDBSCAN(
                min_cluster_size=mcs,
                min_samples=ms,
                metric='euclidean',
                cluster_selection_method='eom'
            )

            topic_model = BERTopic(
                embedding_model=model,
                umap_model=umap_model,
                hdbscan_model=hdbscan_model,
                vectorizer_model=vectorizer_model,
                top_n_words=10,
                nr_topics=None,
                verbose=False
            )

            topics, probs = topic_model.fit_transform(pool_texts, pool_embs)
            dur = time.time() - t0

            # Evaluate metrics
            # Outlier rate
            outlier_count = sum(1 for t in topics if t == -1)
            outlier_rate = outlier_count / len(topics) if len(topics) > 0 else 1.0

            # Routing-adjusted coverage on H_dev
            h_dev_convs_in_clusters = set()
            for t, u in zip(topics, pool_units):
                if t != -1 and u['conversation_id'] in dev_h_convs:
                    h_dev_convs_in_clusters.add(u['conversation_id'])
            h_dev_cov = len(h_dev_convs_in_clusters) / len(dev_h_convs) if dev_h_convs else 0.0

            # Macro cluster purity proxy on clusters with support >= 5 convs
            cluster_conv_flows = defaultdict(list)
            for t, u in zip(topics, pool_units):
                if t != -1:
                    cluster_conv_flows[t].append((u['conversation_id'], u['scenario_flow']))

            purities = []
            qualifying_clusters = 0
            for t, conv_flow_list in cluster_conv_flows.items():
                distinct_convs = {c for c, _ in conv_flow_list}
                if len(distinct_convs) >= 5:
                    qualifying_clusters += 1
                    # Max proportion of same flow
                    flow_counts = Counter(f for _, f in conv_flow_list)
                    max_flow_count = max(flow_counts.values())
                    purities.append(max_flow_count / len(conv_flow_list))

            macro_purity = sum(purities) / len(purities) if purities else 0.0
            harmonic = round8((2 * h_dev_cov * macro_purity) / (h_dev_cov + macro_purity)) if (h_dev_cov + macro_purity) > 0 else 0.0

            evaluations.append({
                'n_neighbors': nn,
                'effective_n_neighbors': eff_nn,
                'n_components': nc,
                'min_cluster_size': mcs,
                'min_samples': ms,
                'status': 'success',
                'duration_seconds': round8(dur),
                'qualifying_clusters': qualifying_clusters,
                'outlier_rate': round8(outlier_rate),
                'h_dev_coverage': round8(h_dev_cov),
                'macro_purity': round8(macro_purity),
                'harmonic_mean': harmonic
            })
        except Exception as e:
            evaluations.append({
                'n_neighbors': nn,
                'effective_n_neighbors': eff_nn,
                'n_components': nc,
                'min_cluster_size': mcs,
                'min_samples': ms,
                'status': f'failed:{e}',
                'harmonic_mean': 0.0
            })

    # Selection
    valid_runs = [e for e in evaluations if e.get('status') == 'success' and e.get('qualifying_clusters', 0) > 0]
    dev_failed = False

    if valid_runs:
        best = sorted(
            valid_runs,
            key=lambda e: (e['harmonic_mean'], -e['outlier_rate'], -e['n_neighbors'], -e['n_components'], -e['min_cluster_size'], -e['min_samples']),
            reverse=True
        )[0]
    else:
        # Fallback to (5, 2, 5, 1)
        best = evaluations[0]
        dev_failed = True

    print(f"\nDiscovery selection complete!")
    print(f"Best config: nn={best['n_neighbors']}, nc={best['n_components']}, mcs={best['min_cluster_size']}, ms={best['min_samples']}")
    print(f"Harmonic mean: {best.get('harmonic_mean', 0.0):.4f}, Outlier rate: {best.get('outlier_rate', 1.0):.4f}")
    print(f"Discovery dev failed: {dev_failed}")

    out_path = ROOT / 'artifacts/phase1/discovery_selection.json'
    write_json(out_path, {
        'schema_version': '1.0.0',
        'experiment_id': 'phase1',
        'run_id': 'discovery_v1',
        'best_configuration': best,
        'discovery_dev_failed': dev_failed,
        'all_evaluations': evaluations
    })
    print(f"Saved discovery selection to {out_path}.")


if __name__ == '__main__':
    run_discovery_search()
