"""Live Inference and Data Processing Engine for BERTopic Customer Intelligence Portal.

Enables real-time customer conversation classification, novel topic routing,
evidence span localization, and batch CSV processing for management demos.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st

from bertopic_poc.taxonomy import (
    FLOW_DESCRIPTIONS_EN,
    KNOWN_K_FLOWS,
    HIDDEN_FINAL_FLOWS,
    FLOW_SUBFLOW_CANONICAL,
)
from bertopic_poc.ui.data_loader import get_default_artifacts_root, load_candidates


SAMPLE_DEMO_QUERIES = [
    {
        "label": "🧥 Lỗi sản phẩm (Known Flow: product_defect)",
        "text": "I received my jacket yesterday but the zipper is completely broken and there is a dirty stain on the sleeve. I want to return it for a refund.",
        "expected_intent": "Khách muốn hoàn tiền do áo bị hỏng khóa và dính vết bẩn.",
    },
    {
        "label": "📦 Hủy đơn hàng (Known Flow: order_issue)",
        "text": "Hello, please cancel my pending order #58219 right now because the delivery time is too slow and I do not want it anymore.",
        "expected_intent": "Khách yêu cầu hủy đơn do thời gian giao hàng quá lâu.",
    },
    {
        "label": "💳 Khiếu nại hóa đơn định kỳ (Novel Flow: subscription_inquiry)",
        "text": "Why was my account charged 49 dollars for the monthly subscription today? I want to dispute this recurring billing charge immediately.",
        "expected_intent": "Phát hiện nhu cầu mới: Khách khiếu nại cước phí định kỳ hàng tháng.",
    },
    {
        "label": "🌐 Lỗi kỹ thuật website (Novel Flow: troubleshoot_site)",
        "text": "The checkout page gives an error 500 when I enter my credit card, and my shopping cart disappeared completely.",
        "expected_intent": "Phát hiện nhu cầu mới: Lỗi hệ thống thanh toán và mất giỏ hàng trên web.",
    },
    {
        "label": "👋 Chào hỏi xã giao (Non-Need: Không nêu nhu cầu)",
        "text": "Hello, good morning! Thanks for your help today. Bye!",
        "expected_intent": "Câu thoại xã giao thông thường, hệ thống tự động lọc bỏ.",
    },
]


@st.cache_resource(show_spinner=False)
def get_sentence_transformer_model():
    """Load and cache SentenceTransformer model singleton."""
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


@st.cache_data(show_spinner=False)
def get_prototype_flow_embeddings() -> Tuple[List[str], np.ndarray]:
    """Compute and cache normalized embeddings for the 10 flows."""
    model = get_sentence_transformer_model()
    flows = list(FLOW_DESCRIPTIONS_EN.keys())
    descs = [FLOW_DESCRIPTIONS_EN[f] for f in flows]
    embs = model.encode(descs, normalize_embeddings=True)
    return flows, np.array(embs)


def is_non_need_greeting(text: str) -> bool:
    """Detect simple non-need social pleasantries."""
    t = text.strip().lower()
    greetings = {"hi", "hello", "hey", "thanks", "thank you", "ok", "okay", "yes", "no", "bye", "goodbye"}
    # Strip punctuation
    t_clean = re.sub(r"[^\w\s]", "", t).strip()
    words = t_clean.split()
    if len(words) <= 3 and all(w in greetings for w in words):
        return True
    return False


def extract_evidence_span(text: str, flow_emb: np.ndarray, model: Any) -> Tuple[int, int, str]:
    """Find the specific sentence or clause with the highest similarity to the predicted flow."""
    sentences = re.split(r"(?<=[.?!;])\s+", text)
    if len(sentences) <= 1:
        return 0, len(text), text

    sent_embs = model.encode(sentences, normalize_embeddings=True)
    sims = np.dot(sent_embs, flow_emb.T).flatten()
    best_idx = int(np.argmax(sims))
    best_sent = sentences[best_idx]

    start = text.find(best_sent)
    if start == -1:
        start = 0
    end = start + len(best_sent)
    return start, end, best_sent


def analyze_single_text(text: str, artifacts_root: Optional[str] = None) -> Dict[str, Any]:
    """Analyze a single customer conversation text in real-time."""
    cleaned = text.strip()
    if not cleaned:
        return {"status": "empty", "message": "Văn bản rỗng."}

    # 1. Check non-need
    if is_non_need_greeting(cleaned):
        return {
            "status": "non_need",
            "predicted_flow": "non_need",
            "display_name": "Câu Xã Giao (Non-Need)",
            "confidence": 0.99,
            "category": "Không Nêu Nhu Cầu",
            "badge_color": "#64748b",
            "decision": "Lọc tự động (Bỏ qua)",
            "evidence_span": (0, len(cleaned), cleaned),
            "explanation": "Câu thoại chỉ mang tính chất chào hỏi, cảm ơn hoặc xác nhận ngắn, không chứa yêu cầu nghiệp vụ.",
            "top_matches": [],
            "nearest_cluster": None,
        }

    # 2. Embed input text
    model = get_sentence_transformer_model()
    flows, flow_embs = get_prototype_flow_embeddings()

    input_emb = model.encode([cleaned], normalize_embeddings=True)
    sims = np.dot(flow_embs, input_emb.T).flatten()

    # Sort descending
    sorted_indices = np.argsort(-sims)
    top1_idx = sorted_indices[0]
    top2_idx = sorted_indices[1]

    top1_flow = flows[top1_idx]
    top1_score = float(sims[top1_idx])
    top2_score = float(sims[top2_idx])
    delta = top1_score - top2_score

    # Thresholds from Gate G1
    tau = 0.20
    delta_threshold = 0.03

    # Evidence span
    span_start, span_end, span_text = extract_evidence_span(cleaned, flow_embs[top1_idx], model)

    # Determine status & category
    is_known = top1_flow in KNOWN_K_FLOWS
    is_hidden_family = top1_flow in HIDDEN_FINAL_FLOWS

    # Find nearest candidate cluster from discovery
    nearest_cluster = None
    if artifacts_root is None:
        artifacts_root = str(get_default_artifacts_root())

    try:
        candidates = load_candidates(artifacts_root)
        q_words = set(re.findall(r"\w+", cleaned.lower()))
        best_cand = None
        max_overlap = 0
        for c in candidates:
            kws = set(c.get("top_keywords", [])[:8])
            overlap = len(q_words & kws)
            if overlap > max_overlap:
                max_overlap = overlap
                best_cand = c
        if best_cand and max_overlap >= 1:
            nearest_cluster = {
                "cluster_id": best_cand.get("cluster_id"),
                "top_keywords": ", ".join(best_cand.get("top_keywords", [])[:8]),
                "status": best_cand.get("status"),
                "overlap_keywords": list(q_words & set(best_cand.get("top_keywords", []))),
            }
    except Exception:
        pass

    if top1_score >= tau and delta >= delta_threshold:
        if is_hidden_family:
            category = "Nhu Cầu Mới (Novel / Hidden Flow)"
            badge_color = "#f59e0b"
            decision = f"Định tuyến Discovery Pool -> Họ chủ đề: {top1_flow}"
            explanation = f"Phát hiện nhu cầu phát sinh ngoài 7 luồng chuẩn. Khớp với họ chủ đề ẩn [{top1_flow}]."
        else:
            category = "Chủ Đề Đã Biết (Known Flow)"
            badge_color = "#10b981"
            decision = f"Tự động gán: {top1_flow}"
            explanation = f"Khớp chính xác với chủ đề cố định đã được huấn luyện [{top1_flow}]."
    else:
        category = "Cụm Mới Cần Thẩm Định (Discovery Pool)"
        badge_color = "#3b82f6"
        decision = "Chuyển Hội Đồng Nghiệp Vụ Thẩm Định"
        explanation = "Độ tin cậy nằm dưới ngưỡng tự động phân loại; chuyển vào Pool khám phá chủ đề mới."

    top_matches = [
        {
            "flow": flows[idx],
            "score": float(sims[idx]),
            "pct": f"{float(sims[idx])*100:.1f}%",
            "type": "Known" if flows[idx] in KNOWN_K_FLOWS else "Novel Discovery",
        }
        for idx in sorted_indices[:4]
    ]

    return {
        "status": "success",
        "predicted_flow": top1_flow,
        "display_name": top1_flow.replace("_", " ").title(),
        "confidence": top1_score,
        "confidence_pct": f"{top1_score*100:.1f}%",
        "category": category,
        "badge_color": badge_color,
        "decision": decision,
        "evidence_span": (span_start, span_end, span_text),
        "explanation": explanation,
        "top_matches": top_matches,
        "nearest_cluster": nearest_cluster,
    }


def analyze_batch_dataframe(df: pd.DataFrame, text_column: str) -> pd.DataFrame:
    """Analyze a batch DataFrame of customer messages."""
    model = get_sentence_transformer_model()
    flows, flow_embs = get_prototype_flow_embeddings()

    texts = df[text_column].astype(str).tolist()
    embs = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)

    # Matrix multiplication: (N, 384) x (384, 10) -> (N, 10)
    sim_matrix = np.dot(embs, flow_embs.T)

    results = []
    for i, t in enumerate(texts):
        if is_non_need_greeting(t):
            results.append({
                "Nội Dung Hội Thoại": t,
                "Chủ Đề Dự Đoán": "non_need",
                "Phân Loại": "Xã Giao",
                "Độ Tin Cậy": "99.0%",
                "Hành Động Đề Xuất": "Bỏ qua",
            })
            continue

        row_sims = sim_matrix[i]
        top1_idx = int(np.argmax(row_sims))
        score = float(row_sims[top1_idx])
        flow = flows[top1_idx]

        if flow in KNOWN_K_FLOWS and score >= 0.20:
            cat = "Chủ Đề Đã Biết"
            action = f"Tự động gán: {flow}"
        elif flow in HIDDEN_FINAL_FLOWS:
            cat = "Nhu Cầu Mới"
            action = f"Định tuyến Discovery: {flow}"
        else:
            cat = "Cụm Khám Phá"
            action = "Chờ thẩm định"

        results.append({
            "Nội Dung Hội Thoại": t,
            "Chủ Đề Dự Đoán": flow,
            "Phân Loại": cat,
            "Độ Tin Cậy": f"{score*100:.1f}%",
            "Hành Động Đề Xuất": action,
        })

    return pd.DataFrame(results)
