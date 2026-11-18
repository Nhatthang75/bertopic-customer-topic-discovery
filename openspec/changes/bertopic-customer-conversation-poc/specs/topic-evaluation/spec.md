# Spec Delta

## Purpose

Đánh giá phân loại, unseen detection và discovery bằng protocol có giới hạn tìm kiếm, checkpoint chống leakage và metric phân biệt proxy nhãn kịch bản với bằng chứng semantic.

## ADDED Requirements

### Requirement: Split và duplicate manifest bất biến
Hệ thống MUST giữ mọi turn/span/window/view cùng hội thoại trong một split; nhóm text trùng vượt split loại khỏi phần sớm theo giữ test>dev>train, có exclusion manifest, không sửa raw hoặc đổi ngưỡng dedup sau metric.

#### Scenario: Trùng train-test
- **WHEN** kiểm tra không nhãn phát hiện nhóm trùng vượt split
- **THEN** giữ test, loại train khỏi phần sử dụng và công bố số trước/sau lọc.

### Requirement: Registry và evaluator có trước tuning
Hệ thống SHALL khóa G0 gồm model registry, search grid, budget, metric/tie/fallback, rubric/schema và exposure log; evaluator/fixtures SHALL pass trước chọn threshold hoặc clustering.

#### Scenario: Tuning thiếu evaluator
- **WHEN** evaluator hoặc fixture liên quan chưa pass
- **THEN** chặn tuning/benchmark tương ứng, không tự chọn theo biểu đồ.

### Requirement: Lựa chọn model hữu hạn trên dữ liệu được phép
Hệ thống SHALL xét đúng hai embedding ứng viên đăng ký, grids và ngân sách ở design §5; không chọn bằng H_final/test. Timeout/OOM/unavailable SHALL ghi rõ; hết cấu hình hợp lệ thì resource_blocked, không thêm model sau xem điểm.

#### Scenario: Hết tài nguyên
- **WHEN** không embedding nào chạy hợp lệ trong ngân sách
- **THEN** báo resource_blocked và không đi G1, không thay dataset hoặc target để ghi pass.

#### Scenario: Grid không đạt ràng buộc dev
- **WHEN** không cấu hình đạt unknown F1 dev>=0,60
- **THEN** áp fallback objective đã đăng ký, gắn dev_constraint_failed và giữ nguyên mục tiêu test.

### Requirement: Flow ẩn và taxonomy K giữ nguyên
Hệ thống MUST dùng H_final={subscription_inquiry,troubleshoot_site}, H_dev={shipping_issue}; open train K, dev K+H_dev, test K+H_final bỏ H_dev. Không text/nhãn H_final được dùng chọn embedding/threshold/descriptions/clustering open-set.

#### Scenario: Manifest chứa hidden train
- **WHEN** train open-set hoặc artifact model chứa H_final/H_dev
- **THEN** run invalid, không chấm như benchmark hợp lệ.

### Requirement: Gate configuration và output toàn cục
Hệ thống MUST khóa open config tại G1, open assignments/names/samples/blinded review tại G2 trước closed-set exposure, rồi closed config/predictions và mọi phương án đăng ký tại G3 trước release test ground truth cho scoring/model selector/reviewer. Trusted custodian chỉ được dùng sealed label để tạo membership theo policy, không chấm hoặc tiết lộ lớp.

#### Scenario: Closed-set chạy trước khóa open review
- **WHEN** muốn đưa full taxonomy/closed-set outputs cho người chọn model trước G2
- **THEN** chặn thao tác hoặc đánh dấu leakage violation, không tiếp tục kết luận confirmatory hợp lệ.

#### Scenario: Trusted custodian chia dữ liệu
- **WHEN** custodian đọc sealed labels trước G3 chỉ để tạo membership theo H policy đã đăng ký
- **THEN** chỉ xuất opaque membership không prediction/score/class IDs cho inference; tiết lộ hoặc dùng tuning làm run invalid.

#### Scenario: Mở nhãn đúng thứ tự
- **WHEN** G3 có đủ hash/timestamp output hoặc failure artifact của mọi phương án đã đăng ký
- **THEN** evaluator mới mở test labels và không được sửa prediction/name/review khóa.

### Requirement: Leakage làm run invalid
Hệ thống SHALL kiểm tra feature injection, label access, reuse fitted artifact, reviewer exposure và hash sau gate; vi phạm SHALL giữ log và benchmark invalid, không sửa lịch sử để hợp thức hóa.

#### Scenario: Mutation sau G1
- **WHEN** config threshold hoặc model hash thay sau G1
- **THEN** run invalid và bị loại khỏi nghiệm thu.

#### Scenario: Nhãn làm thay feature
- **WHEN** thay scenario/targets/candidates cùng membership đã khóa làm feature/prediction thay
- **THEN** leakage fixture fail, không được chạy test confirmatory.

#### Scenario: Tái dùng closed model
- **WHEN** open-set nhận fitted model/vocabulary/prototype đã học full closed-set
- **THEN** run invalid dù file nằm namespace khác.

### Requirement: Inductive và transductive tách báo cáo
Hệ thống SHALL ghi classifier inference là inductive và BERTopic fit batch test không nhãn với tham số khóa là batch_transductive. Closed-set lựa chọn độc lập sau G2 không được phản hồi cấu hình open-set.

#### Scenario: Fit discovery test pool
- **WHEN** fit BERTopic trên routed test text không nhãn
- **THEN** báo transductive và không dùng fitted artifact đó cho tuning hoặc gọi đây là predictive inductive test.

### Requirement: Cohort và trạng thái thiếu bằng chứng không đổi denominator
Hệ thống SHALL dùng S/S_cs/S_os đã khóa theo design; non_need/insufficient vẫn trong benchmark. Unseen positive GT là H_final, prediction là residual_flag gồm mixed; score-null chỉ loại khỏi rank metric và báo score_coverage.

#### Scenario: Hidden thiếu evidence
- **WHEN** conversation H_final chỉ insufficient_evidence và residual_flag=false
- **THEN** tính FN unseen/routing miss, không loại khỏi binary F1 hoặc recovery denominator.

### Requirement: Phân loại và multi-label chấm đúng cấp
Hệ thống SHALL báo P/R/F1/accuracy/confusion/support cấp hội thoại, subflow coverage và end-to-end child error; abstain known tính FN. ABCD label không làm ground truth mọi span; multi-label chỉ chấm manual gold độc lập.

#### Scenario: Parent sai hoặc child null
- **WHEN** conversation có child canonical ground truth nhưng parent sai/child null
- **THEN** tính lỗi subflow, không chỉ chấm những mẫu parent đúng để làm đẹp metric.

### Requirement: Recovery flow qua nhiều cluster
Hệ thống SHALL tính Q_h gồm mọi cluster support>=5 và purity_h>=0,70; union conversation Q_h không đếm trùng. recovered_proxy yêu cầu family precision>=0,70 và recall>=0,30 trên toàn S_h, giữ routing misses trong mẫu số.

#### Scenario: Hai subtopic hợp phục hồi flow
- **WHEN** hai cluster thuần h mỗi cluster có 10 conversation, overlap2 và S_h=50
- **THEN** union18, precision1, recall0,36, recovered_proxy=true dù từng cluster chỉ recall0,20.

#### Scenario: Không có hidden support
- **WHEN** S_h rỗng sau lọc
- **THEN** recovery pending/no_support, không ghi pass hoặc tự giảm mục tiêu2/2.

### Requirement: Recovery proxy không thay semantic validation
Hệ thống SHALL báo riêng semantic recovery bằng candidates accepted_novel ở G2 và đối chiếu nghĩa độc lập sau G3 trên mô tả/samples đã khóa; scenario flow không chứng minh topic tại mọi unit.

#### Scenario: Cluster thuần nhãn nhưng vô nghĩa
- **WHEN** cluster đủ proxy precision/recall nhưng review sample không biểu đạt nhu cầu chung
- **THEN** chỉ có thể recovered_proxy, không recovered_semantic_supported hoặc topic mới human_verified.

### Requirement: Metric clustering có grain và outlier rõ
Hệ thống SHALL tính ground-truth NMI/ARI proxy trên evidence units non-outlier, báo coverage; stability dùng cùng IDs với ARI_all gồm -1 và ARI_shared trên giao non-outlier kèm shared_coverage. Trường hợp suy biến SHALL null có lý do.

#### Scenario: Mọi seed toàn outlier
- **WHEN** các seed đều gán mọi unit là -1
- **THEN** không dùng ARI_all cao để tuyên bố discovery ổn định tốt; ARI_shared=null/degenerate và coverage0.

### Requirement: Tái lập, CI và manual gold độc lập
Hệ thống SHALL chạy seed13/42/73, báo mọi seed và bootstrap F1 theo conversation 1000 lần/seed42. Manual gold tối đa200 conversation có sampling manifest, hai reviewer/adjudication và predictions ẩn, không tuning.

#### Scenario: Bootstrap theo hội thoại
- **WHEN** một conversation có nhiều units/windows
- **THEN** resample cả conversation, không coi units độc lập để thu hẹp CI giả.

### Requirement: Mốc nghiệm thu giữ nguyên và tách trạng thái
Hệ thống SHALL giữ Macro-F1>=0,70, unknown F1>=0,60, routing recall>=0,70, seed42 recovered_proxy2/2 với ngưỡng family đã định; báo functional/proxy/semantic/validity riêng. Complete PoC đòi semantic human_verified, không có High unresolved hoặc leakage.

#### Scenario: Proxy pass nhưng review thiếu
- **WHEN** proxy đạt mọi target nhưng reviewer chưa đủ hoặc semantic mapping chưa rõ
- **THEN** semantic/overall pending, không tuyên bố PoC hoàn tất.

#### Scenario: Chất lượng thấp
- **WHEN** metric không đạt target
- **THEN** giữ fail/error analysis, không đổi hidden set, threshold hay split để ghi pass.

### Requirement: Công bố test exposure và Advanced
Hệ thống SHALL công bố test từng được khảo sát cấu trúc/count/mẫu, không gọi hoàn toàn blind. Advanced chỉ tham gia nếu đăng ký trước G1; kết quả thêm sau G3 SHALL exploratory riêng.

#### Scenario: Bổ sung sau mở nhãn
- **WHEN** một phương án mới được đề xuất sau xem test metrics
- **THEN** không được thay main result hoặc đăng ký hồi tố như benchmark confirmatory.


