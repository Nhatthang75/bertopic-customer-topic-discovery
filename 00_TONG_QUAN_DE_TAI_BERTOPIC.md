# TỔNG QUAN ĐỀ TÀI
## Phân tích nhu cầu khách hàng từ hội thoại bằng BERTopic và khám phá chủ đề mới

> **Loại tài liệu:** Tài liệu nghiên cứu định hướng (overview / study guide), **chưa phải** đặc tả yêu cầu, thiết kế chính thức hay kế hoạch triển khai đã được phê duyệt.  
> **Phiên bản:** 1.0 — 03/11/2026  
> **Đối tượng đọc:** Người mới nghiên cứu BERTopic, có nền tảng Data Science / AI; người trao đổi yêu cầu nghiệp vụ với doanh nghiệp.  
> **Trạng thái:** Giả thuyết ban đầu; cần làm rõ yêu cầu và cấu trúc dữ liệu thực tế.

---

## Mục lục

1. [Bối cảnh và mục tiêu](#1-bối-cảnh-và-mục-tiêu)
2. [Bài toán thực sự cần giải quyết](#2-bài-toán-thực-sự-cần-giải-quyết)
3. [Bộ thuật ngữ quan trọng](#3-bộ-thuật-ngữ-quan-trọng)
4. [BERTopic là gì, hoạt động thế nào?](#4-bertopic-là-gì-hoạt-động-thế-nào)
5. [Fixed topic, guided topic, zero-shot và topic mới](#5-fixed-topic-guided-topic-zero-shot-và-topic-mới)
6. [Dữ liệu đầu vào: chat và cuộc gọi](#6-dữ-liệu-đầu-vào-chat-và-cuộc-gọi)
7. [Đơn vị phân tích và bài toán nhiều chủ đề](#7-đơn-vị-phân-tích-và-bài-toán-nhiều-chủ-đề)
8. [Kiến trúc bài toán từ đầu đến cuối](#8-kiến-trúc-bài-toán-từ-đầu-đến-cuối)
9. [Các phương án kỹ thuật có thể lựa chọn](#9-các-phương-án-kỹ-thuật-có-thể-lựa-chọn)
10. [Quy trình phát hiện và xác minh chủ đề mới](#10-quy-trình-phát-hiện-và-xác-minh-chủ-đề-mới)
11. [Kết quả và thống kê doanh nghiệp quan tâm](#11-kết-quả-và-thống-kê-doanh-nghiệp-quan-tâm)
12. [Đánh giá chất lượng hệ thống](#12-đánh-giá-chất-lượng-hệ-thống)
13. [Công nghệ và nơi thao tác](#13-công-nghệ-và-nơi-thao-tác)
14. [Lộ trình học và nghiên cứu](#14-lộ-trình-học-và-nghiên-cứu)
15. [Rủi ro, hiểu lầm và những điều không nên làm](#15-rủi-ro-hiểu-lầm-và-những-điều-không-nên-làm)
16. [Có nên dùng OpenSpec để đặc tả không?](#16-có-nên-dùng-openspec-để-đặc-tả-không)
17. [Những câu cần xác nhận với sếp](#17-những-câu-cần-xác-nhận-với-sếp)
18. [Danh sách nguồn đọc chính thức](#18-danh-sách-nguồn-đọc-chính-thức)
19. [Kết luận và định hướng chốt](#19-kết-luận-và-định-hướng-chốt)

---

## 1. Bối cảnh và mục tiêu

### 1.1. Bối cảnh giả định

Doanh nghiệp có những cuộc trao đổi giữa **nhân viên tư vấn** và **khách hàng** trên một hoặc nhiều kênh: website, chatbot, Messenger, Zalo, email, tổng đài điện thoại, v.v.

- Với **chat**, đầu vào thường đã là văn bản.
- Với **cuộc gọi**, có thể cần chuyển audio thành văn bản (speech-to-text / ASR) và phân biệt ai đang nói.
- Doanh nghiệp có thể đã có **danh mục chủ đề hiện hữu**: giá, sản phẩm, giao hàng, khuyến mãi, bảo hành, thanh toán, v.v.
- Yêu cầu mới có thể là **phân tích khách hàng nói về gì**, **thống kê tần suất**, và **phát hiện nhu cầu/chủ đề chưa có trong danh mục**.

**Lưu ý:** Chưa biết doanh nghiệp thực tế thuộc ngành nào, có bao nhiêu topic và cung cấp dữ liệu ở cấu trúc nào. Mọi ví dụ bên dưới đều là dữ liệu giả định, không phải yêu cầu đã xác nhận.

### 1.2. Cách diễn đạt bài toán trong một câu

> Nghiên cứu giải pháp NLP/Topic Modeling cho hội thoại tư vấn nhằm nhận diện các chủ đề có sẵn, khám phá các nhóm nhu cầu mới phát sinh, thống kê theo khách hàng/cuộc hội thoại/thời gian và cung cấp bằng chứng để người phụ trách nghiệp vụ xác minh.

### 1.3. Những câu hỏi doanh nghiệp muốn trả lời

1. Khách hàng nhắc đến các chủ đề nào?
2. Các chủ đề phổ biến nhất là gì?
3. Một khách/câu/cuộc trò chuyện có đề cập nhiều chủ đề không?
4. Có những chủ đề nào chưa nằm trong danh mục hiện có?
5. Mỗi chủ đề mới xuất hiện trong bao nhiêu đoạn text, bao nhiêu cuộc hội thoại, bao nhiêu khách duy nhất?
6. Chủ đề có tăng/giảm theo tuần, tháng hay chiến dịch không?
7. Có đủ bằng chứng để thêm chủ đề mới vào danh mục chính thức không?

### 1.4. Kết quả nghiên cứu nên hướng tới

Một **PoC** có thể chứng minh:

- Đọc dữ liệu text đã chuẩn hóa.
- Tách và phân tích nội dung khách hàng, có xét ngữ cảnh khi cần.
- Đối chiếu với taxonomy (danh mục chủ đề cố định).
- Gom nhóm các nội dung chưa được giải thích tốt.
- Đưa ra các **ứng viên chủ đề mới**, kèm ví dụ và số liệu.
- Cho phép người phân tích rà soát, chấp nhận/gộp/từ chối đề xuất.
- Xuất bảng và biểu đồ cơ bản.

Không nhất thiết phải triển khai thành sản phẩm production ngay từ đầu.

---

## 2. Bài toán thực sự cần giải quyết

Đề tài nghe như “học BERTopic”, nhưng về mặt AI có **nhiều bài toán khác nhau**:

| Bài toán | Câu hỏi | Phương pháp phù hợp |
|---|---|---|
| **Topic classification** | Đoạn này thuộc chủ đề có sẵn nào? | Rule-based, embedding similarity, zero-shot classification hoặc supervised classifier |
| **Topic discovery** | Trong kho text có những nhóm nội dung lặp lại nào? | BERTopic / clustering |
| **Novel topic discovery** | Nhóm nào không khớp với danh mục đã có? | Phát hiện phần chưa khớp + clustering + kiểm duyệt |
| **Multi-label classification** | Một đoạn nhắc đến nhiều chủ đề nào? | Multi-label classifier hoặc tách theo ý nghĩa rồi tổng hợp |
| **Intent detection** | Khách định làm gì? | Intent classifier / information extraction |
| **Trend analytics** | Nhu cầu biến đổi ra sao theo thời gian? | Gom nhóm theo timestamp, chuẩn hóa tỷ lệ và phân tích chuỗi thời gian |
| **Speech processing** | Làm sao biến cuộc gọi thành text có phân biệt người nói? | ASR + speaker diarization |

**Điểm mấu chốt:** BERTopic hữu ích nhất cho **khám phá và mô tả chủ đề**, nhưng **không mặc nhiên giải quyết tốt mọi bài toán phân loại đa nhãn, nhận diện ý định mua hàng hoặc đọc đúng ngữ cảnh hội thoại**.

### 2.1. Chủ đề khác gì ý định?

Câu: “Máy này bảo hành 12 tháng đúng không?”

- **Topic:** Bảo hành.
- **Intent:** Xác nhận chính sách bảo hành.

Câu: “Máy vừa mua bị hỏng, tôi cần đổi ngay.”

- **Topic:** Sản phẩm lỗi / đổi trả / hậu mãi (phụ thuộc taxonomy).
- **Intent:** Yêu cầu đổi sản phẩm / khiếu nại.

Câu: “Có giảm giá thêm không? Tôi chốt hôm nay.”

- **Topic:** Giá / khuyến mãi.
- **Intent:** Thương lượng giá / sẵn sàng mua.

Nếu sếp muốn **nhu cầu** theo nghĩa “mục đích cần giải quyết”, có thể cần thêm phân loại **intent** bên cạnh **topic**.

### 2.2. Chủ đề khác gì sản phẩm?

“iPhone 17”, “laptop”, “máy lọc nước” có thể là **thực thể/sản phẩm** (entity), không nhất thiết là tên topic. Một cấu trúc phân tích giàu thông tin hơn có thể là:

`topic = giá` + `product = laptop` + `intent = hỏi giá` + `channel = chat`.

---

## 3. Bộ thuật ngữ quan trọng

| Thuật ngữ | Giải nghĩa ngắn | Mức độ quan trọng |
|---|---|---|
| NLP | Xử lý ngôn ngữ tự nhiên | Rất cao |
| Document | Đơn vị văn bản đưa vào mô hình | Rất cao |
| Corpus | Tập hợp các document | Cao |
| Text embedding | Vector biểu diễn ngữ nghĩa của text | Rất cao |
| Cosine similarity | Độ tương đồng của hai vector | Rất cao |
| Clustering | Gom nhóm không cần nhãn sẵn | Rất cao |
| BERTopic | Thư viện topic modeling dùng embeddings và cách biểu diễn topic qua c-TF-IDF | Rất cao |
| Taxonomy | Danh mục / hệ thống phân loại chủ đề chính thức | Rất cao |
| Fixed / predefined topic | Topic đã được định nghĩa trước | Rất cao |
| Guided / seeded topic modeling | Dùng seed để định hướng quá trình tạo topic | Cao |
| Zero-shot topic modeling | Dùng mô tả topic có sẵn để đối chiếu mà không cần huấn luyện trên bộ nhãn của riêng doanh nghiệp | Rất cao |
| Novel / emerging topic | Chủ đề mới so với danh mục hiện có, có thể đang nổi lên | Rất cao |
| Multi-label | Một đơn vị văn bản có nhiều nhãn | Rất cao |
| Topic drift | Sự thay đổi ý nghĩa/chủ đề hoặc cách mô tả qua thời gian | Trung bình |
| Outlier | Document không thuộc cụm rõ ràng | Cao |
| Ground truth | Tập nhãn do người xác minh | Rất cao |
| Precision / Recall / F1 | Thước đo đánh giá nhận diện nhãn | Rất cao |
| Human-in-the-loop | Con người tham gia kiểm duyệt quyết định | Rất cao |
| ASR / Speech-to-Text | Chuyển giọng nói thành text | Khi có audio |
| Diarization | Phân biệt các người nói trong audio | Khi có audio |
| PoC | Chứng minh tính khả thi của ý tưởng | Cao |

**Về cụm “fix topic” sếp nhắc đến:** Có thể là **fixed topic**, cũng có thể sếp đang nói đến **seed topic**, **zero-shot topic** hoặc quy trình **gán topic cố định**. Chưa đủ căn cứ để khẳng định sếp định dùng thuật toán cụ thể nào. Cần xác nhận yêu cầu nghiệp vụ trước.

---

## 4. BERTopic là gì, hoạt động thế nào?

### 4.1. Ý tưởng cơ bản

BERTopic giúp tìm các nhóm văn bản có ý nghĩa tương đồng và mô tả mỗi nhóm bằng từ khóa đặc trưng. Quy trình mặc định thường gồm:

```text
Tập văn bản (documents)
        |
        v
Embedding model (chuyển text thành vectors)
        |
        v
UMAP (giảm số chiều, theo cấu hình mặc định)
        |
        v
HDBSCAN (phân cụm, theo cấu hình mặc định)
        |
        v
c-TF-IDF (tìm các từ tiêu biểu của từng cụm)
        |
        v
Danh sách topic + từ khóa + document đại diện
```

Đây là **pipeline mặc định phổ biến**, không phải kiến trúc bắt buộc: BERTopic cho phép thay thế embedding, giảm chiều, phân cụm và topic representation.

### 4.2. Các thành phần chính

**Embedding model:** Biến các câu như “Có đóng góp hàng tháng được không?” và “Cửa hàng hỗ trợ trả góp chứ?” thành vector gần nhau hơn khi nghĩa tương đồng. Chất lượng embedding rất quan trọng với tiếng Việt.

**UMAP:** Giảm chiều vector để hỗ trợ phân cụm; tính ngẫu nhiên có thể khiến kết quả khác nhau khi chạy lại nếu chưa kiểm soát seed và môi trường.

**HDBSCAN:** Tìm những nhóm văn bản có mật độ tương đồng cao, có thể để lại các điểm không rõ nhóm thành **outlier**.

**c-TF-IDF:** Tìm các từ/cụm từ thể hiện đặc trưng của từng cụm. Nó giúp **mô tả** topic; không đồng nghĩa với việc hiểu chính xác nhu cầu nghiệp vụ.

**Topic representation / labeling:** Sau khi tìm cụm, hệ thống hoặc người phân tích có thể đặt tên dễ hiểu như “Hỏi trả góp”. Tên tự sinh cần được rà soát.

### 4.3. Những kết quả BERTopic có thể trả về

- Topic ID và document nào thuộc topic nào.
- Số document từng topic.
- Từ khóa mô tả và ví dụ đại diện.
- Bảng thông tin topic và document.
- Biểu đồ các topic, mức tương đồng, biểu diễn theo thời gian.
- Ước lượng phân bố topic trong document thông qua phương pháp hậu xử lý `approximate_distribution()`.

Lưu ý: `approximate_distribution()` không phải một bộ phân loại đa nhãn đã được hiệu chỉnh sẵn cho taxonomy doanh nghiệp.

### 4.4. Topic `-1` có nghĩa gì?

Trong pipeline dùng HDBSCAN, `-1` thường là **outlier**: văn bản chưa được gán vào cụm nào đủ rõ. **Không kết luận `-1` là topic mới.** Có thể do văn bản ngắn, nhiễu, riêng lẻ, sai ASR hoặc đúng là một nhu cầu mới nhưng chưa có đủ mẫu để tạo cụm.

---

## 5. Fixed topic, guided topic, zero-shot và topic mới

### 5.1. Fixed / predefined topics

Là danh mục được doanh nghiệp xác định trước và có mã ổn định. Ví dụ giả lập:

| topic_code | topic_name | Định nghĩa khái quát |
|---|---|---|
| T01 | Giá | Khách hỏi giá, mức phí, chi phí |
| T02 | Tư vấn sản phẩm | Khách cần thông số, tính năng, so sánh |
| T03 | Khuyến mãi | Khách hỏi voucher, ưu đãi |
| T04 | Giao hàng | Phí vận chuyển, thời gian, phạm vi |
| T05 | Bảo hành | Chính sách, thời hạn, quy trình bảo hành |
| T06 | Thanh toán | Hình thức thanh toán, trả góp |

**Cần quản lý rõ:** ID, tên, mô tả, ví dụ thuộc topic, ví dụ **không** thuộc topic, topic cha/con nếu có, trạng thái sử dụng và phiên bản danh mục.

### 5.2. Guided / seeded BERTopic

Dùng danh sách từ khóa theo từng chủ đề để **định hướng** BERTopic (tham số `seed_topic_list`). Mô hình được “gợi ý” nhưng **không bảo đảm** mọi nhóm seed xuất hiện chính xác như taxonomy, hay không bị tách/gộp. Vì vậy, guided BERTopic không phải sự thay thế trực tiếp cho bộ phân loại fixed topic có hợp đồng nhãn cứng.

### 5.3. Zero-shot BERTopic

Có thể cung cấp `zeroshot_topic_list` là các tên/mô tả chủ đề. Những document đủ tương đồng có thể được gán theo chủ đề có sẵn; phần chưa đủ tương đồng tiếp tục đi vào bước clustering. Độ bao phủ phụ thuộc `zeroshot_min_similarity` và embedding model.

**Cần nhớ:**

- Mô tả topic tốt thường hữu ích hơn những tên quá ngắn hoặc mơ hồ.
- Ngưỡng similarity **phải hiệu chỉnh bằng dữ liệu thật**, không có giá trị “đúng” cho mọi mô hình.
- Nếu ngưỡng thấp: nhiều văn bản vào fixed topic nhưng tăng nguy cơ gán nhầm.
- Nếu ngưỡng cao: nhiều văn bản đi sang nhánh khám phá; có thể bỏ sót các fixed topic.
- Dữ liệu có nhiều nhu cầu trên cùng đoạn phải được xử lý riêng, vì một lần gán topic chính không giải quyết đầy đủ multi-label.

### 5.4. Unsupervised discovery

Cho BERTopic chạy **không có danh mục ban đầu** để xem các nhóm nào tự xuất hiện. Hữu ích để nhìn rộng hơn và phát hiện điểm mù của taxonomy, nhưng có rủi ro tạo quá nhiều cụm, lặp chủ đề hoặc cụm thiên về ngôn ngữ của nhân viên.

### 5.5. So sánh phương pháp

| Phương án | Điểm mạnh | Hạn chế | Khi nên thử |
|---|---|---|---|
| Embedding similarity với taxonomy | Dễ giải thích, có danh mục nhãn cố định | Ngưỡng khó chuẩn; nhiều nghĩa dễ nhầm | Baseline ban đầu |
| Multi-label supervised classifier | Hiệu quả khi có tập gán nhãn chất lượng | Cần dữ liệu gán nhãn | Khi đã có dữ liệu đủ tốt |
| Guided BERTopic | Tạo cụm có định hướng | Seed không cố định cứng kết quả | Nghiên cứu khám phá có hướng |
| Zero-shot BERTopic | Kết hợp danh mục sẵn và khám phá chưa khớp | Cần kiểm tra ngưỡng và trường hợp đa nhãn | Rất đáng thử trong PoC |
| Unsupervised BERTopic | Khám phá rộng, không cần nhãn | Kết quả phải diễn giải và gộp/tách | So sánh/khám phá toàn bộ |
| Hybrid classification + discovery | Rõ trách nhiệm từng phần, hỗ trợ multi-label | Nhiều thành phần cần đánh giá | Kiến trúc mục tiêu có triển vọng |

**Khuyến nghị nghiên cứu:** Không mặc định một thuật toán duy nhất sẽ đáp ứng cả hai mục tiêu “nhãn cố định chính xác” và “tìm ra nhu cầu mới”. Hãy so sánh **zero-shot BERTopic** với **hybrid: fixed-topic classification + BERTopic discovery**.

---

## 6. Dữ liệu đầu vào: chat và cuộc gọi

### 6.1. Hình thức dữ liệu có thể được giao

- `CSV`, `XLSX`: file tin nhắn/hội thoại.
- `JSON`/`JSONL`: bản ghi hội thoại có metadata.
- Database/API/export từ phần mềm CRM, helpdesk.
- Audio (`wav`, `mp3`, ...) hoặc bản transcript từ tổng đài.

Chưa biết định dạng thật; **không nên thiết kế cứng pipeline trước khi xem một mẫu đã ẩn thông tin cá nhân**.

### 6.2. Dữ liệu theo từng tin nhắn — ví dụ giả lập

| conversation_id | message_id | role | timestamp | text |
|---|---|---|---|---|
| C001 | M001 | customer | 2026-10-01 09:00 | Máy này giá bao nhiêu? |
| C001 | M002 | agent | 2026-10-01 09:01 | Dạ giá 12 triệu ạ. |
| C001 | M003 | customer | 2026-10-01 09:02 | Có hỗ trợ trả góp không? |
| C002 | M004 | customer | 2026-10-02 10:00 | Giao hàng đến tỉnh được không? |

Các trường quan trọng:

| Trường | Ý nghĩa | Mức độ |
|---|---|---|
| `conversation_id` | Nhận diện và tổng hợp cuộc trò chuyện | Nên bắt buộc cho thống kê theo hội thoại |
| `message_id` | Nhận diện tin nhắn, tránh trùng dữ liệu | Nên có |
| `role` | Khách/nhân viên/bot/hệ thống | Rất quan trọng nếu muốn biết **nhu cầu của khách** |
| `text` | Nội dung phân tích | Bắt buộc cho mô hình text |
| `timestamp` | Diễn biến thời gian | Cần nếu phân tích xu hướng |
| `customer_id` | Đếm số khách duy nhất | Tùy chọn, phải bảo vệ riêng tư |
| `channel` | Website/Messenger/Zalo/hotline... | Tùy chọn |
| `agent_id` | Nhân viên tư vấn | Tùy chọn |
| `language` | Ngôn ngữ / tiếng Việt pha tiếng Anh | Tùy chọn |

Nếu chỉ có một cột `text`, vẫn có thể chạy BERTopic, nhưng không thể suy ra đáng tin cậy “bao nhiêu cuộc hội thoại” hoặc “bao nhiêu khách duy nhất”.

### 6.3. Với audio

```text
Audio
  -> ASR / Speech-to-Text
  -> Speaker diarization (phân biệt người nói, nếu cần)
  -> Gán speaker vào vai trò khách / nhân viên
  -> Transcript có timestamp
  -> Tiền xử lý và phân tích như dữ liệu chat
```

Điểm cần lưu ý: ASR có thể sai số, tên sản phẩm, tên riêng, từ địa phương và tiếng Việt pha tiếng Anh. Speaker diarization chỉ phân biệt các nguồn giọng nói, **không tự bảo đảm** xác định đúng người nào là khách. Phải đo lỗi và kiểm tra phương thức ánh xạ speaker -> role.

### 6.4. Tiền xử lý có chủ đích

- Bỏ hoặc chuẩn hóa phần hệ thống, bot, lời chào lặp lại khi không liên quan.
- Phát hiện nội dung rỗng, trùng lặp, spam.
- Giữ những ký hiệu quan trọng cho nghiệp vụ: giá, số lượng, mẫu sản phẩm, các từ “0%”, “trả góp”.
- Xử lý viết tắt: “ko”, “k”, “ib”, “ship”, “bh”, ... bằng quy tắc đã kiểm thử.
- Ẩn thông tin cá nhân trước khi phân tích, nhất là khi chia sẻ dữ liệu để nghiên cứu.
- Có thể dùng tách từ tiếng Việt cho bước trích từ khóa, **không mặc định** phải tách từ theo cùng một cách cho mọi embedding model.

### 6.5. Đánh giá độ phù hợp của dữ liệu

Cần biết: bao nhiêu bản ghi, tỷ lệ rỗng, tỷ lệ thiếu role, thiếu timestamp, số hội thoại, độ dài trung bình, tỷ lệ chat vs audio, số ngôn ngữ, trùng lặp, phần trăm đoạn quá ngắn, khoảng thời gian thu thập, phạm vi cho phép sử dụng.

---

## 7. Đơn vị phân tích và bài toán nhiều chủ đề

### 7.1. Ba mức phân tích

1. **Message-level:** mỗi tin nhắn là một đơn vị; giữ rõ ai nói nhưng câu ngắn dễ thiếu ngữ cảnh.
2. **Utterance / semantic segment:** nhóm một hoặc vài phát biểu thành đoạn mang đủ ý nghĩa; thường thích hợp để phát hiện nhu cầu.
3. **Conversation-level:** cả cuộc hội thoại; thuận tiện cho báo cáo nhưng dễ có **nhiều chủ đề** trong một document.

Đề xuất ban đầu: **xử lý ở mức phát biểu/đoạn mang ý nghĩa, sau đó tổng hợp theo `conversation_id`**. Khi câu quá ngắn, bổ sung ngữ cảnh trước/sau có kiểm soát.

### 7.2. Ví dụ một câu có nhiều topic

> “Cho mình hỏi giá bao nhiêu, có trả góp 0% không, mua hôm nay thì bao lâu nhận hàng?”

Nhãn có thể là: `Giá`, `Thanh toán / trả góp`, `Giao hàng`.

Nếu chỉ gán một topic chính, hai trong ba nhu cầu bị bỏ sót. Do đó nên đánh giá **multi-label**, hoặc tách đoạn theo ý nghĩa rồi gán nhãn và gộp kết quả.

### 7.3. Phân biệt lời nhân viên và nhu cầu khách

Nếu nhân viên tự giới thiệu “bên em có trả góp, bảo hành, freeship” trong mọi cuộc chat, thống kê toàn bộ text sẽ khiến các topic này tăng giả tạo. Cần xác định rõ:

- Chỉ phân tích nội dung khách nói?
- Hay phân tích cả hai nhưng ghi rõ `speaker_role`?
- Khi nhân viên nhắc lại nhu cầu của khách, có coi đó là bằng chứng không?

Để trả lời **nhu cầu khách**, ưu tiên lấy phát biểu khách làm nguồn chính; ngữ cảnh nhân viên chỉ dùng hỗ trợ giải nghĩa khi cần.

---

## 8. Kiến trúc bài toán từ đầu đến cuối

```text
             [CHAT TEXT]                [AUDIO]
                  |                        |
                  |                  ASR + diarization
                  |                        |
                  +------------+-----------+
                               |
                    Data validation / privacy
                               |
                  Chuẩn hóa role, thời gian,
                  hội thoại, đoạn mang ý nghĩa
                               |
                    Text embeddings (vi)
                               |
                      +--------+--------+
                      |                 |
               NHÁNH A              NHÁNH B
          Fixed-topic matching   Topic discovery
          / multi-label model    (BERTopic/clustering)
                      |                 |
           Topic hiện có       Ứng viên topic mới
                      |                 |
                      +--------+--------+
                               |
                Rà soát mẫu + đối chiếu taxonomy
                               |
               Thống kê theo đoạn / conversation
                  / khách / kênh / thời gian
                               |
                  CSV / Báo cáo / Dashboard
```

Đây là **kiến trúc tham khảo**, chưa phải thiết kế bắt buộc. Nếu dùng **zero-shot BERTopic**, một số bước đối chiếu topic có sẵn và clustering có thể diễn ra trong cùng một quy trình. Tuy nhiên, vấn đề **multi-label** và **phê duyệt chủ đề mới** vẫn phải được thiết kế riêng.

### 8.1. Đầu vào và đầu ra ở mức khái niệm

**Đầu vào:** dữ liệu hội thoại text có metadata, danh mục topic có sẵn, tùy chọn thời gian, thông tin kênh và vai trò người nói.

**Đầu ra kỳ vọng:**

- Bảng `segment -> topics` (có thể nhiều nhãn).
- Bảng `conversation -> topics` (tổng hợp, không đếm trùng).
- Danh sách `new_topic_candidates` với tên tạm, ví dụ, tần suất.
- Bảng thống kê chủ đề theo thời gian / kênh.
- Báo cáo đánh giá mô hình so với dữ liệu gán nhãn.

---

## 9. Các phương án kỹ thuật có thể lựa chọn

### Phương án A — Baseline: so khớp embedding với danh mục

1. Viết mô tả rõ cho từng topic có sẵn.
2. Tạo embeddings cho đoạn văn bản và mô tả topic.
3. Tính similarity, áp ngưỡng/điều kiện gán nhãn.
4. Ghi nhận những đoạn khó phân loại vào nhóm xem xét.

Ưu điểm: dễ giải thích, dễ quan sát lỗi; có thể hỗ trợ multi-label nếu đánh giá được ngưỡng cho từng nhãn. Nhược điểm: phụ thuộc chất lượng mô tả và embedding, thiếu ngữ cảnh và có thể nhầm các topic gần nhau.

### Phương án B — Unsupervised BERTopic

Chạy trên dữ liệu khách hàng hoặc phần dữ liệu chưa khớp danh mục; khám phá nhóm mới rồi đối chiếu thủ công. Không nên coi số cụm thu được là số lượng chủ đề nghiệp vụ thực.

### Phương án C — Zero-shot BERTopic

Đưa mô tả topic có sẵn vào mô hình, phần còn lại được phân cụm. Phù hợp để thử nhanh ý tưởng “topic có sẵn + khám phá mới” nhưng cần kiểm tra kỹ false positive, ngưỡng similarity, multi-label và độ ổn định.

### Phương án D — Hybrid được đề xuất để nghiên cứu sâu

Kết hợp **bộ phân loại cố định (có thể đa nhãn)** với **BERTopic discovery**. Những đoạn thiếu độ tin cậy, không đủ nhãn, hoặc được chọn qua kiểm tra chất lượng đi vào nhánh khám phá. Các cụm mới phải qua kiểm duyệt của con người.

**Tại sao nên benchmark thay vì chọn luôn D?** Vì phương án tối ưu phụ thuộc lượng dữ liệu, ngành nghề, chất lượng taxonomy, yêu cầu độ chính xác và tài nguyên thực thi.

### 9.1. Gợi ý về embeddings tiếng Việt

Có thể so sánh một mô hình multilingual gọn nhẹ với các mô hình multilingual mạnh hơn (chẳng hạn dòng multilingual-e5 hoặc BGE-M3), miễn phù hợp giấy phép, tài nguyên và chính sách dữ liệu. Không có mô hình nào bảo đảm tốt nhất cho tất cả các cuộc chat tiếng Việt, đặc biệt với slang, lỗi chính tả và nội dung rất ngắn.

### 9.2. Các tham số ảnh hưởng lớn

| Tham số/điểm thiết kế | Ảnh hưởng |
|---|---|
| Embedding model | Chất lượng biểu diễn ý nghĩa |
| Document/segment granularity | Mức độ ngữ cảnh vs đa topic |
| UMAP settings | Cấu trúc dữ liệu sau giảm chiều, độ ổn định |
| HDBSCAN `min_cluster_size` / `min_samples` | Kích thước cụm, số outlier |
| BERTopic `min_topic_size` | Kích thước topic tối thiểu theo cấu hình |
| `zeroshot_min_similarity` | Tỷ lệ gán predefined topic vs đi clustering |
| Vectorizer/tokenizer | Chất lượng từ khóa đại diện, quan trọng với tiếng Việt |
| Topic descriptions | Chất lượng so khớp fixed topics |
| Version của taxonomy | Khả năng so sánh kết quả theo thời gian |

Tất cả cần được đo bằng tập đánh giá; tránh điều chỉnh theo cảm giác vì “nhìn biểu đồ đẹp”.

---

## 10. Quy trình phát hiện và xác minh chủ đề mới

### 10.1. Chủ đề mới được định nghĩa thế nào?

Một chủ đề chỉ nên gọi là **mới so với taxonomy hiện hành** khi:

- Nội dung của nó **khác về mặt nghiệp vụ** so với các nhãn đã có.
- Có đủ ví dụ thuộc cùng một nhu cầu có thể giải thích được.
- Không đơn thuần là từ đồng nghĩa/cách nói mới của một topic sẵn có.
- Có độ phổ biến hoặc tác động kinh doanh đáng quan tâm **theo tiêu chí doanh nghiệp quyết định**.

**Một cụm tự sinh của BERTopic ≠ một chủ đề mới đã được công nhận.**

### 10.2. Quy trình đề xuất

1. Gom các đoạn chưa phù hợp với taxonomy hoặc có độ tin cậy thấp.
2. Phân cụm để tìm nội dung lặp lại.
3. Xem từ khóa và tối thiểu một tập mẫu đại diện mỗi cụm.
4. Kiểm tra trùng với fixed topic, trùng với ứng viên khác và các lỗi dữ liệu.
5. Đặt **tên tạm** kèm mô tả bằng ngôn ngữ nghiệp vụ.
6. Đếm số đoạn / số hội thoại / số khách duy nhất, tránh nhầm các đơn vị.
7. Đo mức tăng theo thời gian nếu có timestamp.
8. Chuyển cho người phụ trách quyết định `accept / merge / reject / monitor`.
9. Nếu được duyệt, cập nhật taxonomy theo phiên bản; không âm thầm sửa toàn bộ số liệu cũ.

### 10.3. Ví dụ minh họa — không phải dữ liệu công ty

| Ứng viên topic | Số cuộc hội thoại chứa topic | Ví dụ ngắn | Nhận định |
|---|---:|---|---|
| Thu cũ đổi mới | 127 | “Có nhận máy cũ trừ tiền không?” | Cần kiểm tra đã thuộc chính sách ưu đãi hay chưa |
| Thuê thiết bị ngắn hạn | 63 | “Có thể thuê 3 ngày không?” | Có thể là nhu cầu mới |
| Hỗ trợ chuyển dữ liệu | 35 | “Mua máy mới có chuyển dữ liệu giúp không?” | Cần đối chiếu topic dịch vụ hỗ trợ |

### 10.4. Topic mới vs topic hiếm vs nhiễu

- **Topic mới:** có ý nghĩa riêng và chưa có trong taxonomy.
- **Topic hiếm:** có ý nghĩa nhưng số lượng rất ít; chưa chắc cần chính thức hóa.
- **Nhiễu:** câu thiếu ý, lỗi nhập liệu, bot/system message, lời chào, transcript sai.
- **Topic trùng:** mô hình tách một nhu cầu ra nhiều cụm do cách diễn đạt.

---

## 11. Kết quả và thống kê doanh nghiệp quan tâm

### 11.1. Định nghĩa chỉ số để không đếm sai

Ví dụ một khách trong một cuộc hội thoại hỏi “trả góp” ba lần:

- **3 lượt nhắc đến** (mentions), nếu đã định nghĩa và tách được ba lượt phù hợp.
- **1 cuộc hội thoại có topic trả góp** (conversation count).
- **1 khách duy nhất có topic trả góp** (unique customers), nếu có ID khách tin cậy.

Cần chọn mẫu số khi trình bày tỷ lệ:

- `% hội thoại có topic X = số hội thoại có X / tổng số hội thoại đủ điều kiện`.
- `% khách hỏi X = số khách có X / tổng số khách đủ điều kiện`.
- Một cuộc hội thoại có thể nhiều topic, nên **tổng % theo topic có thể lớn hơn 100%**.

### 11.2. Bảng phân tích mong muốn

| Báo cáo | Ví dụ ý nghĩa |
|---|---|
| Top topics | Khách thường hỏi về điều gì |
| New topic candidates | Nội dung chưa có trong danh mục |
| Topic by week/month | Xu hướng tăng/giảm |
| Topic by channel | Messenger khác tổng đài ở đâu |
| Topic by product/category | Nhu cầu theo nhóm sản phẩm |
| Co-occurrence | Chủ đề nào thường xuất hiện cùng nhau |
| Unknown/outlier rate | Bao nhiêu đoạn chưa được giải thích tốt |
| Review queue | Những cụm nào còn chờ người xác minh |

### 11.3. Các chỉ số không nên hiểu nhầm

- **Nhiều lượt nhắc đến ≠ nhiều khách hàng.**
- **Nhu cầu tăng về số lượng ≠ tăng tỷ trọng:** có thể do tổng traffic tăng.
- **Một topic được đề cập nhiều ≠ khách hàng hài lòng/không hài lòng.** Muốn biết điều này cần dữ liệu/nhãn tương ứng.
- **Các ID tự sinh của BERTopic không bảo đảm ổn định** sau khi train lại: nên có bảng mapping sang taxonomy chính thức và quản lý phiên bản.

---

## 12. Đánh giá chất lượng hệ thống

### 12.1. Vì sao cần ground truth?

Clustering đẹp trên biểu đồ không chứng minh phân loại đúng. Cần một tập mẫu đại diện được gán nhãn bởi người có hiểu biết nghiệp vụ; có thể bắt đầu với một tập nhỏ để phát hiện lỗi, sau đó mở rộng.

Nếu bài toán multi-label, mỗi đoạn được phép có **nhiều nhãn**. Hướng dẫn người gán nhãn phải rõ ràng: ví dụ nào thuộc/không thuộc, xử lý câu ngắn, ngữ cảnh, chủ đề trùng nhau.

### 12.2. Chỉ số phân loại known topics

- **Precision:** Trong số nhãn hệ thống gán, có bao nhiêu nhãn đúng?
- **Recall:** Trong số nhãn thực sự có, hệ thống tìm ra bao nhiêu?
- **F1:** Cân bằng precision và recall.
- **Micro-F1 / Macro-F1:** Phù hợp với bài toán multi-label, giúp thấy ảnh hưởng của các topic phổ biến/hiếm.
- **Per-topic metrics:** Quan trọng vì có thể một topic tốt nhưng một topic khác rất kém.

### 12.3. Chỉ số khám phá topic mới

- **Candidate precision:** Trong số topic ứng viên đề xuất, bao nhiêu thực sự mới và có ý nghĩa khi con người kiểm tra?
- **Novelty recall (nếu có nhãn chuẩn):** Bao nhiêu nhóm nhu cầu mới quan trọng được phát hiện?
- **Coherence/interpretability:** Các ví dụ trong cụm có nhất quán không? Từ khóa có giúp hiểu cụm không?
- **Stability:** Khi đổi random seed hoặc mẫu dữ liệu, kết quả có biến động quá lớn không?
- **Noise/outlier rate:** Tỷ lệ dữ liệu chưa vào nhóm rõ ràng, cần phân tích theo nguyên nhân.
- **Operational usefulness:** Chủ đề mới có giúp bộ phận kinh doanh/chăm sóc khách hàng đưa ra hành động không?

### 12.4. Một thiết kế đánh giá tốt

1. Lấy dữ liệu nhiều tuần/kênh, không chỉ một đợt chiến dịch.
2. Tách train/dev/test theo hội thoại để tránh cùng một cuộc chat xuất hiện ở cả train và test.
3. Nếu mục tiêu dự báo dữ liệu tương lai, ưu tiên kiểm tra thêm **temporal holdout**.
4. Tạo ví dụ khó: từ viết tắt, câu ngắn, nhiều topic, câu mơ hồ, nhãn gần nhau, transcript có lỗi.
5. So sánh baseline, zero-shot BERTopic và hybrid trên cùng mẫu.
6. Báo cáo cả lỗi thực tế, chi phí chạy, tốc độ, độ ổn định và giới hạn.

**Chưa nên tự đặt target kiểu “F1 phải trên 90%”** nếu chưa biết độ khó dữ liệu, rủi ro kinh doanh và chất lượng nhãn.

---

## 13. Công nghệ và nơi thao tác

### 13.1. Công cụ nghiên cứu cơ bản

| Mục đích | Công nghệ/công cụ gợi ý | Nơi thao tác |
|---|---|---|
| Viết tài liệu tổng quan | Markdown | VS Code |
| Đọc/sửa dữ liệu | Python + pandas | VS Code hoặc Jupyter Notebook |
| Khám phá topic | BERTopic | Python trên local / server được phép |
| Embedding | sentence-transformers hoặc backend tương thích | Python |
| Clustering | UMAP + HDBSCAN (pipeline mặc định) | Python |
| Đánh giá | scikit-learn | Python |
| Biểu đồ | Plotly / matplotlib | Notebook |
| Demo bảng điều khiển | Streamlit | Trình duyệt + local server |
| Xử lý audio (nếu có) | ASR như Whisper, speaker diarization | Môi trường được doanh nghiệp cho phép |
| Theo dõi mã nguồn | Git | VS Code/Git CLI |
| Đặc tả khi chốt phạm vi | OpenSpec | CLI + VS Code + coding agent |

### 13.2. Nên làm ở đâu trước?

Trong thư mục dự án `BERTopic` đang mở trong VS Code, giai đoạn hiện tại chỉ cần **đọc tài liệu, ghi chú câu hỏi và nghiên cứu một vài phương pháp**. Không cần mở máy chủ, thiết lập database hay đăng ký dịch vụ AI ngay.

Khi đến giai đoạn PoC, lựa chọn **Python + môi trường ảo + Jupyter/VS Code** thường dễ hiểu và dễ kiểm tra nhất. Việc dùng GPU, API cloud hay server phụ thuộc dữ liệu, nguồn lực và yêu cầu bảo mật.

### 13.3. Có cần LLM không?

**Không bắt buộc.** BERTopic và embedding model đã đủ cho một thử nghiệm khám phá topic. LLM có thể giúp *đặt tên cụm, tóm tắt câu đại diện, nhận diện intent hoặc hỗ trợ rà soát*, nhưng thêm chi phí và rủi ro rò rỉ thông tin nếu gửi dữ liệu thật tới dịch vụ bên ngoài.

### 13.4. Công cụ nào là công cụ chính?

- **BERTopic:** tạo/phân tích topic.
- **Sentence Transformers:** tạo text embeddings.
- **Pandas:** xử lý bảng dữ liệu và tính toán thống kê.
- **OpenSpec:** quản lý yêu cầu/thiết kế/công việc, **không phải** mô hình NLP và không thay BERTopic.
- **Coding agent/Codex:** có thể hỗ trợ đọc đặc tả và viết code, nhưng vẫn cần người kiểm tra đúng yêu cầu và chất lượng kết quả.

---

## 14. Lộ trình học và nghiên cứu

Đây là lộ trình tham khảo, **không phải lịch thực thi đã chốt**.

| Chặng | Cần hiểu gì | Kết quả tự kiểm tra |
|---|---|---|
| A — Hiểu nghiệp vụ | Khách hàng, cuộc hội thoại, topic hiện có, topic mới | Giải thích lại bài toán bằng ví dụ cụ thể |
| B — Kiến thức NLP | Document, embedding, similarity, clustering, multi-label | Phân biệt bài toán phân loại với khám phá |
| C — BERTopic cơ bản | UMAP/HDBSCAN/c-TF-IDF, `-1`, topic keywords, representative docs | Đọc được bảng topic và biết các giới hạn |
| D — Topic có sẵn | Fixed taxonomy, guided, zero-shot | Nêu được ưu/nhược của từng cách |
| E — Khám phá topic mới | Candidate discovery, review, gộp/tách | Giải thích vì sao một cụm chưa chắc là topic mới |
| F — Đánh giá | Ground truth, precision/recall/F1, stability | Biết thế nào là bằng chứng mô hình hoạt động tốt |
| G — Thiết kế đầu ra | Topic statistics, trend, dashboard | Phân biệt tần suất mention/conversation/customer |
| H — Đặc tả | OpenSpec, phạm vi, dữ liệu, chấp nhận | Sẵn sàng chốt yêu cầu trước coding |

### 14.1. Thứ tự đọc đề xuất

**Lượt 1:** Phần 1, 2, 3, 5, 7, 10, 17 để hiểu **đề tài sếp giao**.  
**Lượt 2:** Phần 4, 6, 8, 9, 12 để hiểu **cách làm kỹ thuật**.  
**Lượt 3:** Phần 11, 13, 14, 15, 16 để hiểu **đầu ra, công cụ, rủi ro và bước kế tiếp**.

### 14.2. Những kiến thức nên ưu tiên học sâu nhất

1. Text embeddings và cosine similarity.
2. Clustering, UMAP và HDBSCAN.
3. BERTopic `fit_transform`, `get_topic_info`, `get_document_info`.
4. Fixed taxonomy, guided BERTopic, zero-shot BERTopic.
5. Multi-label classification và sự cần thiết của ngữ cảnh hội thoại.
6. Cách kiểm chứng một chủ đề **mới về mặt nghiệp vụ**.
7. F1-score, human review và quản lý dữ liệu gán nhãn.

---

## 15. Rủi ro, hiểu lầm và những điều không nên làm

| Sai lầm thường gặp | Hậu quả | Cách tránh |
|---|---|---|
| Coi tất cả lời nhân viên là nhu cầu khách | Thống kê sai lệch | Lưu `role`, định nghĩa rõ phạm vi |
| Mỗi cuộc hội thoại chỉ có một chủ đề | Bỏ sót nhu cầu | Thiết kế multi-label / semantic segments |
| Coi `-1` là “topic mới” | Báo cáo nhiều false positives | Phân biệt outlier với novelty |
| Coi số cụm = số chủ đề nghiệp vụ | Topic trùng/lẻ/tạp | Review, merge và mapping taxonomy |
| Coi topic model là intent classifier | Không trả lời đúng mục đích khách | Tách topic và intent |
| Dùng mô tả fixed topic quá ngắn/mơ hồ | Nhầm nhãn | Mô tả, ví dụ dương/âm rõ ràng |
| Dùng một ngưỡng similarity mặc định | Nhãn sai nhiều | Hiệu chỉnh trên tập dữ liệu có nhãn |
| Không quản lý phiên bản taxonomy | Số liệu qua tháng khó so sánh | Lưu taxonomy_version và mapping |
| Đếm message thay cho conversation | Tần suất tăng giả | Định nghĩa đơn vị thống kê |
| Dùng dữ liệu thật ở dịch vụ public không được phép | Rủi ro lộ thông tin | Ẩn PII, phân quyền và phê duyệt |
| Chỉ đánh giá biểu đồ đẹp | Không biết mô hình đúng/sai | Ground truth, metric và error analysis |
| Tạo spec/thiết kế quá sớm | Xây sai bài toán | Xác nhận yêu cầu và dữ liệu mẫu trước |

### 15.1. Vấn đề đặc thù tiếng Việt

- Không dấu, sai dấu, lỗi gõ.
- Viết tắt “ko”, “k”, “ck”, “ib”, “ship”, “bh”.
- Một câu ngắn cần ngữ cảnh: “Cái này có không?”, “Sao vậy?”.
- Nhiều câu chen tiếng Anh, mã sản phẩm, phần trăm, đơn vị tiền tệ.
- Nhân viên có văn mẫu lặp lại khiến topic bị chi phối.
- Với audio: tiếng ồn, giọng địa phương, overlap speech, speaker split sai.

### 15.2. Bảo mật, đạo đức và tuân thủ

Hội thoại tư vấn thường chứa số điện thoại, địa chỉ, tên, thông tin đơn hàng và đôi khi dữ liệu nhạy cảm. Cần xác minh phạm vi sử dụng hợp pháp, mức độ đồng ý, quyền truy cập, thời hạn lưu trữ và phương án ẩn thông tin. Ưu tiên PoC trên dữ liệu giả lập hoặc dữ liệu đã ẩn danh/giảm thiểu khi chưa có phê duyệt.

---

## 16. Có nên dùng OpenSpec để đặc tả không?

**Có, nếu bạn định tiếp tục triển khai PoC bằng VS Code và coding agent**. OpenSpec giúp phân tách:

- **Why:** Vì sao làm, phạm vi và giá trị cần tạo → `proposal.md`.
- **What:** Hệ thống phải có hành vi gì, đầu vào/đầu ra/trường hợp kiểm thử → `specs/<capability>/spec.md`.
- **How:** Phương án kiến trúc và kỹ thuật → `design.md`.
- **Tasks:** Danh sách công việc có thể thực hiện, kiểm tra → `tasks.md`.

Theo tài liệu OpenSpec, đây là các artifact của workflow `spec-driven`. Có thể nghiên cứu và chỉnh các tài liệu trước khi bước sang thực thi.

### 16.1. Nhưng **chưa nên** khởi tạo đặc tả chính thức lúc này

Bởi vì hiện vẫn chưa rõ:

1. Sếp muốn **fixed-topic classifier** hay chỉ muốn **gợi ý topic mới**?
2. Danh mục topic hiện có đã hoàn chỉnh chưa?
3. Dữ liệu thực tế có những trường gì?
4. Mức phân tích là tin nhắn, đoạn ý nghĩa hay hội thoại?
5. Đầu ra bắt buộc có dashboard không?
6. Có cần xử lý audio ngay từ PoC không?

**Tài liệu đang đọc là overview để hiểu bài toán, không phải bản đặc tả đã được chốt.**

### 16.2. Sau này OpenSpec có thể chia capability thế nào?

Một danh sách ứng viên, **chưa tạo file**:

- `conversation-ingestion`: tiếp nhận, xác thực định dạng và chuẩn hóa text.
- `customer-utterance-processing`: phân đoạn, ngữ cảnh, phân biệt role.
- `fixed-topic-classification`: gán một/nhiều topic có sẵn.
- `topic-discovery`: tìm ứng viên topic chưa có.
- `topic-review`: duyệt/gộp/từ chối topic mới.
- `topic-analytics`: thống kê và báo cáo.
- `evaluation`: đo chất lượng và lưu kết quả kiểm thử.
- `audio-transcription`: chỉ khi audio nằm trong phạm vi PoC.

Không nhất thiết tách chính xác như trên; nên để **ranh giới nghiệp vụ** quyết định.

### 16.3. Khi nào chuyển từ overview sang OpenSpec?

Chỉ khi có tối thiểu: **mục tiêu được xác nhận**, **một bộ danh mục topic hoặc nguyên tắc tạo topic**, **mẫu dữ liệu đã xem**, **đầu ra mong muốn**, **giới hạn phạm vi và bảo mật**. Lúc đó mới có cơ sở viết acceptance criteria và thiết kế một thử nghiệm có thể kiểm chứng.

---

## 17. Những câu cần xác nhận với sếp

Đây là checklist thảo luận, **không phải yêu cầu gửi trả lời ngay**.

### 17.1. Mục tiêu

- [ ] Mục tiêu chính là phân loại chủ đề có sẵn, phát hiện mới, hay cả hai?
- [ ] “Fix topic” nghĩa chính xác là gì trong dự án này?
- [ ] Sếp cần báo cáo nghiên cứu, PoC nội bộ hay hệ thống vận hành thực?
- [ ] Muốn hiểu “nhu cầu” ở mức **topic** hay cả **intent**, mức quan tâm và hành vi mua?

### 17.2. Dữ liệu

- [ ] Có dữ liệu mẫu không? Số lượng, định dạng, ngôn ngữ?
- [ ] Có `conversation_id`, `role`, `timestamp`, `customer_id`?
- [ ] Có audio hay transcript có sẵn? Có phân biệt speaker không?
- [ ] Có cần xử lý thời gian thực hay chỉ batch offline?
- [ ] Có hạn chế bảo mật, lưu trữ, cloud/API không?

### 17.3. Topic

- [ ] Danh sách topic cố định có bao nhiêu nhãn và mô tả chi tiết ra sao?
- [ ] Có topic cha/con, nhiều nhãn trên một câu không?
- [ ] Topic mới có được tự động thêm vào danh mục hay bắt buộc duyệt?
- [ ] Topic ít phổ biến nhưng quan trọng có cần được ưu tiên không?

### 17.4. Đầu ra và đánh giá

- [ ] Thống kê theo tin nhắn, đoạn text, conversation hay khách duy nhất?
- [ ] Cần xem xu hướng theo ngày/tuần/tháng hay kênh nào?
- [ ] Có bộ gán nhãn chuẩn để đánh giá chưa?
- [ ] Độ chính xác / tốc độ / mức sai sót cho phép là bao nhiêu?
- [ ] Ai sẽ xác minh các topic mới?

---

## 18. Danh sách nguồn đọc chính thức

### BERTopic

1. **Tổng quan và các API:** https://maartengr.github.io/BERTopic/
2. **Quick Start:** https://maartengr.github.io/BERTopic/getting_started/quickstart/quickstart.html
3. **Guided Topic Modeling:** https://maartengr.github.io/BERTopic/getting_started/guided/guided.html
4. **Zero-shot Topic Modeling:** https://maartengr.github.io/BERTopic/getting_started/zeroshot/zeroshot.html
5. **Outlier Reduction:** https://maartengr.github.io/BERTopic/getting_started/outlier_reduction/outlier_reduction.html
6. **Dynamic / Topics over Time:** https://maartengr.github.io/BERTopic/getting_started/topicsovertime/topicsovertime.html
7. **API & approximate_distribution:** https://maartengr.github.io/BERTopic/api/bertopic.html
8. **Mã nguồn BERTopic:** https://github.com/MaartenGr/BERTopic

### OpenSpec

9. **Trang chủ và workflow:** https://openspec.dev/
10. **Spec-driven artifacts:** https://openspec.dev/docs/schemas/spec-driven
11. **Cấu hình OpenSpec:** https://openspec.dev/docs/configuration

### Kiến thức bổ sung nên tự tìm hiểu

- Text embedding, cosine similarity, UMAP, HDBSCAN, c-TF-IDF.
- Multi-label classification và đánh giá Micro-/Macro-F1.
- Conversation segmentation, speaker diarization, ASR quality.
- Ground truth annotation, taxonomy design, data governance.

> **Cách học:** Ưu tiên trang tài liệu chính thức của dự án, sau đó dùng notebook nhỏ để kiểm chứng các khái niệm. Tránh sao chép cấu hình “ngưỡng tốt nhất” từ một bài blog sang dữ liệu tiếng Việt của doanh nghiệp mà không đánh giá lại.

---

## 19. Kết luận và định hướng chốt

**Đề tài ở mức nghiệp vụ:** Phân tích nhu cầu khách hàng qua hội thoại, dùng chủ đề có sẵn để thống kê và khám phá những nhu cầu chưa được theo dõi.

**Đề tài ở mức kỹ thuật:** Kết hợp NLP embeddings, phân loại chủ đề, BERTopic/clustering, phân tích hội thoại, đánh giá mô hình và thống kê.

**Điểm khó nhất không phải cài thư viện**, mà là:

1. Định nghĩa đúng “topic” và “nhu cầu” theo hoạt động kinh doanh.
2. Chọn đơn vị phân tích không làm mất chủ đề đa nhãn.
3. Chứng minh một nhóm văn bản thực sự là **topic mới**, không phải topic cũ diễn đạt khác.
4. Đếm và trình bày số liệu đúng, tránh trùng lặp.
5. Đo chất lượng mô hình trên dữ liệu tiếng Việt có nhãn và đảm bảo bảo mật.

**Chiến lược nghiên cứu đề xuất:**

- Hiểu dữ liệu và taxonomy trước.
- Thử baseline phân loại fixed topic.
- Thử BERTopic unsupervised và zero-shot để khám phá.
- So sánh với phương án hybrid và đánh giá nhiều nhãn.
- Đưa topic mới qua human review trước khi chính thức hóa.
- Sau khi yêu cầu rõ ràng mới dùng **OpenSpec** tạo proposal, specs, design và tasks; **chưa đặc tả/triển khai trong giai đoạn đọc tổng quan này**.

---

**Ghi chú cuối:** Toàn bộ số liệu, tên topic, câu chat và cấu trúc dữ liệu trong tài liệu là **ví dụ minh họa**. Không có dữ liệu hay xác nhận yêu cầu thực tế của doanh nghiệp tại thời điểm viết.
