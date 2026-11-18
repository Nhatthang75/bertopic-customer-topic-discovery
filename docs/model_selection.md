# Hướng dẫn Tìm kiếm Mô hình, Ngưỡng Tương đồng và Baseline (Group 5)

Tài liệu này quy định quy trình tìm kiếm mô hình phân loại, tối ưu hóa ngưỡng tương đồng ($\tau, \delta$), xây dựng baseline và hiệu chuẩn ngưỡng theo thiết kế đã đăng ký.

## 1. Ứng viên Mô hình và Ngân sách Thực thi

- **Mô hình đăng ký tại G0**:
  1. `sentence-transformers/all-MiniLM-L6-v2` (revision: `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`)
  2. `sentence-transformers/all-mpnet-base-v2` (revision: `e8c3b32edf5434bc2275fc9bab85f82640a19130`)
- **Ngân sách thực thi**:
  - Tối đa 4 CPU threads, RAM tiến trình $\le 8$ GiB.
  - Batch size mặc định 32 (giảm xuống 8 nếu gặp Out Of Memory).
  - Smoke test: Tối đa 200 cuộc hội thoại Train K (chọn theo hash seed 42), thời gian $\le 10$ phút/mô hình.
  - Tuyệt đối không mở tập Test hoặc $H_{final}$ trong quá trình tìm kiếm mô hình.

## 2. Lưới Tìm kiếm Ngưỡng Cha (Parent Grid 52 Cấu hình)

- **Tham số $\tau$ (Similarity Threshold)**:
  - Giá trị từ $0,20$ đến $0,80$ với bước nhảy $0,05$ (13 giá trị: $0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80$).
- **Tham số $\delta$ (Margin Threshold)**:
  - 4 giá trị: $0, 0.05, 0.10, 0.15$.
  - Tổng số cấu hình: $13 \times 4 = 52$ tổ hợp mỗi mô hình.

## 3. Tiêu chí Chọn Cấu hình và Quy tắc Xử lý Hòa điểm (Tie-breaking)

1. **Mục tiêu chính**:
   - Lọc các cấu hình đạt ràng buộc phát hiện unknown trên tập dev: $\text{Unknown F1} \ge 0,60$.
   - Trong các cấu hình đạt ràng buộc, chọn cấu hình có **Known Macro-F1 lớn nhất**.
2. **Quy tắc Fallback khi không đạt ràng buộc**:
   - Nếu không có cấu hình nào đạt $\text{Unknown F1} \ge 0,60$, chọn cấu hình có **Trung bình điều hòa (Harmonic Mean)** giữa Known Macro-F1 và Unknown F1 cao nhất:
     $$\text{Harmonic Mean} = \frac{2 \times \text{Macro-F1} \times \text{Unknown-F1}}{\text{Macro-F1} + \text{Unknown-F1}}$$
   - Đánh dấu trạng thái `dev_constraint_failed = True`. Giữ nguyên mục tiêu nghiệm thu test, tuyệt đối không tự ý sửa ngưỡng hoặc mở rộng lưới ngoài ngân sách.
3. **Thứ tự phá vỡ hòa điểm (Tie-break)**:
   1. Unknown F1 cao hơn.
   2. Thứ tự ưu tiên mô hình tại G0 (`all-MiniLM-L6-v2` trước).
   3. $\tau$ nhỏ hơn.
   4. $\delta$ nhỏ hơn.

## 4. Ngưỡng Phân lớp Con (Child Threshold)

- Áp dụng cùng lưới 52 cấu hình $(\tau_{child}, \delta_{child})$ chung cho tất cả các subflow dưới flow cha đã được chấp nhận (`accepted`).
- Đánh giá end-to-end trên tập Dev K có nhãn canonical child.
- Nếu thiếu dữ liệu hiệu chuẩn cho subflow, áp dụng cấu hình dự phòng mặc định: $\tau_{child} = 0,50, \delta_{child} = 0,10$ với `calibration_state = "fallback"`.

## 5. Mô hình Baseline TF-IDF + Logistic Regression

- Fit từ vựng (Vocabulary / IDF) và mô hình Logistic Regression ($C \in \{0.1, 1.0, 10.0\}$, $L2$ penalty) duy nhất trên tập Train K (nối các lượt nói khách hàng analyzable ở cấp cuộc hội thoại).
- Điểm từ chối (Rejection Score):
  $$\text{Rejection Score} = 1.0 - \max(\text{predict\_proba})$$
- Tìm kiếm ngưỡng $q \in \{0.35, 0.50, 0.65, 0.80, 0.95\}$ trên Dev K + $H_{dev}$ (15 tổ hợp $(C, q)$).
- Nếu $\max(\text{predict\_proba}) < q \rightarrow$ từ chối dự đoán (`abstain`), gắn cờ `residual_flag = True` (dự đoán Unknown).
