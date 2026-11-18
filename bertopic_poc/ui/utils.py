"""UI utilities for BERTopic Web Dashboard, including safe HTML highlight rendering."""
from __future__ import annotations

import html
from typing import Optional


def highlight_evidence_span(
    text: str,
    span_start: Optional[int],
    span_end: Optional[int],
    evidence_status: str = "model_supported",
) -> str:
    """Highlight evidence span within masked_customer_text using strict [span_start:span_end] offsets.

    Uses HTML escaping to prevent XSS while rendering visual marks.
    No offset drift: exactly slices [span_start:span_end].
    """
    if not text:
        return ""

    if (
        span_start is None
        or span_end is None
        or span_start < 0
        or span_end <= span_start
        or span_start >= len(text)
    ):
        return html.escape(text)

    # Clamp span_end to length of text
    actual_end = min(span_end, len(text))

    before = html.escape(text[:span_start])
    target = html.escape(text[span_start:actual_end])
    after = html.escape(text[actual_end:])

    # Style by evidence status with dark-mode friendly high-contrast neon tints
    if evidence_status == "human_verified":
        bg_color = "rgba(16, 185, 129, 0.25)"
        border_color = "#10b981"
        text_color = "#34d399"
        badge_label = "Human Verified"
    elif evidence_status == "model_supported":
        bg_color = "rgba(245, 158, 11, 0.25)"
        border_color = "#f59e0b"
        text_color = "#fbbf24"
        badge_label = "Model Supported"
    elif evidence_status == "cluster_only":
        bg_color = "rgba(148, 163, 184, 0.2)"
        border_color = "#64748b"
        text_color = "#cbd5e1"
        badge_label = "Cluster Only"
    else:
        bg_color = "rgba(56, 189, 248, 0.25)"
        border_color = "#38bdf8"
        text_color = "#7dd3fc"
        badge_label = evidence_status

    badge = f"<span style='font-size: 0.75em; padding: 2px 6px; background: {border_color}; color: #0f172a; border-radius: 4px; margin-left: 6px; font-weight: 700;'>{badge_label}</span>"
    highlighted = (
        f"<mark style='background-color: {bg_color}; border: 1px solid {border_color}; "
        f"color: {text_color}; font-weight: 600; border-radius: 4px; padding: 2px 5px;'>"
        f"{target}</mark>{badge}"
    )

    return f"{before}{highlighted}{after}"


def inject_custom_css():
    """Inject modern Dark Mode SaaS Web App styling for Streamlit."""
    import streamlit as st

    css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }

    /* Hero Banner Dark Mode */
    .hero-banner {
        background: linear-gradient(135deg, #020617 0%, #0f172a 45%, #1e1b4b 100%);
        color: #f8fafc;
        border: 1px solid #334155;
        padding: 1.5rem 2rem;
        border-radius: 14px;
        margin-bottom: 1.25rem;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.6);
    }
    .hero-title {
        font-size: 1.75rem;
        font-weight: 700;
        color: #f8fafc !important;
        margin: 0 0 0.4rem 0;
        letter-spacing: -0.02em;
    }
    .hero-desc {
        color: #94a3b8;
        font-size: 0.95rem;
        margin: 0;
    }

    /* Modern Dark KPI Cards */
    .metric-card {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 1rem 1.25rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.4);
        transition: all 0.2s ease-in-out;
        height: 100%;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 20px -2px rgba(0, 0, 0, 0.6);
        border-color: #38bdf8;
    }
    .kpi-title {
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: #94a3b8;
        margin-bottom: 0.25rem;
    }
    .kpi-value {
        font-size: 1.65rem;
        font-weight: 700;
        color: #f8fafc;
        line-height: 1.2;
    }
    .kpi-sub {
        font-size: 0.775rem;
        color: #34d399;
        font-weight: 500;
        margin-top: 0.25rem;
    }

    /* Badges Pill */
    .badge-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.35rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .badge-blue { background: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.4); }
    .badge-green { background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4); }
    .badge-amber { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4); }
    .badge-purple { background: rgba(168, 85, 247, 0.15); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.4); }

    /* Modern Dark Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 1px solid #334155;
        padding-bottom: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 42px;
        white-space: pre-wrap;
        background-color: #1e293b;
        color: #94a3b8;
        border-radius: 8px 8px 0px 0px;
        border: 1px solid #334155;
        border-bottom: none;
        gap: 4px;
        padding: 8px 16px;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background-color: #0f172a !important;
        color: #38bdf8 !important;
        font-weight: 600 !important;
        border-top: 2px solid #38bdf8 !important;
        border-bottom: 2px solid #0f172a !important;
    }

    /* Conversation Turn Box */
    .turn-box {
        background: #1e293b;
        border: 1px solid #334155;
        border-left: 4px solid #38bdf8;
        padding: 12px 16px;
        border-radius: 8px;
        margin-bottom: 10px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
