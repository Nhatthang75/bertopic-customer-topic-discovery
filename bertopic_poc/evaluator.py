"""Evaluator: fixed classification, unknown detection, flow-family recovery, decision table và clustering metrics."""
from __future__ import annotations
from collections import Counter, defaultdict
import math
from typing import Dict, List, Optional, Set, Tuple


def round8(val: float) -> float:
    return round(val, 8)


def evaluate_decision_table(
    s1: float,
    s2: float,
    tau: float = 0.50,
    delta: float = 0.10
) -> str:
    """
    Quy tắc quyết định trên evidence unit analyzable:
    1. s1 < tau -> unmatched
    2. s1 >= tau và s1 - s2 < delta -> ambiguous
    3. s1 >= tau và s1 - s2 >= delta -> accepted
    """
    s1_r = round8(s1)
    s2_r = round8(s2)
    tau_r = round8(tau)
    delta_r = round8(delta)

    if s1_r < tau_r:
        return 'unmatched'
    margin = round8(s1_r - s2_r)
    if margin < delta_r:
        return 'ambiguous'
    return 'accepted'


def evaluate_fixed_classification(
    predictions: List[Optional[str]],
    ground_truth: List[str],
    classes: List[str]
) -> Dict:
    """
    Đánh giá phân loại Macro-F1, Precision, Recall cấp conversation.
    Abstain (None hoặc rỗng) tính là FN cho class đó.
    """
    tp = Counter()
    fp = Counter()
    fn = Counter()

    for pred, gt in zip(predictions, ground_truth):
        if pred == gt:
            tp[gt] += 1
        else:
            fn[gt] += 1
            if pred in classes:
                fp[pred] += 1

    per_class = {}
    f1s, precs, recs = [], [], []
    for c in classes:
        p_c = tp[c] / (tp[c] + fp[c]) if (tp[c] + fp[c]) > 0 else 0.0
        r_c = tp[c] / (tp[c] + fn[c]) if (tp[c] + fn[c]) > 0 else 0.0
        f1_c = (2 * p_c * r_c) / (p_c + r_c) if (p_c + r_c) > 0 else 0.0
        per_class[c] = {'precision': round8(p_c), 'recall': round8(r_c), 'f1': round8(f1_c), 'support': tp[c] + fn[c]}
        if (tp[c] + fn[c]) > 0:
            precs.append(p_c)
            recs.append(r_c)
            f1s.append(f1_c)

    macro_f1 = sum(f1s) / len(f1s) if f1s else 0.0
    macro_prec = sum(precs) / len(precs) if precs else 0.0
    macro_rec = sum(recs) / len(recs) if recs else 0.0
    accuracy = sum(tp.values()) / len(ground_truth) if ground_truth else 0.0

    return {
        'macro_f1': round8(macro_f1),
        'macro_precision': round8(macro_prec),
        'macro_recall': round8(macro_rec),
        'accuracy': round8(accuracy),
        'per_class': per_class
    }


def evaluate_unknown_detection(
    residual_flags: List[bool],
    is_hidden_ground_truth: List[bool],
    decision_scores: Optional[List[Optional[float]]] = None
) -> Dict:
    """
    Đánh giá phát hiện Unknown (Positive = hidden flow).
    residual_flag=True là Positive prediction (gồm cả mixed).
    Non-need / insufficient_evidence có residual_flag=False nhưng vẫn nằm trong mẫu số (FN nếu hidden).
    """
    tp = 0
    fp = 0
    tn = 0
    fn = 0

    valid_scores = 0
    total = len(residual_flags)

    for pred_pos, is_gt_pos in zip(residual_flags, is_hidden_ground_truth):
        if pred_pos and is_gt_pos:
            tp += 1
        elif pred_pos and not is_gt_pos:
            fp += 1
        elif not pred_pos and is_gt_pos:
            fn += 1
        else:
            tn += 1

    if decision_scores:
        valid_scores = sum(1 for s in decision_scores if s is not None)

    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

    score_cov = valid_scores / total if total > 0 else 1.0

    return {
        'precision': round8(prec),
        'recall': round8(rec),
        'f1': round8(f1),
        'tp': tp,
        'fp': fp,
        'tn': tn,
        'fn': fn,
        'total': total,
        'score_coverage': round8(score_cov)
    }


def evaluate_flow_family_recovery(
    hidden_flows: List[str],
    cluster_conversation_map: Dict[str, Set[str]],
    conversation_hidden_flow_map: Dict[str, str],
    all_hidden_flow_conversations: Dict[str, Set[str]],
    min_support: int = 5,
    min_purity: float = 0.70,
    min_recall: float = 0.30
) -> Dict:
    """
    Đánh giá Flow-family recovery proxy:
    - Với mỗi hidden flow h:
      Cluster c qualifies nếu support >= min_support và purity_h >= min_purity
      U_h = distinct union của conversations thuộc các clusters qualify
      family_precision = |U_h giao S_h| / |U_h|
      family_recall = |U_h giao S_h| / |S_h|
      recovered_proxy = True nếu có cluster qualify, precision >= 0.70 và recall >= 0.30
    """
    results = {}
    recovered_count = 0

    for h in hidden_flows:
        s_h = all_hidden_flow_conversations.get(h, set())
        if not s_h:
            results[h] = {
                'recovered': False,
                'qualifying_clusters': [],
                'family_precision': None,
                'family_recall': 0.0,
                'support': 0,
                'status': 'no_support'
            }
            continue

        qualifying_clusters = []
        for c_id, convs in cluster_conversation_map.items():
            if len(convs) < min_support:
                continue
            # Purity
            h_in_c = sum(1 for cid in convs if conversation_hidden_flow_map.get(cid) == h)
            purity = h_in_c / len(convs)
            if purity >= min_purity:
                qualifying_clusters.append(c_id)

        if not qualifying_clusters:
            results[h] = {
                'recovered': False,
                'qualifying_clusters': [],
                'family_precision': None,
                'family_recall': 0.0,
                'support': len(s_h),
                'status': 'no_qualifying_cluster'
            }
            continue

        # Family Union
        u_h = set()
        for c_id in qualifying_clusters:
            u_h.update(cluster_conversation_map[c_id])

        h_in_u = sum(1 for cid in u_h if conversation_hidden_flow_map.get(cid) == h)
        family_prec = h_in_u / len(u_h) if u_h else 0.0
        family_rec = h_in_u / len(s_h) if s_h else 0.0

        is_recovered = (len(qualifying_clusters) > 0 and family_prec >= min_purity and family_rec >= min_recall)
        if is_recovered:
            recovered_count += 1

        results[h] = {
            'recovered': is_recovered,
            'qualifying_clusters': qualifying_clusters,
            'family_precision': round8(family_prec),
            'family_recall': round8(family_rec),
            'support': len(s_h),
            'status': 'recovered' if is_recovered else 'threshold_not_met'
        }

    return {
        'recovered_flows_count': recovered_count,
        'total_hidden_flows': len(hidden_flows),
        'all_recovered': recovered_count == len(hidden_flows),
        'flows': results
    }


def evaluate_clustering_stability(
    labels_a: List[int],
    labels_b: List[int]
) -> Dict:
    """
    Tính ARI stability qua 2 seed:
    - ARI_all: tính trên toàn bộ units (-1 xem như một nhãn riêng)
    - ARI_shared: tính trên giao các units không phải outlier ở cả 2 seed
    - Degenerate: nếu toàn bộ là outlier hoặc <2 cụm, trả null_reason='degenerate'
    """
    if len(labels_a) != len(labels_b):
        raise ValueError("length_mismatch")

    total = len(labels_a)
    non_outlier_idx = [i for i in range(total) if labels_a[i] != -1 and labels_b[i] != -1]
    shared_cov = len(non_outlier_idx) / total if total > 0 else 0.0

    # Degenerate check: all outlier in either
    if all(x == -1 for x in labels_a) or all(x == -1 for x in labels_b):
        return {
            'ARI_all': 1.0 if labels_a == labels_b else 0.0,
            'ARI_shared': None,
            'shared_coverage': round8(shared_cov),
            'degenerate': True,
            'null_reason': 'degenerate_all_outliers'
        }

    # Simplified ARI calculation for shared
    if len(non_outlier_idx) < 2:
        return {
            'ARI_all': 0.0,
            'ARI_shared': None,
            'shared_coverage': round8(shared_cov),
            'degenerate': True,
            'null_reason': 'insufficient_shared_units'
        }

    sub_a = [labels_a[i] for i in non_outlier_idx]
    sub_b = [labels_b[i] for i in non_outlier_idx]

    # Calculate Adjusted Rand Index
    ari_shared = _compute_ari(sub_a, sub_b)
    ari_all = _compute_ari(labels_a, labels_b)

    return {
        'ARI_all': round8(ari_all),
        'ARI_shared': round8(ari_shared),
        'shared_coverage': round8(shared_cov),
        'degenerate': False,
        'null_reason': None
    }


def _compute_ari(labels_true: List[int], labels_pred: List[int]) -> float:
    """Tính Adjusted Rand Index thuần túy không dùng thư viện ngoài."""
    n = len(labels_true)
    if n <= 1:
        return 1.0

    # Contingency table
    contingency = defaultdict(int)
    row_sum = defaultdict(int)
    col_sum = defaultdict(int)

    for a, b in zip(labels_true, labels_pred):
        contingency[(a, b)] += 1
        row_sum[a] += 1
        col_sum[b] += 1

    comb2 = lambda x: (x * (x - 1)) / 2.0

    sum_comb_c = sum(comb2(v) for v in contingency.values())
    sum_comb_r = sum(comb2(v) for v in row_sum.values())
    sum_comb_col = sum(comb2(v) for v in col_sum.values())
    total_comb = comb2(n)

    if total_comb == 0:
        return 1.0

    expected_index = (sum_comb_r * sum_comb_col) / total_comb
    max_index = (sum_comb_r + sum_comb_col) / 2.0

    if max_index == expected_index:
        return 1.0

    ari = (sum_comb_c - expected_index) / (max_index - expected_index)
    return ari


def bootstrap_ci(
    values: List[float],
    n_replicates: int = 1000,
    seed: int = 42,
    alpha: float = 0.05
) -> Optional[Tuple[float, float]]:
    """Tính Percentile 95% Confidence Interval bằng bootstrap cấp hội thoại."""
    if not values:
        return None
    import random
    rng = random.Random(seed)
    n = len(values)
    means = []
    for _ in range(n_replicates):
        sample = [values[rng.randint(0, n - 1)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    lower_idx = int(n_replicates * (alpha / 2))
    upper_idx = int(n_replicates * (1 - alpha / 2))
    return round8(means[lower_idx]), round8(means[upper_idx])
