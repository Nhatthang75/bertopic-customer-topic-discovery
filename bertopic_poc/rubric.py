"""Rubric đánh giá chất lượng cụm phát hiện chủ đề mới và bộ chọn mẫu 5 đại diện + 5 ngẫu nhiên."""
from __future__ import annotations
import hashlib
from typing import Dict, List, Optional, Set, Tuple


def select_review_samples(
    cluster_units: List[Dict],
    seed: int = 42,
    run_id: str = "run_default",
    cluster_key: str = "cluster_0"
) -> Dict[str, List[str]]:
    """
    Chọn tối đa 5 đơn vị đại diện (representative) gần centroid nhất từ các conversation khác nhau,
    và tối đa 5 đơn vị ngẫu nhiên (random) từ các conversation còn lại theo hash(seed, run_id, cluster_key, unit_id).
    Mỗi conversation chỉ xuất hiện tối đa 1 lần trong tập mẫu.
    """
    seen_convs: Set[str] = set()
    representative_unit_ids: List[str] = []

    # Sort units by distance to centroid (nếu có distance)
    sorted_by_dist = sorted(cluster_units, key=lambda u: u.get('distance_to_centroid', 0.0))
    for u in sorted_by_dist:
        cid = u['conversation_id']
        if cid not in seen_convs:
            seen_convs.add(cid)
            representative_unit_ids.append(u['evidence_unit_id'])
            if len(representative_unit_ids) >= 5:
                break

    # Pick up to 5 random units from remaining distinct conversations
    remaining = [u for u in cluster_units if u['conversation_id'] not in seen_convs]

    def hash_key(u):
        h = hashlib.sha256(f"{seed}:{run_id}:{cluster_key}:{u['evidence_unit_id']}".encode()).hexdigest()
        return h

    sorted_random = sorted(remaining, key=hash_key)
    random_unit_ids: List[str] = []
    for u in sorted_random:
        cid = u['conversation_id']
        if cid not in seen_convs:
            seen_convs.add(cid)
            random_unit_ids.append(u['evidence_unit_id'])
            if len(random_unit_ids) >= 5:
                break

    return {
        'representative_unit_ids': representative_unit_ids,
        'random_unit_ids': random_unit_ids,
        'all_sample_ids': representative_unit_ids + random_unit_ids
    }


def evaluate_rubric_adjudication(
    support_conversations: int,
    reviewer1_scores: Dict[str, int],
    reviewer2_scores: Dict[str, int],
    adjudication: Optional[Dict[str, int]] = None,
    target_known_topic: Optional[str] = None
) -> Tuple[str, Dict]:
    """
    Đánh giá quyết định cluster:
    - Coherence: 0, 1, 2 (cần >=80% sample confirm)
    - Novelty: 0 (trùng known), 1 (chưa chắc), 2 (mới rõ rệt)
    Trả về (status, final_scores)
    status thuộc: 'accepted_novel', 'merged', 'rejected', 'monitor', 'pending'
    """
    if reviewer1_scores is None or reviewer2_scores is None:
        return 'pending', {'reason': 'missing_reviewer'}

    coherence = adjudication.get('coherence') if adjudication else min(reviewer1_scores.get('coherence', 0), reviewer2_scores.get('coherence', 0))
    novelty = adjudication.get('novelty') if adjudication else min(reviewer1_scores.get('novelty', 0), reviewer2_scores.get('novelty', 0))

    final = {'coherence': coherence, 'novelty': novelty}

    if support_conversations < 5:
        return 'monitor', final

    if novelty == 0 and target_known_topic:
        return 'merged', final

    if coherence == 2 and novelty == 2:
        return 'accepted_novel', final

    if coherence == 0:
        return 'rejected', final

    return 'monitor', final
