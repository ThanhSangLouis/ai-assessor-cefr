# Xây dựng hệ thống AI hỗ trợ đánh giá năng lực nói tiếng Anh theo CEFR cho sinh viên đại học Việt Nam ở trình độ A2-B2

> Bản Markdown được chuyển từ [`AI_Assessor_Speaking_CEFR_10_tuan.pptx`](../artifacts/source/presentations/AI_Assessor_Speaking_CEFR_10_tuan.pptx). Nội dung được sắp theo từng slide; file gốc được giữ nguyên.

## Slide 1: BÁO CÁO ĐỊNH HƯỚNG KHÓA LUẬN

- Thiết kế đánh giá • Dữ liệu người Việt • Lộ trình triển khai 10 tuần
- ALDM-L: Speaking × Assess × AI Assessor<br>Phạm vi kiểm chứng đề xuất: sinh viên Việt Nam, A2–B2, formative assessment
- 20.08.2026

## Slide 2: ĐỊNH HƯỚNG KHÓA LUẬN

- Đề tài đáng làm, nhưng phải chứng minh độ tin cậy
- Giá trị nghiên cứu không nằm ở việc gọi một mô hình AI, mà ở cách đo đúng construct và kiểm định với giảng viên.
- 6
- 4
- 10
- mặt của Speaking cần được đánh giá theo CEFR
- người Việt trong L2-ARCTIC — hữu ích nhưng quá nhỏ và không có CEFR
- tuần để xây, thu dữ liệu và kiểm định một proof-of-concept
- Kết luận: phạm vi phải là A2–B2, low-stakes và có human review.

## Slide 3: ĐỊNH HƯỚNG KHÓA LUẬN

- Khoảng trống không nằm ở việc “dùng AI”
- Đã có hệ thống công khai
- Đóng góp có thể bảo vệ
- Speaklify: pipeline CEFR end-to-end, gần trùng ý tưởng sản phẩm.<br>EvalYaks: chấm transcript Cambridge B2, không có pronunciation audio.<br>GOPT/SpeechOcean: mạnh ở pronunciation, không phải CEFR holistic.<br>Các demo ứng dụng thường thiếu kiểm định với rater và accent Việt.
- Rubric CEFR A2–B2 được vận hành hóa và có anchor.<br>Dữ liệu sinh viên Việt Nam được hai giảng viên chấm.<br>Speaker-level split, AI–human agreement và calibration.<br>Phân tích lỗi ASR giọng Việt, uncertainty và human review.
- Không fork một đồ án có sẵn; dùng chúng làm related work và baseline kiến trúc.

## Slide 4: ĐỊNH HƯỚNG KHÓA LUẬN

- Phương án tốt nhất: Nhóm 1 + phần cần thiết của Nhóm 2
- Một chu trình duy nhất giúp giữ phạm vi và làm rõ vai trò sư phạm của từng AI.
- 01
- 02
- 03
- 04
- AI Assessor
- Conversation Partner
- AI Feedbacker
- Personalizer
- Lõi nghiên cứu<br>Chấm A2/B1/B2 + tiêu chí
- Tạo Task C bán cấu trúc<br>Đo Interaction
- Giải thích bằng evidence<br>Ưu tiên cải thiện
- Chỉ là stretch<br>Chọn 1–2 task tiếp theo
- Không triển khai đồng thời LMS, thi high-stakes, phỏng vấn việc làm và chatbot tự do trong 10 tuần.

## Slide 5: ĐỊNH HƯỚNG KHÓA LUẬN

- CEFR yêu cầu sáu mặt của năng lực nói
- Range
- Accuracy
- Fluency
- Từ vựng và cấu trúc đủ để diễn đạt ý
- Mức kiểm soát ngữ pháp và cách tự sửa
- Nhịp nói, pause và khả năng duy trì lời nói
- Interaction
- Coherence
- Phonology
- Khởi tạo, phản hồi, hỏi lại và quản lý lượt
- Phát triển chủ đề và liên kết các ý
- Intelligibility, âm, trọng âm, nhịp và ngữ điệu
- Interaction chỉ được chấm khi có nhiệm vụ tương tác; accent không phải lỗi nếu thông điệp vẫn dễ hiểu.

## Slide 6: ĐỊNH HƯỚNG KHÓA LUẬN

- Ba nhiệm vụ tạo đủ bằng chứng để chấm
- A
- B
- C
- Kể / mô tả
- Nêu quan điểm
- Hội thoại bán cấu trúc
- 90–120 giây
- 120 giây
- 3–5 lượt
- Range • Fluency<br>Coherence • Phonology
- Range • Accuracy<br>Coherence
- Interaction • Fluency<br>Response relevance
- Một trải nghiệm học tập đáng nhớ
- Có nên dùng AI khi học ngoại ngữ?
- Lập kế hoạch hoạt động nhóm

## Slide 7: ĐỊNH HƯỚNG KHÓA LUẬN

- Dữ liệu người Việt có, nhưng chưa có nhãn CEFR đầy đủ
- Corpus công khai hỗ trợ pronunciation/ASR; dữ liệu tại trường mới là tập kiểm định chính.
- *Số mẫu mirror cần kiểm tra lại trước khi công bố thống kê chính thức.

## Slide 8: ĐỊNH HƯỚNG KHÓA LUẬN

- Pipeline chấm: tách bằng chứng khỏi diễn giải
- 01
- 02
- 03
- 04
- 05
- 06
- Task + audio
- Quality + ASR
- Feature lanes
- Criterion models
- Calibration
- Evidence + review
- A / B / C
- VAD • noise • timestamps
- Audio • text • interaction
- A2 / B1 / B2 probabilities
- overall • boundary • confidence
- feedback • teacher queue
- LLM, nếu dùng, chỉ nhận rubric + evidence đã kiểm chứng để diễn giải; điểm chính phải lặp lại được và có version.

## Slide 9: ĐỊNH HƯỚNG KHÓA LUẬN

- Mô hình được đánh giá so với cả baseline và giảng viên
- Thang baseline
- Bằng chứng thành công
- QWK
- B0
- Majority / stratified
- metric chính cho AI–human agreement
- B1
- Audio-only
- Human–human agreement trước khi train<br>MAE theo band + adjacent accuracy<br>Macro-F1 + confusion matrix<br>WER trên tập chép tay<br>Calibration + error analysis
- B2
- Transcript-only
- B3
- Frozen rubric LLM
- M1
- Late fusion + calibration
- QWK ≥ 0,60 là mục tiêu dự án, không phải chuẩn CEFR chính thức.

## Slide 10: ĐỊNH HƯỚNG KHÓA LUẬN

- Mười tuần được quản lý bằng cổng G1–G10
- W1
- W2
- W3
- W4
- W5
- W6
- W7
- W8
- W9
- W10
- Research + scope
- G2
- Build vertical slice
- G3
- Pilot + calibration
- G4
- Collect + lock data
- G6
- Baseline + fusion
- G8
- Integrate + usability
- G9
- Final holdout + report
- G10
- Không đạt cổng → hạ phạm vi hoặc sửa nền tảng; không bù bằng cách thêm tính năng trình diễn.

## Slide 11: ĐỊNH HƯỚNG KHÓA LUẬN

- Rủi ro lớn nhất là dữ liệu và nhãn, không phải frontend
- RỦI RO
- KIỂM SOÁT
- Thiếu band / ít speaker
- Quota mềm • GroupKFold • hạ tuyên bố
- Rater không nhất quán
- Anchor • calibration • adjudication
- ASR sai accent Việt
- WER subset • audio features • review rule
- LLM bịa feedback
- Evidence grounding • template • human review
- Quá phạm vi
- MVP gate • bỏ Group 3/4 trước khi giảm validation
- Ưu tiên theo thứ tự: rubric → rater → dữ liệu → thực nghiệm → demo.

## Slide 12: QUYẾT ĐỊNH CẦN CHỐT

- Ba điều kiện để bắt đầu đúng hướng
- Phạm vi
- 01
- A2–B2 • low-stakes • Nhóm 1 + phần Nhóm 2
- Con người
- 02
- Hai rater • calibration • chấm mù • adjudication
- Dữ liệu
- 03
- 40–60 sinh viên mục tiêu • speaker split • consent
- Khuyến nghị: duyệt MVP trước, chỉ thêm hội thoại/personalizer khi dữ liệu và baseline đã qua cổng G8.
