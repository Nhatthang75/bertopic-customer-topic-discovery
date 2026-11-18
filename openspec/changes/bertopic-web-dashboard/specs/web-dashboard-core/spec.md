# Spec Delta

## Purpose

Cung cấp nền tảng Web Dashboard tương tác bằng Streamlit, điều phối nạp dữ liệu tĩnh theo nguyên tắc Zero-Fit on Render, quản lý bộ nhớ đệm an toàn và bảo vệ thông tin nhận dạng cá nhân (PII).

## ADDED Requirements

### Requirement: Khởi chạy và điều hướng đa trang
Hệ thống SHALL cung cấp ứng dụng web Streamlit đa trang với thanh điều hướng (sidebar) chuyển đổi giữa 5 trang chức năng: Overview, Fixed Topic Analytics, New Topic Discovery, Conversation Explorer và Model Evaluation.

#### Scenario: Chuyển trang thành công
- **WHEN** người dùng bấm chọn một trang chức năng trên thanh điều hướng bên trái
- **THEN** hệ thống hiển thị chính xác nội dung trang đó và lưu giữ trạng thái bộ lọc trong phiên làm việc.

### Requirement: Nạp dữ liệu Zero-Fit on Render
Hệ thống MUST tải toàn bộ dữ liệu từ các file artifacts Schema 1.0.0 đã khóa tại thư mục cấu hình mà không thực hiện huấn luyện lại, không gọi hàm fit/fit_transform, và không tính toán vector embedding mới khi tải trang.

#### Scenario: Mở trang không gọi mô hình
- **WHEN** người dùng tải lại trang hoặc mở trang mới trên trình duyệt
- **THEN** ứng dụng đọc trực tiếp dữ liệu từ các file JSON/CSV/JSONL có sẵn và render giao diện trong thời gian dưới 2 giây.

### Requirement: Bảo vệ thông tin PII
Hệ thống SHALL chỉ hiển thị nội dung câu thoại khách hàng đã được che mờ PII (masked text) từ segments.jsonl, không lưu trữ và không cung cấp tính năng phục hồi danh tính cá nhân trên giao diện web.

#### Scenario: Hiển thị văn bản an toàn
- **WHEN** giao diện hiển thị câu thoại hoặc phân đoạn bằng chứng của khách hàng
- **THEN** các thực thể tên khách hàng được thể hiện dưới dạng thẻ ẩn danh đã chuẩn hóa và không lộ thông tin nhạy cảm.

### Requirement: Xử lý trạng thái rỗng và cảnh báo lỗi dữ liệu
Hệ thống SHALL hiển thị thông báo trạng thái tải (loading spinner) trong khi đọc tệp lớn và hiển thị hộp thoại cảnh báo lỗi thân thiện (error state) thay vì sập ứng dụng khi thiếu tệp artifact hoặc dữ liệu không khớp schema.

#### Scenario: Thiếu tệp artifact hoặc lỗi định dạng
- **WHEN** một tệp dữ liệu cần thiết trong artifacts không tồn tại hoặc bị lỗi định dạng
- **THEN** giao diện hiển thị thông báo lỗi chi tiết hướng dẫn kiểm tra thư mục artifacts và vô hiệu hóa an toàn các khối chức năng phụ thuộc.

#### Scenario: Trạng thái chờ khi nạp dữ liệu lần đầu
- **WHEN** hệ thống đang nạp tệp phân đoạn lớn vào bộ nhớ đệm trong lần truy cập đầu tiên
- **THEN** giao diện hiển thị biểu tượng quay chờ kèm thông báo Đang nạp dữ liệu phân đoạn.
