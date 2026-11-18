# Proposal

## Why

PoC cần chứng minh khả năng nhận diện danh mục đã biết, khám phá nhu cầu chưa có bằng BERTopic và thống kê hội thoại có bằng chứng. Review trước xác định các khoảng trống về quyết định đa nhãn, recovery, mention và leakage; lần sửa này làm rõ hợp đồng và nghiệm thu trước khi lập trình.

## What Changes

- Giữ pipeline batch offline ABCD: customer là bằng chứng, agent là context tùy chọn, action và metadata nhãn không vào feature.
- Giữ 10 flow/55 subflow; alias có căn cứ, nhãn mơ hồ giữ unresolved, topic khác intent/action.
- Phân loại từng evidence span bằng similarity và margin; nhiều nhãn chỉ được hợp từ các span độc lập accepted, không biến hai nhãn cạnh tranh thành multi-label.
- Chốt search protocol hữu hạn trên train/dev được phép, gồm model, threshold, baseline và clustering; có ngân sách và fallback công khai.
- Tách unseen detection, routing, flow-family recovery proxy và chất lượng cluster do con người xác minh. Một flow có thể được phục hồi qua hợp nhiều cluster; giữ các ngưỡng chất lượng đã đăng ký.
- Phân biệt customer_message_count, segment_count, mention_count và conversation_count; mention chưa có evidence đủ điều kiện là null, không ghi là đã xác minh.
- Thêm checkpoint khóa cấu hình, output và review toàn cục trước mở test label; không dùng kết quả closed-set để chỉnh open-set.
- Quy định schema_version, grain, khóa, null, artifact bất biến và dashboard chỉ đọc kết quả đã xuất.

### Phạm vi Must-have

Sáu capability bên dưới đều bắt buộc: chuẩn bị dữ liệu; taxonomy; Fixed Topic Classification; BERTopic New Topic Discovery; thống kê/export/dashboard demo; đánh giá và audit. Bắt buộc có baseline TF-IDF, ba seed discovery, kiểm tra routing trên toàn bộ span hợp lệ và human review có rubric. Thiếu reviewer được phép xuất kỹ thuật với semantic_status=pending nhưng không kết luận novelty đã kiểm chứng hoặc hoàn tất nghiệm thu PoC.

### Optional / Advanced

Zero-shot BERTopic, context agent, delexed ablation, threshold từng lớp, fine-tuning và thí nghiệm ẩn subflow là mở rộng, không chặn nghiệm thu Must-have. Các mở rộng tác động mô hình chỉ chạy nếu đăng ký trước G1 và có ngân sách riêng; không được xem test rồi quyết định bổ sung vào cùng benchmark. Không đưa triển khai Advanced vào checklist bắt buộc.

### Phạm vi và giới hạn

“Nhu cầu” là topic khách đề cập, không phải intent mua hàng/cảm xúc/chuyển đổi. ABCD có nhãn kịch bản chính cấp hội thoại, không có multi-label ground truth mọi turn. Hiện chỉ đặc tả tiếng Anh dạng text; không ASR, diarization, realtime, CRM hay cam kết tiếng Việt/audio. Thiếu timestamp/customer ID/channel thì unavailable, không bịa dữ liệu.

H_final={subscription_inquiry,troubleshoot_site}, H_dev={shipping_issue} giữ nguyên. Các mục tiêu flow Macro-F1 >=0,70, unknown F1 >=0,60, routing recall >=0,70, recovery 2/2 với precision >=0,70, recall >=0,30 và support >=5 hội thoại được giữ nguyên; recovery đổi từ một cluster sang flow-family union có kiểm soát vì review phát hiện sai khác cấp độ. Không có kết quả mô hình nào được dùng để sửa ngưỡng.

Change này chỉ sửa tài liệu hiện có. Chưa viết code, cài thư viện AI, chạy mô hình, xây dashboard hay thực hiện apply; dữ liệu raw nguyên vẹn. Chỉ thực thi sau yêu cầu mới.

## Capabilities

### New Capabilities

- `conversation-preparation`: Nguồn chỉ đọc, privacy, evidence span, trạng thái nội dung và provenance.
- `topic-taxonomy`: Taxonomy phân cấp, alias, version và danh mục theo experiment.
- `fixed-topic-classification`: Quyết định span rõ ràng, hợp nhiều nhãn, rejection và phân cấp.
- `new-topic-discovery`: BERTopic, routing, bằng chứng cluster và review có rubric.
- `topic-evaluation`: Evaluator trước tuning, search protocol, checkpoint leakage, metric và nghiệm thu.
- `topic-analytics-dashboard`: Schema đầu ra, thống kê có evidence và dashboard demo.

### Modified Capabilities

Không có main capability sẵn; tiếp tục sửa các ADDED Requirements trong change hiện tại, không tạo change mới.

## Impact

Chỉ sửa proposal, design, tasks và 6 specs của change này; không sửa config, overview hoặc nguồn dữ liệu. Thực thi tương lai tạo artifacts riêng trong workspace theo run/experiment/schema version. Overview vẫn là tài liệu định hướng; design hiện tại chốt các lựa chọn PoC và công bố test đã từng được khảo sát cấu trúc, không phải blind benchmark hoàn toàn.
