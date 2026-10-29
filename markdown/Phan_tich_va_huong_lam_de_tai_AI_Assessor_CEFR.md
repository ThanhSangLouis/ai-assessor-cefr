# Xây dựng hệ thống AI hỗ trợ đánh giá năng lực nói tiếng Anh theo CEFR cho sinh viên đại học Việt Nam ở trình độ A2-B2

> Bản Markdown được chuyển từ [`Phan_tich_va_huong_lam_de_tai_AI_Assessor_CEFR.docx`](../artifacts/source/documents/Phan_tich_va_huong_lam_de_tai_AI_Assessor_CEFR.docx). File gốc được giữ nguyên.

BÁO CÁO PHÂN TÍCH & ĐỀ XUẤT KHÓA LUẬN

Phương án kết hợp đánh giá, hội thoại tương tác và phản hồi cá nhân hóa

| Trục chính | Speaking × Assess × AI Assessor |
| --- | --- |
| Kết hợp đề xuất | Nhóm 1 + Nhóm 2; Nhóm 4 ở mức mở rộng |
| Đối tượng | Sinh viên Việt Nam học tiếng Anh, phạm vi A2-B2 |
| Mục đích | Đánh giá hỗ trợ học tập, không phải chứng chỉ CEFR chính thức |

Ngày cập nhật: 20/08/2026

Căn cứ: Ma trận ALDM-L trong tài liệu định hướng đề tài năm 2026

## Kết luận điều hành

| Khuyến nghị chốt đề tài: Kết hợp Nhóm 1 (Diagnostic & Assessment) với một phần Nhóm 2 (Interactive & Practical Skills Training). AI Assessor là lõi nghiên cứu; AI Conversation Partner tạo tình huống nói và AI Feedbacker giải thích kết quả. Chỉ đưa Nhóm 4 vào dưới dạng gợi ý bài luyện tiếp theo, không xây cả hệ thống điều phối lộ trình. |
| --- |

Tên đề tài chốt: “Xây dựng hệ thống AI hỗ trợ đánh giá năng lực nói tiếng Anh theo CEFR cho sinh viên đại học Việt Nam ở trình độ A2-B2”.

Sản phẩm nên được định vị là công cụ đánh giá hình thành (formative, low-stakes): cung cấp mức CEFR ước lượng, điểm theo tiêu chí, bằng chứng và hướng cải thiện. Không tuyên bố cấp chứng chỉ CEFR, không thay thế giám khảo và không dùng một điểm AI duy nhất để ra quyết định học vụ.

## 1. Có thể kết hợp mấy nhóm đề tài?

Tài liệu định hướng chia đề tài thành bốn nhóm. Đề tài gốc thuộc Nhóm 1 với cấu hình Speaking × Assess × AI Assessor. Vì năng lực Interaction chỉ có thể quan sát tốt khi người học thực sự đối thoại, việc bổ sung một phiên hội thoại có cấu trúc từ Nhóm 2 là hợp lý về mặt sư phạm và cũng làm rõ tiêu chí Interaction trong CEFR [1].

| Phương án | Phạm vi | Giá trị | Rủi ro | Kết luận |
| --- | --- | --- | --- | --- |
| Chỉ Nhóm 1 | Ghi âm bài nói, chấm CEFR, xuất báo cáo | Dễ hoàn thành; tập trung đánh giá | Không đo tốt tương tác | Phương án tối thiểu |
| Nhóm 1 + 2 | Đánh giá + hội thoại 3-5 lượt + phản hồi | Đo được production và interaction | Tăng công sức thu thập dữ liệu | Khuyến nghị |
| Nhóm 1 + 2 + 4 | Thêm hồ sơ năng lực và lộ trình cá nhân hóa | Tạo vòng lặp học tập đầy đủ | Dễ vượt phạm vi khóa luận | Chỉ làm extension |
| Nhóm 1 + 3 | Đánh giá qua phỏng vấn việc làm | Bài toán ứng dụng rõ | Đề tài chuyển sang employability | Chỉ chọn nếu đổi ngữ cảnh |

| Nguyên tắc phạm vi: Kết hợp nhóm theo một chu trình duy nhất: Elicit speech → Assess → Explain → Recommend next practice. Không biến khóa luận thành một nền tảng LMS đầy đủ. |
| --- |

## 2. Định vị trong ma trận ALDM-L

| Thành phần | Vai trò trong đề tài | Mức ưu tiên |
| --- | --- | --- |
| Speaking × Assess × AI Assessor | Ước lượng mức A2/B1/B2 và chấm sáu tiêu chí CEFR | Lõi bắt buộc |
| Speaking × Interact × AI Conversation Partner | Tạo hội thoại bán cấu trúc để quan sát lượt lời và khả năng phản hồi | Bắt buộc ở bản kết hợp |
| Speaking × Reflect × AI Feedbacker | Phản hồi có bằng chứng, chỉ ra điểm mạnh và hành động cải thiện | Bắt buộc |
| Toàn diện × Adapt × AI Personalizer | Đề xuất 1-2 bài luyện tiếp theo dựa trên tiêu chí yếu | Mở rộng |
| English Employability × Perform × AI Simulator | Mô phỏng phỏng vấn việc làm | Ngoài phạm vi hiện tại |

Phân công Human-AI phải rõ: giảng viên thiết kế nhiệm vụ, chuẩn hóa rubric và xử lý trường hợp bất định; AI phân tích dữ liệu và tạo phản hồi; sinh viên thực hiện nhiệm vụ và phản tư. Đây là cách giữ đúng tinh thần AI hỗ trợ của tài liệu ALDM-L.

## 3. Bài toán nghiên cứu

### 3.1. Vấn đề

Chấm nói thủ công tốn thời gian, khó mở rộng và có biến thiên giữa giám khảo. Tuy nhiên, chấm tự động dễ bị lệch do ASR nhận sai giọng người học, do mô hình chú trọng độ trôi chảy hơn nội dung, hoặc do dữ liệu huấn luyện không đại diện cho sinh viên Việt Nam. Vì vậy, khóa luận không chỉ xây phần mềm mà phải kiểm chứng độ đồng thuận, độ tin cậy và tính công bằng so với giảng viên [5][6].

### 3.2. Mục tiêu tổng quát

Xây dựng và đánh giá một nguyên mẫu AI hỗ trợ chấm Speaking theo CEFR, sử dụng kết hợp tín hiệu âm thanh, bản ghi lời nói và đặc trưng tương tác; đồng thời cung cấp phản hồi có thể giải thích và cơ chế chuyển cho giảng viên khi hệ thống không chắc chắn.

### 3.3. Mục tiêu cụ thể

- Xây dựng rubric vận hành hóa từ sáu đặc trưng định tính của ngôn ngữ nói CEFR: Range, Accuracy, Fluency, Interaction, Coherence và Phonology [1].

- Thiết kế bộ nhiệm vụ nói có khả năng khơi gợi đủ bằng chứng cho các tiêu chí, gồm bài nói độc thoại và hội thoại bán cấu trúc.

- Xây pipeline Audio → ASR → đặc trưng âm học/ngôn ngữ/tương tác → mô hình chấm thứ bậc → phản hồi.

- Tạo bộ dữ liệu sinh viên Việt Nam có đồng thuận tham gia và được ít nhất hai giảng viên chấm độc lập.

- Đánh giá AI-human agreement, sai số theo mức CEFR, độ bền với chất lượng âm thanh và khác biệt giữa các nhóm người học.

- Xây giao diện cho sinh viên và bảng kiểm duyệt cho giảng viên, có confidence và bằng chứng đi kèm.

### 3.4. Câu hỏi nghiên cứu

- RQ1: Điểm CEFR do hệ thống dự đoán đồng thuận với giảng viên ở mức nào?

- RQ2: Mô hình kết hợp âm thanh + transcript + tương tác có tốt hơn các baseline chỉ dùng một nguồn dữ liệu hay không?

- RQ3: Sai số thay đổi thế nào theo mức CEFR, giới tính, thiết bị, độ ồn và đặc điểm giọng nói?

- RQ4: Sinh viên và giảng viên đánh giá thế nào về độ rõ ràng, hữu ích và khả năng hành động của phản hồi?

## 4. Phạm vi nên chốt

| Trong phạm vi | Ngoài phạm vi |
| --- | --- |
| Sinh viên Việt Nam học tiếng Anh; đánh giá A2-B2 | Tuyên bố độ chính xác cho toàn bộ A1-C2 khi chưa đủ dữ liệu |
| Đánh giá hỗ trợ học tập, mức rủi ro thấp | Cấp chứng chỉ hoặc thay thế hoàn toàn giám khảo |
| 2 nhiệm vụ độc thoại + 1 hội thoại ngắn | Thi nói chuẩn hóa quy mô lớn, chống gian lận toàn diện |
| Sáu tiêu chí CEFR và mức tổng thể | Đánh giá tính cách, trí thông minh hoặc khả năng nghề nghiệp |
| Phản hồi có căn cứ và gợi ý luyện tập | Sinh nội dung dài thay người học hoặc tự động quyết định học vụ |

Có thể hiển thị A1-C2 trong giao diện tham khảo, nhưng báo cáo thực nghiệm chỉ nên khẳng định cho dải trình độ đã có đủ dữ liệu. Với bối cảnh sinh viên và nguồn lực khóa luận, A2-B2 là lựa chọn thực tế hơn.

## 5. Khung đánh giá CEFR

CEFR Companion Volume 2020 cung cấp bảng Qualitative Features of Spoken Language với sáu cột Range, Accuracy, Fluency, Interaction, Coherence và Phonology. Appendix 3 mô tả rõ các mức A1-C2; riêng B2 nhấn mạnh khả năng diễn đạt quan điểm, mức kiểm soát ngữ pháp tương đối cao, nhịp nói khá đều, quản lý lượt lời, liên kết phát ngôn và độ dễ hiểu của phát âm [1].

| Tiêu chí | Bằng chứng AI có thể quan sát | Lưu ý chấm |
| --- | --- | --- |
| Range | Độ đa dạng từ vựng, độ tinh vi từ, cấu trúc câu, phạm vi chủ đề | Không đồng nhất từ hiếm với trình độ cao |
| Accuracy | Lỗi ngữ pháp, tỷ lệ câu/đơn vị không lỗi, tự sửa | ASR có thể biến lỗi phát âm thành lỗi từ |
| Fluency | Speech rate, articulation rate, pause ratio, mean length of run, sửa/khởi đầu lại | Không thưởng cho nói nhanh nhưng khó hiểu |
| Interaction | Phản hồi đúng ý, turn-taking, hỏi lại, duy trì/chốt hội thoại | Chỉ chấm khi có nhiệm vụ tương tác |
| Coherence | Phát triển chủ đề, từ nối, tham chiếu, mạch lập luận | Cần xét toàn bài, không chỉ đếm từ nối |
| Phonology | Intelligibility, âm đoạn, trọng âm, nhịp điệu, ngữ điệu | Không phạt accent nếu thông điệp vẫn dễ hiểu |

| Rubric vận hành: Mỗi tiêu chí được chấm trên thang thứ bậc A2/B1/B2 kèm xác suất; mức tổng thể không nên chỉ là trung bình cộng máy móc. Có thể áp dụng nguyên tắc “best-fit” với điều kiện không có tiêu chí cốt lõi thấp hơn quá một bậc. |
| --- |

## 6. Thiết kế nhiệm vụ nói

| Nhiệm vụ | Thời lượng | Bằng chứng chính | Gợi ý prompt |
| --- | --- | --- | --- |
| Task A - Mô tả/kể chuyện | 90-120 giây | Range, Fluency, Coherence, Phonology | Kể lại một trải nghiệm học tập đáng nhớ và lý do |
| Task B - Nêu quan điểm | 120 giây | Range, Accuracy, Coherence | Sinh viên có nên dùng AI trong học ngoại ngữ không? |
| Task C - Hội thoại AI | 3-5 lượt; 3 phút | Interaction, Fluency, phản hồi phù hợp | Lập kế hoạch hoạt động nhóm hoặc xử lý tình huống quen thuộc |

Task C nên dùng kịch bản bán cấu trúc: AI có thể diễn đạt lại hoặc hỏi sâu, nhưng phải đi theo cây mục tiêu đã định để mọi người học gặp độ khó tương đương. Không để mô hình hội thoại tự do hoàn toàn vì sẽ làm biến thiên nhiệm vụ và giảm khả năng so sánh điểm.

## 7. Chiến lược dữ liệu

### 7.1. Dữ liệu uy tín có thể sử dụng

| Nguồn | Quy mô/nhãn | Cách dùng phù hợp | Giới hạn |
| --- | --- | --- | --- |
| Speak & Improve Corpus 2025 [2] | Khoảng 315 giờ; >45.000 phát ngôn; >7.000 bài; CEFR holistic; 55 giờ transcript thủ công | Nghiên cứu CEFR, ASR L2, disfluency; pretrain/benchmark nếu được cấp quyền | Phi thương mại; hạn chế chia sẻ dữ liệu/mô hình và dùng LLM |
| speechocean762 [3] | 5.000 câu; 250 người nói; 5 chuyên gia chấm; CC BY 4.0 | Benchmark pronunciation/fluency và kiểm tra pipeline âm học | Người nói L1 Mandarin; đọc câu; không có CEFR holistic |
| L2-ARCTIC [4] | 24 người nói, gồm 4 người Việt; ~1 giờ/người; nhãn lỗi phone | Kiểm tra ASR/phát âm với accent Việt; nghiên cứu lỗi phát âm | Quy mô nhỏ; phần lớn read speech; CC BY-NC 4.0; không có CEFR |
| Trinity Lancaster Corpus [7] | 4,2 triệu từ; >2.000 tương tác thi nói | Phân tích discourse, interaction và đặc trưng theo trình độ | Cần kiểm tra quyền truy cập; không thay thế dữ liệu audio gắn nhãn cục bộ |
| Dữ liệu sinh viên tại trường | Đề xuất 60-100 SV × 2-3 nhiệm vụ | Tập kiểm định chính cho đúng đối tượng triển khai | Cần consent, hai giám khảo, cân bằng mức và bảo vệ dữ liệu |

### 7.2. Kế hoạch thu dữ liệu cục bộ

- Pilot 10-20 sinh viên để kiểm tra prompt, độ dài, chất lượng âm thanh, hướng dẫn và rubric.

- Thu chính thức 60-100 sinh viên; mỗi người làm Task A và B, một tập con làm Task C. Mục tiêu 120-250 response hợp lệ.

- Cố gắng phân tầng A2/B1/B2; nếu lệch lớp, dùng macro-F1, trọng số lớp và báo cáo phân phối nhãn.

- Hai giảng viên chấm độc lập theo sáu tiêu chí và mức tổng thể; 20-30% mẫu được chấm kép tối thiểu, tốt nhất là toàn bộ.

- Ẩn danh ID, tách bảng thông tin nhận dạng khỏi audio; lưu consent_version, thiết bị, noise condition và thời lượng.

- Chia train/dev/test theo speaker, tuyệt đối không để các bài của cùng một sinh viên xuất hiện ở cả train và test.

| Phương án khi dữ liệu ít: Dùng GroupKFold 5-fold theo speaker, mô hình đặc trưng có regularization và baseline rõ ràng. Không fine-tune end-to-end một mô hình âm thanh lớn trên vài trăm response rồi tuyên bố tổng quát hóa. |
| --- |

### 7.3. Lược đồ dữ liệu tối thiểu

| Nhóm trường | Trường gợi ý |
| --- | --- |
| Định danh ẩn danh | speaker_id, session_id, response_id, consent_version |
| Nhiệm vụ | task_id, prompt_version, task_type, difficulty_target |
| Âm thanh | audio_uri, duration, sample_rate, device_type, noise_flag |
| ASR | transcript_raw, transcript_clean, word_timestamps, asr_confidence, WER_subset |
| Nhãn người chấm | rater_id, six_criteria, overall_cefr, comments, adjudicated_score |
| Đặc trưng/mô hình | feature_version, acoustic_features, text_features, model_version |
| Kết quả | predicted_level, criterion_scores, confidence, evidence, review_status |

## 8. Kiến trúc hệ thống đề xuất

| Luồng xử lý: Nhiệm vụ nói → ghi âm/hội thoại → kiểm tra chất lượng → ASR có timestamp → trích xuất đặc trưng → chấm theo rubric → hiệu chỉnh confidence → tạo báo cáo → giảng viên duyệt khi cần. |
| --- |

| Tầng | Thành phần | Công nghệ khả thi | Đầu ra |
| --- | --- | --- | --- |
| Giao diện | Recorder, Conversation UI, report, teacher dashboard | React/Next.js hoặc giao diện web tương đương | Audio, lượt hội thoại, báo cáo |
| API | Quản lý phiên, nhiệm vụ, chấm, xuất kết quả | FastAPI; REST; background job | JSON có version và trạng thái |
| Speech | VAD, quality check, ASR, timestamps | faster-whisper/Whisper; ffmpeg; WebRTC VAD | Transcript + thời gian từ |
| Feature | Âm học, từ vựng, ngữ pháp, discourse, interaction | librosa/parselmouth; spaCy; bộ luật/embedding | Feature vector có giải thích |
| Scoring | Baseline và late-fusion ordinal model | Ordinal logistic/XGBoost; calibration | Mức CEFR + xác suất |
| Feedback | Tạo nhận xét từ evidence và rubric | Template trước; LLM có ràng buộc ở bản nâng cao | 2 điểm mạnh, 2 ưu tiên, bài luyện |
| Dữ liệu | Metadata, audio, audit log, model registry | PostgreSQL + object storage | Khả năng truy vết |

Thiết kế ưu tiên mô hình hybrid có thể giải thích. LLM, nếu dùng, nên nhận transcript + feature đã kiểm chứng + rubric và chỉ tạo phần diễn giải; điểm số chính phải đến từ quy trình có thể lặp lại, có version và được hiệu chỉnh trên dữ liệu người chấm.

## 9. Thiết kế mô hình và baseline

| Mô hình | Đầu vào | Mục đích |
| --- | --- | --- |
| B0 - Majority/stratified baseline | Phân phối nhãn | Mốc thấp nhất để tránh báo cáo kết quả ảo |
| B1 - Transcript-only | Đặc trưng từ vựng, ngữ pháp, coherence | Đo giá trị của nội dung ngôn ngữ |
| B2 - Audio-only | Pause, rate, prosody, embedding | Đo giá trị của fluency/phonology |
| B3 - Rule/LLM rubric | Transcript + rubric | Baseline đánh giá bằng mô hình ngôn ngữ có prompt cố định |
| M1 - Late fusion | B1 + B2 + interaction features | Mô hình chính, dự đoán thứ bậc và confidence |
| M2 - Ablation | Bỏ từng nhóm feature | Giải thích nhóm tín hiệu đóng góp vào điểm |

### 9.1. Đặc trưng nên ưu tiên

- Fluency: speech rate, articulation rate, số/tổng thời lượng pause, pause ratio, mean length of run, repetition và self-repair.

- Phonology: intelligibility proxy, ASR confidence/WER trên tập con, phone/prosody embedding, stress/rhythm/intonation ở mức phù hợp dữ liệu.

- Range: type-token/MTLD, độ phủ từ vựng, độ đa dạng cấu trúc và độ dài đơn vị cú pháp.

- Accuracy: lỗi ngữ pháp theo 100 từ, tỷ lệ clause không lỗi, agreement/tense/article và dấu hiệu tự sửa.

- Coherence: discourse markers, topic continuity, semantic similarity giữa các đoạn, cấu trúc mở-thân-kết.

- Interaction: latency phản hồi, độ phù hợp với câu hỏi, turn balance, clarification request, follow-up và task completion.

Không dùng độ chính xác ASR như một điểm phát âm trực tiếp. ASR có thể thiên lệch theo accent và môi trường thu; cần đánh giá WER theo nhóm và dùng các tín hiệu phát âm độc lập khi có thể.

## 10. Thiết kế thí nghiệm và tiêu chí thành công

| Mục tiêu | Chỉ số chính | Cách báo cáo |
| --- | --- | --- |
| Độ tin cậy nhãn | Human-human QWK/ICC | Theo từng tiêu chí và overall; xử lý bất đồng |
| AI-human agreement | QWK (primary), Spearman, ICC | 95% bootstrap CI; so với human-human |
| Sai số thứ bậc | MAE theo band; exact/adjacent accuracy | Confusion matrix A2/B1/B2 |
| Phân loại đa lớp | Macro-F1, per-class precision/recall | Không chỉ dùng accuracy khi lệch lớp |
| ASR | WER/CER trên tập transcript thủ công | Theo trình độ, thiết bị, noise và nhóm người nói |
| Calibration | Brier score/ECE | Reliability plot; ngưỡng human review |
| Công bằng | Chênh lệch AI-human theo subgroup | Effect size + CI; tránh kết luận khi n nhỏ |
| Khả dụng | SUS hoặc thang Likert; thời gian hoàn thành | Sinh viên và giảng viên tách riêng |

ETS nhấn mạnh rằng độ tin cậy người chấm thấp sẽ giới hạn chất lượng mô hình; trong kinh nghiệm được báo cáo, human QWK dưới 0,60 thường dẫn đến mô hình quá kém để sử dụng. ETS cũng nêu 0,70 như một ngưỡng tham khảo cho một số bối cảnh thực hành, nhưng ngưỡng phải phụ thuộc mục đích và mức rủi ro [6].

| Mục tiêu khóa luận đề xuất: Proof-of-concept đạt AI-human QWK ≥ 0,60 và adjacent accuracy ≥ 85%; mục tiêu tốt là QWK ≥ 0,70. Đây là tiêu chí đánh giá nghiên cứu, không phải bằng chứng đủ để cấp chứng chỉ hay triển khai high-stakes. |
| --- |

### 10.1. Quy trình đánh giá

- Huấn luyện giám khảo bằng anchor samples; chấm mù và ngẫu nhiên hóa response.

- Tính human-human agreement trước khi dùng nhãn để huấn luyện AI; adjudicate các ca lệch từ hai band trở lên.

- Chia dữ liệu theo speaker; khóa test set trước khi tối ưu mô hình.

- So sánh B0-B3 với M1 bằng cùng split và bootstrap confidence interval.

- Phân tích lỗi định tính tối thiểu 20 ca: AI cao hơn người, AI thấp hơn người, ASR lỗi, gần ranh giới CEFR.

- Kiểm tra subgroup và điều kiện âm thanh; công bố giới hạn mẫu thay vì che sai số trung bình.

## 11. Luồng chức năng của nguyên mẫu

| Bước | Sinh viên | Hệ thống | Giảng viên |
| --- | --- | --- | --- |
| 1 | Chọn/nhận nhiệm vụ | Hiển thị hướng dẫn và kiểm tra mic | Tạo prompt và target level |
| 2 | Ghi âm hoặc hội thoại | Thu audio, turn log, kiểm tra noise | Không can thiệp |
| 3 | Chờ xử lý | ASR, feature extraction, scoring, confidence | Theo dõi lỗi xử lý |
| 4 | Xem báo cáo | CEFR ước lượng + 6 tiêu chí + evidence | Duyệt ca confidence thấp |
| 5 | Luyện lại | Đề xuất 1-2 nhiệm vụ theo tiêu chí yếu | Có thể sửa khuyến nghị |
| 6 | Thử lại | So sánh phiên trước-sau | Theo dõi tiến bộ |

### 11.1. Báo cáo đầu ra tối thiểu

- Mức CEFR ước lượng và confidence; nếu sát ranh giới hiển thị dạng B1/B2 thay vì khẳng định tuyệt đối.

- Sáu tiêu chí với mô tả ngắn bám rubric, không chỉ số điểm trần trụi.

- Evidence: đoạn transcript, timestamp, chỉ số pause/rate và ví dụ cụ thể.

- Hai điểm mạnh, hai ưu tiên cải thiện và một bài luyện tiếp theo.

- Cờ cảnh báo audio kém, response quá ngắn, lệch chủ đề hoặc mô hình không chắc chắn.

- Lịch sử phiên và so sánh theo tiêu chí, nhưng không suy diễn tiến bộ từ một lần đo duy nhất.

## 12. API và cấu trúc module gợi ý

| Module/API | Trách nhiệm |
| --- | --- |
| POST /sessions | Tạo phiên, gán task set và prompt version |
| POST /responses | Tải audio/turn log, kiểm tra định dạng và consent |
| POST /responses/{id}/score | Khởi chạy pipeline chấm bất đồng bộ |
| GET /responses/{id}/report | Trả level, criteria, confidence, evidence và model version |
| POST /ratings | Nhập điểm giảng viên và trạng thái adjudication |
| GET /teacher/review-queue | Danh sách confidence thấp, audio lỗi hoặc AI-human lệch lớn |
| GET /analytics/evaluation | QWK, F1, MAE, confusion matrix và subgroup diagnostics |

## 13. Kế hoạch thực hiện 16 tuần

| Tuần | Công việc | Đầu ra kiểm chứng |
| --- | --- | --- |
| 1-2 | Tổng quan CEFR, automated speaking assessment, dữ liệu và đạo đức | Research matrix; phạm vi A2-B2; danh mục nguồn |
| 3-4 | Thiết kế rubric, task A/B/C, hướng dẫn chấm | Rubric v1; prompt bank; anchor samples |
| 5 | Xây recorder, ASR baseline; pilot | 10-20 người; báo cáo lỗi và chỉnh task |
| 6-8 | Thu dữ liệu chính và chấm bởi giảng viên | 120-250 response; human agreement |
| 9-10 | Feature extraction và baseline B0-B3 | Bảng kết quả baseline; error analysis |
| 11-12 | Mô hình fusion, calibration, confidence/review rule | Model M1; ablation; model card |
| 13 | Hoàn thiện giao diện report và teacher dashboard | End-to-end demo |
| 14 | Đánh giá AI-human, subgroup, usability | Metrics + CI + biểu đồ |
| 15 | Viết luận văn, sơ đồ, bảng kết quả | Bản thảo đầy đủ |
| 16 | Kiểm thử cuối, đóng gói, slide và demo | Mã nguồn, dữ liệu ẩn danh, báo cáo, video/demo |

## 14. Rủi ro và biện pháp kiểm soát

| Rủi ro | Tác động | Kiểm soát |
| --- | --- | --- |
| Thiếu dữ liệu theo band | Mô hình thiên về lớp đông | Quota A2/B1/B2; GroupKFold; macro metrics; thu bổ sung |
| Giám khảo không nhất quán | Nhãn không đáng tin | Training, anchors, chấm kép, QWK trước training, adjudication |
| ASR sai accent Việt | Sai grammar/range | WER theo subgroup; transcript thủ công tập con; audio features độc lập |
| Prompt không tương đương | Điểm phản ánh độ khó task | Prompt version, task blueprint, bán cấu trúc và pilot |
| LLM tạo phản hồi sai | Gây hiểu lầm người học | Grounding bằng evidence; template; cấm bịa lỗi; human review |
| Rò rỉ dữ liệu | Vi phạm quyền riêng tư/licence | Consent, pseudonym, mã hóa, retention, không tải corpus hạn chế lên dịch vụ giữ dữ liệu |
| Quá phạm vi | Không hoàn thiện nghiên cứu | MVP: recorder + assessor + report; conversation/personalizer theo milestone |

## 15. Đạo đức, quyền riêng tư và giới hạn sử dụng

- Xin đồng thuận rõ ràng cho việc ghi âm, chấm bởi con người, huấn luyện/đánh giá mô hình và thời hạn lưu trữ.

- Dùng speaker_id ẩn danh; thông tin nhận dạng và audio lưu tách biệt; giới hạn quyền truy cập.

- Cho phép người tham gia rút dữ liệu nếu quy trình nghiên cứu và quy định của trường cho phép.

- Không suy diễn giới tính, dân tộc, tính cách hoặc năng lực ngoài mục tiêu đánh giá nói.

- Công bố model version, phạm vi A2-B2, dữ liệu huấn luyện, điều kiện thất bại và confidence.

- Các quyết định có hệ quả học vụ phải do giảng viên xác nhận; AI chỉ cung cấp bằng chứng hỗ trợ.

- Tuân thủ licence từng corpus. Speak & Improve 2025 chỉ cấp quyền nghiên cứu/giáo dục phi thương mại và có hạn chế chia sẻ, phát hành mô hình/thống kê, cũng như xử lý qua LLM [2].

## 16. Sản phẩm bàn giao kỳ vọng

- Bộ rubric CEFR vận hành hóa cho A2-B2 và hướng dẫn giám khảo.

- Bộ nhiệm vụ nói/prompt bank có version và blueprint.

- Bộ dữ liệu cục bộ ẩn danh, datasheet và quy trình consent; chỉ chia sẻ trong phạm vi được phép.

- Pipeline ASR, feature extraction, scoring, calibration và feedback có model/version log.

- Ứng dụng web chạy end-to-end cho sinh viên và giảng viên.

- Báo cáo thực nghiệm gồm baseline, ablation, AI-human agreement, fairness diagnostics và error analysis.

- Model card, tài liệu cài đặt, API, kịch bản demo và danh sách giới hạn.

## 17. Cấu trúc luận văn gợi ý

| Chương | Nội dung |
| --- | --- |
| Chương 1 | Bối cảnh, vấn đề, mục tiêu, câu hỏi nghiên cứu, phạm vi và đóng góp |
| Chương 2 | CEFR speaking construct, automated speech assessment, ASR L2, dữ liệu và nghiên cứu liên quan |
| Chương 3 | Phương pháp: task design, rubric, thu dữ liệu, rating protocol, feature/model và metrics |
| Chương 4 | Thiết kế hệ thống, kiến trúc, database, API, giao diện và bảo mật |
| Chương 5 | Kết quả thực nghiệm, baseline, ablation, AI-human agreement, fairness và error analysis |
| Chương 6 | Thảo luận, giới hạn, kết luận và hướng phát triển |

## 18. Tiêu chí để chốt đề tài với giảng viên

- Chốt tên đề tài theo hướng “hỗ trợ đánh giá” và xác định A2-B2 là phạm vi kiểm chứng.

- Xác nhận có ít nhất hai giảng viên tiếng Anh tham gia xây rubric/chấm dữ liệu.

- Xác nhận nguồn người học và quy trình đồng thuận, lưu trữ audio.

- Chọn mức kết hợp: Nhóm 1 + 2 là mục tiêu; Nhóm 4 chỉ là gợi ý bài luyện.

- Chốt metric chính là QWK AI-human và human-human; split theo speaker.

- Chốt MVP trước khi làm hội thoại thích ứng hoặc LLM feedback nâng cao.

| MVP bảo vệ được: Sinh viên làm 2 bài nói → hệ thống trả CEFR A2/B1/B2 + 5 tiêu chí không tương tác → giảng viên xem confidence/evidence. Sau đó mới thêm Task C để đo Interaction và khép kín phương án Nhóm 1 + 2. |
| --- |

## Tài liệu tham khảo và nguồn dữ liệu

[1] Council of Europe (2020). Common European Framework of Reference for Languages: Learning, Teaching, Assessment - Companion Volume. Appendix 3: Qualitative Features of Spoken Language. Truy cập nguồn

[2] Cambridge University Press & Assessment (2025). The Speak & Improve Corpus 2025. Truy cập nguồn

[3] Zhang, J. et al. (2021). speechocean762: An Open-Source Non-native English Speech Corpus for Pronunciation Assessment. Interspeech 2021 / OpenSLR SLR101. Truy cập nguồn

[4] Zhao, G. et al. (2018). L2-ARCTIC: A Non-native English Speech Corpus. Interspeech 2018. Truy cập nguồn

[5] Xi, X., Higgins, D., Zechner, K., & Williamson, D. M. (2008). Automated Scoring of Spontaneous Speech Using SpeechRater v1.0. ETS Research Report RR-08-62. Truy cập nguồn

[6] ETS (2021). Best Practices for Constructed-Response Scoring. Sections on automated scoring, human-rater reliability and fairness. Truy cập nguồn

[7] Gablasova, D., Brezina, V., & McEnery, T. (2019). The Trinity Lancaster Corpus: Development, description and application. International Journal of Learner Corpus Research, 5(2), 126-158. Truy cập nguồn

[8] Cambridge English. Linguaskill Speaking Global Assessment Criteria. Truy cập nguồn

[9] Cai, Z. (2025). Developing an Automatic Pronunciation Scorer: Aligning Speech Evaluation Models and Applied Linguistics Constructs. Language Learning. Truy cập nguồn

Nguồn nội bộ: “2026 Định hướng xác định đề tài khóa luận.docx”, phần Ma trận ALDM-L và bốn nhóm đề tài khóa luận.

## Phụ lục A. Quy tắc quyết định mức CEFR

Đây là quy tắc thiết kế để thử nghiệm, không phải quy định chính thức của Council of Europe. Mô hình phải được hiệu chỉnh bằng điểm giảng viên và công bố confidence.

| Trạng thái | Cách hiển thị |
| --- | --- |
| Xác suất mức cao nhất ≥ 0,70 và audio hợp lệ | Hiển thị một mức, ví dụ B1, cùng sáu tiêu chí |
| Hai mức liền kề gần nhau | Hiển thị vùng ranh giới, ví dụ B1/B2, và yêu cầu thêm nhiệm vụ |
| Audio lỗi, response quá ngắn hoặc lệch chủ đề | Không chấm; yêu cầu ghi lại |
| Confidence thấp hoặc tiêu chí mâu thuẫn lớn | Đưa vào teacher review queue |
| Quyết định học vụ/high-stakes | Bắt buộc có người chấm xác nhận |

## Phụ lục B. Definition of Done cho khóa luận

- Rubric và task blueprint được giảng viên phê duyệt trước khi thu chính thức.

- Có human-human agreement và quy trình xử lý bất đồng.

- Mọi split đều theo speaker và test set được khóa.

- Có ít nhất ba baseline và một mô hình fusion; có ablation.

- Báo cáo QWK, macro-F1, MAE, adjacent accuracy, calibration và subgroup diagnostics.

- Demo end-to-end có confidence, evidence, human review và audit trail.

- Có datasheet/model card, consent, giới hạn sử dụng và hướng dẫn tái lập.
