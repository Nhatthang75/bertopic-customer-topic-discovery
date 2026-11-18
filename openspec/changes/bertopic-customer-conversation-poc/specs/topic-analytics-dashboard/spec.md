# Spec Delta

## Purpose

Xuất thống kê và dashboard demo có schema, provenance và evidence basis rõ ràng, ngăn đếm trùng hoặc trình bày proxy/dự đoán như số liệu đã xác minh.

## ADDED Requirements

### Requirement: Bốn đơn vị đếm riêng
Hệ thống SHALL phân biệt customer_message_count, segment_count, mention_count và conversation_count theo design §2/§9. Message gồm mọi customer turn hợp lệ, mention đếm distinct turn-topic có localized evidence, conversation đếm distinct conversation-topic.

#### Scenario: Lời chào và cảm ơn
- **WHEN** Hi, I need a refund, Thanks là ba turn customer
- **THEN** message_count=3, predicted refund mention_count=1, conversation_count=1; agent/action không được cộng vào customer messages.

#### Scenario: Cùng topic nhiều span/cửa sổ
- **WHEN** một turn có hai span cùng topic hoặc windows overlap
- **THEN** mention cho cặp turn-topic vẫn1, segment_count có thể khác và được chú giải.

### Requirement: Evidence basis và null trung thực
Hệ thống MUST gắn basis predicted/verified/cluster_membership; thiếu localized span-topic SHALL mention_count=null với lý do. Review mẫu không cho phép xuất verified tổng corpus; partial verified scope SHALL công bố membership/coverage.

#### Scenario: Chưa localize topic
- **WHEN** candidate chỉ có cluster membership
- **THEN** xuất segment/conversation membership, mention_count=null/missing_localized_evidence và không gắn verified.

#### Scenario: Review một phần
- **WHEN** mới review một phần unit trong scope
- **THEN** verified tổng scope chưa đầy đủ là null/unreviewed_scope, không extrapolate; số trong reviewed scope có coverage rõ.

### Requirement: Mẫu số không bị topic filter làm sai
Hệ thống SHALL dùng cohort metadata scope làm eligible_conversations; lọc topic/source/review_status chỉ đổi numerator. Parent roll-up/merge SHALL dùng union, không cộng đếm trùng.

#### Scenario: Lọc một topic
- **WHEN** scope có100 hội thoại và20 hội thoại mang topic X, người dùng chỉ chọn X
- **THEN** share X vẫn20/100, không thành20/20 vì lọc topic.

#### Scenario: Mẫu số rỗng
- **WHEN** metadata filter không còn hội thoại eligible
- **THEN** share=null/empty_scope, không chia0 hoặc tạo phần trăm mặc định.

### Requirement: Schema version và kiểu dữ liệu
Hệ thống SHALL xuất artifact schema_version1.0.0 với grain, keys/types/null/foreign-key tại design §9; JSON dùng null thật, CSV dùng reserved null token \N, không NaN/Infinity. Unknown major hoặc vi phạm schema SHALL bị chặn.

#### Scenario: Round-trip export
- **WHEN** CSV chứa Unicode, dấu phẩy, newline và null
- **THEN** parse/export giữ giá trị theo RFC4180, null khác empty string và không mất dấu tiếng Việt.

#### Scenario: Key trùng hoặc version sai
- **WHEN** artifact có duplicate unique key, foreign-key lỗi hoặc schema major không hỗ trợ
- **THEN** trả schema_error, dashboard không hiển thị file như run hợp lệ.

### Requirement: Cluster ID có scope và lifecycle bất biến
Hệ thống SHALL scope cluster bằng experiment/run/seed/local ID; -1 không tạo candidate. Artifact đã khóa không ghi đè; merge có target hợp lệ cùng run hoặc known taxonomy, cấm self/cycle/cross-run; promotion tạo taxonomy/run mới.

#### Scenario: Cùng local ID ở hai seed
- **WHEN** seed13 và seed42 cùng có local cluster0
- **THEN** hai cluster keys khác nhau, không gộp topic hoặc support chỉ vì trùng số0.

#### Scenario: Sửa review sau mở nhãn
- **WHEN** review mới được ghi sau G3
- **THEN** tạo review_version exploratory mới, giữ blinded review và metrics confirmatory cũ.

### Requirement: Artifact và truy vết đầy đủ
Hệ thống SHALL xuất manifest/quality/metrics JSON, segments/assignments/candidates/reviews JSONL, conversation_topics/topic_statistics CSV và report Markdown; có hash/version/gate events và drill-down masked customer spans.

#### Scenario: Truy ngược số đếm
- **WHEN** chọn một hàng thống kê
- **THEN** truy được conversation-topic, unit và turn/span tạo count, không expose raw PII hoặc label store chưa mở.

### Requirement: Metadata thiếu không được giả lập
Hệ thống MUST ghi unique_customers/time_bucket/channel null/unavailable với ABCD khi thiếu nguồn tin cậy; không dùng tên/email giả, purchase_date, run timestamp hoặc split làm chiều tương ứng.

#### Scenario: Dashboard ABCD
- **WHEN** nguồn không có timestamp chat/customer ID/channel
- **THEN** vô hiệu các biểu đồ/chỉ số đó kèm giải thích, giữ source_split chỉ là split.

### Requirement: Dashboard chỉ đọc kết quả và phân biệt trạng thái
Hệ thống SHALL có tổng quan/fixed/discovery-review/evaluation/export, không fit khi mở; hiển thị run/version, evidence basis, ground_truth_type, inductive/transductive và functional/proxy/semantic/validity status riêng.

#### Scenario: Proxy đạt nhưng semantic pending
- **WHEN** benchmark proxy pass còn review chưa hoàn tất
- **THEN** dashboard thể hiện pending semantic/overall, không gắn nhãn PoC hoàn tất.

#### Scenario: Run invalid
- **WHEN** leakage audit đánh dấu invalid
- **THEN** hiển thị invalid cùng lý do, không đưa vào bảng kết quả nghiệm thu pass.

### Requirement: Filter và export nhất quán
Hệ thống SHALL lọc run/experiment/split/topic level/source/review_status/evidence_basis và xuất đúng bảng với scope/denominator hiện tại; fixed/candidate merge không bị đếm hai lần trong reviewed view.

#### Scenario: Đối chiếu export
- **WHEN** xuất bảng dưới bộ lọc đã chọn
- **THEN** mọi count/share/null/basis khớp dashboard và merge roll-up dùng distinct union.

### Requirement: Báo cáo giới hạn và phần chưa đo
Hệ thống SHALL báo test exposure, resource/search coverage, target pass/fail/pending, proxy/semantic, error analysis và hạn chế ABCD; không tuyên bố tiếng Việt/audio đã kiểm chứng từ text tiếng Anh.

#### Scenario: Chưa có thử nghiệm thực
- **WHEN** chưa chạy mô hình hoặc chưa có review đủ điều kiện
- **THEN** ghi chưa đo/pending tương ứng, không thay bằng số giả hoặc cam kết chất lượng.
