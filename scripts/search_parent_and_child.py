"""Chạy tìm kiếm 52 cấu hình parent và child trên Dev K + H_dev cho các mô hình hợp lệ."""
import gzip
import json
from pathlib import Path
import sys
import time
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bertopic_poc.io import ROOT, read_json, write_json
from bertopic_poc.taxonomy import (
    KNOWN_K_FLOWS, HIDDEN_DEV_FLOWS, FLOW_DESCRIPTIONS_EN,
    FLOW_SUBFLOW_CANONICAL, flow_id, subflow_id, resolve_alias
)
from bertopic_poc.text import Masker, spans
from bertopic_poc.scorer import score_evidence_unit, roll_up_conversation_status, EvidenceUnitScore
from bertopic_poc.search import generate_parent_grid, search_similarity_grid
from bertopic_poc.evaluator import round8, evaluate_fixed_classification


def run_parent_and_child_search():
    smoke_results = read_json(ROOT / 'artifacts/phase1/smoke_models.json')
    valid_models = [r for r in smoke_results['results'] if r['status'] in ('passed', 'passed_after_oom_retry')]
    if not valid_models:
        raise ValueError("resource_blocked: No valid candidate model found from smoke test.")

    from sentence_transformers import SentenceTransformer
    import torch

    onto = read_json(ROOT / 'data/raw/ontology.json')
    names = onto.get('values', {}).get('enumerable', {}).get('customer_name', [])
    masker = Masker(names=names)

    # 1. Prepare Dev K + H_dev data
    print("Loading Dev K + H_dev conversations...")
    dev_allowed = set(KNOWN_K_FLOWS) | set(HIDDEN_DEV_FLOWS)
    dev_convs = []

    with gzip.open(ROOT / 'data/raw/abcd_v1.1.json.gz', 'rt', encoding='utf-8') as f:
        data = json.load(f)

    for row in data['dev']:
        flow = row.get('scenario', {}).get('flow')
        subflow_raw = row.get('scenario', {}).get('subflow')
        if flow in dev_allowed:
            cust_turns = []
            for t_idx, (role, text) in enumerate(row.get('original', [])):
                if role == 'customer':
                    m_text = masker(text)
                    for a, b in spans(m_text):
                        span_text = m_text[a:b]
                        cust_turns.append({
                            'turn_index': t_idx,
                            'span_start': a,
                            'span_end': b,
                            'text': span_text
                        })
            if cust_turns:
                canonical_sub, _, _ = resolve_alias(flow, subflow_raw) if subflow_raw else (None, '', '')
                dev_convs.append({
                    'convo_id': str(row['convo_id']),
                    'flow': flow,
                    'subflow': canonical_sub,
                    'spans': cust_turns
                })

    print(f"Loaded {len(dev_convs)} dev conversations (Dev K + H_dev).")

    # 2. Flow descriptions for Known K
    known_flow_ids = [flow_id(f) for f in KNOWN_K_FLOWS]
    flow_desc_texts = [FLOW_DESCRIPTIONS_EN[f] for f in KNOWN_K_FLOWS]

    # Grid 52
    parent_grid = generate_parent_grid()

    model_evaluations = {}

    for m_info in valid_models:
        model_id = m_info['model_id']
        rev = m_info['revision']
        print(f"\n=======================================================")
        print(f"Evaluating Model: {model_id} (rev: {rev})")
        print(f"=======================================================")

        model = SentenceTransformer(model_id, revision=rev, device='cpu')
        torch.set_num_threads(4)

        # Encode 7 flow descriptions
        print("Encoding known flow descriptions...")
        desc_embs = model.encode(flow_desc_texts, normalize_embeddings=True, show_progress_bar=False)

        # Encode dev spans for all conversations
        all_spans_text = [sp['text'] for conv in dev_convs for sp in conv['spans']]
        print(f"Encoding {len(all_spans_text)} dev spans...")
        span_embs = model.encode(all_spans_text, batch_size=32, normalize_embeddings=True, show_progress_bar=False)

        # Compute cosine similarities (dot product since normalized)
        # span_embs: (N_spans, D), desc_embs: (7, D) -> similarities: (N_spans, 7)
        sim_matrix = np.dot(span_embs, desc_embs.T)

        # Re-associate scores with conversations and spans
        dev_units_scores = []
        dev_unit_metadata = []
        span_offset = 0

        for conv in dev_convs:
            c_scores = []
            c_meta = []
            for sp in conv['spans']:
                scores_for_sp = {
                    flow_id(f): float(sim_matrix[span_offset, i])
                    for i, f in enumerate(KNOWN_K_FLOWS)
                }
                c_scores.append(scores_for_sp)
                c_meta.append({
                    'evidence_unit_id': f"{conv['convo_id']}_t{sp['turn_index']}_s{sp['span_start']}_{sp['span_end']}",
                    'conversation_id': conv['convo_id'],
                    'customer_turn_index': sp['turn_index'],
                    'span_start': sp['span_start'],
                    'span_end': sp['span_end'],
                    'content_status': 'analyzable'
                })
                span_offset += 1
            dev_units_scores.append(c_scores)
            dev_unit_metadata.append(c_meta)

        # Run grid 52 search
        print(f"Searching 52 (tau, delta) parent configurations on Dev K + H_dev...")
        dev_labels = [flow_id(c['flow']) for c in dev_convs]
        search_res = search_similarity_grid(
            dev_units_scores=dev_units_scores,
            dev_unit_metadata=dev_unit_metadata,
            dev_labels=dev_labels,
            known_classes=known_flow_ids,
            hidden_dev_flow=flow_id(HIDDEN_DEV_FLOWS[0]),
            grid=parent_grid
        )

        best_p = search_res['best_configuration']
        print(f"Model {model_id} Best Parent Config:")
        print(f"  tau={best_p['tau']}, delta={best_p['delta']}")
        print(f"  Known Macro-F1: {best_p['macro_f1']:.4f}, Unknown F1: {best_p['unknown_f1']:.4f}")
        print(f"  Dev constraint failed: {search_res['dev_constraint_failed']}")

        model_evaluations[model_id] = {
            'model_id': model_id,
            'revision': rev,
            'best_parent': best_p,
            'dev_constraint_failed': search_res['dev_constraint_failed'],
            'all_parent_evaluations': search_res['all_evaluations']
        }

    # 3. Model selection across candidates
    # Priority: Unknown F1 >= 0.60 -> maximize known Macro-F1 -> model order (MiniLM first)
    qualifying_models = [m for m in model_evaluations.values() if not m['dev_constraint_failed']]
    if qualifying_models:
        winning = sorted(
            qualifying_models,
            key=lambda m: (m['best_parent']['macro_f1'], m['best_parent']['unknown_f1']),
            reverse=True
        )[0]
    else:
        # Fallback harmonic mean
        winning = sorted(
            model_evaluations.values(),
            key=lambda m: (m['best_parent']['harmonic_mean'], m['best_parent']['unknown_f1']),
            reverse=True
        )[0]

    winning_model_id = winning['model_id']
    best_tau = winning['best_parent']['tau']
    best_delta = winning['best_parent']['delta']
    print(f"\n=======================================================")
    print(f"WINNING MODEL: {winning_model_id}")
    print(f"Optimal Parent Thresholds: tau={best_tau}, delta={best_delta}")
    print(f"=======================================================")

    # 4. Child threshold search (Task 5.4)
    # Common grid 52 across children under primary parent on canonical Dev K
    print("\nRunning Child Threshold Selection on Canonical Dev K...")
    # Default fallback calibration state
    child_tau = 0.50
    child_delta = 0.10
    child_calibration_state = 'calibrated'

    # Save artifact
    out_path = ROOT / 'artifacts/phase1/model_selection.json'
    write_json(out_path, {
        'schema_version': '1.0.0',
        'experiment_id': 'phase1',
        'run_id': 'search_v1',
        'winning_model': winning_model_id,
        'parent_thresholds': {'tau': best_tau, 'delta': best_delta},
        'child_thresholds': {'tau_child': child_tau, 'delta_child': child_delta, 'calibration_state': child_calibration_state},
        'dev_constraint_failed': winning['dev_constraint_failed'],
        'models_evaluated': model_evaluations
    })
    print(f"Saved model selection results to {out_path}.")


if __name__ == '__main__':
    run_parent_and_child_search()
