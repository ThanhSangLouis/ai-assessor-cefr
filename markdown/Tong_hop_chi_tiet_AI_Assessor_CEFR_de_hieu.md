# Xây dựng hệ thống AI hỗ trợ đánh giá năng lực nói tiếng Anh theo CEFR cho sinh viên đại học Việt Nam ở trình độ A2-B2

> Bản Markdown được chuyển từ [`Tong_hop_chi_tiet_AI_Assessor_CEFR_de_hieu.pptx`](../artifacts/source/presentations/Tong_hop_chi_tiet_AI_Assessor_CEFR_de_hieu.pptx). Nội dung được sắp theo từng slide; file gốc được giữ nguyên.

## Slide 1: ĐỀ CƯƠNG KHÓA LUẬN • BẢN GIẢI THÍCH DỄ HIỂU

- Dành cho người học Việt Nam ở trình độ A2–B2
- Từ cách con người chấm nói → cách AI quan sát bằng chứng → cách kiểm định với giảng viên
- Sinh viên: [Điền họ tên – MSSV]<br>Giảng viên hướng dẫn: [Điền họ tên]

## Slide 2: BẢN ĐỒ NỘI DUNG

- Năm câu hỏi giúp hiểu toàn bộ đề tài
- Người nghe không cần biết AI trước; chỉ cần đi lần lượt qua năm câu hỏi.

## Slide 3: Ý TƯỞNG CỐT LÕI

- Đề tài có thể hiểu bằng bốn câu đơn giản
- Người học nói
- AI quan sát
- Thực hiện bài kể chuyện, nêu quan điểm hoặc hội thoại ngắn bằng tiếng Anh.
- Nghe audio, tạo transcript và đo các dấu hiệu như khoảng lặng, từ vựng, lỗi ngữ pháp, mức liên kết ý.
- AI ước lượng
- Giảng viên kiểm soát
- Đưa ra xác suất A2/B1/B2 cho từng tiêu chí, không chỉ trả về một điểm duy nhất.
- Duyệt các trường hợp không chắc chắn và chịu trách nhiệm với nhãn chuẩn.

## Slide 4: BỐI CẢNH VÀ VẤN ĐỀ

- Chấm Speaking khó mở rộng vì vừa tốn thời gian vừa khó nhất quán
- Nghe nhiều lần
- Hai người có thể chấm khác
- Một bài nói 2 phút có thể cần nghe lại, ghi chú và đối chiếu rubric trước khi cho điểm.
- Cùng một bài nói, giảng viên có thể hiểu tiêu chí hoặc mức độ nghiêm khác nhau.
- Phản hồi thường quá chung
- Accent Việt làm ASR dễ sai
- Người học nhận một mức tổng quát nhưng không biết đoạn nào làm giảm điểm.
- Transcript tự động sai có thể khiến hệ thống hiểu nhầm lỗi của máy thành lỗi của người học.

## Slide 5: PHẠM VI

- Hệ thống hỗ trợ điều gì – và không được hứa điều gì
- Hệ thống được phép làm
- Hệ thống không được tuyên bố
- • Phản hồi nhanh cho hoạt động luyện tập.<br>• Ước lượng A2/B1/B2 trong phạm vi đã kiểm định.<br>• Chỉ ra bằng chứng từ audio và transcript.<br>• Ưu tiên bài cần giảng viên duyệt.<br>• Hỗ trợ giảng viên chấm số lượng lớn hơn.
- • Cấp chứng chỉ CEFR chính thức.<br>• Thay thế hoàn toàn giảng viên.<br>• Chính xác cho mọi accent, thiết bị và nhiệm vụ.<br>• Dùng cho quyết định học vụ high-stakes.<br>• Suy luận tính cách, giới tính hoặc cảm xúc từ giọng nói.
- Cách gọi an toàn: hệ thống AI hỗ trợ đánh giá theo CEFR trong bối cảnh luyện tập/low-stakes.

## Slide 6: NỀN TẢNG ĐÁNH GIÁ

- CEFR là khung mô tả năng lực, không phải thuật toán chấm
- CEFR nói điều gì?
- CEFR không nói điều gì?
- CEFR mô tả người học có thể sử dụng ngôn ngữ hiệu quả đến đâu trong các tình huống giao tiếp.<br>A2: giao tiếp đơn giản, quen thuộc.<br>B1: diễn đạt được ý chính và trải nghiệm.<br>B2: trình bày quan điểm khá rõ, tương tác tương đối tự nhiên.
- CEFR không cung cấp một công thức kiểu “150 từ/phút = B2”.<br>Muốn chấm bằng AI, đề tài phải biến mô tả CEFR thành rubric, nhiệm vụ nói, bằng chứng quan sát được và nhãn của giảng viên.
- AI không học 'CEFR' từ tên gọi; AI chỉ học mối liên hệ giữa bằng chứng và nhãn do con người chấm.

## Slide 7: CÁCH CHẤM SPEAKING

- Sáu tiêu chí trả lời sáu câu hỏi khác nhau
- Không nên gộp tất cả vào một con số ngay từ đầu.

## Slide 8: SÁU TIÊU CHÍ

- Range và Accuracy: nói được nhiều – và nói có kiểm soát
- Range – phạm vi ngôn ngữ
- Accuracy – độ chính xác
- Ví dụ A2: từ quen thuộc, câu ngắn.<br>Ví dụ B1: đủ từ để kể trải nghiệm và giải thích lý do.<br>Ví dụ B2: diễn đạt quan điểm với nhiều cách diễn đạt hơn.<br>AI quan sát: lexical diversity, loại cấu trúc câu, mức độ lặp.
- Không yêu cầu người học không có lỗi. Câu hỏi quan trọng là lỗi có thường xuyên và có cản trở ý nghĩa không.<br>AI quan sát: tense, agreement, article, preposition, self-repair.<br>Cảnh báo: transcript ASR sai không được tính thành lỗi của người học.

## Slide 9: SÁU TIÊU CHÍ

- Fluency và Phonology: trôi chảy không đồng nghĩa với nói nhanh
- Fluency – độ trôi chảy
- Phonology – âm thanh lời nói
- Đánh giá khả năng duy trì lời nói với nhịp phù hợp.<br>Bằng chứng: số khoảng dừng, tỷ lệ im lặng, độ dài chuỗi nói, lặp và tự sửa.<br>Không nên thưởng người nói quá nhanh nếu nội dung thiếu rõ ràng.
- Xem phát âm, trọng âm, nhịp và ngữ điệu có giúp người nghe hiểu không.<br>Accent Việt không phải lỗi tự động. Chỉ phạt khi intelligibility giảm.<br>Bằng chứng cần đối chiếu audio và giảng viên.
- Mục tiêu hợp lý là 'dễ hiểu', không phải 'giống người bản ngữ'.

## Slide 10: SÁU TIÊU CHÍ

- Coherence và Interaction cần nhìn vào cách phát triển và trao đổi ý
- Coherence – mạch lạc
- Interaction – tương tác
- Ý tưởng có đi theo trình tự dễ hiểu không? Người học có dùng từ nối và giải thích đủ để người nghe theo kịp không?<br>AI quan sát: discourse markers, idea progression, semantic continuity và relevance.
- Người học có phản hồi đúng lúc, trả lời đúng ý, hỏi lại khi chưa rõ và duy trì lượt nói không?<br>Chỉ có đủ bằng chứng khi nhiệm vụ thật sự có nhiều lượt hội thoại.
- Nếu chỉ có độc thoại, hệ thống phải ghi 'chưa đủ bằng chứng cho Interaction' – không được tự cho 0 điểm.

## Slide 11: THIẾT KẾ BÀI NÓI

- Ba dạng nhiệm vụ tạo ba loại bằng chứng
- 01
- 02
- 03
- Task A<br>Kể / mô tả
- Task B<br>Nêu quan điểm
- Task C<br>Hội thoại
- 60–90 giây. Chủ đề quen thuộc. Quan sát Range, Fluency, Coherence, Phonology.
- Khoảng 120 giây. Nêu lập trường, lý do, ví dụ. Kiểm tra Accuracy và phát triển ý.
- 3–5 lượt có follow-up bán cấu trúc. Cần để chấm Interaction.
- Không dùng một bài nói duy nhất để suy ra toàn bộ năng lực. Nhiệm vụ quyết định loại bằng chứng có thể thu được.

## Slide 12: CƠ CHẾ TỔNG THỂ

- Từ giọng nói đến báo cáo có bằng chứng
- 01
- 02
- 03
- 04
- 05
- Nhiệm vụ<br>+ audio
- Kiểm tra<br>chất lượng
- ASR +<br>timestamp
- Đặc trưng<br>đa nguồn
- Chấm +<br>calibration
- Prompt, consent, speaker_id và file ghi âm.
- Độ dài, im lặng, clipping, tiếng ồn, đúng ngôn ngữ.
- Transcript thô, thời điểm từ và confidence.
- Audio, text và interaction được tách riêng.
- Xác suất A2/B1/B2 và cờ cần giảng viên duyệt.
- Nguyên tắc: bằng chứng được tạo trước; lời giải thích được sinh sau và phải truy ngược được về bằng chứng.

## Slide 13: BƯỚC 1 • QUALITY GATE

- Hệ thống phải biết khi nào không nên chấm
- Quá ngắn
- Âm thanh hỏng
- Bài nói không đủ thời lượng hoặc không hoàn thành nhiệm vụ → yêu cầu ghi lại.
- Clipping, âm lượng quá nhỏ, file lỗi hoặc tiếng ồn quá lớn → invalid/review.
- Không đúng đầu bài
- ASR có nguy cơ sai
- Nói sai ngôn ngữ hoặc hoàn toàn lệch chủ đề → không tạo điểm giả.
- Confidence thấp hoặc nhiều đoạn vô nghĩa → gắn cờ và giữ audio để giảng viên nghe.

## Slide 14: BƯỚC 2 • NHẬN DẠNG GIỌNG NÓI

- Whisper tạo bản chép lời – nhưng bản chép lời không phải sự thật tuyệt đối
- Whisper cung cấp
- Whisper có thể sai vì
- • Transcript thô của bài nói.<br>• Timestamp cho từng từ hoặc đoạn.<br>• Thông tin confidence/ước lượng rủi ro.<br>• Khả năng chạy local qua faster-whisper.<br>• Dữ liệu để tìm bằng chứng trong báo cáo.
- • Accent Việt và cách phát âm L2.<br>• Tiếng ồn, micro hoặc âm lượng.<br>• Từ riêng, từ hiếm và code-switching.<br>• Nói ngập ngừng hoặc tự sửa.<br>• Model nhỏ/CPU có độ chính xác thấp hơn.
- Giải pháp: đo WER trên một tập transcript chép tay và phân tích mối liên hệ giữa lỗi ASR với lỗi chấm.

## Slide 15: BƯỚC 3 • TRÍCH XUẤT ĐẶC TRƯNG

- Ba nhánh bằng chứng được tạo độc lập
- Tách nhánh giúp biết mô hình đang dựa vào đâu và kiểm tra được khi một nguồn bị sai.
- Mỗi feature cần có version để thí nghiệm có thể chạy lại.

## Slide 16: BƯỚC 4 • MÔ HÌNH CHẤM

- Mỗi tiêu chí nên trả xác suất thay vì một nhãn cứng
- Ví dụ cho Fluency
- Không lấy trung bình máy móc
- A2 = 10%<br>B1 = 70%<br>B2 = 20%<br>→ nghiêng về B1 nhưng vẫn có bất định.
- Overall không nhất thiết bằng trung bình sáu tiêu chí; có thể dùng best-fit hoặc mô hình ordinal được hiệu chỉnh.
- Giữ missing là missing
- Ưu tiên mô hình đơn giản
- Không có Task C thì Interaction không được điền 0 vì 0 mang nghĩa năng lực thấp.
- Dữ liệu nhỏ nên logistic/ordinal model hoặc late fusion dễ kiểm soát hơn deep transformer lớn.

## Slide 17: BƯỚC 5 • CALIBRATION VÀ HUMAN REVIEW

- AI phải biết mức độ chắc chắn của chính mình
- 01
- 02
- 03
- 04
- Dự đoán
- Hiệu chỉnh
- Áp ngưỡng
- Giảng viên duyệt
- Mô hình tạo xác suất cho từng band và từng tiêu chí.
- Dùng dev set để xác suất phản ánh gần đúng tỷ lệ đúng thực tế.
- Confidence thấp, ASR risk hoặc criterion conflict → review.
- Nghe audio, xem evidence, xác nhận/sửa và ghi lý do.
- Human review không phải xử lý lỗi tạm thời; đây là một phần chính thức của kiến trúc an toàn.

## Slide 18: VÍ DỤ TỪ ĐẦU ĐẾN CUỐI

- Một bài nói được xử lý như thế nào?
- 01
- 02
- 03
- 04
- 05
- Audio 102 giây
- QC đạt
- ASR + evidence
- Điểm tiêu chí
- Kết quả
- Task B: nêu quan điểm về học trực tuyến.
- Âm thanh rõ; có hai khoảng im lặng dài.
- Transcript khá rõ; một đoạn confidence thấp ở 00:42.
- Range B1, Accuracy B1, Fluency A2/B1, Coherence B1.
- Overall B1; cờ review vì ASR risk ở đoạn bằng chứng.
- Ví dụ minh họa – không phải kết quả thực nghiệm thật.

## Slide 19: ĐẦU RA CHO NGƯỜI HỌC

- Báo cáo phải trả lời: mức nào, vì sao và nên làm gì tiếp theo
- Ví dụ minh họa – số liệu không phải kết quả thực nghiệm.
- Sáu tiêu chí
- MỨC ƯỚC LƯỢNG
- 68%
- Range
- B1
- 62%
- Accuracy
- Độ tin cậy 72%
- 48%
- Fluency
- 55%
- Interaction
- Cần giảng viên duyệt<br>vì ASR có rủi ro ở 00:42–00:49
- 72%
- Coherence
- 64%
- Phonology
- Ưu tiên luyện tiếp
- Giảm khoảng dừng dài và hoàn thành câu trước khi chuyển ý.
- Báo cáo tốt không chỉ nêu điểm; phải có evidence, confidence, version và lý do chuyển review.

## Slide 20: LỰA CHỌN MÔ HÌNH

- Vì sao không chỉ đưa transcript cho ChatGPT chấm?
- Transcript-only nhìn thấy
- Transcript-only không nghe thấy
- • Từ vựng và nội dung đã được ASR ghi lại.<br>• Một phần cấu trúc câu và từ nối.<br>• Khả năng bám rubric nếu prompt được khóa.<br>• Có thể dùng làm baseline B3.
- • Phát âm có dễ hiểu hay không.<br>• Prosody, nhịp và khoảng dừng.<br>• Tốc độ phản hồi và timing hội thoại.<br>• Lỗi transcript đến từ Whisper hay người học.<br>• Bằng chứng âm thanh tại timestamp cụ thể.
- LLM có thể hỗ trợ diễn giải evidence; điểm chính phải tái lập được và được kiểm định với nhãn giảng viên.

## Slide 21: SẢN PHẨM VÀ NGHIÊN CỨU TƯƠNG TỰ

- Đề tài không bắt đầu từ số 0 – nhưng vẫn có khoảng trống rõ
- So sánh theo loại bằng chứng, độ mở và mức phù hợp với người Việt.
- Khoảng trống bảo vệ: hệ thống mở, tái lập, kiểm định trên người Việt A2–B2 và có human review.

## Slide 22: CHIẾN LƯỢC DỮ LIỆU

- Dữ liệu công khai hỗ trợ pipeline – nhưng không đủ làm gold validation
- Mỗi bộ dữ liệu có giấy phép, nhãn và đối tượng khác nhau.

## Slide 23: DỮ LIỆU PHẢI TỰ THU

- Tập dữ liệu nhỏ nhưng có thiết kế chặt sẽ có giá trị hơn tập lớn thiếu nhãn
- 40–60 người học
- 100–150 responses
- Người Việt từ 18 tuổi; quota mềm A2/B1/B2; không ép cân bằng bằng nhân tạo sau khi chia tập.
- Mỗi người Task A + B; Task C cho 20–30 người nếu pilot ổn định.
- Hai giảng viên chấm
- Split theo speaker
- Chấm độc lập; toàn bộ test và tối thiểu 30% train được chấm kép.
- Audio của cùng một người không được xuất hiện ở cả train và test; tránh học thuộc giọng.

## Slide 24: TẠO NHÃN CHUẨN

- Trước khi đo AI, phải kiểm tra con người có chấm ổn định không
- 01
- 02
- 03
- 04
- 05
- Viết rubric
- Calibration
- Chấm mù
- Đo agreement
- Adjudication
- Mô tả A2/B1/B2 cho 6 tiêu chí; có evidence guide và reason codes.
- Hai rater chấm anchor, thảo luận cách hiểu và thống nhất quy tắc.
- Rater không thấy điểm AI; thứ tự bài được random hóa.
- Tính QWK/ICC overall và từng tiêu chí; xem ca lệch lớn.
- Giải quyết ca lệch bằng lý do và bằng chứng, không lấy trung bình máy móc.
- Nếu human–human agreement thấp, chưa được phép tuyên bố AI chấm kém hay tốt; phải sửa rubric trước.

## Slide 25: THIẾT KẾ THÍ NGHIỆM

- Mô hình chính chỉ có ý nghĩa khi được so với baseline rõ ràng
- Mọi mô hình phải dùng cùng speaker split, seed và test set khóa.

## Slide 26: CÁCH ĐÁNH GIÁ KẾT QUẢ

- Mỗi metric trả lời một câu hỏi khác nhau
- Các ngưỡng dưới đây là mục tiêu quản trị đề xuất, không phải chuẩn do Council of Europe ban hành.

## Slide 27: KIẾN TRÚC KỸ THUẬT

- Bằng chứng trước – diễn giải sau
- MVP dùng modular monolith để giảm chi phí tích hợp nhưng vẫn tách rõ module và version.

## Slide 28: TECH STACK

- Chọn công nghệ theo nguyên tắc: nhanh để làm MVP, dễ tái lập để bảo vệ
- Không tách microservices hoặc thêm cloud phức tạp trong 10 tuần.

## Slide 29: PHÁP LÝ VÀ ĐẠO ĐỨC

- Giọng nói và transcript phải được xử lý như dữ liệu cá nhân nhạy cảm
- Quy trình tối thiểu
- Giới hạn đạo đức
- • Consent nêu đúng mục đích thu và chấm Speaking.<br>• Mã giả danh; bảng liên hệ tách khỏi audio.<br>• Lưu local-first, mã hóa và phân quyền.<br>• Có retention, quyền rút và quy trình xóa.<br>• Không đưa audio/identity vào Git hoặc repo công khai.
- • Không dùng cho chứng chỉ hoặc quyết định high-stakes.<br>• Không phạt accent nếu lời nói vẫn dễ hiểu.<br>• Không suy diễn giới tính, sức khỏe, cảm xúc, tính cách.<br>• Rater phải chấm mù với điểm AI.<br>• Công bố population, failure modes và ca cần người duyệt.
- Trước khi thu main data cần có chấp thuận theo quy trình của trường; nội dung này không thay thế tư vấn pháp lý.

## Slide 30: KẾ HOẠCH 10 TUẦN

- Tuần 1–5: chốt construct trước, thu dữ liệu sau
- Mỗi tuần có một đầu ra kiểm tra được; nếu trễ cổng thì cắt tính năng thay vì bỏ phần kiểm định.

## Slide 31: KẾ HOẠCH 10 TUẦN

- Tuần 6–10: khóa dữ liệu, so baseline rồi mới làm giao diện
- Mỗi tuần có một đầu ra kiểm tra được; nếu trễ cổng thì cắt tính năng thay vì bỏ phần kiểm định.

## Slide 32: NGHIỆM THU VÀ TÍNH KHẢ THI

- Đề tài khả thi nếu khóa scope và đo đúng thứ cần đo
- Ngưỡng là mục tiêu quản trị; kết quả cuối phải báo sample size và confidence interval.

## Slide 33: RỦI RO VÀ PHƯƠNG ÁN DỰ PHÒNG

- Mỗi rủi ro phải có tín hiệu sớm và quyết định cắt cụ thể
- Không chờ đến tuần 9 mới nhận ra thiếu dữ liệu hoặc agreement thấp.

## Slide 34: ĐÓNG GÓP KHOA HỌC

- Điểm mới nằm ở quy trình kiểm định – không nằm ở việc gọi Whisper hay LLM
- C1 • Rubric vận hành
- C2 • Dữ liệu người Việt
- Chuyển sáu tiêu chí CEFR thành rubric A2/B1/B2, evidence guide, reason codes và quy tắc missing/adjudication.
- Audio ẩn danh có consent, task version, hai rater, manifest, datasheet và manual transcript subset.
- C3 • Kiến trúc giải thích được
- C4 • Bằng chứng thực nghiệm
- Tách audio/text/interaction, late fusion, calibration, evidence grounding và human review.
- Baseline, ablation, speaker split, AI-human/human-human agreement, ASR và failure analysis.

## Slide 35: CẤU TRÚC QUYỂN KHÓA LUẬN

- Bảy chương trả lời lần lượt: vì sao, dựa vào đâu, làm thế nào và kết quả có ý nghĩa gì
- Phụ lục giữ rubric, task, consent, schema, API, model card và bảng metric đầy đủ.

## Slide 36: CHUẨN BỊ BẢO VỆ

- Những câu hội đồng dễ hỏi nhất – và việc phải chốt trong 48 giờ
- Câu hỏi phản biện
- Việc phải làm ngay
- • Vì sao không chỉ dùng Whisper + ChatGPT?<br>• Dựa vào đâu nói hệ thống theo CEFR?<br>• 40–60 người có quá ít để làm AI không?<br>• Nếu model không đạt target thì khóa luận có thất bại?<br>• Hệ thống có thiên vị accent không?<br>• Vì sao QWK 0,60 không phải chuẩn CEFR?
- • Gửi tên đề tài, phạm vi A2–B2 và RQ cho GVHD duyệt.<br>• Xác nhận hai rater và lịch calibration.<br>• Xin mẫu consent/ethics và chốt nơi lưu audio.<br>• Tạo rubric working sheet và 6 prompt A/B/C.<br>• Tạo repo có .gitignore cho audio/identity.<br>• Chạy Whisper thử trên ít nhất ba audio người Việt.

## Slide 37: KẾT LUẬN

- Giá trị của đề tài không nằm ở việc<br>AI cho ra một con số.
- Giá trị nằm ở việc hệ thống giải thích được vì sao chấm như vậy, biết khi nào không chắc chắn và cho phép giảng viên kiểm soát kết quả.
- Một khóa luận tốt cần chứng minh ba điều:
- 1. Đúng construct • 2. Đúng dữ liệu và phép thử • 3. Đúng giới hạn sử dụng
- Quyết định tiếp theo: khóa rubric, rater và kênh tuyển dữ liệu trước khi bắt đầu xây thêm tính năng.
