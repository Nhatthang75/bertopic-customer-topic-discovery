"""Quản lý cohorts S/S_cs/S_os và 4 đơn vị thống kê: message, segment, mention, conversation."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from .taxonomy import KNOWN_K_FLOWS, HIDDEN_FINAL_FLOWS


@dataclass
class StatisticsScope:
    scope_id: str
    eligible_conversation_ids: Set[str]
    total_customer_messages: int
    experiment_id: str = "phase1"
    run_id: str = "run_default"


def build_topic_statistics(
    scope: StatisticsScope,
    topic_id: str,
    source: str,
    evidence_basis: str,
    assignments: List[Dict],
    reviewed_scope_conversation_ids: Optional[Set[str]] = None
) -> Dict:
    """
    Tính toán 4 đơn vị đếm cho một topic trong một scope:
    - customer_message_count: tổng lượt khách trong scope (lặp rõ ràng ở các dòng topic)
    - source_messages_with_assignment: số customer turn có assignment topic này
    - segment_count: số segment/window có assignment topic này
    - mention_count: số (convo_id, turn_index, topic) có localized evidence; null nếu cluster_only hoặc chưa review
    - conversation_count: số distinct conversation có assignment topic này trong scope
    - conversation_share: conversation_count / eligible_conversations
    """
    eligible_convs = scope.eligible_conversation_ids
    denom = len(eligible_convs)
    if denom == 0:
        return {
            'schema_version': '1.0.0',
            'experiment_id': scope.experiment_id,
            'run_id': scope.run_id,
            'scope_id': scope.scope_id,
            'topic_id': topic_id,
            'source': source,
            'evidence_basis': evidence_basis,
            'customer_message_count': 0,
            'source_messages_with_assignment': 0,
            'segment_count': 0,
            'mention_count': None,
            'conversation_count': 0,
            'eligible_conversations': 0,
            'conversation_share': None,
            'evidence_coverage': 0.0,
            'unique_customers': None,
            'time_bucket': None,
            'channel': None,
            'null_reason': 'empty_scope'
        }

    # Filter assignments for this topic and scope
    matching_assignments = [
        a for a in assignments
        if a.get('topic_id') == topic_id and a.get('conversation_id') in eligible_convs
    ]

    matched_convs = {a['conversation_id'] for a in matching_assignments}
    conversation_count = len(matched_convs)
    conversation_share = round(conversation_count / denom, 8) if denom > 0 else None

    # Distinct segments
    distinct_segments = set()
    for a in matching_assignments:
        for sid in a.get('segment_ids', []):
            distinct_segments.add(sid)
    segment_count = len(distinct_segments)

    # Source messages (customer turns) with assignment
    source_message_keys = {
        (a['conversation_id'], span.get('turn_index'))
        for a in matching_assignments
        for span in a.get('evidence_spans', [])
        if span.get('turn_index') is not None
    }
    source_messages_with_assignment = len(source_message_keys)

    # Mention count logic based on evidence_basis
    null_reason = None
    mention_count = None

    if evidence_basis == 'cluster_membership':
        null_reason = 'missing_localized_evidence'
        mention_count = None
    elif evidence_basis == 'verified':
        if reviewed_scope_conversation_ids is None or not eligible_convs.issubset(reviewed_scope_conversation_ids):
            null_reason = 'unreviewed_scope'
            mention_count = None
        else:
            # Verified mentions
            mention_count = len(source_message_keys)
    elif evidence_basis == 'predicted':
        # Localized model_supported evidence spans
        localized_spans = {
            (a['conversation_id'], span.get('turn_index'), topic_id)
            for a in matching_assignments
            for span in a.get('evidence_spans', [])
            if span.get('turn_index') is not None
        }
        mention_count = len(localized_spans)
        if mention_count == 0 and conversation_count > 0:
            mention_count = None
            null_reason = 'missing_localized_evidence'

    evidence_coverage = round(conversation_count / denom, 8) if denom > 0 else 0.0

    return {
        'schema_version': '1.0.0',
        'experiment_id': scope.experiment_id,
        'run_id': scope.run_id,
        'scope_id': scope.scope_id,
        'topic_id': topic_id,
        'source': source,
        'evidence_basis': evidence_basis,
        'customer_message_count': scope.total_customer_messages,
        'source_messages_with_assignment': source_messages_with_assignment,
        'segment_count': segment_count,
        'mention_count': mention_count,
        'conversation_count': conversation_count,
        'eligible_conversations': denom,
        'conversation_share': conversation_share,
        'evidence_coverage': evidence_coverage,
        'unique_customers': None,
        'time_bucket': None,
        'channel': None,
        'null_reason': null_reason
    }


def roll_up_flow_statistics(
    scope: StatisticsScope,
    flow_id: str,
    source: str,
    evidence_basis: str,
    child_assignments: List[Dict]
) -> Dict:
    """
    Roll-up thống kê lên cấp Flow dùng distinct union của conversations,
    không cộng dồn để tránh đếm trùng.
    """
    raw_flow_name = flow_id.removeprefix('flow:')
    subflow_prefix = f"subflow:{raw_flow_name}/"
    mapped_assignments = []
    for a in child_assignments:
        tid = a.get('topic_id', '')
        if tid == flow_id or tid.startswith(subflow_prefix):
            mapped_assignments.append(dict(a, topic_id=flow_id))

    return build_topic_statistics(
        scope=scope,
        topic_id=flow_id,
        source=source,
        evidence_basis=evidence_basis,
        assignments=mapped_assignments
    )
