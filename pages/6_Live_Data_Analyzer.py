"""Live Data Processing and Text Analyzer Page for BERTopic PoC Dashboard."""
from __future__ import annotations

import io
import time
import pandas as pd
import plotly.express as px
import streamlit as st

from bertopic_poc.ui.live_engine import (
    SAMPLE_DEMO_QUERIES,
    analyze_single_text,
    analyze_batch_dataframe,
)
from bertopic_poc.ui.utils import highlight_evidence_span, inject_custom_css
from bertopic_poc.ui.data_loader import get_default_artifacts_root

st.set_page_config(
    page_title="Live Data Analyzer | BERTopic PoC",
    page_icon="🚀",
    layout="wide",
)


def render_live_analyzer():
    inject_custom_css()

    st.title("🚀 Chạy Dữ Liệu & Phân Tích Trực Tiếp (Live Customer Intelligence)")
    st.caption("Công cụ phân loại thời gian thực và xử lý tệp hội thoại hàng loạt dành cho quản lý CSKH")

    artifacts_root = str(get_default_artifacts_root())

    tab_live, tab_batch = st.tabs([
        "💬 Thử Nghiệm Tức Thì (Live Text Analyzer)",
        "📁 Xử Lý Tệp Hàng Loạt (Batch CSV Processing)",
    ])

    # -------------------------------------------------------------
    # TAB 1: LIVE TEXT ANALYZER
    # -------------------------------------------------------------
    with tab_live:
        st.markdown("#### 🎯 Nhập Hội Thoại Khách Hàng Để Phân Tích Tức Thì")
        st.write("Bấm chọn một tình huống mẫu thực tế bên dưới hoặc tự nhập câu thoại để kiểm tra khả năng bóc tách:")

        # Quick sample buttons
        col_s1, col_s2, col_s3 = st.columns(3)
        col_s4, col_s5, _ = st.columns(3)

        selected_sample_text = None

        if col_s1.button("🧥 Lỗi Sản Phẩm (Defect)", use_container_width=True):
            selected_sample_text = SAMPLE_DEMO_QUERIES[0]["text"]
        if col_s2.button("📦 Hủy Đơn Hàng (Order Issue)", use_container_width=True):
            selected_sample_text = SAMPLE_DEMO_QUERIES[1]["text"]
        if col_s3.button("💳 Khiếu Nại Cước Phí (Subscription)", use_container_width=True):
            selected_sample_text = SAMPLE_DEMO_QUERIES[2]["text"]
        if col_s4.button("🌐 Lỗi Web (Troubleshoot Site)", use_container_width=True):
            selected_sample_text = SAMPLE_DEMO_QUERIES[3]["text"]
        if col_s5.button("👋 Chào Hỏi Xã Giao (Non-Need)", use_container_width=True):
            selected_sample_text = SAMPLE_DEMO_QUERIES[4]["text"]

        default_val = selected_sample_text if selected_sample_text else SAMPLE_DEMO_QUERIES[0]["text"]

        user_input = st.text_area(
            "Nội dung câu thoại của khách hàng (tiếng Anh):",
            value=default_val,
            height=110,
            placeholder="Nhập câu thoại của khách hàng tại đây (Ví dụ: I want to cancel my order...)",
            key="live_analyzer_text_input",
        )

        run_btn = st.button("🚀 Chạy Phân Tích Ngay (Analyze Now)", type="primary", use_container_width=True)

        if run_btn or selected_sample_text:
            with st.spinner("Đang chạy suy luận mô hình SentenceTransformer all-MiniLM-L6-v2..."):
                t_start = time.time()
                res = analyze_single_text(user_input, artifacts_root=artifacts_root)
                dur_ms = (time.time() - t_start) * 1000

            if res.get("status") == "empty":
                st.warning("Vui lòng nhập nội dung văn bản.")
            else:
                st.markdown("---")
                st.markdown("### 🏆 Kết Quả Phân Tích Thời Gian Thực")

                # Top Result Metrics
                m_c1, m_c2, m_c3, m_c4 = st.columns(4)
                with m_c1:
                    st.metric("Chủ Đề Dự Đoán", res.get("display_name", "N/A"))
                with m_c2:
                    st.metric("Độ Tin Cậy (Confidence)", res.get("confidence_pct", "0%"))
                with m_c3:
                    st.metric("Phân Loại Luồng", res.get("category", "N/A"))
                with m_c4:
                    st.metric("Thời Gian Xử Lý", f"{dur_ms:.1f} ms")

                # Action and Evidence Highlight
                st.markdown("##### 📌 Hành Động Nghiệp Vụ & Bằng Chứng Trích Xuất:")
                cat = res.get("category", "")
                badge_color = res.get("badge_color", "#38bdf8")

                span_s, span_e, span_t = res.get("evidence_span", (0, len(user_input), user_input))
                ev_status = "human_verified" if "Đã Biết" in cat else ("model_supported" if "Mới" in cat else "cluster_only")
                hl_html = highlight_evidence_span(user_input, span_s, span_e, evidence_status=ev_status)

                st.markdown(
                    f"""
                    <div class="turn-box" style="border-left-color: {badge_color};">
                        <div style="display: flex; justify-content: space-between; font-size: 0.85rem; margin-bottom: 8px;">
                            <span style="color: {badge_color}; font-weight: 700;">● QUYẾT ĐỊNH: {res.get('decision')}</span>
                            <span style="color: #94a3b8;">Độ dài câu: {len(user_input)} ký tự</span>
                        </div>
                        <div style="font-size: 1.05rem; color: #f8fafc; line-height: 1.6; margin-bottom: 10px;">
                            {hl_html}
                        </div>
                        <div style="font-size: 0.825rem; color: #94a3b8; border-top: 1px solid #334155; padding-top: 8px;">
                            💡 <b>Lý giải AI:</b> {res.get('explanation')}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Detail comparisons
                r_col1, r_col2 = st.columns([1, 1])
                with r_col1:
                    st.markdown("##### 📊 Top 4 Chủ Đề Tương Đồng Cao Nhất:")
                    matches = res.get("top_matches", [])
                    if matches:
                        match_df = pd.DataFrame(matches)
                        fig_m = px.bar(
                            match_df,
                            x="score",
                            y="flow",
                            orientation="h",
                            text="pct",
                            color="type",
                            color_discrete_map={"Known": "#34d399", "Novel Discovery": "#f59e0b"},
                            labels={"score": "Độ Tương Đồng Cosine", "flow": "Chủ Đề (Flow)", "type": "Loại"},
                            template="plotly_dark",
                            title="Xác Suất So Khớp Của Các Chủ Đề",
                        )
                        fig_m.update_layout(
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)",
                            font=dict(color="#f8fafc", family="Inter, sans-serif"),
                            height=250,
                            margin=dict(l=10, r=10, t=30, b=10),
                        )
                        st.plotly_chart(fig_m, use_container_width=True)

                with r_col2:
                    st.markdown("##### 🔮 Đối Soát Khám Phá Cụm (Discovery Match):")
                    nc = res.get("nearest_cluster")
                    if nc:
                        st.success(f"✓ Tìm thấy cụm liên quan trong kho phát hiện: **Cụm #{nc.get('cluster_id')}**")
                        st.write(f"- **Top từ khóa c-TF-IDF**: `{nc.get('top_keywords')}`")
                        st.write(f"- **Trạng thái thẩm định**: `{nc.get('status')}`")
                        if nc.get("overlap_keywords"):
                            st.write(f"- **Từ khóa giao thoa**: `{', '.join(nc.get('overlap_keywords'))}`")
                    else:
                        st.info("Câu thoại khớp vào các luồng cố định có sẵn, không trùng cụm mới trong Discovery Pool.")

    # -------------------------------------------------------------
    # TAB 2: BATCH CSV PROCESSING
    # -------------------------------------------------------------
    with tab_batch:
        st.markdown("#### 📁 Tải Lên Danh Sách Hội Thoại Để Quét Hàng Loạt (Batch Inference)")
        st.write("Tải lên file CSV chứa câu thoại khách hàng hoặc bấm nút nạp tập 15 hội thoại mẫu để chạy thử ngay:")

        b_c1, b_c2 = st.columns([2, 1])
        with b_c1:
            uploaded_file = st.file_uploader("Chọn file CSV hội thoại:", type=["csv"])
        with b_c2:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            use_sample_btn = st.button("⚡ Nạp 15 Câu Thoại Mẫu ABCD", use_container_width=True)

        batch_df = None

        if uploaded_file is not None:
            try:
                batch_df = pd.read_csv(uploaded_file)
                st.success(f"✓ Đã nạp thành công file với **{len(batch_df):,} dòng**.")
            except Exception as e:
                st.error(f"Lỗi đọc file CSV: {e}")

        elif use_sample_btn or "sample_batch_df" in st.session_state:
            if use_sample_btn or "sample_batch_df" not in st.session_state:
                sample_data = [
                    {"customer_text": "I received my jacket yesterday but the zipper is completely broken."},
                    {"customer_text": "Please cancel my order #58219 right now, delivery is too slow."},
                    {"customer_text": "Why was my account charged 49 dollars for the monthly subscription?"},
                    {"customer_text": "The checkout page gives error 500 when I enter credit card details."},
                    {"customer_text": "Hello, good morning! Thanks for your help today."},
                    {"customer_text": "I forgot my password and cannot log into my account."},
                    {"customer_text": "Can you change my shipping address to 123 Main Street?"},
                    {"customer_text": "Is this boots model available in size 10 black?"},
                    {"customer_text": "Do you offer price matching if competitor has lower price?"},
                    {"customer_text": "What is the return window policy for storewide purchases?"},
                    {"customer_text": "My package tracking says delivered but I never received it."},
                    {"customer_text": "How do I upgrade my membership plan to premium tier?"},
                    {"customer_text": "There is a strange charge on my bill that I want to dispute."},
                    {"customer_text": "The search bar on the website is not showing any results."},
                    {"customer_text": "Thank you, have a great day!"},
                ]
                st.session_state["sample_batch_df"] = pd.DataFrame(sample_data)
            batch_df = st.session_state["sample_batch_df"]
            st.info("💡 Đang sử dụng danh sách 15 câu thoại mẫu bao gồm đa dạng luồng nghiệp vụ.")

        if batch_df is not None:
            text_cols = [c for c in batch_df.columns if batch_df[c].dtype == object]
            default_col = text_cols[0] if text_cols else batch_df.columns[0]

            chosen_col = st.selectbox("Chọn cột chứa câu thoại khách hàng:", options=batch_df.columns, index=batch_df.columns.get_loc(default_col))

            run_batch_btn = st.button("▶️ Chạy Phân Tích Hàng Loạt", type="primary")

            if run_batch_btn:
                progress_bar = st.progress(0, text="Đang xử lý vector hóa mô hình...")
                for p in range(1, 80, 20):
                    time.sleep(0.05)
                    progress_bar.progress(p, text=f"Đang phân loại batch {p}%...")

                res_df = analyze_batch_dataframe(batch_df, chosen_col)
                progress_bar.progress(100, text="Hoàn tất phân tích 100%!")

                st.markdown("---")
                st.markdown("### 📊 Tổng Hợp Kết Quả Quét Hàng Loạt")

                # Summary KPIs
                b_kpi1, b_kpi2, b_kpi3, b_kpi4 = st.columns(4)
                with b_kpi1:
                    st.metric("Tổng Số Câu Thoại", f"{len(res_df):,}")
                with b_kpi2:
                    known_c = sum(res_df["Phân Loại"] == "Chủ Đề Đã Biết")
                    st.metric("Chủ Đề Đã Biết (Known)", f"{known_c:,}")
                with b_kpi3:
                    novel_c = sum(res_df["Phân Loại"] == "Nhu Cầu Mới")
                    st.metric("Nhu Cầu Mới (Novel)", f"{novel_c:,}", delta=f"{novel_c/len(res_df)*100:.1f}%")
                with b_kpi4:
                    non_c = sum(res_df["Phân Loại"] == "Xã Giao")
                    st.metric("Lọc Xã Giao (Non-need)", f"{non_c:,}")

                # Batch Chart
                fig_batch = px.histogram(
                    res_df,
                    x="Chủ Đề Dự Đoán",
                    color="Phân Loại",
                    title="Phân Bổ Chủ Đề Dự Đoán Trong Tệp Dữ Liệu",
                    template="plotly_dark",
                    color_discrete_map={"Chủ Đề Đã Biết": "#34d399", "Nhu Cầu Mới": "#f59e0b", "Xã Giao": "#64748b", "Cụm Khám Phá": "#38bdf8"},
                )
                fig_batch.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#f8fafc", family="Inter, sans-serif"),
                    height=320,
                )
                st.plotly_chart(fig_batch, use_container_width=True)

                # Results Dataframe
                st.markdown("##### 📑 Bảng Chi Tiết Kết Quả:")
                st.dataframe(res_df, use_container_width=True, hide_index=True)

                # Export CSV button
                csv_bytes = res_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📥 Tải Xuống File Báo Cáo Kết Quả (CSV)",
                    data=csv_bytes,
                    file_name="batch_analysis_results.csv",
                    mime="text/csv",
                )


if __name__ == "__main__":
    render_live_analyzer()
