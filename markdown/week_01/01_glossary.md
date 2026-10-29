# Xây dựng hệ thống AI hỗ trợ đánh giá năng lực nói tiếng Anh theo CEFR cho sinh viên đại học Việt Nam ở trình độ A2-B2

## 01. Bảng thuật ngữ dùng thống nhất

| Thuộc tính | Giá trị |
| --- | --- |
| Tuần | W1 - Nền tảng đo lường, phạm vi và điều kiện nghiên cứu |
| Trạng thái | DRAFT - cần thực hiện và xác nhận |
| Người phụ trách | SV2 |
| Người duyệt | GV Ngoại ngữ |
| Phiên bản | 1.1 |
| Ngày cập nhật | 02/09/2026 |

## 1. Mục đích

File này là từ điển làm việc của nhóm. Khi một thuật ngữ có nhiều cách hiểu, nhóm dùng định nghĩa trong file này và ghi nguồn.

## 2. Thuật ngữ cốt lõi

| Thuật ngữ | Nghĩa dùng trong đề tài | Không được hiểu thành |
| --- | --- | --- |
| CEFR | Khung tham chiếu mô tả năng lực ngôn ngữ theo mức và descriptor | Một bài thi hoặc thuật toán chấm |
| Descriptor | Mô tả tích cực về điều người học có thể làm hoặc chất lượng thể hiện | Feature kỹ thuật có ngưỡng cố định |
| Construct | Năng lực hoặc đặc tính lý thuyết mà hệ thống muốn suy luận | Danh sách feature có sẵn |
| Performance | Bài thể hiện cụ thể trong một nhiệm vụ, thời điểm và điều kiện | Toàn bộ năng lực ổn định của người học |
| Proficiency | Năng lực rộng hơn được suy luận từ nhiều performance phù hợp | Điểm của một bài nói duy nhất |
| Spoken production | Lời nói theo lượt dài: kể, mô tả, cung cấp thông tin, lập luận | Mọi hoạt động có âm thanh |
| Spoken interaction | Đồng kiến tạo hội thoại qua nghe, phản hồi, lượt nói và làm rõ | Độc thoại trả lời prompt |
| Mediation | Xử lý/truyền đạt nội dung, làm trung gian hoặc hỗ trợ kiến tạo ý nghĩa | Chỉ dịch thuật; hoặc đồng nghĩa với interaction |
| Range | Phạm vi cấu trúc và từ vựng có thể huy động | Số từ hoặc độ dài câu đơn thuần |
| Accuracy | Mức kiểm soát cấu trúc và lựa chọn từ trong khi giao tiếp | Mọi lỗi xuất hiện trong transcript ASR |
| Fluency | Khả năng duy trì và phát triển lời nói dù có do dự, pause và sửa | Nói càng nhanh càng tốt |
| Interaction | Khởi tạo, phản hồi, giữ lượt, phối hợp và yêu cầu làm rõ | Độ trôi chảy của độc thoại |
| Coherence | Phát triển, tổ chức và liên kết ý thành diễn ngôn có thể theo dõi | Chỉ số lượng từ nối |
| Phonology | Intelligibility, sound articulation và prosody | Mức giống giọng bản ngữ |
| Intelligibility | Mức người nghe tiếp cận được thông điệp | Accent ít hay nhiều |
| Sound articulation | Độ rõ/chính xác khi tạo âm và từ | Chấm accent xã hội |
| Prosody | Stress, rhythm, intonation và chunking hỗ trợ ý nghĩa | Cao độ trung bình đơn lẻ |
| Rubric | Bộ tiêu chí và mô tả mức dùng để hướng dẫn chấm | Prompt gửi LLM |
| Rater | Giảng viên chấm bài độc lập theo rubric | Người sửa transcript |
| Adjudicator | Người thứ ba quyết định nhãn tham chiếu khi rater bất đồng | Rater thứ ba chấm mọi bài từ đầu |
| Anchor | Bài mẫu đã được thảo luận và gắn mức để hiệu chuẩn người chấm | Bài do AI tự gắn nhãn |
| Gold label | Nhãn tham chiếu sau quy trình double-rating/adjudication | Nhãn tuyệt đối không có sai số |
| Human-human agreement | Mức đồng thuận giữa các rater trước adjudication | Độ chính xác tuyệt đối của con người |
| AI-human agreement | Mức đồng thuận giữa dự đoán AI và nhãn người chấm | Bằng chứng duy nhất của validity |
| QWK | Đồng thuận có trọng số cho nhãn thứ bậc | Accuracy thông thường |
| Macro-F1 | Trung bình F1 giữa các lớp, giảm ảnh hưởng lớp lớn | Chỉ số đồng thuận thứ bậc |
| Gross Error Rate | Tỷ lệ lệch xa, ví dụ A2 thành B2 | Tỷ lệ lỗi ASR |
| Confidence | Độ tin cậy do mô hình báo cho dự đoán | Cam kết dự đoán chắc chắn đúng |
| Calibration | Kiểm tra confidence có khớp xác suất đúng thực tế | Tăng điểm mô hình tùy ý |
| ASR | Chuyển audio thành văn bản | Công cụ đánh giá CEFR hoàn chỉnh |
| WER | Tỷ lệ từ ASR nhận sai so với transcript tay | Tỷ lệ lỗi nói của người học |
| Feature | Dấu hiệu máy đo được từ audio, text hoặc lượt nói | Tiêu chí CEFR |
| Proxy | Dấu hiệu thay thế gián tiếp cho một phần construct | Bằng chứng đầy đủ cho construct |
| Confounder | Yếu tố làm sai quan hệ giữa bằng chứng và năng lực | Lỗi có thể bỏ qua |
| Speaker-level split | Mọi bài của một người chỉ thuộc một nhóm dữ liệu | Chia ngẫu nhiên từng audio |
| Data leakage | Thông tin train lọt vào validation/test | Chỉ là lộ PII |
| Formative assessment | Thu thập thông tin để cải thiện học và phản hồi | Thi cuối kỳ tự động |
| Diagnostic use | Xác định điểm mạnh/yếu cần hỗ trợ | Chẩn đoán y khoa/tâm lý |
| Low-stakes | Kết quả không tự quyết định học vụ/chứng chỉ | Không cần quy trình chất lượng |
| Validity | Bằng chứng rằng hệ thống đánh giá đúng construct cho mục đích đã nêu | Một metric cao duy nhất |
| Reliability | Mức ổn định/nhất quán của kết quả | Validity |
| Feasibility | Mức có thể triển khai với thời gian, nhân lực và dữ liệu thực tế | Lý do bỏ qua validity |
| Familiarisation | Hoạt động giúp nhóm/rater hiểu CEFR và mức trước khi đặc tả/chấm | Một buổi thuyết trình chung |
| Specification | Mô tả coverage, task, construct, criteria và intended use | Code API |
| Standardisation | Huấn luyện và căn chỉnh cách hiểu mức/anchor của rater | Chuẩn hóa audio |
| Validation | Chuỗi thu thập bằng chứng cho claim trong toàn dự án | Chạy test set một lần |
| Teacher review | Giảng viên xem bài do confidence/quality/rule yêu cầu | Giảng viên chấm lại mọi bài |
| CEFR-aligned | Có lập luận và bằng chứng cho quan hệ giữa construct/task/rating/result với CEFR trong đúng phạm vi | “Được Council of Europe chứng nhận” |
| Insufficient evidence | Không đủ bằng chứng hợp lệ để đưa ra mức cho một criterion; ở schema dùng `level=null` và reason code | Điểm thấp hoặc A2 mặc định |
| Evidence ID | Mã tham chiếu tới evidence artifact có thật, provenance, version và quality status | Chuỗi do LLM tự đặt để giải thích |
| Teacher verified | Trạng thái cho biết giảng viên đã thực hiện hành động xác nhận có audit record | Confidence cao hoặc model tự tin |
| Preregistration | Hồ sơ khóa trước về estimand, data split, phân tích và quy tắc quyết định | Tài liệu có thể sửa sau khi xem confirmation set mà không ghi deviation |
| Confirmation set | Tập được cô lập và chỉ dùng sau model freeze theo protocol | Dev/test set để thử nhiều model hoặc tune threshold |
| Document status | DRAFT/IN REVIEW/REVISE/APPROVED/SUPERSEDED của artifact | Trạng thái hoạt động hoặc kết quả gate |
| Activity status | NOT STARTED/IN PROGRESS/COMPLETED/BLOCKED của công việc thực tế | Approval của tài liệu |
| Gate status | NOT HELD/PASS/CONDITIONAL PASS/FAIL của cuộc review có bằng chứng | Tự động PASS vì file đã đầy nội dung |

## 3. Quy tắc cập nhật

- Mỗi thuật ngữ mới phải có định nghĩa, ví dụ và điều không được hiểu sai.
- Thay đổi định nghĩa construct phải ghi vào decision log.
- Thuật ngữ hiển thị cho sinh viên phải dùng tiếng Việt dễ hiểu hơn thuật ngữ nghiên cứu.
- Nguồn nền: CEFR 2001, CEFR Companion Volume 2020, Manual 2009 và Manual phát triển test sửa đổi 2026; link đầy đủ ở `02_source_reading_log.md`.
