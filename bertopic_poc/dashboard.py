"""Dashboard service and reader: reads pre-computed schema 1.0.0 artifacts without fitting any models."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, List, Optional, Any

from .io import ROOT, read_json
from .contracts import csv_load


def load_dashboard_state(artifacts_root: Optional[Path] = None) -> Dict[str, Any]:
    """
    Đọc toàn bộ artifacts của run mà KHÔNG fit bất kỳ mô hình nào:
    - run_manifest.json
    - data_quality.json
    - topic_statistics.csv
    - conversation_topics.csv
    - candidates.jsonl
    - reviews.jsonl
    - metrics.json
    - report.md
    """
    if artifacts_root is None:
        artifacts_root = ROOT / 'artifacts/phase1'

    cons_dir = artifacts_root / 'consolidated'
    eval_dir = artifacts_root / 'evaluation'

    manifest = read_json(artifacts_root / 'run_manifest.json')
    data_quality = read_json(cons_dir / 'data_quality.json')
    metrics_data = read_json(eval_dir / 'metrics.json')

    # Read candidates
    candidates = []
    with open(cons_dir / 'candidates.jsonl', 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                candidates.append(json.loads(line))

    # Read reviews
    reviews = []
    with open(cons_dir / 'reviews.jsonl', 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                reviews.append(json.loads(line))

    # Read conversation_topics
    conv_topics_text = (cons_dir / 'conversation_topics.csv').read_text(encoding='utf-8')
    conv_topics = csv_load(conv_topics_text)

    # Read topic_statistics
    topic_stats_text = (cons_dir / 'topic_statistics.csv').read_text(encoding='utf-8')
    topic_stats = csv_load(topic_stats_text)

    # Read report.md
    report_text = (eval_dir / 'report.md').read_text(encoding='utf-8')

    return {
        'run_manifest': manifest,
        'data_quality': data_quality,
        'metrics': metrics_data,
        'candidates': candidates,
        'reviews': reviews,
        'conversation_topics': conv_topics,
        'topic_statistics': topic_stats,
        'report_markdown': report_text,
        'benchmark_validity': manifest.get('benchmark_validity', 'valid_with_declared_test_exposure'),
        'gates': manifest.get('gate_events', [])
    }


def render_terminal_dashboard(state: Dict[str, Any]) -> str:
    """Render a text summary view of the dashboard for CLI demonstration."""
    m = state['run_manifest']
    metrics = state['metrics']
    dq = state['data_quality']

    lines = [
        "==================================================================",
        "          BERTOPIC CUSTOMER CONVERSATION POC DASHBOARD            ",
        "==================================================================",
        f"Experiment ID: {m.get('experiment_id')} | Run ID: {m.get('run_id')}",
        f"Schema Version: {m.get('schema_version')} | Benchmark Validity: {state['benchmark_validity']}",
        f"Winning Model: {m.get('model_revisions', {}).get('winning_model')}",
        "------------------------------------------------------------------",
        "GATES PROGRESSION:",
    ]
    for g in state['gates']:
        lines.append(f"  [{g.get('status').upper()}] Gate {g.get('gate')} @ {g.get('timestamp')}")

    lines.extend([
        "------------------------------------------------------------------",
        "DATASET QUALITY COUNTS (ABCD v1.1):",
        f"  Total Read: {dq['counts']['read']}",
        f"  Eligible: {dq['counts']['eligible']} | Quarantine: {dq['counts']['quarantine']} | Excluded: {dq['counts']['excluded']}",
        "------------------------------------------------------------------",
        "KEY EVALUATION METRICS (Test Set):",
        f"  Closed-Set 10-Flow Macro-F1: {metrics.get('closed_macro_f1', 0.0):.4f}",
        f"  Open-Set Unknown Detection F1: {metrics.get('unknown_f1', 0.0):.4f}",
        f"  Routing Recall on H_final: {metrics.get('routing_recall', 0.0):.2%}",
        f"  Flow-Family Recovery Proxy: {metrics.get('recovered_flows_proxy')}/2",
        "------------------------------------------------------------------",
        f"DISCOVERY & REVIEW SUMMARY (Seed 42):",
        f"  Total Candidates: {len(state['candidates'])}",
        f"  Blinded Reviews Recorded: {len(state['reviews'])}",
        "=================================================================="
    ])
    return "\n".join(lines)
