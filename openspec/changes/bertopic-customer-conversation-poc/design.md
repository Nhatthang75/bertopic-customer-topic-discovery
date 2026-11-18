# Design

## Context

Xem `proposal.md` về mục tiêu và phạm vi Must-have/Advanced. Đây là bản sửa planning artifacts sau review H1–H5, M1–M4, L1; không có triển khai hoặc kết quả mô hình. Schema hiện tại là spec-driven, CLI nội bộ 1.16.0.

### Bằng chứng dữ liệu đã khảo sát

| Thuộc tính | Quan sát chỉ đọc trước đó |
|---|---|
| Split | train 8.034; dev 1.004; test 1.004; tổng 10.042 hội thoại |
| Cấu trúc | convo_id, scenario, original, delexed; original gồm [role,text]; delexed có speaker/text/turn_count/targets/candidates |
| Role | customer 89.372 turn; agent 95.129; action 36.482 |
| Kiểm tra sơ bộ | Không trùng convo_id; original/delexed cùng số turn, chưa chứng minh alignment ngữ nghĩa mọi turn |
| Ontology | 10 flow, 55 subflow; các biến thể FAQ; status_questions 30 và status_delivery_date 3 chưa có mapping chắc chắn |
| Metadata thiếu | Không có timestamp hội thoại, customer ID bền vững hoặc channel tin cậy; purchase_date không phải ngày chat |

SHA-256 nguồn: ABCD `2bdf53ac359543dcdc38d55bc6513e78df120363f8f44870716e909f4606de15`; ontology `2e1c1d763518ba084ada7f7bc8b54f0b489c81da3b170875cf9340891e06524c`.

Test đã được xem cấu trúc, count, một mẫu hội thoại và phân bố subflow phục vụ review. Đây không phải blind benchmark hoàn toàn. Đặc biệt subscription_inquiry có 94 hội thoại test trước dedup, subflow lớn nhất 26; tiêu chí ép một cluster phủ 30% toàn flow có thể đánh trượt các cụm subflow đúng. Việc sửa sang family union là sửa đơn vị đánh giá trước chạy, không hạ ngưỡng để làm đẹp số đo. Không đọc thêm test để chọn mô hình.

## Goals / Non-Goals

**Goals:** Quyết định có thể lập trình không đoán; evidence theo turn/span; search hữu hạn; checkpoint chống leakage; metrics tách proxy/semantic; schema và dependency tasks đủ rõ.

**Non-Goals:** Không bảo đảm tách được mọi câu chứa nhiều nhu cầu; không dùng ABCD nhãn đơn để chứng minh multi-label. Không biến label ẩn thành prompt/seed. Không xác nhận novelty khi thiếu human review. Không thực thi trong workflow này.

## Decisions

### 1. Kiến trúc và thứ tự phụ thuộc

```text
raw chỉ đọc -> validate/mask -> split/group manifest -> schema + fixture/evaluator
 -> taxonomy K -> span features -> fixed classifier -> unresolved span routing
 -> BERTopic batch -> candidates -> blinded review -> khóa output
 -> evaluator mở nhãn -> proxy metrics + semantic review metrics
 -> thống kê/evidence -> artifacts -> dashboard đọc artifacts
```

Classifier và discovery là hai nhánh riêng: classifier gán known IDs, BERTopic tìm cụm không nhãn trên nội dung chưa giải thích. Một cụm chưa phải topic mới. Must-have gồm similarity classifier, baseline TF-IDF, BERTopic, all-span routing ablation, 3 seed, review, export và dashboard. Advanced theo proposal chỉ được đăng ký trước G1; bỏ qua Advanced không làm thiếu Must-have. Không tái dùng fitted artifact giữa closed/open-set; cache embeddings chỉ chia sẻ khi pretrained chưa thích nghi trên ABCD, cùng hash masked text/model revision và không có label.

Thứ tự thực thi bắt buộc: registry/schema -> dữ liệu/taxonomy -> evaluator/fixture/rubric -> model search -> G1 -> open-set test không nhãn và blinded review -> G2 -> closed-set độc lập -> G3 -> mở test label/evaluate -> dashboard. G0–G3 tại §6; tasks bám đúng thứ tự, không tuning trước evaluator.

### 2. Feature, trạng thái nội dung và evidence (H1, H4, M3)

Nguồn chính là original đã mask PII độc lập nhãn; không dùng scenario để mask. Marker trung tính cho tên/email/phone/address/ID; không gọi dịch vụ ngoài. Feature allowlist: conversation_id, source_split, segment_id, evidence_unit_id, customer_turn_index, span_start, span_end, masked_customer_text, context_turn_indices, context_text, language, preprocessing_version. Chỉ text được phép vector hóa; IDs/offset/split là provenance. Scenario, targets, candidates, action và action arguments bị chặn. Đổi nhãn trên bản sao sau khi khóa membership không được đổi feature/inference. delexed/context là Advanced; delexed phải mask lại và kiểm tra alignment, lệch chỉ loại view ablation, không tự loại original hợp lệ.

**Evidence unit:** Must-have không gộp nhiều turn thành một đơn vị quyết định. Trong mỗi customer turn, tách span ở ranh giới câu `.?!`, dấu `;` và xuống dòng; giữ decimal và danh sách viết tắt cố định trong preprocessing_version. Không tách tùy ý ở từ and/or. Ghi khoảng [start,end) theo Unicode code point trên masked turn sau chuẩn hóa NFC, không offset trên raw. Splitter/rule được đóng băng từ train trước G1. Giữ phủ định và ý nghĩa nghiệp vụ, không stem/xóa stopword mạnh trước embedding.

Mỗi span là một segment và một evidence unit, tối đa 200 token model. Span dài chia cửa sổ 200 overlap 20 có cùng evidence_unit_id và offset con. Nhãn của evidence unit được xét trên score lớn nhất của từng topic qua các cửa sổ; overlap không tạo mention thêm. Không tự suy ra hai nhu cầu từ hai cửa sổ cùng unit; top-2 vẫn qua margin tại §4. Câu có nhiều nhu cầu nhưng không tách được phải báo giới hạn, không tuyên bố multi-label đầy đủ; semantic clause splitting là Advanced.

**Bộ lọc xác định trước model:** normalize case/space và bỏ punctuation biên để exact-match toàn span. Danh sách non_need_v1: hi, hello, hey, good morning, good afternoon, good evening, thanks, thank you, thank you very much, bye, goodbye, have a nice day. Span chỉ còn marker PII/space cũng non_need. Không xóa một phần span: “Hello, I need a refund” vẫn analyzable. Exact standalone yes/no/ok/okay/sure/that one/it/this -> insufficient_evidence ở view chính. Mọi text khác không rỗng là analyzable; không dùng taxonomy keywords để loại câu unseen ngắn. Danh sách có thể mở rộng từ train trước G1 và version hóa, không từ test. Masker/splitter có fixture và kiểm tra mẫu train; không cam kết bắt mọi PII.

| Trạng thái evidence unit | Điều kiện | Fixed / discovery |
|---|---|---|
| non_need | Exact toàn span ở whitelist hoặc PII-only | Không gán, không route |
| insufficient_evidence | Tham chiếu rời rạc theo rule trên | Không gán, không route; báo riêng |
| accepted | Analyzable, một nhãn thắng ngưỡng và margin | Known evidence |
| unmatched | Analyzable, điểm cao nhất dưới tau | Route |
| ambiguous | Analyzable, đủ similarity nhưng margin thiếu | Route; giữ competing scores, không nhận cả hai |

Hợp hội thoại dùng Kset=known labels accepted và Rset=unmatched/ambiguous có thể route:

| conversation_status | Quy tắc |
|---|---|
| non_need | Mọi unit hợp lệ đều non_need |
| insufficient_evidence | Kset/Rset rỗng, có ít nhất một unit insufficient_evidence |
| known | Kset không rỗng, Rset rỗng |
| unknown_candidate | Kset rỗng, Rset không rỗng |
| mixed | Kset và Rset đều không rỗng; đây là mixed known + unresolved, chưa chứng minh phần residual thực sự novel |

Giữ cờ has_insufficient_evidence riêng kể cả khi known/mixed. Unknown_candidate khác topic mới accepted. Primary_topic benchmark là accepted flow có max score qua units, hòa điểm theo ID tăng dần; nếu không có accepted thì prediction=abstain, không đổi non_need/insufficient thành unseen. Binary unseen prediction dùng residual_flag=(Rset không rỗng), nên mixed cũng positive; false positives trên known được tính bình thường. Ground-truth multi-label/mixed chỉ có từ annotation độc lập.

**Evidence và đếm:** assignment accepted phải chỉ đúng customer turn/span (hoặc parent span cho các cửa sổ), không lan nhãn sang turn lân cận. Evidence_status=model_supported chỉ là dự đoán; human_verified chỉ khi reviewer xác nhận span-topic cụ thể. Discovery assignment là cluster membership, evidence_status=cluster_only cho tới khi review đúng cặp span-topic, không tự human_verify cả cụm vì vài mẫu tốt.

- customer_message_count: số customer turn hợp lệ, gồm lời chào/PII-only, không gồm agent/action; per-topic là số turn nguồn có assignment, nhãn source_messages_with_assignment rõ ràng, không gọi là mention đã kiểm chứng.
- segment_count: distinct segment/cửa sổ có assignment; raw total và per-topic báo riêng.
- mention_count: distinct (conversation_id,customer_turn_index,topic_id) có span localizable và model_supported hoặc human_verified; bắt buộc evidence_basis=predicted hoặc verified, coverage và scope. Nhãn trần không evidence => mention_count=null/null_reason=missing_localized_evidence. Cột verified không có review đầy đủ trong scope => null, không extrapolate từ mẫu.
- conversation_count: distinct conversation-topic có assignment trong scope, predicted/verified tách riêng; flow roll-up dùng union, không cộng số con.

Fixture bắt buộc: turn 1 “Hi”, turn 2 “I need a refund”, turn 3 “Thanks” -> 3 messages nhưng chỉ turn 2 là evidence refund, predicted mention=1. Ba turn nhu cầu thực cùng topic -> mention=3/conversation=1. Một turn có hai span cùng topic -> mention=1. Overlap -> không tăng mention. Cluster chỉ có membership chưa localize ý nghĩa -> mention=null.

### 3. Taxonomy và nhãn chưa chuẩn hóa

Flow là proxy topic cấp cha, subflow cấp con; lưu source_label_type=dataset_intent, không đồng nhất với intent nghiệp vụ. Intent độc lập=null khi chưa có annotation riêng; action không làm topic/intent evidence.

| Flow | Các subflow chuẩn |
|---|---|
| account_access | recover_username, recover_password, reset_2fa |
| manage_account | status_service_added, status_service_removed, status_shipping_question, status_credit_missing, manage_change_address, manage_change_name, manage_change_phone, manage_payment_method |
| order_issue | status_mystery_fee, status_delivery_time, status_payment_method, status_quantity, manage_upgrade, manage_downgrade, manage_create, manage_cancel |
| product_defect | refund_initiate, refund_update, refund_status, return_stain, return_color, return_size |
| purchase_dispute | bad_price_competitor, bad_price_yesterday, out_of_stock_general, out_of_stock_one_item, promo_code_invalid, promo_code_out_of_date, mistimed_billing_already_returned, mistimed_billing_never_bought |
| shipping_issue | status, manage, missing, cost |
| single_item_query | boots, shirt, jeans, jacket |
| storewide_query | pricing, membership, timing, policy |
| subscription_inquiry | status_active, status_due_amount, status_due_date, manage_pay_bill, manage_extension, manage_dispute_bill |
| troubleshoot_site | credit_card, shopping_cart, search_results, slow_speed |

ID flow:<flow>, subflow:<flow>/<child>; đủ 10/55 trong taxonomy đầy đủ. Mỗi mục có parent, mô tả tiếng Anh cố định cho model, giải thích tiếng Việt, inclusion/exclusion, alias và version. Mô tả known K từ ontology/train K trước G1, không sửa dựa dev/test errors. Full taxonomy closed-set được soạn độc lập từ ontology, không expose mục H_dev/H_final cho open-set hoặc blinded reviewer; chỉ dùng trong closed-set sau G2. Không viết mô tả ẩn từ test.

Mapping chỉ trong label store: single_item_query `<item>_how_<n>`/`<item>_other_<n>` -> item; storewide_query `<category>_<n>` -> category; bắt buộc alias có trong ontology.values.enumerable tương ứng, n=1..4 và đúng flow. Không fuzzy match/cắt suffix khác. status_questions và status_delivery_date giữ canonical_child=null, resolution_status=unresolved; flow hợp lệ vẫn chấm, child loại khỏi mẫu số canonical. Lưu raw_label, canonical_label, mapping_rule/version, resolution_status; không dùng targets để điền. Mapping mới cần căn cứ train, phê duyệt/version mới, không viết lại raw hoặc kết quả cũ.

### 4. Quy tắc Fixed Topic Classification (H1)

Pretrained embedding cục bộ, L2-normalized; score(t,u)=cosine của evidence unit u và description(t). Cosine là similarity, không phải xác suất. Với nhiều cửa sổ, score(t,u)=max cửa sổ, không cộng. Child primary chọn max child accepted dưới primary parent qua các units, tie ID; child của parent khác không được dùng chấm primary child. Làm tròn scores và margin đến 8 chữ số thập phân bằng round-half-even trước so sánh/tie; thresholds là giá trị thập phân đăng ký, không thêm epsilon tùy ý. Sắp theo score giảm dần, ID tăng dần nếu bằng nhau. s1/s2 là top-1/top-2 trên danh mục đang xét; một lớp thì margin=+infinity.

| Ưu tiên | Điều kiện unit analyzable | Quyết định |
|---|---|---|
| 1 | s1 < tau | unmatched, không accepted label |
| 2 | s1 >= tau và s1-s2 < delta | ambiguous, giữ top-2, không accepted label |
| 3 | s1 >= tau và s1-s2 >= delta | accepted đúng top-1, kể cả s2 cũng vượt tau |

Flow trước; child trong mỗi parent accepted dùng tau_child/delta_child riêng, child không đạt -> child=null/child_unresolved, không bỏ parent. Multi-label tại hội thoại/turn là hợp các flow accepted ở evidence units khác nhau có offsets riêng, không gán hai nhãn cạnh tranh cùng một span. Score của hợp dùng max evidence score. Không áp khoảng cách giữa hai nhãn từ hai span khác nhau.

Fixture điểm giả (không phải kết quả model): tau=0,50/delta=0,10; span A điểm account_access=0,80/top2=0,55, span B product_defect=0,82/top2=0,50 -> hợp hai nhãn. Một span shipping_issue=0,76/order_issue=0,73 -> ambiguous, không multi-label. s1=0,49 -> unmatched. s1=0,60/s2=0,50 -> accepted ở biên. Câu “I need a refund; I forgot my password” có hai span độc lập; câu không tách được có thể abstain hoặc chỉ nhận một nhãn, báo giới hạn trong error analysis.

Baseline Must-have: TF-IDF unigram/bigram + Logistic Regression L2, customer analyzable text ghép cấp hội thoại, vocabulary/IDF chỉ fit train tương ứng; không kế thừa scenario label xuống span. Unknown score baseline=1-max predict_proba, ngưỡng q từ dev. Similarity binary detection ở hội thoại dùng max qua units của unresolvedness score a(u)=max(tau-s1,delta-(s1-s2)); residual_flag tương đương tồn tại a(u)>0, ngoại trừ s1=tau và margin=delta được accepted. Để tránh sai biên s1<tau hoặc margin<delta phải được đánh giá trực tiếp theo bảng; a=0 không có residual. Không có analyzable unit thì novelty_score=null. Báo cả s1/cosine novelty chẩn đoán nhưng không dùng nhầm làm score quyết định margin. Primary flow classifier so sánh baseline cùng cohort; nhãn đơn ABCD không phải multi-label ground truth.

### 5. Search protocol hữu hạn và fallback (H2)

G0 đăng ký đúng hai embedding ứng viên theo thứ tự: `sentence-transformers/all-MiniLM-L6-v2`, `sentence-transformers/all-mpnet-base-v2`; khóa revision bất biến, tokenizer, giấy phép, input adapter, max_length và hash model trước đo. Đây là ứng viên, chưa biết model thắng. Không tải/cài/chạy ở giai đoạn đặc tả. Model không khả dụng/không phù hợp giấy phép/bộ nhớ được ghi unavailable, không tự thêm ứng viên sau xem điểm. Nếu cả hai không dùng được, dừng model search với resource_blocked; không tự đổi target hoặc chạy API ngoài. Mô hình đa ngôn ngữ là Advanced trong experiment mới đăng ký trước G1.

Ngân sách Must-have tối đa 4 CPU threads, RAM tiến trình 8 GiB, không yêu cầu GPU; batch embedding mặc định 32, một lần giảm xuống 8 nếu OOM. Smoke test tối đa 200 conversation train K chọn theo hash seed 42, tối đa 10 phút/model; không xem test. Tuning tổng tối đa 4 giờ wall-clock, mỗi cấu hình clustering tối đa 10 phút. Nếu RAM máy không đủ ngân sách, báo resource_blocked để quyết định riêng, không lặng lẽ dùng subset test. Ghi timeout/OOM/skipped; duyệt grid theo thứ tự tăng như dưới, không chọn thủ công sau dừng. Cấu hình đã hoàn tất được phép dùng nếu đủ metric; thiếu search coverage phải công bố. Nếu không có cấu hình hợp lệ cho thành phần bắt buộc, không qua G1.

| Thành phần | Search Must-have | Nguồn fit/chọn |
|---|---|---|
| Flow similarity | tau = 0,20..0,80 bước 0,05; delta={0;0,05;0,10;0,15}; 52 cấu hình/model | Embedding pretrained không fit ABCD; descriptions train K/ontology; chấm dev K+H_dev |
| Child similarity | Cùng grid 52, một cặp ngưỡng chung mọi child, sau khi chọn parent; không nhân grid parent-child | Dev K có child canonical, chấm end-to-end kể cả parent sai; không có mẫu -> tau_child=0,50/delta_child=0,10, calibration_state=fallback |
| Baseline | TF-IDF min_df=2/max_df=1,0/ngram=(1,2), Logistic Regression C={0,1;1;10}, max_iter=1000; q={0,35;0,50;0,65;0,80;0,95}, reject khi max_proba<q | Fit train K, chấm dev K+H_dev, tối đa 15 tổ hợp; không hội tụ ghi invalid configuration |
| UMAP | n_neighbors={5;15}, n_components={2;5}, metric=cosine, min_dist=0,0, random_state=42 | Fit mới trên routed dev pool không nhãn |
| HDBSCAN | min_cluster_size={5;10}, min_samples={1;5}, metric=euclidean, cluster_selection_method=eom | 16 tổ hợp với UMAP; support số document, không phải 5 conversation của review |
| BERTopic representation | top_n_words=10; CountVectorizer ngram=(1,2), min_df=1; loại marker và whitelist boilerplate đóng băng, nr_topics=null, không topic reduction/guidance/seed | Fit chỉ pool tương ứng; không ép số cụm theo số nhãn ẩn |

Embedding/flow selection chỉ dùng open-set dev K+H_dev: chọn cấu hình có unknown F1 >=0,60 rồi tối đa known Macro-F1. Nếu không có cấu hình đạt ràng buộc, chọn harmonic mean của known Macro-F1 và unknown F1 cao nhất, gắn dev_constraint_failed; vẫn giữ mốc nghiệm thu test, không ghi dev đạt. Tie-break: unknown F1 cao hơn, rồi model thứ tự G0, tau tăng, delta tăng. Trường hợp metric không xác định không được coi là 0 để thắng lựa chọn. Child chọn Macro-F1 canonical cao nhất, tie tau rồi delta tăng. Không thêm ngưỡng từng lớp trong Must-have. Baseline dùng cùng tiêu chí flow/unknown rồi C tăng/q tăng; score là xác suất classifier, không so trực tiếp với cosine.

Discovery chọn cấu hình trên dev routed pool bằng evaluator đã kiểm thử: tối đa harmonic mean giữa routing-adjusted coverage H_dev và macro cluster purity proxy theo conversation sets (§8). Routing-adjusted coverage = số conversation H_dev có span trong cluster không -1 / toàn dev H_dev hợp lệ. Macro cluster purity proxy là trung bình max tỷ lệ conversation có cùng scenario.flow mỗi cluster support>=5; không có cluster đủ support thì cấu hình không có discovery score hợp lệ. Dev evaluator được biết class để tính metric, model không được nhận nhãn; đây là model selection có nhãn dev, không phải hoàn toàn unsupervised selection. Các metric này chỉ là proxy, không tự xác minh novelty. Tie-break: outlier rate thấp hơn, rồi tuple (n_neighbors,n_components,min_cluster_size,min_samples) tăng dần. Không tối ưu NMI một mình hoặc chọn bằng biểu đồ đẹp.

Nếu không có cấu hình discovery hợp lệ do all-outlier/small pool, dùng tuple nhỏ nhất trong grid có run kỹ thuật hoàn tất (tuple đầu là (5,2,5,1)), đánh dấu discovery_dev_failed và giữ nguyên tham số khi test; nếu không tuple nào hoàn tất thì resource_blocked. Pool nhỏ hơn điều kiện UMAP có thể trả empty/insufficient_pool có lý do, không âm thầm giảm tham số theo label. Giới hạn n_neighbors hiệu dụng=min(registered_value,N_pool-1) chỉ cho N_pool>=3, đăng ký công thức trước G1; nếu n_components>=N_pool-1 dùng init=random, không đổi chiều để chọn kết quả. Ghi giá trị yêu cầu/hiệu dụng; N_pool<3 trả insufficient_pool. Đây là quy tắc kỹ thuật từ kích thước pool không nhãn, không phải tuning test.

Model embedding thắng từ dev K+H_dev dùng cố định cho các nhánh similarity/discovery. Sau chọn embedding/parent/baseline mới tuning child và clustering, không quay lại chọn embedding theo test hoặc discovery test. Closed-set dùng cùng embedding đã khóa; classifier baseline fit riêng train 10 flow sau G2. Ngưỡng closed-set được chọn chỉ trên dev K (H_dev/H_final không tham gia selection): tối đa Macro-F1 trên 7 known K, tie quy tắc trên; không có ràng buộc unknown trong closed-set. Description đầy đủ từ ontology được cố định trước closed-set tuning, không sửa theo lỗi. Báo calibration domain=K, không tuyên bố đã tối ưu threshold cho 10 flow. Không để closed-set feedback đổi bất cứ lựa chọn open-set nào.

### 6. Split, checkpoint và leakage audit (H5)

Giữ split gốc; mọi view/unit/window cùng conversation cùng split. Exact duplicate trên masked customer text; near-duplicate token 5-gram Jaccard>=0,90 khi >=20 token, connected components; ngắn hơn chỉ exact. Vượt split loại từ phần sớm theo giữ test>dev>train, ghi manifest không sửa raw. Không thay ngưỡng dedup sau nhìn metric. Dedup dùng text không nhãn, không fit model và công bố nguy cơ gom nhầm câu chung; không tuyên bố template/customer-disjoint hoàn toàn.

Giữ H_final={subscription_inquiry,troubleshoot_site}, H_dev={shipping_issue}, K=7 flow còn lại. Open train chỉ K; dev K+H_dev; final test K+H_final, bỏ H_dev. Counts trước lọc 5.683/802/898, báo lại sau dedup. Trusted data custodian giữ sealed test label store, chỉ áp split/hidden policy đã đăng ký để tạo membership opaque; không xem prediction hoặc cung cấp score. Đây là ngoại lệ quyền xử lý nhãn để chia dữ liệu, không phải quyền unblind: model selector/reviewer không nhận test class IDs, file names/counts theo lớp mới hoặc labels. Evaluator trước G3 chỉ chấm fixtures/train/dev; sau G3 mới join test labels với predictions. Các counts/mẫu test đã khảo sát trước đó ghi exposure log. Custodian giữ audit riêng và chỉ xuất cohort membership theo policy; inference nhận ID opaque và feature hợp lệ, không suy ra nhãn từ path/ID. Không dùng text/label H_final từ train/dev để chọn embedding, threshold, mô tả hay clustering open-set. H_dev dev chỉ làm proxy unknown, không cấp tên/ID làm seed. Full taxonomy và fitted artifacts closed-set cách ly đến sau G2.

| Gate | Điều kiện bắt buộc và artifact khóa |
|---|---|
| G0 registry/schema | Trước search: split policy, H sets, search/budget, scope Must-have/Advanced, model revisions, rubric, metric definitions, annotator access, schema và test-exposure log; chỉ smoke train K sau split/taxonomy/fixtures |
| G1 open configuration | Trước test inference: khóa split/exclusion manifest, model/preprocess/taxonomy K, tất cả ngưỡng, clustering, 3 seed 13/42/73, all-span ablation, thuật toán chọn sample/review và danh sách Advanced tham gia; evaluator/fixture phải pass |
| G2 open outputs/review | Trước đưa full taxonomy hoặc kết quả closed-set cho người/agent chọn mô hình: khóa assignments mọi seed/phương án đã đăng ký, candidate names/descriptions, representative+random sample IDs, blinded rubric/review main seed42, predictions, hashes và timestamp; technical seed13/73 và all-unit ablation seed42 ghi review_required=false, name mặc định từ keywords đã khóa, không semantic claim; review chưa xong thì pending và chưa qua gate |
| G3 global outputs | Sau G2 mới chạy closed-set riêng; khóa config closed-set đã chọn dev K và test predictions. Chỉ mở test ground truth khi mọi Must-have và Advanced đã đăng ký có output/review khóa hoặc failure artifact bất biến; cùng event mở nhãn toàn cục cho evaluator |

G3 là release test labels cho người/agent chọn mô hình, reviewer và evaluator scoring, không cấm trusted custodian đọc sealed labels chỉ để tạo membership theo policy trước đó. Nếu custodian dùng labels để lựa chọn model, xem dự đoán hoặc tiết lộ class IDs thì invalid. G2 blinded review không xem H_final taxonomy, scenario label hoặc closed-set outputs; chỉ taxonomy K và text đã mask. Người/agent đã tiếp xúc nhãn test không được tự nhận là blinded reviewer. Cần ít nhất 2 reviewer độc lập đủ điều kiện; thiếu người thì G2 pending, có thể demo kỹ thuật nhưng không complete semantic benchmark. Annotation multi-label test sau G3 thực hiện bởi reviewer khác hoặc cùng người với predictions ẩn; không quay về tuning. Log quyền đọc và input hash là bằng chứng audit, không tuyên bố một process chung tự tạo bảo mật OS tuyệt đối; nếu chưa cách ly được role thì benchmark_status=pending, không gọi blind.

Classifier inference không fit test. BERTopic fit mới trên batch routed test không nhãn với cấu hình khóa là batch_transductive, khác classifier inductive. All-span ablation cùng test span set, tham số/seed khóa, cũng transductive. Sau G3 không sửa assignment/name/merge để cải thiện test. Mở rộng sau G3 thành experiment exploratory mới, không cùng confirmatory result; không xoay H_final.

Leakage fixtures bắt buộc: (1) thay scenario/targets/candidates trên bản sao sau khóa membership không đổi feature/output; (2) inject trường cấm hoặc ID vào vectorizer -> feature_contract_violation; (3) train/dev manifest chứa H_final -> invalid; (4) reuse closed fitted model/cache chứa label -> invalid; (5) release test label trái quyền trước G3 (không tính custodian membership-only đã khai báo) hoặc full hidden taxonomy trước G2 -> invalid; (6) config/artifact hash thay sau gate -> invalid; (7) reviewer đã unblind nhưng tự ký blinded -> invalid. Run invalid giữ logs, không được dùng nghiệm thu; không sửa lịch sử để biến thành hợp lệ. Test đã khảo sát cấu trúc phải công bố, không coi cả protocol hoàn toàn blind.

### 7. BERTopic và human review (M4)

Pool chính: evidence units unmatched/ambiguous; không non_need/insufficient. Mỗi unit là một document (nếu window thì gom theo unit theo quy tắc cố định: trung bình L2-normalized window embeddings rồi L2-normalize, masked text toàn unit cho c-TF-IDF); không tạo nhiều cluster membership cho một unit vì overlap. Không nhầm min_cluster_size document với support distinct conversation>=5. All-span ablation dùng mọi analyzable unit gồm accepted để đo routing loss/mixed miss. Candidate support>=5 conversation -> proposed, nhỏ hơn -> monitor, -1 -> outlier, không tự topic mới. Empty/all-outlier xuất failure/empty artifact rõ.

Mỗi cluster: immutable cluster key, top tối đa10 keywords, count units/windows/conversations, nearest known similarity (embedding centroid cluster vs description, chỉ tham khảo), tên/mô tả tạm do người review viết. Không dùng scenario/targets để đặt tên. Review hiển thị tối đa 5 representative units gần centroid từ các conversation khác nhau (tie ID); thêm tối đa 5 random units từ conversation khác chưa có representative, theo hash(seed=42,run,cluster,unit), không thay mẫu theo câu trả lời. Nếu cluster có <10 conversation, lấy tối đa một unit mỗi conversation đến hết; lưu sampling frame, sample IDs, phương pháp và tỷ lệ. Reviewer có thể mở thêm mẫu theo quy tắc đăng ký trước G1 (thêm 5 theo hash), không cherry-pick. Preview 5 đại diện không thay thế review sample đầy đủ.

Rubric hai reviewer độc lập, chỉ thấy K và samples đã mask:

| Trục | 0 | 1 | 2 |
|---|---|---|---|
| Coherence | Không có nhu cầu chung | Nhu cầu chung nhưng nội dung hỗn tạp | Mô tả chung có ý nghĩa, >=80% sampled units được cả reviewer/adjudicator xác nhận thuộc mô tả |
| Novelty so với K | Cùng nghĩa known | Chưa đủ bằng chứng phân biệt | Khác phạm vi mọi known topic, có mô tả inclusion/exclusion và bằng chứng |

Mỗi sampled unit gắn expresses_need, fits_candidate, localized_span và known_overlap (chỉ K). accepted_novel chỉ khi support>=5, coherence=2 và novelty=2 sau adjudication; merge-to-known nếu novelty=0 và target hợp lệ; rejected khi không có nhu cầu chung hoặc bằng chứng không đủ meaningful; monitor nếu chưa chắc hoặc disagreement chưa giải quyết. Lưu reviewer IDs, rubric từng người, adjudicator/lý do, timestamp, sample_scope. Tỷ lệ >=80% tính trên tất cả sampled units, không bỏ mẫu xấu; thiếu review của một người thì pending. Merge candidate-candidate dùng target cùng run chưa retired, DAG không cycle; không tăng số topic mới vì nhiều cluster cùng nhu cầu. Trạng thái accepted_novel trong review khác status accepted của fixed classifier.

Candidate precision semantic = số proposed candidates đạt accepted_novel / toàn bộ proposed candidates có quyết định review hoàn tất, đồng thời báo reviewed_count/proposed_count và pending_count. Không tính merged-to-known là novel. Không báo tổng precision như toàn bộ corpus nếu coverage chưa đầy đủ; complete PoC review yêu cầu mọi proposed của main seed42 được xử lý, cả monitor là quyết định có lý do nhưng chưa novel. Seed13/73 và all-span ablation chỉ cần kỹ thuật/stability; không có review đầy đủ thì không tuyên bố semantic comparison hoặc recovery semantic cho chúng. Advanced so sánh semantic cần review riêng đăng ký trước.

Sampling xác minh cluster không human_verify mọi assignment: chỉ sampled span-topic được reviewer đánh dấu riêng mới verified evidence. Cụm accepted_novel có conversation_count dự đoán toàn cụm; verified counts chỉ trong reviewed scope, không extrapolate. Không có reviewer thì proxy/technical results có thể xuất nhưng semantic status và nghiệm thu tổng thể pending.

### 8. Metric grain, recovery và nghiệm thu (H3, M2, M3)

Cohort S: hội thoại không quarantine/excluded, có ít nhất một customer turn text hợp lệ sau chuẩn hóa; non_need/insufficient vẫn trong S. S_cs: S thuộc 10 flow test closed-set; S_os: S thuộc K+H_final test; S_h: S_os có scenario.flow=h. Các denominator benchmark lấy từ membership đã khóa trước nội dung dự đoán, không loại mẫu do reject/khó phân tích. Dashboard denominator điều kiện filter metadata ở §9 khác metric cohort.

| Metric | Grain / ground truth / denominator |
|---|---|
| Fixed P/R/F1, accuracy | Một conversation, primary flow vs scenario.flow; abstain tính FN. Macro trên danh sách 10 flow closed-set hoặc K open known; class support=0 trả per-class null, macro trên support>0 kèm list excluded |
| Child P/R/F1 | Một conversation canonical child có ground truth, chọn child của primary parent; sai parent/null child là sai, không chỉ chấm mẫu parent đúng. Coverage canonical là availability GT, prediction coverage báo riêng |
| Multi-label | Conversation và evidence unit trên manual labels độc lập; ABCD scenario không broadcast xuống units; số mẫu/annotation agreement công bố |
| Unseen P/R/F1 | Một conversation S_os; positive GT=H_final; prediction positive=residual_flag, mixed cũng positive; non_need/insufficient prediction negative nhưng vẫn trong denominator, FN nếu GT hidden |
| AUROC/AUPRC | Conversation S_os có analyzable score a_max tại §4; score-null loại riêng và báo score_coverage, không lặng lẽ đổi denominator của binary F1. Baseline dùng 1-max_proba và q |
| Routing recall/loss | Conversation hidden có ít nhất một routed unit / toàn S_H_final; loss=1-recall, giữ hidden gán known/no-evidence trong mẫu số |
| Cluster label purity proxy | Một cluster, distinct conversation sets với scenario label, không gán nhãn đó làm ground truth span. Báo max class share và macro qua cluster support>=5 |
| Outlier/cluster coverage | Một evidence unit/document; -1 riêng. Conversation coverage là distinct conversation có >=1 non-outlier / S của scope, không cộng số unit |
| Fragmentation | Mỗi flow h: số cluster đủ support và purity_h>=0,70, cùng số cluster có ít nhất một conversation h để thấy tách vụn |
| Contamination | Cluster/family: tỷ lệ distinct conversation không mang scenario flow h; semantic known overlap báo riêng trên sampled units |
| NMI/ARI ground-truth proxy | Một evidence unit có đúng 1 predicted cluster và scenario label của conversation chỉ dùng như proxy; loại -1, báo coverage. Không biến conversation-cluster pairs thành mẫu độc lập; không gọi đây semantic accuracy |
| Stability ARI | Cùng tập evidence_unit_id qua 3 seed; báo ARI_all với -1 là một nhãn, ARI_shared trên giao units non-outlier ở cả hai seed, shared_coverage; giao rỗng hoặc <2 non-outlier clusters -> null_reason=degenerate |
| Coherence/diversity | NPMI top10 trên cửa sổ20 token của pool đã công bố; thiếu từ/corpus -> null. Diversity=unique keywords/actual keyword entries, không mặc định10 khi thiếu từ |
| Human quality | Rubric trên unit samples, candidate precision ở §7; manual multi-label test tối đa200 conversation, hai reviewer/adjudication, predictions ẩn, không tuning |

**Flow-family recovery proxy, không ép một flow thành một cluster:** Sau G3, với mỗi hidden flow h và cluster c đủ support>=5, P_h(c)=|C_c giao S_h|/|C_c|; cluster qualifies khi P_h(c)>=0,70. Q_h là toàn bộ cluster qualifies, không chọn subset dựa recall test để làm đẹp. U_h là union C_c của Q_h; family_precision=|U_h giao S_h|/|U_h|, family_recall=|U_h giao S_h|/|S_h|; intersection được đếm một lần dù conversation nằm nhiều cluster. Flow recovered_proxy khi Q_h không rỗng, family_precision>=0,70 và family_recall>=0,30. Support, P/R, routing loss, outlier loss, fragmentation/contamination luôn xuất. Không cluster nào qualifies -> P=null/recall=0, recovered=false; S_h rỗng -> pending/no_support, không pass. Mục tiêu vẫn 2/2 ở seed42. Mapping Q_h chỉ evaluator dùng, không đổi ID/name/merge dự đoán.

**Semantic recovery riêng:** Trong Q_h chỉ lấy các cluster đã accepted_novel blinded ở G2; evaluator độc lập sau G3 đối chiếu mô tả và sampled spans đã khóa với định nghĩa h trong full ontology, ghi mapping nghĩa match/nonmatch/uncertain và lý do, không dùng scenario làm bằng chứng từng span. Tính union/P/R như trên và báo recovered_semantic_supported, cùng sample coverage. Bất đồng adjudicate, uncertain/pending không counted. Đây là assessment sau mở nhãn, không phải model output mới; không viết lại blinded names/rubric. Không có semantic review thì chỉ báo recovered_proxy, không gọi h là topic mới đã xác minh. Báo metric recovery hai tầng tránh một cụm lời xã giao thuần nhãn h được coi là novelty.

Fixture recovery: hai cluster support10 mỗi cluster, purity_h=1, thuộc hai subflow khác nhau, overlap2 conversation h, S_h=50 -> union18, precision1, recall0,36, recovered_proxy=true dù mỗi cụm chỉ0,20. Cluster label-pure nhưng samples là lời xã giao -> có thể proxy recovered nhưng semantic_supported=false. Fixture còn gồm routing miss, hai flow trộn, outlier toàn bộ và cohort h rỗng. Không thay ngưỡng 0,70/0,30/support5 hay mục tiêu2/2 sau test.

NMI/ARI ground-truth proxy chỉ báo khi có ít nhất 2 scenario classes và 2 non-outlier clusters trên tập chấm, ngược lại null/degenerate; không lấy conversation-cluster pairs làm mẫu. ARI_all có thể bằng1 khi mọi seed cùng -1 nhưng phải có degenerate=true và không coi là chất lượng; ARI_shared/coverage báo cạnh đó. Score a(u) dùng cùng scores/margin đã round8 như decision table.

Bootstrap fixed/unknown F1: 1000 resample conversation có hoàn lại từ cohort gốc, seed42, tính metric rồi percentile95% CI; không bootstrap độc lập segment, metric không xác định giữ null và báo số replicate hữu hiệu. Không bootstrap refit BERTopic để gọi đó CI clustering; seed stability là phép riêng. Manual test lấy tối đa200 conversation sau G3 theo hash(seed42,ID), phân tầng K/H_final tỷ lệ theo cohort, lấy dư theo fractional remainder/stratum ID; công bố sampling probabilities, không tuning, không khẳng định population metric nếu chưa weighting. Rubric discovery không thay manual gold multi-label.

**Mốc giữ nguyên:** closed-set Macro-F1>=0,70; open unknown F1>=0,60; routing recall>=0,70; seed42 recovered_proxy=2/2 theo family definition đã sửa. Không đạt ghi fail/error analysis, không đổi H sets/threshold/split sau test. NMI/ARI/child/multi-label/stability là diagnostic không có ngưỡng cứng. Chất lượng semantic có cột riêng: human_verified chỉ khi review hoàn tất và từng flow claimed có recovered_semantic_supported; thiếu người/pending -> tổng nghiệm thu pending, dù proxy pass. Kết luận cuối có functional_status, proxy_quality_status, semantic_status, benchmark_validity; chỉ complete PoC khi chức năng pass, mục tiêu proxy pass, semantic human_verified và validity valid_with_declared_test_exposure. Validation tài liệu không thay nghiệm thu mô hình.

### 9. Schema đầu ra, grain và vòng đời artifact (L1)

Schema_version=`1.0.0`, UTF-8; ID/string không rỗng, counts integer>=0, ratios finite float [0,1], cosine [-1,1], score_type tách cosine/decision_margin/probability; score không được ép mọi loại về [0,1]. Timestamp artifact/review UTC ISO8601, không phải thời gian hội thoại. Các artifact dưới `artifacts/<experiment_id>/<run_id>/` sau phê duyệt; không tạo trong giai đoạn đặc tả. Mỗi row JSONL/CSV có schema_version, experiment_id, run_id; manifest JSON có chính các trường đó. Mỗi metric row có cohort/grain/denominator/null_reason; counts thiếu bằng chứng không đổi thành0. Không tạo trường timestamp hội thoại từ run timestamp.

| Artifact | Khóa duy nhất trong run | Trường bắt buộc ngoài khóa |
|---|---|---|
| run_manifest.json | (experiment_id,run_id) | config_hash, source_hashes object, model_revisions object, split_manifest_hash, taxonomy_version, mapping_version, preprocessing_version, seed int, fit_scopes array, search_registry_hash, gate_events array, artifact_hashes object, benchmark_validity, resource_usage object |
| data_quality.json | (experiment_id,run_id) | counts object: read/quarantine/excluded/eligible, reason_counts object, unresolved_counts object, metadata_availability object, alignment_ablation_failures; reason groups không chồng để đối soát |
| segments.jsonl | segment_id | conversation_id string, source_split enum train/dev/test, evidence_unit_id, customer_turn_index int0-based, span_start/end int0-based code points, masked_customer_text, content_status, preprocessing_version; context fields nullable |
| assignments.jsonl | (evidence_unit_id,topic_id,source) | conversation_id, segment_ids array, score float/null, score_type, assignment_status, evidence_spans array objects, evidence_status enum model_supported/human_verified/cluster_only, cluster_key nullable |
| conversation_topics.csv | (conversation_id,topic_id,source,evidence_basis) | primary_topic bool, max_score nullable, evidence_count nullable int, taxonomy_version; một cặp không bị nhân bởi windows/turns |
| topic_statistics.csv | (scope_id,topic_id,source,evidence_basis) | customer_message_count, source_messages_with_assignment, segment_count, mention_count nullable, conversation_count, eligible_conversations, conversation_share nullable, evidence_coverage float, unique_customers/time_bucket/channel nullable, null_reason nullable |
| candidates.jsonl | cluster_key | seed, local_cluster_id int>=0, keywords array, representative_unit_ids array, random_unit_ids array, conversation_support int, label/description nullable string, status proposed/accepted_novel/merged/rejected/monitor, review_version int |
| reviews.jsonl | (cluster_key,review_version) | reviewer_ids array, rubric_scores object, sample_ids array, per_sample_judgements array, adjudication nullable object, target_id nullable, reason nonempty, reviewed_at UTC; không nhúng ground truth test trước G3 |
| metrics.json | (metric_name,cohort_id,level,seed,evaluation_stage) | value number/null, support int, denominator int/null, grain string, CI array/null, null_reason, experiment_mode inductive/batch_transductive, ground_truth_type scenario_proxy/manual_gold/review_sample |
| report.md | Một file/run | Cấu hình, gates/exposure/leakage audit, proxy+semantic status, metrics/support, error analysis, resources, hạn chế và các phần pending |

topic_id của discovery=`candidate:<run_id>:<seed>:<local_cluster_id>`, cluster_key=(experiment_id,run_id,seed,local_cluster_id) serialize bằng `:` với thành phần ID chỉ dùng [A-Za-z0-9_-]. -1 chỉ là outlier assignment, cluster_key=null, không tạo candidates row; dùng topic_id=null trong unresolved/outlier log thuộc segments, không tạo assignment topic giả. Lặp run khác run_id luôn có key khác dù local ID trùng. Không tái dùng ID candidate retired, không coi local ID giữa seed là cùng topic. Topic known giữ namespace §3.

CSV dùng RFC4180 quoting, null token `\N` (một backslash rồi chữ N), literal string đúng token đó bị từ chối như reserved_value, không có escape tùy implementation; empty string chỉ hợp lệ trường string cho phép, không là null. JSON/JSONL dùng null thật; không NaN/Infinity. Array/object chỉ ở JSONL/JSON, không nhét list tùy ý vào CSV. `null_reason` bắt buộc nếu metric/value tùy chọn không có, ví dụ missing_localized_evidence, unreviewed_scope, unavailable_metadata, empty_scope, no_support, degenerate. Unknown schema major hoặc vi phạm type/key/foreign-key/hash -> schema_error, dashboard không render như run hợp lệ. Thay optional field tương thích tăng minor, đổi grain/meaning tăng major; artifact cũ dùng reader đúng version, không âm thầm reinterpret.

Scope: eligible_conversations = |S| sau metadata filters run/experiment/split (time/channel chỉ khi thật có); lọc topic/source/review_status chỉ lọc numerator, không đổi denominator thành tập đã mang topic. customer_message_count là tổng turn khách của scope, lặp rõ ở các topic rows; source_messages_with_assignment là subset theo topic. evidence_basis=predicted/verified/cluster_membership tách hàng. Verified scope chỉ gồm conversation đã review toàn bộ unit cần thiết, công bố scope membership và coverage so S; partial sample không xuất tổng verified conversation/mention cho toàn S. Không có evidence localizable thì mention null, segment/conversation membership vẫn xuất dưới predicted hoặc cluster_membership. conversation_share=count/denominator cùng declared scope, denom0 -> null; tổng các topic có thể>100%. unique_customers/time_bucket/channel null với ABCD; không dùng tên/email giả, purchase_date hoặc source_split làm trend/customer/channel.

G1/G2/G3 event là append-only, mỗi event có snapshot config và hashes các artifact đã tồn tại. run_manifest.json còn draft tới seal cuối evaluation; chỉ được append gate_events/artifact_hashes mới, không sửa entry/snapshot đã khóa. Hash snapshot và chuỗi event được audit thay vì đòi hash toàn manifest draft không đổi khi thêm metric artifact hợp lệ; sau seal toàn manifest bất biến. Fixture mutation phân biệt append event hợp lệ với sửa snapshot cũ. Trước gate, file draft có thể sửa; sau gate, dự đoán/cluster/sample/name đã khóa bất biến. Review mới sau G3 là review_version mới thuộc exploratory report/view, không sửa blinded_version hoặc metric confirmatory. Merge targets chỉ known topic taxonomy version hợp lệ hoặc candidate cùng run; graph DAG, cấm self/cycle/cross-run, ghi old->target và reason; aggregate reviewed view lấy union conversation-turn-topic sau resolve target, không cộng fixed và candidate đã merge trùng. Promote accepted candidate chỉ ở taxonomy version mới/run tương lai; không ghi lại lịch sử. Run failure/invalid được giữ cùng log và status, không overwrite run_id để chạy lại test giả như lần đầu.

Dashboard Must-have gồm tổng quan chất lượng/số đếm, fixed topics, candidates/review, evaluation và export; không fit khi mở. Hiển thị basis predicted/verified/cluster_membership, ground_truth_type, inductive/transductive, test exposure, pending và invalid. Drill-down customer evidence masked đúng offsets, không lộ label store đang khóa. Export cùng filter/scope/schema phải khớp bảng. Review UI ghi reviews version mới, không ghi đè output khóa. Trend/customer/channel vô hiệu và giải thích khi thiếu metadata.

### 10. Traceability xử lý review và kiểm tra nhất quán

| Review | Quyết định | Capability / nhóm tasks |
|---|---|---|
| H1 | Unit decision table, margin, hợp span độc lập, fixture biên/multi-demand | fixed-topic-classification / 4,5 |
| H2 | Hai model, grid/budget/objective/tie/fallback, dev-only | topic-evaluation / 1,4,5 |
| H3 | Family union proxy, semantic mapping riêng, giữ ngưỡng | topic-evaluation + new-topic-discovery / 4,6,9 |
| H4 | Evidence offsets/basis, count phân biệt, null khi thiếu | conversation-preparation + topic-analytics-dashboard / 2,3,8 |
| H5 | G0–G3, global barrier, immutable outputs, invalid fixtures | topic-evaluation / 1,4,7,9 |
| M1 | Schema/evaluator/fixture trước tuning; open khóa trước closed | tasks / 1..9 |
| M2 | Grain/unit/outlier/score coverage, ARI_all/shared | topic-evaluation / 4,6,9 |
| M3 | State table, cohorts S/S_cs/S_os, residual flag | conversation-preparation + fixed-topic-classification / 2,4,5 |
| M4 | Hai reviewer, rubric, random+representative, proxy/semantic | new-topic-discovery / 4,6,7 |
| L1 | Schema1.0.0, keys, null, version, merge DAG | topic-analytics-dashboard / 1,8,10 |

## Risks / Trade-offs

- [ABCD nhãn kịch bản đơn] -> Flow/subflow chỉ proxy; manual annotations và semantic review riêng, không gán ground truth xuống mọi span.
- [Một sentence nhiều nhu cầu chưa tách] -> Báo error mode và all-span ablation; không gọi Must-have là giải quyết hoàn hảo semantic splitting.
- [Max evidence score thiên hội thoại dài] -> Báo F1/routing theo số evidence units (1,2–5,>5), không đổi aggregation theo test; length-normalized model là Advanced experiment mới.
- [Model pretrained có thể từng thấy dữ liệu công khai] -> Chỉ bảo đảm không thích nghi H_final trong PoC, không chứng minh pretraining-disjoint; ghi model provenance.
- [Một proxy unknown dev có thể không đại diện final] -> Giữ giới hạn nghiên cứu, không xoay H_final hay chọn seed đẹp; bộ ngoài chưa xem cần cho kết luận tổng quát.
- [Human review tốn công hoặc thiếu người] -> Sampling cố định, tài liệu rubric/roles; semantic pending chặn kết luận hoàn tất chứ không bịa chất lượng.
- [Masker bỏ sót hoặc mất ngữ nghĩa] -> Train fixtures/audit và hạn chế PII rõ, evidence offsets trên masked text; không public raw.
- [Ngẫu nhiên/tài nguyên] -> Seed/revision/budget và fallback đăng ký trước; resource_blocked/failed công khai, không đổi target.

## Migration Plan

Chỉ sửa 9 tài liệu hiện có trong change; .openspec.yaml/config/raw/overview không đổi. Thực thi sau yêu cầu mới theo tasks; không archive bây giờ. Kết quả phiên bản cũ giữ reader và manifest tương ứng; rollback bằng chọn run cũ, không sửa dữ liệu gốc hoặc rewrite metrics. Checkpoint thất bại phải được xử lý trước đi tiếp.

## Open Questions

- Model thắng, thời gian/RAM và đạt các mục tiêu hay không cần thực nghiệm theo search protocol, không quyết định trước hoặc bảo đảm trong đặc tả.
- Reviewer cụ thể chưa được phân công; quy tắc đủ điều kiện và fallback pending đã chốt, không được bỏ review để hoàn tất.
- Mapping hai nhãn unresolved chờ bằng chứng train/phê duyệt; default null đã xác định nên không chặn flow benchmark.
- Framework dashboard chọn trong thực thi, không đổi contract; giấy phép nguồn/model phải xác minh trước dùng/phân phối. Không khả dụng thì resource/license_blocked, không tự đổi model ngoài registry.
- Tiếng Việt cần corpus/annotation, tokenizer/embedding/slang riêng; audio cần ASR/diarization/speaker-role và WER/CER cùng tác động topic F1, đều ngoài Must-have hiện tại.



