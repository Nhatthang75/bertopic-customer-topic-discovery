# Proposal: Giao Diện Web Dashboard Tương Tác Cho BERTopic Customer Conversation PoC

## Why

Giai đoạn PoC cốt lõi của giải pháp BERTopic (`bertopic-customer-conversation-poc`) đã hoàn thành thành công 60/60 nhiệm vụ, đáp ứng đầy đủ các tiêu chuẩn kiến trúc nghiêm ngặt (G0–G3), đạt độ phủ định tuyến 100% và thu hồi 2/2 họ chủ đề mới giấu kín. Tuy nhiên, toàn bộ dữ liệu kết quả hiện tại mới chỉ xuất hiện dưới dạng các file dữ liệu cấu trúc Schema 1.0.0 (`assignments.jsonl`, `candidates.jsonl`, `reviews.jsonl`, `conversation_topics.csv`, `topic_statistics.csv`, `metrics.json`, `report.md`) và một script dòng lệnh CLI (`scripts/run_dashboard.py`) in văn bản thuần túy ra Terminal. 

Để các bên liên quan, chuyên gia phân tích nghiệp vụ (business analysts) và nhà quản lý chăm sóc khách hàng có thể trực tiếp trải nghiệm, kiểm tra bằng chứng, tương tác với các biểu đồ phân tích và nghiệm thu PoC một cách trực quan, dự án cần một Web Dashboard tương tác trên trình duyệt được phát triển bằng Streamlit, vận hành theo nguyên tắc tối thượng **Zero-Fit on Render** (chỉ đọc dữ liệu tĩnh đã khóa, không chạy lại bất kỳ mô hình nào khi xem).

## What Changes

- Xây dựng ứng dụng Web Dashboard đa trang (Multi-page Web Application) sử dụng **Streamlit** kết nối trực tiếp với kho artifacts Schema 1.0.0 tại `artifacts/phase1/`.
- Cung cấp 5 trang chuyên biệt:
  1. **Overview (Tổng quan & Vòng đời Thử nghiệm)**: Giám sát 4 Gate (G0–G3), chất lượng dữ liệu nguồn, thông số mô hình thắng cuộc và tóm tắt tiến độ.
  2. **Fixed Topic Analytics (Phân tích Chủ đề Cố định)**: Trực quan hóa phân bổ 10 flow cố định, bảng 4 đơn vị đếm (`message`, `segment`, `mention`, `conversation`) cho từng scope (`test_open`, `test_closed`), minh bạch các trường metadata khuyết (`\N`).
  3. **New Topic Discovery (Khám phá & Thẩm định Chủ đề Mới)**: Lọc và duyệt 1.552 ứng viên qua 3 seed (13, 42, 73); xem chi tiết thẩm định mù với 5 mẫu đại diện (gần tâm centroid) + 5 mẫu ngẫu nhiên độc lập; trực quan hóa đồ thị sáp nhập (Merge DAG).
  4. **Conversation Explorer (Khám phá Hội thoại & Bằng chứng Phân đoạn)**: Tìm kiếm hội thoại, phân trang linh hoạt; hiển thị hội thoại che mờ PII (`masked_customer_text`); highlight chuẩn xác phân đoạn bằng chứng theo provenance offsets `[span_start, span_end]`; phân biệt `model_supported`, `human_verified`, `cluster_only`.
  5. **Model Evaluation (Đo lường Hiệu năng & Kiểm toán Benchmark)**: Hiển thị các KPI cốt lõi (Closed Macro-F1, Unknown F1, Routing recall, Flow-family recovery proxy, Semantic recovery, Stability ARI qua 3 seed, độ chính xác theo độ dài lượt hội thoại) và tích hợp trình đọc báo cáo Markdown đầy đủ.
- Tuân thủ nghiêm ngặt nguyên tắc Zero-Fit on Render: Không import hay gọi bất kỳ hàm huấn luyện (`fit`/`fit_transform`), không tính toán embedding mới khi mở trang.
- Đảm bảo an toàn PII và tính toàn vẹn: Không giải mã ngược PII, không tự suy diễn hay làm sai lệch mẫu số khi người dùng lọc chủ đề.

## Capabilities

### New Capabilities
- `web-dashboard-core`: Quản lý nền tảng ứng dụng Streamlit đa trang, cơ chế nạp dữ liệu Zero-Fit on Render, tối ưu bộ nhớ đệm (caching), quản lý session state và bảo vệ an toàn PII.
- `topic-analytics-view`: Trực quan hóa tổng quan tiến trình 4 Gates, biểu đồ phân bổ chủ đề cố định, bảng 4 đơn vị đếm thống kê và hiển thị trung thực các trường metadata không có sẵn (`\N`).
- `new-topic-discovery-view`: Giao diện duyệt cụm chủ đề mới phát hiện, bộ lọc theo seed và trạng thái thẩm định, modal xem chi tiết 10 mẫu kiểm tra mù (5 đại diện + 5 ngẫu nhiên) và đồ thị Merge DAG.
- `conversation-evidence-explorer`: Trình tìm kiếm, phân trang và khám phá câu thoại khách hàng, highlight bằng chứng phân đoạn theo provenance offsets `[span_start, span_end]` và phân định trạng thái bằng chứng.
- `benchmark-evaluation-view`: Trực quan hóa bảng điều khiển đo lường hiệu năng kỹ thuật, ma trận thu hồi họ chủ đề ẩn (Flow-Family Recovery), đánh giá semantic recovery, độ ổn định phân cụm và trình xem báo cáo tổng kết.

### Modified Capabilities
<!-- Không có capability hiện có nào bị thay đổi yêu cầu; toàn bộ backend artifacts và pipeline hiện tại được giữ nguyên bất biến. -->

## Impact

- **Mã nguồn ứng dụng**: Bổ sung thư mục ứng dụng Streamlit (ví dụ `app/` hoặc `bertopic_poc/ui/`) và script khởi chạy dashboard trên nền web.
- **Phụ thuộc (Dependencies)**: Sử dụng gói `streamlit` đã có hoặc cài đặt trong môi trường ảo `.venv` phục vụ render giao diện, không ảnh hưởng đến các thư viện lõi (`sentence-transformers`, `bertopic`, `scikit-learn`).
- **Dữ liệu & Artifacts**: Đọc trực tiếp (read-only) từ `artifacts/phase1/consolidated/`, `artifacts/phase1/evaluation/` và `data/raw/ontology.json`. Tuyệt đối không ghi đè, xóa hoặc sửa đổi bất kỳ artifact nào đã được kiểm toán và ký băm SHA-256.
- **Hệ thống hiện tại**: Hoàn toàn tương thích ngược; script CLI `scripts/run_dashboard.py` và toàn bộ 54 bài test hiện có tiếp tục hoạt động độc lập và bảo toàn kết quả.
