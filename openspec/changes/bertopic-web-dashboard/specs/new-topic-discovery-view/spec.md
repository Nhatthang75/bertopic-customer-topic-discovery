# Spec Delta

## Purpose

Cung cấp giao diện khám phá các cụm chủ đề mới phát hiện, hỗ trợ lọc theo seed và trạng thái thẩm định, hiển thị chi tiết mẫu thẩm định mù và đồ thị quan hệ sáp nhập.

## ADDED Requirements

### Requirement: Bảng danh sách cụm ứng viên và bộ lọc linh hoạt
Hệ thống SHALL hiển thị bảng danh sách các cụm chủ đề mới từ candidates.jsonl với cluster_key, từ khóa nổi bật (top 10 keywords), độ hỗ trợ hội thoại (conversation_support), trạng thái thẩm định và mô tả tóm tắt.

#### Scenario: Lọc cụm theo seed và trạng thái
- **WHEN** người dùng chọn seed=42 và lọc trạng thái accepted_novel
- **THEN** bảng chỉ hiển thị các cụm thỏa mãn cả hai tiêu chí và cập nhật số lượng kết quả tìm thấy.

#### Scenario: Bộ lọc không có cụm phù hợp
- **WHEN** bộ lọc kết hợp không khớp cụm chủ đề nào
- **THEN** bảng hiển thị thông báo trạng thái rỗng Không có cụm chủ đề nào phù hợp với bộ lọc hiện tại thay vì bảng trống trơn.

### Requirement: Xem chi tiết thẩm định mù và mẫu đại diện ngẫu nhiên
Hệ thống SHALL hiển thị khung chi tiết thẩm định cho cụm được chọn, bao gồm tối đa 5 mẫu đại diện (gần tâm centroid nhất) và tối đa 5 mẫu ngẫu nhiên từ các hội thoại khác nhau, kèm điểm số rubric của 2 thẩm định viên và quyết định cuối cùng.

#### Scenario: Chọn xem chi tiết một cụm
- **WHEN** người dùng bấm chọn một hàng cụm trong bảng danh sách
- **THEN** giao diện mở khung chi tiết thể hiện danh sách mẫu câu thoại đã mask, điểm Coherence, Novelty và lý do phê duyệt.

### Requirement: Trực quan hóa đồ thị sáp nhập không chu trình
Hệ thống SHALL hiển thị sơ đồ hoặc bảng danh sách các liên kết sáp nhập (Merge DAG) giữa các cụm tương đồng hoặc giữa cụm mới với chủ đề đã biết, đảm bảo không có liên kết tự trỏ hoặc chu trình khép kín.

#### Scenario: Xem sơ đồ sáp nhập
- **WHEN** người dùng chuyển sang tab Merge DAG trên trang New Topic Discovery
- **THEN** hệ thống vẽ đồ thị có hướng thể hiện các quan hệ từ cụm nguồn đến cụm đích hợp lệ.
