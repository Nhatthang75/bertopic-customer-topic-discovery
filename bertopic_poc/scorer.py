"""Similarity scorer, evidence window aggregation, decision table và conversation roll-up."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from bertopic_poc.evaluator import round8, evaluate_decision_table


@dataclass
class EvidenceUnitScore:
    evidence_unit_id: str
    conversation_id: str
    customer_turn_index: int
    span_start: int
    span_end: int
    content_status: str
    s1: float
    s2: float
    top1_topic: str
    top2_topic: Optional[str]
    decision: str  # 'accepted', 'ambiguous', 'unmatched', 'non_need', 'insufficient_evidence'


def score_evidence_unit(
    unit_id: str,
    conversation_id: str,
    turn_index: int,
    span_start: int,
    span_end: int,
    content_status: str,
    topic_scores: Dict[str, float],
    tau: float = 0.50,
    delta: float = 0.10
) -> EvidenceUnitScore:
    """
    Chấm điểm một evidence unit:
    - Nếu content_status != 'analyzable' -> trả decision tương ứng, không gán topic
    - Sắp score giảm dần, tie ID tăng dần
    - Quyết định accepted / ambiguous / unmatched theo tau và delta
    """
    if content_status in ('non_need', 'insufficient_evidence'):
        return EvidenceUnitScore(
            evidence_unit_id=unit_id,
            conversation_id=conversation_id,
            customer_turn_index=turn_index,
            span_start=span_start,
            span_end=span_end,
            content_status=content_status,
            s1=0.0,
            s2=0.0,
            top1_topic='',
            top2_topic=None,
            decision=content_status
        )

    # Sort topics by score desc, topic_id asc
    sorted_topics = sorted(
        topic_scores.items(),
        key=lambda item: (-round8(item[1]), item[0])
    )

    if not sorted_topics:
        return EvidenceUnitScore(
            evidence_unit_id=unit_id,
            conversation_id=conversation_id,
            customer_turn_index=turn_index,
            span_start=span_start,
            span_end=span_end,
            content_status=content_status,
            s1=0.0,
            s2=0.0,
            top1_topic='',
            top2_topic=None,
            decision='unmatched'
        )

    t1, s1 = sorted_topics[0]
    t2, s2 = sorted_topics[1] if len(sorted_topics) > 1 else (None, 0.0)

    s1_r = round8(s1)
    s2_r = round8(s2) if t2 else 0.0

    decision = evaluate_decision_table(s1_r, s2_r, tau=tau, delta=delta)

    return EvidenceUnitScore(
        evidence_unit_id=unit_id,
        conversation_id=conversation_id,
        customer_turn_index=turn_index,
        span_start=span_start,
        span_end=span_end,
        content_status=content_status,
        s1=s1_r,
        s2=s2_r,
        top1_topic=t1,
        top2_topic=t2,
        decision=decision
    )


def aggregate_windows_max_score(
    window_scores: List[Dict[str, float]]
) -> Dict[str, float]:
    """Gộp điểm qua các cửa sổ của một evidence unit bằng max, không cộng."""
    max_scores: Dict[str, float] = {}
    for w in window_scores:
        for t, s in w.items():
            if t not in max_scores or s > max_scores[t]:
                max_scores[t] = s
    return {t: round8(s) for t, s in max_scores.items()}


def roll_up_conversation_status(
    unit_scores: List[EvidenceUnitScore]
) -> Dict:
    """
    Hợp trạng thái hội thoại:
    - Kset = known labels accepted từ các spans
    - Rset = units unmatched hoặc ambiguous
    - conversation_status: non_need, insufficient_evidence, known, unknown_candidate, mixed
    - primary_topic: accepted flow có max score qua các units, tie ID asc; nếu rỗng -> None (abstain)
    - residual_flag: True nếu Rset không rỗng
    """
    if not unit_scores:
        return {
            'conversation_status': 'non_need',
            'primary_topic': None,
            'residual_flag': False,
            'accepted_topics': set(),
            'has_insufficient_evidence': False
        }

    k_set = set()
    r_set = set()
    all_non_need = True
    has_insufficient = False

    best_accepted_score = -1.0
    primary_topic = None

    for u in unit_scores:
        if u.content_status == 'non_need':
            continue
        all_non_need = False

        if u.content_status == 'insufficient_evidence':
            has_insufficient = True
            continue

        if u.decision == 'accepted':
            k_set.add(u.top1_topic)
            if u.s1 > best_accepted_score or (u.s1 == best_accepted_score and (primary_topic is None or u.top1_topic < primary_topic)):
                best_accepted_score = u.s1
                primary_topic = u.top1_topic
        elif u.decision in ('unmatched', 'ambiguous'):
            r_set.add(u.evidence_unit_id)

    if all_non_need:
        status = 'non_need'
    elif not k_set and not r_set and has_insufficient:
        status = 'insufficient_evidence'
    elif k_set and not r_set:
        status = 'known'
    elif not k_set and r_set:
        status = 'unknown_candidate'
    else:  # k_set and r_set
        status = 'mixed'

    residual_flag = len(r_set) > 0

    return {
        'conversation_status': status,
        'primary_topic': primary_topic,
        'residual_flag': residual_flag,
        'accepted_topics': k_set,
        'has_insufficient_evidence': has_insufficient
    }
