# Xây dựng hệ thống AI hỗ trợ đánh giá năng lực nói tiếng Anh theo CEFR cho sinh viên đại học Việt Nam ở trình độ A2-B2

> Bản Markdown được chuyển từ [`AI_Assessor_CEFR_De_Hieu_Day_Du_v4.pptx`](../artifacts/source/presentations/AI_Assessor_CEFR_De_Hieu_Day_Du_v4.pptx). Nội dung được sắp theo từng slide; file gốc được giữ nguyên.

## Slide 1: ĐỀ CƯƠNG KHÓA LUẬN • BẢN GIẢI THÍCH DỄ HIỂU

- Cho sinh viên đại học Việt Nam ở trình độ A2–B2
- Từ cách giảng viên chấm nói → bằng chứng AI quan sát → cách kiểm định kết quả
- Sinh viên: [Điền họ tên – MSSV]<br>Giảng viên hướng dẫn: [Điền họ tên]

## Slide 2: HIỂU TRONG 30 GIÂY

- Một bài nói đi vào, một hồ sơ năng lực có bằng chứng đi ra
- AI chấm sơ bộ theo rubric do giảng viên thiết lập; giảng viên quyết định cuối cùng.
- Bài nói
- AI quan sát
- Ước lượng
- Giải thích
- Kiểm duyệt
- Audio + nhiệm vụ
- Âm thanh, transcript, lượt nói
- A2 / B1 / B2 + 6 tiêu chí
- Timestamp, lỗi, pause, trích đoạn
- Ca bất định → giảng viên
- Giá trị chính không phải là một con số. Giá trị là phản hồi nhanh, truy vết được và dùng được để chọn bài luyện tiếp theo.

## Slide 3: BỐI CẢNH

- Vấn đề không chỉ là chấm chậm, mà là thiếu phản hồi có thể hành động
- Trong lớp đông, giảng viên khó nghe lại nhiều lần và chỉ ra bằng chứng cho từng sinh viên.
- Tốn công
- Khó nhất quán
- Phản hồi khó dùng
- Chấm Speaking cần nghe audio, đối chiếu rubric và viết nhận xét. Khối lượng tăng gần tuyến tính theo số sinh viên.
- Điểm chịu ảnh hưởng bởi cách hiểu rubric, tải chấm, độ khó prompt và mức đồng thuận giữa người chấm.
- Một mức tổng quát không nói cho người học biết đoạn nào ngập ngừng, ý nào thiếu liên kết hoặc âm nào khó hiểu.
- Câu hỏi thực tế: AI có thể giảm phần việc lặp lại nhưng vẫn giữ chuẩn chấm và quyền quyết định của giảng viên không?

## Slide 4: BÀI TOÁN NGHIÊN CỨU

- Hệ thống phải được kiểm định như một công cụ đo lường, không chỉ như một demo AI
- Một giao diện chạy được chưa chứng minh rằng điểm số có ý nghĩa.
- Làm thế nào ước lượng mức Speaking A2–B2 theo sáu tiêu chí CEFR, kèm bằng chứng và độ tin cậy, trên dữ liệu người Việt được tách theo người nói?
- 1. Đúng construct?
- 2. Đồng thuận với người?
- 3. Biết khi nào không chắc?
- Tín hiệu máy có thực sự phản ánh Range, Accuracy, Fluency, Interaction, Coherence và Phonology?
- AI gần giảng viên đến đâu, và trần đồng thuận giữa hai giảng viên là bao nhiêu?
- Confidence có phát hiện được audio lỗi, ASR sai và bài ở ranh giới hai band không?

## Slide 5: PHẠM VI

- Khóa phạm vi để kết quả có thể bảo vệ trong 10 tuần
- Tên đề tài chốt: Xây dựng hệ thống AI hỗ trợ đánh giá năng lực nói tiếng Anh theo CEFR cho sinh viên đại học Việt Nam ở trình độ A2-B2.
- Trong phạm vi
- Ngoài phạm vi
- • Sinh viên Việt Nam từ 18 tuổi<br>• Ba mức A2, B1, B2<br>• Formative / low-stakes<br>• Audio + transcript + interaction<br>• Điểm sơ bộ, evidence, confidence<br>• Hàng đợi giảng viên duyệt
- • Cấp chứng chỉ CEFR chính thức<br>• A1, C1, C2<br>• Thi high-stakes hoặc chống gian lận<br>• Chatbot hội thoại tự do<br>• Suy luận cảm xúc, giới tính, tính cách<br>• Thay thế hoàn toàn giảng viên
- Cách gọi an toàn: hệ thống AI hỗ trợ đánh giá theo CEFR trong bối cảnh luyện tập.

## Slide 6: ĐỊNH VỊ ĐỀ TÀI

- Đề tài nằm đúng ô Speaking × Assess × AI Assessor của khung ALDM-L
- D1–D8 giúp nói rõ đối tượng, năng lực, dữ liệu đầu ra và cách kết quả quay lại việc học.
- D1 • Learner
- D2 • Competency
- D3 • Stage
- D4 • Activity
- SV đại học Việt Nam, 18+, A2–B2
- Speaking, 6 tiêu chí CEFR
- Assess chính; Diagnose/Adapt phụ
- Task A kể; B quan điểm; C hội thoại
- D5 • AI role
- D6 • Human role
- D7 • Learning data
- D8 • Adaptation
- Assessor chính; Feedbacker phụ
- GV sở hữu rubric và quyết định cuối
- speaking_profile + evidence + confidence
- Gợi ý task tiếp; xuất profile cho module khác
- AI Level 2: AI là đối tác hỗ trợ đánh giá và phản hồi; chưa tự điều phối lộ trình dài hạn.

## Slide 7: HUMAN–AI COLLABORATION

- AI làm phần lặp lại; giảng viên giữ chuẩn và quyết định sư phạm
- Ba vai trò phải được phân định ngay từ thiết kế.
- AI
- Giảng viên
- Sinh viên
- • Kiểm tra audio<br>• Chuyển lời nói thành text<br>• Trích đặc trưng<br>• Ước lượng 6 tiêu chí<br>• Gắn evidence và confidence<br>• Đẩy ca rủi ro vào review
- • Thiết lập và sở hữu rubric<br>• Chọn anchor và hiệu chuẩn rater<br>• Chấm dữ liệu gold<br>• Duyệt ca low-confidence<br>• Phân xử bất đồng<br>• Quyết định cuối cùng
- • Thực hiện Task A/B/C<br>• Đồng ý tham gia và thu hồi consent<br>• Xem evidence<br>• Tự đối chiếu bản ghi<br>• Thực hiện nhiệm vụ luyện tiếp

## Slide 8: NỀN TẢNG ĐO LƯỜNG

- CEFR mô tả năng lực; CEFR không cung cấp công thức chấm tự động
- Dự án phải nối ba thứ: construct → nhiệm vụ → bằng chứng.
- Construct
- Task
- Evidence
- Score
- Validation
- Ta muốn đo năng lực nào?
- Bài nói nào làm năng lực xuất hiện?
- Con người/máy quan sát được gì?
- Quy tắc nào biến evidence thành mức?
- Kết quả có đáng tin và công bằng?
- Một LLM đọc transcript rồi trả “B1” chưa đủ để tuyên bố chấm theo CEFR.
- Rubric phải do giảng viên thiết lập.
- Nhiệm vụ phải tạo đủ bằng chứng cho tiêu chí.
- Điểm AI phải so với người chấm và có khoảng tin cậy.

## Slide 9: BA MỨC NGHIÊN CỨU

- A2, B1 và B2 khác nhau ở mức độc lập, độ phát triển ý và khả năng kiểm soát
- Các câu dưới đây chỉ là ví dụ minh họa, không phải anchor chính thức.
- A2 • Nói về điều quen thuộc
- B1 • Giải thích và nối ý
- B2 • Phát triển lập luận
- “I like my city because it is quiet. There are many parks.”<br>Câu ngắn, từ quen thuộc, ý đơn giản nhưng người nghe vẫn theo được.
- “I prefer living here because public transport is convenient, although it can be crowded.”<br>Có lý do, đối lập và kết nối rõ hơn.
- “Although the city is expensive, its opportunities often outweigh the disadvantages, especially for young professionals.”<br>Ý được phát triển linh hoạt và chính xác hơn.
- Không được xếp mức chỉ từ một câu. Cần nhiều nhiệm vụ và nhiều tiêu chí.

## Slide 10: SÁU TIÊU CHÍ

- CEFR nhìn bài nói như một hồ sơ, không phải một điểm duy nhất
- Mỗi tiêu chí trả lời một câu hỏi khác nhau về năng lực giao tiếp.
- Range
- Accuracy
- Fluency
- Có đủ từ và cấu trúc để diễn đạt?
- Kiểm soát ngữ pháp đến đâu?
- Duy trì lời nói và ngắt nghỉ ra sao?
- Coherence
- Interaction
- Phonology
- Ý có phát triển và liên kết không?
- Có phối hợp được trong hội thoại?
- Thông điệp có dễ hiểu qua âm và ngữ điệu?
- Overall chỉ được tạo sau khi xem profile 6 tiêu chí và bằng chứng của từng nhiệm vụ.

## Slide 11: RANGE • PHẠM VI NGÔN NGỮ

- Không hỏi “nói bao nhiêu từ”, mà hỏi “có đủ công cụ để diễn đạt ý không”
- AI quan sát độ đa dạng từ, cấu trúc và khả năng diễn đạt lại.
- Con người nghe gì?
- Máy đo gì?
- Máy dễ hiểu sai gì?
- • Từ vựng có đủ cho chủ đề<br>• Có dùng câu ghép/mệnh đề phù hợp<br>• Có paraphrase khi thiếu từ<br>• Cụm từ có tự nhiên và đa dạng
- • Lexical profile theo tần suất/mức độ<br>• MTLD hoặc HD-D cho lexical diversity<br>• Độ đa dạng cấu trúc câu<br>• N-gram/cụm từ và semantic coverage
- • Bài dài bị thưởng điểm<br>• Tên riêng làm “từ hiếm” tăng giả<br>• Transcript sai tạo từ lạ<br>• Dùng từ khó nhưng sai nghĩa
- Nguyên tắc: chuẩn hóa theo độ dài và kiểm tra từ trong ngữ cảnh; không dùng word count làm điểm Range.

## Slide 12: ACCURACY • ĐỘ CHÍNH XÁC

- Lỗi cần được tính theo mức kiểm soát, không phải đếm máy móc
- Tự sửa là bằng chứng tích cực; lỗi ASR không được biến thành lỗi của sinh viên.
- Máy phải ghi nhận hai sự kiện
- “Yesterday I go… I mean, I went to school.”
- Sai thì ở lần nói đầu
- Tự phát hiện và sửa đúng
- Đơn vị phân tích
- Loại bằng chứng
- Guardrail bắt buộc
- AS-unit và clause phù hợp hơn “câu viết” vì lời nói thường dang dở, có ngập ngừng và tự sửa.
- Agreement, tense, preposition, word form, clause accuracy, error-free unit và repair.
- Token ASR confidence thấp không được dùng để kết luận lỗi; cần audit bằng transcript chép tay.

## Slide 13: FLUENCY • ĐỘ TRÔI CHẢY

- Nói nhanh không đồng nghĩa với nói trôi chảy
- Fluency là khả năng duy trì lời nói với nhịp và khoảng dừng phù hợp nhiệm vụ.
- A • Nhanh nhưng vỡ vụn
- Tín hiệu AI quan sát
- • Articulation rate<br>• Pause count / duration / ratio<br>• Mean run length<br>• Repetition và restart<br>• Filled pause: um, uh, er
- Nhiều pause giữa ý, lặp và restart
- B • Chậm hơn nhưng ổn định
- Pause ở ranh giới ý; mean run length dài hơn
- Phải chuẩn hóa theo loại nhiệm vụ: kể chuyện, nêu quan điểm và hội thoại có nhịp tự nhiên khác nhau.

## Slide 14: COHERENCE • TÍNH MẠCH LẠC

- Một bài đúng ngữ pháp vẫn có thể khó theo dõi nếu ý rời rạc
- Coherence nhìn cách ý được mở, phát triển, minh họa và kết lại.
- Nêu ý
- Lý do
- Ví dụ
- Giới hạn
- Kết
- I prefer online learning
- because it saves travel time
- for example, recorded lectures
- however, interaction is weaker
- so a blended model is better
- Máy quan sát
- Rủi ro
- Discourse markers, semantic continuity, idea progression, topic relevance và cấu trúc lập luận.
- Transcript mất từ nối hoặc nhận sai từ khóa có thể làm mô hình kết luận bài lạc ý.
- LLM có thể hỗ trợ đánh giá mạch lạc, nhưng phải bị ràng buộc bởi rubric và evidence đã lưu.

## Slide 15: INTERACTION • KHẢ NĂNG TƯƠNG TÁC

- Không có hội thoại thì không có đủ bằng chứng để chấm Interaction
- Tiêu chí này chỉ được tính ở Task C có nhiều lượt nói được kiểm soát.
- AI: Could you explain why you prefer studying at home?
- Sinh viên: I can focus better there. Do you mean compared with the library?
- Máy có thể đo
- AI: Yes. What makes the library less suitable for you?
- Latency phía client, hoàn thành lượt, relevance, clarification, repair và khả năng phản hồi follow-up.
- Nếu chỉ làm độc thoại: ghi “chưa đủ bằng chứng”, không tự cho 0 điểm.

## Slide 16: PHONOLOGY • PHÁT ÂM VÀ NGỮ ĐIỆU

- Mục tiêu là dễ hiểu, không phải xóa giọng Việt
- Đây là tiêu chí có construct coverage yếu nhất trong phiên bản 10 tuần.
- 1. Âm cục bộ
- 2. Prosody
- 3. Intelligibility
- Forced alignment + GOP ước lượng âm nào khác xa mẫu; ví dụ phụ âm cuối hoặc nguyên âm dễ nhầm.
- F0 range, trọng âm, nhịp, độ dài và đường ngữ điệu giúp mô tả phần vượt ra ngoài từng âm riêng lẻ.
- Điều CEFR quan tâm nhất: người nghe có hiểu không và cần cố gắng bao nhiêu để hiểu.
- GOP thấp ≠ phát âm kém. Có thể do accent, thiết bị, alignment hoặc dữ liệu huấn luyện không đại diện người Việt.
- Guardrail: không phạt accent nếu thông điệp vẫn dễ hiểu; ca không chắc phải chuyển giảng viên.

## Slide 17: NGUYÊN TẮC QUAN TRỌNG

- Feature là bằng chứng gián tiếp; feature không phải chính tiêu chí CEFR
- Mỗi chỉ số cần trả lời được: nó hỗ trợ kết luận nào, và khi nào nó không còn đáng tin?
- Máy đo trực tiếp
- Construct cần kết luận
- Guardrails
- Tốc độ nói<br>Số và độ dài pause<br>Độ đa dạng từ<br>ASR confidence<br>F0 / rhythm<br>Turn latency
- Fluency<br>Range<br>Accuracy<br>Coherence<br>Interaction<br>Phonology
- Task phù hợp<br>ASR risk<br>Audio QC<br>Accent audit<br>Confidence<br>Teacher review
- diễn giải
- Ví dụ: articulation rate cao chỉ cho biết nói nhanh; không đủ để kết luận Fluency cao.

## Slide 18: TASK BLUEPRINT

- Ba nhiệm vụ tạo ba loại bằng chứng bổ sung cho nhau
- Không có một task duy nhất đo tốt cả sáu tiêu chí.
- Task A • Kể / mô tả
- Task B • Nêu quan điểm
- Task C • Hội thoại
- 90–120 giây<br>Chủ đề quen thuộc<br>2 prompt tương đương<br>Mạnh về: Range, Fluency, Coherence, Phonology<br>Không chấm Interaction
- Khoảng 120 giây<br>30 giây chuẩn bị<br>3 bullet gợi ý cho A2<br>Mạnh về: Range, Accuracy, Coherence, relevance<br>Kiểm soát kiến thức nền
- 3 lượt nói<br>Prompt tree cố định<br>Audio câu hỏi ghi sẵn<br>Mạnh về: Interaction, Fluency, clarification<br>Pilot trên 25–30 người

## Slide 19: TRẢI NGHIỆM SỬ DỤNG

- Sản phẩm là một vòng lặp học tập ngắn, không phải màn hình trả điểm
- Elicit → Assess → Explain → Review → Practice.
- 1. Elicit
- 2. Assess
- 3. Explain
- 4. Review
- 5. Practice
- Sinh viên làm Task A/B/C
- AI tạo điểm sơ bộ
- Hiện bằng chứng dễ hiểu
- Giảng viên duyệt ca khó
- Một nhiệm vụ luyện tiếp
- Ví dụ gợi ý: kể lại cùng chủ đề trong 90 giây, dùng ít nhất ba từ nối và giữ mỗi ý trong một cụm nói hoàn chỉnh.
- Chỉ sinh gợi ý khi có đủ evidence và confidence đạt ngưỡng.

## Slide 20: KIẾN TRÚC TỔNG THỂ

- Pipeline tách dữ liệu gốc, bằng chứng, mô hình chấm và lớp phản hồi
- Tách lớp giúp chạy lại thí nghiệm và truy vết khi điểm bị sửa.
- Thu bài
- Quality gate
- Evidence
- Scoring
- Calibration
- Report
- Recorder + metadata
- Noise, clipping, silence
- Audio + text + turns
- Models + late fusion
- Confidence + thresholds
- Profile + teacher queue
- Nguyên tắc version hóa
- Nguyên tắc truy vết
- audio_id, transcript_version, feature_version, rubric_version, model_version và calibration_version.
- Mỗi nhận xét phải trỏ về evidence_id, timestamp hoặc đoạn transcript cụ thể.

## Slide 21: TRÍCH XUẤT ĐẶC TRƯNG

- Ba nhánh bằng chứng được tạo độc lập trước khi kết hợp
- Khi một nguồn sai, nhóm có thể biết mô hình đang dựa vào đâu.
- Audio
- Transcript
- Interaction
- Duration, voiced ratio, pause, articulation rate, F0, rhythm, GOP và chất lượng thu âm.<br>Dùng chủ yếu cho Fluency và Phonology.
- Từ vựng, cấu trúc, lỗi, từ nối, semantic relevance và self-repair.<br>Dùng chủ yếu cho Range, Accuracy và Coherence.
- Turn count, latency client-side, clarification, follow-up, relevance và completion.<br>Chỉ dùng khi Task C cung cấp đủ lượt nói.
- Quality là nhánh kiểm soát: noise, clipping và ASR risk quyết định reject/review; không được dùng trực tiếp làm điểm năng lực.

## Slide 22: RỦI RO ASR

- Một từ nhận sai có thể tạo thành nhiều lỗi giả ở các bước phía sau
- ASR là cảm biến không hoàn hảo, không phải ground truth.
- Người học nói đúng
- ASR nhận sai
- NLP kết luận sai
- Điểm giảm giả
- “I went to school”
- “I want school”
- thiếu giới từ / sai nghĩa
- Accuracy + Coherence
- Guardrails
- Audit bắt buộc
- • Lưu word/token confidence<br>• So WER trên transcript chép tay<br>• Giảm trọng số vùng không chắc<br>• Log accent, thiết bị và noise<br>• Chuyển review khi vượt ngưỡng
- Chọn 15–20 bài đa dạng band, accent và thiết bị để chép tay hoàn toàn; so lỗi model trên ASR và transcript chuẩn.

## Slide 23: MÔ HÌNH CHẤM

- Late fusion giữ được nguồn bằng chứng và dễ kiểm tra hơn một mô hình hộp đen duy nhất
- Mỗi nhánh tạo điểm/xác suất; bước cuối mới kết hợp và hiệu chỉnh confidence.
- Audio model
- Fluency / Phonology probabilities
- Late fusion
- Calibration
- Text model
- Confidence phản ánh đúng xác suất trả lời đúng; đặt ngưỡng teacher review
- Kết hợp xác suất + quality flags + missing criteria
- Range / Accuracy / Coherence probabilities
- Interaction model
- Interaction probability khi có Task C
- Baseline bắt buộc: audio-only, transcript-only và frozen-rubric LLM local.

## Slide 24: ĐẦU RA

- Báo cáo phải cho biết điểm, lý do và mức độ đáng tin
- Kết quả được chuẩn hóa thành speaking_profile để dùng cho phản hồi và module học tập phía sau.
- Hồ sơ hiển thị cho sinh viên
- speaking_profile.json
- {<br>"overall": {"band":"B1", "confidence":0.67},<br>"criteria": {<br>"range":"B1", "fluency":"A2+",<br>"interaction":null<br>},<br>"evidence_refs":["e17","e24"],<br>"weakest_criteria":["fluency"],<br>"next_task_hint":"retell_with_connectors",<br>"teacher_verified":false<br>}
- Overall: B1 • confidence: trung bình
- Tiêu chí
- Mức
- Bằng chứng
- Range
- B1
- Từ đủ chủ đề; còn lặp
- Fluency
- A2+
- 2 pause dài tại 00:38, 01:04
- Interaction
- —
- Chưa làm Task C

## Slide 25: KHẢO SÁT SẢN PHẨM VÀ NGHIÊN CỨU

- Mỗi nguồn giải quyết tốt một phần, nhưng chưa khớp toàn bộ bài toán người Việt A2–B2
- Dùng các hệ thống này làm baseline, tham khảo kiến trúc hoặc học cách thiết kế trải nghiệm.
- SpeechRater
- Speak & Improve
- EvalYaks
- GOPT
- Hệ thống chấm nói tự động kinh điển; mạnh về construct, feature và validation.<br>Thiếu: mã nguồn/định hướng riêng cho người Việt.
- UX luyện nói và dữ liệu L2 lớn.<br>Thiếu: kiểm soát trực tiếp mô hình và xác nhận subset người Việt phù hợp.
- Mã nguồn/prompt cho đánh giá transcript theo B2.<br>Thiếu: audio, phát âm, fluency và các mức A2/B1.
- Baseline chấm phát âm nhiều mức.<br>Thiếu: domain shift Mandarin L1 + scripted khi áp lên người Việt nói tự nhiên.
- Khoảng trống nằm ở sự kết hợp: người Việt + audio tự nhiên + 6 tiêu chí + nhiều rater + confidence + teacher review.

## Slide 26: KHOẢNG TRỐNG NGHIÊN CỨU

- Điểm mới không nằm ở việc gọi một API, mà ở thiết kế đo lường và kiểm định
- Đề tài đóng góp bằng cách làm rõ mối nối giữa rubric, evidence, model và con người.
- 01
- Rubric CEFR được vận hành hóa thành bằng chứng máy đo được
- 02
- Dữ liệu người Việt có hai người chấm và phân xử
- 03
- So sánh audio-only, transcript-only và multimodal
- 04
- Calibration, teacher queue và error audit theo accent/thiết bị
- Tuyên bố khoa học phù hợp: PoC được kiểm định trong bối cảnh formative A2–B2; không tuyên bố tổng quát cho mọi kỳ thi và mọi accent.

## Slide 27: DỮ LIỆU CÔNG KHAI

- Dữ liệu có sẵn giúp dựng pipeline, nhưng không thay thế tập kiểm định người Việt
- Mỗi corpus chỉ nên dùng đúng vai trò mà nhãn và đối tượng của nó cho phép.
- Nguồn
- Có người Việt?
- Nhãn chính
- Vai trò phù hợp
- L2-ARCTIC
- 4/24 người
- Transcript + lỗi phát âm; không CEFR
- ASR/accent/pronunciation sanity check
- Speak & Improve
- Nhiều L1; cần kiểm tra subset
- Holistic score; transcript/error subset
- Benchmark hoặc pretraining theo license
- SpeechOcean762
- Chủ yếu Mandarin L1
- Điểm phone/word/utterance
- Pronunciation baseline; không đại diện VN
- EvalYaks
- Dữ liệu synthetic
- B2 transcript rubric
- Baseline LLM cho nhánh text
- Không có corpus công khai nào ở đây đồng thời đáp ứng: audio tự nhiên + nhiều người Việt + 6 tiêu chí CEFR + nhiều rater.

## Slide 28: DỮ LIỆU PHẢI TỰ THU

- Tập người Việt nhỏ nhưng được thiết kế đúng còn giá trị hơn dữ liệu lớn nhưng sai nhãn
- Mục tiêu 70–90 speaker; sàn khả thi 60; mọi split phải theo người nói.
- Quy mô
- Metadata tối thiểu
- Kiểm soát phân bố
- 70–90 sinh viên<br>140–180 response Task A/B<br>25–30 người làm thêm Task C<br>15–20 bài chép tay hoàn toàn
- speaker_id giả<br>trình độ sàng lọc<br>prompt/version<br>thiết bị và môi trường<br>thời lượng/noise<br>consent version
- Theo dõi band, giới tính tự khai nếu được consent, prompt, thiết bị và noise. Không ép thu thuộc tính nhạy cảm không cần thiết.
- Speaker-level split: mọi bài của cùng một người chỉ nằm trong một nhóm dữ liệu, tránh học thuộc giọng.

## Slide 29: NHÃN VÀ GOLD STANDARD

- Phải đo đồng thuận giữa người chấm trước khi đánh giá AI
- Nếu hai giảng viên chưa thống nhất, không thể đòi AI khớp một nhãn tuyệt đối.
- Rubric v1
- Anchor
- Calibration
- Double rating
- Adjudication
- GV thiết lập mô tả A2/B1/B2
- Bài mẫu cho từng band/tiêu chí
- Chấm thử và thảo luận bất đồng
- Hai rater chấm độc lập
- Người thứ ba phân xử
- Báo cáo human–human
- Nhãn gold
- Agreement, QWK + CI, confusion matrix và loại bất đồng theo tiêu chí/task.
- Không dùng chính một rater để vừa làm gold vừa đại diện agreement. Adjudicator tạo nhãn cuối cho ca bất đồng.

## Slide 30: THIẾT KẾ THÍ NGHIỆM

- Đánh giá trên người nói chưa từng xuất hiện trong huấn luyện
- Repeated GroupKFold là phân tích chính; confirmation set chỉ dùng một lần ở cuối.
- Split đúng
- So sánh công bằng
- Phân tích sai
- Group theo speaker_id. Mọi response của một người đi cùng fold. Preprocessing, feature selection và calibration đều fit trong training fold.
- B0 majority/ordinal baseline<br>B1 audio-only<br>B2 transcript-only<br>B3 frozen-rubric LLM local<br>M1 late fusion
- Theo band, task, prompt, noise, thiết bị, WER và accent proxy. Tách lỗi gross A2↔B2 khỏi lỗi liền kề.
- So hai mô hình bằng paired cluster bootstrap theo speaker; không so hai khoảng tin cậy độc lập.

## Slide 31: TIÊU CHÍ ĐÁNH GIÁ MÔ HÌNH

- Không có một metric duy nhất đủ trả lời hệ thống có dùng được hay không
- Cần nhìn agreement, lỗi nghiêm trọng, calibration, reliability và nguyên nhân sai.
- QWK + CI
- Macro-F1
- Gross Error Rate
- Đồng thuận trên mức có thứ tự; A2→B2 bị phạt nặng hơn A2→B1.
- Không để band đông che khuất band ít.
- Tỷ lệ nhảy hai band, ví dụ A2↔B2.
- Calibration
- Reliability
- Error audit
- Confidence 70% có đúng khoảng 70% trường hợp không?
- Cùng người, task tương đương hoặc chạy lại có ổn định không?
- Lỗi tập trung ở accent, WER, noise, prompt hay tiêu chí nào?
- Mục tiêu hợp lý: AI tiến gần trần human–human và biết từ chối ca không chắc; không hứa “chính xác tuyệt đối”.

## Slide 32: TECH STACK

- Ưu tiên thành phần chạy local, mô hình tiền huấn luyện và công cụ dễ kiểm tra
- Mục tiêu 10 tuần là một pipeline đo lường hoàn chỉnh, không phải huấn luyện foundation model.
- Lớp
- Lựa chọn
- Lý do
- Web / API
- React hoặc Next.js + FastAPI
- Tách UI thu âm và pipeline Python; dễ demo và test API
- Lưu trữ
- PostgreSQL + object storage local
- Metadata có schema; audio tách khỏi bảng điểm
- ASR
- faster-whisper local
- Baseline thực dụng, có timestamp; không gửi audio ra cloud
- Audio
- librosa / Praat-Parselmouth
- Pause, rate, F0, rhythm và quality features
- Text
- spaCy/Stanza + sentence-transformers
- Cấu trúc, lỗi, coherence và relevance
- Model
- scikit-learn / PyTorch + calibration
- Baseline rõ, late fusion và thí nghiệm lặp lại

## Slide 33: PHÁP LÝ VÀ ĐẠO ĐỨC

- Giọng nói là dữ liệu cá nhân; thiết kế an toàn phải có ngay từ lúc thu
- Mục tiêu là tối thiểu hóa dữ liệu, giới hạn mục đích và giữ người thật trong vòng quyết định.
- Trước khi thu
- Trong khi xử lý
- Khi báo cáo
- Consent rõ mục đích<br>Người tham gia 18+<br>Quyền từ chối/rút lui<br>Mô tả thời gian lưu<br>Không gắn tham gia với điểm học phần
- Pseudonymization<br>Mã hóa khi lưu/truyền<br>Phân quyền truy cập<br>Local-first<br>Log truy cập và phiên bản
- Không suy luận cảm xúc/giới tính<br>Không xếp hạng công khai<br>Nêu uncertainty<br>Cho phép giảng viên sửa<br>Xóa dữ liệu theo chính sách
- Fairness không phải “mọi nhóm cùng điểm”, mà là lỗi mô hình không tăng vô lý do accent, noise hoặc thiết bị.

## Slide 34: KẾ HOẠCH 10 TUẦN • PHẦN 1

- Tuần 1–5: chốt construct trước, thu dữ liệu sau
- Mỗi tuần có một cổng nghiệm thu; nếu trễ, cắt tính năng chứ không bỏ kiểm định.
- Tuần
- Trọng tâm
- Việc phải hoàn thành
- Cổng
- W1
- Scope + CEFR + pháp lý
- Chốt tên/RQ/A2–B2; xác nhận rater; consent + data plan
- G1: GVHD duyệt phạm vi
- W2
- Rubric + task
- Rubric 6 tiêu chí; Task A/B/C; prompt bank; anchor
- G2: rater giải thích được điểm
- W3
- Vertical slice
- Recorder/upload; QC; ASR; feature cơ bản; report JSON
- G3: chạy end-to-end 1 bài
- W4
- Pilot + calibration
- Thu 8–12 người; double-rate; sửa prompt/rubric; khóa v1
- G4: completion ≥85%; agreement dùng được
- W5
- Main collection 1
- Thu 20–30 người; QC ngay; rater chấm cuốn chiếu
- G5: metadata đầy đủ ≥90%

## Slide 35: KẾ HOẠCH 10 TUẦN • PHẦN 2

- Tuần 6–10: khóa dữ liệu, kiểm định, hoàn thiện sản phẩm và luận văn
- Không tinh chỉnh vô hạn trên confirmation set.
- Tuần
- Trọng tâm
- Việc phải hoàn thành
- Cổng
- W6
- Main collection 2
- Đạt sàn 60, mục tiêu 70–90; chốt Task C subset; adjudicate
- G6: đủ dữ liệu + nhãn
- W7
- Baseline
- Audio-only, transcript-only, LLM local; GroupKFold
- G7: bảng baseline có CI
- W8
- Fusion + calibration
- Late fusion; threshold teacher review; ablation
- G8: model freeze
- W9
- Evaluation + UX
- Error/fairness audit; teacher queue; usability test
- G9: acceptance test
- W10
- Đóng gói
- Confirmation run; viết kết quả; slide/demo; archive artifact
- G10: tái lập được
- W10 dùng để xác nhận và đóng gói, không dùng để bắt đầu viết luận văn.

## Slide 36: TÍNH KHẢ THI VÀ DỰ PHÒNG

- Đề tài khả thi có điều kiện; rater và dữ liệu là đường găng
- Rủi ro được xử lý bằng cổng quyết định, không chờ đến cuối mới phát hiện.
- Rủi ro
- Dấu hiệu sớm
- Phương án dự phòng
- Không đủ rater
- W1 chưa có cam kết thời gian
- Giảm response/người; giữ double-rating; chuyển kết luận thành pilot
- Không đủ 60 speaker
- W5 dưới 25 người
- Tăng kênh tuyển; khóa A/B; giảm Task C; báo CI rộng
- ASR sai giọng Việt
- WER/manual subset cao
- Confidence masking; transcript audit; teacher review; phân tích riêng
- Phonology không ổn
- QWK thấp và bias accent
- Chỉ báo evidence; giảm trọng số; không dùng để quyết overall một mình
- Trễ tiến độ
- G3/G4 không đạt
- Cắt chatbot, LMS, dashboard nâng cao; giữ data + validation

## Slide 37: TIÊU CHÍ NGHIỆM THU

- Nghiệm thu theo năm lớp: chạy được, có dữ liệu, đo đúng, biết giới hạn và tái lập được
- Không dùng một ngưỡng accuracy duy nhất để quyết định thành công.
- 1 • Chức năng
- Thu âm → ASR → evidence → score → report → teacher review chạy end-to-end.
- 2 • Dữ liệu
- Đạt sàn speaker, metadata đủ, consent hợp lệ, split theo người nói.
- 3 • Đo lường
- Có human–human trước AI–human; QWK/CI, GER, macro-F1 và error analysis.
- 4 • Tin cậy
- Có calibration, confidence threshold, invalid/ASR-risk flags và audit accent/thiết bị.
- 5 • Tái lập
- Có version, manifest, seed, environment, rubric và script chạy lại kết quả.

## Slide 38: ĐÓNG GÓP KHOA HỌC VÀ KỸ THUẬT

- Đóng góp chính là một quy trình đánh giá có thể kiểm tra, không phải một mô hình “thần kỳ”
- Mỗi đóng góp tạo ra một artifact có thể bàn giao.
- 01
- Bản đồ rubric → task → evidence → feature cho 6 tiêu chí
- 02
- Tập dữ liệu pilot người Việt có double-rating và adjudication
- 03
- Baseline và late-fusion protocol có speaker-level evaluation
- 04
- Calibration, teacher-review policy và error/fairness audit
- 05
- speaking_profile schema nối đánh giá với luyện tập thích ứng
- 06
- Bộ tài liệu tái lập: code, version, split manifest, rubric, model card

## Slide 39: CÂU HỎI HỘI ĐỒNG THƯỜNG GẶP

- Trả lời bằng phạm vi, bằng chứng và giới hạn, không trả lời bằng khẩu hiệu AI
- Bốn câu dưới đây bao phủ phần dễ bị hỏi nhất.
- Câu hỏi
- Cách trả lời ngắn
- Tại sao gọi là theo CEFR?
- Vì rubric/task/evidence bám 6 tiêu chí CEFR và điểm được kiểm định với rater; không phải vì LLM tự ghi nhãn CEFR.
- AI có thay giảng viên không?
- Không. AI chấm sơ bộ; GV sở hữu rubric, duyệt ca bất định và quyết định cuối cùng.
- Dữ liệu người Việt có đủ không?
- Đủ cho PoC có CI và error analysis nếu đạt sàn; không đủ để tuyên bố tổng quát cho mọi người Việt.
- Phát âm chấm thế nào?
- Kết hợp GOP, prosody và intelligibility; không phạt accent; Phonology được công bố là tiêu chí rủi ro nhất.
- Vì sao không chỉ dùng LLM?
- Transcript không chứa đầy đủ pause, rhythm, intelligibility và interaction; ASR error còn có thể tạo lỗi ngữ pháp giả.

## Slide 40: NGUỒN NỀN TẢNG

- Ưu tiên tài liệu chính thức, bài báo gốc, kho dữ liệu và mã nguồn của tác giả
- Các URL đầy đủ được đặt trong speaker notes của từng slide.
- Chuẩn và kiểm định
- Mô hình, mã nguồn và dữ liệu
- • CEFR Companion Volume 2020<br>• Council of Europe: Relating Examinations to CEFR<br>• Manual for Language Test Development, 2026<br>• Cambridge Speaking Assessment Criteria<br>• ETS SpeechRater<br>• ETS Evidence-Centered Design
- • Multimodal Speaking Assessment, RANLP 2023<br>• Transcript-based grading, ACL 2020<br>• GOPT official repository<br>• L2-ARCTIC<br>• Speak & Improve Corpus 2025<br>• SpeechOcean762 và EvalYaks
- Nguyên tắc sử dụng nguồn: corpus khác miền chỉ dùng làm baseline; dữ liệu người Việt tự thu mới dùng cho kết luận chính.

## Slide 41: KẾT LUẬN CHỐT

- Đề tài khả thi khi xem AI là một công cụ đo lường có kiểm soát
- Thành công không được định nghĩa bởi việc AI luôn đưa ra điểm. Thành công là AI đưa ra điểm có bằng chứng khi đủ tin cậy, và biết chuyển người thật xem lại khi không đủ bằng chứng.
- Chốt triển khai
- A2–B2 • low-stakes • 6 tiêu chí • 2 rater + 1 adjudicator • speaker-level validation • human-in-the-loop
- AI chấm sơ bộ. Giảng viên giữ chuẩn và quyết định cuối cùng.
