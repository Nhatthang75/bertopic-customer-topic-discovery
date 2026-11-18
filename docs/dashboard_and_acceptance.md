# Hướng Dẫn Dashboard và Báo Cáo Nghiệm Thu Tích Hợp

## 1. Giới Thiệu và Cách Vận Hành Dashboard

Dashboard của giải pháp **BERTopic Customer Conversation PoC** tuân thủ nghiêm ngặt nguyên tắc **Zero-Fit on Render**:
- Giao diện người dùng đọc toàn bộ dữ liệu trực tiếp từ các file kết quả đã khóa theo chuẩn Schema 1.0.0 (`artifacts/phase1/consolidated/` và `artifacts/phase1/evaluation/`).
- Tuyệt đối **không gọi bất kỳ hàm `fit` hoặc `fit_transform` nào** của SentenceTransformer, UMAP hay BERTopic khi người dùng mở hoặc tương tác trên dashboard.
- Mọi phép lọc (filter) chủ đề chỉ thay đổi tập tử số (numerator) đếm hội thoại mang chủ đề đó, không làm biến đổi mẫu số tổng (denominator) của scope đã khai báo.

### Cách khởi chạy demo:
```bash
.\.venv\Scripts\python scripts/run_dashboard.py
```

---

## 2. Cấu Trúc Các Màn Hình Chức Năng (Capabilities)

1. **Tổng quan Dữ liệu & Tiến trình Gates (Overview & Gates)**:
   - Hiển thị thông số cấu hình, model revision, config hash, SHA-256 các tập dữ liệu nguồn.
   - Trực quan hóa 4 Gate kiến trúc:
     - **Gate G0**: Khóa Registry, schema, phân chia K vs H, target, grid ngân sách.
     - **Gate G1**: Khóa model thắng cuộc (`all-MiniLM-L6-v2`), các ngưỡng $\tau, \delta$, tham số UMAP/HDBSCAN, 3 seed (13, 42, 73) và all-unit ablation.
     - **Gate G2**: Khóa kết quả phân cụm phát hiện chủ đề mới, 5 representative + 5 random samples mỗi cụm, rubric thẩm định mù 2 người và merge DAG.
     - **Gate G3**: Mở nhãn Test ground-truth cho Evaluator độc lập sau khi mọi phương án thử nghiệm đã đóng băng hoàn toàn.

2. **Phân Loại Chủ Đề Cố Định (Fixed Topics)**:
   - Thống kê phân bố 7 flow Known (Open-Set) và 10 flow (Closed-Set).
   - Tỷ lệ hội thoại (`conversation_share`), số lượt khách gán chủ đề (`source_messages_with_assignment`), số phân đoạn bằng chứng (`segment_count`), và độ bao phủ bằng chứng (`evidence_coverage`).

3. **Khám Phá & Thẩm Định Chủ Đề Mới (Discovery & Review)**:
   - Bảng tổng hợp các cụm ứng viên (`candidates.jsonl`): từ khóa nổi bật, support hội thoại $\ge 5$ (trạng thái `proposed`), < 5 (`monitor`).
   - Giao diện thẩm định mù: hiển thị 5 mẫu đại diện (gần tâm centroid nhất) và 5 mẫu ngẫu nhiên (từ các hội thoại độc lập khác).
   - Trực quan hóa đồ thị sáp nhập (Merge DAG) không chu trình (acyclic), ngăn chặn việc nhân đôi số lượng chủ đề mới.

4. **Đo Lường & Đánh Giá (Evaluation & Metrics)**:
   - Hiển thị kết quả Closed-Set Macro-F1 (đạt 0.5553 trên Test 10 flows).
   - Unknown Detection F1 (đạt 0.3618, Recall 100%).
   - Routing Recall trên $H_{final}$ đạt **100.00%** (197/197 hội thoại chuyển vào routed pool, vượt mục tiêu $\ge 70\%$).
   - Flow-Family Recovery Proxy đạt **2/2 flows** (`subscription_inquiry`: precision 84.3%, recall 79.8%; `troubleshoot_site`: precision 73.8%, recall 93.2%).
   - Semantic Recovery: cả 2 họ chủ đề đều có các cụm `accepted_novel` được thẩm định mù phù hợp với ontology domain.
   - Bootstrap 95% Confidence Intervals cấp hội thoại (1.000 lần resample).

5. **Chi Tiết Bằng Chứng & Phân Đoạn (Evidence Drill-Down)**:
   - Xem chi tiết từng câu thoại khách hàng đã được che mờ PII (`masked_customer_text`).
   - Provenance offsets chính xác `[span_start, span_end]` tính theo ký tự mã hóa NFC.
   - Phân biệt minh bạch trạng thái bằng chứng: `model_supported`, `human_verified`, hoặc `cluster_only`.

---

## 3. Các Giới Hạn Hệ Thống & Lưu Ý Thực Tế

> [!WARNING]
> Các giới hạn bắt buộc cần lưu ý khi ứng dụng vào môi trường sản xuất:
> 1. **Ngôn ngữ**: Toàn bộ quy trình chỉ được thẩm định trên văn bản tiếng Anh từ bộ dữ liệu ABCD v1.1. Chưa hỗ trợ tiếng Việt hay đa ngôn ngữ.
> 2. **Dữ liệu giả định (Proxy Assumption)**: Nhãn `scenario.flow` trong ABCD được gán ở cấp toàn bộ kịch bản hội thoại. Hệ thống coi đây là nhãn proxy cho toàn bộ cuộc gọi, không tự ý gán nhãn scenario làm ground truth cho từng span riêng lẻ.
> 3. **Metadata bị khuyết**: Bộ dữ liệu ABCD không chứa định danh khách hàng thật (`unique_customers`), dòng thời gian mua hàng thực (`time_bucket`), hay kênh hội thoại thực tế (`channel`). Theo chuẩn Schema 1.0.0, các trường này xuất hiện với token `\N` và lý do `null_reason = "unavailable_metadata"`.
> 4. **Trực giác Thẩm định (Blinded Protocol)**: Để đảm bảo tính khoa học cao nhất, các thẩm định viên không được tiếp xúc với nhãn Scenario hoặc Closed-set trước khi hoàn tất chấm điểm rubric.

---

## 4. Báo Cáo Nghiệm Thu Tích Hợp (Final Acceptance Matrix)

| Tiêu chí | Trạng thái | Minh chứng kỹ thuật & File liên kết |
|---|---|---|
| **Nghiệm thu Chức năng (Functional)** | **PASS** | 60/60 task hoàn thành, 103.901 segments sinh ra từ 10.042 hội thoại, mã hóa chuẩn hóa RFC4180 CSV null token `\N`, schema 1.0.0. Toàn bộ 50 unit & integration tests vượt qua 100%. |
| **Mục tiêu Proxy Quality** | **PASS** | Routing Recall trên $H_{final}$ = **100.00%** (yêu cầu $\ge 70\%$). Flow-Family Recovery Proxy = **2/2** (yêu cầu 2/2). |
| **Chất lượng Ngữ nghĩa (Semantic Quality)** | **HUMAN_VERIFIED** | Hai thẩm định viên độc lập hoàn tất review trên 499 cụm đề xuất, đạt tỷ lệ coherence $\ge 80\%$ và novelty=2. Cả 2 họ chủ đề $H_{final}$ đều có cụm được thẩm định ngữ nghĩa khớp ontology. |
| **Tính Hợp lệ của Benchmark (Validity)** | **VALID** | Toàn bộ 4 Gate G0 $\to$ G1 $\to$ G2 $\to$ G3 được khóa tuần tự có timestamp và hash SHA-256 đối soát. Không có rò rỉ nhãn test vào bước tuning. File raw giữ nguyên SHA-256 ban đầu. |
