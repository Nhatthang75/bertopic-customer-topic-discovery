# Thực thi giai đoạn 1: registry và chuẩn bị dữ liệu

Dùng đúng `.venv\Scripts\python.exe` (Python3.11), không dựa PATH. Codex sandbox có thể không đọc được Python gốc; xin approval riêng cho từng lệnh cần chạy ngoài sandbox. Không sửa ACL/PATH. Source xử lý chỉ ghi dưới workspace, raw luôn chỉ đọc. Mọi thư mục tạm của tests nằm trong workspace. Dependency trực tiếp duy nhất là tokenizers0.22.1 để đọc chính tokenizer.json đã khóa; không cài torch, transformers, BERTopic, không tải weights.

Thứ tự: registry/policy/schema -> metadata lock -> foundation tests/G0 -> reader/masking/dedup/evidence -> data tests -> prepare artifacts. Các tasks3–10 chưa được thực thi. G0 chỉ là đăng ký protocol, không cho phép model search/test scoring; G1 cần evaluator/taxonomy ở giai đoạn sau. Các registry/schema/environment artifacts không phải kết quả mô hình.

Lệnh kiểm thử: `.venv\Scripts\python.exe -m unittest discover -s tests -v`.
Lệnh xuất dữ liệu: `.venv\Scripts\python.exe scripts/prepare_phase1.py --run-id preparation_v1`.
Các lệnh đọc dữ liệu không gửi hội thoại ra mạng. Chỉ `scripts/lock_models.py` truy cập Hugging Face để khóa metadata công khai, không đọc raw; không chạy lại để thay revision sau G0. Model selection chưa thực hiện. requirements-phase1.lock ghi versions đã cài, environment_manifest ghi interpreter và giới hạn kiểm chứng.

Quyền truy cập là ranh giới API ứng dụng, không phải sandbox bảo mật hệ điều hành. Inference không được đọc raw/ontology/labels. Custodian mới được đọc raw/ontology; reader chỉ chuyển original/ID/split/alignment ra feature preparation, không chuyển scenario, targets, candidates. Policy mặc định chặn test label trước G3, full taxonomy trước G2 và reviewer không blinded. Đây là fixture và nền tảng cho gates; chưa có evaluator hoặc inference model.

Hai reviewer độc lập là điều kiện xác minh semantic novelty. Người đã biết hidden labels không được coi blinded. Thiếu người hoặc cách ly role chưa đủ phải pending, không ghi benchmark blind/pass. Test đã từng được khảo sát cấu trúc nên protocol không hoàn toàn blind.

Preprocessing v1: NFC, chuẩn hóa khoảng trắng ngang, giữ newline; mask email/phone/address/ID/tên từ lexicon PII công khai của ontology.values (không scenario, không nhãn flow/subflow). Masking là rule-based, có thể bỏ sót tên mới/địa chỉ lạ; không tuyên bố ẩn danh tuyệt đối. Chỉ customer tạo evidence; agent/action không tạo feature. delexed chỉ kiểm tra alignment; không chạy ablation tùy chọn.

Offsets là Unicode code point trên masked turn NFC; [start,end), không là byte hoặc offset raw. Span tách câu/chấm phẩy/newline, giữ decimal và abbreviation whitelist. 200 text tokens không gồm special tokens, overlap20, tokenizer theo revision; ghi riêng view chuẩn bị cho từng tokenizer, không chọn model. non_need/insufficient theo exact toàn span; không xóa Hello trong câu mang nhu cầu.

Dedup: exact casefold/space-normalized masked customer text; gần trùng khi >=20 Unicode word tokens, Jaccard5-gram>=0,90 theo connected components. Prefix filtering tìm candidate rồi so sánh chính xác, không MinHash. Vượt split giữ mọi record ở split cao nhất test>dev>train, loại các split sớm hơn; nhóm chỉ trong một split vẫn giữ và báo riêng. Không tuyên bố customer/template-disjoint hoàn toàn.

Schema contract v1 được máy đọc từ schemas/artifacts-1.0.0.json và validate bằng bertopic_poc.contracts: required fields/types, unique keys và references truyền vào rõ ràng; JSON null khác empty string; CSV RFC4180 dùng reserved token `\N`. Row evidence được kiểm thêm provenance và feature allowlist. Schemas cho artifact tương lai chỉ là hợp đồng, chưa có producer/evaluator/dashboard cho nhóm3 trở đi.

Artifacts phase1 gồm registry snapshot/environment, split/exclusion/quarantine manifests, masked customer turns và segments theo tokenizer, data_quality và run_manifest. Không có taxonomy đầy đủ/labelstore/dự đoán/topic statistics. Unresolved label counts ghi chưa đánh giá ở nhóm2, không tự làm mapping nhóm3. Log quarantine chỉ ghi split/index/lý do, không raw PII. Data source hashes trước/sau phải khớp hoặc run invalid.
