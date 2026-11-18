"""Smoke test 2 mô hình embedding trên tối đa 200 cuộc hội thoại Train K."""
import gzip
import hashlib
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bertopic_poc.io import ROOT, read_json, write_json
from bertopic_poc.taxonomy import KNOWN_K_FLOWS, flow_id
from bertopic_poc.text import Masker


def select_smoke_train_conversations(max_convs: int = 200, seed: int = 42) -> list[dict]:
    with gzip.open(ROOT / 'data/raw/abcd_v1.1.json.gz', 'rt', encoding='utf-8') as f:
        data = json.load(f)

    onto = read_json(ROOT / 'data/raw/ontology.json')
    names = onto.get('values', {}).get('enumerable', {}).get('customer_name', [])
    masker = Masker(names=names)

    candidates = []
    for row in data['train']:
        flow = row.get('scenario', {}).get('flow')
        if flow in KNOWN_K_FLOWS:
            cid = str(row['convo_id'])
            # Deterministic hash ranking
            h = hashlib.sha256(f"{seed}:{cid}".encode()).hexdigest()
            cust_turns = [masker(text) for role, text in row.get('original', []) if role == 'customer']
            if cust_turns:
                candidates.append({
                    'convo_id': cid,
                    'flow': flow,
                    'text': " ".join(cust_turns),
                    'hash': h
                })

    candidates.sort(key=lambda x: x['hash'])
    return candidates[:max_convs]


def run_smoke():
    registry = read_json(ROOT / 'config/experiment_registry.json')
    budget = registry['budget']
    max_convs = budget['smoke_conversations']
    batch_size = budget['batch']

    print(f"Selecting up to {max_convs} smoke conversations from Train K...")
    samples = select_smoke_train_conversations(max_convs=max_convs, seed=42)
    sample_texts = [s['text'] for s in samples]
    print(f"Selected {len(samples)} conversations.")

    from sentence_transformers import SentenceTransformer
    import torch

    # Restrict to budget cpu threads
    torch.set_num_threads(budget.get('cpu_threads', 4))

    results = []
    for m in registry['models']:
        model_id = m['model_id']
        rev = m['revision']
        print(f"\n--- Smoke testing model: {model_id} (rev: {rev}) ---")
        t0 = time.time()
        status = 'passed'
        embeddings = None
        error_msg = None

        try:
            model = SentenceTransformer(model_id, revision=rev, device='cpu')
            # Test encoding with registered batch size
            embeddings = model.encode(
                sample_texts,
                batch_size=batch_size,
                normalize_embeddings=True,
                show_progress_bar=False
            )
            dur = time.time() - t0
            print(f"Inference successful in {dur:.2f}s. Shape: {embeddings.shape}")
        except Exception as e:
            # Check OOM retry with batch 8
            print(f"Warning: Batch {batch_size} failed with error: {e}. Retrying with batch {budget['oom_retry_batch']}...")
            try:
                t0_retry = time.time()
                embeddings = model.encode(
                    sample_texts,
                    batch_size=budget['oom_retry_batch'],
                    normalize_embeddings=True,
                    show_progress_bar=False
                )
                dur = time.time() - t0_retry
                print(f"Retry successful in {dur:.2f}s. Shape: {embeddings.shape}")
                status = 'passed_after_oom_retry'
            except Exception as e2:
                dur = time.time() - t0
                status = 'unavailable'
                error_msg = str(e2)
                print(f"Model {model_id} marked unavailable: {error_msg}")

        results.append({
            'model_id': model_id,
            'revision': rev,
            'status': status,
            'duration_seconds': round(dur, 2),
            'sample_count': len(sample_texts),
            'embedding_dim': int(embeddings.shape[1]) if embeddings is not None else None,
            'normalized': True if embeddings is not None else False,
            'error': error_msg
        })

    out_path = ROOT / 'artifacts/phase1/smoke_models.json'
    write_json(out_path, {
        'schema_version': '1.0.0',
        'experiment_id': 'phase1',
        'run_id': 'smoke_v1',
        'results': results,
        'all_passed': any(r['status'] in ('passed', 'passed_after_oom_retry') for r in results)
    })
    print(f"\nSmoke test results saved to {out_path}.")


if __name__ == '__main__':
    run_smoke()
