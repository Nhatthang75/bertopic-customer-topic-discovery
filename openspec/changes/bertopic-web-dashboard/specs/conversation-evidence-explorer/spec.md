# Spec Delta

## Purpose

Cung cấp công cụ tìm kiếm, phân trang và truy vết hội thoại khách hàng, làm nổi bật bằng chứng phân đoạn theo tọa độ ký tự chính xác và phân định trạng thái xác thực.

## ADDED Requirements

### Requirement: Tìm kiếm và lọc danh sách cuộc hội thoại
Hệ thống SHALL cho phép người dùng tìm kiếm theo mã hội thoại (conversation_id), lọc theo chủ đề chính (primary_topic), nguồn dữ liệu (train/dev/test), và trạng thái bằng chứng (model_supported, human_verified, cluster_only).

#### Scenario: Tìm kiếm theo mã hội thoại
- **WHEN** người dùng nhập một mã hội thoại hợp lệ vào ô tìm kiếm và bấm Enter
- **THEN** bảng danh sách lọc đúng cuộc hội thoại đó kèm điểm tin cậy max_score và số lượng bằng chứng.

#### Scenario: Tìm kiếm không có kết quả
- **WHEN** người dùng nhập mã hội thoại không tồn tại hoặc bộ lọc không khớp cuộc gọi nào
- **THEN** giao diện hiển thị thông báo trạng thái rỗng thân thiện Không tìm thấy cuộc hội thoại phù hợp và hướng dẫn thử lại với điều kiện khác.

### Requirement: Phân trang danh sách hội thoại
Hệ thống SHALL hỗ trợ phân trang cho danh sách cuộc hội thoại với kích thước trang tùy chọn (ví dụ 10, 25, 50 dòng mỗi trang) và bộ đếm tổng số trang, ngăn chặn hiện tượng tải chậm trình duyệt.

#### Scenario: Chuyển trang danh sách
- **WHEN** người dùng bấm nút Next hoặc chọn số trang kế tiếp
- **THEN** giao diện hiển thị tập con hội thoại tương ứng mà không làm mất các điều kiện lọc đang chọn.

### Requirement: Làm nổi bật phân đoạn bằng chứng theo offsets
Hệ thống SHALL hiển thị tuần tự các lượt chat của khách hàng và dùng hiệu ứng đánh dấu (highlight) trực quan cho các cụm từ bằng chứng dựa trên tọa độ span_start và span_end từ assignments.jsonl.

#### Scenario: Xem chi tiết bằng chứng trong cuộc gọi
- **WHEN** người dùng chọn một cuộc hội thoại để xem chi tiết
- **THEN** khung nội dung hiển thị các câu thoại với vùng bằng chứng được tô màu theo trạng thái xác thực và ghi rõ content_status.
