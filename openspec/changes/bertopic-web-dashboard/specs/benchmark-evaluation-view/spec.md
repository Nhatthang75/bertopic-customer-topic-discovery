# Spec Delta

## Purpose

Cung cấp giao diện đo lường hiệu năng kỹ thuật của mô hình, hiển thị ma trận thu hồi họ chủ đề mới, so sánh độ ổn định giữa các seed và tích hợp trình xem báo cáo Markdown.

## ADDED Requirements

### Requirement: Thẻ chỉ số hiệu năng kỹ thuật cốt lõi
Hệ thống SHALL hiển thị các thẻ KPI đo lường từ metrics.json: Closed-Set Macro-F1 kèm Bootstrap 95% CI, Unknown Detection F1 kèm Bootstrap 95% CI, Routing Recall trên H_final, và số họ chủ đề thu hồi thành công.

#### Scenario: Xem các chỉ số KPI kiểm thử
- **WHEN** người dùng mở trang Model Evaluation
- **THEN** các thẻ KPI hiển thị đầy đủ giá trị đo lường, khoảng tin cậy 95%, kích thước mẫu kiểm thử, và nhãn đánh giá đạt mục tiêu.

### Requirement: Ma trận thu hồi họ chủ đề mới chi tiết
Hệ thống SHALL hiển thị bảng chi tiết Flow-Family Recovery cho từng họ chủ đề ẩn trong H_final gồm số cụm đạt chuẩn, độ chính xác họ (family_precision), độ bao phủ họ (family_recall), và trạng thái thu hồi ngữ nghĩa.

#### Scenario: Đối chiếu kết quả thu hồi 2 họ chủ đề
- **WHEN** người dùng xem bảng ma trận Flow-Family Recovery
- **THEN** giao diện hiển thị thông số chi tiết cho cả hai họ subscription_inquiry và troubleshoot_site với trạng thái recovered.

### Requirement: Đo lường độ ổn định phân cụm và độ dài hội thoại
Hệ thống SHALL trực quan hóa chỉ số tương đồng Adjusted Rand Index (ARI) giữa các seed (Seed 42 vs 13, Seed 42 vs 73) kèm tỷ lệ bao phủ chia sẻ, và bảng độ chính xác theo các nhóm độ dài lượt chat.

#### Scenario: Phân tích độ ổn định thuật toán
- **WHEN** người dùng chuyển sang tab Stability & Diagnostics
- **THEN** hệ thống hiển thị bảng so sánh ARI giữa 3 seed ngẫu nhiên và biểu đồ tỷ lệ chính xác theo 3 nhóm độ dài lượt thoại.

### Requirement: Tích hợp trình xem báo cáo tổng kết toàn văn
Hệ thống SHALL hiển thị trực tiếp toàn bộ nội dung báo cáo nghiệm thu từ report.md dưới dạng giao diện Markdown có định dạng rõ ràng, cho phép người dùng đọc và tải về mà không cần mở file ngoài.

#### Scenario: Đọc báo cáo toàn diện
- **WHEN** người dùng cuộn đến phần Báo cáo Nghiệm thu Tổng kết
- **THEN** toàn bộ nội dung report.md được render đầy đủ với các bảng biểu và đề mục tiêu chuẩn.
