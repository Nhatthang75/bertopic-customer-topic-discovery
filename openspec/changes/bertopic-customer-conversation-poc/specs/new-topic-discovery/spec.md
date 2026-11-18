# Spec Delta

## Purpose

Khám phá nhóm nhu cầu từ phần customer text chưa được danh mục giải thích, cung cấp review có bằng chứng và phân biệt cluster, outlier, proxy recovery với topic mới được xác minh.

## ADDED Requirements

### Requirement: Pool và chế độ discovery rõ ràng
Hệ thống SHALL dùng BERTopic trên evidence units unmatched/ambiguous đủ nội dung, không dùng non_need/insufficient; không đưa nhãn ẩn vào seed/feature/name. Test discovery SHALL ghi batch_transductive, tham số khóa trước G1.

#### Scenario: Discovery batch mới
- **WHEN** nhận routed test pool sau classifier inductive đã khóa
- **THEN** fit cụm bằng text không nhãn, xuất mode batch_transductive và không chuyển fitted artifact test về tuning.

#### Scenario: Không đủ pool
- **WHEN** pool rỗng hoặc dưới điều kiện đã đăng ký
- **THEN** xuất empty/insufficient_pool với lý do, không dựng topic giả hoặc tự sửa tham số dựa kết quả test.

### Requirement: Một evidence unit một membership
Hệ thống SHALL gom windows cùng evidence unit theo quy tắc không nhãn đã khóa trước clustering; output một membership/unit, không nhân support theo overlap.

#### Scenario: Span dài nhiều windows
- **WHEN** một unit có nhiều windows overlap
- **THEN** cluster support theo unit/conversation không tăng chỉ vì có nhiều cửa sổ.

### Requirement: Support không đồng nghĩa novelty
Hệ thống SHALL xuất keywords, masked evidence, unit/conversation support và nearest known. Cluster >=5 distinct conversations thành proposed, nhỏ hơn monitor; -1 SHALL là outlier, không tạo candidate mới.

#### Scenario: Nhiều đoạn từ một hội thoại
- **WHEN** cluster có 20 units nhưng chỉ một conversation
- **THEN** giữ monitor, không coi support đạt ngưỡng5 hội thoại.

#### Scenario: Tất cả là outlier
- **WHEN** mọi unit mang local cluster -1
- **THEN** outlier rate=1, candidate list rỗng, không báo novelty thành công.

### Requirement: Sampling review không cherry-pick
Hệ thống SHALL lưu tối đa5 representative units từ conversation khác nhau và tối đa5 random units từ conversation khác còn lại theo hash seed42. Sample IDs/frame/quy tắc mở thêm SHALL khóa trước xem đáp án; cluster nhỏ lấy hết conversation có thể lấy.

#### Scenario: Cluster đủ mười hội thoại
- **WHEN** cluster có ít nhất mười conversation
- **THEN** review gồm năm đại diện và năm ngẫu nhiên không trùng conversation, không chỉ năm ví dụ đẹp.

### Requirement: Rubric hai reviewer và trạng thái semantic
Hệ thống SHALL dùng hai reviewer độc lập đủ điều kiện, rubric coherence/novelty 0..2 và adjudication. accepted_novel yêu cầu support>=5, coherence=2 với >=80% samples fits_candidate, novelty=2 khác taxonomy K; thiếu review SHALL pending.

#### Scenario: Cụm có support nhưng trùng known
- **WHEN** reviewer xác nhận cùng nghĩa known topic
- **THEN** ghi merged với target hợp lệ hoặc rejected, không tăng accepted_novel/candidate precision numerator.

#### Scenario: Thiếu reviewer
- **WHEN** chỉ một reviewer hoàn thành
- **THEN** semantic_status=pending, không công nhận novelty hoặc nghiệm thu PoC hoàn tất chỉ nhờ proxy metrics.

#### Scenario: Hai reviewer bất đồng
- **WHEN** coherence/novelty khác nhau
- **THEN** giữ từng rubric và adjudication có lý do; chưa adjudicate thì không accepted_novel.

### Requirement: Review cluster không xác minh mọi assignment
Hệ thống MUST giữ evidence_status theo cặp unit-topic; một cluster accepted_novel không tự biến mọi membership thành human_verified hoặc tạo verified mention toàn corpus từ samples.

#### Scenario: Review mười unit trong cluster lớn
- **WHEN** cluster có một trăm unit nhưng chỉ mười unit được review
- **THEN** verified evidence giới hạn đúng sampled spans, conversation_count toàn cluster vẫn là dự đoán và verified tổng scope chưa đủ thì null.

### Requirement: Review và lifecycle bất biến qua gate
Hệ thống SHALL khóa assignments/names/samples/blinded review ở G2 trước full hidden taxonomy/closed-set exposure, kiểm tra target merge hợp lệ và DAG; review sau G3 thuộc version exploratory mới.

#### Scenario: Merge cycle
- **WHEN** merge A->B trong khi B đã dẫn ngược về A, hoặc target khác run
- **THEN** từ chối quyết định và giữ lịch sử cũ nguyên vẹn.

#### Scenario: Mở ground truth
- **WHEN** evaluator mở H_final sau G3
- **THEN** mapping nghĩa/flow chỉ vào evaluation, không đổi tên cụm hoặc review blinded đã khóa.

### Requirement: Routing loss và discovery toàn bộ
Hệ thống SHALL báo routing recall/loss, outlier, contamination và fragmentation; all-analyzable-unit ablation cùng seed42 là Must-have kỹ thuật để đo routing miss, không thay main prediction.

#### Scenario: Hidden bị gán known
- **WHEN** conversation hidden không có unit nào được route
- **THEN** ghi routing miss, giữ trong denominator recovery và so sánh với all-unit ablation đã đăng ký.

### Requirement: Candidate precision có coverage
Hệ thống SHALL tính semantic candidate precision bằng accepted_novel trên proposed đã review hoàn tất, báo reviewed/proposed/pending; merged-to-known không là novel. Chưa review hết main seed42 SHALL không tuyên bố complete semantic PoC.

#### Scenario: Một phần queue chưa review
- **WHEN** có 10 proposed nhưng chỉ 6 đã review
- **THEN** báo precision trên 6 và coverage6/10, pending4, không trình bày như precision toàn bộ queue.
