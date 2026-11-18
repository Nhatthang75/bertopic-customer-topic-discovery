"""Fixed Topic Analytics Page for BERTopic PoC Dashboard."""
from __future__ import annotations

import streamlit as st
import pandas as pd
import plotly.express as px

from bertopic_poc.ui.data_loader import (
    get_default_artifacts_root,
    load_topic_statistics,
)
from bertopic_poc.ui.utils import inject_custom_css

st.set_page_config(
    page_title="Fixed Topic Analytics | BERTopic PoC",
    page_icon="📈",
    layout="wide",
)

def render_fixed_topics():
    inject_custom_css()
    st.title("📈 Phân Tích Chủ Đề Cố Định (Fixed Topic Analytics)")
    st.caption("Khám phá phân bổ 10 Flows phân loại có giám sát theo 4 đơn vị đếm thống kê Schema 1.0.0")

    artifacts_root = str(get_default_artifacts_root())
    try:
        df_all = load_topic_statistics(artifacts_root)
    except Exception as e:
        st.error(f"Lỗi nạp dữ liệu thống kê chủ đề: {e}")
        return

    # Scope selector
    st.markdown("### 🎯 Phạm Vi Đánh Giá (Scope Selector)")
    scope_options = {
        "scope:test_open": "scope:test_open (7 Known flows trong tập mở, N=898)",
        "scope:test_closed": "scope:test_closed (10 Closed flows trong tập đóng, N=1,004)",
    }

    selected_scope = st.radio(
        "Chọn tập phân tích:",
        options=list(scope_options.keys()),
        format_func=lambda x: scope_options[x],
        horizontal=True,
    )

    df_scope = df_all[df_all["scope_id"] == selected_scope].copy()
    if df_scope.empty:
        st.warning("Không tìm thấy dữ liệu cho phạm vi đã chọn.")
        return

    eligible_n = int(df_scope["eligible_conversations"].iloc[0]) if "eligible_conversations" in df_scope.columns else 1004

    # Top KPIs for this scope
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.metric("Số Lượng Chủ Đề", f"{len(df_scope)} Flows")
    with kpi2:
        st.metric("Mẫu Số Hội Thoại Hợp Lệ (N)", f"{eligible_n:,}")
    with kpi3:
        top_topic = df_scope.sort_values(by="conversation_count", ascending=False).iloc[0]
        st.metric("Chủ Đề Phổ Biến Nhất", top_topic["topic_id"].replace("flow:", ""))
    with kpi4:
        st.metric("Tỷ Lệ Cao Nhất", f"{top_topic['conversation_share']:.2%}")

    st.markdown("---")

    # Interactive Chart Section
    st.markdown("### 📊 Biểu Đồ Phân Bổ Chủ Đề Hội Thoại")
    c_left, c_right = st.columns([1, 3])
    with c_left:
        chart_mode = st.radio(
            "Đơn vị hiển thị:",
            options=["Tỷ lệ hội thoại (%)", "Số lượng hội thoại (N)"],
            index=0,
        )
        sort_by = st.selectbox(
            "Sắp xếp theo:",
            options=["Tỷ lệ giảm dần", "Tên chủ đề A-Z"],
            index=0,
        )

    # Prepare chart dataframe
    chart_df = df_scope.copy()
    chart_df["display_name"] = chart_df["topic_id"].str.replace("flow:", "")
    chart_df["share_pct"] = chart_df["conversation_share"] * 100.0

    if sort_by == "Tỷ lệ giảm dần":
        chart_df = chart_df.sort_values(by="conversation_share", ascending=True)
    else:
        chart_df = chart_df.sort_values(by="display_name", ascending=False)

    with c_right:
        if chart_mode == "Tỷ lệ hội thoại (%)":
            fig = px.bar(
                chart_df,
                x="share_pct",
                y="display_name",
                orientation="h",
                text=chart_df["share_pct"].apply(lambda v: f"{v:.1f}%"),
                labels={"share_pct": "Tỷ Lệ Hội Thoại (%)", "display_name": "Chủ Đề (Flow)"},
                title=f"Tỷ Lệ Hội Thoại Theo Chủ Đề ({selected_scope} - Mẫu số N={eligible_n})",
                color="share_pct",
                color_continuous_scale="Blues",
                template="plotly_dark",
            )
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#f8fafc", family="Inter, sans-serif"),
                xaxis_title="Tỷ Lệ Hội Thoại (%)",
                yaxis_title="Chủ Đề",
                height=420,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            fig = px.bar(
                chart_df,
                x="conversation_count",
                y="display_name",
                orientation="h",
                text=chart_df["conversation_count"],
                labels={"conversation_count": "Số Lượng Hội Thoại", "display_name": "Chủ Đề (Flow)"},
                title=f"Số Lượng Hội Thoại Theo Chủ Đề ({selected_scope})",
                color="conversation_count",
                color_continuous_scale="Viridis",
                template="plotly_dark",
            )
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#f8fafc", family="Inter, sans-serif"),
                xaxis_title="Số Lượng Hội Thoại",
                yaxis_title="Chủ Đề",
                height=420,
            )
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Detailed 4-Counting-Units Table
    st.markdown("### 📑 Bảng Chi Tiết 4 Đơn Vị Đếm Thống Kê")
    st.caption(
        "Mỗi dòng đại diện cho một chủ đề cố định. Các giá trị tuân thủ đúng định dạng RFC4180 và Schema 1.0.0."
    )

    display_table = pd.DataFrame({
        "Mã Chủ Đề (Flow ID)": df_scope["topic_id"],
        "Câu Khách Hàng": df_scope["customer_message_count"],
        "Lượt Thoại Gán Nhãn": df_scope["source_messages_with_assignment"],
        "Số Phân Đoạn": df_scope["segment_count"],
        "Số Hội Thoại": df_scope["conversation_count"],
        "Mẫu Số Hợp Lệ": df_scope["eligible_conversations"],
        "Tỷ Lệ Hội Thoại": df_scope["conversation_share"].apply(lambda x: f"{x:.2%}"),
        "Độ Phủ Bằng Chứng": df_scope["evidence_coverage"].apply(lambda x: f"{x:.2%}" if pd.notnull(x) else "\\N"),
    })

    st.dataframe(display_table, hide_index=True, use_container_width=True)

    st.markdown("---")

    # Honest Metadata Absence Warning
    st.markdown("### ⚠️ Minh Bạch Về Metadata Không Khả Dụng Trong ABCD v1.1")
    w1, w2 = st.columns([2, 1])
    with w1:
        st.warning(
            "**Bảo toàn tính trung thực của dữ liệu (No Hallucination)**:\n\n"
            "Các trường sau trong bảng `topic_statistics.csv` được gắn giá trị `\\N` (Null Token chuẩn RFC4180):\n"
            "- **`unique_customers`**: Không có sẵn (`\\N`) vì ABCD không phân định mã định danh khách hàng duy nhất giữa các phiên.\n"
            "- **`time_bucket`**: Không có sẵn (`\\N`) vì dữ liệu ABCD thu thập qua CrowdWorker không có thông tin mốc thời gian thực.\n"
            "- **`channel`**: Không có sẵn (`\\N`) vì toàn bộ hội thoại được thực hiện qua giao diện web chat mô phỏng duy nhất.\n\n"
            "Hệ thống tuyệt đối **không tự suy diễn số liệu giả lập** nhằm đảm bảo tính chuẩn xác cho nghiệm thu khoa học."
        )
    with w2:
        st.info(
            "**Công Thức Tính Toán Chuẩn**:\n\n"
            "$$\\text{conversation\\_share} = \\frac{\\text{conversation\\_count}}{\\text{eligible\\_conversations}}$$\n\n"
            "- Với `scope:test_open`: Mẫu số = 898\n"
            "- Với `scope:test_closed`: Mẫu số = 1,004\n\n"
            "Khi lọc chủ đề hiển thị, mẫu số vẫn được **giữ nguyên không đổi**."
        )


if __name__ == "__main__":
    render_fixed_topics()
