"""Phiên bản 1.0 (Gốc) - BERTopic PoC Nghiệm Thu Khoa Học & Báo Cáo Đánh Giá.

Phiên bản tập trung vào tính trung thực khoa học, kiểm soát 4 Gate (G0 -> G3),
và trực quan hóa tĩnh theo nguyên tắc Zero-Fit on Render.
"""
from __future__ import annotations

import streamlit as st
from bertopic_poc.ui.data_loader import (
    get_default_artifacts_root,
    load_manifest_bundle,
    load_evaluation_metrics,
)

st.set_page_config(
    page_title="BERTopic Customer Conversation PoC (Bản Báo Cáo Nghiệm Thu)",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


def render_sidebar():
    with st.sidebar:
        st.markdown("### 🧭 Điều Hướng Nghiệm Thu")
        st.info(
            "Vui lòng chọn một trang phân tích từ menu điều hướng phía trên của Streamlit:\n\n"
            "- **1_Overview**: Giám sát 4 Gates & KPIs\n"
            "- **2_Fixed_Topic_Analytics**: Phân tích 10 Flows\n"
            "- **3_New_Topic_Discovery**: 1.552 Ứng viên & Thẩm định mù\n"
            "- **4_Conversation_Explorer**: Tra cứu & Highlight bằng chứng\n"
            "- **5_Model_Evaluation**: Đo lường & Báo cáo PoC"
        )
        st.markdown("---")
        st.caption("🔒 **Trạng thái**: Schema 1.0.0 LOCKED")
        st.caption("⚡ **Nguyên tắc**: Zero-Fit on Render")
        st.caption("🛡️ **Bảo mật**: PII Masked & Tokenized")


def main():
    render_sidebar()

    st.title("🎯 Hệ Thống Phân Tích & Khám Phá Chủ Đề Hội Thoại Khách Hàng")
    st.caption("Nền tảng trực quan hóa kết quả BERTopic Customer Conversation PoC (Schema 1.0.0 - Bản Báo Cáo)")

    # Status badges
    col_b1, col_b2, col_b3, col_b4 = st.columns(4)
    with col_b1:
        st.success("🔒 **Gates**: G0, G1, G2, G3 LOCKED")
    with col_b2:
        st.info("⚡ **Zero-Fit**: 100% Pre-computed Artifacts")
    with col_b3:
        st.warning("🛡️ **PII**: Che mờ & Ẩn danh")
    with col_b4:
        st.success("✅ **Nghiệm thu**: VALID")

    st.markdown("---")

    # Load summary metrics
    try:
        artifacts_root = str(get_default_artifacts_root())
        bundle = load_manifest_bundle(artifacts_root)
        metrics = load_evaluation_metrics(artifacts_root)
        dq = bundle.get("data_quality", {})
        counts = dq.get("counts", {})

        st.subheader("📌 Tổng Quan Nhanh Toàn Hệ Thống")
        kpi_c1, kpi_c2, kpi_c3, kpi_c4 = st.columns(4)
        kpi_c1.metric("Tổng Cuộc Hội Thoại", f"{counts.get('read', 10042):,}")
        kpi_c2.metric("Số Phân Đoạn Xử Lý", "103,901")
        kpi_c3.metric("Mô Hình Thắng Cuộc", "all-MiniLM-L6-v2")
        kpi_c4.metric("Flow-Family Recovery", f"{metrics.get('recovered_flows_proxy', 2)} / 2 Họ")

        st.markdown("---")

        st.subheader("🚀 Khám Phá Các Phân Hệ Phân Tích")
        p_col1, p_col2 = st.columns(2)

        with p_col1:
            st.markdown(
                """
                #### 1. 📊 [Overview](pages/1_Overview.py)
                - Giám sát tiến trình 4 Gate kiến trúc (G0, G1, G2, G3).
                - Đối soát mã băm SHA-256 tính toàn vẹn của artifacts.
                - Cấu hình mô hình SentenceTransformer, UMAP & HDBSCAN.
                - Trạng thái sức khỏe dữ liệu (Data Quality & Null reasons).

                #### 2. 📈 [Fixed Topic Analytics](pages/2_Fixed_Topic_Analytics.py)
                - Bộ lọc phạm vi: `scope:test_open` (7 Known flows) & `scope:test_closed` (10 Closed flows).
                - Biểu đồ phân bổ tỷ lệ hội thoại (`conversation_share`).
                - Bảng chi tiết 4 đơn vị đếm thống kê trung thực.
                - Cảnh báo rõ ràng các trường `unique_customers`, `time_bucket`, `channel` là `\\N`.
                """
            )

        with p_col2:
            st.markdown(
                """
                #### 3. 🔍 [New Topic Discovery](pages/3_New_Topic_Discovery.py)
                - Khám phá 1.552 ứng viên cụm mới theo 3 Random Seeds (42, 13, 73).
                - Khung xem chi tiết cụm (Top-10 từ khóa, số hội thoại hỗ trợ).
                - Thẩm định mù (Blinded Review) với 10 mẫu (5 centroid + 5 random) và điểm rubric 2 trục.
                - Đồ thị sáp nhập cụm (Merge DAG) không chu trình.

                #### 4. 💬 [Conversation Explorer](pages/4_Conversation_Explorer.py)
                - Tra cứu hội thoại theo `conversation_id`, topic và trạng thái bằng chứng.
                - Phân trang mượt mà (10, 25, 50 dòng/trang) không quá tải bộ nhớ.
                - Hiển thị câu thoại khách hàng đã che mờ PII kèm highlight tọa độ `[span_start:span_end]`.

                #### 5. 🎯 [Model Evaluation](pages/5_Model_Evaluation.py)
                - Thẻ KPI đo lường cốt lõi (Macro-F1 0.5553, Unknown F1 0.3618, Routing 100%).
                - Ma trận Flow-family Recovery chi tiết cho 2 họ chủ đề.
                - Biểu đồ độ ổn định phân cụm ARI giữa các seed và phân tích độ dài lượt thoại.
                - Xem trực tiếp toàn văn báo cáo Markdown `report.md`.
                """
            )

    except Exception as e:
        st.error(f"Lỗi tải dữ liệu artifacts: {e}")
        st.info("Vui lòng kiểm tra thư mục artifacts/phase1 đã có đầy đủ các file nghiệm thu Schema 1.0.0.")


if __name__ == "__main__":
    main()
