# Tasks

## 1. Nền tảng ứng dụng Streamlit và Tầng nạp dữ liệu đệm (Web Dashboard Core)

- [x] 1.1 Khởi tạo cấu trúc dự án Streamlit (`app.py`, thư mục `pages/` và module `bertopic_poc.ui`); xác minh cấu trúc file và kiểm tra khả năng import thư viện Streamlit trong môi trường ảo.
- [x] 1.2 Xây dựng module `bertopic_poc.ui.data_loader` với cơ chế bộ nhớ đệm `@st.cache_data` để nạp `run_manifest.json`, `topic_statistics.csv`, `candidates.jsonl`, `reviews.jsonl`, `metrics.json`, `report.md`; tích hợp trạng thái tải (loading spinner) và xử lý lỗi tệp an toàn; xác minh thời gian nạp dưới 500ms và không gọi bất kỳ hàm huấn luyện mô hình nào.
- [x] 1.3 Xây dựng chỉ mục tra cứu hội thoại nhẹ (lightweight conversation index) từ `conversation_topics.csv` và `assignments.jsonl`; xác minh khả năng tra cứu nhanh theo `conversation_id` và lọc theo topic mà không quá tải RAM.
- [x] 1.4 Viết unit test cho data loader trong `tests/test_ui_data_loader.py`; xác minh xử lý an toàn khi thiếu file hoặc lỗi schema, đảm bảo tính bất biến của dữ liệu gốc.

## 2. Màn hình 1 — Overview & Giám sát tiến trình Gates

- [x] 2.1 Xây dựng giao diện trang `pages/1_Overview.py` hiển thị các thẻ KPI tổng quan (tổng hội thoại, phân đoạn, số chủ đề cố định, số ứng viên phát hiện); xác minh số liệu khớp chính xác 100% với `run_manifest.json` và `data_quality.json`.
- [x] 2.2 Xây dựng thành phần trực quan hóa tiến trình 4 Gate (G0, G1, G2, G3) với huy hiệu trạng thái LOCKED, vết thời gian khóa UTC, và mã băm SHA-256 đối soát; xác minh hiển thị đúng cờ `valid_with_declared_test_exposure`.
- [x] 2.3 Hiển thị thông số cấu hình mô hình thắng cuộc (`sentence-transformers/all-MiniLM-L6-v2`), ngưỡng phân loại và cấu hình UMAP/HDBSCAN; xác minh khớp với `g1_snapshot.json`.
- [x] 2.4 Viết kiểm thử tự động cho trang Overview trong `tests/test_ui_overview.py`; xác minh render thành công các khối số liệu và bảng Gate.

## 3. Màn hình 2 — Phân tích chủ đề cố định (Fixed Topic Analytics)

- [x] 3.1 Xây dựng giao diện trang `pages/2_Fixed_Topic_Analytics.py` với bộ chọn phạm vi (Scope selector) giữa `scope:test_open` (7 Known flows) và `scope:test_closed` (10 Closed flows); xác minh chuyển đổi scope mượt mà.
- [x] 3.2 Tích hợp biểu đồ cột tương tác (Plotly / Streamlit native chart) biểu diễn tỷ lệ hội thoại (`conversation_share`) và số lượng hội thoại (`conversation_count`); xác minh công thức `conversation_share = conversation_count / eligible_conversations`.
- [x] 3.3 Xây dựng bảng chi tiết 4 đơn vị đếm (`customer_message_count`, `source_messages_with_assignment`, `segment_count`, `conversation_count`); xác minh các cột hiển thị đúng số liệu từ `topic_statistics.csv`.
- [x] 3.4 Xây dựng khối cảnh báo và giải thích các trường metadata không có sẵn trong ABCD (`unique_customers`, `time_bucket`, `channel`) hiển thị nhãn "Không có sẵn (\N)" trung thực; xác minh không tự suy diễn số liệu giả.
- [x] 3.5 Viết unit test cho trang Fixed Topic Analytics trong `tests/test_ui_fixed_topics.py`; xác minh tính đúng đắn của mẫu số khi lọc chủ đề.

## 4. Màn hình 3 — Khám phá & Thẩm định chủ đề mới (New Topic Discovery)

- [x] 4.1 Xây dựng giao diện trang `pages/3_New_Topic_Discovery.py` với bộ lọc theo Seed (42, 13, 73) và trạng thái thẩm định (`proposed`, `accepted_novel`, `monitor`); xử lý trạng thái rỗng thân thiện khi không có cụm nào khớp bộ lọc; xác minh hiển thị bảng danh sách 1.552 ứng viên từ `candidates.jsonl`.
- [x] 4.2 Xây dựng khung xem chi tiết cụm (Cluster Detail Modal/Expander) hiển thị danh sách từ khóa nổi bật (top 10 keywords), độ hỗ trợ hội thoại (`conversation_support`), và nhãn mô tả tạm thời; xác minh khớp dữ liệu ứng viên.
- [x] 4.3 Tích hợp khung hiển thị kết quả thẩm định mù từ `reviews.jsonl` gồm 5 mẫu đại diện (gần tâm centroid) + 5 mẫu ngẫu nhiên độc lập, điểm số rubric 2 trục (Coherence, Novelty) của 2 chuyên gia và quyết định Adjudication; xác minh không để lộ đáp án ground-truth.
- [x] 4.4 Xây dựng bảng hoặc đồ thị trực quan hóa quan hệ sáp nhập (Merge DAG) giữa các cụm tương đồng; xác minh đồ thị phi chu trình và kiểm tra tính hợp lệ của cụm đích.
- [x] 4.5 Viết unit test cho trang New Topic Discovery trong `tests/test_ui_discovery.py`; xác minh hiển thị đúng 10 mẫu kiểm tra và điểm rubric.

## 5. Màn hình 4 & 5 — Khám phá hội thoại & Đánh giá mô hình (Explorer & Evaluation)

- [x] 5.1 Xây dựng giao diện trang `pages/4_Conversation_Explorer.py` hỗ trợ tìm kiếm theo `conversation_id`, lọc theo chủ đề chính, tập dữ liệu (`source_split`), và trạng thái bằng chứng (`model_supported`, `human_verified`, `cluster_only`); xử lý trạng thái rỗng khi tìm kiếm không có kết quả; xác minh tìm kiếm chính xác.
- [x] 5.2 Xây dựng tính năng phân trang (Pagination) cho danh sách cuộc hội thoại (10, 25, 50 dòng/trang); xác minh chuyển trang mượt mà và không tải toàn bộ 103.901 dòng vào bộ nhớ DOM cùng lúc.
- [x] 5.3 Xây dựng khung hiển thị chi tiết câu thoại khách hàng đã che mờ PII (`masked_customer_text`), thực hiện highlight trực quan vùng bằng chứng theo đúng tọa độ `[span_start:span_end]` và màu sắc theo `evidence_status`; xác minh không lệch ký tự.
- [x] 5.4 Xây dựng giao diện trang `pages/5_Model_Evaluation.py` hiển thị các thẻ KPI đo lường cốt lõi (Closed Macro-F1, Unknown F1, Routing recall, Flow-family recovery proxy) kèm khoảng tin cậy Bootstrap 95%; xác minh số liệu khớp `metrics.json`.
- [x] 5.5 Xây dựng bảng ma trận chi tiết Flow-Family Recovery cho 2 họ chủ đề `subscription_inquiry` và `troubleshoot_site` kèm trạng thái xác thực ngữ nghĩa (`semantic_supported = True`); xác minh hiển thị đúng 2/2 họ chủ đề thu hồi.
- [x] 5.6 Xây dựng biểu đồ so sánh độ ổn định phân cụm ARI giữa 3 seed và biểu đồ độ chính xác theo nhóm độ dài lượt thoại; xác minh hiển thị đúng các giá trị ARI ~0.21 - 0.24.
- [x] 5.7 Tích hợp trình render toàn văn báo cáo Markdown từ `report.md` với tính năng tải xuống; xác minh hiển thị đầy đủ văn bản và bảng biểu.
- [x] 5.8 Viết unit test cho trang Explorer và Evaluation trong `tests/test_ui_explorer_and_eval.py`; xác minh tính chính xác của hàm highlight offset và hiển thị KPI.

## 6. Tích hợp tổng thể, Tài liệu vận hành và Kiểm toán nghiệm thu

- [x] 6.1 Xây dựng script khởi chạy dashboard `run_web_dashboard.py` tích hợp kiểm tra môi trường ảo và tự động mở trình duyệt; xác minh khởi động thành công với cổng mặc định 8501.
- [x] 6.2 Cập nhật tài liệu hướng dẫn sử dụng và vận hành Web Dashboard trong `docs/web_dashboard_guide.md` (hướng dẫn từng trang, cách lọc và xử lý sự cố); xác minh tài liệu chi tiết, dễ hiểu cho người dùng không chuyên kỹ thuật.
- [x] 6.3 Tạo file `README.md` ở thư mục gốc của repository giới thiệu tổng quan dự án, hướng dẫn chạy CLI dashboard và Web dashboard; xác minh hiển thị định dạng Markdown chuẩn.
- [x] 6.4 Chạy kiểm thử tích hợp toàn diện (E2E Test) trên tất cả các trang web và bộ lọc; xác minh 100% không phát sinh lỗi ngoại lệ hoặc rò rỉ dữ liệu PII.
- [x] 6.5 Hoàn thiện báo cáo nghiệm thu tích hợp giao diện web và trình người dùng xem xét phê duyệt; xác minh đạt đầy đủ 4 trạng thái nghiệm thu (Functional PASS, Proxy Quality PASS, Semantic HUMAN_VERIFIED, Benchmark Validity VALID).
