# Hướng Dẫn Sử Dụng & Vận Hành Web Dashboard (BERTopic PoC)

Tài liệu này hướng dẫn người dùng cuối và các bên liên quan cách khởi chạy, sử dụng và khai thác toàn bộ tính năng của giao diện Web Dashboard cho dự án **BERTopic Customer Conversation PoC**.

---

## 1. Hướng Dẫn Khởi Chạy Nhanh (Quick Start)

### 1.1. Khởi chạy bằng script tự động (Khuyến nghị)
Mở cửa sổ dòng lệnh (Terminal / PowerShell) tại thư mục gốc của dự án và chạy:

```powershell
.\.venv\Scripts\python run_web_dashboard.py
```

- Hệ thống sẽ tự động kiểm tra môi trường ảo `.venv`, xác nhận tính toàn vẹn của các file kết quả (artifacts) và khởi chạy Streamlit tại địa chỉ:
  👉 **`http://localhost:8501`**
- Trình duyệt web mặc định của bạn sẽ tự động mở trang chủ của ứng dụng.

### 1.2. Khởi chạy trực tiếp qua Streamlit
Nếu muốn tùy chỉnh cổng hoặc tham số nâng cao:

```powershell
.\.venv\Scripts\streamlit run app.py --server.port 8501
```

---

## 2. Giới Thiệu Chi Tiết 5 Màn Hình Trực Quan

Ứng dụng được thiết kế dạng đa trang (Multi-page App). Bạn có thể dễ dàng chuyển đổi qua thanh menu điều hướng ở góc trên bên trái:

```
[🧭 Menu Điều Hướng]
├── 1_Overview
├── 2_Fixed_Topic_Analytics
├── 3_New_Topic_Discovery
├── 4_Conversation_Explorer
└── 5_Model_Evaluation
```

---

### Màn Hình 1: 📊 Overview & Giám Sát Tiến Trình Gates (`1_Overview.py`)

- **Mục đích**: Cung cấp bức tranh toàn cảnh về quy mô dữ liệu, trạng thái bất biến của 4 Gate kiến trúc và cấu hình mô hình AI.
- **Thành phần chính**:
  1. **Thẻ KPI tổng quan**:
     - *Tổng cuộc hội thoại*: 10,042 cuộc hội thoại ABCD v1.1 hợp lệ.
     - *Tổng số phân đoạn*: 103,901 phân đoạn câu thoại (bao gồm 80,112 câu nêu nhu cầu khách hàng).
     - *Số chủ đề cố định*: 10 Closed Flows.
     - *Số ứng viên phát hiện*: 1,552 cụm chủ đề mới.
  2. **Tiến trình kiểm soát 4 Gate (G0 → G3)**:
     - Hiển thị huy hiệu **LOCKED** xanh lá cho tất cả các Gate.
     - Vết thời gian khóa UTC và mã băm SHA-256 đối soát chống can thiệp.
  3. **Cấu hình mô hình thắng cuộc**:
     - Model ID: `sentence-transformers/all-MiniLM-L6-v2`.
     - Ngưỡng phân loại: $\tau = 0.20, \delta = 0.05$ (Parent) và $\tau_{child} = 0.50, \delta_{child} = 0.10$ (Child).
     - Siêu tham số UMAP & HDBSCAN (`min_cluster_size = 5`).
  4. **Chất lượng dữ liệu**: Bảng thống kê phân phối câu thoại và giải thích khả dụng metadata.

---

### Màn Hình 2: 📈 Phân Tích Chủ Đề Cố Định (`2_Fixed_Topic_Analytics.py`)

- **Mục đích**: Khám phá mức độ phân bổ của 10 chủ đề phân loại có giám sát theo 4 đơn vị đếm chuẩn Schema 1.0.0.
- **Thao tác & Bộ lọc**:
  - **Bộ chọn phạm vi (Scope Selector)**: Chuyển đổi giữa `scope:test_open` (7 Known flows, mẫu số N=898) và `scope:test_closed` (10 Closed flows, mẫu số N=1,004).
  - **Chế độ hiển thị biểu đồ**: Chọn xem theo **Tỷ lệ hội thoại (%)** hoặc **Số lượng hội thoại (N)**.
- **Bảng 4 đơn vị đếm thống kê**:
  - `Câu Khách Hàng (customer_message_count)`
  - `Lượt Thoại Gán Nhãn (source_messages_with_assignment)`
  - `Số Phân Đoạn (segment_count)`
  - `Số Hội Thoại (conversation_count)`
- **Lưu ý minh bạch dữ liệu**: Các trường `unique_customers`, `time_bucket`, `channel` hiển thị nhãn `\N` (Không có sẵn) đúng chuẩn RFC4180 vì bộ dữ liệu ABCD không chứa các trường này; hệ thống cam kết **không tự tạo số liệu ảo**.

---

### Màn Hình 3: 🔍 Khám Phá & Thẩm Định Chủ Đề Mới (`3_New_Topic_Discovery.py`)

- **Mục đích**: Trực quan hóa 1,552 cụm chủ đề mới được phát hiện tự động bằng thuật toán phân cụm BERTopic qua 3 random seeds.
- **Thao tác & Bộ lọc**:
  - **Lọc theo Random Seed**: Seed 42 (primary), Seed 13, Seed 73.
  - **Lọc theo Trạng thái**: `accepted_novel` (Đã nghiệm thu), `monitor` (Theo dõi), `proposed` (Chờ thẩm định).
  - **Tìm kiếm từ khóa**: Nhập từ khóa muốn tra cứu (ví dụ: `refund`, `payment`, `order`).
- **Khung xem chi tiết & Thẩm định mù (Blinded Review)**:
  - Chọn một mã cụm để xem Top 10 từ khóa c-TF-IDF và độ hỗ trợ hội thoại.
  - Xem biên bản thẩm định mù gồm **10 mẫu kiểm tra** (5 mẫu gần tâm centroid + 5 mẫu ngẫu nhiên độc lập) kèm điểm số rubric 2 trục (Mạch lạc - Coherence & Tính mới - Novelty) của 2 chuyên gia độc lập.
  - Đồ thị sáp nhập cụm (Merge DAG) chứng minh tính phi chu trình (0 Cycles).

---

### Màn Hình 4: 💬 Khám Phá Hội Thoại & Truy Vết Bằng Chứng (`4_Conversation_Explorer.py`)

- **Mục đích**: Cho phép chuyên viên tra cứu chi tiết từng cuộc hội thoại, kiểm tra câu thoại đã được che mờ PII và trực quan hóa vùng bằng chứng trích xuất.
- **Thao tác & Tìm kiếm**:
  - **Tìm kiếm theo ID**: Nhập mã cuộc hội thoại (ví dụ: `f4fd3222b6a01a7825d97613`).
  - **Lọc theo chủ đề & Trạng thái bằng chứng**: `human_verified`, `model_supported`, `cluster_only`.
  - **Phân trang mượt mà**: Tùy chọn 10, 25 hoặc 50 dòng/trang giúp tải nhanh và tiết kiệm bộ nhớ RAM.
- **Trực quan hóa bằng chứng (Offset Highlights)**:
  - Từng câu thoại khách hàng được hiển thị với văn bản đã ẩn danh (`masked_customer_text`).
  - Vùng văn bản làm bằng chứng được tô sáng chính xác theo tọa độ ký tự `[span_start:span_end]`.
  - Thẻ màu sắc tương ứng: Xanh lá (`human_verified`), Vàng (`model_supported`), Xám (`cluster_only`).

---

### Màn Hình 5: 🎯 Đánh Giá Mô Hình & Nghiệm Thu Khoa Học (`5_Model_Evaluation.py`)

- **Mục đích**: Báo cáo toàn diện kết quả đo lường xác nhận trên tập kiểm thử nhằm phục vụ nghiệm thu dự án.
- **Các chỉ số chính**:
  - **Closed-Set Macro-F1**: `0.5553` (Khoảng tin cậy Bootstrap 95%: `[0.5468, 0.6066]`).
  - **Unknown Detection F1**: `0.3618` (Khoảng tin cậy Bootstrap 95%: `[0.1927, 0.2494]`).
  - **Routing Recall trên $H_{final}$**: `100.00%` (Đạt vượt mức mục tiêu $\ge 70\%$).
  - **Flow-Family Recovery Proxy**: `2 / 2 Họ chủ đề` thu hồi thành công (`subscription_inquiry` & `troubleshoot_site`).
- **Biểu đồ chẩn đoán**:
  - Độ ổn định phân cụm ARI giữa 3 random seeds (~0.21 - 0.24, Shared coverage > 86%).
  - Độ chính xác phân loại theo độ dài cuộc hội thoại (Ngắn: 50.0%, Trung bình: 43.3%, Dài: 45.6%).
- **Xem và tải báo cáo**: Tích hợp nút tải xuống toàn văn tệp `report.md`.

---

## 3. Hướng Dẫn Xử Lý Sự Cố Thường Gặp (Troubleshooting)

| Tình huống | Nguyên nhân | Cách khắc phục |
|---|---|---|
| **Cổng 8501 đang bị chiếm dụng** | Một tiến trình Streamlit khác đang chạy trên cổng 8501. | Chạy với cổng khác: `.\.venv\Scripts\python run_web_dashboard.py --port 8502` |
| **Báo lỗi thiếu file artifact** | Thư mục `artifacts/phase1/` chưa đầy đủ. | Kiểm tra lại kết quả chạy pipeline PoC hoặc cấu hình biến môi trường `BERTOPIC_ARTIFACTS_ROOT`. |
| **Trình duyệt không tự động mở** | Trình duyệt bị chặn mở cửa sổ mới từ dòng lệnh. | Mở trình duyệt thủ công và truy cập `http://localhost:8501`. |
| **Bộ nhớ tải trang lớn** | Đang tải nhiều phân đoạn hội thoại cùng lúc. | Giảm số dòng hiển thị tại bộ lọc phân trang (chọn 10 dòng/trang). |

---

## 4. Cam Kết An Toàn & Bảo Mật

1. **Zero-Fit on Render**: Giao diện chỉ đọc các kết quả đã được tính toán sẵn từ các tệp artifact. Tuyệt đối không gọi mô hình AI hay huấn luyện lại dữ liệu khi người dùng bấm nút trên web.
2. **Bảo vệ quyền riêng tư (PII Protection)**: Toàn bộ thông tin cá nhân khách hàng (tên, tài khoản, số điện thoại) đã được che mờ và ẩn danh hóa trước khi hiển thị.
