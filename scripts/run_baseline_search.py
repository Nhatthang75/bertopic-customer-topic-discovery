"""Chạy tìm kiếm Baseline TF-IDF + Logistic Regression trên Train K / Dev K + H_dev."""
import gzip
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bertopic_poc.io import ROOT, read_json, write_json
from bertopic_poc.baseline import search_baseline_grid
from bertopic_poc.taxonomy import KNOWN_K_FLOWS, HIDDEN_DEV_FLOWS, flow_id
from bertopic_poc.text import Masker, normalize


def main():
    print("Loading data for baseline search...")
    onto = read_json(ROOT / 'data/raw/ontology.json')
    names = onto.get('values', {}).get('enumerable', {}).get('customer_name', [])
    masker = Masker(names=names)

    train_texts = []
    train_labels = []
    dev_texts = []
    dev_labels = []

    # Read raw ABCD directly for custodian training/dev split
    with gzip.open(ROOT / 'data/raw/abcd_v1.1.json.gz', 'rt', encoding='utf-8') as f:
        data = json.load(f)

    # 1. Train K: only known flows
    for row in data['train']:
        flow = row.get('scenario', {}).get('flow')
        if flow in KNOWN_K_FLOWS:
            # Concatenate customer turns
            cust_turns = [masker(text) for role, text in row.get('original', []) if role == 'customer']
            if cust_turns:
                train_texts.append(" ".join(cust_turns))
                train_labels.append(flow_id(flow))

    # 2. Dev K + H_dev: known flows + shipping_issue
    dev_allowed = set(KNOWN_K_FLOWS) | set(HIDDEN_DEV_FLOWS)
    for row in data['dev']:
        flow = row.get('scenario', {}).get('flow')
        if flow in dev_allowed:
            cust_turns = [masker(text) for role, text in row.get('original', []) if role == 'customer']
            if cust_turns:
                dev_texts.append(" ".join(cust_turns))
                dev_labels.append(flow_id(flow))

    print(f"Train K samples: {len(train_texts)} across {len(KNOWN_K_FLOWS)} flows.")
    print(f"Dev K + H_dev samples: {len(dev_texts)} (Known K + H_dev).")

    known_classes = [flow_id(f) for f in KNOWN_K_FLOWS]
    hidden_dev_class = flow_id(HIDDEN_DEV_FLOWS[0])

    start_t = time.time()
    print("Searching 15 (C, q) baseline combinations...")
    grid_result = search_baseline_grid(
        train_texts=train_texts,
        train_labels=train_labels,
        dev_texts=dev_texts,
        dev_labels=dev_labels,
        known_classes=known_classes,
        hidden_dev_class=hidden_dev_class,
        c_grid=(0.1, 1.0, 10.0),
        q_grid=(0.35, 0.50, 0.65, 0.80, 0.95)
    )
    duration = time.time() - start_t

    best = grid_result['best_configuration']
    print(f"Search complete in {duration:.2f}s.")
    print(f"Best configuration: C={best['C']}, q={best['q']}")
    print(f"Known Macro-F1: {best['macro_f1']:.4f}, Unknown F1: {best['unknown_f1']:.4f}")
    print(f"Dev constraint failed: {grid_result['dev_constraint_failed']}")

    out_path = ROOT / 'artifacts/phase1/baseline_search.json'
    write_json(out_path, {
        'schema_version': '1.0.0',
        'experiment_id': 'phase1',
        'run_id': 'baseline_v1',
        'duration_seconds': round(duration, 2),
        'best_configuration': best,
        'dev_constraint_failed': grid_result['dev_constraint_failed'],
        'all_evaluations': grid_result['all_evaluations']
    })
    print(f"Saved baseline search results to {out_path}")


if __name__ == '__main__':
    main()
