# Spec Delta

## Purpose

Quản lý topic phân cấp và nhãn chưa chuẩn hóa từ ontology ABCD, duy trì phiên bản có thể truy vết và cách ly danh mục ẩn theo protocol đánh giá.

## ADDED Requirements

### Requirement: Taxonomy đầy đủ và ID phân cấp
Hệ thống SHALL biểu diễn đủ 10 flow/55 subflow chuẩn, ID có namespace cha, mô tả/inclusion/exclusion và version; lưu source_label_type=dataset_intent thay vì khẳng định ontology là taxonomy nghiệp vụ hoàn chỉnh.

#### Scenario: Nạp ontology
- **WHEN** nạp ontology hiện tại
- **THEN** có 10 parent/55 child, ID subflow:shipping_issue/status không xung đột với child cùng tên khác.

### Requirement: Chuẩn hóa alias dựa ontology
Hệ thống SHALL chỉ chuẩn hóa FAQ aliases có membership trong ontology và đúng flow; giữ raw_label, canonical_label, mapping_rule, mapping_version và resolution_status.

#### Scenario: Alias sản phẩm và cửa hàng
- **WHEN** gặp single_item_query/jacket_how_2 và storewide_query/timing_4 có trong ontology
- **THEN** chuẩn hóa lần lượt thành jacket và timing dưới đúng parent, giữ provenance mapping.

#### Scenario: Không tùy tiện cắt suffix
- **WHEN** gặp timing_99 hoặc jacket_how_2 dưới flow khác
- **THEN** trả unresolved, không fuzzy-match hoặc tự cắt suffix.

### Requirement: Nhãn mơ hồ giữ unresolved
Hệ thống MUST giữ subscription_inquiry/status_questions và order_issue/status_delivery_date ở child=null khi chưa có approved mapping; không dùng targets để lấp. Flow hợp lệ vẫn được chấm, child không vào denominator canonical.

#### Scenario: Hai nhãn lệch ontology
- **WHEN** đọc status_questions hoặc status_delivery_date
- **THEN** không tự gán sang status_active/status_delivery_time, báo unresolved count và canonical coverage.

### Requirement: Danh mục open-set không chứa topic ẩn
Hệ thống MUST chỉ cấp K cho open-set classifier/discovery/reviewer, loại flow ẩn và mọi child/alias/description/example/prototype liên quan. Danh mục đầy đủ closed-set SHALL cách ly tới sau G2.

#### Scenario: Tạo taxonomy K
- **WHEN** dựng open-set với H_final và H_dev đã đăng ký
- **THEN** artifact phục vụ model không có mục subscription_inquiry, troubleshoot_site, shipping_issue hoặc hậu duệ của chúng.

#### Scenario: Truy cập danh mục đầy đủ trước gate
- **WHEN** open-set model selector hoặc blinded reviewer đọc taxonomy ẩn trước G2
- **THEN** ghi leakage violation và benchmark invalid, không tiếp tục như run hợp lệ.

### Requirement: Nguồn mô tả không bị tuning theo test
Hệ thống SHALL khóa mô tả K từ ontology/train K trước G1; mô tả full taxonomy closed-set từ ontology được cố định trước closed-set tuning và không phản hồi ngược open-set. Không sửa mô tả bằng lỗi test.

#### Scenario: Closed-set sau khóa open-set
- **WHEN** G2 đã khóa assignments/names/review open-set
- **THEN** có thể dùng full taxonomy cho closed-set độc lập, giữ nguyên open-set artifacts/config.

### Requirement: Topic khác intent và action
Hệ thống SHALL giữ intent độc lập=null khi chưa có annotation riêng; action không được dùng làm evidence nhu cầu hoặc intent khách.

#### Scenario: Action hoàn tiền
- **WHEN** có action offer-refund nhưng không có customer evidence
- **THEN** không tạo topic/mention/intent khách chỉ từ action.

### Requirement: Version và lịch sử mapping
Hệ thống SHALL tăng version khi taxonomy/mapping thay đổi, lưu căn cứ train và phê duyệt; không ghi đè raw, run cũ hoặc đổi mapping từ test để chấm lại như lần đầu.

#### Scenario: Phê duyệt alias mới
- **WHEN** có căn cứ train và quyết định mapping mới
- **THEN** áp dụng ở run/version mới, kết quả và coverage cũ giữ nguyên để đối chiếu.
