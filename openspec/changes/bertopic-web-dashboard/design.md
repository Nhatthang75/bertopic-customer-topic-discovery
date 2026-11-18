# Design: Kiến Trúc Kỹ Thuật Web Dashboard Streamlit Cho BERTopic PoC

## Context

Dự án đã hoàn tất giai đoạn PoC thuật toán (`bertopic-customer-conversation-poc`) với 60/60 task, toàn bộ kết quả thử nghiệm và đánh giá chất lượng đã được cố định vào các file artifact Schema 1.0.0 tại `artifacts/phase1/` dưới sự bảo vệ của 4 Gate kiến trúc (G0, G1, G2, G3). Xem chi tiết bối cảnh và động lực tại `proposal.md`.

Hệ sinh thái công nghệ sẵn có:
- Ngôn ngữ: Python 3.11 trong môi trường ảo `.venv/`.
- Cấu trúc dữ liệu: Các file RFC4180 CSV (với null token `\N`), JSONL và JSON.
- Module đọc dữ liệu hiện có: `bertopic_poc.dashboard` và `bertopic_poc.contracts`.

Thiết kế này đặc tả kiến trúc tầng trình diễn (Presentation Layer) sử dụng **Streamlit** độc lập, tương tác trực tiếp với kho dữ liệu tĩnh mà không can thiệp vào bất kỳ module logic lõi nào.

## Goals / Non-Goals

**Goals:**
- Xây dựng ứng dụng Streamlit đa trang với 5 màn hình trực quan: Overview, Fixed Topic Analytics, New Topic Discovery, Conversation Explorer, Model Evaluation.
- Thực thi nghiêm ngặt nguyên tắc **Zero-Fit on Render**: Tải 100% dữ liệu từ artifacts đã tính toán sẵn, tuyệt đối không gọi `fit`/`fit_transform` hay sinh vector embedding khi tương tác giao diện.
- Trực quan hóa chính xác 4 đơn vị đếm thống kê (`message`, `segment`, `mention`, `conversation`), xử lý minh bạch giá trị rỗng `\N`.
- Hiển thị trực quan câu thoại che mờ PII kèm highlight bằng chứng phân đoạn theo đúng tọa độ provenance offsets `[span_start, span_end]`.
- Thời gian phản hồi nhanh (< 100ms cho các thao tác chuyển trang và lọc dữ liệu nhờ `@st.cache_data`).

**Non-Goals:**
- Không huấn luyện lại, tinh chỉnh hoặc suy luận lại mô hình BERTopic hay SentenceTransformer.
- Không sửa đổi cấu trúc raw data trong `data/raw/` hoặc các snapshot Gate đã khóa.
- Không tự tạo dữ liệu giả lập cho các trường metadata không có trong ABCD (`unique_customers`, `time_bucket`, `channel`).
- Không xây dựng hệ thống cơ sở dữ liệu quan hệ (SQL) hay backend server phức tạp; Streamlit đọc trực tiếp file hệ thống.

## Decisions

### 1. Kiến trúc Đa trang Streamlit (Multi-page App Structure)
- **Quyết định**: Sử dụng cấu trúc thư mục tiêu chuẩn `app.py` (điểm vào chính) kết hợp với các trang con trong thư mục `pages/` (hoặc định tuyến qua `st.navigation` của Streamlit hiện đại):
  - `pages/1_Overview.py`
  - `pages/2_Fixed_Topic_Analytics.py`
  - `pages/3_New_Topic_Discovery.py`
  - `pages/4_Conversation_Explorer.py`
  - `pages/5_Model_Evaluation.py`
- **Lý do**: Tách biệt logic hiển thị của từng trang, giúp mã nguồn gọn gàng, dễ bảo trì và kiểm thử đơn vị độc lập.
- **Phương án thay thế đã loại bỏ**: Xây dựng toàn bộ trong 1 file `dashboard.py` dùng tab/radio; bị loại vì file sẽ quá dài (>1.000 dòng) và khó phân tách trạng thái phiên.

### 2. Tầng Nạp Dữ Liệu Bộ Nhớ Đệm (Cached Data Access Layer)
- **Quyết định**: Xây dựng module `bertopic_poc.ui.data_loader` bọc các hàm đọc artifact bằng decorator `@st.cache_data`:
  - `get_manifest_data()`: Đọc `run_manifest.json`, `g*_snapshot.json`.
  - `get_topic_statistics(scope_id)`: Đọc và lọc `topic_statistics.csv`.
  - `get_candidates(seed, status)`: Đọc và lọc `candidates.jsonl`.
  - `get_reviews()`: Đọc `reviews.jsonl` tạo từ điển tra cứu theo `cluster_key`.
  - `get_conversation_index()`: Tạo chỉ mục ánh xạ nhanh từ `conversation_topics.csv` và `assignments.jsonl`.
  - `get_conversation_segments(conversation_id)`: Đọc phân đoạn từ `segments.jsonl` hoặc file index.
- **Lý do**: Tránh việc đọc lại đĩa cứng nhiều lần khi người dùng tương tác với bộ lọc, giảm độ trễ từ vài giây xuống mili-giây.

### 3. Xử Lý Tối Ưu Tệp Dữ Liệu Lớn (`segments.jsonl` ~53MB)
- **Quyết định**: Không nạp toàn bộ 103.901 dòng của `segments.jsonl` vào DataFrame hiển thị cùng lúc. Thay vào đó:
  - Chỉ mục hóa ánh xạ `conversation_id -> list[segment_id]` trong bộ nhớ nhẹ.
  - Phân trang hiển thị ở Conversation Explorer (10, 20 hoặc 50 hội thoại mỗi trang).
  - Chỉ truy xuất nội dung chi tiết của cuộc hội thoại khi người dùng bấm chọn xem chi tiết.
- **Lý do**: Tiết kiệm RAM của máy chủ/máy trạm cá nhân, đảm bảo trình duyệt không bị treo (DOM overload).

### 4. Cơ Chế Highlight Bằng Chứng Offsets & Che Mờ PII
- **Quyết định**: Sử dụng hàm format HTML an toàn (kết hợp `st.markdown(..., unsafe_allow_html=True)`) để cắt lát chuỗi `masked_customer_text` theo `[span_start:span_end]`:
  - Đoạn text trước bằng chứng: hiển thị bình thường.
  - Đoạn text trong bằng chứng: bọc trong thẻ `<mark class="evidence-tag">` có màu sắc theo `evidence_status` (xanh cho `human_verified`, vàng cho `model_supported`, xám cho `cluster_only`).
  - Đoạn text sau bằng chứng: hiển thị tiếp tục.
- **Lý do**: Đáp ứng chính xác yêu cầu truy vết bằng chứng câu thoại của đặc tả mà không làm thay đổi nội dung câu từ của khách hàng.

### 5. Ánh Xạ Nguồn Dữ Liệu Chi Tiết (Data Source Mapping)

| Trang | Khối giao diện / Biểu đồ | File nguồn artifact | Trường dữ liệu / Công thức |
|---|---|---|---|
| **Overview** | Thẻ KPI tổng quan | `run_manifest.json`, `data_quality.json` | `counts.eligible`, `model_revisions.winning_model`, `benchmark_validity` |
| **Overview** | Trạng thái 4 Gates | `run_manifest.json`, `g*_snapshot.json` | `gate_events[].gate`, `gate_events[].status`, `timestamp`, `locked_outputs` |
| **Fixed Topics** | Biểu đồ phân bổ tỷ lệ | `topic_statistics.csv` | Lọc `scope_id`, vẽ cột `conversation_share` = `conversation_count / eligible_conversations` |
| **Fixed Topics** | Bảng 4 đơn vị đếm | `topic_statistics.csv` | `customer_message_count`, `source_messages_with_assignment`, `segment_count`, `conversation_count` |
| **New Discovery**| Bảng ứng viên cụm mới | `candidates.jsonl` | `cluster_key`, `seed`, `keywords`, `conversation_support`, `status` |
| **New Discovery**| Khung thẩm định mù | `reviews.jsonl`, `candidates.jsonl` | `representative_unit_ids`, `random_unit_ids`, `rubric_scores`, `adjudication` |
| **Conversation** | Danh sách tìm kiếm | `conversation_topics.csv` | `conversation_id`, `topic_id`, `primary_topic`, `max_score`, `evidence_count` |
| **Conversation** | Chi tiết câu thoại | `segments.jsonl`, `assignments.jsonl` | `masked_customer_text`, `evidence_spans` (`span_start`, `span_end`), `content_status` |
| **Model Eval**   | KPI hiệu năng chính | `metrics.json` | `closed_macro_f1`, `unknown_f1`, `routing_recall`, `recovered_flows_proxy` |
| **Model Eval**   | Flow Recovery Matrix | `metrics.json` (`semantic_recovery`) | `qualifying_clusters`, `family_precision`, `family_recall`, `semantic_supported` |
| **Model Eval**   | Clustering Stability | `metrics.json` (`stability`) | `ARI_all`, `shared_coverage` giữa seed 42 vs 13, 42 vs 73 |
| **Model Eval**   | Toàn văn Báo cáo | `report.md` | Render Markdown gốc trực tiếp bằng `st.markdown()` |

### 6. Xử Lý Trạng Thái Giao Diện: Loading, Empty States và Phục Hồi Lỗi (Graceful Degradation)
- **Loading State**: Sử dụng `st.spinner("Đang tải dữ liệu...")` trong các thao tác nạp dữ liệu lần đầu và chuyển trang phân đoạn lớn, đảm bảo người dùng biết hệ thống đang phản hồi.
- **Empty States**: Khi bộ lọc hoặc từ khóa tìm kiếm không trả về bản ghi nào, giao diện hiển thị thông báo `st.info()` thân thiện hướng dẫn người dùng thử lại, ngăn chặn hiện tượng bảng dữ liệu trống trơn gây hiểu nhầm ứng dụng bị lỗi.
- **Error Handling**: Khi thiếu tệp artifact hoặc tệp bị sai schema, khối chức năng liên quan hiển thị hộp thoại `st.error()` chi tiết và cô lập lỗi an toàn (graceful degradation), đảm bảo các trang và thành phần độc lập khác vẫn hoạt động ổn định.

## Risks / Trade-offs

- **[Rủi ro] Kích thước file `segments.jsonl` lớn (53MB)**  
  $\to$ *Giải pháp giảm thiểu*: Tách cache và chỉ đọc theo batch/hội thoại khi có yêu cầu xem chi tiết.
- **[Rủi ro] Hiểu nhầm các trường metadata rỗng (`unique_customers`, `time_bucket`, `channel`)**  
  $\to$ *Giải pháp giảm thiểu*: Hiển thị hộp cảnh báo giải thích rõ đây là đặc điểm của bộ dữ liệu ABCD, không có thông tin thời gian/kênh, tránh người dùng tưởng dashboard bị lỗi dữ liệu.
- **[Rủi ro] Thao tác lọc chủ đề làm thay đổi mẫu số chia tỷ lệ**  
  $\to$ *Giải pháp giảm thiểu*: Cố định mẫu số `eligible_conversations` lấy trực tiếp từ file `topic_statistics.csv`, việc lọc chủ đề chỉ thay đổi danh sách dòng hiển thị (tử số), không tính toán lại mẫu số.

## Migration / Rollback Plan

- **Tính tương thích**: Dashboard Streamlit là một giao diện độc lập được triển khai bổ sung.
- **Khả năng rollback**: Nếu có bất kỳ sự cố nào, chỉ cần dừng tiến trình Streamlit; toàn bộ kết quả PoC, file báo cáo và script CLI `scripts/run_dashboard.py` vẫn nguyên vẹn 100%.

## Open Questions

- *Không có câu hỏi mở*: Toàn bộ 6 file dữ liệu chuẩn Schema 1.0.0, mã băm Gate, và các chỉ số đo lường đã được chuẩn hóa và kiểm tra hoàn tất.
