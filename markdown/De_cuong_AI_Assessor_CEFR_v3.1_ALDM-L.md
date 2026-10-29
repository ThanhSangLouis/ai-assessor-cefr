# Xây dựng hệ thống AI hỗ trợ đánh giá năng lực nói tiếng Anh theo CEFR cho sinh viên đại học Việt Nam ở trình độ A2-B2

> Bản Markdown được chuyển từ [`De_cuong_AI_Assessor_CEFR_v3.1_ALDM-L.docx`](../artifacts/source/documents/De_cuong_AI_Assessor_CEFR_v3.1_ALDM-L.docx). File gốc được giữ nguyên.

## ĐỀ CƯƠNG NGHIÊN CỨU KHÓA LUẬN — PHIÊN BẢN 3.1

*Phiên bản 3.1 · 22/08/2026 · Đã đối chiếu khung ALDM-L*

> ERRATA QUẢN TRỊ 02/09/2026: tài liệu tổng hợp này chứa các lựa chọn kỹ thuật được viết bằng từ “chốt”, nhưng bộ hồ sơ W1 chưa có sign-off tương ứng. Cho đến khi G1/G2 thực tế phê duyệt, `week_01/21_week1_decision_log.md` là nguồn chuẩn về trạng thái. Đặc biệt, phương thức Task C, thiết kế parallel-form và quy mô/precision analysis đang `PROPOSED` hoặc `BLOCKING`; xem D013-D015 và C001-C003.

Development of an AI-Assisted System for CEFR-Aligned English Speaking Assessment for Vietnamese University Students at A2-B2 Levels

| Nhóm sinh viên: [3 SV — điền họ tên, MSSV] | Giảng viên hướng dẫn: [điền họ tên] |
| --- | --- |
| Đối tượng: Sinh viên đại học Việt Nam từ 18 tuổi, A2–B2 | Bối cảnh sử dụng: Formative / low-stakes |
| Thiết kế: Audio + transcript + interaction | Thẩm định: 2 rater độc lập + 1 adjudicator |
| Phiên bản: 3.1 — 22/08/2026 | Thời gian: 10 tuần |

> QUYẾT ĐỊNH CHỐT AI chấm điểm sơ bộ theo rubric do giảng viên Khoa Ngoại ngữ thiết lập; giảng viên kiểm duyệt và đưa ra quyết định cuối cùng. Hệ thống phục vụ đánh giá quá trình (formative/low-stakes), giúp sinh viên biết điểm mạnh, điểm cần cải thiện và nhiệm vụ luyện tập tiếp theo; hệ thống không tự cấp chứng chỉ CEFR.

Tài liệu này dùng để trao đổi với giảng viên hướng dẫn và làm khung viết khóa luận. Các ngưỡng metric là mục tiêu quản trị dự án, không phải chuẩn chính thức của Council of Europe.

## GHI CHÚ PHIÊN BẢN: v3.0 → v3.1

Bản v3.1 giữ nguyên thiết kế nghiên cứu và các quyết định kỹ thuật quan trọng của v3.0. Phần sửa tập trung vào việc đáp ứng khung ALDM-L và làm câu văn dễ hiểu hơn cho người mới tiếp cận đề tài.

| # | Nội dung đã sửa | Kết quả trong v3.1 |
| --- | --- | --- |
| 1 | Định vị ALDM-L | Thêm bảng D1–D8, AI Level, bối cảnh và mô hình học tập. |
| 2 | Quyền sở hữu chuẩn chấm | Xác định giảng viên Ngoại ngữ thiết lập và sở hữu rubric; nhóm CNTT vận hành hóa thành hệ thống. |
| 3 | Phân công ba bên | Thêm bảng riêng nêu rõ AI làm gì, giảng viên làm gì và sinh viên làm gì. |
| 4 | Dữ liệu dùng để điều chỉnh học | Bổ sung hồ sơ speaking_profile.json, người sử dụng hồ sơ và nhiệm vụ luyện tiếp theo. |
| 5 | Living Lab | Ánh xạ kế hoạch 10 tuần sang Pedagogy Lab, Tech Lab và lớp học thực tế. |
| 6 | Khả năng đọc hiểu | Thêm tóm tắt 30 giây, bảng thuật ngữ và các đoạn giải thích trước phần kỹ thuật/thống kê. |

## LỊCH SỬ THAY ĐỔI KỸ THUẬT: v2.0 → v3.0

Bản v3.0 giữ nguyên định vị, construct, kiến trúc và tech stack của v2.0. Mười thay đổi dưới đây xử lý các lỗ hổng về thống kê, tính khả thi thời gian và thiết kế đo lường.

| # | Thay đổi | Mục | Lý do |
| --- | --- | --- | --- |
| 1 | Thiết kế đánh giá chính chuyển từ single holdout sang repeated GroupKFold; holdout đổi vai trò thành confirmation set | 10.3 | CI hẹp hơn 2.25 lần ở cùng chi phí (mô phỏng, Phụ lục S4.2) |
| 2 | So sánh model bắt buộc dùng paired cluster bootstrap | 10.3 | So hai CI độc lập chỉ phát hiện được chênh lệch thật 1% số lần (S4.3) |
| 3 | Công bố trước MDE = ΔQWK 0.16; RQ2 tuyên bố là exploratory | 1.4, 10.2 | Không hứa độ nhạy không có thật |
| 4 | Bỏ adjacent accuracy; thêm Gross Error Rate; chuyển MAE và QWK sang tương đối theo trần người | 10.2 | Adjacent accuracy với 3 band thấp hơn cả baseline tầm thường |
| 5 | Mục tiêu mẫu 70–90 speaker × 2 response thay cho 40–60 × 2–3 | 7.2 | Nhiều speaker cho CI hẹp hơn ở cùng chi phí chấm; nhóm 3 người có đủ nhân lực tuyển |
| 6 | Thêm bài sàng lọc trình độ trước session, dùng làm biến convergent validity | 7.2, 7.3 | Kiểm soát phân bố band; tạo trục đo độc lập với 2 rater |
| 7 | Chỉ định adjudicator thứ ba; ước lượng lại công sức rater lên ~25 giờ/người | 7.3, 12.1 | Nhãn gold phải độc lập với chỉ số agreement |
| 8 | Chốt interlocutor Task C = prompt tree cố định, đo latency client-side | 2.2 | Nếu không, feature latency của Interaction vô giá trị |
| 9 | Thêm RQ6 — reliability của chính hệ thống AI | 1.4, 10.3 | v2.0 đo validity kỹ nhưng gần như không đo reliability |
| 10 | Kế hoạch 10 tuần có lane viết luận văn chạy song song từ W1 | 9 | 108–156 trang không thể viết trong W10 |

Thay đổi phụ: baseline B3 chuyển sang LLM chạy local; giảm manual transcription từ 30–45 xuống 15–20 bài nhưng chép hoàn toàn từ đầu; thêm trần 20 feature/tiêu chí; thêm 5 câu hỏi hội đồng (Q17–Q21).

## TÓM TẮT ĐIỀU HÀNH

> HIỂU TRONG 30 GIÂY Đầu vào là bài nói tiếng Anh của sinh viên. Đầu ra là mức A2/B1/B2, điểm theo sáu tiêu chí, bằng chứng cụ thể và gợi ý luyện tiếp. AI chấm sơ bộ; giảng viên chịu trách nhiệm về chuẩn chấm, kiểm duyệt các trường hợp khó và quyết định cuối cùng.

Đề tài giải quyết bài toán đánh giá kỹ năng nói tiếng Anh tốn nhiều thời gian và khó thực hiện thường xuyên trong lớp đông. Hệ thống nhận bài nói của sinh viên, chuyển lời nói thành văn bản, đo các dấu hiệu trong âm thanh và nội dung, rồi ước lượng mức A2/B1/B2 theo sáu tiêu chí CEFR. Mỗi kết quả đi kèm bằng chứng, mức độ tin cậy và cờ yêu cầu giảng viên xem lại. Nhờ vậy, AI hỗ trợ chấm nhanh hơn nhưng không giành quyền quyết định của giảng viên.

> KẾT LUẬN KHẢ THI Khả thi có điều kiện trong 10 tuần nếu: khóa phạm vi A2–B2, chỉ phục vụ low-stakes, có 2 rater + 1 adjudicator cam kết ~25 giờ, thu tối thiểu 60 (mục tiêu 70–90) sinh viên, dùng mô hình tiền huấn luyện để trích đặc trưng, viết luận văn song song từ tuần 1, và không mở rộng sang LMS/thi chống gian lận/phỏng vấn việc làm/chatbot tự do.

| Thành phần | Quyết định chốt |
| --- | --- |
| Construct | Range, Accuracy, Fluency, Interaction, Coherence, Phonology theo CEFR Companion Volume 2020 [1]. |
| Nhiệm vụ | Task A kể/mô tả (2 prompt tương đương); Task B nêu quan điểm; Task C hội thoại bán cấu trúc với prompt tree cố định. |
| Dữ liệu chính | 70–90 sinh viên đại học Việt Nam (sàn 60); 140–180 response; nhãn 2 rater + adjudicator; split theo speaker. |
| Mô hình | Baseline audio-only, transcript-only, frozen rubric LLM (local); mô hình chính late fusion + calibration. |
| Đầu ra | Mức ước lượng, sáu tiêu chí, confidence, evidence, hai ưu tiên cải thiện, cờ teacher review. |
| Đánh giá | Human–human trước AI–human; repeated GroupKFold; Agreement Ratio, QWK+CI, Gross Error Rate, macro-F1, calibration, reliability, error analysis. |

## MỤC LỤC

- Hướng dẫn đọc nhanh · 1. Bối cảnh và vấn đề · 2. Giải pháp đề xuất · 3. Khảo sát sản phẩm tương tự và khoảng trống · 4. Kiến trúc kỹ thuật · 5. Tech stack và lý do chọn · 6. Phạm vi đề tài · 7. Dữ liệu · 8. Pháp lý và đạo đức · 9. Kế hoạch 10 tuần, phân công và Living Lab · 10. Tiêu chí nghiệm thu và phương pháp đánh giá · 11. Đóng góp khoa học · 12. Đánh giá tính khả thi · 13. Rủi ro và dự phòng · 14. Câu hỏi hội đồng · 15. Cấu trúc quyển khóa luận · Tài liệu tham khảo

## HƯỚNG DẪN ĐỌC NHANH

Đề cương vẫn dùng một số thuật ngữ kỹ thuật vì đây là nghiên cứu giao thoa giữa giáo dục, ngôn ngữ học và trí tuệ nhân tạo. Bảng dưới đây giải thích theo cách ngắn gọn; các thuật ngữ sẽ được định nghĩa lại tại nơi sử dụng lần đầu.

| Thuật ngữ | Giải thích dễ hiểu |
| --- | --- |
| CEFR | Khung tham chiếu châu Âu mô tả năng lực ngoại ngữ theo các mức từ A1 đến C2; đề tài chỉ nghiên cứu A2, B1 và B2. |
| Rubric | Bảng tiêu chí chấm điểm. Rubric quy định ở mỗi mức A2/B1/B2, sinh viên cần thể hiện được điều gì. |
| Rater / adjudicator | Rater là giảng viên chấm bài. Adjudicator là người thứ ba phân xử khi hai người chấm không thống nhất. |
| ASR | Automatic Speech Recognition: công nghệ chuyển lời nói trong audio thành văn bản. |
| Feature | Một dấu hiệu máy đo được, ví dụ tốc độ nói, số lần ngập ngừng, độ đa dạng từ vựng hoặc thời gian phản hồi. |
| Baseline | Mô hình đơn giản dùng làm mốc so sánh. Mô hình mới chỉ có ý nghĩa khi được so công bằng với các mốc này. |
| Late fusion | Cách kết hợp kết quả từ âm thanh, văn bản và tương tác ở bước cuối thay vì trộn tất cả dữ liệu ngay từ đầu. |
| Confidence / calibration | Confidence là độ tự tin của AI. Calibration kiểm tra xem mức tự tin đó có phản ánh đúng khả năng AI trả lời đúng hay không. |
| QWK | Chỉ số đo mức đồng thuận giữa hai bên chấm các mức có thứ tự; lỗi A2 thành B2 bị phạt nặng hơn lỗi A2 thành B1. |
| WER | Tỷ lệ từ mà ASR nhận sai so với bản chép tay. WER cao có thể làm điểm từ vựng/ngữ pháp sai theo. |
| Speaker-level split | Mọi bài của cùng một người chỉ nằm ở một nhóm dữ liệu. Quy tắc này tránh để hệ thống học thuộc giọng người rồi được đánh giá trên chính người đó. |
| PoC / MVP | PoC là bản chứng minh ý tưởng có thể hoạt động; MVP là tập chức năng tối thiểu phải hoàn thành trong 10 tuần. |

## 1. BỐI CẢNH VÀ VẤN ĐỀ

### 1.1. Bối cảnh

Đánh giá năng lực nói cần nhiều thời gian của giảng viên, chịu ảnh hưởng bởi tải chấm, cách hiểu rubric và độ khó của nhiệm vụ. Trong lớp học đông, người học thường nhận điểm tổng quát nhưng thiếu bằng chứng cụ thể để sửa. Các hệ thống tự động có thể giảm thời gian phản hồi, nhưng chỉ có giá trị khi điểm số được liên kết với construct rõ ràng, nhiệm vụ phù hợp và dữ liệu chấm bởi con người.

CEFR Companion Volume 2020 mô tả sáu đặc trưng định tính của ngôn ngữ nói: Range, Accuracy, Fluency, Interaction, Coherence và Phonology [1]. CEFR là khung tham chiếu, không phải một thuật toán chấm; vì vậy dự án phải chứng minh cách mỗi tiêu chí được tạo bằng chứng, chấm, hiệu chỉnh và kiểm định. Một nhãn do LLM sinh ra mà không có rater validation không đủ để tuyên bố hệ thống đánh giá theo CEFR.

### 1.2. Vấn đề nghiên cứu cốt lõi

- Thiếu phản hồi nhanh và nhất quán cho hoạt động luyện Speaking ở quy mô lớp học.

- ASR có thể nhận sai tiếng Anh mang accent Việt; lỗi transcript có thể bị hiểu nhầm thành lỗi từ vựng hoặc ngữ pháp.

- Các chỉ báo kỹ thuật như speech rate, pause hoặc ASR confidence chỉ phản ánh một phần construct, không thể thay thế toàn bộ rubric CEFR.

- Dữ liệu công khai có người Việt nhưng rất ít bộ vừa có audio tự nhiên, vừa có sáu nhãn CEFR, vừa có nhiều giảng viên chấm.

- Nhiều demo công khai tập trung vào UX hoặc prompt LLM, nhưng thiếu speaker-level split, calibration, human–human agreement và phân tích sai lệch theo accent/thiết bị.

- Phần lớn nghiên cứu quy mô nhỏ báo cáo điểm số mà không báo khoảng tin cậy, khiến kết luận không kiểm chứng được.

### 1.3. Phát biểu bài toán

> BÀI TOÁN NGHIÊN CỨU Làm thế nào xây dựng một hệ thống AI có thể ước lượng mức Speaking A2–B2 của sinh viên đại học Việt Nam theo sáu tiêu chí CEFR, cung cấp bằng chứng và độ tin cậy, đồng thời đạt mức đồng thuận hữu ích so với trần đồng thuận giữa chính các giảng viên, trên dữ liệu được tách theo người nói?

### 1.4. Câu hỏi nghiên cứu

| Mã | Câu hỏi | Vị thế |
| --- | --- | --- |
| RQ1 | Điểm từng tiêu chí và mức overall của hệ thống đồng thuận với giảng viên ở mức nào, so với trần human–human, và với khoảng tin cậy nào? | Khẳng định (confirmatory) |
| RQ2 | Kết hợp audio + transcript + interaction có cải thiện so với audio-only và transcript-only không? | Exploratory — chỉ đủ độ nhạy khi ΔQWK ≥ 0.16 |
| RQ3 | WER, độ ồn, thời lượng, thiết bị và prompt ảnh hưởng thế nào đến sai số chấm? | Exploratory |
| RQ4 | Calibration và confidence threshold có phát hiện được các ca cần giảng viên duyệt không? | Exploratory |
| RQ5 | Phản hồi grounded bằng timestamp/transcript có rõ ràng và hành động được hơn phản hồi chung chung không? | Exploratory |
| RQ6 | Điểm của hệ thống có ổn định giữa hai prompt tương đương, giữa các lần chạy và trước nhiễu âm thanh không? | Mới ở v3.0 — exploratory |

> Tuyên bố độ nhạy (công bố trước khi thu dữ liệu): mô phỏng Monte Carlo (Phụ lục S4) cho thấy với quy mô mẫu dự kiến, nghiên cứu chỉ đủ độ nhạy để phát hiện chênh lệch ΔQWK ≥ 0.16 giữa hai mô hình. Chênh lệch nhỏ hơn sẽ được báo cáo là không kết luận được, không phải “không có khác biệt”.

> `[CẦN XÁC MINH]` Workspace tại lần audit 02/09/2026 chưa có Phụ lục S hoặc script/config/output mô phỏng. Các con số MDE, CI và quy mô mẫu trong tài liệu này chỉ được dùng như planning assumptions cho đến khi artifact được cung cấp/tái tạo và D015 được duyệt.

### 1.5. Vị trí đề tài trong ma trận ALDM-L

Theo tài liệu định hướng của khoa, đề tài nằm đúng ô Speaking × Assess × AI Assessor của Nhóm 1 – Đánh giá, chẩn đoán và định vị năng lực [21]. Nói đơn giản, sinh viên thực hiện bài nói; AI phân tích và chấm sơ bộ; giảng viên thiết lập chuẩn chấm và giữ quyền quyết định cuối cùng.

| Chiều | Nội dung của đề tài | Hiểu đơn giản |
| --- | --- | --- |
| D1 – Learner | Sinh viên đại học Việt Nam từ 18 tuổi, dùng tiếng Anh như ngoại ngữ, trình độ A2–B2. Không gồm A1, C1, C2 và người dưới 18 tuổi. | Đề tài chỉ cam kết cho đúng nhóm đã thu và kiểm định dữ liệu. |
| D2 – Competency | Speaking là năng lực chính; gồm Range, Accuracy, Fluency, Interaction, Coherence và Phonology theo CEFR Companion Volume 2020. | Đánh giá nhiều mặt của việc nói, không chỉ phát âm hoặc tốc độ. |
| D3 – Learning Stage | Assess là giai đoạn chính; Diagnose và Reflect & Adapt là giai đoạn phụ. | Chấm mức hiện tại, sau đó chỉ ra điều cần luyện tiếp. |
| D4 – Learning Activity | Task A kể/mô tả; Task B nêu quan điểm; Task C hội thoại bán cấu trúc ba lượt. | Ba loại bài tạo đủ bằng chứng cho sáu tiêu chí. |
| D5 – AI Role | AI Assessor là vai trò chính; AI Feedbacker là vai trò phụ. Không đóng vai AI Tutor, Conversation Partner hay Orchestrator. | AI chấm và giải thích kết quả, không dạy thay hoặc điều phối toàn bộ khóa học. |
| D6 – Human Role | Giảng viên Ngoại ngữ thiết lập/sở hữu rubric và anchor, hiệu chuẩn người chấm, duyệt ca khó. Nhóm CNTT vận hành hóa rubric. Sinh viên làm bài và tự đối chiếu phản hồi. | Chuẩn chấm thuộc về giảng viên; AI và nhóm kỹ thuật thực hiện theo chuẩn đó. |
| D7 – Learning Data | Hồ sơ speaking_profile gồm điểm tổng, sáu tiêu chí, xác suất, confidence, bằng chứng, cờ chất lượng và lịch sử giảng viên chỉnh sửa. | Mỗi lần chấm tạo ra một hồ sơ có thể truy vết. |
| D8 – Adaptation | Hồ sơ dùng để gợi ý nhiệm vụ luyện tiếp và có thể làm đầu vào cho các module hội thoại, luyện nghe hoặc điều phối lộ trình. | Kết quả chấm không dừng ở một con điểm; nó giúp quyết định bước học tiếp theo. |
| AI Level | Level 2 – AI as Learning Partner. AI phản hồi và gợi ý luyện tập, nhưng chưa theo dõi dài hạn hoặc tự điều phối toàn bộ lộ trình. | Đúng với phạm vi 10 tuần và vẫn giữ giảng viên trong vòng kiểm soát. |
| Context | Trường đại học; thử nghiệm trong lớp tiếng Anh theo mô hình Living Lab. | Nơi kiểm định là bối cảnh giáo dục thực tế, không phải kỳ thi chứng chỉ. |
| Learning Model | Blended Learning – kết hợp hoạt động trên lớp với hệ thống số. | AI bổ sung cho hoạt động của giảng viên, không thay thế lớp học. |

### 1.6. Ma trận phối hợp giữa AI, giảng viên và sinh viên

Bảng này là ranh giới trách nhiệm của hệ thống. Quy tắc quan trọng nhất là AI được phép chấm sơ bộ và gợi ý, còn giảng viên chịu trách nhiệm về chuẩn chấm và quyết định sư phạm.

| Hoạt động | AI làm gì | Giảng viên làm gì | Sinh viên làm gì |
| --- | --- | --- | --- |
| Thiết kế chuẩn | Không tự đặt chuẩn. | Thiết lập rubric A2/B1/B2, chọn bài mẫu chuẩn (anchor) và hiệu chuẩn người chấm. | Không tham gia chấm chuẩn. |
| Thực hiện bài nói | Thu âm và kiểm tra chất lượng file. | Thiết kế/chọn nhiệm vụ phù hợp với mục tiêu học tập. | Thực hiện Task A, B và Task C nếu được chọn. |
| Chấm sơ bộ | Phân tích phát âm, độ trôi chảy, từ vựng, ngữ pháp, liên kết và tương tác; trả xác suất kèm bằng chứng. | Không can thiệp vào lần chạy AI; cung cấp nhãn chuẩn cho nghiên cứu. | Không sửa audio hoặc transcript sau khi nộp. |
| Kiểm duyệt | Gắn cờ bài có confidence thấp, audio kém hoặc dấu hiệu ASR sai. | Duyệt ca khó, phân xử bất đồng và quyết định cuối cùng. | Có thể yêu cầu giải thích hoặc phản hồi về kết quả. |
| Phản hồi | Nêu tối đa hai điểm mạnh, hai ưu tiên và dẫn timestamp/transcript làm bằng chứng. | Bổ sung nhận xét bậc cao khi cần. | Nghe lại bài, đọc bằng chứng và tự đối chiếu. |
| Điều chỉnh học | Đề xuất một nhiệm vụ luyện tiếp dựa trên tiêu chí yếu nhất. | Chấp nhận, sửa hoặc thay nhiệm vụ theo mục tiêu môn học. | Chọn và thực hiện nhiệm vụ tiếp theo. |

### 1.7. Vị trí trong hệ sinh thái và dữ liệu đầu ra

Đề tài là một cổng tạo dữ liệu năng lực nói cho hệ sinh thái ALDM-L. Phạm vi khóa luận chỉ xây hệ thống đánh giá và định nghĩa giao diện dữ liệu; không xây toàn bộ các module sử dụng dữ liệu ở phía sau.

> LUỒNG GIÁ TRỊ Sinh viên làm bài nói → AI tạo bằng chứng và điểm sơ bộ → giảng viên kiểm duyệt → speaking_profile.json được xác nhận → hệ thống học tập chọn bài luyện phù hợp hơn.

| Nơi sử dụng hồ sơ | Cách sử dụng | Trạng thái trong khóa luận |
| --- | --- | --- |
| Báo cáo cho sinh viên | Hiển thị mức hiện tại, điểm mạnh, điểm yếu và bằng chứng cụ thể. | Trong phạm vi MVP. |
| Giảng viên | Xem hàng đợi bài cần duyệt, sửa kết quả và chọn nhiệm vụ luyện tiếp. | Trong phạm vi MVP mở rộng. |
| Đề tài 3 – AI Conversation Partner | Chọn độ khó của kịch bản hội thoại theo band và tiêu chí yếu. | Chỉ định nghĩa giao diện; không xây module. |
| Đề tài 5 – Luyện nghe thích ứng | Tham khảo band và hồ sơ ngôn ngữ để chọn nội dung nghe phù hợp. | Chỉ định nghĩa giao diện; không xây module. |
| Đề tài 8 – AI Orchestrator | Kết hợp hồ sơ nói với dữ liệu kỹ năng khác để xếp lộ trình cá nhân hóa. | Chỉ định nghĩa giao diện; không xây module. |

#### 1.7.1. Đặc tả tối thiểu của speaking_profile.json

| Nhóm trường | Trường dữ liệu chính | Ý nghĩa |
| --- | --- | --- |
| Định danh giả | learner_id, assessed_at | Liên kết các lần đánh giá mà không lưu tên trong dữ liệu mô hình. |
| Phiên bản | rubric_version, model_version, calibration_version | Biết kết quả được tạo bằng chuẩn và mô hình nào. |
| Kết quả tổng | overall.band, overall.probs, overall.confidence | Mức A2/B1/B2, xác suất từng mức và độ tin cậy. |
| Sáu tiêu chí | range, accuracy, fluency, interaction, coherence, phonology | Điểm chi tiết; Interaction có thể là “chưa đủ bằng chứng”. |
| Bằng chứng | evidence_refs, reason_codes | Tham chiếu đến timestamp, transcript và lý do hệ thống đưa ra kết quả. |
| Điều chỉnh | weakest_criteria, next_task_hint | Tiêu chí cần ưu tiên và gợi ý một nhiệm vụ luyện tiếp. |
| Kiểm duyệt | teacher_verified, review_status | Cho biết giảng viên đã xác nhận/sửa kết quả hay chưa. |

## 2. GIẢI PHÁP ĐỀ XUẤT

### 2.1. Mô hình sản phẩm

Giải pháp là vòng lặp Elicit – Assess – Explain – Review – Practice. Sinh viên hoàn thành các nhiệm vụ nói được thiết kế trước theo một bản mô tả thống nhất (task blueprint); pipeline tạo điểm theo từng tiêu chí; báo cáo gắn điểm với bằng chứng; ca bất định vào hàng đợi giảng viên; hệ thống gợi ý một nhiệm vụ luyện tiếp theo. Đây là hệ thống hỗ trợ học tập, không cấp chứng chỉ và không tự quyết định kết quả học vụ.

> NGUYÊN TẮC Tách bằng chứng khỏi diễn giải. Audio/transcript/turn log tạo evidence có version; mô hình chấm tạo probability; lớp feedback chỉ được dùng rubric và evidence đã kiểm chứng.

### 2.2. Blueprint nhiệm vụ nói

| Nhiệm vụ | Cách thực hiện | Bằng chứng chính | Giới hạn |
| --- | --- | --- | --- |
| Task A — Kể/mô tả | 90–120 giây; chủ đề quen thuộc; 2 prompt tương đương (A1, A2) cho phép đo parallel-form reliability. | Range, Fluency, Coherence, Phonology. | Không đủ bằng chứng cho Interaction. |
| Task B — Nêu quan điểm | ~120 giây. 30 giây chuẩn bị + prompt có 3 bullet gợi ý để giảm floor effect ở người học A2. Ghi lại prep time làm biến kiểm soát. | Range, Accuracy, Fluency, Coherence, task relevance. | Cần kiểm soát độ khó và kiến thức nền. |
| Task C — Hội thoại | 3 lượt. Prompt tree cố định, audio ghi sẵn, chọn nhánh follow-up theo rule đơn giản (độ dài/độ trễ của lượt trước). | Interaction, Fluency, relevance, clarification, turn management. | Chỉ triển khai cho 25–30 speaker sau khi tree ổn định ở pilot. |

#### 2.2.1. Thiết kế interlocutor cho Task C (bổ sung ở v3.0)

v2.0 không chỉ định ai là người đối thoại. Ba phương án và lý do lựa chọn:

| Phương án | Vấn đề | Quyết định |
| --- | --- | --- |
| Người thật hỏi trực tiếp | Follow-up khác nhau giữa các thí sinh → confound độ khó; nhân đôi chi phí thu | Loại |
| LLM hội thoại thời gian thực | Latency hệ thống lẫn vào latency người học → feature Interaction vô giá trị | Loại |
| Prompt tree cố định, audio ghi sẵn | Kém tự nhiên hơn, nhưng mọi thí sinh gặp cùng tập kích thích; chưa tự chứng minh đủ interactional authenticity | Phương án đề xuất, chờ D013/G2 |

Quy định đo latency: mốc bắt đầu = thời điểm kết thúc phát audio prompt, đo ở phía client. System latency (mạng, buffer, UI) log riêng vào bảng quality và không được đưa vào feature Interaction. Việc này phải hoàn tất và test trước cổng G2.

### 2.3. Sáu tiêu chí đánh giá

| Tiêu chí | Ý nghĩa vận hành | Evidence máy có thể đo | Cảnh báo |
| --- | --- | --- | --- |
| Range | Phạm vi từ vựng/cấu trúc đủ để diễn đạt và paraphrase. | Lexical profile, MTLD/HD-D, cấu trúc câu, đa dạng cụm từ. | Không thưởng độ dài đơn thuần. |
| Accuracy | Mức kiểm soát ngữ pháp và khả năng tự sửa. | Lỗi trên AS-unit/clause, agreement, tense, preposition, repair. | ASR error không được tính thành lỗi người học. |
| Fluency | Duy trì lời nói với nhịp và pause phù hợp nhiệm vụ. | Articulation rate, pause ratio/count, mean run length, repetitions. | Không đồng nhất nói nhanh với giỏi. |
| Interaction | Khởi tạo, phản hồi, giữ lượt, làm rõ và phối hợp hội thoại. | Latency (client-side), turn completion, clarification, relevance. | Chỉ chấm khi có Task C. |
| Coherence | Phát triển và liên kết ý rõ ràng. | Discourse markers, idea progression, semantic continuity, topic relevance. | Transcript sai có thể làm giảm điểm giả. |
| Phonology | Intelligibility, âm, trọng âm, nhịp và ngữ điệu. | GOP tính local từ wav2vec2 + prosody (F0 range, rhythm metrics). | Không phạt accent nếu thông điệp dễ hiểu [1]. Đây là tiêu chí có construct coverage yếu nhất — xem 2.3.1. |

### 1. Cách đọc bảng

- Tiêu chí: Năng lực Speaking cần đánh giá theo CEFR.

- Ý nghĩa vận hành: Diễn giải tiêu chí thành hành vi có thể quan sát.

- Evidence máy có thể đo: Đặc trưng lấy từ audio hoặc transcript.

- Cảnh báo: Những trường hợp chỉ số máy có thể dẫn đến kết luận sai.

Hệ thống không nên tính điểm CEFR bằng một công thức đơn giản. Nó cần tổng hợp nhiều bằng chứng, kiểm tra độ tin cậy rồi mới đưa ra điểm.

### 2. Range: Phạm vi ngôn ngữ

Range đánh giá người nói có đủ từ vựng và cấu trúc để trình bày ý tưởng hay không.

Máy có thể đo:

- Lexical profile: Người nói sử dụng từ phổ biến hay từ nâng cao, có phù hợp chủ đề không.

- MTLD/HD-D: Chỉ số đo độ đa dạng từ vựng, ít bị ảnh hưởng bởi độ dài bài nói hơn tỷ lệ từ không lặp.

- Cấu trúc câu: Câu đơn, câu ghép, mệnh đề phụ, câu điều kiện, mệnh đề quan hệ.

- Cụm từ: Ví dụ in my opinion, one possible reason is, on the other hand.

- Paraphrase: Khi không nhớ một từ, người học có thể diễn đạt lại bằng cách khác hay không.

Ví dụ:

I like this city because it is good and people are good.

Bài nói dễ hiểu nhưng phạm vi từ vựng và cấu trúc còn hạn chế.

I enjoy living in this city because it provides convenient public services and a friendly environment.

Câu sau thể hiện Range tốt hơn nhờ từ vựng và cấu trúc đa dạng.

Cảnh báo: Không được chấm Range chỉ dựa trên số lượng từ. Một bài dài nhưng lặp lại nhiều từ đơn giản vẫn có thể có Range thấp.

### 3. Accuracy: Độ chính xác

Accuracy đánh giá khả năng kiểm soát ngữ pháp và khả năng tự sửa lỗi.

Máy có thể phát hiện lỗi theo:

- AS-unit: Một mệnh đề độc lập cùng các mệnh đề phụ liên quan. Đây là đơn vị phù hợp để phân tích lời nói hơn câu viết.

- Clause: Kiểm tra lỗi ở từng mệnh đề.

- Agreement: Sự hòa hợp chủ ngữ và động từ, ví dụ She go thay vì She goes.

- Tense: Sử dụng sai thì.

- Preposition: Dùng sai giới từ.

- Repair: Người học nhận ra và tự sửa lỗi.

Ví dụ:

Yesterday I go... I mean, I went to school.

Người học ban đầu sai thì nhưng đã tự sửa. Hệ thống nên ghi nhận lỗi, đồng thời ghi nhận khả năng kiểm soát và tự sửa.

Cảnh báo lớn nhất là lỗi ASR. Người học nói đúng nhưng hệ thống nhận dạng sai thì mô-đun kiểm tra ngữ pháp có thể kết luận nhầm. Vì vậy:

- Phải lưu độ tin cậy của ASR.

- Không chấm mạnh những từ ASR không chắc chắn.

- Có thể chạy nhiều mô hình ASR để đối chiếu.

- Cần kiểm tra transcript trên giọng người Việt.

### 4. Fluency: Độ trôi chảy

Fluency không chỉ là nói nhanh. Tiêu chí này đánh giá khả năng duy trì lời nói với nhịp độ và khoảng dừng phù hợp.

Máy có thể đo:

- Articulation rate: Số âm tiết hoặc từ được nói trong một giây, không tính thời gian im lặng.

- Pause count: Số lần dừng.

- Pause duration: Thời gian mỗi lần dừng.

- Pause ratio: Tỷ lệ thời gian im lặng trên toàn bài nói.

- Mean run length: Số từ trung bình nói được giữa hai khoảng dừng.

- Repetition: Mức độ lặp từ hoặc lặp cụm từ.

- Filled pauses: Các âm đệm như um, uh, er.

Ví dụ, người nói nhanh nhưng dừng sai vị trí, lặp lại nhiều và khó hiểu không nên được điểm Fluency cao. Ngược lại, người nói hơi chậm nhưng ổn định, ngắt nghỉ đúng ý vẫn có thể được đánh giá tốt.

### 5. Interaction: Khả năng tương tác

Interaction đánh giá khả năng tham gia vào hội thoại, không phải năng lực độc thoại.

Máy có thể đo:

- Latency: Thời gian từ khi hệ thống hỏi đến khi người học bắt đầu trả lời.

- Turn completion: Người học có hoàn thành lượt nói không.

- Clarification: Có biết yêu cầu giải thích lại không.

- Repair: Có biết sửa hoặc diễn đạt lại khi đối thoại gặp vấn đề không.

- Relevance: Câu trả lời có liên quan đến câu hỏi trước không.

- Turn-taking: Khả năng nhận lượt và nhường lượt.

Ví dụ, khi không hiểu câu hỏi, người học nói:

Could you repeat the question, please?

Đây là bằng chứng tích cực về Interaction, không nhất thiết là một lỗi.

Dòng “Chỉ chấm khi có Task C” có nghĩa là hệ thống chỉ đánh giá Interaction trong nhiệm vụ hội thoại với AI hoặc giám khảo. Bài đọc thành tiếng hoặc bài độc thoại không cung cấp đủ bằng chứng cho tiêu chí này.

### 6. Coherence: Tính mạch lạc

Coherence đánh giá cách người học tổ chức và kết nối ý tưởng.

Máy có thể đo:

- Discourse markers: firstly, because, however, therefore, for example.

- Idea progression: Ý sau có phát triển từ ý trước không.

- Semantic continuity: Các câu có liên kết về mặt ý nghĩa không.

- Topic relevance: Nội dung có bám sát câu hỏi không.

- Mở bài, phát triển và kết luận: Bài nói có cấu trúc hợp lý không.

Một bài nói có thể đúng ngữ pháp nhưng vẫn thiếu Coherence nếu các câu rời rạc hoặc chuyển chủ đề đột ngột.

Cảnh báo: Transcript sai có thể làm máy tưởng rằng bài nói không liên kết. Vì vậy điểm Coherence cần đi kèm độ tin cậy ASR và không nên dựa hoàn toàn vào một LLM.

### 7. Phonology: Phát âm và ngữ điệu

Phonology trong CEFR không có nghĩa là “nói giống người bản ngữ”. Nó tập trung vào:

- Intelligibility: Người nghe có hiểu được không.

- Phát âm âm riêng lẻ.

- Trọng âm từ và trọng âm câu.

- Nhịp điệu.

- Ngữ điệu.

- Khả năng làm nổi bật thông tin quan trọng.

#### GOP là gì?

GOP, Goodness of Pronunciation, là chỉ số so sánh âm người học phát ra với âm mà mô hình mong đợi.

Ví dụ, người học cần nói từ ship. Hệ thống căn chỉnh audio với các âm /ʃ/ /ɪ/ /p/, sau đó ước lượng mỗi âm được phát ra rõ đến mức nào.

wav2vec2 có thể được dùng để:

- Trích xuất biểu diễn âm thanh.

- Căn chỉnh audio với âm vị hoặc từ.

- Tính GOP cho từng âm.

- Xác định vị trí có nguy cơ phát âm sai.

#### Prosody là gì?

Prosody là các yếu tố vượt ra ngoài từng âm riêng lẻ:

- F0 range: Khoảng biến thiên cao độ giọng nói.

- Trọng âm từ và câu.

- Nhịp điệu giữa âm tiết.

- Độ dài âm.

- Đường ngữ điệu lên xuống.

- Cách chia câu thành các cụm ý.

#### Tại sao Phonology có “construct coverage yếu nhất”?

Construct là năng lực mà hệ thống muốn đánh giá. Construct coverage là mức độ các chỉ số máy bao phủ đầy đủ năng lực đó.

GOP chỉ phản ánh một phần độ chính xác của âm vị. F0 và rhythm metrics chỉ phản ánh một phần ngữ điệu, nhưng CEFR quan tâm nhiều nhất đến việc người nghe thực sự có hiểu và phải cố gắng bao nhiêu để hiểu.

Máy có thể sai trong các trường hợp:

- Người học có giọng Việt rõ nhưng vẫn dễ hiểu.

- GOP thấp vì khác giọng dữ liệu huấn luyện.

- Microphone kém làm điểm phát âm giảm.

- Người học phát âm từng âm đúng nhưng ngữ điệu khiến câu khó hiểu.

- ASR nhận đúng câu chưa chắc người nghe thấy dễ hiểu.

- ASR nhận sai chưa chắc người học phát âm sai.

Vì vậy, không được phạt người học chỉ vì có accent. Phương án tốt hơn là kết hợp:

- GOP cho phát âm cục bộ.

- Đặc trưng prosody.

- Tỷ lệ từ ASR nhận dạng được.

- Mô hình dự đoán intelligibility.

- Điểm dễ hiểu do giám khảo hoặc người nghe đánh giá.

- Kiểm tra riêng trên dữ liệu giọng Việt.

### 8. Cách hệ thống sử dụng các bằng chứng

Quy trình hợp lý là:

Audio

-> Kiểm tra chất lượng thu âm

-> ASR và transcript

-> Đặc trưng âm thanh

-> Đặc trưng ngôn ngữ

-> Điểm từng tiêu chí CEFR

-> Kiểm tra độ tin cậy

-> Mức CEFR tổng hợp và phản hồi

Hệ thống nên trả kết quả dạng hồ sơ:

Range:       B1

Accuracy:    A2+

Fluency:     B1

Interaction: B1

Coherence:   B1

Phonology:   A2+

Tổng hợp:    B1, độ tin cậy trung bình

#### 2.3.1. Tuyên bố trước về giới hạn của Phonology

Ba lựa chọn kỹ thuật đều có nhược điểm, và đề tài chọn phương án ít rủi ro pháp lý nhất:

| Lựa chọn | Vấn đề |
| --- | --- |
| GOPT + SpeechOcean762 [7][8] | Huấn luyện trên L1 Mandarin, scripted speech → domain shift kép khi áp lên giọng Việt, spontaneous |
| Azure Pronunciation Assessment [12] | Chất lượng tốt nhưng là cloud → mâu thuẫn nguyên tắc local-first, cần consent chuyển dữ liệu riêng |
| GOP tự tính bằng wav2vec2 local | Phụ thuộc forced alignment trên transcript ASR → lỗi cộng dồn. Chọn phương án này. |

Đề tài công bố trước rằng Phonology dự kiến có QWK thấp nhất trong sáu tiêu chí. Nêu trước tốt hơn để hội đồng phát hiện.

### 2.4. Báo cáo kết quả

- Mức overall ước lượng A2/B1/B2 và xác suất từng mức; hiển thị vùng ranh giới khi hai mức liền kề gần nhau.

- Điểm từng tiêu chí; Interaction ghi “chưa đủ bằng chứng” nếu người học không làm Task C.

- Evidence gồm timestamp, đoạn transcript, số liệu pause/rate và ghi chú model có thể truy vết theo evidence_id.

- Tối đa hai điểm mạnh, hai ưu tiên cải thiện và một nhiệm vụ luyện tiếp theo.

- Cờ invalid / low confidence / ASR risk và lý do chuyển sang teacher review.

- Hiển thị rubric_version, prompt_version, model_version, calibration_version và ngày chấm.

### 2.5. Cách kết quả đánh giá được dùng để cải thiện việc học

Sau khi chấm, hệ thống không chỉ trả một mức CEFR. Nó thực hiện một vòng phản hồi ngắn gồm năm bước:

Bước 1 – Xác định tiêu chí yếu nhất nhưng chỉ khi có đủ bằng chứng và confidence đạt ngưỡng.

Bước 2 – Trích tối đa hai bằng chứng dễ hiểu, ví dụ đoạn ngập ngừng dài hoặc một ý chưa được liên kết rõ.

Bước 3 – Sinh một gợi ý luyện tập theo mẫu đã duyệt, ví dụ kể lại cùng chủ đề trong 90 giây nhưng dùng ba từ nối bắt buộc.

Bước 4 – Chuyển bài cho giảng viên nếu audio kém, ASR có nguy cơ sai hoặc hai mức liền kề có xác suất quá gần nhau.

Bước 5 – Lưu kết quả đã được giảng viên xác nhận vào speaking_profile để lần học tiếp theo dùng được.

> Giới hạn: đề tài chỉ đề xuất một nhiệm vụ luyện tiếp theo bằng quy tắc minh bạch. Việc xây hệ thống cá nhân hóa dài hạn thuộc AI Level 3–5 và nằm ngoài phạm vi 10 tuần.

## 3. KHẢO SÁT SẢN PHẨM TƯƠNG TỰ VÀ KHOẢNG TRỐNG

### 3.1. Sản phẩm đang vận hành

| Hệ thống | Cách tiếp cận | Điểm mạnh | Khoảng trống so với đề tài |
| --- | --- | --- | --- |
| ETS SpeechRater | ASR + feature phát âm, fluency, vocabulary, grammar [4]. | Lịch sử vận hành, nghiên cứu validity. | Đóng, theo ngữ cảnh TOEFL; không cung cấp dữ liệu/mô hình mở để kiểm định người Việt A2–B2. |
| Speak & Improve | Người học trả lời speaking test và nhận CEFR grade tự động [5]. | Trải nghiệm hoàn chỉnh; corpus lớn; spontaneous speech. | Mô hình chấm đóng; không công bố sáu điểm CEFR cho người Việt. |
| Azure Pronunciation Assessment | Điểm accuracy, fluency, prosody [12]. | API rõ, word/phoneme granularity. | Trọng tâm pronunciation; paid/closed; không thay thế construct sáu tiêu chí. |
| SpeechAce | API spontaneous speech, CEFR mapping [13]. | Gần sản phẩm mong muốn, feedback chi tiết. | Black box, trả phí; chưa có kiểm định độc lập trên sinh viên Việt Nam. |

### 3.2. Nghiên cứu và mã nguồn công khai

| Công trình | Phạm vi | Giá trị | Giới hạn cần xử lý |
| --- | --- | --- | --- |
| GOPT + SpeechOcean762 [7][8] | Pronunciation đa khía cạnh; open code/data. | Baseline cho accuracy, fluency, prosody. | Chủ yếu L1 Mandarin, scripted; không chấm Range/Coherence/Interaction. |
| EvalYaks [3] | LoRA Mistral 7B chấm transcript B2. | LLM có thể bám rubric transcript. | Chỉ B2 và transcript; không có âm thanh; con số không so trực tiếp được với QWK trên dữ liệu Việt Nam. |
| Nebhi & Szaszák 2023 [14] | Multimodal audio + text, multitask CEFR. | Ủng hộ hướng fusion đa phương thức. | Không tạo benchmark công khai cho người Việt; kiến trúc nặng so với 10 tuần. |
| Cambridge spontaneous assessment [15] | 994 candidate, 6 L1 gồm Vietnamese. | Bằng chứng rằng confidence + back-off human là thiết kế hợp lý. | Dữ liệu không công khai; không tái lập trực tiếp được. |

### 3.3. Khoảng trống có thể bảo vệ

> KHOẢNG TRỐNG CHÍNH Chưa có một baseline công khai, dễ tái lập, được kiểm định trên sinh viên Việt Nam A2–B2 bằng sáu tiêu chí CEFR, có nhiều rater độc lập, speaker-level split, khoảng tin cậy được báo cáo đầy đủ, calibration, phân tích lỗi ASR/accent và teacher review.

- Không cạnh tranh trực tiếp với sản phẩm thương mại; đề tài cung cấp bằng chứng validity cục bộ và quy trình tái lập.

- EvalYaks là related work/baseline transcript, không phải source code để sao chép.

- GOPT/Azure có thể dùng làm pronunciation baseline hoặc external feature, không được gọi là điểm CEFR holistic.

- Đóng góp tập trung vào: đối tượng người Việt, task blueprint, rubric, rater protocol, uncertainty, precision analysis và error analysis.

## 4. KIẾN TRÚC KỸ THUẬT

Bản thử nghiệm dùng kiến trúc modular monolith, nghĩa là các chức năng chính cùng chạy trong một ứng dụng Python nhưng vẫn được chia thành các module rõ ràng. Cách này phù hợp với 10 tuần vì nhóm không phải vận hành nhiều dịch vụ riêng. Luồng đơn giản là: nhận audio → kiểm tra chất lượng → chuyển giọng nói thành văn bản → đo đặc trưng → chấm theo từng tiêu chí → tạo bằng chứng/phản hồi → chuyển ca khó cho giảng viên → xuất hồ sơ năng lực.

### 4.1. Luồng xử lý

- Tạo session: gán speaker_id giả danh, task_id, prompt_version, consent_version.

- Thu/nhận audio: lưu bản gốc ở kho hạn chế; tạo bản mono 16 kHz cho xử lý.

- Quality gate: duration, silence, clipping, noise proxy, language, response relevance sơ bộ.

- ASR: transcript_raw, word timestamps, confidence, model_version. Không chỉnh transcript bằng tay.

- Feature lanes: audio, text, interaction tạo độc lập với feature_version.

- Criterion scoring: mỗi tiêu chí trả probability A2/B1/B2; missing criterion giữ nguyên missing.

- Calibration/aggregation: học trong inner fold; overall là ordinal model, không phải trung bình cơ học.

- Evidence/feedback: chọn evidence đã lưu; feedback template là mặc định, LLM chỉ là stretch.

- Human review: low confidence, ASR risk, audio invalid hoặc criterion conflict vào teacher queue.

- Audit: lưu mọi *_version và decision log.

### 4.2. Feature lanes

| Lane | Feature bắt buộc | Dùng cho | Không được suy diễn |
| --- | --- | --- | --- |
| Audio | Duration, voiced ratio, articulation rate, pause count/ratio, run length, F0/rhythm summary. | Fluency, Phonology, quality diagnostics. | Không suy giới tính, cảm xúc, bệnh lý, tính cách, nguồn gốc. |
| Text | Lexical diversity/profile, syntax/error proxy, discourse markers, semantic relevance. | Range, Accuracy, Coherence, relevance. | Không coi transcript ASR là ground truth tuyệt đối. |
| Interaction | Turn count, latency client-side, completion, clarification, follow-up relevance, turn balance. | Interaction và task completion. | Không chấm nếu không có Task C. Không trộn system latency. |
| Quality | SNR proxy, clipping, silence, duration, ASR confidence/estimated risk. | Reject/review rule và error analysis. | Không dùng trực tiếp làm điểm năng lực. |

> Trần số chiều (mới ở v3.0): tối đa 20 feature cho mỗi tiêu chí, chọn bên trong fold. Với ~150 mẫu và 3 lớp, vượt trần này gần như chắc chắn overfit.

### 4.3. API

| Endpoint | Mục đích | Đầu vào chính | Đầu ra chính |
| --- | --- | --- | --- |
| POST /sessions | Tạo phiên đánh giá. | speaker_id, task_id, versions. | session_id, upload policy. |
| POST /responses | Upload/ghi nhận audio. | session_id, audio, metadata. | response_id, QC status. |
| POST /score | Chạy pipeline bất đồng bộ. | response_id, model_version. | job_id, status. |
| GET /reports/{id} | Xem báo cáo người học. | response/session id. | criteria, overall, evidence, flags. |
| POST /reviews | Giảng viên xác nhận/sửa. | rater_id, rating, reason. | review record, adjudication status. |
| GET /profiles/{learner_id} | Xuất hồ sơ năng lực nói đã kiểm duyệt. | learner_id, profile_version. | speaking_profile.json. |

## 5. TECH STACK VÀ LÝ DO CHỌN

> QUAN ĐIỂM CHỌN STACK Ưu tiên một ngôn ngữ Python cho ML và backend, giao diện mỏng, chạy local-first, tái lập thí nghiệm, ít dịch vụ vận hành. Không dùng microservices hoặc hạ tầng cloud phức tạp cho MVP.

| Lớp | Công nghệ chốt | Lý do chọn | Dự phòng |
| --- | --- | --- | --- |
| Ngôn ngữ | Python 3.11+ | Hệ sinh thái speech/ML mạnh. | — |
| API | FastAPI + Pydantic [16] | Type hints, validation, OpenAPI tự động. | Script batch nếu UI trễ. |
| Frontend | Streamlit | Nhanh tạo recorder, report, teacher queue. | Gradio hoặc HTML tối giản. |
| Audio | FFmpeg | Ổn định khi chuyển mono/16 kHz, batch. | soundfile/pydub. |
| VAD + ASR | Silero VAD + faster-whisper [17] | Timestamps/VAD, chạy local, cấu hình CPU/GPU. | Whisper nhỏ hơn. |
| Acoustic features | librosa + Parselmouth | Feature fluency/prosody minh bạch, dễ ablation. | Giữ feature tối thiểu. |
| Phonology | wav2vec2 GOP local | Không gửi audio ra ngoài; tính được trên CPU. | Chỉ prosody nếu GOP không ổn định. |
| Text features | spaCy/Stanza + sentence-transformers | Syntax/discourse/relevance không phụ thuộc LLM. | Handcrafted lexical baseline. |
| Scoring | scikit-learn + statsmodels (ordinal logistic) | Baseline mạnh với dữ liệu nhỏ; dễ giải thích. | Ordinal ridge; RF nông ≤ depth 5. |
| Feedback | Template grounded bằng evidence | Tái lập, giảm hallucination, bảo vệ dữ liệu. | LLM local opt-in là stretch. |
| Storage | SQLite + encrypted filesystem | Đủ cho nhóm nghiên cứu nhỏ; audio tách metadata. | PostgreSQL + MinIO. |
| Tracking | MLflow local + manifest/checksum [18] | Log config, metric, artifact, dataset reference. | CSV/JSON versioned. |
| Đóng gói | Docker Compose + pytest | Môi trường demo tái lập, test schema/audio/API. | Virtualenv + script offline. |

### 5.1. Vì sao không dùng LLM end-to-end làm bộ chấm chính

- LLM transcript-only không nghe được intelligibility, prosody, pause hoặc interaction timing.

- Điểm và giải thích thay đổi theo prompt/model version; khó tái lập nếu không khóa cấu hình.

- Lỗi ASR bị che giấu khi chỉ đưa transcript cho LLM.

- Dữ liệu audio/transcript gửi dịch vụ ngoài tạo rủi ro pháp lý và retention.

- LLM vẫn có giá trị như baseline B3 hoặc lớp diễn giải có evidence; không được tự tạo evidence.

### 5.2. Baseline B3 chạy local (thay đổi ở v3.0)

v2.0 có mâu thuẫn nội tại: mục 5 yêu cầu local-first nhưng mục 10.3 bắt buộc baseline “frozen rubric LLM”, mà nếu gọi API nước ngoài thì transcript người học rời khỏi máy nghiên cứu.

Quyết định: B3 chạy LLM local (Qwen2.5-7B-Instruct hoặc Llama-3.1-8B lượng tử hóa Q4, chạy được trên 16 GB RAM). Lợi ích: sạch về pháp lý, khóa được model version vĩnh viễn, tái lập tuyệt đối.

Nếu bắt buộc dùng API ngoài (chỉ khi local không chạy nổi), phải đủ 4 điều kiện: (i) consent chuyển dữ liệu riêng biệt, (ii) bước scrubbing tên riêng/địa danh trước khi gửi, (iii) chỉ gửi transcript — không bao giờ gửi audio, (iv) ghi vào data map và model card.

Thiết kế prompt phòng ngừa: Task A dùng đề kiểu “mô tả một bức tranh/tình huống” thay vì “kể về gia đình em”, để giảm khả năng transcript chứa thông tin định danh gián tiếp.

## 6. PHẠM VI ĐỀ TÀI

### 6.1. Trong phạm vi

- Tiếng Anh là ngoại ngữ của sinh viên đại học Việt Nam từ 18 tuổi; dải mục tiêu A2–B2.

- Ba loại nhiệm vụ A/B/C; Task C thu trên tập con, không suy Interaction từ monologue.

- Sáu tiêu chí CEFR và overall ước lượng; low-stakes/formative.

- Audio quality, ASR, feature extraction, criterion scoring, calibration, evidence, feedback, teacher review.

- Hai rater + một adjudicator; calibration/adjudication; human–human và AI–human evaluation.

- Precision analysis, reliability analysis và pre-registration.

- Web proof-of-concept chạy trên máy nghiên cứu; không yêu cầu SLA sản xuất.

Định nghĩa và xuất hồ sơ speaking_profile đã được giảng viên kiểm duyệt để các module khác có thể sử dụng.

### 6.2. Ngoài phạm vi

- Chứng chỉ CEFR, kỳ thi high-stakes, quyết định học vụ tự động.

- A1, C1, C2; trẻ vị thành niên; ngôn ngữ khác tiếng Anh.

- Speaker identification, emotion/personality inference, phát hiện gian lận bằng sinh trắc học.

- LMS đầy đủ, payment, proctoring, mobile native, hệ thống tuyển dụng.

- Chatbot hội thoại tự do; recommender học máy dài hạn.

- Huấn luyện ASR hoặc foundation model từ đầu.

Xây dựng hoàn chỉnh AI Conversation Partner, hệ thống luyện nghe thích ứng hoặc AI Orchestrator; đề tài chỉ cung cấp giao diện dữ liệu cho các hướng này.

### 6.3. MVP và stretch

| Mức | Hạng mục | Điều kiện chấp nhận |
| --- | --- | --- |
| MVP bắt buộc | Task A/B, QC, ASR, audio/text features, 5 tiêu chí khả dụng, overall, confidence, report, rater form, speaking_profile.json, baselines và đánh giá có khoảng tin cậy. | Hoàn tất trước cổng G8; demo end-to-end; đánh giá theo speaker. |
| MVP mở rộng | Task C + Interaction + teacher queue. | Chỉ giữ nếu prompt tree ổn định sau pilot W4. |
| Stretch | LLM feedback grounded, task recommendation, theo dõi tiến bộ hai phiên. | Chỉ bắt đầu sau khi vượt G8. |
| Loại bỏ đầu tiên | LMS, chatbot tự do, interview simulator, dashboard phức tạp. | Cắt ngay khi một cổng trễ. |

## 7. DỮ LIỆU

> KẾT LUẬN DỮ LIỆU Có dữ liệu người Việt nói tiếng Anh, nhưng chưa có corpus công khai đủ lớn với sáu nhãn CEFR và protocol nhiều rater phù hợp. Public data chỉ hỗ trợ ASR/pronunciation/sanity check; tập dữ liệu tự thu là bằng chứng kiểm định chính.

### 7.1. Dữ liệu có sẵn

| Nguồn | Quy mô/phủ | Nhãn | License | Vai trò |
| --- | --- | --- | --- | --- |
| L2-ARCTIC [9] | 24 người, 6 L1; 4 người Việt; scripted + một phần unscripted. | Transcript, lỗi phát âm; không CEFR. | CC BY-NC 4.0 | Test pipeline, accent robustness, ASR sanity. |
| Speech Accent Archive [10] | Nhiều L1, cùng đoạn đọc; lọc được Vietnamese. | Metadata, phonetic analysis. | CC BY-NC-SA 4.0 theo trang download chính thức kiểm tra 02/09/2026 | External accent check; không CEFR. |
| ICNALE Spoken [11] | Người học đại học châu Á; spoken modules hiện không liệt kê Việt Nam. Việt Nam xuất hiện ở Written Essays Plus, không phải speech. | CEFR-linked band dựa test/VST. | Đăng ký; cấm tái phân phối; cấm phân tích interviewer speech | Related work/task/rater research; không gọi là dữ liệu nói người Việt. |
| Speak & Improve Corpus 2025 [6] | ~315 giờ L2 spontaneous monologue; ~55 giờ có transcript. | Holistic CEFR-like score. | Non-commercial research, đăng ký, không tái phân phối | Auxiliary benchmark; source paper nói speaker có thể nằm ở cả train/test và không xác nhận Vietnamese subset, nên không dùng official split cho claim speaker-disjoint. |
| SpeechOcean762 [8] | 5.000 utterance, 250 speaker, chủ yếu Mandarin L1. | Phone/word/utterance pronunciation. | CC BY 4.0 | Pronunciation baseline; không đại diện người Việt. |

### 7.2. Dữ liệu tự thu (chỉnh ở v3.0)

Đối tượng tuyển là sinh viên đại học Việt Nam từ 18 tuổi, đang học tiếng Anh như ngoại ngữ và có trình độ dự kiến trong dải A2–B2. Bài sàng lọc chỉ dùng để cân bằng mẫu; nhãn chính vẫn do giảng viên chấm theo rubric.

| Hạng mục | v2.0 | v3.0 | Lý do |
| --- | --- | --- | --- |
| Số speaker | 40–60 | 70–90 (sàn cứng 60) | Nhiều speaker cho CI hẹp hơn ở cùng chi phí chấm (S4.5); nhóm 3 người có đủ nhân lực tuyển |
| Response/speaker | 2–3 | 2 (Task A + B), +Task C cho 25–30 người | Ràng buộc thật là năng lực chấm, không phải số người |
| Tổng response | 100–150 | 140–180 |  |
| Sàng lọc trình độ | Không | Có — VST hoặc điểm xếp lớp | Kiểm soát phân bố band; tạo trục convergent validity |
| Pilot | 8–12 người | 10–14 người |  |
| Chấm kép | “tối thiểu” | Mặc định: 100% confirmation set + 35% còn lại | Ước lượng lại giờ rater (S7.2) |
| Manual transcript | 20–30% (30–45 bài) | 15–20 bài, chép hoàn toàn từ đầu | Tránh bias do post-edit (S10) |
| Split | 60/20/20 | Repeated GroupKFold 5×5 + confirmation set 8–12 speaker | CI hẹp hơn 2.25 lần (S4.2) |

#### 7.2.1. Sàng lọc trình độ trước session

Một bài Vocabulary Size Test 10–15 phút (hoặc điểm xếp lớp có sẵn của trường) chạy trước khi ghi âm. Hai công dụng:

- Điều phối tuyển để tránh 70% mẫu dồn vào B1 — rủi ro làm sụp macro-F1 và khiến band A2 không ước lượng được.

- Convergent validity: báo cáo corr(AI overall, điểm sàng lọc) — một bằng chứng validity độc lập hoàn toàn với hai rater. Với chỉ hai rater, trần người rất mỏng; có thêm trục đo độc lập là cứu cánh nếu rater agreement thấp.

Điểm sàng lọc không được dùng làm nhãn huấn luyện và không hiển thị cho rater.

### 7.3. Quy trình thu và chấm

- Giải thích nghiên cứu, xin consent tự nguyện, gán speaker_id, tách bảng liên hệ khỏi audio.

- Chạy bài sàng lọc; lưu điểm vào bảng riêng, không hiển thị cho rater.

- Thu Task A + Task B; cách phân hai prompt tương đương phải chờ D014. Luân phiên một prompt/người không tạo cặp within-speaker để trả lời RQ6; quality gate ngay để ghi lại nếu invalid.

- Task C cho tập con 25–30 sinh viên, dùng prompt tree cố định.

- Random hóa thứ tự chấm, khác nhau cho từng rater; rater không thấy điểm AI, điểm sàng lọc, band tự khai hay điểm của rater kia.

- Calibration 60–90 phút; 2–3 anchor mỗi band; chấm thử 12–15 bài; tính QWK/ICC. QWK < 0.60 → không main collect.

- Chèn 5 bài lặp lại giữa và cuối đợt để đo intra-rater drift.

- Adjudicator thứ ba phân xử ca lệch ≥1 band ở overall hoặc ≥1 band ở ≥2 tiêu chí. Không lấy trung bình cơ học.

- Báo cáo agreement trước adjudication làm trần người; nhãn gold là phán quyết adjudicator.

- Khóa manifest, fold assignment và confirmation set trước khi train; confirmation set chạy đúng một lần ở W10.

### 7.4. Schema tối thiểu

| Nhóm | Trường bắt buộc |
| --- | --- |
| Identity (tách riêng) | participant_key, consent_version, contact, withdrawal_status |
| Screening (tách riêng) | participant_key, screening_score, screening_date |
| Response manifest | speaker_id, session_id, response_id, task_id, prompt_version, audio_uri, duration, qc_status, device_type, snr_proxy |
| ASR | asr_model, transcript_raw, word_timestamps, confidence, wer_manual_subset |
| Rating | rater_id, rubric_version, six criteria, overall, evidence, reason_codes, rating_started_at, adjudicated_label, adjudicator_id |
| Model output | model_version, fold_id, repeat_id, probabilities, calibration_version, review_reason, evidence_ids |
| Learning profile | learner_id, assessed_at, rubric_version, model_version, overall, six criteria, confidence, evidence_refs, weakest_criteria, next_task_hint, teacher_verified |

## 8. PHÁP LÝ VÀ ĐẠO ĐỨC

Tại thời điểm 22/08/2026, Luật Bảo vệ dữ liệu cá nhân số 91/2025/QH15 có hiệu lực từ 01/01/2026 [19], và Nghị định 356/2025/NĐ-CP quy định chi tiết thi hành [20]. Audio, transcript, metadata và điểm đánh giá có thể là dữ liệu cá nhân; dữ liệu giọng nói cần bảo vệ nghiêm ngặt. Nội dung dưới đây là thiết kế tuân thủ thực hành, không thay thế tư vấn pháp lý hoặc quy trình ethics của trường.

### 8.1. Yêu cầu tối thiểu

| Nguyên tắc | Cách áp dụng |
| --- | --- |
| Mục đích cụ thể | Consent nêu rõ thu audio để nghiên cứu đánh giá Speaking A2–B2; không tái dùng cho nhận dạng giọng nói. |
| Tối thiểu hóa | Không thu CCCD, địa chỉ, dữ liệu sức khỏe; giới tính/chứng chỉ chỉ khi tự nguyện. |
| Tự nguyện | Không gắn quyền tham gia với điểm môn học; được từ chối/rút không chịu bất lợi. |
| Quyền dữ liệu | Cơ chế xem, sửa metadata, rút consent, xóa raw audio trong thời hạn công bố. |
| Lưu trữ | Audio mã hóa, access theo vai trò, log truy cập, backup kiểm soát; không commit Git. |
| Thời hạn | Xóa raw audio tối đa 12 tháng sau bảo vệ hoặc sớm hơn theo chính sách trường. |
| Chuyển dữ liệu | Xử lý local là mặc định. Mọi ngoại lệ cần consent riêng + scrubbing + chỉ transcript (xem 5.2). |
| Sự cố | Đầu mối báo cáo, thu hồi quyền truy cập, đánh giá ảnh hưởng. |

### 8.2. Đạo đức đánh giá

- Không dùng kết quả như chứng chỉ, điểm thi chính thức hoặc căn cứ duy nhất cho quyết định học vụ.

- Không phạt accent Việt nếu intelligibility bảo đảm; không lấy “native-like” làm mục tiêu.

- Không suy diễn giới tính, dân tộc, cảm xúc, sức khỏe, tính cách từ giọng nói.

- Công bố confidence, failure modes và population đã kiểm chứng.

- Rater chấm mù; người học biết có AI, dữ liệu nào được lưu, khi nào có người duyệt.

- Subgroup analysis chỉ khi consent và đủ n; không công bố bảng có ô < 5 người.

- License inventory cho từng corpus, model và API.

### 8.3. Checklist trước khi thu

- ☐ Văn bản chấp thuận của GVHD hoặc hội đồng ethics theo quy định trường

- ☐ Consent, participant information sheet, quy trình rút/xóa đã duyệt

- ☐ Data map chỉ rõ nơi lưu audio, transcript, identity key, screening score, rating, backup

- ☐ Tài khoản rater riêng; kho dữ liệu không public; secret không nằm trong repo

- ☐ License inventory cho từng corpus/model/API

- ☐ Model card/datasheet có prohibited uses và retention

## 9. KẾ HOẠCH 10 TUẦN VÀ PHÂN CÔNG

### 9.1. Phân công nhóm 3 người

> Giả định cần GVHD xác nhận: đề tài do nhóm 3 sinh viên thực hiện. Nếu thực tế là 1 sinh viên, phải cắt Task C và giảm mục tiêu mẫu xuống 45–55 speaker; xem 9.5.

| Vai trò | Phụ trách chính | Sản phẩm sở hữu |
| --- | --- | --- |
| SV1 — Speech pipeline | Ingest, FFmpeg, VAD, ASR, forced alignment, GOP/prosody, audio feature lane, WER protocol | Chương 4 (phần pipeline), phụ lục feature dictionary |
| SV2 — Đo lường & mô hình | Vận hành hóa rubric do giảng viên Ngoại ngữ thiết lập, xây công cụ cho người chấm, text/interaction feature, scoring, calibration, toàn bộ evaluation và thống kê | Chương 3, Chương 5, Phụ lục S |
| SV3 — Sản phẩm & tích hợp | FastAPI, Streamlit, teacher queue, report/evidence, Docker, tổ chức thu dữ liệu, consent/ethics, usability test | Chương 4 (phần hệ thống), phụ lục API/consent |

Việc chung không chia được: thiết kế task/prompt (cả nhóm, W2), error analysis 25 ca (chia 3, chéo kiểm), Chương 1/2/6/7 (chủ biên luân phiên).

### 9.2. Lịch 10 tuần — hai lane song song

Điểm khác biệt lớn nhất so với v2.0: lane viết luận văn chạy từ W1, không dồn vào W10. Mục 15 dự kiến 108–156 trang; không ai viết được số đó trong một tuần.

| Tuần | Lane KỸ THUẬT | Lane VIẾT | Cổng |
| --- | --- | --- | --- |
| W1 | Đọc CEFR; GV Ngoại ngữ chủ trì chốt rubric/anchor; nhóm CNTT chốt tên/RQ/phạm vi và vận hành hóa yêu cầu; xác nhận 2 rater + 1 adjudicator; draft consent/data plan; nộp hồ sơ ethics. | Chương 1 (100%) | G1: GVHD duyệt phạm vi, RQ, vai trò rater/adjudicator, kế hoạch dữ liệu |
| W2 | Pedagogy Lab thiết lập rubric A2/B1/B2 và task; Tech Lab chuyển thành bảng chấm, reason codes, schema, prompt bank; chốt interlocutor và cách đo latency Task C. | Chương 2 (100%) | G2: rater giải thích được điểm; mỗi tiêu chí có task tạo evidence; thiết kế Task C đã test |
| W3 | Vertical slice: recorder/upload, FFmpeg, QC, faster-whisper, transcript/timestamp, feature cơ bản, report JSON, loader L2-ARCTIC; chốt B3 local vs API | Chương 3 (70%) | G3: một response 2 phút chạy end-to-end, không lộ danh tính |
| W4 | Pilot 10–14 sinh viên; test completion/QC/ASR; double-rate; tính agreement; sửa prompt/rubric; khóa v1; theo dõi tỷ lệ invalid theo band (floor effect Task B) | Chương 3 (100%) | G4: completion ≥85%; QWK human–human ≥0.60, nếu thấp hơn thì chưa main collect |
| W5 | Main collection 1: 30–40 sinh viên; QC hằng ngày; rater chấm cuốn chiếu; theo dõi band/device/noise | Chương 4 (50%) | G5: metadata đầy đủ ≥90%; invalid có reason; không PII trong model workspace |
| W6 | Main collection 2: đạt 70–90 sinh viên; adjudication; manual transcript 15–20 bài; human agreement; khóa fold assignment + confirmation set + bảng pre-registration | Chương 4 (100%) | G6: dataset_v1 khóa, không speaker leakage, pre-registration đã ký |
| W7 | B0 majority; B1 audio; B2 transcript; B3 LLM local; feature dictionary; nested CV; metric/confusion/error list | Chương 5 — dựng bảng trống | G7: ít nhất một baseline hơn B0; chạy tái lập bằng script |
| W8 | Late fusion/ordinal M1; calibration Platt; threshold review; 5 ablation; paired cluster bootstrap; WER–error; phân tích 25 ca lỗi | Chương 5 (70%) | G8: M1 so với toàn bộ baseline bằng paired bootstrap; chọn model tốt nhất, không chọn theo độ phức tạp |
| W9 | Report evidence; teacher queue; xuất speaking_profile; đo RQ6; Living Lab usability với 6–8 sinh viên + 2 giảng viên; khóa API/UI/model. | Chương 5 (100%) + Chương 6 (60%) | G9: workflow hoàn tất; feedback không bịa; low-confidence chuyển review |
| W10 | Khóa code/config; chạy confirmation set đúng 1 lần; plots/CI; model card/datasheet; demo offline | Chương 6 (100%) + Chương 7 + slide | G10: máy sạch chạy theo README; slide khớp báo cáo; giới hạn nêu rõ |

Nguyên tắc: Chương 1–3 phải xong ~90% trước main collection. Chúng chỉ mô tả những gì đã quyết định — không phụ thuộc kết quả.

### 9.3. Ánh xạ kế hoạch 10 tuần theo mô hình Living Lab

Ba phòng lab không phải ba dự án riêng. Đây là cách phân vai để chuẩn ngôn ngữ, công nghệ và dữ liệu lớp học được kiểm tra lẫn nhau. Mỗi đầu việc chỉ hoàn tất khi đúng bên chịu trách nhiệm đã xác nhận.

| Lab | Đơn vị/vai trò | Công việc trong đề tài | Tuần |
| --- | --- | --- | --- |
| Pedagogy Lab | Giảng viên/Khoa Ngoại ngữ | Thiết lập và sở hữu rubric, chọn anchor, thiết kế nhiệm vụ, hiệu chuẩn người chấm, phân xử và duyệt gợi ý luyện tập. | W1–W2, W4–W6, W9 |
| Tech Lab | Nhóm sinh viên Khoa CNTT | Vận hành hóa rubric; xây pipeline audio/ASR/feature/model; calibration; API/UI; kiểm thử; xuất speaking_profile. | W1–W10 |
| Living Lab | Lớp tiếng Anh thực tế | Pilot, thu dữ liệu chính, thử hàng đợi giảng viên, kiểm tra cách sinh viên hiểu phản hồi và khả năng sử dụng. | W4–W6, W9 |

> Điểm kiểm soát: rubric chỉ được khóa sau khi Pedagogy Lab duyệt; dữ liệu chính chỉ được thu sau pilot Living Lab; mô hình chỉ được chốt sau khi Tech Lab báo cáo đầy đủ sai số và các trường hợp cần người duyệt.

### 9.4. Quy tắc cắt phạm vi

| Tình huống | Hành động |
| --- | --- |
| Trễ G2 | Bỏ Task C khỏi MVP; không báo cáo Interaction |
| Hết W3 chưa được phép thu dữ liệu | Chỉ tiếp tục pipeline/sanity check trên L2-ARCTIC, Speech Accent Archive hoặc corpus đã duyệt license. Không được biến public read-speech không CEFR thành exploratory validation trên sinh viên Việt Nam; claim chính tạm `BLOCKED/NOT EVALUATED` cho đến khi có dữ liệu đúng population/protocol. |
| QWK human–human < 0.60 ở G4 | Dành trọn W5 sửa rubric/anchor; giảm tuyên bố thành exploratory prototype |
| < 45 speaker ở G6 | Giữ GroupKFold nhưng công bố CI rộng và không tuyên bố generalization; dồn trọng tâm vào rater study + error analysis |
| Fusion không hơn baseline ở G8 | Chọn baseline đơn giản tốt nhất, giải thích bằng ablation; không thêm deep model phút cuối |
| UI trễ ở G9 | Giữ Streamlit tối giản; không hy sinh evaluation để làm giao diện |
| Lane viết trễ 2 tuần liên tiếp | Cắt toàn bộ stretch, SV3 chuyển sang hỗ trợ viết |

### 9.5. Nếu đề tài do 1 sinh viên thực hiện

Cắt: Task C và toàn bộ tiêu chí Interaction; teacher queue rút gọn thành export CSV; mục tiêu mẫu giảm còn 45–55 speaker; bỏ usability test chính thức, thay bằng 3 phỏng vấn ngắn. Giữ nguyên toàn bộ thiết kế thống kê ở Phụ lục S — đó là phần không được cắt.

## 10. TIÊU CHÍ NGHIỆM THU VÀ PHƯƠNG PHÁP ĐÁNH GIÁ

### 10.1. Điều kiện nghiệm thu chức năng

- Ghi âm/upload, QC, ASR, scoring và report chạy end-to-end; lỗi trả reason code thay vì điểm giả.

- Report có criterion, overall, confidence, evidence, version và human-review flag.

- Rater form và teacher queue lưu được điểm độc lập, reason và adjudication.

- Dữ liệu nhạy cảm không nằm trong Git; có consent/retention status, role-based access, deletion procedure.

- Repo có README, config/seed, test schema/audio/API, sample không nhạy cảm và demo offline.

- Toàn bộ bảng metric tái tạo được bằng một lệnh từ manifest đã khóa.

Xuất được speaking_profile.json đúng schema; teacher_verified chỉ là true sau khi giảng viên xác nhận hoặc theo quy tắc duyệt đã công bố.

### 10.2. Ngưỡng và cách diễn giải (sửa lớn ở v3.0)

Hiểu đơn giản: AI không cần giống tuyệt đối một giảng viên, vì chính hai giảng viên cũng có thể chấm khác nhau. Do đó, nghiên cứu đo “trần con người” trước, rồi xem AI đạt được bao nhiêu phần so với trần đó. QWK đo mức đồng thuận; khoảng tin cậy cho biết kết quả còn bất định đến mức nào; calibration cho biết confidence của AI có đáng tin hay không.

| Hạng mục | Metric | Ngưỡng v3.1 | Cách dùng |
| --- | --- | --- | --- |
| Trần người | QWK/ICC human–human, tính trước adjudication | ≥0,60 để main collect; mục tiêu ≥0,70 | Nếu thấp: sửa rubric/anchor, chấm lại pilot |
| Chỉ tiêu chính | Agreement Ratio = QWK(AI,gold) / QWK(r1,r2) | ≥0,85 | Tự chuẩn hóa theo độ khó dữ liệu; là câu trả lời cho “0,60 lấy ở đâu ra” |
| Đồng thuận tuyệt đối | QWK(AI,gold) + 95% cluster bootstrap CI | Báo cáo kèm CI, không ngưỡng cứng | So với trần người, không so với con số tuyệt đối |
| Lỗi nghiêm trọng | Gross Error Rate (lệch 2 band, A2↔B2) | ≤5% | Thay thế adjacent accuracy đã bị loại bỏ |
| Sai số band | MAE(AI) / MAE(human–human) | ≤1,30 | Tương đối, không tuyệt đối |
| Cân bằng lớp | Macro-F1 + confusion matrix | M1 > B0 với paired bootstrap CI loại trừ 0 | Không báo accuracy đơn thuần khi band lệch |
| Calibration | Brier, ECE 5 bin, reliability curve — tính trên OOF (n≈160) | ECE ≤0,15 | Với n nhỏ, đọc curve định tính là chính |
| Ngưỡng review | Yield của human-review queue | Bắt ≥70% gross error khi flag ≤25% response | Trình bày bằng đường cong yield–flag rate |
| Reliability AI | Parallel-form r giữa 2 prompt Task A | ≥0,70 | Mới ở v3.0 (RQ6) |
| ASR | WER trên 15–20 bài chép tay from scratch | Báo cáo, không đặt ngưỡng | Tạo ASR-risk flag; ước lượng upper bound |
| Convergent validity | corr(AI overall, điểm sàng lọc) | Báo cáo; kỳ vọng 0,45–0,70 | Trục đo độc lập với rater |
| Hiệu năng | Xử lý response 2 phút trên máy tham chiếu | ≤60 giây | Không tuyên bố real-time nếu chưa đo |

> Ba ngưỡng của v2.0 đã bị loại và lý do: (a) Adjacent accuracy ≥80% — với 3 band, “adjacent” chỉ loại trừ lỗi A2↔B2, nên một model luôn đoán B1 đạt 100%. Ngưỡng này thấp hơn baseline tầm thường. (b) MAE ≤0,50 tuyệt đối — với phân bố 30/40/30, model luôn đoán B1 có MAE 0,60; ngưỡng cũ chỉ tốt hơn 17%. (c) ECE ≤0,15 trên test set — 25–30 điểm chia 10 bin là vô nghĩa; chuyển sang OOF.

Lưu ý: mọi mốc trên là mục tiêu quản trị đề tài để quyết định cổng tiến độ. Council of Europe không ban hành các mốc này cho hệ thống AI.

### 10.3. Thiết kế thực nghiệm bắt buộc

| # | Quy định | Chi tiết ở |
| --- | --- | --- |
| 1 | Repeated Stratified GroupKFold 5×5, nhóm theo speaker_id; báo cáo trên out-of-fold predictions | S3.2 |
| 2 | Confirmation set 8–12 speaker, chạy đúng một lần ở W10, không phải nguồn số liệu chính | S3.2 |
| 3 | Nested CV: mọi bước chọn feature, scaling, tune, calibration, chọn ngưỡng nằm trong inner fold | S3.3 |
| 4 | Baseline: B0 majority; B1 audio-only; B2 transcript-only; B3 frozen rubric LLM local; M1 late fusion + calibration | S5 |
| 5 | Cluster bootstrap theo speaker, 2000 vòng, seed 0 cho mọi CI | S6.1 |
| 6 | Paired cluster bootstrap trên hiệu số khi so hai model — không so hai CI độc lập | S6.2 |
| 7 | Một so sánh khẳng định duy nhất: M1 vs. baseline unimodal tốt nhất, trên overall. Mọi so sánh khác là exploratory | S6.3 |
| 8 | Ablation A1–A5, trong đó A4 (bỏ duration + prompt_id) kiểm tra model có shortcut không | S11.3 |
| 9 | Error taxonomy 25 ca, 8 mã lỗi, có kiểm chứng chéo | S11.1 |
| 10 | Subgroup theo band/noise/device; demographic chỉ khi consent và đủ n | S11.2 |
| 11 | Trần 20 feature/tiêu chí, chọn trong fold | 4.2 |
| 12 | Bảng pre-registration ký tại G6 trước khi train | S12 |

> Vì sao thay đổi số 1 và 6 là quan trọng nhất. Mô phỏng Monte Carlo (400 lần, seed cố định, script nộp kèm repo):

| Thiết kế | Độ rộng 95% CI của QWK |
| --- | --- |
| Single holdout 10 speaker (v2.0) | 0,564 → QWK 0,60 nghĩa là CI [0,32; 0,88] |
| OOF repeated GroupKFold 50 speaker (v3.0) | 0,251 → CI [0,48; 0,73] |

| Cách so sánh hai model (ΔQWK thật = 0,11) | Khả năng phát hiện |
| --- | --- |
| Paired cluster bootstrap | 47% |
| Hai CI độc lập, xem có chồng lấn | 1% |

> Đổi thiết kế đánh giá làm CI hẹp hơn 2,25 lần mà không tốn thêm một đồng chi phí thu dữ liệu nào.

## 11. ĐÓNG GÓP KHOA HỌC

| Mã | Đóng góp | Sản phẩm |
| --- | --- | --- |
| C1 | Vận hành hóa construct | Rubric A2–B2 sáu tiêu chí, blueprint nhiệm vụ, evidence guide, anchor, quy tắc missing/adjudication |
| C2 | Dữ liệu cục bộ | Tập dữ liệu người học Việt Nam ẩn danh, có consent, task/prompt version, nhãn 2 rater + adjudicator, manifest, datasheet, WER subset |
| C3 | Kiến trúc có thể giải thích | Pipeline late fusion tách audio/text/interaction, calibration, evidence grounding, human review, ASR-risk flag |
| C4 | Bằng chứng thực nghiệm có khoảng tin cậy | Baseline/fusion/ablation trên speaker split; AI–human và human–human agreement; precision analysis công bố trước; confidence/error/ASR analysis |
| C5 | Bài học cho accent Việt | Phân tích lỗi ASR và điểm theo điều kiện âm thanh; taxonomy failure modes |
| C6 | Protocol tái lập cho nghiên cứu speech assessment quy mô nhỏ | Phụ lục S: thiết kế CV, paired bootstrap, MDE, pre-registration — dùng lại được cho các đề tài cùng dạng |
| C7 | Giao diện dữ liệu cho hệ sinh thái học tập | Schema speaking_profile có version, bằng chứng, confidence, trạng thái giảng viên kiểm duyệt và gợi ý nhiệm vụ tiếp theo. |

### 11.1. Ranh giới tính mới

Tính mới không nằm ở Whisper, FastAPI hay việc gọi LLM. Tính mới có thể bảo vệ nằm ở sự kết hợp có kiểm soát giữa CEFR construct, dữ liệu người Việt, rater validation, đa phương thức, calibration, human review và kỷ luật thống kê được công bố trước. Nếu M1 không vượt baseline, khóa luận vẫn có đóng góp nếu phân tích được trần người, lỗi ASR, construct coverage và điều kiện thất bại một cách tái lập.

> TUYÊN BỐ PHÙ HỢP: Trên tập sinh viên Việt Nam A2–B2 và các nhiệm vụ đã thiết kế, mô hình X đạt Agreement Ratio Y so với trần giảng viên (95% CI …), cải thiện/không cải thiện so với baseline Z ở mức ΔQWK … (95% CI …); confidence và error analysis chỉ ra các điều kiện cần human review.

> TUYÊN BỐ CẦN TRÁNH: Hệ thống chấm CEFR chính xác cho mọi người Việt; thay thế giám khảo; không thiên lệch; đạt chuẩn Council of Europe; hoạt động cho mọi task/accent/thiết bị. Và: “không có khác biệt giữa hai model” khi thực chất là “không đủ độ nhạy để kết luận”.

## 12. ĐÁNH GIÁ TÍNH KHẢ THI

| Khía cạnh | Mức | Cơ sở | Điều kiện |
| --- | --- | --- | --- |
| Kỹ thuật | Cao | ASR, feature toolkit, ordinal ML, web prototype đều có công cụ mở | Giữ modular monolith; không train foundation model; fallback CPU |
| Dữ liệu | Trung bình | Public data hỗ trợ nhưng gold Vietnamese phải tự thu | Xác nhận kênh tuyển W1; pilot W4; ≥60 speaker hoặc giảm claim |
| Nhãn/rater | Trung bình–thấp | 2 rater + 1 adjudicator là nút thắt lớn nhất; ~25 giờ/rater, không phải 8–14 | Khóa lịch từ W1; chấm kép 100% confirmation + 35% còn lại |
| Pháp lý | Trung bình | Luật 91/2025 và NĐ 356/2025 đang hiệu lực | Consent, local-first, data map, retention, phê duyệt trước W4 |
| Thời gian | Trung bình | 10 tuần đủ cho PoC nếu viết song song từ W1 | Cổng G1–G10; hai lane; cắt Task C/LLM/UI khi trễ |
| Khoa học | Cao có điều kiện | RQ đo được; có baseline, trần người, ablation, error analysis, MDE công bố trước | Không overclaim; báo CI, limitations, population |
| Vận hành | Cao cho demo | Streamlit/FastAPI/Docker đủ cho một máy/lab | Không hứa SLA, scale, mobile production |

> KẾT LUẬN: Đề tài khả thi ở mức proof-of-concept nghiên cứu có kiểm định. Ba điều kiện quyết định không phải GPU mà là: (1) rubric tốt và 2 rater cam kết đủ giờ, (2) quyền thu audio được phê duyệt trước W4, (3) luận văn được viết song song từ W1.

### 12.1. Nguồn lực tối thiểu

- Máy 16 GB RAM; 40–60 GB lưu trữ riêng; GPU 6–8 GB là lợi thế, không bắt buộc.

- 2 rater × ~25 giờ + 1 adjudicator × ~5 giờ. (v2.0 ước 8–14 giờ/rater là thấp hơn thực tế khoảng 2 lần: 160 response × 6–10 phút ≈ 20 giờ, cộng calibration và adjudication.)

- Không gian thu tương đối yên tĩnh; ít nhất 2 loại thiết bị để kiểm tra robustness.

- Kênh tuyển 70–90 sinh viên đã được cho phép trước W1.

- Repo riêng; kho dữ liệu hạn chế; backup; một máy demo offline.

- GVHD duyệt scope, ethics, protocol và các cổng G1/G4/G6/G8/G10.

## 13. RỦI RO VÀ DỰ PHÒNG

| Rủi ro | Tín hiệu sớm | Phòng ngừa | Dự phòng |
| --- | --- | --- | --- |
| Chậm phê duyệt ethics | W2 chưa có phản hồi | Nộp hồ sơ ngày đầu W1; hỏi quy trình trước khi viết | Hết W3 chưa được phép → chuyển sang public data, giảm claim |
| Không đủ giờ rater | Chưa khóa lịch ở W1 | Giới hạn 160 response; form chấm gọn; evidence chỉ cho ca adjudication | Giảm còn 120 response; chấm kép 100% confirmation + 25% |
| Agreement thấp | Pilot QWK <0,60 | Anchor, rater guide, calibration, reason codes | Thu hẹp rubric; exploratory study |
| Thu mẫu chậm | <30 speaker cuối W5 | Nhiều kênh tuyển đã được phép; lịch thu cố định | Ưu tiên speaker hơn Task C; bỏ stretch |
| Band lệch | Một band <20% mẫu ở W5 | Bài sàng lọc điều phối tuyển | Class weights; macro-F1; không oversample trước khi chia fold |
| Floor effect Task B ở A2 | Tỷ lệ invalid ở band A2 cao bất thường tại pilot | 30 giây chuẩn bị + 3 bullet gợi ý | Cho phép prompt đơn giản hơn cho A2, ghi làm biến kiểm soát |
| ASR sai accent Việt | WER cao, transcript vô nghĩa | Benchmark local từ W1; VAD/QC; manual subset | Audio-only model; ASR-risk flag; upper bound bằng transcript tay |
| Thiếu GPU | ASR/model quá chậm | faster-whisper small/base, batch, quantization | CPU batch; giảm embedding |
| Overfit do n nhỏ | Kết quả CV tốt bất thường (QWK >0,80) | Trần 20 feature; nested CV; ablation A4 | Rút về ordinal logistic 5–8 feature; báo cáo trung thực |
| Fusion không hơn baseline | Dev result không cải thiện | Ablation, regularization, feature audit | Chọn model đơn giản; đóng góp từ negative result |
| Feedback bịa | Không truy được evidence | Template mặc định; evidence IDs; deterministic rules | Tắt LLM; chỉ hiển thị evidence + khuyến nghị chuẩn hóa |
| Lane viết tụt hậu | Cuối W4 chưa xong Chương 1–3 | Chủ biên luân phiên; deadline tuần | Cắt toàn bộ stretch; SV3 chuyển sang viết |
| Scope creep | Thêm LMS/chatbot/mobile trước G8 | MVP gate và backlog stretch riêng | Cắt ngay; demo tối giản |
| Demo lỗi | Phụ thuộc internet/API | Docker, cached model, sample offline, rehearsal | Video/JSON/slide backup |

## 14. CÂU HỎI HỘI ĐỒNG VÀ CÁCH TRẢ LỜI

Q1. Vì sao không dùng Whisper rồi đưa transcript cho ChatGPT chấm? Transcript-only không chứa pause, prosody, intelligibility và interaction timing. LLM có thể là baseline/feedback layer, nhưng điểm chính phải kết hợp audio, text và interaction, hiệu chỉnh trên nhãn giảng viên.

Q2. Dựa vào đâu để nói hệ thống theo CEFR? Dựa trên CEFR Companion Volume 2020 [1], sáu tiêu chí, task blueprint, rubric A2/B1/B2, anchor và validation với rater. Đề tài chỉ nói aligned/hỗ trợ đánh giá, không tuyên bố được Council of Europe chứng nhận.

Q3. Điểm mới là gì khi EvalYaks và SpeechAce đã tồn tại? EvalYaks chấm transcript B2; SpeechAce là API đóng. Đề tài cung cấp quy trình tái lập và bằng chứng cục bộ cho người Việt A2–B2: nhiều rater, fusion audio/text/interaction, ASR/accent error, calibration, human review và precision analysis công bố trước.

Q4. 70–90 người có quá ít để làm AI không? Quá ít để huấn luyện foundation model hoặc tuyên bố tổng quát rộng, nhưng đủ cho PoC nếu dùng pretrained features, model đơn giản, GroupKFold, cluster bootstrap CI và báo giới hạn. Chúng em đã mô phỏng trước độ chính xác đạt được: CI của QWK rộng khoảng 0,22–0,25, và chỉ phát hiện được chênh lệch ΔQWK ≥ 0,16. Con số đó được công bố trong đề cương, trước khi thu dữ liệu.

Q5. Tại sao chỉ A2–B2? Đây là dải phổ biến trong sinh viên và giảm sparsity/độ phức tạp rubric. A1/C1/C2 cần task, anchor và dữ liệu khác.

Q6. Overall được tính bằng trung bình sáu tiêu chí? Không. Hệ thống giữ probability theo criterion và dùng ordinal aggregation học từ overall của rater. Missing Interaction không bị điền 0.

Q7. Vì sao dùng QWK? Band A2–B1–B2 có thứ tự, và lỗi lệch hai band nghiêm trọng hơn lệch một band. QWK phản ánh thứ tự tốt hơn accuracy. Vẫn báo MAE, macro-F1, Gross Error Rate và confusion matrix.

Q8. QWK 0,60 có phải chuẩn CEFR? Không, và ở v3.0 chúng em không còn dùng ngưỡng tuyệt đối làm chỉ tiêu chính. Chỉ tiêu chính là Agreement Ratio = QWK(AI,gold)/QWK(rater1,rater2) ≥ 0,85 — tức AI đạt bao nhiêu phần trăm trần đồng thuận của chính con người. Cách này tự chuẩn hóa theo độ khó thực tế của dữ liệu.

Q9. Nếu ASR nhận sai giọng Việt thì sao? Đo WER trên 15–20 bài chép tay hoàn toàn từ đầu, phân tích tương quan WER–sai số, giữ audio-only baseline, tạo ASR-risk flag và chuyển review.

Q10. Hệ thống có thiên vị accent không? Không thể khẳng định “không thiên vị” từ mẫu nhỏ. Đề tài dùng intelligibility thay native-likeness, kiểm tra lỗi theo điều kiện có đủ n và công bố failure modes; accent không bị trừ nếu thông điệp rõ.

Q11. Interaction được chấm thế nào? Chỉ từ Task C, dùng prompt tree cố định để mọi thí sinh gặp cùng tập kích thích. Latency đo ở client từ thời điểm kết thúc phát prompt; system latency log riêng và không đưa vào feature. Nếu chỉ có monologue, báo “chưa đủ bằng chứng”.

Q12. Tại sao không dùng deep multimodal transformer? Dữ liệu nhỏ và thời gian 10 tuần làm mô hình lớn dễ overfit và khó giải thích. Late fusion với pretrained features tạo baseline nghiêm túc, ablation rõ, dễ tái lập.

Q13. Dữ liệu công khai có đủ không? Không đủ cho gold validation người Việt. L2-ARCTIC/Speech Accent Archive hỗ trợ accent/ASR, SpeechOcean hỗ trợ pronunciation, Speak & Improve hỗ trợ benchmark; gold labels vẫn phải tự thu.

Q14. Pháp lý xử lý audio ra sao? Consent theo mục đích, mã giả danh, identity tách riêng, local-first, mã hóa/quyền truy cập, retention/xóa, quyền rút, không dùng speaker identification; theo Luật 91/2025/QH15 [19] và Nghị định 356/2025 [20].

Q15. Nếu model không đạt target thì khóa luận có thất bại? Không, nếu protocol đúng và phân tích được trần người, baseline, confidence, lỗi ASR, task/rubric và giới hạn. Negative result có giá trị hơn một accuracy cao do leakage hoặc test tuning.

Q16. Hệ thống có thay giảng viên không? Không. AI chấm điểm sơ bộ theo rubric do giảng viên thiết lập, nêu bằng chứng và gắn cờ ca khó. Giảng viên sở hữu chuẩn chấm, kiểm duyệt và quyết định cuối cùng; đặc biệt hệ thống không tự dùng kết quả cho quyết định học vụ.

### 14.1. Năm câu hỏi bổ sung ở v3.0

Q17. Em đo độ ổn định của chính hệ thống AI như thế nào, không chỉ đồng thuận với giảng viên? Ba cách (RQ6): (i) parallel-form — Task A có hai prompt tương đương, đo tương quan điểm AI giữa hai prompt của cùng người, mục tiêu r ≥ 0,70; (ii) ổn định thuật toán — chạy lại với 5 seed, SD của QWK ≤ 0,03; (iii) ổn định trước nhiễu — thêm nhiễu trắng ở SNR 20 dB, ≤15% speaker đổi band. Parallel-form còn đặt trần trên cho QWK có thể đạt được: nếu chính con người chấm cùng một người ở hai prompt chỉ tương quan 0,65 thì không AI nào vượt được mức đó.

Q18. Feature selection làm trước hay sau khi chia dữ liệu? Bên trong fold, không có ngoại lệ. Chuẩn hóa, chọn feature, tune hyperparameter, học calibration map và chọn ngưỡng confidence đều nằm trong inner 4-fold của nested CV. Chọn feature trên toàn bộ dữ liệu rồi mới CV có thể thổi phồng kết quả 10–20 điểm QWK.

Q19. Với ~160 mẫu mà dùng embedding nghìn chiều thì overfit chắc chắn — em kiểm soát thế nào? Trần cứng 20 feature/tiêu chí, chọn bằng correlation filter + L1 trong fold. Ưu tiên ordinal logistic regression thay vì gradient boosting. Mỗi feature phải giải thích được bằng ngôn ngữ rubric qua feature dictionary. Ablation A4 (bỏ duration và prompt_id) kiểm tra model có shortcut không.

Q20. Ai là người phân xử khi hai giảng viên lệch nhau? Một adjudicator thứ ba được chỉ định từ cổng G1, không tham gia chấm vòng đầu. Agreement human–human được báo cáo trước adjudication để phản ánh trần người thật; nhãn gold là phán quyết của adjudicator. Nếu hai rater tự thảo luận thống nhất, nhãn gold sẽ không còn độc lập với chính chỉ số agreement đang báo cáo.

Q21. Task B “nêu quan điểm” có quá khó với người học A2 không? Có, và đây là floor effect thật. Biện pháp: 30 giây chuẩn bị, prompt kèm 3 bullet gợi ý, ghi lại prep time làm biến kiểm soát, và theo dõi tỷ lệ QC-invalid theo band ngay từ pilot W4. Nếu band A2 có tỷ lệ invalid cao bất thường, prompt sẽ được đơn giản hóa và ghi nhận như một biến thiết kế.

Q22. Đề tài nằm ở đâu trong ALDM-L? Đề tài nằm ở ô Speaking × Assess × AI Assessor, thuộc Nhóm 1. D1–D8 đã được chỉ rõ; AI ở Level 2; mô hình triển khai gồm Pedagogy Lab, Tech Lab và Living Lab.

Q23. Dữ liệu tạo ra được dùng thế nào để điều chỉnh việc học? Sau khi giảng viên kiểm duyệt, hệ thống xuất speaking_profile gồm sáu tiêu chí, confidence, bằng chứng, tiêu chí yếu và next_task_hint. Hồ sơ dùng để chọn nhiệm vụ luyện tiếp; các module hội thoại/luyện nghe/điều phối phía sau chỉ là hướng tích hợp, không thuộc phạm vi triển khai của khóa luận.

## 15. CẤU TRÚC QUYỂN KHÓA LUẬN

| Chương | Nội dung | Bằng chứng phải có | Trang | Viết ở tuần |
| --- | --- | --- | --- | --- |
| 1. Giới thiệu | Bối cảnh, vấn đề, mục tiêu, RQ, phạm vi, đóng góp | Problem statement và RQ đo được | 8–12 | W1 |
| 2. Cơ sở lý thuyết & related work | CEFR, spoken assessment validity, ASR/ASA, sản phẩm tương tự, khoảng trống | Research matrix, định nghĩa construct, gap | 18–25 | W2 |
| 3. Phương pháp | Task/rubric, participant, consent, rater, thu dữ liệu, split, precision analysis, metric, ethics | Protocol tái lập, human–human agreement, datasheet, bảng pre-registration | 22–30 | W3–W4 |
| 4. Thiết kế & triển khai | Kiến trúc, schema, QC/ASR/features/models/calibration/feedback/review, tech stack | Sơ đồ, API, versioning, bảo mật, test | 20–30 | W5–W6 |
| 5. Thực nghiệm & kết quả | Baseline, M1, ablation, CI, calibration, WER, reliability, error/subgroup/usability | Bảng metric cùng split, confusion, plots, ca lỗi | 25–35 | W7–W9 |
| 6. Thảo luận | Trả lời RQ, so related work, validity, fairness, limitations, threats | Không overclaim; phân biệt kết luận nội bộ và tổng quát | 12–18 | W9–W10 |
| 7. Kết luận & hướng phát triển | Tóm tắt đóng góp, kết luận có điều kiện, mở rộng | Kết luận khớp metric và phạm vi | 5–8 | W10 |

### 15.1. Phụ lục

- A: Rubric A2/B1/B2 và rater handbook

- B: Task blueprint, prompt bank, follow-up tree Task C

- C: Consent, participant information sheet, data management plan

- D: Rating form, reason codes, anchor và ví dụ adjudication

- E: Data dictionary, manifest schema, model card, datasheet

- F: API, cấu trúc repo, config/seed, hướng dẫn tái lập

- G: Bảng metric đầy đủ, CI, confusion, ablation, error taxonomy

- S: Thiết kế thống kê và protocol đánh giá (tài liệu riêng, v3.0)

### 15.2. Checklist 48 giờ đầu

| # | Việc | Vì sao gấp |
| --- | --- | --- |
| 1 | Hỏi trường về quy trình phê duyệt thu dữ liệu người | Nếu cần hội đồng ethics chính thức và mất >4 tuần, toàn bộ kế hoạch 10 tuần vô hiệu. Đây là biến rủi ro duy nhất nhóm không kiểm soát được. |
| 2 | Xác nhận bằng văn bản 2 rater + 1 adjudicator, cam kết ~25 giờ/rater | Nếu không cam kết được, phải giảm ngay xuống 120 response |
| 3 | Chốt kênh tuyển 70–90 người — cụ thể lớp nào, giảng viên nào, ngày nào | Rủi ro số 2 |
| 4 | Chạy faster-whisper trên 3–5 file tiếng Anh giọng Việt, tính WER thô bằng tay | Nếu WER >35%, toàn bộ nhánh text feature lung lay — cần biết ở W1, không phải W7 |
| 5 | Gửi GVHD: tên đề tài, phạm vi A2–B2, RQ1–RQ6, memo thay đổi v2→v3 | Cổng G1 |
| 6 | Chốt công cụ sàng lọc trình độ và xin phép sử dụng | Ảnh hưởng lịch tuyển |
| 7 | Tạo repo, .gitignore audio/identity, issue board, lịch G1–G10 |  |
| 8 | Tạo rubric working sheet từ CEFR Appendix 3 và 6 prompt A/B/C |  |
| 9 | Đăng ký/tải L2-ARCTIC đúng license |  |

## TÀI LIỆU THAM KHẢO

Các nguồn [1]-[21] được kiểm tra trong bản gốc ngày 21/08/2026; nguồn [19], [20] được xác minh lại và [22] được bổ sung ngày 02/09/2026. Khi nộp luận văn, chuyển danh mục sang chuẩn trích dẫn của khoa và lưu bản PDF/DOI cho nguồn học thuật.

[1] Council of Europe (2020). Common European Framework of Reference for Languages: Companion Volume. Appendix 3: qualitative features of spoken language. https://rm.coe.int/cefr-companion-volume-with-new-descriptors-2020/16809ea0d4

[2] Council of Europe. CEFR Companion Volume and language versions. https://www.coe.int/en/web/common-european-framework-reference-languages/cefr-companion-volume-and-its-language-versions

[3] Scaria et al. EvalYaks: Instruction Tuning Datasets and LoRA Fine-tuned Models for Automated Scoring of CEFR B2 Speaking Assessment Transcripts. arXiv:2408.12226. https://github.com/Talking-Yak/EvalYaks

[4] Xi, Higgins, Zechner & Williamson (2008). Automated Scoring of Spontaneous Speech Using SpeechRater v1.0. ETS Research Report RR-08-62.

[5] University of Cambridge. Speak & Improve. https://speakandimprove.com/

[6] Knill et al. Speak & Improve Corpus 2025: an L2 English Speech Corpus for Language Assessment and Feedback. DOI: 10.17863/CAM.114333

[7] Gong et al. GOPT: Transformer-Based Multi-Aspect Multi-Granularity Non-Native English Speaker Pronunciation Assessment. ICASSP 2022. https://github.com/YuanGongND/gopt

[8] Zhang et al. SpeechOcean762: An Open-Source Non-native English Speech Corpus for Pronunciation Assessment. CC BY 4.0. https://www.openslr.org/101/

[9] Texas A&M PSI Lab. L2-ARCTIC: a non-native English speech corpus. 24 speakers, including four Vietnamese; CC BY-NC 4.0.

[10] George Mason University. Speech Accent Archive. CC BY-NC-SA 4.0. https://accent.gmu.edu/download/

[11] The ICNALE: International Corpus Network of Asian Learners of English.

[12] Microsoft Learn. Use pronunciation assessment.

[13] SpeechAce API Documentation. https://docs.speechace.com/

[14] Nebhi & Szaszák (2023). Automatic Assessment of Spoken English Proficiency Based on Multimodal and Multitask Transformers. RANLP 2023.

[15] van Dalen et al. Towards automatic assessment of spontaneous spoken English. Includes Vietnamese L1 in a multi-L1 CEFR dataset.

[16] FastAPI Documentation. https://fastapi.tiangolo.com/

[17] SYSTRAN. faster-whisper. https://github.com/SYSTRAN/faster-whisper

[18] MLflow Documentation. ML Experiment Tracking.

[19] Quốc hội. Luật Bảo vệ dữ liệu cá nhân số 91/2025/QH15. Hiệu lực từ 01/01/2026.

[20] Chính phủ. Nghị định số 356/2025/NĐ-CP. Hiệu lực từ 01/01/2026.

[21] Tài liệu nội bộ (2026). 2026 Định hướng xác định đề tài khóa luận: Ma trận Thiết kế Học tập Ngoại ngữ với AI (ALDM-L) và các nhóm đề tài khóa luận.

[22] Council of Europe & ALTE (2026). New revised Manual for Language Test Development and Examining: For use with the CEFR. https://rm.coe.int/new-revised-manual-for-language-test-development-and-examining-joint-p/48802cc30d

AI Assessor CEFR · Phiên bản 3.1 · 22/08/2026 · Đã đối chiếu khung ALDM-L · Đi kèm Phụ lục S (Thiết kế thống kê và protocol đánh giá)
