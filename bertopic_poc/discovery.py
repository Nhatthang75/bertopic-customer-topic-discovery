"""Discovery: Routed pool extraction, UMAP/HDBSCAN grid search, Candidate creation và Merge DAG validation."""
from __future__ import annotations
from collections import Counter, defaultdict
import hashlib
from typing import Dict, List, Optional, Set, Tuple
import numpy as np

from bertopic_poc.evaluator import round8


def build_routed_pool(
    unit_records: List[Dict],
    unit_embeddings: Optional[np.ndarray] = None
) -> Dict:
    """
    Tạo routed pool theo evidence unit:
    - Chỉ lấy units analyzable có decision thuộc ('unmatched', 'ambiguous')
    - Loại bỏ non_need và insufficient_evidence
    - Gom window embeddings theo unit: trung bình L2-normalized window embeddings rồi L2-normalize
    - Trả về status 'ready', 'empty_pool', hoặc 'insufficient_pool' nếu N_pool < 3
    """
    eligible_units = []
    indices = []

    for idx, u in enumerate(unit_records):
        status = u.get('content_status', 'analyzable')
        decision = u.get('decision', 'unmatched')
        if status in ('non_need', 'insufficient_evidence'):
            continue
        if decision in ('unmatched', 'ambiguous'):
            eligible_units.append(u)
            indices.append(idx)

    n_pool = len(eligible_units)
    if n_pool == 0:
        return {'status': 'empty_pool', 'pool_units': [], 'pool_embeddings': None, 'n_pool': 0}
    if n_pool < 3:
        return {'status': 'insufficient_pool', 'pool_units': eligible_units, 'pool_embeddings': None, 'n_pool': n_pool}

    # Extract or aggregate embeddings
    pool_embs = None
    if unit_embeddings is not None and len(indices) > 0:
        pool_embs = unit_embeddings[indices]
        # Ensure L2 normalization
        norms = np.linalg.norm(pool_embs, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        pool_embs = pool_embs / norms

    return {
        'status': 'ready',
        'pool_units': eligible_units,
        'pool_embeddings': pool_embs,
        'n_pool': n_pool
    }


def generate_discovery_grid() -> List[Tuple[int, int, int, int]]:
    """Tạo 16 cấu hình (n_neighbors, n_components, min_cluster_size, min_samples)."""
    grid = []
    for nn in (5, 15):
        for nc in (2, 5):
            for mcs in (5, 10):
                for ms in (1, 5):
                    grid.append((nn, nc, mcs, ms))
    return grid


def build_cluster_candidates(
    labels: List[int],
    pool_units: List[Dict],
    run_id: str,
    seed: int,
    top_keywords_map: Optional[Dict[int, List[str]]] = None
) -> List[Dict]:
    """
    Tạo cluster candidate rows:
    - Outlier (-1) không tạo candidate row
    - Support tính theo số distinct conversation_id
    - Support >= 5 -> status 'proposed', < 5 -> status 'monitor'
    - cluster_key = f"candidate:{run_id}:{seed}:{local_cluster_id}"
    """
    cluster_to_convs = defaultdict(set)
    cluster_to_units = defaultdict(list)

    for label, u in zip(labels, pool_units):
        if label == -1:
            continue
        cluster_to_convs[label].add(u['conversation_id'])
        cluster_to_units[label].append(u['evidence_unit_id'])

    candidates = []
    for local_id in sorted(cluster_to_convs.keys()):
        conv_support = len(cluster_to_convs[local_id])
        status = 'proposed' if conv_support >= 5 else 'monitor'
        c_key = f"candidate:{run_id}:{seed}:{local_id}"
        kw = top_keywords_map.get(local_id, []) if top_keywords_map else []

        candidates.append({
            'schema_version': '1.0.0',
            'experiment_id': 'phase1',
            'run_id': run_id,
            'cluster_key': c_key,
            'seed': seed,
            'local_cluster_id': local_id,
            'keywords': kw[:10],
            'representative_unit_ids': cluster_to_units[local_id][:5],
            'random_unit_ids': cluster_to_units[local_id][5:10],
            'conversation_support': conv_support,
            'label': None,
            'description': None,
            'status': status,
            'review_version': 1
        })

    return candidates


def validate_merge_dag(
    merge_edges: List[Tuple[str, str]],
    current_run_candidates: Set[str],
    known_topics: Set[str]
) -> Tuple[bool, Optional[str]]:
    """
    Kiểm tra tính hợp lệ của Merge DAG:
    - source phải là candidate trong run hiện tại
    - target phải là known topic hợp lệ hoặc candidate cùng run
    - cấm self-merge (A -> A)
    - cấm chu trình (cycle)
    - cấm target khác run
    Trả về (is_valid, error_reason)
    """
    graph = defaultdict(set)
    valid_targets = current_run_candidates | known_topics

    for src, tgt in merge_edges:
        if src not in current_run_candidates:
            return False, f"invalid_source:{src}"
        if tgt not in valid_targets:
            return False, f"invalid_target:{tgt}"
        if src == tgt:
            return False, f"self_merge:{src}"
        graph[src].add(tgt)

    # Cycle detection via DFS
    visited = set()
    rec_stack = set()

    def has_cycle(node):
        visited.add(node)
        rec_stack.add(node)
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                if has_cycle(neighbor):
                    return True
            elif neighbor in rec_stack:
                return True
        rec_stack.remove(node)
        return False

    for node in graph:
        if node not in visited:
            if has_cycle(node):
                return False, f"cycle_detected:{node}"

    return True, None
