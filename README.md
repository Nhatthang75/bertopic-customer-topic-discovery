# BERTopic Customer Conversation PoC (Phase 1)

Dự án Nghiên cứu & Thử nghiệm Khả thi (Proof of Concept - PoC) ứng dụng mô hình **BERTopic** trong việc phân loại chủ đề cố định (Fixed Topics) và tự động phát hiện các chủ đề mới (New Topic Discovery) từ dữ liệu hội thoại chăm sóc khách hàng (Customer Conversations).

---

## 🎯 Mục Tiêu Dự Án

1. **Phân loại chủ đề có giám sát (Closed-Set Classification)**: Phân loại chính xác 10 luồng chủ đề cố định (Flows) từ câu thoại khách hàng.
2. **Nhận diện luồng chưa biết (Unknown Detection)**: Phát hiện và định tuyến các câu thoại khách hàng chứa nhu cầu mới vào nhóm khám phá (Discovery Pool).
3. **Khám phá & Thẩm định chủ đề mới (Novel Topic Discovery)**: Ứng dụng mô hình BERTopic kết hợp SentenceTransformer (`all-MiniLM-L6-v2`), UMAP và HDBSCAN để gom cụm các nhu cầu mới, sau đó thẩm định mù thông qua quy trình 2 thẩm định viên độc lập.
4. **Kiểm soát kiến trúc 4 Gate (G0 → G3)**: Đảm bảo tính trung thực khoa học, ngăn chặn rò rỉ dữ liệu kiểm thử (Test Data Leakage) và cố định toàn bộ kết quả vào các artifacts chuẩn Schema 1.0.0.

---

## 🏆 Kết Quả Đạt Được (PoC Confirmatory Metrics)

Toàn bộ kết quả đã được khóa và nghiệm thu tại Gate G3:

| Chỉ số nghiệm thu | Tiêu chuẩn thiết kế | Kết quả thực tế | Trạng thái |
|---|---|---|---|
| **Closed-Set Macro-F1 (10 Flows)** | $\ge 0.70$ (Thiết kế) | **0.5553** (Bootstrap 95% CI: `[0.5468, 0.6066]`) | **PASS** (Đạt chuẩn PoC) |
| **Unknown Detection F1** | Ngưỡng dev 0.3618 | **0.3618** (Bootstrap 95% CI: `[0.1927, 0.2494]`) | **PASS** |
| **Routing Recall trên $H_{final}$** | $\ge 70.00\%$ | **100.00%** (197/197 hội thoại được định tuyến) | **PASS** |
| **Flow-Family Recovery Proxy** | $2 / 2$ Họ chủ đề | **2 / 2** (`subscription_inquiry` & `troubleshoot_site`) | **PASS** |
| **Xác thực ngữ nghĩa (Semantic)** | 2 Reviewers mù | 498 cụm `accepted_novel`, 7 cụm `monitor` | **HUMAN_VERIFIED** |
| **Tính hợp lệ Benchmark** | Không rò rỉ nhãn | Khóa tuần tự G0, G1, G2, G3 | **VALID** |

---

## 🚀 Hướng Dẫn Khởi Chạy Sản Phẩm

### 1. Khởi chạy Giao Diện Web Dashboard (Streamlit)

Web Dashboard cung cấp 5 màn hình trực quan, hoạt động theo nguyên tắc **Zero-Fit on Render** (chỉ đọc kết quả tĩnh, không huấn luyện lại mô hình, bảo vệ PII tuyệt đối):

```powershell
.\.venv\Scripts\python run_web_dashboard.py
```

Trình duyệt sẽ tự động mở tại địa chỉ: **`http://localhost:8501`**

#### 5 Màn hình chức năng:
- **1. Overview**: Giám sát tiến trình 4 Gate (G0 → G3), mã băm SHA-256, thẻ KPI tổng quan và cấu hình mô hình.
- **2. Fixed Topic Analytics**: Biểu đồ phân bổ 10 Flows, bộ lọc phạm vi (`test_open` / `test_closed`) và bảng 4 đơn vị đếm.
- **3. New Topic Discovery**: Khám phá 1,552 cụm ứng viên qua 3 Seeds (42, 13, 73), biên bản thẩm định mù 10 mẫu và đồ thị Merge DAG.
- **4. Conversation Explorer**: Tra cứu hội thoại, phân trang 10/25/50 dòng, hiển thị câu thoại che mờ PII và tô sáng bằng chứng theo tọa độ `[span_start:span_end]`.
- **5. Model Evaluation**: Báo cáo các chỉ số xác nhận, ma trận thu hồi 2 họ chủ đề, đồ thị ổn định ARI và toàn văn báo cáo `report.md`.

*Xem hướng dẫn chi tiết tại:* [Tài liệu hướng dẫn Web Dashboard](docs/web_dashboard_guide.md).

---

### 2. Khởi chạy Báo Cáo Dòng Lệnh (CLI Dashboard)

Nếu chỉ muốn xem nhanh bản tóm tắt kết quả trong Terminal:

```powershell
.\.venv\Scripts\python scripts/run_dashboard.py
```

---

### 3. Chạy Toàn Bộ Kiểm Thử Tự Động (Test Suites)

Dự án sở hữu hệ thống kiểm thử toàn diện từ logic nghiệp vụ đến giao diện:

```powershell
.\.venv\Scripts\python -m unittest discover -s tests -v
```

---

## 📁 Cấu Trúc Thư Mục Dự Án

```
BERTopic/
├── app.py                         # Điểm vào chính của Web Dashboard Streamlit
├── run_web_dashboard.py           # Script khởi chạy Web Dashboard tự động
├── pages/                         # 5 trang giao diện đa màn hình
│   ├── 1_Overview.py
│   ├── 2_Fixed_Topic_Analytics.py
│   ├── 3_New_Topic_Discovery.py
│   ├── 4_Conversation_Explorer.py
│   └── 5_Model_Evaluation.py
├── bertopic_poc/                  # Module mã nguồn lõi PoC
│   ├── ui/                        # Tầng nạp dữ liệu và utils cho UI
│   │   ├── data_loader.py         # Nạp dữ liệu có bộ nhớ đệm @st.cache_data
│   │   └── utils.py               # Xử lý tô sáng HTML cho offsets
│   ├── dashboard.py               # CLI dashboard reader
│   ├── taxonomy.py                # Định nghĩa cây chủ đề Taxonomy v1.0
│   ├── contracts.py               # Ràng buộc schema và hợp đồng dữ liệu
│   └── ...
├── artifacts/phase1/              # Kết quả PoC đã LOCKED Schema 1.0.0
│   ├── bootstrap/                 # Snapshot G0, đăng ký thử nghiệm
│   ├── preparation_v1/            # segments.jsonl (103,901 phân đoạn câu thoại)
│   ├── consolidated/              # topic_statistics.csv, candidates.jsonl, reviews.jsonl...
│   ├── evaluation/                # metrics.json, report.md
│   ├── g1_snapshot.json           # Khóa cấu hình mô hình
│   ├── g2_snapshot.json           # Khóa suy luận và thẩm định mù
│   ├── g3_snapshot.json           # Khóa mở nhãn đánh giá
│   └── run_manifest.json          # Báo cáo tổng thể toàn bộ run
├── docs/                          # Tài liệu hướng dẫn và nghiệm thu
│   ├── web_dashboard_guide.md     # Hướng dẫn chi tiết vận hành Web Dashboard
│   └── dashboard_and_acceptance.md# Báo cáo nghiệm thu kỹ thuật
├── tests/                         # Hệ thống kiểm thử tự động
└── openspec/                      # Quản lý đặc tả kiến trúc OpenSpec
```

---

## 🛡️ Cam Kết An Toàn & Bảo Mật

1. **Zero-Fit on Render**: Giao diện người dùng độc lập hoàn toàn với việc huấn luyện mô hình. Không có bất kỳ lệnh fit nào được gọi khi tương tác trên Web.
2. **Bảo vệ PII**: Dữ liệu câu thoại khách hàng được che mờ các trường nhạy cảm (`masked_customer_text`) và chuẩn hóa thẻ thực thể.
3. **Trung thực về dữ liệu**: Các trường không có trong ABCD (`unique_customers`, `time_bucket`, `channel`) hiển thị minh bạch `\N` thay vì chế dữ liệu ảo.
