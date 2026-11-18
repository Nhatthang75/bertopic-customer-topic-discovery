# Định nghĩa Metrics, Grain, Rubric và Bảng Ánh xạ Kiểm thử

Tài liệu này quy định chi tiết định nghĩa các thước đo đánh giá, cấp độ phân giải (grain), xử lý giá trị rỗng (`null_reason`), rubric đánh giá con người và bảng ánh xạ từ Requirements của 6 Specs sang các Test Fixtures đã kiểm chứng.

## 1. Bảng Định nghĩa Metrics và Grain

| Metric | Grain / Cấp độ | Ground Truth | Mẫu số (Denominator) | Quy tắc xử lý rỗng / Biên |
|---|---|---|---|---|
| **Fixed Macro-F1 / P / R** | Cấp cuộc hội thoại | `scenario.flow` | Tập $S_{cs}$ hoặc $S_{os}$ known | Abstain tính là False Negative (FN). Lớp không có mẫu trong tập trả `null`. |
| **Child F1 / Accuracy** | Cấp cuộc hội thoại | `scenario.subflow` | Tập hội thoại có canonical child | Tính end-to-end: nếu parent sai hoặc child không đạt ngưỡng/margin $\rightarrow$ tính là sai subflow. |
| **Unknown F1 / P / R** | Cấp cuộc hội thoại | Cờ $h \in H_{final}$ | Toàn bộ tập $S_{os}$ | Prediction là `residual_flag` (gồm cả `mixed`). `non_need` và `insufficient_evidence` có prediction=False nhưng vẫn nằm trong mẫu số (tính FN nếu thuộc hidden). |
| **Flow-family Recovery Proxy** | Cấp hidden flow $h$ | Danh sách hội thoại $S_h$ | Toàn bộ $|S_h|$ | $Q_h$ gồm các cluster có support $\ge 5$ và purity $\ge 0,70$. Đạt khi có cluster qualify, family precision $\ge 0,70$ và family recall $\ge 0,30$. |
| **Semantic Recovery** | Cấp hidden flow $h$ | Ontology định nghĩa $h$ | Các cluster $Q_h$ | Chỉ xét các cluster đạt `accepted_novel` ở đánh giá mù G2, đối chiếu nghĩa độc lập sau G3. |
| **Clustering Stability ARI** | Cấp evidence unit | Cùng tập ID qua 3 seed | Giao units non-outlier | Báo `ARI_all` (outlier -1 là 1 nhãn) và `ARI_shared` kèm `shared_coverage`. Toàn bộ outlier $\rightarrow$ `null_reason: 'degenerate_all_outliers'`. |

## 2. Rubric Đánh giá Chuyên gia (Human Rubric)

Áp dụng cho 2 chuyên gia đánh giá độc lập trên tập mẫu 5 đại diện + 5 ngẫu nhiên không trùng hội thoại:

| Trục đánh giá | Mức 0 | Mức 1 | Mức 2 |
|---|---|---|---|
| **Độ mạch lạc (Coherence)** | Không có nhu cầu chung nào có thể nhận diện | Có nhu cầu chung nhưng nội dung hỗn tạp hoặc lẫn lộn | Mô tả nhu cầu chung rõ ràng; $\ge 80\%$ các sample units được xác nhận thuộc mô tả |
| **Tính mới so với K (Novelty)** | Cùng ý nghĩa với một topic đã biết trong $K$ | Chưa đủ bằng chứng để phân biệt chắc chắn với $K$ | Hoàn toàn khác biệt phạm vi của mọi topic trong $K$, có tiêu chí bao gồm/loại trừ |

- **Kết luận Cụm**:
  - `accepted_novel`: support $\ge 5$ hội thoại, Coherence = 2, Novelty = 2.
  - `merged`: Novelty = 0 và có topic $K$ tương ứng.
  - `rejected`: Coherence = 0 hoặc nội dung không mang nhu cầu khách hàng.
  - `monitor`: support $< 5$ hoặc bất đồng chưa được hội đồng phân xử (adjudication).

## 3. Bảng Ánh xạ Requirement sang Test Fixture (6 Specs)

| Capability / Spec | Yêu cầu cốt lõi | Test File & Fixture cụ thể | Trạng thái |
|---|---|---|---|
| **conversation-preparation** | Đọc nguồn nguyên vẹn, hash SHA-256 bất biến, cách ly role/nhãn | `test_data.py`: `test_full_abcd_counts_and_hashes`, `test_read_ontology_and_hashes` | **PASS** |
| | PII Masker, NFC normalization, giữ nguyên phủ định/giá/sản phẩm | `test_data.py`: `test_masker_pii_and_semantic_preservation` | **PASS** |
| | Tách span theo câu/chấm phẩy, token window 200/overlap 20 | `test_data.py`: `test_spans_sentence_and_semicolon`, `test_evidence_tokenizer_and_windows` | **PASS** |
| | Phân loại trạng thái nội dung (non_need, insufficient, analyzable) | `test_data.py`: `test_content_status_rules` | **PASS** |
| | Dedup và xử lý cross-split theo ưu tiên test > dev > train | `test_data.py`: `test_dedup_cross_split_priority` | **PASS** |
| **topic-taxonomy** | Cấu trúc 10 flow / 55 subflow, namespace rõ ràng | `test_taxonomy_and_cohorts.py`: `test_taxonomy_10_55_structure` | **PASS** |
| | Chuẩn hóa alias theo ontology, giữ unresolved cho nhãn lệch | `test_taxonomy_and_cohorts.py`: `test_alias_resolution` | **PASS** |
| | Phân lập danh mục Known K và kiểm soát quyền truy cập Full Taxonomy | `test_taxonomy_and_cohorts.py`: `test_known_vs_full_isolation` | **PASS** |
| **fixed-topic-classification** | Decision table ($\tau = 0,50, \delta = 0,10$), phân biệt accepted/ambiguous/unmatched | `test_evaluator_and_fixtures.py`: `test_decision_table_fixtures` | **PASS** |
| | Abstain tính là FN, không loại mẫu khỏi mẫu số | `test_evaluator_and_fixtures.py`: `test_fixed_classification_and_abstain_is_fn` | **PASS** |
| | Multi-label hợp từ các span độc lập, không gán 2 nhãn cạnh tranh trên cùng 1 span | `test_evaluator_and_fixtures.py`: `test_decision_table_fixtures` | **PASS** |
| **new-topic-discovery** | Chọn mẫu 5 đại diện + 5 ngẫu nhiên không trùng conversation | `test_evaluator_and_fixtures.py`: `test_rubric_and_sample_selection` | **PASS** |
| | Rubric Coherence/Novelty, tiêu chí accepted_novel và merged | `test_evaluator_and_fixtures.py`: `test_rubric_and_sample_selection` | **PASS** |
| | ARI stability qua seed và xử lý suy biến all-outliers | `test_evaluator_and_fixtures.py`: `test_clustering_stability_and_degenerate` | **PASS** |
| **topic-evaluation** | Flow-family recovery proxy: hợp các cụm đạt chuẩn, không ép 1 flow = 1 cụm | `test_evaluator_and_fixtures.py`: `test_flow_family_recovery_fixture` | **PASS** |
| | Đánh giá Unknown detection, residual_flag và score coverage | `test_evaluator_and_fixtures.py`: `test_unknown_detection_metrics` | **PASS** |
| | Bootstrap 95% CI ở cấp độ hội thoại | `test_evaluator_and_fixtures.py`: `test_bootstrap_ci_conversation_level` | **PASS** |
| | Bắt lỗi rò rỉ (leakage): early labels, reviewer unblinded, role vi phạm | `test_evaluator_and_fixtures.py`: `test_leakage_and_audit_fixtures` | **PASS** |
| **topic-analytics-dashboard** | 4 đơn vị đếm phân biệt (message, segment, mention, conversation) | `test_taxonomy_and_cohorts.py`: `test_four_counting_units` | **PASS** |
| | Roll-up từ subflow lên flow dùng distinct union | `test_taxonomy_and_cohorts.py`: `test_roll_up_distinct_union` | **PASS** |
| | Bộ lọc topic không làm sai lệch mẫu số `eligible_conversations` | `test_taxonomy_and_cohorts.py`: `test_topic_filter_and_null_rules` | **PASS** |
| | Tuân thủ Schema 1.0.0, unique keys, null token và validation | `test_foundation.py`: `test_contract_types_versions_and_keys`, `test_csv_round_trip` | **PASS** |

> [!NOTE]
> Toàn bộ 4 nhóm tiền đề (Nhóm 1–4) đã hoàn thành và đạt 100% các bài kiểm thử trước khi tiến hành bước tiếp theo (tìm kiếm và tuning mô hình ở Nhóm 5–6).
