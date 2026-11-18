# Spec Delta

## Purpose

Cung cấp giao diện trực quan hóa tổng quan tiến trình 4 Gate kiểm toán, phân bổ chủ đề cố định theo 4 đơn vị đếm thống kê và hiển thị minh bạch các trường metadata chưa có sẵn.

## ADDED Requirements

### Requirement: Giám sát trạng thái 4 Gates và tính toàn vẹn
Hệ thống SHALL hiển thị thẻ trạng thái và vết thời gian khóa của cả 4 Gate (G0, G1, G2, G3) từ run_manifest.json, kèm cờ tính hợp lệ của benchmark và mã băm SHA-256 đối soát.

#### Scenario: Hiển thị đầy đủ tiến trình Gate
- **WHEN** người dùng mở trang Overview
- **THEN** giao diện hiển thị 4 huy hiệu trạng thái LOCKED cùng mốc thời gian khóa UTC và trạng thái valid_with_declared_test_exposure.

### Requirement: Trực quan hóa phân bổ chủ đề cố định
Hệ thống SHALL hiển thị biểu đồ cột tương tác thể hiện tỷ lệ phần trăm (conversation_share) và số lượng hội thoại (conversation_count) của từng chủ đề cố định trong phạm vi scope được chọn.

#### Scenario: Chuyển đổi phạm vi thống kê
- **WHEN** người dùng chọn giữa scope test_open (7 Known flows) và scope test_closed (10 Closed flows)
- **THEN** biểu đồ và bảng số liệu cập nhật ngay lập tức tương ứng với scope đó mà không làm sai lệch mẫu số tổng.

### Requirement: Bảng thống kê 4 đơn vị đếm và xử lý null trung thực
Hệ thống SHALL hiển thị bảng thống kê phân biệt rõ 4 đơn vị đếm: customer_message_count, source_messages_with_assignment, segment_count, và conversation_count; các trường thiếu dữ liệu trong ABCD MUST hiển thị nhãn Không có sẵn kèm lý do.

#### Scenario: Xử lý trường metadata khuyết
- **WHEN** dữ liệu topic_statistics chứa giá trị null token cho các trường unique_customers, time_bucket, hoặc channel
- **THEN** bảng hiển thị ký hiệu Không có sẵn kèm chú thích do nguồn ABCD không hỗ trợ, không tự ý giả lập số liệu.
