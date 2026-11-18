# Hướng dẫn Khám phá Chủ đề Mới (Discovery), Đánh giá Chuyên gia và Quy tắc Hợp nhất (Merge DAG)

Tài liệu này quy định quy trình trích xuất routed pool, chạy phân cụm UMAP/HDBSCAN, thiết lập hàng chờ đánh giá mù (blinded review), phân công 2 chuyên gia và xác thực hợp nhất cây DAG.

## 1. Trích xuất Routed Pool

- **Tiêu chí vào Pool**:
  - Chỉ nhận các evidence units có trạng thái `analyzable` và được fixed classifier gắn quyết định `unmatched` hoặc `ambiguous`.
  - Tuyệt đối loại bỏ các span `non_need` (lời chào, cảm ơn, PII-only) và `insufficient_evidence` (từ rời rạc yes/no).
- **Đại diện Document**:
  - Mỗi evidence unit là một document.
  - Nếu span dài có nhiều cửa sổ 200 token: Vector embedding của unit được tính bằng trung bình L2-normalized của các window embeddings, sau đó L2-normalize lại. Không nhân số lượng cluster membership theo số cửa sổ.
- **Kích thước Pool**:
  - $N_{pool} \ge 3$: Tiến hành tìm kiếm cấu hình phân cụm. Tham số $n\_neighbors$ hiệu dụng được giới hạn:
    $$n\_neighbors_{effective} = \min(n\_neighbors_{registered}, N_{pool} - 1)$$
  - Nếu $n\_components \ge N_{pool} - 1$: Áp dụng `init = 'random'`.
  - Nếu $N_{pool} < 3$: Xuất trạng thái `insufficient_pool`. Nếu $N_{pool} = 0$: Xuất `empty_pool`.

## 2. Lưới Tham số 16 Cấu hình UMAP + HDBSCAN

- **UMAP**:
  - $n\_neighbors \in \{5, 15\}$
  - $n\_components \in \{2, 5\}$
  - $metric = 'cosine'$, $min\_dist = 0.0$, $random\_state = 42$
- **HDBSCAN**:
  - $min\_cluster\_size \in \{5, 10\}$
  - $min\_samples \in \{1, 5\}$
  - $metric = 'euclidean'$, $cluster\_selection\_method = 'eom'$
- **Tiêu chí Chọn Cấu hình**:
  - Tối đa hóa trung bình điều hòa giữa Routing-adjusted coverage $H_{dev}$ và Macro cluster purity proxy.
  - Phá vỡ hòa điểm: Outlier rate thấp hơn $\rightarrow$ tuple tăng dần.
  - Fallback: $(5, 2, 5, 1)$ kèm cờ `discovery_dev_failed = True`.

## 3. Tạo Ứng viên (Candidate Representation)

- Cụm ngoại lai (nhãn $-1$): Được theo dõi dưới dạng outlier, **không tạo bản ghi candidate**.
- Ngưỡng hỗ trợ (Support): Tính theo **số cuộc hội thoại phân biệt** (`conversation_support`):
  - $\ge 5$ cuộc hội thoại $\rightarrow$ Đạt điều kiện `status = "proposed"`.
  - $< 5$ cuộc hội thoại $\rightarrow$ Đưa vào giám sát `status = "monitor"`.
- Định danh bất biến: `cluster_key = "candidate:<run_id>:<seed>:<local_cluster_id>"`.

## 4. Quy trình Đánh giá Mù (Blinded Review Pipeline)

- **Chọn mẫu đại diện (Sampling Frame)**:
  - Tối đa 5 units gần centroid nhất từ các cuộc hội thoại khác nhau.
  - Tối đa 5 units ngẫu nhiên (chọn theo hàm băm `hash(seed=42, run_id, cluster_key, unit_id)`) từ các hội thoại còn lại chưa có đại diện.
  - Tổng số mẫu tối đa 10 units không trùng cuộc hội thoại.
- **Điều kiện Chuyên gia (Reviewer Requirements)**:
  - Bắt buộc tối thiểu **2 chuyên gia độc lập** đủ điều kiện.
  - **Quy tắc cách ly mù**: Chuyên gia chỉ được tiếp cận danh mục Known $K$ và nội dung text đã khử PII. Tuyệt đối không được xem nhãn kịch bản $H_{final}$, ontology đầy đủ hoặc kết quả closed-set trước cổng G2.
  - Nếu thiếu chuyên gia hoặc chưa hoàn tất đánh giá: Trạng thái ngữ nghĩa ghi nhận `semantic_status = "pending"`, không được kết luận PoC hoàn tất.
- **Trạng thái Chấp thuận Chủ đề Mới (`accepted_novel`)**:
  - Yêu cầu đồng thời: `conversation_support >= 5`, `Coherence = 2` ($\ge 80\%$ samples xác nhận thuộc mô tả chung), và `Novelty = 2` (khác biệt rõ rệt toàn bộ $K$).
  - Nếu `Novelty = 0`: Gán trạng thái `merged` với topic $K$ tương ứng.

## 5. Xác thực Đồ thị Hợp nhất (Merge DAG Validator)

- Hợp nhất candidate với topic $K$ hoặc candidate khác trong cùng run phải tuân thủ cấu trúc đồ thị có hướng không chu trình (DAG).
- Nghiêm cấm hợp nhất chính mình ($A \rightarrow A$).
- Nghiêm cấm chu trình ($A \rightarrow B \rightarrow A$).
- Nghiêm cấm trỏ mục tiêu sang run khác.
- Lượt xem tổng hợp đã hợp nhất sử dụng distinct union, không đếm trùng hội thoại mang cả topic gốc lẫn topic đích.
