"""Conversation Evidence Explorer Page for BERTopic PoC Dashboard."""
from __future__ import annotations

import streamlit as st
import pandas as pd
from pathlib import Path

from bertopic_poc.ui.data_loader import (
    get_default_artifacts_root,
    load_conversation_index,
    load_segments_index,
    get_conversation_segments_and_assignments,
)
from bertopic_poc.ui.utils import highlight_evidence_span, inject_custom_css

st.set_page_config(
    page_title="Conversation Explorer | BERTopic PoC",
    page_icon="💬",
    layout="wide",
)

def render_conversation_explorer():
    inject_custom_css()
    st.title("💬 Khám Phá Hội Thoại & Truy Vết Bằng Chứng (Conversation Explorer)")
    st.caption("Tra cứu câu thoại khách hàng đã che mờ PII, phân trang mượt mà và highlight bằng chứng offsets Schema 1.0.0")

    artifacts_root = str(get_default_artifacts_root())
    try:
        df_conv = load_conversation_index(artifacts_root)
    except Exception as e:
        st.error(f"Lỗi nạp chỉ mục hội thoại: {e}")
        return

    # Filter section
    st.markdown("### 🔍 Bộ Lọc & Tìm Kiếm Hội Thoại")
    f1, f2, f3, f4 = st.columns([2, 1, 1, 1])

    with f1:
        cid_query = st.text_input(
            "Tìm kiếm theo mã hội thoại (Conversation ID):",
            placeholder="VD: f4fd3222b6a01a7825d97613 hoặc nhập một phần ID...",
        ).strip()

    all_topics = ["Tất cả (All Topics)"] + sorted(list(df_conv["topic_id"].dropna().unique()))
    with f2:
        selected_topic = st.selectbox("Lọc theo chủ đề gán:", options=all_topics, index=0)

    all_sources = ["Tất cả (All Sources)"] + sorted(list(df_conv["source"].dropna().unique()))
    with f3:
        selected_source = st.selectbox("Nguồn phân loại:", options=all_sources, index=0)

    all_ev_statuses = ["Tất cả (All Statuses)", "human_verified", "model_supported", "cluster_only"]
    with f4:
        selected_ev_status = st.selectbox("Trạng thái bằng chứng:", options=all_ev_statuses, index=0)

    # Apply filters
    filtered_df = df_conv
    if cid_query:
        filtered_df = filtered_df[filtered_df["conversation_id"].str.contains(cid_query, case=False, na=False)]

    if selected_topic != "Tất cả (All Topics)":
        filtered_df = filtered_df[filtered_df["topic_id"] == selected_topic]

    if selected_source != "Tất cả (All Sources)":
        filtered_df = filtered_df[filtered_df["source"] == selected_source]

    if selected_ev_status != "Tất cả (All Statuses)":
        filtered_df = filtered_df[filtered_df["evidence_status"] == selected_ev_status]

    # Metrics
    st.markdown("---")
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Kết Quả Tìm Kiếm", f"{len(filtered_df):,} dòng")
    with m2:
        unique_convs = filtered_df["conversation_id"].nunique()
        st.metric("Số Hội Thoại Khớp", f"{unique_convs:,} cuộc")
    with m3:
        hum_count = sum(filtered_df["evidence_status"] == "human_verified")
        st.metric("Human Verified", f"{hum_count:,}")
    with m4:
        mod_count = sum(filtered_df["evidence_status"] == "model_supported")
        st.metric("Model Supported", f"{mod_count:,}")

    # Empty state handling
    if filtered_df.empty:
        st.info("💡 Không tìm thấy cuộc hội thoại nào khớp với điều kiện tìm kiếm. Vui lòng kiểm tra lại mã ID hoặc bộ lọc.")
        return

    st.markdown("---")

    # Pagination controls
    st.markdown("### 📑 Danh Sách Hội Thoại")
    p_col1, p_col2 = st.columns([1, 2])
    with p_col1:
        page_size = st.selectbox("Số dòng mỗi trang:", options=[10, 25, 50], index=0)
    
    total_pages = max(1, (len(filtered_df) + page_size - 1) // page_size)
    with p_col2:
        page_num = st.number_input("Trang hiện tại:", min_value=1, max_value=total_pages, value=1, step=1)

    start_idx = (page_num - 1) * page_size
    end_idx = min(start_idx + page_size, len(filtered_df))
    page_data = filtered_df.iloc[start_idx:end_idx]

    display_page_df = pd.DataFrame({
        "Conversation ID": page_data["conversation_id"],
        "Chủ Đề (Topic ID)": page_data["topic_id"],
        "Nguồn Gán": page_data["source"],
        "Điểm Tối Đa (Max Score)": page_data["max_score"].apply(lambda x: f"{float(x):.4f}" if pd.notnull(x) else "\\N"),
        "Số Bằng Chứng": page_data["evidence_count"],
        "Trạng Thái Bằng Chứng": page_data["evidence_status"],
    })

    st.dataframe(display_page_df, hide_index=True, use_container_width=True)
    st.caption(f"Hiển thị dòng {start_idx + 1} - {end_idx} trên tổng số {len(filtered_df):,} dòng (Trang {page_num} / {total_pages}).")

    st.markdown("---")

    # Conversation Detail Inspector
    st.markdown("### 🔎 Xem Chi Tiết Hội Thoại & Highlight Vùng Bằng Chứng (Offsets)")
    candidate_cids = list(page_data["conversation_id"].unique())
    selected_cid = st.selectbox("Chọn Conversation ID từ trang hiện tại để kiểm tra câu thoại:", options=candidate_cids, index=0)

    if selected_cid:
        # Load segments index lazily
        segments_path = Path(artifacts_root) / "preparation_v1/segments.jsonl"
        if not segments_path.is_file():
            segments_path = Path(artifacts_root) / "smoke_test/segments.jsonl"

        with st.spinner("Đang tải dữ liệu phân đoạn..."):
            seg_idx = load_segments_index(str(segments_path))
            segments, assignments = get_conversation_segments_and_assignments(
                selected_cid, artifacts_root, seg_idx
            )

        st.markdown(f"#### 💬 Cuộc Hội Thoại: `{selected_cid}`")
        top_c1, top_c2 = st.columns(2)
        with top_c1:
            st.info(f"Tổng số phân đoạn tìm thấy: **{len(segments)} segments**")
        with top_c2:
            st.info(f"Tổng số bản ghi gán nhãn (assignments): **{len(assignments)} assignments**")

        # Map assignment spans for this conversation
        # Key: segment_id or customer_turn_index
        assignment_spans = {}
        for a in assignments:
            seg_ids = a.get("segment_ids", [])
            for s_id in seg_ids:
                assignment_spans[s_id] = {
                    "spans": a.get("evidence_spans", []),
                    "evidence_status": a.get("evidence_status", "model_supported"),
                    "topic_id": a.get("topic_id", "N/A"),
                    "score": a.get("score"),
                }

        # Render conversation turns
        st.markdown("##### Dòng Thời Gian Hội Thoại (Transcript with Offset Highlights):")
        if not segments:
            st.warning("Không có phân đoạn nào được ghi nhận cho cuộc hội thoại này.")
        else:
            for seg in segments:
                s_id = seg.get("segment_id")
                turn_idx = seg.get("customer_turn_index", 0)
                masked_text = seg.get("masked_customer_text", "")
                context_text = seg.get("context_text", "")
                span_start = seg.get("span_start")
                span_end = seg.get("span_end")
                c_status = seg.get("content_status", "analyzable")

                # Determine evidence status
                assign_info = assignment_spans.get(s_id)
                ev_status = assign_info.get("evidence_status", "model_supported") if assign_info else "cluster_only"

                with st.chat_message("user"):
                    st.caption(f"**Khách hàng (Lượt {turn_idx})** • Phân đoạn: `{s_id}` • Trạng thái: `{c_status}`")
                    
                    # Highlight evidence text strictly by [span_start:span_end]
                    highlighted_html = highlight_evidence_span(
                        masked_text, span_start, span_end, evidence_status=ev_status
                    )
                    st.markdown(highlighted_html, unsafe_allow_html=True)
                    
                    # Details expander
                    with st.expander("Tọa độ offsets & Ngữ cảnh Agent tiền nhiệm"):
                        st.write(f"- **Tọa độ bằng chứng**: `[span_start: {span_start}, span_end: {span_end}]`")
                        if span_start is not None and span_end is not None and 0 <= span_start < span_end <= len(masked_text):
                            st.write(f"- **Văn bản trích xuất**: *\"{masked_text[span_start:span_end]}\"*")
                        if context_text:
                            st.write(f"- **Lời thoại Agent trước đó**: *\"{context_text}\"*")
                        if assign_info:
                            st.write(f"- **Topic gán**: `{assign_info.get('topic_id')}` | **Score**: `{assign_info.get('score')}`")


if __name__ == "__main__":
    render_conversation_explorer()
