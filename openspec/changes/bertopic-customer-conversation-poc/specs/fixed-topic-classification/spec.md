# Spec Delta

## Purpose

Phân loại danh mục đã biết từ customer evidence spans bằng quy tắc quyết định xác định, hợp nhiều nhu cầu có bằng chứng và giữ trạng thái thiếu chắc chắn minh bạch.

## ADDED Requirements

### Requirement: Quyết định span theo threshold và margin
Hệ thống SHALL xét analyzable evidence unit theo thứ tự: s1<tau là unmatched; còn lại margin<delta là ambiguous; còn lại accepted đúng top-1. Hòa score SHALL sắp topic ID tăng; không nhận hai nhãn cạnh tranh cùng unit.

#### Scenario: Hai nhãn gần nghĩa
- **WHEN** tau=0,50, delta=0,10 và một span có shipping_issue=0,76, order_issue=0,73
- **THEN** trả ambiguous, giữ competing scores, không xuất hai accepted labels.

#### Scenario: Giá trị biên
- **WHEN** tau=0,50, delta=0,10, s1=0,60 và s2=0,50
- **THEN** top-1 accepted theo score/margin round-half-even đến 8 chữ số thập phân đã khóa, không đổi hành vi giữa các lần chạy.

#### Scenario: Điểm dưới ngưỡng
- **WHEN** s1=0,49 với tau=0,50
- **THEN** trả unmatched dù margin lớn, không gán known topic.

### Requirement: Multi-label phải có các evidence units độc lập
Hệ thống SHALL hợp nhãn accepted từ các span độc lập có offsets riêng tại turn/conversation; không dùng ABCD scenario đơn làm multi-label ground truth hoặc suy hai nhu cầu chỉ vì top-2 cùng vượt tau.

#### Scenario: Hai nhu cầu thật
- **WHEN** span A thuộc account_access có điểm 0,80/top2=0,55 và span B thuộc product_defect có điểm 0,82/top2=0,50, tau=0,50/delta=0,10
- **THEN** hội thoại giữ cả hai nhãn và hai evidence spans độc lập.

#### Scenario: Hai nhãn cùng vượt tau nhưng một nhãn thắng rõ
- **WHEN** cùng unit có s1=0,85, s2=0,60 và delta=0,10
- **THEN** chỉ nhận top-1, không coi đó là multi-label.

### Requirement: Window không làm nhân evidence
Hệ thống SHALL gộp điểm từng topic qua windows cùng evidence_unit_id bằng max trước xét threshold/margin; windows không được tạo thêm nhãn hoặc mention độc lập.

#### Scenario: Overlap cùng span
- **WHEN** hai window chồng lấn cùng biểu đạt một nhu cầu
- **THEN** chỉ có một evidence unit-topic assignment và một cặp turn-topic cho mention.

### Requirement: Child có ngưỡng riêng và cho phép null
Hệ thống SHALL chỉ xét child dưới parent accepted bằng tau_child/delta_child khóa riêng; child không đạt giữ parent và child=null. Score/type/version/evidence SHALL đi cùng output; similarity không được gọi là probability.

#### Scenario: Chỉ biết cha
- **WHEN** flow accepted nhưng child dưới threshold hoặc thiếu margin
- **THEN** xuất parent, child=null/child_unresolved và không đoán child.

### Requirement: Trạng thái hội thoại không đồng nhất với unseen
Hệ thống SHALL trả non_need, insufficient_evidence, known, unknown_candidate hoặc mixed theo bảng hợp Kset/Rset trong design; mixed nghĩa known cộng residual chưa rõ, không tự xác nhận novel topic.

#### Scenario: Known cộng residual
- **WHEN** một unit accepted known và unit khác unmatched/ambiguous
- **THEN** conversation_status=mixed, residual_flag=true, vẫn giữ known label và route đúng residual unit.

#### Scenario: Không có nhu cầu hoặc thiếu bằng chứng
- **WHEN** không có accepted/routed unit và hội thoại chỉ non_need hoặc có insufficient_evidence
- **THEN** trả trạng thái tương ứng, residual_flag=false, không gọi đây là phát hiện unseen.

### Requirement: Tổng hợp và điểm benchmark tái lập
Hệ thống SHALL chọn primary flow theo max accepted evidence score, tie theo ID; không accepted thì abstain. Unseen prediction SHALL dùng residual_flag; decision score SHALL phản ánh threshold/margin, score-null báo coverage riêng.

#### Scenario: Known bị abstain
- **WHEN** ground truth known nhưng mọi unit chưa đủ điều kiện accepted
- **THEN** primary=abstain, tính FN known, không loại mẫu khỏi benchmark.

### Requirement: Chọn cấu hình có giới hạn và baseline công bằng
Hệ thống SHALL tuân search registry train/dev-only, ngân sách/grid/tie/fallback ở design §5; baseline có rejection score/ngưỡng riêng. Mọi phép so sánh SHALL cùng cohort, tách top-1, reject và multi-label manual.

#### Scenario: Không cấu hình dev đạt ràng buộc
- **WHEN** không có cấu hình unknown F1 dev>=0,60
- **THEN** chọn theo fallback objective đăng ký, gắn dev_constraint_failed, không đổi target test hoặc thêm model tùy ý.

#### Scenario: Baseline open-set
- **WHEN** benchmark baseline đã fit train K
- **THEN** dùng q chọn từ dev K+H_dev và 1-max_proba cho unknown score, không dùng cosine threshold của classifier chính.

### Requirement: Optional không làm thay đổi Must-have sau test
Hệ thống MUST chỉ đưa per-class thresholds, context/delexed hoặc fine-tuning vào benchmark nếu đăng ký trước G1; kết quả thêm sau mở test SHALL là exploratory riêng.

#### Scenario: Đề xuất cải tiến sau thấy lỗi test
- **WHEN** muốn thêm semantic clause splitter hoặc threshold từng lớp sau G3
- **THEN** giữ kết quả confirmatory cũ và đăng ký experiment exploratory mới, không thay kết luận test ban đầu.

