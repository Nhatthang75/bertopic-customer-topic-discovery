# Tasks

Tất cả checkbox là công việc thực thi tương lai sau yêu cầu mới, chưa thực hiện. Must-have gồm sáu capability, baseline, all-unit routing ablation seed42, discovery seed13/42/73, review main seed42, export/dashboard và đánh giá. Không bắt đầu apply trong lần sửa tài liệu này. Mỗi nhóm chỉ bắt đầu khi dependency được nêu đã pass; không dùng thứ tự checklist để vượt gate.

## 1. Must-have — Registry, quyền truy cập và schema trước dữ liệu mô hình

- [x] 1.1 Tạo experiment registry G0 giữ H_final/H_dev/K, target cũ, scope, grids/budget/fallback và test-exposure log theo design §5–6; xác minh registry hash và không có kết quả test dùng để sửa registry.
- [x] 1.2 Ghi roles/input scopes, trusted custodian sealed-label membership-only, namespace/cache policy và điều kiện reviewer blinded; xác minh fixture truy cập hidden taxonomy/test labels trái gate bị chặn/invalid, inference không nhận label store.
- [x] 1.3 Tạo schema1.0.0/unique keys/types/foreign-keys/null token theo design §9; xác minh fixture JSON/CSV Unicode/newline/null, duplicate key và unknown-major có kết quả mong đợi trước các producer model.
- [x] 1.4 Khóa đúng hai model IDs cùng revisions/tokenizers/licenses và ngân sách trong registry, chưa chọn model bằng metric; xác minh revision bất biến và ghi unavailable nếu nguồn/giấy phép không đáp ứng, không tự thêm model.
- [x] 1.5 Viết hướng dẫn offline/gates/schema và raw read-only; xác minh phân biệt planning complete với implementation complete và quy tắc không fit khi mở dashboard.

## 2. Must-have — Dữ liệu, split và evidence units

- [x] 2.1 Tạo reader/validator ABCD gzip và ontology; xác minh count nguồn 10.042, role/schema/quarantine fixture và hash raw trước/sau không đổi.
- [x] 2.2 Tạo masked original view bằng masker không dùng nhãn, chuẩn hóa NFC và provenance offsets; xác minh fixtures PII/phủ định/giá/sản phẩm và mẫu train K không bị nối scenario vào feature.
- [x] 2.3 Tạo exact/near-duplicate audit, split/exclusion manifest không nhãn theo design §6; xác minh nhóm vượt split giữ test>dev>train, counts đối soát và không chuyển raw.
- [x] 2.4 Tạo evidence units theo customer turn/sentence/semicolon, window200-overlap20 và immutable IDs; xác minh fixtures một turn hai span, decimal/viết tắt, long span và không mất text.
- [x] 2.5 Tạo bộ lọc non_need/insufficient_evidence/analyzable exact theo design §2; xác minh Hi/Thanks/Yes, “Hello, I need a refund”, unseen text ngắn và PII-only có trạng thái đúng.
- [x] 2.6 Tạo feature allowlist và kiểm tra mutation/injection; xác minh thay nhãn sau khóa membership không đổi features, ID/split/action không vector hóa và forbidden field làm invalid.
- [x] 2.7 Xuất data_quality/segments schema1.0.0 và tài liệu evidence/offset/content status; xác minh read=quarantine+excluded+eligible theo nhóm không chồng, ablation alignment lỗi không loại original hợp lệ và empty corpus không gọi model.

## 3. Must-have — Taxonomy và nền tảng thống kê

- [x] 3.1 Tạo taxonomy đầy đủ10/55, IDs/parent/mapping version và kho labels riêng; xác minh namespace/status child không trùng và không coi action là topic/intent.
- [x] 3.2 Tạo alias mapping có membership/flow, giữ hai nhãn lệch unresolved; xác minh jacket_how_2/timing_4 đúng, timing_99/sai flow unresolved và canonical coverage đúng.
- [x] 3.3 Soạn mô tả K từ ontology/train K, tách full taxonomy chỉ dùng sau G2; xác minh không có hidden child/alias/prototype trong model K hoặc review input.
- [x] 3.4 Tạo các cohort S/S_cs/S_os và count helpers cho message/segment/mention/conversation theo schema trước producer; xác minh fixtures Hi/refund/Thanks cho3 messages nhưng1 predicted mention, overlap/roll-up không tăng trùng.
- [x] 3.5 Tạo evidence basis/null/scope và mẫu số metadata-only; xác minh cluster_only mention=null, verified partial không extrapolate, lọc topic20/100 vẫn20% và empty share=null.
- [x] 3.6 Viết hướng dẫn taxonomy/intent/action, alias và số đếm; xác minh tài liệu ví dụ không coi ABCD scenario là gold label cho mọi span.

## 4. Must-have — Evaluator, rubric và fixture trước tuning

- [x] 4.1 Tạo evaluator fixed flow/child end-to-end và unknown P/R/F1/rank scores/cohorts; xác minh abstain=FN, parent sai/child null không bị loại, hidden insufficient vẫn FN và score-null có coverage.
- [x] 4.2 Tạo recovery family-union evaluator cùng proxy/semantic stages và contamination/fragmentation/routing loss; xác minh fixture hai cluster10-overlap2 trên50 ra recall0,36, không cluster>=0,30 riêng vẫn recovered family.
- [x] 4.3 Tạo clustering metrics unit grain, NMI/ARI proxy, ARI_all/shared, NPMI/diversity và null cases; xác minh all-outlier/shared empty/one-cluster không bị báo discovery ổn định tốt.
- [x] 4.4 Tạo dev search scorer/objective/tie/fallback, bootstrap1000 theo conversation, manual sample manifest; xác minh fixture numeric chọn đúng, giữ metric null và bootstrap không coi windows độc lập.
- [x] 4.5 Tạo rubric/sample selector/review history/adjudication cho hai reviewer, >=80% coherence và novelty2; xác minh representative+random không trùng conversation, merged-known không tính novel và partial review=pending.
- [x] 4.6 Tạo gate/audit fixtures cho hidden train, closed-model reuse, early label access, reviewer exposure, mutation sau gate và cache leak; xác minh tất cả vi phạm làm benchmark invalid và logs bất biến.
- [x] 4.7 Tạo test decision table bằng score giả tau0,50/delta0,10, span độc lập/competing/biên và child fallback; xác minh kỳ vọng một/multi-label/ambiguous/unmatched trước model search.
- [x] 4.8 Ghi tài liệu định nghĩa metric/grain/null/rubric và bảng requirement->fixture cho sáu specs; xác minh nhóm1–4 pass trước tuning nhóm5–6, không có benchmark dùng evaluator chưa kiểm chứng.

## 5. Must-have — Model/threshold search trên train-dev được phép

- [x] 5.1 Sau nhóm1–4, smoke hai model theo hash train K tối đa200 conversation, RAM/thread/batch/time đã đăng ký; xác minh không dùng H_final/test, ghi OOM retry/unavailable và dừng resource_blocked nếu không ứng viên hợp lệ.
- [x] 5.2 Tạo similarity scorer normalized/rounding, evidence-unit window aggregation và decision table; xác minh fixture nhóm4.7 pass và output accepted có đúng customer span offsets.
- [x] 5.3 Chạy grid52 parent mỗi model trên dev K+H_dev bằng evaluator đã pass, chọn model/threshold theo objective/tie/fallback; xác minh search log đủ attempted/skipped/timeouts và không có H_final/descriptions test.
- [x] 5.4 Chọn child threshold chung bằng grid52 sau parent, canonical dev K end-to-end; xác minh parent sai vẫn child error, thiếu support thì fallback0,50/0,10 có calibration_state, không mở test.
- [x] 5.5 Tạo baseline TF-IDF/Logistic Regression và search15 C/q train K/dev K+H_dev; xác minh vocabulary chỉ fit train, rejection score/proba khác cosine và convergence failure được ghi.
- [x] 5.6 Tạo conversation primary/status/residual flag và report known/unknown/mixed/no-evidence; xác minh fixtures multi-span, competing labels, non_need, insufficient và score-null đúng cohort.
- [x] 5.7 Ghi hướng dẫn model selection/threshold/calibration/search coverage; xác minh dev_constraint_failed không bị đổi thành pass và không lặng lẽ mở rộng grid/ngân sách.

## 6. Must-have — Discovery tuning và chuẩn bị review

- [x] 6.1 Tạo routed pool theo evidence unit và gom window embeddings không nhãn theo design §7; xác minh non_need/insufficient không vào pool, overlap không nhân membership, empty/insufficient_pool có artifact.
- [x] 6.2 Search16 UMAP/HDBSCAN configs trên dev pool theo design §5, vectorizer cố định; xác minh dùng proxy dev evaluator trước chọn, không hidden seeds/labels, có log effective neighbors/init/timeout/fallback.
- [x] 6.3 Tạo cluster candidates/keywords/nearest-known/support/IDs cho main và technical runs; xác minh support theo conversation>=5, -1 không candidates row, cluster IDs khác seed/run không trộn.
- [x] 6.4 Tạo review pipeline theo rubric/sampling nhóm4.5 và merge DAG validator; xác minh thiếu reviewer/lý do, cycle/cross-run target bị từ chối và human_verified chỉ đúng sampled span-topic.
- [x] 6.5 Viết hướng dẫn review/coherence/novelty và phân công hai reviewer đủ điều kiện; xác minh reviewer không được đọc hidden taxonomy/closed results trước G2, nếu thiếu người ghi pending và không vượt gate.

## 7. Must-have — G1, open test không nhãn và G2

- [x] 7.1 Audit toàn bộ registry/model/search/split/schema/metric/rubric fixtures, khóa G1; xác minh hashes/config và seed13/42/73, all-unit ablation seed42 cùng Advanced đăng ký trước đều hiện trong manifest, test chưa tham gia tuning.
- [x] 7.2 Chạy classifier inductive trên test K+H_final với config khóa, lưu primary/status/residual/evidence; xác minh không đọc label store hoặc fit model trên test và ghi failure artifact nếu lỗi.
- [x] 7.3 Chạy routed BERTopic seed13/42/73 và all-analyzable-unit ablation seed42 không nhãn với tham số khóa; xác minh mode transductive, không gộp dev/test và không điều chỉnh theo test label/biểu đồ.
- [x] 7.4 Khóa sampling frame/IDs, hai reviewer blinded review mọi proposed main seed42 và adjudicate bằng rubric; xác minh names/descriptions, per-sample judgments và reviewer access đầy đủ, semantic pending không được bỏ qua.
- [x] 7.5 Khóa G2 với mọi open assignment/candidate name/sample/review hoặc technical failure artifact, ghi review_required=false cho technical seed13/73 và ablation không so sánh semantic; xác minh full hidden taxonomy/closed-set chưa được expose.

## 8. Must-have — Closed-set độc lập và hoàn thiện producer artifacts

- [x] 8.1 Chỉ sau G2, dùng full taxonomy soạn cố định từ ontology và fit baseline riêng train10 flow; xác minh không tái dùng model/vocabulary giữa experiments và không sửa open-set config/output.
- [x] 8.2 Chọn thresholds closed-set trên dev K theo protocol riêng design §5, giữ embedding khóa; xác minh không dùng dev H_final/H_dev hoặc closed feedback để chọn embedding/description/open thresholds.
- [x] 8.3 Khóa closed config trước inference, chạy closed test10 flow và xuất prediction không mở test gold; xác minh namespace, configuration hash, score/evidence/cohort và không tuning test.
- [x] 8.4 Xuất assignments/conversation_topics/candidates/reviews/quality/statistics schema1.0.0 từ cả hai experiments; xác minh keys/foreign-keys/basis/null và đối soát với helper nhóm3.
- [x] 8.5 Hoàn thiện immutable manifest/gate logs/resource usage/report skeleton; xác minh post-gate file mutation bị audit invalid, raw hash không đổi và chưa mở test label trước G3.

## 9. Must-have — G3, evaluation và báo cáo chất lượng

- [x] 9.1 Audit global barrier: mọi phương án đăng ký có config/output/review yêu cầu khóa hoặc failure artifact, rồi ghi G3 trước mở test labels; xác minh không phương án nào được bổ sung hồi tố sau unblind.
- [x] 9.2 Tính fixed/unknown/child/routing/recovery_proxy và cluster metrics từ evaluator đã pass, bootstrap CI; xác minh support/denominator/abstain/null đúng và proxy không được gọi semantic truth.
- [x] 9.3 Evaluator độc lập đối chiếu nghĩa frozen candidates/samples với H_final ontology sau G3 để báo semantic_supported/uncertain, không sửa blinded output; xác minh cluster label-pure nhưng xã giao không được semantic recovery.
- [x] 9.4 Lấy tối đa200 conversation manual gold theo manifest sau G3, hai reviewer predictions ẩn/adjudication; xác minh không broadcast scenario xuống span và không quay về tuning; thiếu reviewer ghi pending.
- [x] 9.5 Báo stability ba seed với ARI_all/ARI_shared/shared_coverage, routing/all-unit comparison, fragmentation/contamination và length buckets; xác minh không chọn seed đẹp nhất hoặc ARI all-outlier làm bằng chứng chất lượng.
- [x] 9.6 Xuất metrics/report với functional/proxy/semantic/validity statuses và targets giữ nguyên; xác minh fail/pending không biến pass, complete PoC đòi human_verified và ghi rõ test đã khảo sát cấu trúc.

## 10. Must-have — Dashboard, export và nghiệm thu tích hợp

- [x] 10.1 Tạo dashboard đọc artifacts với tổng quan/fixed/discovery-review/evaluation/export; xác minh mở trang không fit model, hiển thị version/basis/proxy-vs-semantic/mode/gates/invalid/pending đúng.
- [x] 10.2 Tạo masked evidence drill-down và review UI append-only; xác minh đúng offsets, không lộ label store/PII và review sau G3 có exploratory version không sửa metrics cũ.
- [x] 10.3 Tạo filters/export/empty/schema-error states; xác minh numerator/denominator/csv khớp bảng, topic filter không tự làm share100%, metadata thiếu bị vô hiệu và merge view dùng distinct union.
- [x] 10.4 Viết hướng dẫn demo/schema/review và giới hạn tiếng Anh/nhãn đơn/test exposure; xác minh không khẳng định tiếng Việt/audio/trend/customer IDs chưa kiểm chứng.
- [x] 10.5 Chạy traceability toàn bộ scenario sáu specs và end-to-end count/hash audit; xác minh fixture của từng nhóm đã pass tại nhóm đó, không để integration thay evaluator/test còn thiếu.
- [x] 10.6 Trình báo cáo nghiệm thu chức năng, mục tiêu proxy, semantic và benchmark validity riêng; xác minh còn pending/fail thì không tự ghi complete PoC hoặc archive.

## Workflow follow-up

- Optional/Advanced không thuộc checkbox Must-have: zero-shot BERTopic, context/delexed ablation, threshold mỗi lớp, fine-tuning, semantic clause splitting, hidden-subflow experiment. Chỉ thêm theo scope/phê duyệt và đăng ký trước G1; sau G3 là exploratory experiment riêng, không sửa kết quả confirmatory.
- Sau thực thi, trình người dùng xem xét kết quả và phần fail/pending; chỉ archive khi có yêu cầu mới và đủ điều kiện nghiệm thu. Không thực hiện apply/archive trong lần sửa tài liệu.

