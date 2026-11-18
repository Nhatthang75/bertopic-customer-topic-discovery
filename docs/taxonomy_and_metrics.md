# Hướng dẫn Taxonomy, Alias và 4 Đơn vị Đếm Thống kê

Tài liệu này quy định cấu trúc danh mục, nguyên tắc chuẩn hóa alias, phân biệt chủ đề với ý định/hành động, và phương pháp tính toán 4 đơn vị đếm trong PoC.

## 1. Cấu trúc Taxonomy 10 Flow / 55 Subflow

Hệ thống biểu diễn cấu trúc 2 tầng xuất phát từ ontology ABCD:
- **Tầng Flow (10 danh mục)**:
  - Known $K$ (7 flows): `account_access`, `manage_account`, `order_issue`, `product_defect`, `purchase_dispute`, `single_item_query`, `storewide_query`.
  - Hidden dev $H_{dev}$ (1 flow): `shipping_issue`.
  - Hidden final $H_{final}$ (2 flows): `subscription_inquiry`, `troubleshoot_site`.
  - Định danh định dạng: `flow:<flow_name>` (ví dụ: `flow:account_access`).
- **Tầng Subflow (55 danh mục chuẩn)**:
  - Định danh có namespace cha: `subflow:<flow_name>/<subflow_name>` (ví dụ: `subflow:shipping_issue/status`).
  - Tránh hoàn toàn xung đột tên con giữa các nhánh khác nhau.
- **Phân lập danh mục**:
  - Open-set model và reviewer mù chỉ được tiếp cận danh mục $K$ trước cổng G2.
  - Toàn bộ danh mục 10 flow và các subflow ẩn được cách ly nghiêm ngặt cho đến sau G2.

## 2. Nguyên tắc Chuẩn hóa Alias và Trạng thái Unresolved

- **Căn cứ Ontology**: Chỉ chuẩn hóa các FAQ alias có membership trong `ontology.values.enumerable` và khớp đúng flow cha:
  - `single_item_query`: `<item>_how_<n>` và `<item>_other_<n>` ($n \in \{1..4\}$) chuẩn hóa về `<item>` (boots, shirt, jeans, jacket).
  - `storewide_query`: `<category>_<n>` ($n \in \{1..4\}$) chuẩn hóa về `<category>` (pricing, membership, timing, policy).
- **Cấm đoán**: Tuyệt đối không fuzzy matching, không tự ý cắt đuôi số lạ (ví dụ: `timing_99` bị gán `unresolved`).
- **Nhãn lệch Ontology**:
  - `subscription_inquiry/status_questions`
  - `order_issue/status_delivery_date`
  - Giữ nguyên `canonical_child = null` và `resolution_status = "unresolved"`. Không dùng `targets` của delexed để đoán bù.

## 3. Phân biệt Topic, Intent và Action

- **Nhu cầu khách hàng (Topic)**: Là chủ đề cụ thể mà khách hàng đề cập trong lượt nói của mình.
- **Ý định (Intent)**: Intent nghiệp vụ độc lập được để `null` khi chưa có annotation chuyên biệt; không đồng nhất dataset intent với intent kinh doanh.
- **Hành động (Action)**: Các hành động của agent (`action` turns) hoặc metadata action trong ABCD **không phải là bằng chứng** cho nhu cầu khách hàng. Không được suy luận chủ đề hoặc tạo mention chỉ từ action.
- **Giới hạn nhãn kịch bản (Scenario)**: Nhãn `scenario` trong ABCD là nhãn kịch bản cấp toàn bộ cuộc hội thoại, **không phải là gold label cho mọi turn/span**. Không được broadcast nhãn kịch bản xuống từng span làm ground-truth.

## 4. Bốn Đơn vị Đếm Thống kê (Counting Units)

1. **`customer_message_count`**:
   - Tổng số lượt nói hợp lệ của khách hàng (`role == 'customer'`), gồm cả lời chào và PII.
   - Không tính lượt nói của agent hoặc action.
   - Thể hiện quy mô tương tác của khách hàng trong scope.
2. **`segment_count`**:
   - Số lượng đoạn text (span hoặc token window $\le 200$) có gán nhãn chủ đề.
3. **`mention_count`**:
   - Số lượt đề cập cục bộ xác định: distinct `(conversation_id, customer_turn_index, topic_id)` có bằng chứng định vị (`localized_evidence`).
   - Yêu cầu `evidence_basis` là `predicted` (model_supported) hoặc `verified` (human_verified).
   - Nếu topic chỉ có `cluster_membership` mà chưa có span cụ thể $\rightarrow$ `mention_count = null` với `null_reason: "missing_localized_evidence"`.
   - Nếu mới chỉ kiểm chứng một phần scope $\rightarrow$ `verified mention_count = null` với `null_reason: "unreviewed_scope"`, tuyệt đối không ngoại suy (extrapolate).
4. **`conversation_count`**:
   - Số cuộc hội thoại phân biệt mang chủ đề trong scope.
   - Khi tổng hợp (roll-up) từ subflow lên flow cha, bắt buộc dùng **distinct union** các cuộc hội thoại, không cộng tổng số học để tránh đếm trùng.

## 5. Mẫu số và Bộ lọc (Denominator & Filtering)

- Mẫu số `eligible_conversations` được xác định theo metadata scope của tập dữ liệu (các hội thoại hợp lệ không bị loại bỏ bởi quarantine/dedup).
- **Bộ lọc chủ đề (Topic Filter)**: Khi người dùng lọc xem một topic $X$, chỉ tử số `conversation_count` thay đổi, mẫu số `eligible_conversations` **giữ nguyên**.
  - Ví dụ: Trong 100 hội thoại có 20 hội thoại về $X$, tỷ lệ `conversation_share` luôn là $20/100 = 20\%$, không bao giờ biến thành $20/20 = 100\%$.
- **Thiếu metadata**: `unique_customers`, `time_bucket`, `channel` được ghi nhận `null` đối với tập dữ liệu ABCD vì nguồn không cung cấp thông tin này đáng tin cậy.
