# Xây dựng hệ thống AI hỗ trợ đánh giá năng lực nói tiếng Anh theo CEFR cho sinh viên đại học Việt Nam ở trình độ A2-B2

> Bản Markdown được chuyển từ [`Dinh_huong_chi_tiet_10_tuan_AI_Assessor_CEFR.docx`](../artifacts/source/documents/Dinh_huong_chi_tiet_10_tuan_AI_Assessor_CEFR.docx). File gốc được giữ nguyên.

BÁO CÁO ĐỊNH HƯỚNG KHÓA LUẬN

Phạm vi nghiên cứu, thiết kế đánh giá, chiến lược dữ liệu người Việt và kế hoạch triển khai chi tiết trong 10 tuần

Định vị ALDM-L: Speaking × Assess × AI Assessor

Kết hợp đề xuất: Diagnostic & Assessment + Interactive Speaking + Evidence-based Feedback

Phiên bản 1.0  |  Cập nhật 20/08/2026

Mục đích: chốt đề tài, lập kế hoạch thực hiện và làm khung viết đề cương

## Kết luận điều hành

Phương án nên chốt
Xây dựng hệ thống AI hỗ trợ đánh giá năng lực nói tiếng Anh của sinh viên Việt Nam ở dải A2-B2 theo CEFR, kết hợp bài nói độc thoại và một hội thoại bán cấu trúc, trả về mức CEFR ước lượng, sáu tiêu chí, bằng chứng, độ tin cậy và phản hồi cải thiện. Hệ thống là formative/low-stakes, không cấp chứng chỉ và không thay thế giám khảo.

| Hạng mục | Quyết định |
| --- | --- |
| Lõi nghiên cứu | Nhóm 1: Speaking × Assess × AI Assessor |
| Kết hợp bắt buộc | Một phần Nhóm 2: AI Conversation Partner để quan sát Interaction; AI Feedbacker để giải thích kết quả |
| Mở rộng có điều kiện | Nhóm 4 ở mức gợi ý 1-2 nhiệm vụ tiếp theo; không xây AI Orchestrator đầy đủ |
| Biến thể khác | Nhóm 3 nếu đổi bối cảnh sang phỏng vấn việc làm; không nên triển khai đồng thời trong 10 tuần |
| Đối tượng | Sinh viên Việt Nam học tiếng Anh; phạm vi kiểm chứng A2-B2 |
| Dữ liệu chính | Dữ liệu tự thu tại trường và được giảng viên chấm; corpus công khai chỉ hỗ trợ pretrain/benchmark |
| Metric chính | Human-human QWK trước; AI-human QWK, MAE theo band, adjacent accuracy và macro-F1 sau |
| MVP | Recorder → ASR → scoring → confidence/evidence → báo cáo → teacher review queue |

Giả định kế hoạch: một sinh viên kỹ thuật làm 18-22 giờ/tuần; có một giảng viên hướng dẫn và hai giảng viên tiếng Anh hỗ trợ chuẩn hóa/chấm mẫu. Nếu thiếu người chấm hoặc chưa được phép thu audio, đề tài phải hạ tuyên bố xuống mức nguyên mẫu thăm dò.

### Mục lục nội dung

- 1. Định vị và phạm vi đề tài

- 2. Vấn đề nghiên cứu, khoảng trống và đóng góp

- 3. Phân tích các hướng kết hợp

- 4. Câu hỏi nghiên cứu và tiêu chí thành công

- 5. Cách đánh giá Speaking theo CEFR

- 6. Thiết kế nhiệm vụ nói

- 7. Chiến lược dữ liệu, đặc biệt dữ liệu người Việt

- 8. Quy trình chấm của giảng viên

- 9. Kiến trúc kỹ thuật và pipeline chấm

- 10. Mô hình, baseline và thực nghiệm

- 11. Kế hoạch triển khai chi tiết 10 tuần

- 12. Phân vai, rủi ro, đạo đức và bảo mật

- 13. Sản phẩm bàn giao và Definition of Done

- 14. Cấu trúc luận văn đề xuất

- Phụ lục: rubric A2-B2, schema dữ liệu, API và checklist khởi động

## 1. Định vị và phạm vi đề tài

### 1.1. Tên đề tài

Tên đề tài chốt: “Xây dựng hệ thống AI hỗ trợ đánh giá năng lực nói tiếng Anh theo CEFR cho sinh viên đại học Việt Nam ở trình độ A2-B2”.

Nên dùng cụm “hỗ trợ đánh giá” hoặc “ước lượng mức CEFR” thay cho “chấm CEFR chính thức”. Council of Europe cung cấp khung tham chiếu và descriptor nhưng không xác nhận chất lượng của từng hệ thống/ kỳ thi tự tuyên bố liên kết với CEFR.

### 1.2. Phạm vi kiểm chứng

| Trong phạm vi | Ngoài phạm vi 10 tuần |
| --- | --- |
| A2-B2; sinh viên Việt Nam; formative assessment | Khẳng định A1-C2 khi không đủ mẫu từng band |
| Hai bài nói độc thoại và một hội thoại ngắn | Thi chuẩn hóa high-stakes hoặc cấp chứng chỉ |
| Sáu đặc trưng CEFR: Range, Accuracy, Fluency, Interaction, Coherence, Phonology | Đánh giá tính cách, trí thông minh, thái độ hoặc năng lực nghề nghiệp tổng quát |
| Confidence, evidence và human review | Một điểm AI duy nhất quyết định kết quả học vụ |
| So sánh baseline và phân tích lỗi | Fine-tune end-to-end mô hình speech lớn trên vài chục người nói |

### 1.3. Chu trình sản phẩm

Learning loop mục tiêu
Elicit speech → kiểm tra chất lượng → nhận dạng lời nói → trích xuất bằng chứng → chấm theo rubric → hiệu chỉnh độ tin cậy → giải thích kết quả → giảng viên duyệt ca bất định → đề xuất nhiệm vụ luyện tiếp theo.

## 2. Vấn đề nghiên cứu, khoảng trống và đóng góp

### 2.1. Vấn đề

- Chấm Speaking thủ công tốn thời gian, khó mở rộng và có biến thiên giữa giám khảo.

- ASR có thể nhận sai giọng Việt; lỗi ASR có thể bị mô hình hiểu nhầm thành lỗi từ vựng hoặc ngữ pháp.

- Một số hệ thống tự động thưởng quá nhiều cho tốc độ nói, độ dài hoặc accent gần bản ngữ, trong khi CEFR nhấn mạnh khả năng giao tiếp và intelligibility.

- Corpus phát âm phổ biến chủ yếu là người nói L1 Mandarin; dữ liệu CEFR toàn cầu chưa chắc đại diện cho sinh viên Việt Nam.

- Nhiều demo công khai có kiến trúc tốt nhưng thiếu kiểm định AI-human, calibration, speaker-level split và phân tích sai lệch.

### 2.2. Khoảng trống nghiên cứu có thể bảo vệ

Ý tưởng “AI chấm Speaking” đã có. Điểm mới không nên đặt ở việc gọi API hoặc dùng Whisper, mà ở thiết kế và kiểm định cho đúng đối tượng người Việt: rubric CEFR được vận hành hóa, nhiệm vụ nói có blueprint, dữ liệu cục bộ được hai giám khảo chấm, split theo speaker, đánh giá ảnh hưởng của ASR/accent và cơ chế human review.

### 2.3. Đóng góp dự kiến

- Một rubric A2-B2 có hướng dẫn bằng chứng, anchor samples và quy tắc xử lý bất đồng.

- Một bộ nhiệm vụ nói gồm production và interaction, có version và mục tiêu bằng chứng.

- Một tập dữ liệu người Việt được ẩn danh, có consent, metadata và nhãn giám khảo.

- Một pipeline đa phương thức kết hợp audio, transcript và turn log, có confidence và evidence.

- Một thực nghiệm tái lập gồm baseline, fusion, ablation, AI-human agreement, error analysis và subgroup diagnostics.

- Một ứng dụng web proof-of-concept phục vụ sinh viên và hàng đợi kiểm duyệt cho giảng viên.

## 3. Phân tích các hướng kết hợp

| Phương án | Giá trị | Chi phí/rủi ro | Khuyến nghị |
| --- | --- | --- | --- |
| Nhóm 1 | Tập trung độ tin cậy chấm điểm | Không đo tốt Interaction | MVP tối thiểu |
| Nhóm 1 + phần Nhóm 2 | Đo production + interaction; phản hồi có hành động | Thêm turn log, kịch bản và dữ liệu | Phương án chính |
| Nhóm 1 + 2 + phần Nhóm 4 | Khép vòng assess-practice-reassess | Dễ thành LMS/orchestrator quá lớn | Chỉ rule-based recommendation |
| Nhóm 1 + Nhóm 3 | Ứng dụng phỏng vấn rõ ràng | Construct đổi sang employability | Chọn thay thế, không cộng dồn |
| Nhóm 1 + 2 + 3 + 4 | Demo nhiều tính năng | Không đủ 10 tuần; khó kiểm định | Không chọn |

### 3.1. Kết hợp được khuyến nghị

| ALDM-L cell | Vai trò trong hệ thống | Mức ưu tiên |
| --- | --- | --- |
| Speaking × Assess × AI Assessor | Dự đoán tiêu chí và mức A2/B1/B2; confidence; evidence | Lõi bắt buộc |
| Speaking × Interact × AI Conversation Partner | Tạo hội thoại bán cấu trúc 3-5 lượt để quan sát turn-taking | Bắt buộc nếu tuyên bố Interaction |
| Speaking × Reflect × AI Feedbacker | Diễn giải điểm mạnh, ưu tiên cải thiện và ví dụ | Bắt buộc |
| Toàn diện × Adapt × AI Personalizer | Chọn 1-2 nhiệm vụ tiếp theo theo tiêu chí yếu | Stretch, dùng luật |
| Employability × Perform × AI Simulator | Đổi task thành phỏng vấn tuyển dụng | Nhánh đề tài khác |

Quy tắc giữ phạm vi
Chỉ kết hợp các vai trò nằm trong cùng một chu trình Elicit → Assess → Explain → Recommend. Không xây chatbot tự do, LMS, hệ thống thi chống gian lận và mô phỏng phỏng vấn cùng lúc.

### 3.2. Các hướng mở rộng có thể viết trong luận văn

- Assess → Practice → Reassess: theo dõi thay đổi theo từng tiêu chí qua nhiều phiên; chỉ nên demo bằng 2 phiên/người.

- Assessor + Feedbacker: so sánh feedback template với feedback LLM đã grounded bằng evidence.

- Assessor + Personalizer: ánh xạ tiêu chí yếu sang task bank; không cần recommender học máy.

- Assessor + Simulator: thay Task C bằng phỏng vấn việc làm, nhưng phải dùng rubric bổ sung về task fulfillment và professional interaction.

- Assessor + Analyst: dashboard cohort cho giảng viên; chỉ thống kê ẩn danh, không xếp hạng sinh viên công khai.

## 4. Câu hỏi nghiên cứu và tiêu chí thành công

### 4.1. Câu hỏi nghiên cứu

- RQ1. Mức CEFR và điểm tiêu chí do hệ thống dự đoán đồng thuận với giảng viên ở mức nào?

- RQ2. Kết hợp audio + transcript + interaction có cải thiện so với audio-only và transcript-only không?

- RQ3. Lỗi ASR, độ ồn, thời lượng và khác biệt thiết bị ảnh hưởng thế nào đến sai số chấm?

- RQ4. Confidence/calibration có giúp phát hiện ca cần giảng viên duyệt không?

- RQ5. Sinh viên và giảng viên đánh giá phản hồi có rõ ràng, đúng bằng chứng và có thể hành động không?

### 4.2. Giả thuyết có thể kiểm định

- H1. Late fusion đạt QWK cao hơn từng baseline đơn phương thức trên cùng speaker split.

- H2. Sai số tăng khi WER tăng; vì vậy cần quality gate và human review cho audio/ASR kém.

- H3. Feedback grounded bằng timestamp/transcript được người dùng đánh giá hữu ích hơn feedback chung chung.

### 4.3. Tiêu chí thành công

| Lớp | Chỉ số | Mục tiêu vận hành |
| --- | --- | --- |
| Nhãn | Human-human QWK/ICC | Tính trước khi train; nếu QWK < 0,60, sửa rubric/anchor và chấm lại pilot |
| Mô hình | AI-human QWK | Mục tiêu proof-of-concept ≥ 0,60; báo cáo CI và không che human ceiling |
| Sai số | MAE band, adjacent accuracy | Adjacent accuracy mục tiêu ≥ 80-85%; phân tích ca lệch ≥2 band |
| Lệch lớp | Macro-F1, per-class recall | Báo cáo thay vì chỉ accuracy |
| ASR | WER trên tập chép tay | Báo cáo theo band, thiết bị và noise; không dùng WER làm điểm phát âm |
| Tin cậy | Brier/ECE hoặc reliability bins | Confidence thấp phải tăng tỷ lệ bắt đúng ca sai |
| Khả dụng | Task completion, Likert/SUS | Người dùng hiểu báo cáo và tìm được hành động tiếp theo |

Các ngưỡng trên là mục tiêu quản trị dự án, không phải ngưỡng chính thức do Council of Europe ban hành. Nếu dữ liệu nhỏ, phải ưu tiên confidence interval, error analysis và giới hạn tổng quát hóa.

## 5. Cách đánh giá Speaking theo CEFR

CEFR Companion Volume 2020, Appendix 3 mô tả sáu đặc trưng định tính của ngôn ngữ nói: Range, Accuracy, Fluency, Interaction, Coherence và Phonology. Hệ thống cần đánh giá construct này, không đồng nhất một feature kỹ thuật với toàn bộ một tiêu chí.

| Tiêu chí | Ý nghĩa chấm | Bằng chứng quan sát | Bẫy cần tránh |
| --- | --- | --- | --- |
| Range | Phạm vi từ/cấu trúc để diễn đạt ý | Lexical diversity, lexical sophistication, syntactic variety | Từ hiếm không tự động đồng nghĩa trình độ cao |
| Accuracy | Mức kiểm soát ngữ pháp và từ | Lỗi/100 từ, error-free clauses, self-repair | ASR sai có thể tạo lỗi giả |
| Fluency | Khả năng duy trì lời nói dễ theo dõi | Speech/articulation rate, pause ratio, mean length of run | Không thưởng nói nhanh nhưng khó hiểu |
| Interaction | Khởi tạo, duy trì, phản hồi và quản lý lượt | Response relevance, latency, clarification, turn balance | Không chấm từ monologue |
| Coherence | Phát triển và liên kết ý | Topic progression, discourse markers, semantic continuity | Đếm từ nối đơn thuần |
| Phonology | Intelligibility và kiểm soát âm/prosody | Phone errors, stress, rhythm, intonation, listener effort | Phạt accent dù thông điệp vẫn rõ |

### 5.1. Quy tắc chấm

- Chấm từng tiêu chí theo thang thứ bậc A2/B1/B2, kèm ghi chú bằng chứng.

- Mức overall dùng best-fit được hiệu chỉnh trên điểm giám khảo; không lấy trung bình cộng máy móc.

- Interaction chỉ được báo cáo khi người học hoàn thành Task C hoặc một task tương tác tương đương.

- Phonology tập trung intelligibility; accent Việt còn nghe thấy không phải là lỗi nếu không cản trở hiểu.

- Nếu response quá ngắn, lệch đề, audio lỗi hoặc confidence thấp, hệ thống từ chối chấm/đưa vào review thay vì bịa điểm.

- Báo cáo nên hiển thị vùng ranh giới như B1/B2 khi hai xác suất liền kề gần nhau.

### 5.2. Quality gate trước khi chấm

| Kiểm tra | Hành động |
| --- | --- |
| Audio không mở được, clipping nặng hoặc sample rate sai | Từ chối và yêu cầu ghi lại |
| Speech duration dưới ngưỡng task | Đánh dấu insufficient evidence; không gán CEFR chắc chắn |
| Tỷ lệ silence quá cao hoặc SNR thấp | Cảnh báo và đưa vào teacher review |
| Ngôn ngữ không phải tiếng Anh/lệch đề rõ | Không chấm; lưu reason code |
| ASR confidence thấp | Giảm confidence tổng; ưu tiên audio features và chép tay khi đánh giá |
| Mâu thuẫn lớn giữa tiêu chí | Yêu cầu thêm task hoặc giảng viên duyệt |

## 6. Thiết kế nhiệm vụ nói

| Task | Thời lượng | Construct chính | Ví dụ |
| --- | --- | --- | --- |
| A. Kể/mô tả | 90-120 giây | Range, Fluency, Coherence, Phonology | Kể một trải nghiệm học tập đáng nhớ và giải thích tác động |
| B. Nêu quan điểm | 120 giây | Range, Accuracy, Coherence | Sinh viên có nên dùng AI khi học ngoại ngữ không? |
| C. Hội thoại bán cấu trúc | 3-5 lượt, tối đa 3 phút | Interaction, Fluency, relevance | Lập kế hoạch hoạt động nhóm với ràng buộc thời gian/ngân sách |

### 6.1. Blueprint và tính tương đương

- Mỗi prompt có target level, chủ đề, chức năng giao tiếp, thời lượng, từ khóa không bắt buộc và các follow-up cố định.

- Task C dùng cây hội thoại bán cấu trúc; AI có thể paraphrase nhưng không tự ý tăng độ khó hoặc đổi mục tiêu.

- Mỗi task có prompt_version; không trộn phiên bản trong phân tích mà không ghi nhận.

- Pilot kiểm tra prompt có gây lệch văn hóa, đòi kiến thức chuyên môn hoặc khiến một nhóm thiếu nội dung để nói không.

- Không dùng cùng một prompt cho train và đánh giá holdout nếu mục tiêu là kiểm tra tổng quát hóa theo task.

### 6.2. Đầu ra báo cáo cho người học

- Mức CEFR ước lượng và confidence/range boundary.

- Sáu tiêu chí; nếu thiếu Task C phải ghi Interaction: chưa đủ bằng chứng.

- Evidence gồm timestamp, đoạn transcript, pause/rate và ví dụ cụ thể.

- Hai điểm mạnh, tối đa hai ưu tiên cải thiện, một nhiệm vụ luyện tiếp theo.

- Cờ audio kém, response ngắn, lệch chủ đề hoặc cần giảng viên duyệt.

- Model version, rubric version và ngày chấm để có thể truy vết.

## 7. Chiến lược dữ liệu, đặc biệt dữ liệu người Việt

### 7.1. Kết luận về dữ liệu công khai

Kết luận dữ liệu
Có dữ liệu người Việt nói tiếng Anh, nhưng chưa thấy corpus công khai vừa đủ lớn vừa có sáu điểm CEFR Speaking. Vì vậy dữ liệu công khai chỉ hỗ trợ pronunciation/ASR hoặc pretraining; bộ dữ liệu sinh viên Việt Nam được giảng viên chấm phải là tập kiểm định chính.

| Nguồn | Có người Việt? | Nhãn | Cách dùng |
| --- | --- | --- | --- |
| L2-ARCTIC | 4 người, 2 nam + 2 nữ | Transcript, phone alignment, lỗi phát âm; không CEFR | Kiểm tra ASR/phát âm giọng Việt; benchmark phụ |
| Speech Accent Archive | Có hơn 20 mẫu được liệt kê trong mirror | Đọc cùng đoạn, metadata; không CEFR | External sanity check cho accent Việt |
| CSLU Foreign Accented English | Có L1 Vietnamese | Accent 4 mức bởi 3 người nghe; toàn corpus 4.925 utterance | Nghiên cứu accent; phải mua/xin quyền |
| Speak & Improve 2025 | Toàn cầu; chưa xác nhận subset Việt | Khoảng 315 giờ, holistic CEFR | Benchmark CEFR chung nếu được cấp quyền; licence chặt |
| SpeechOcean762 | Không; L1 Mandarin | 5 chuyên gia; phone/word/sentence pronunciation | Pretrain/benchmark pronunciation, không đại diện Việt |
| Dữ liệu tại trường | Có | Sáu tiêu chí + overall do giảng viên chấm | Nguồn chính để hiệu chỉnh và kết luận |

### 7.2. Kế hoạch dữ liệu cục bộ trong 10 tuần

| Mức | Người tham gia | Responses | Ý nghĩa |
| --- | --- | --- | --- |
| Pilot | 10-15 | 20-35 | Sửa task, recorder và rubric; không dùng để kết luận chính |
| Mục tiêu | 40-60 | 80-120 monologue + 20-40 dialogue | Đủ cho proof-of-concept và GroupKFold theo speaker |
| Tối thiểu | 30 | 60 monologue | Chỉ kết luận thăm dò; Interaction có thể là extension |
| Tốt | 80-100 | 160-250 | Ổn định hơn nhưng khó hoàn thành chấm trong 10 tuần |

### 7.3. Quy trình thu

1. Xin phê duyệt/đồng thuận trước khi thu; mô tả mục đích, cách dùng audio, người chấm, thời hạn lưu và quyền rút dữ liệu.

1. Gán speaker_id giả danh; bảng liên hệ, consent và audio lưu tách biệt.

1. Thu Task A và B cho mọi người; Task C cho một tập con nếu thời gian cho phép.

1. Ghi metadata tối thiểu: task_version, duration, device_type, noise_flag, self-reported level hoặc chứng chỉ hiện có.

1. Chép tay 20-30% response để tính WER; ưu tiên đủ từng band và điều kiện thiết bị.

1. Hai giảng viên chấm độc lập toàn bộ nếu có thể; tối thiểu chấm kép 30%, gồm toàn bộ test set.

1. Tách train/dev/test theo speaker. Không để response của cùng người xuất hiện ở nhiều split.

### 7.4. Phân bổ nhãn và version

- Dùng quota mềm A2/B1/B2; nếu band lệch, không oversample trước khi chia speaker.

- Khóa dataset_v1 sau adjudication; mọi thay đổi tạo dataset_v2 và changelog.

- Không đưa dữ liệu hạn chế licence lên GitHub, Hugging Face hoặc API LLM có retention/training không phù hợp.

- Dữ liệu synthetic có thể kiểm tra API/UI nhưng không thay thế dữ liệu người thật để đánh giá độ chính xác.

## 8. Quy trình chấm của giảng viên

### 8.1. Chuẩn hóa giám khảo

1. Tổ chức buổi 60-90 phút đọc rubric và thống nhất khái niệm intelligibility, pause, error và best-fit.

1. Chọn 2-3 anchor cho mỗi band; thảo luận lý do chấm theo từng tiêu chí.

1. Chấm thử 8-12 response độc lập; tính QWK/ICC và xem chênh lệch theo criterion.

1. Sửa rubric/anchor trước khi chấm chính thức, không sửa ngầm giữa chừng.

1. Chấm mù, random order; giám khảo không thấy điểm AI khi tạo gold labels.

### 8.2. Xử lý bất đồng

| Tình huống | Quy tắc |
| --- | --- |
| Lệch 0-1 band | Có thể lấy median/consensus theo protocol đã chốt; vẫn lưu điểm từng rater |
| Lệch ≥2 band hoặc tiêu chí mâu thuẫn | Adjudication bởi rater thứ ba hoặc buổi thống nhất có biên bản |
| Audio kém/response thiếu | Gán invalid hoặc insufficient evidence; không ép về A2 |
| Interaction thiếu task | Để missing, không suy ra từ monologue |
| Human-human QWK thấp | Dừng train; kiểm tra rubric, anchor, prompt và đào tạo lại |

## 9. Kiến trúc kỹ thuật và pipeline chấm

Kiến trúc ưu tiên
Một pipeline hybrid có thể giải thích: audio và transcript tạo feature có version; mô hình ordinal dự đoán; LLM chỉ là baseline hoặc lớp diễn giải được grounded bằng evidence. Không để LLM tự do vừa chấm vừa bịa lý do.

| Tầng | Thành phần | Công nghệ khả thi | Đầu ra |
| --- | --- | --- | --- |
| Frontend | Recorder, Task UI, report, review queue | React/Next.js hoặc web framework sẵn có | Audio, turn log, report |
| API | Session, upload, scoring job, rating | FastAPI + background worker | JSON versioned |
| Speech | VAD, quality, ASR, timestamps | faster-whisper, ffmpeg, WebRTC VAD | Transcript + timing |
| Feature | Acoustic, lexical, grammar, discourse, interaction | librosa/parselmouth, spaCy, embeddings | Feature vector |
| Scoring | Criterion models + overall + calibration | Ordinal/logistic/tree model | Band probabilities |
| Feedback | Evidence selection + templates/LLM constrained | Template first; LLM optional | Strengths/actions |
| Storage | Metadata, audio, ratings, model registry | PostgreSQL/SQLite + object folder | Audit trail |

### 9.1. Pipeline chi tiết

1. Tạo session và gán task_id/prompt_version.

1. Thu audio; lưu file gốc; tạo bản chuẩn hóa mono 16 kHz cho xử lý.

1. Chạy quality gate: duration, clipping, silence, SNR proxy và language detection.

1. ASR có word timestamps; lưu transcript_raw, confidence và model version.

1. Trích audio features, text features và interaction features theo feature_version.

1. Dự đoán xác suất từng band cho từng criterion; calibration trên dev set.

1. Tổng hợp overall bằng mô hình/rule best-fit đã kiểm định; sinh review_reason nếu bất định.

1. Chọn evidence; tạo feedback theo template hoặc LLM constrained.

1. Lưu kết quả, model_version, rubric_version; hiển thị report hoặc đưa vào teacher queue.

### 9.2. Nguyên tắc scoring

- Feature là chỉ báo, không phải định nghĩa construct. Ví dụ speech rate không đồng nhất Fluency.

- Không dùng ASR confidence/WER làm điểm Phonology trực tiếp.

- Tiêu chí missing phải được giữ missing; không điền 0 vì sẽ kéo overall xuống sai.

- Mỗi output cần probability hoặc uncertainty; không chỉ trả label.

- Mọi lời giải thích phải truy về evidence đã lưu; cấm đưa lỗi không xuất hiện trong audio/transcript.

## 10. Mô hình, baseline và thực nghiệm

| Mô hình | Đầu vào | Mục đích |
| --- | --- | --- |
| B0 Majority/stratified | Phân phối nhãn | Mốc thấp nhất; phát hiện accuracy ảo do lệch lớp |
| B1 Audio-only | Rate, pause, prosody, embeddings | Đo tín hiệu Fluency/Phonology |
| B2 Transcript-only | Lexical, grammar, discourse | Đo Range/Accuracy/Coherence |
| B3 Frozen rubric LLM | Transcript + rubric + task | Baseline LLM; prompt và model version cố định |
| M1 Late fusion | B1 + B2 + interaction | Mô hình chính; ordinal probabilities |
| M2 Ablation | M1 bỏ từng feature group | Giải thích đóng góp và phát hiện shortcut |

### 10.1. Thiết kế split

- Nếu có ≥50 speakers: train/dev/test khoảng 60/20/20 theo speaker, cố gắng giữ phân phối band.

- Nếu chỉ 30-49 speakers: GroupKFold 5-fold cho phát triển và khóa 6-10 speakers làm holdout nếu đủ.

- External sanity set: bốn người Việt trong L2-ARCTIC hoặc Speech Accent Archive chỉ dùng kiểm tra robustness, không tính CEFR accuracy.

- Không tune prompt/model trên test set; chỉ chạy final holdout một lần ở Tuần 10.

### 10.2. Phân tích bắt buộc

- QWK/ICC human-human theo overall và từng criterion.

- QWK, MAE band, exact/adjacent accuracy, macro-F1 và confusion matrix AI-human.

- 95% bootstrap confidence interval theo speaker.

- Ablation audio/text/interaction; so sánh trên cùng split.

- WER trên tập chép tay và tương quan WER-sai số chấm.

- Tối thiểu 20 ca lỗi: AI cao hơn người, thấp hơn người, ASR lỗi, boundary và audio kém.

- Subgroup diagnostics theo dữ liệu được tự nguyện cung cấp và có đủ n; nếu n nhỏ chỉ mô tả, không kết luận fairness.

## 11. Kế hoạch triển khai chi tiết trong 10 tuần

Kế hoạch dưới đây dùng cổng G1-G10. Không chuyển sang bước sau nếu đầu ra nền tảng chưa đạt: đặc biệt không train trước khi rubric, nhãn và speaker split được khóa.

### Tuần 1. Chốt đề tài, construct và quản trị nghiên cứu

Mục tiêu: Biến ý tưởng thành một project charter có phạm vi A2-B2, câu hỏi nghiên cứu, người chấm và ràng buộc đạo đức rõ ràng.

Khối lượng dự kiến: 18-20 giờ

Các bước thực hiện:

1. Ngày 1: đọc CEFR Companion Volume, Appendix 3; lập bảng Range-Accuracy-Fluency-Interaction-Coherence-Phonology.

1. Ngày 2: lập literature/repository matrix gồm SpeechRater, Speak & Improve, L2-ARCTIC, SpeechOcean/GOPT, Speaklify và EvalYaks.

1. Ngày 3: chốt tên đề tài, RQ1-RQ5, dải A2-B2, formative use và Definition of Done sơ bộ.

1. Ngày 4: xác nhận hai giảng viên/rater, nguồn tuyển người học, consent, thời hạn lưu audio và quyền truy cập.

1. Ngày 5: tạo risk register, backlog, Git repository và lịch họp cố định với giảng viên.

Đầu ra bắt buộc:

- Project charter 2-3 trang và sơ đồ ALDM-L của đề tài.

- Research matrix có nguồn, dữ liệu, construct, metric và giới hạn.

- Draft consent/data management plan; danh sách rater và lịch chấm.

- Backlog được chia MVP/stretch, không có hạng mục LMS/phỏng vấn ngoài phạm vi.

Cổng G1
Giảng viên hướng dẫn duyệt tên, A2-B2, RQ, vai trò hai rater và chiến lược dữ liệu. Nếu chưa xác nhận được rater, không hứa hẹn AI-human validation trong đề cương.

Phương án dự phòng: Nếu thủ tục thu dữ liệu chưa rõ, chuẩn bị pipeline trên corpus công khai nhưng chưa thu người thật; đồng thời đổi lịch để xin phép trong Tuần 1-2.

### Tuần 2. Thiết kế rubric, task và protocol chấm

Mục tiêu: Tạo công cụ đo trước khi xây mô hình, bảo đảm mỗi tiêu chí có bằng chứng và nhiệm vụ phù hợp.

Khối lượng dự kiến: 20-22 giờ + 2 giờ/rater

Các bước thực hiện:

1. Ngày 1: viết rubric A2/B1/B2 cho sáu tiêu chí bằng ngôn ngữ vận hành, tránh sao chép nguyên văn dài.

1. Ngày 2: thiết kế Task A/B/C, prompt bank, time limit, follow-up tree và quality rules.

1. Ngày 3: tạo rating form, reason codes, quy tắc missing/invalid và adjudication.

1. Ngày 4: cùng hai rater chấm thử 4-6 audio mẫu công khai; ghi điểm bất đồng và sửa descriptor.

1. Ngày 5: chốt data schema, file naming, prompt_version, rubric_version và rater guide v1.

Đầu ra bắt buộc:

- Rubric v1 + rater handbook + rating spreadsheet/form.

- Task blueprint và tối thiểu 6 prompt (2 biến thể cho mỗi task).

- Consent/participant instruction và checklist chất lượng audio.

- Data dictionary/schema v1.

Cổng G2
Hai rater có thể áp dụng rubric cho cùng mẫu và giải thích khác biệt. Mọi criterion đều có task tạo bằng chứng; Interaction không được suy ra từ monologue.

Phương án dự phòng: Nếu Task C chưa ổn định, giữ A/B là MVP; mô tả Interaction là giai đoạn mở rộng và không báo overall đầy đủ sáu tiêu chí.

### Tuần 3. Xây vertical slice và chuẩn bị dữ liệu

Mục tiêu: Có một luồng end-to-end từ ghi âm đến report thô, đồng thời nhập được public data để kiểm tra pipeline.

Khối lượng dự kiến: 22-25 giờ

Các bước thực hiện:

1. Ngày 1: tạo cấu trúc frontend/backend/data/model; định nghĩa API session, response, score và rating.

1. Ngày 2: xây recorder/upload, kiểm tra định dạng và lưu audio theo speaker_id/session_id.

1. Ngày 3: tích hợp ffmpeg + faster-whisper; trả transcript và word timestamps.

1. Ngày 4: quality gate duration/silence/clipping; log model_version và lỗi xử lý.

1. Ngày 5: tải/đọc L2-ARCTIC theo licence; lọc bốn người Việt; chạy batch thử và tạo report JSON.

Đầu ra bắt buộc:

- Demo: record → upload → transcript → features cơ bản → report JSON.

- Data loader cho local audio và L2-ARCTIC.

- Logging, error code và README cài đặt tối thiểu.

- Unit test cho audio validation và schema.

Cổng G3
Một response 90-120 giây được xử lý end-to-end không thao tác tay; lỗi audio trả reason code rõ; không lộ tên thật trong đường dẫn/log.

Phương án dự phòng: Nếu UI chậm, dùng Streamlit/form web đơn giản; giá trị nghiên cứu nằm ở dữ liệu và đánh giá, không nằm ở frontend phức tạp.

### Tuần 4. Pilot, hiệu chỉnh task và rater calibration

Mục tiêu: Phát hiện lỗi đo lường và kỹ thuật trước khi thu chính thức.

Khối lượng dự kiến: 20 giờ + 3-4 giờ/rater

Các bước thực hiện:

1. Tuyển 10-15 sinh viên pilot, cố gắng có trình độ khác nhau; mỗi người làm A/B, một số làm C.

1. Theo dõi completion, duration, noise, lỗi recorder, ASR failure và phản hồi người dùng.

1. Hai rater chấm mù cùng tối thiểu 10-15 response; tính QWK/ICC sơ bộ.

1. Chép tay một tập con, tính WER và kiểm tra lỗi đặc thù giọng Việt.

1. Sửa prompt/rubric/UI; đóng băng rubric_v1 và prompt_v1 trước main collection.

Đầu ra bắt buộc:

- Pilot dataset và pilot report.

- Human-human agreement theo overall/criterion.

- Danh sách lỗi ASR/task/UI và quyết định sửa.

- Rubric_v1, prompt_v1, rater_guide_v1 đã khóa.

Cổng G4
Task completion ≥85%; không có lỗi hệ thống nghiêm trọng; human agreement đạt mức dùng được hoặc có kế hoạch calibration lại. Nếu QWK <0,60, dừng thu chính thức.

Phương án dự phòng: Nếu agreement thấp, thu hẹp rubric về A2/B1/B2, tăng anchor và chấm lại pilot; không giải quyết bằng cách lấy trung bình điểm bất nhất.

### Tuần 5. Thu dữ liệu chính - đợt 1 và chấm cuốn chiếu

Mục tiêu: Thu khoảng một nửa chỉ tiêu và phát hiện lệch band/thiết bị sớm.

Khối lượng dự kiến: 20-24 giờ + 3 giờ/rater

Các bước thực hiện:

1. Tuyển 20-30 người đầu; xác nhận consent và hướng dẫn mic/môi trường.

1. Thu Task A/B; thu Task C cho 10-15 người nếu module ổn định.

1. Chạy quality gate hằng ngày; yêu cầu ghi lại ngay khi audio không hợp lệ.

1. Rater chấm cuốn chiếu theo batch nhỏ, random order; không thấy điểm AI.

1. Theo dõi dashboard quota band, giới tính tự nguyện, device và noise; điều chỉnh tuyển mẫu.

Đầu ra bắt buộc:

- Khoảng 40-60 monologue hợp lệ và 10-15 dialogue.

- Bảng tiến độ chấm và missing/invalid reasons.

- Data quality report đợt 1.

- Danh sách subgroup còn thiếu để tuyển bổ sung.

Cổng G5
Ít nhất 90% file có metadata và task_version đúng; invalid rate được giải thích; không có dữ liệu định danh trong kho làm việc của mô hình.

Phương án dự phòng: Nếu tuyển chậm, mở thêm lớp/kênh tuyển đã được phép; ưu tiên đủ speakers hơn nhiều task trên cùng một speaker.

### Tuần 6. Hoàn tất thu, khóa nhãn và chia dữ liệu

Mục tiêu: Đạt quy mô tối thiểu, hoàn tất chấm kép/adjudication và khóa dataset v1 theo speaker.

Khối lượng dự kiến: 22-25 giờ + 4-6 giờ/rater

Các bước thực hiện:

1. Thu bổ sung để đạt 40-60 speakers; ưu tiên band/subgroup thiếu.

1. Hoàn tất double-rating toàn test set và tối thiểu 30% toàn bộ corpus; adjudicate ca lệch lớn.

1. Chép tay đủ 20-30% response để đánh giá ASR.

1. Tính human-human agreement chính thức; kiểm tra drift giữa batch đầu/cuối.

1. Tạo train/dev/test hoặc GroupKFold groups theo speaker; khóa dataset manifest và checksum.

Đầu ra bắt buộc:

- Dataset_v1 ẩn danh + datasheet + manifest.

- Gold ratings, điểm từng rater và adjudicated label.

- Human agreement report và WER subset.

- Speaker-level split đã khóa; changelog/version log.

Cổng G6
Không có speaker leakage; human agreement đủ để huấn luyện; test labels được tách khỏi quá trình phát triển. Tất cả file có consent_version và retention status.

Phương án dự phòng: Nếu <30 speakers hoặc nhãn chưa ổn định, chuyển mục tiêu thành exploratory prototype, dùng GroupKFold và giảm tuyên bố; không dựng con số accuracy từ split ngẫu nhiên theo response.

### Tuần 7. Trích xuất feature và xây baseline

Mục tiêu: Có bảng kết quả B0-B3 trên cùng split và pipeline tái lập.

Khối lượng dự kiến: 24-28 giờ

Các bước thực hiện:

1. Xây B0 majority/stratified và script đánh giá chuẩn.

1. Trích audio features: rate, articulation rate, pause count/ratio, run length, pitch/prosody summary.

1. Trích text features: lexical diversity, grammar error proxies, sentence/syntax, discourse/coherence.

1. Trích interaction features: response latency, relevance, clarification, turn balance và completion.

1. Train B1 audio-only, B2 transcript-only; chạy B3 frozen LLM nếu licence/privacy cho phép; log seeds/config.

Đầu ra bắt buộc:

- Feature pipeline versioned và feature dictionary.

- Baseline result table: QWK, MAE, adjacent accuracy, macro-F1.

- Confusion matrix và danh sách lỗi ban đầu.

- Experiment config, seed và README tái lập.

Cổng G7
Ít nhất một baseline tốt hơn B0 theo QWK/macro-F1 mà không rò rỉ speaker/task. Kết quả tái chạy cho cùng seed/config nhất quán.

Phương án dự phòng: Nếu text feature bị ASR phá mạnh, dùng transcript chép tay subset để lượng hóa upper bound; không âm thầm thay transcript test bằng bản sửa tay.

### Tuần 8. Fusion, calibration và phân tích lỗi

Mục tiêu: Xây mô hình chính M1, chứng minh đóng góp từng nguồn và xác định rule human review.

Khối lượng dự kiến: 24-28 giờ

Các bước thực hiện:

1. Train late-fusion/ordinal model trên audio + text + interaction với regularization.

1. Calibrate probability trên dev set; thử threshold boundary và low-confidence queue.

1. Chạy ablation bỏ audio, text, interaction và các feature có nguy cơ shortcut.

1. Bootstrap CI theo speaker; kiểm tra sai số theo band/device/noise khi đủ mẫu.

1. Phân tích thủ công tối thiểu 20 ca; gắn taxonomy: ASR, prompt, audio, boundary, rubric, model.

Đầu ra bắt buộc:

- M1 model artifact + model card draft.

- Ablation/calibration/error-analysis report.

- Confidence thresholds và review_reason rules.

- Quyết định feature nào được giữ cho bản demo.

Cổng G8
M1 được so với tất cả baseline trên cùng split; confidence có ý nghĩa vận hành; mọi subgroup claim có sample size và CI.

Phương án dự phòng: Nếu fusion không tốt hơn baseline, giữ mô hình đơn giản tốt nhất và giải thích nguyên nhân; không chọn model phức tạp chỉ để trình diễn.

### Tuần 9. Tích hợp báo cáo, teacher review và usability

Mục tiêu: Biến pipeline nghiên cứu thành demo end-to-end có bằng chứng, giới hạn và luồng người duyệt.

Khối lượng dự kiến: 22-26 giờ

Các bước thực hiện:

1. Tích hợp model đã khóa vào scoring service; thêm timeout, retry và job status.

1. Xây report: level/boundary, six criteria, confidence, evidence, strengths/actions và caveat.

1. Xây teacher queue: low confidence, invalid audio, criterion conflict và AI-human discrepancy.

1. Test với 5-8 sinh viên và 2 giảng viên; đo task completion, thời gian, Likert/SUS và phỏng vấn ngắn.

1. Sửa lỗi nghiêm trọng; khóa UI/API/model version cho đánh giá cuối.

Đầu ra bắt buộc:

- Demo web end-to-end và teacher review queue.

- Usability notes/data và danh sách fix.

- API documentation và deployment guide.

- Model/rubric/version hiển thị trong report.

Cổng G9
Người dùng hoàn thành workflow không trợ giúp đáng kể; report không bịa evidence; trường hợp low confidence được chuyển đúng sang review.

Phương án dự phòng: Nếu frontend chưa hoàn thiện, dùng giao diện đơn giản nhưng giữ đủ recorder, report và review queue; không dành tuần cuối cho animation/design phụ.

### Tuần 10. Đánh giá cuối, viết báo cáo và đóng gói

Mục tiêu: Chạy holdout một lần, hoàn thiện bằng chứng nghiên cứu và chuẩn bị bảo vệ tái lập được.

Khối lượng dự kiến: 26-30 giờ

Các bước thực hiện:

1. Khóa code/config rồi chạy final holdout; xuất metric, CI, confusion matrix và calibration plot.

1. Hoàn thiện error/fairness discussion, limitations và threat-to-validity.

1. Hoàn thiện datasheet, model card, consent/data retention record và licence inventory.

1. Viết/ghép các chương phương pháp, hệ thống, kết quả; kiểm tra mọi claim có bảng/nguồn hỗ trợ.

1. Đóng gói repo, requirements, seed/config, demo script, slide và phương án offline nếu mất mạng.

Đầu ra bắt buộc:

- Báo cáo thực nghiệm cuối và luận văn draft hoàn chỉnh.

- Source code + setup + test + sample data không nhạy cảm.

- Model card, dataset datasheet, ethics/licence note.

- Slide, kịch bản demo 5-7 phút và checklist bảo vệ.

Cổng G10
Một máy sạch có thể chạy demo theo README; test set không bị dùng để tune; mọi số liệu trong slide khớp báo cáo; giới hạn low-stakes và A2-B2 được nêu rõ.

Phương án dự phòng: Nếu metric không đạt mục tiêu, báo cáo trung thực baseline, human ceiling, error taxonomy và giới hạn dữ liệu; giá trị khóa luận vẫn nằm ở quy trình đánh giá nghiêm túc.

### 11.1. Tóm tắt cổng tiến độ

| Tuần | Cổng | Không đạt thì |
| --- | --- | --- |
| 1 | Duyệt scope + rater + data plan | Hạ phạm vi, chưa cam kết validation |
| 2 | Rubric/task đo được construct | Sửa trước khi code scoring |
| 3 | Vertical slice chạy được | Đơn giản hóa UI/stack |
| 4 | Pilot + agreement dùng được | Calibration và chấm lại |
| 5 | 50% quota, metadata sạch | Điều chỉnh tuyển/collection |
| 6 | Dataset/split/label khóa | Chuyển exploratory |
| 7 | Baselines tái lập | Sửa leakage/feature pipeline |
| 8 | Model + uncertainty + analysis | Giữ baseline đơn giản |
| 9 | Demo và review queue dùng được | Bỏ polish, giữ workflow |
| 10 | Holdout + report + package | Không thêm feature mới |

## 12. Phân vai, nguồn lực, rủi ro và đạo đức

### 12.1. Phân vai Human-AI

| Chủ thể | Trách nhiệm |
| --- | --- |
| Sinh viên thực hiện khóa luận | Thiết kế kỹ thuật, thu/xử lý dữ liệu, thực nghiệm, tài liệu, bảo mật và báo cáo giới hạn |
| Giảng viên ngoại ngữ/rater | Chuẩn hóa rubric, anchor, chấm mù, adjudication và kiểm duyệt phản hồi |
| Giảng viên hướng dẫn | Duyệt construct, phương pháp, ethics, scope và diễn giải kết quả |
| Người học tham gia | Đồng thuận, thực hiện task và có quyền theo quy trình của nghiên cứu |
| AI | ASR, feature, ước lượng, chọn evidence và đề xuất feedback; không ra quyết định học vụ |

### 12.2. Nguồn lực tối thiểu

- Máy phát triển có 16 GB RAM; GPU là lợi thế nhưng có thể dùng faster-whisper small/base hoặc batch cloud đã được phép.

- Hai rater; tổng 8-14 giờ/người tùy số response và tỷ lệ chấm kép.

- Không gian thu tương đối yên tĩnh và ít nhất một kịch bản thu bằng thiết bị cá nhân để kiểm tra robustness.

- Kho lưu audio có kiểm soát truy cập; backup; retention/deletion plan.

- Repo riêng cho code; dữ liệu nhạy cảm nằm ngoài Git và được `.gitignore`.

### 12.3. Rủi ro và kiểm soát

| Rủi ro | Dấu hiệu | Kiểm soát |
| --- | --- | --- |
| Thiếu dữ liệu/band | Một lớp chiếm đa số | Quota, macro metrics, GroupKFold; thu bổ sung; hạ claim |
| Rater không nhất quán | QWK thấp | Anchor, calibration, chấm mù, adjudication |
| ASR sai accent Việt | WER cao; lỗi từ giả | WER subset, audio features độc lập, review rule |
| Prompt không tương đương | Điểm lệch theo prompt | Blueprint, version, pilot và randomization |
| LLM hallucination | Feedback không có evidence | Template/grounding, schema validation, human review |
| Data leakage | Cùng speaker nhiều split | Group split, manifest/check tự động |
| Rò rỉ dữ liệu | Audio/ID xuất hiện trong repo/log | Pseudonym, access control, retention, privacy audit |
| Quá phạm vi | UI/chatbot chiếm tiến độ | MVP gate; bỏ Group 3/4 trước khi giảm validation |

### 12.4. Đạo đức và sử dụng có trách nhiệm

- Không dùng output như chứng chỉ, điểm thi chính thức hoặc căn cứ duy nhất cho quyết định học vụ.

- Không suy diễn giới tính, dân tộc, tính cách, tình trạng sức khỏe hoặc khả năng nghề nghiệp từ giọng nói.

- Cho người dùng biết hệ thống dùng AI, phạm vi A2-B2, dữ liệu nào được lưu và khi nào cần người duyệt.

- Không phạt accent; tập trung intelligibility và khả năng truyền đạt.

- Tuân thủ licence: L2-ARCTIC CC BY-NC 4.0; Speak & Improve có điều khoản nghiên cứu và hạn chế chia sẻ/xử lý.

- Model card phải công bố population, task, version, metric, failure modes và prohibited uses.

## 13. Sản phẩm bàn giao và Definition of Done

### 13.1. Sản phẩm

- Rubric A2-B2, rater guide, anchor set và task blueprint.

- Dataset cục bộ ẩn danh, datasheet, manifest và consent/retention record trong phạm vi được phép.

- Pipeline audio quality, ASR, feature, scoring, calibration, evidence và feedback.

- Web app recorder/report và teacher review queue.

- Experiment package: splits, configs, seeds, metrics, plots, error taxonomy và ablation.

- Model card, API/setup docs, licence inventory, demo script và luận văn.

### 13.2. Definition of Done

- Rubric/task được giảng viên phê duyệt trước main collection.

- Có human-human agreement và quy trình xử lý bất đồng.

- Mọi split theo speaker; test set khóa trước tuning.

- Có B0, audio-only, transcript-only và model chính; có ablation.

- Báo cáo QWK, MAE band, adjacent accuracy, macro-F1 và confidence interval.

- Có WER subset, error analysis và diagnostics theo điều kiện âm thanh.

- Demo hiển thị confidence, evidence, version và human review.

- Không có dữ liệu nhạy cảm trong Git; có model card/datasheet/README.

- Claim trong kết luận chỉ áp dụng cho population, task và level đã kiểm chứng.

### 13.3. MVP và stretch

| MVP phải bảo vệ được | Stretch chỉ làm sau G8 |
| --- | --- |
| Task A/B; recorder; quality gate | Task C hội thoại realtime |
| ASR + audio/text features | GOPT/phone-level visualization nâng cao |
| A2/B1/B2 + five production criteria | Đủ Interaction và overall sáu tiêu chí |
| Confidence/evidence + teacher review | Personalized task recommendation |
| Baseline/fusion/error analysis | Longitudinal progress dashboard |

## 14. Cấu trúc luận văn đề xuất

| Chương | Nội dung |
| --- | --- |
| 1. Mở đầu | Bối cảnh, vấn đề, mục tiêu, RQ, phạm vi, đóng góp và giới hạn low-stakes |
| 2. Cơ sở lý thuyết | CEFR speaking construct, automated speech scoring, L2 ASR, dữ liệu và hệ thống liên quan |
| 3. Phương pháp | Task/rubric, participants, consent, rating protocol, feature/model, split và metrics |
| 4. Thiết kế hệ thống | Kiến trúc, API, schema, pipeline, UI, audit và bảo mật |
| 5. Kết quả | Human agreement, baseline, fusion, ablation, calibration, WER, error/subgroup analysis |
| 6. Thảo luận | Trả lời RQ, threat-to-validity, giới hạn, đạo đức và hướng phát triển |

## Phụ lục A. Rubric vận hành A2-B2

Các descriptor dưới đây là bản vận hành rút gọn để thí nghiệm, cần được giảng viên hiệu chỉnh bằng anchor. Chúng không thay thế nguyên văn CEFR và không tự tạo liên kết chính thức với CEFR.

### Range

| Mức | Descriptor vận hành |
| --- | --- |
| A2 | Dùng mẫu câu đơn giản và vốn từ hạn chế cho nhu cầu quen thuộc; thường phải vòng tránh khi thiếu từ. |
| B1 | Có đủ ngôn ngữ cho chủ đề quen thuộc; diễn đạt được ý chính dù còn do dự/circumlocution. |
| B2 | Có phạm vi đủ rộng để mô tả rõ và nêu quan điểm; dùng được một số cấu trúc phức. |

### Accuracy

| Mức | Descriptor vận hành |
| --- | --- |
| A2 | Kiểm soát một số cấu trúc đơn giản; lỗi thường xuyên nhưng ý cơ bản còn hiểu được. |
| B1 | Dùng tương đối chính xác các mẫu quen thuộc; lỗi xuất hiện ở cấu trúc khó nhưng ít phá nghĩa. |
| B2 | Kiểm soát ngữ pháp tương đối cao; lỗi không thường gây hiểu nhầm và có khả năng tự sửa. |

### Fluency

| Mức | Descriptor vận hành |
| --- | --- |
| A2 | Tạo cụm/câu ngắn; pause, restart và reformulation rõ, cần thời gian lập kế hoạch. |
| B1 | Duy trì lời nói dễ hiểu; pause để tìm từ/ngữ pháp còn rõ trong đoạn dài. |
| B2 | Nói với nhịp khá đều; có do dự nhưng không gây căng thẳng đáng kể cho người nghe. |

### Interaction

| Mức | Descriptor vận hành |
| --- | --- |
| A2 | Trao đổi đơn giản khi đối tác hỗ trợ; phản hồi câu hỏi trực tiếp và dùng công thức quen thuộc. |
| B1 | Khởi tạo, duy trì và kết thúc hội thoại đơn giản; xác nhận hiểu và phản hồi phù hợp chủ đề quen thuộc. |
| B2 | Chủ động quản lý lượt, follow-up, duy trì thảo luận và thích ứng tương đối tự nhiên với đối tác. |

### Coherence

| Mức | Descriptor vận hành |
| --- | --- |
| A2 | Nối cụm/câu bằng liên từ rất cơ bản; ý thường liệt kê hoặc rời ngắn. |
| B1 | Liên kết chuỗi điểm đơn giản theo tuyến tính; chủ đề nhìn chung theo dõi được. |
| B2 | Phát triển ý rõ, dùng phương tiện liên kết phù hợp; cấu trúc bài nói tương đối mạch lạc. |

### Phonology

| Mức | Descriptor vận hành |
| --- | --- |
| A2 | Nhìn chung hiểu được từ/cụm quen thuộc nhưng người nghe đôi khi cần nỗ lực hoặc yêu cầu lặp. |
| B1 | Phát âm nhìn chung dễ hiểu; stress/intonation xấp xỉ phù hợp dù ảnh hưởng L1 còn rõ. |
| B2 | Dễ hiểu xuyên suốt; kiểm soát stress, rhythm, intonation đủ để hỗ trợ thông điệp; accent không cản trở. |

## Phụ lục B. Lược đồ dữ liệu tối thiểu

| Nhóm | Trường gợi ý | Ghi chú |
| --- | --- | --- |
| Định danh giả | speaker_id, session_id, response_id | Không dùng MSSV/tên trong pipeline |
| Consent | consent_version, consent_time, withdrawal_status | Lưu tách bảng liên hệ |
| Task | task_id, prompt_version, task_type, target_band | Đảm bảo truy vết độ khó |
| Audio | audio_uri, duration, sample_rate, device_type, noise_flag | File gốc + bản 16 kHz |
| ASR | transcript_raw, word_timestamps, asr_confidence, asr_version | Bản chép tay lưu trường riêng |
| Rating | rater_id, six_criteria, overall, comment, adjudicated | Giữ điểm từng rater |
| Feature | feature_version, acoustic/text/interaction_features | Không lưu object không version |
| Prediction | criterion_probs, overall_probs, confidence, evidence | Có review_reason/status |
| Audit | model_version, rubric_version, created_at, processing_log | Tái lập và giải trình |

## Phụ lục C. API và cấu trúc module gợi ý

| Endpoint | Trách nhiệm |
| --- | --- |
| POST /sessions | Tạo phiên, gán task set và prompt_version |
| POST /responses | Tải audio/turn log, kiểm tra consent và định dạng |
| POST /responses/{id}/score | Chạy pipeline bất đồng bộ |
| GET /responses/{id}/report | Trả criterion, overall, confidence, evidence và version |
| POST /ratings | Nhập điểm rater và adjudication status |
| GET /teacher/review-queue | Danh sách low confidence/invalid/conflict |
| GET /analytics/evaluation | QWK, MAE, F1, confusion và diagnostics |

Cấu trúc thư mục tham khảo:

apps/web/                 # recorder, report, teacher review

services/api/            # FastAPI routes và jobs

src/speech/              # quality, VAD, ASR

src/features/            # acoustic, text, interaction

src/scoring/             # baselines, fusion, calibration

src/feedback/            # evidence + templates/LLM guardrails

experiments/configs/     # splits, seeds, model configs

data/manifests/          # chỉ manifest ẩn danh, không commit audio

docs/                    # rubric, datasheet, model card, ethics

tests/                   # schema, leakage, audio, API tests

## Phụ lục D. Checklist khởi động 48 giờ đầu

1. Gửi tên đề tài và phạm vi A2-B2 cho giảng viên duyệt.

1. Xác nhận hai rater, thời gian calibration và số response có thể chấm.

1. Xin mẫu consent/quy trình ethics của trường.

1. Tạo repo, `.gitignore` cho audio/ID và issue board 10 tuần.

1. Tải CEFR Companion Volume và tạo rubric working sheet.

1. Đăng ký/truy cập L2-ARCTIC theo đúng licence.

1. Chạy thử faster-whisper với ba audio giọng Việt.

1. Chốt ngày pilot cuối Tuần 4 và main collection Tuần 5-6.

## Tài liệu tham khảo và đường dẫn

[1] Council of Europe (2020), CEFR Companion Volume. Mở nguồn. Appendix 3: qualitative features of spoken language

[2] Council of Europe, CEFR level descriptions and assessment resources. Mở nguồn

[3] Zhao et al. (2018), L2-ARCTIC official corpus page. Mở nguồn. Includes four Vietnamese L1 speakers

[4] KoelLabs processed L2-ARCTIC dataset. Mở nguồn. CC BY-NC 4.0; gated access

[5] Cambridge University Press & Assessment, Speak & Improve Corpus 2025. Truy cập có đăng ký theo research licence; holistic CEFR-like; cấm tái phân phối và có hạn chế derivative release.

[6] Zhang et al., SpeechOcean762. Mở nguồn. Public pronunciation scoring corpus; L1 Mandarin

[7] Gong et al., GOPT pronunciation assessment implementation. Mở nguồn. Pronunciation component, not holistic CEFR

[8] ETS, Automated Scoring of Spontaneous Speech Using SpeechRater v1.0. Mở nguồn

[9] LDC, CSLU Foreign Accented English Release 1.2. Mở nguồn. Includes Vietnamese L1; licensed access

[10] Speaklify public repository. Mở nguồn. Closest public end-to-end prototype; study/cite, do not reuse as coursework

[11] EvalYaks public repository. Mở nguồn. B2 transcript/interaction scoring reference

[12] Speech Accent Archive dataset mirror. Mở nguồn. Vietnamese-accented English samples; no CEFR

Nguồn nội bộ: “2026 Định hướng xác định đề tài khóa luận.docx”, phần ALDM-L và bốn nhóm đề tài; “Phan_tich_va_huong_lam_de_tai_AI_Assessor_CEFR.docx”, bản phân tích nền đã tạo trong workspace.
