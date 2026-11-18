# Spec Delta

## Purpose

Chuẩn bị hội thoại nhiều lượt thành evidence units ở cấp customer span, bảo toàn dữ liệu và ngăn metadata nhãn ảnh hưởng đầu vào phân tích.

## ADDED Requirements

### Requirement: Đọc nguồn và giữ dữ liệu nguyên vẹn
Hệ thống SHALL đọc ABCD/ontology chỉ đọc, giữ split, hash và số hội thoại/turn; bản ghi lỗi SHALL vào quarantine suy ra với lý do, không sửa raw.

#### Scenario: Kiểm kê nguồn hiện tại
- **WHEN** đọc hai nguồn đã khai báo với hash khảo sát
- **THEN** báo train/dev/test 8.034/1.004/1.004 trước lọc và hash raw không đổi sau run.

#### Scenario: Bản ghi lỗi
- **WHEN** thiếu ID/text, role lạ hoặc ID trùng
- **THEN** ghi quarantine và reason count, không đoán role hoặc âm thầm bỏ lỗi.

### Requirement: Feature không chứa nhãn
Hệ thống MUST dùng allowlist feature; scenario, targets, candidates, action và ID/split không được vector hóa. Label store SHALL riêng khỏi inference và thay nhãn sau khóa membership không được đổi feature/prediction.

#### Scenario: Thay metadata
- **WHEN** thay scenario/targets/candidates trên bản sao cùng membership đã khóa
- **THEN** feature và prediction của pipeline đã khóa không đổi.

#### Scenario: Inject trường cấm
- **WHEN** nhãn hoặc ID/split được nối vào input vectorizer
- **THEN** trả feature_contract_violation và đánh dấu run invalid.

### Requirement: Privacy và hai view cùng nguồn
Hệ thống SHALL dùng original đã mask độc lập nhãn làm view chính; delexed/context là Advanced, phải đăng ký trước G1. Cả hai view giữ cùng split, delexed được mask lại và kiểm tra alignment.

#### Scenario: PII còn trong delexed
- **WHEN** một view delexed vẫn có email/tên phát hiện được
- **THEN** export dùng marker trung tính, không coi view là đã ẩn danh hoàn toàn.

#### Scenario: Ablation lệch alignment
- **WHEN** role/thứ tự delexed không khớp original
- **THEN** loại riêng view ablation với alignment_error, không loại original hợp lệ chỉ vì lỗi view tùy chọn.

### Requirement: Evidence ở customer turn và span
Hệ thống SHALL tạo evidence units trong từng customer turn, không gộp turn để suy diễn evidence. Mỗi unit có ID, turn index, masked text và offsets [start,end) theo Unicode code point; windows dài giữ parent unit.

#### Scenario: Hai nhu cầu ở một turn
- **WHEN** turn là “I need a refund; I forgot my password”
- **THEN** tách hai span ở dấu chấm phẩy, giữ cùng turn nguồn và offsets độc lập để phân loại.

#### Scenario: Nội dung dài
- **WHEN** span vượt 200 token theo tokenizer đã khóa
- **THEN** windows 200/overlap20 giữ chung evidence_unit_id, không mất phần text và không tạo mention thêm vì overlap.

### Requirement: Trạng thái nội dung có quy tắc cố định
Hệ thống SHALL phân biệt non_need, insufficient_evidence và analyzable bằng exact toàn span theo preprocessing version; không lọc unseen text bằng known-topic keywords hoặc xóa một phần câu mang nhu cầu.

#### Scenario: Lời chào kèm nhu cầu
- **WHEN** text là “Hello, I need a refund”
- **THEN** giữ analyzable, không loại cả câu vì có Hello.

#### Scenario: Câu tham chiếu và lời xã giao
- **WHEN** span chỉ là yes, còn span khác chỉ là thanks theo whitelist đã khóa
- **THEN** lần lượt trả insufficient_evidence và non_need, không route hoặc tự ép topic.

### Requirement: Agent không tự tạo nhu cầu
Hệ thống MUST loại action khỏi model, lấy customer làm evidence; context agent chỉ trong view Advanced, tối đa hai turn ngôn ngữ trước, không dùng tương lai và không tạo mention khi thiếu bằng chứng khách.

#### Scenario: Agent quảng bá dịch vụ
- **WHEN** chỉ agent nhắc một topic còn khách không có bằng chứng tương ứng
- **THEN** không tăng mention/conversation topic đó.

### Requirement: Evidence basis không bị nâng cấp sai
Hệ thống SHALL phân biệt model_supported, cluster_only và human_verified; nhãn segment không được lan sang lời chào/cảm ơn hoặc mọi turn nguồn. Human review một mẫu không xác minh toàn cluster.

#### Scenario: Ba turn chỉ một nhu cầu
- **WHEN** ba turn khách là Hi, I need a refund, Thanks
- **THEN** customer_message_count=3 nhưng chỉ turn thứ hai có evidence refund và predicted mention_count=1.

#### Scenario: Membership chưa có evidence topic
- **WHEN** chỉ có cluster membership mà chưa xác định span biểu đạt topic
- **THEN** mention_count=null với missing_localized_evidence, vẫn xuất segment/conversation membership có nhãn basis rõ.

### Requirement: Dữ liệu rỗng và cohort được công bố
Hệ thống SHALL báo số đọc/quarantine/excluded/eligible không chồng nhóm; non_need/insufficient hợp lệ vẫn trong cohort S. Tập không còn customer text hợp lệ SHALL có empty report và không gọi model.

#### Scenario: Hội thoại chỉ lời chào
- **WHEN** hội thoại hợp lệ chỉ có customer chào hỏi
- **THEN** giữ trong eligible_conversations, status non_need, không coi là unseen topic.

#### Scenario: Tất cả dữ liệu lỗi
- **WHEN** mọi hội thoại bị quarantine/excluded
- **THEN** dừng run với empty_scope và báo đầy đủ số loại, không fit model trên tập rỗng.
