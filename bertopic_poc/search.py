"""Tìm kiếm mô hình, ngưỡng tương đồng (tau, delta) và baseline trên tập Train K / Dev K + H_dev."""
from __future__ import annotations
import math
from typing import Dict, List, Optional, Tuple
from bertopic_poc.evaluator import round8, evaluate_fixed_classification, evaluate_unknown_detection
from bertopic_poc.scorer import score_evidence_unit, roll_up_conversation_status, EvidenceUnitScore
from bertopic_poc.taxonomy import KNOWN_K_FLOWS, FLOW_DESCRIPTIONS_EN, flow_id, subflow_id, FLOW_SUBFLOW_CANONICAL


def generate_parent_grid() -> List[Tuple[float, float]]:
    """Tạo 52 cấu hình (tau, delta) cho parent similarity."""
    taus = [round8(0.20 + i * 0.05) for i in range(13)]  # 0.20 to 0.80
    deltas = [0.0, 0.05, 0.10, 0.15]
    grid = []
    for t in taus:
        for d in deltas:
            grid.append((t, d))
    return grid


def search_similarity_grid(
    dev_units_scores: List[List[Dict[str, float]]],
    dev_unit_metadata: List[Dict],
    dev_labels: List[str],
    known_classes: List[str],
    hidden_dev_flow: str = 'shipping_issue',
    grid: Optional[List[Tuple[float, float]]] = None
) -> Dict:
    """
    Chạy grid search 52 cấu hình (tau, delta) trên tập Dev K + H_dev:
    - dev_units_scores: danh sách các hội thoại, mỗi hội thoại gồm danh sách các dict {flow_id: cosine_score}
    - dev_unit_metadata: metadata tương ứng cho mỗi unit (content_status, offsets...)
    - dev_labels: ground truth flow của mỗi hội thoại
    - Tiêu chí: unknown F1 >= 0.60 rồi maximize known Macro-F1.
    - Fallback: harmonic mean của known Macro-F1 và unknown F1 cao nhất, gắn dev_constraint_failed=True.
    - Tie-break: unknown F1 desc, tau asc, delta asc.
    """
    if grid is None:
        grid = generate_parent_grid()

    is_hidden_gt = [label == hidden_dev_flow for label in dev_labels]
    known_idx = [i for i, h in enumerate(is_hidden_gt) if not h]

    all_results = []

    for tau, delta in grid:
        preds = []
        residual_flags = []

        for conv_scores, conv_meta in zip(dev_units_scores, dev_unit_metadata):
            unit_res = []
            for scores_dict, meta in zip(conv_scores, conv_meta):
                u_score = score_evidence_unit(
                    unit_id=meta.get('evidence_unit_id', ''),
                    conversation_id=meta.get('conversation_id', ''),
                    turn_index=meta.get('customer_turn_index', 0),
                    span_start=meta.get('span_start', 0),
                    span_end=meta.get('span_end', 0),
                    content_status=meta.get('content_status', 'analyzable'),
                    topic_scores=scores_dict,
                    tau=tau,
                    delta=delta
                )
                unit_res.append(u_score)

            roll = roll_up_conversation_status(unit_res)
            preds.append(roll['primary_topic'])
            residual_flags.append(roll['residual_flag'])

        # Fixed evaluation on known dev samples
        known_preds = [preds[i] for i in known_idx]
        known_gt = [dev_labels[i] for i in known_idx]
        fixed_res = evaluate_fixed_classification(known_preds, known_gt, known_classes)

        # Unknown evaluation on all dev samples
        unknown_res = evaluate_unknown_detection(residual_flags, is_hidden_gt)

        macro_f1 = fixed_res['macro_f1']
        unknown_f1 = unknown_res['f1']
        harmonic = round8((2 * macro_f1 * unknown_f1) / (macro_f1 + unknown_f1)) if (macro_f1 + unknown_f1) > 0 else 0.0

        all_results.append({
            'tau': tau,
            'delta': delta,
            'macro_f1': macro_f1,
            'unknown_f1': unknown_f1,
            'harmonic_mean': harmonic,
            'fixed_metrics': fixed_res,
            'unknown_metrics': unknown_res
        })

    # Selection
    qualifying = [r for r in all_results if r['unknown_f1'] >= 0.60]
    dev_constraint_failed = False

    if qualifying:
        # Maximize known Macro-F1, tie: unknown F1 desc, tau asc, delta asc
        best = sorted(
            qualifying,
            key=lambda r: (r['macro_f1'], r['unknown_f1'], -r['tau'], -r['delta']),
            reverse=True
        )[0]
    else:
        # Fallback: harmonic mean, tie: unknown F1 desc, tau asc, delta asc
        best = sorted(
            all_results,
            key=lambda r: (r['harmonic_mean'], r['unknown_f1'], -r['tau'], -r['delta']),
            reverse=True
        )[0]
        dev_constraint_failed = True

    return {
        'best_configuration': best,
        'dev_constraint_failed': dev_constraint_failed,
        'all_evaluations': all_results
    }
