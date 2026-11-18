"""Data loader module for BERTopic PoC Streamlit Dashboard.

Strict Zero-Fit on Render: Reads pre-computed Schema 1.0.0 artifacts only.
Never invokes model training, embedding, or fitting.
"""
from __future__ import annotations

import csv
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

from bertopic_poc.io import ROOT
from bertopic_poc.evidence import opaque_id

DEFAULT_ARTIFACTS_ROOT = ROOT / "artifacts/phase1"


def get_default_artifacts_root() -> Path:
    """Return the default artifacts directory path."""
    env_path = os.getenv("BERTOPIC_ARTIFACTS_ROOT")
    if env_path:
        return Path(env_path)
    return DEFAULT_ARTIFACTS_ROOT


@st.cache_data(show_spinner=False)
def load_json_file(path_str: str) -> Dict[str, Any]:
    """Read a JSON file safely with caching."""
    path = Path(path_str)
    if not path.is_file():
        raise FileNotFoundError(f"Artifact not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(show_spinner=False)
def load_manifest_bundle(root_dir_str: str) -> Dict[str, Any]:
    """Load run_manifest.json, gate snapshots, and data_quality.json."""
    root = Path(root_dir_str)
    manifest_path = root / "run_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"run_manifest.json missing at {manifest_path}")

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # Gate snapshots
    gates = {}
    g0_path = root / "bootstrap/g0_snapshot.json"
    if not g0_path.is_file():
        g0_path = root / "g0_snapshot.json"
    if g0_path.is_file():
        with open(g0_path, "r", encoding="utf-8") as f:
            gates["G0"] = json.load(f)

    for g_num in ["G1", "G2", "G3"]:
        g_path = root / f"g{g_num[1]}.json" if (root / f"g{g_num[1]}.json").is_file() else root / f"g{g_num[1].lower()}_snapshot.json"
        if g_path.is_file():
            with open(g_path, "r", encoding="utf-8") as f:
                gates[g_num] = json.load(f)

    # Data quality
    dq_path = root / "consolidated/data_quality.json"
    if not dq_path.is_file():
        dq_path = root / "preparation_v1/data_quality.json"
    dq = {}
    if dq_path.is_file():
        with open(dq_path, "r", encoding="utf-8") as f:
            dq = json.load(f)

    return {
        "manifest": manifest,
        "gates": gates,
        "gate_events": manifest.get("gate_events", []),
        "data_quality": dq,
        "experiment_id": manifest.get("experiment_id", "phase1"),
        "run_id": manifest.get("run_id", "consolidated_v1"),
        "winning_model": manifest.get("model_revisions", {}).get("winning_model", "sentence-transformers/all-MiniLM-L6-v2"),
        "benchmark_validity": manifest.get("benchmark_validity", "valid_with_declared_test_exposure"),
        "artifact_hashes": manifest.get("artifact_hashes", {})
    }


@st.cache_data(show_spinner=False)
def load_topic_statistics(root_dir_str: str) -> pd.DataFrame:
    """Load topic_statistics.csv into a pandas DataFrame."""
    root = Path(root_dir_str)
    csv_path = root / "consolidated/topic_statistics.csv"
    if not csv_path.is_file():
        raise FileNotFoundError(f"topic_statistics.csv missing at {csv_path}")

    df = pd.read_csv(csv_path, dtype={"topic_id": str, "scope_id": str})
    # Numeric conversions with fallback
    num_cols = [
        "customer_message_count",
        "source_messages_with_assignment",
        "segment_count",
        "mention_count",
        "conversation_count",
        "eligible_conversations",
        "conversation_share",
        "evidence_coverage",
    ]
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


@st.cache_data(show_spinner=False)
def load_candidates(root_dir_str: str) -> List[Dict[str, Any]]:
    """Load candidates.jsonl into a list of candidate dictionaries."""
    root = Path(root_dir_str)
    jsonl_path = root / "consolidated/candidates.jsonl"
    if not jsonl_path.is_file():
        raise FileNotFoundError(f"candidates.jsonl missing at {jsonl_path}")

    candidates = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if line_str:
                candidates.append(json.loads(line_str))
    return candidates


@st.cache_data(show_spinner=False)
def load_reviews_map(root_dir_str: str) -> Dict[str, Dict[str, Any]]:
    """Load reviews.jsonl indexed by cluster_key."""
    root = Path(root_dir_str)
    jsonl_path = root / "consolidated/reviews.jsonl"
    if not jsonl_path.is_file():
        raise FileNotFoundError(f"reviews.jsonl missing at {jsonl_path}")

    reviews_map = {}
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if line_str:
                item = json.loads(line_str)
                k = item.get("cluster_key")
                if k:
                    reviews_map[k] = item
    return reviews_map


@st.cache_data(show_spinner=False)
def load_evaluation_metrics(root_dir_str: str) -> Dict[str, Any]:
    """Load metrics.json from evaluation directory."""
    root = Path(root_dir_str)
    path = root / "evaluation/metrics.json"
    if not path.is_file():
        raise FileNotFoundError(f"metrics.json missing at {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(show_spinner=False)
def load_report_markdown(root_dir_str: str) -> str:
    """Load report.md text from evaluation directory."""
    root = Path(root_dir_str)
    path = root / "evaluation/report.md"
    if not path.is_file():
        raise FileNotFoundError(f"report.md missing at {path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


@st.cache_data(show_spinner=False)
def load_conversation_index(root_dir_str: str) -> pd.DataFrame:
    """Build lightweight conversation index from conversation_topics.csv and assignments.jsonl."""
    root = Path(root_dir_str)
    conv_csv = root / "consolidated/conversation_topics.csv"
    if not conv_csv.is_file():
        raise FileNotFoundError(f"conversation_topics.csv missing at {conv_csv}")

    df_conv = pd.read_csv(
        conv_csv,
        dtype={
            "conversation_id": str,
            "topic_id": str,
            "source": str,
            "primary_topic": str,
        },
    )

    # Read assignments.jsonl to summarize evidence status and source_split per conversation
    assign_path = root / "consolidated/assignments.jsonl"
    assign_summary: Dict[str, Dict[str, Any]] = {}
    if assign_path.is_file():
        with open(assign_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                a = json.loads(line)
                cid = a.get("conversation_id")
                if not cid:
                    continue
                if cid not in assign_summary:
                    assign_summary[cid] = {
                        "evidence_statuses": set(),
                        "topic_ids": set(),
                        "cluster_keys": set(),
                        "has_human_verified": False,
                        "has_model_supported": False,
                    }
                ev_status = a.get("evidence_status", "unknown")
                assign_summary[cid]["evidence_statuses"].add(ev_status)
                if ev_status == "human_verified":
                    assign_summary[cid]["has_human_verified"] = True
                elif ev_status == "model_supported":
                    assign_summary[cid]["has_model_supported"] = True
                if a.get("topic_id"):
                    assign_summary[cid]["topic_ids"].add(a.get("topic_id"))
                if a.get("cluster_key"):
                    assign_summary[cid]["cluster_keys"].add(a.get("cluster_key"))

    # Map summary into DataFrame
    def compute_evidence_category(row_cid: str) -> str:
        entry = assign_summary.get(row_cid)
        if not entry:
            return "model_supported"
        if entry["has_human_verified"]:
            return "human_verified"
        if entry["has_model_supported"]:
            return "model_supported"
        return "cluster_only"

    df_conv["evidence_status"] = df_conv["conversation_id"].apply(compute_evidence_category)
    if "primary_topic" in df_conv.columns:
        df_conv["is_primary"] = df_conv["primary_topic"].astype(str).str.lower().isin(["true", "1"])
    else:
        df_conv["is_primary"] = True

    return df_conv


@st.cache_data(show_spinner=True)
def load_segments_index(segments_file_str: str) -> Dict[str, List[int]]:
    """Build byte-offset index for segments.jsonl mapping conversation_id -> list[byte_offset]."""
    path = Path(segments_file_str)
    if not path.is_file():
        raise FileNotFoundError(f"segments.jsonl missing at {path}")

    index: Dict[str, List[int]] = {}
    with open(path, "rb") as f:
        while True:
            offset = f.tell()
            line = f.readline()
            if not line:
                break
            idx = line.find(b'"conversation_id": "')
            if idx != -1:
                end_quote = line.find(b'"', idx + 20)
                if end_quote != -1:
                    cid = line[idx + 20 : end_quote].decode("ascii", errors="replace")
                    if cid not in index:
                        index[cid] = []
                    index[cid].append(offset)
    return index


def get_conversation_segments_and_assignments(
    conversation_id: str,
    root_dir_str: str,
    segments_index: Optional[Dict[str, List[int]]] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Retrieve segments and assignments for a given conversation_id efficiently."""
    root = Path(root_dir_str)
    segments_path = root / "preparation_v1/segments.jsonl"
    if not segments_path.is_file():
        segments_path = root / "smoke_test/segments.jsonl"

    segments: List[Dict[str, Any]] = []
    target_cids = {conversation_id, opaque_id(conversation_id)}

    offsets = []
    if segments_index is not None:
        for t_cid in target_cids:
            offsets.extend(segments_index.get(t_cid, []))

    if offsets:
        with open(segments_path, "rb") as f:
            for offset in offsets:
                f.seek(offset)
                line = f.readline()
                if line.strip():
                    try:
                        segments.append(json.loads(line.decode("utf-8")))
                    except Exception:
                        pass
    else:
        # Fallback linear scan if index not available
        if segments_path.is_file():
            with open(segments_path, "r", encoding="utf-8") as f:
                for line in f:
                    if any(f'"conversation_id": "{t_cid}"' in line for t_cid in target_cids):
                        try:
                            item = json.loads(line)
                            if item.get("conversation_id") in target_cids:
                                segments.append(item)
                        except Exception:
                            pass

    # Sort segments by customer_turn_index
    segments.sort(key=lambda x: x.get("customer_turn_index", 0))

    # Load assignments for this conversation
    assignments: List[Dict[str, Any]] = []
    assign_path = root / "consolidated/assignments.jsonl"
    if assign_path.is_file():
        with open(assign_path, "r", encoding="utf-8") as f:
            for line in f:
                if any(f'"conversation_id": "{t_cid}"' in line for t_cid in target_cids):
                    try:
                        item = json.loads(line)
                        if item.get("conversation_id") in target_cids:
                            assignments.append(item)
                    except Exception:
                        pass

    return segments, assignments
