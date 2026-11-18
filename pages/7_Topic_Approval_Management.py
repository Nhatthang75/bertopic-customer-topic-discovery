"""Topic Approval and Taxonomy Management Page for BERTopic PoC Dashboard."""
from __future__ import annotations

import json
import streamlit as st
import pandas as pd

from bertopic_poc.ui.data_loader import (
    get_default_artifacts_root,
    load_candidates,
    load_reviews_map,
)
from bertopic_poc.ui.utils import inject_custom_css
from bertopic_poc.taxonomy import KNOWN_K_FLOWS, HIDDEN_FINAL_FLOWS

st.set_page_config(
    page_title="Topic Approval Management | BERTopic PoC",
    page_icon="🏷️",
    layout="wide",
)


def render_approval_management():
    inject_custom_css()

    st.title("🏷️ Quản Trị & Phê Duyệt Danh Mục Chủ Đề (Taxonomy & Novel Topic Approvals)")
    st.caption("Khu vực tác vụ dành cho Quản lý CSKH: Xem xét các cụm chủ đề mới do AI phát hiện và quyết định đưa vào danh mục chính thức")

    artifacts_root = str(get_default_artifacts_root())

    try:
        candidates = load_candidates(artifacts_root)
        reviews_map = load_reviews_map(artifacts_root)
    except Exception as e:
        st.error(f"Lỗi nạp dữ liệu ứng viên: {e}")
        return

    # Initialize session state for approvals
    if "approved_clusters" not in st.session_state:
        st.session_state["approved_clusters"] = {}
    if "merged_clusters" not in st.session_state:
        st.session_state["merged_clusters"] = {}

    # Executive Overview Cards
    top_c1, top_c2, top_c3, top_c4 = st.columns(4)
    with top_c1:
        st.metric("Chủ Đề Cố Định Ban Đầu", f"{len(KNOWN_K_FLOWS) + len(HIDDEN_FINAL_FLOWS)} Flows")
    with top_c2:
        st.metric("Tổng Số Cụm AI Đề Xuất", f"{len(candidates):,} Cụm")
    with top_c3:
        num_approved = len(st.session_state["approved_clusters"])
        st.metric("Chủ Đề Mới Đã Duyệt", f"{num_approved} Chủ đề", delta=f"+{num_approved}" if num_approved > 0 else None)
    with top_c4:
        num_merged = len(st.session_state["merged_clusters"])
        st.metric("Cụm Sáp Nhập (Merged)", f"{num_merged} Cụm")

    st.markdown("---")

    # Workflow Section
    st.markdown("### 📋 Danh Sách Cụm Chủ Đề Mới Chờ Quản Lý Phê Duyệt")

    f_col1, f_col2, f_col3 = st.columns(3)
    with f_col1:
        chosen_seed = st.selectbox("Lọc theo Random Seed:", options=["Seed 42 (Chính thức)", "Seed 13", "Seed 73", "Tất cả"], index=0)
    with f_col2:
        chosen_status = st.selectbox("Lọc theo trạng thái:", options=["Tất cả", "accepted_novel", "monitor", "proposed"], index=0)
    with f_col3:
        kw_filter = st.text_input("Lọc theo từ khóa:", placeholder="VD: subscription, troubleshooting, refund...")

    filtered = candidates
    if "42" in chosen_seed:
        filtered = [c for c in filtered if c.get("seed") == 42]
    elif "13" in chosen_seed:
        filtered = [c for c in filtered if c.get("seed") == 13]
    elif "73" in chosen_seed:
        filtered = [c for c in filtered if c.get("seed") == 73]

    if chosen_status != "Tất cả":
        filtered = [c for c in filtered if c.get("status") == chosen_status]

    if kw_filter.strip():
        q = kw_filter.strip().lower()
        filtered = [c for c in filtered if any(q in kw.lower() for kw in c.get("top_keywords", []))]

    st.write(f"Tìm thấy **{len(filtered):,} cụm** theo bộ lọc:")

    # Select cluster to review
    if not filtered:
        st.info("Không có cụm nào khớp với bộ lọc.")
        return

    cluster_options = [f"Cụm #{c.get('cluster_id')} | Seed {c.get('seed')} | Support: {c.get('conversation_support')} | Keywords: {', '.join(c.get('top_keywords', [])[:5])}" for c in filtered[:50]]
    chosen_label = st.selectbox("Chọn một cụm để thực hiện phê duyệt / xử lý nghiệp vụ:", options=cluster_options, index=0)

    chosen_cid = int(chosen_label.split(" | ")[0].replace("Cụm #", ""))
    target_cand = next((c for c in filtered if c.get("cluster_id") == chosen_cid), None)

    if target_cand:
        st.markdown(f"#### 🔍 Chi Tiết Cụm Ứng Viên #{chosen_cid}")

        det_c1, det_c2 = st.columns([2, 1])
        with det_c1:
            st.write(f"- **Top 10 từ khóa đặc trưng (c-TF-IDF)**: `{', '.join(target_cand.get('top_keywords', []))}`")
            st.write(f"- **Số cuộc hội thoại hỗ trợ**: `{target_cand.get('conversation_support')}` cuộc hội thoại")
            st.write(f"- **Chủ đề gần nhất trong kho**: `{target_cand.get('nearest_known_flow', 'N/A')}`")

            # Check review info
            rev = reviews_map.get(chosen_cid)
            if rev:
                st.write(f"- **Kết quả thẩm định mù 2 chuyên gia**: Quyết định `{rev.get('adjudication', {}).get('status')}` (Coherence: `{rev.get('adjudication', {}).get('coherence')}`, Novelty: `{rev.get('adjudication', {}).get('novelty')}`)")
            else:
                st.write("- **Trạng thái thẩm định**: Chưa có biên bản mù")

        with det_c2:
            current_override = st.session_state["approved_clusters"].get(chosen_cid)
            current_merge = st.session_state["merged_clusters"].get(chosen_cid)

            if current_override:
                st.success(f"✅ **ĐÃ PHÊ DUYỆT**: Trở thành flow mới `flow:{current_override['new_name']}`")
            elif current_merge:
                st.warning(f"🔗 **ĐÃ SÁP NHẬP**: Gộp vào `{current_merge['target_flow']}`")
            else:
                st.info(f"⏳ **TRẠNG THÁI HIỆN TẠI**: `{target_cand.get('status')}`")

        # Action Buttons for Manager
        st.markdown("##### ⚡ Quyết Định Của Quản Lý (Management Action):")
        act_col1, act_col2, act_col3 = st.columns(3)

        with act_col1:
            default_new_name = target_cand.get("cluster_name", f"custom_flow_{chosen_cid}").replace(" ", "_").lower()
            new_flow_name = st.text_input("Tên Flow Mới:", value=default_new_name, key=f"name_input_{chosen_cid}")
            if st.button("✅ Phê Duyệt Thêm Vào Danh Mục", type="primary", use_container_width=True, key=f"approve_{chosen_cid}"):
                st.session_state["approved_clusters"][chosen_cid] = {
                    "cluster_id": chosen_cid,
                    "new_name": new_flow_name,
                    "top_keywords": target_cand.get("top_keywords", []),
                    "support": target_cand.get("conversation_support"),
                }
                if chosen_cid in st.session_state["merged_clusters"]:
                    del st.session_state["merged_clusters"][chosen_cid]
                st.success(f"✓ Đã phê duyệt cụm #{chosen_cid} thành chủ đề chính thức `{new_flow_name}`!")
                st.rerun()

        with act_col2:
            all_existing_flows = KNOWN_K_FLOWS + HIDDEN_FINAL_FLOWS
            target_merge_flow = st.selectbox("Chọn Flow có sẵn để gộp:", options=all_existing_flows, index=0, key=f"merge_target_{chosen_cid}")
            if st.button("🔗 Sáp Nhập Vào Flow Này", use_container_width=True, key=f"merge_{chosen_cid}"):
                st.session_state["merged_clusters"][chosen_cid] = {
                    "cluster_id": chosen_cid,
                    "target_flow": target_merge_flow,
                }
                if chosen_cid in st.session_state["approved_clusters"]:
                    del st.session_state["approved_clusters"][chosen_cid]
                st.warning(f"✓ Đã sáp nhập cụm #{chosen_cid} vào luồng `{target_merge_flow}`!")
                st.rerun()

        with act_col3:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            if st.button("🔄 Đặt Lại Trạng Thái Ban Đầu", use_container_width=True, key=f"reset_{chosen_cid}"):
                st.session_state["approved_clusters"].pop(chosen_cid, None)
                st.session_state["merged_clusters"].pop(chosen_cid, None)
                st.info(f"Đã đặt lại trạng thái ban đầu cho cụm #{chosen_cid}.")
                st.rerun()

    # Dynamic Updated Taxonomy Section
    st.markdown("---")
    st.markdown("### 🏛️ Danh Mục Chủ Đề Đã Được Cập Nhật (Dynamic Taxonomy v1.1)")
    st.caption("Danh mục này tự động mở rộng theo thời gian thực mỗi khi quản lý bấm duyệt chủ đề mới.")

    base_flows = [{"Mã Flow": f"flow:{f}", "Tên Phổ Thông": f.replace('_', ' ').title(), "Nguồn Gốc": "Cố Định Ban Đầu (Baseline)"} for f in (KNOWN_K_FLOWS + HIDDEN_FINAL_FLOWS)]

    for cid, app_info in st.session_state["approved_clusters"].items():
        base_flows.append({
            "Mã Flow": f"flow:{app_info['new_name']}",
            "Tên Phổ Thông": app_info['new_name'].replace('_', ' ').title(),
            "Nguồn Gốc": f"AI Khám Phá (Cụm #{cid} - Quản lý đã duyệt)",
        })

    tax_df = pd.DataFrame(base_flows)
    st.dataframe(tax_df, use_container_width=True, hide_index=True)

    # Export Updated Taxonomy
    tax_json = tax_df.to_json(orient="records", indent=2)
    st.download_button(
        label="📥 Tải Xuống Danh Mục Taxonomy Mới (JSON)",
        data=tax_json,
        file_name="updated_taxonomy_v1.1.json",
        mime="application/json",
    )


if __name__ == "__main__":
    render_approval_management()
