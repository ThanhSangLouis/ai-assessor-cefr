# Xây dựng hệ thống AI hỗ trợ đánh giá năng lực nói tiếng Anh theo CEFR cho sinh viên đại học Việt Nam ở trình độ A2-B2

## Giả định triển khai

- Thời gian thực hiện: 10 tuần.
- Nhóm thực hiện: 3 sinh viên.
- Nhân sự chuyên môn: 2 giảng viên chấm độc lập và 1 giảng viên phân xử.
- Đối tượng: sinh viên đại học Việt Nam từ 18 tuổi, trình độ A2-B2.
- Bối cảnh sử dụng: đánh giá quá trình, mức độ rủi ro thấp; hệ thống không cấp chứng chỉ CEFR.

## Phân công

| Vai trò | Nhiệm vụ chính | Sản phẩm sở hữu |
| --- | --- | --- |
| SV1 - Speech pipeline | Audio, QC, ASR, timestamp, WER, Fluency và Phonology features | Pipeline âm thanh và feature dictionary |
| SV2 - Đo lường và mô hình | Rubric, công cụ chấm, text/interaction features, mô hình, calibration và thống kê | Phương pháp đánh giá và kết quả thực nghiệm |
| SV3 - Sản phẩm và dữ liệu | API, giao diện, teacher queue, consent, thu dữ liệu, usability và đóng gói | Hệ thống tích hợp và hồ sơ dữ liệu |
| Giảng viên Ngoại ngữ | Sở hữu rubric, chọn anchor, hiệu chuẩn, chấm độc lập và phân xử | Rubric và nhãn tham chiếu |

## Tuần 1 - Chốt bài toán và điều kiện nghiên cứu

**Mục tiêu:** xác định chính xác hệ thống đánh giá ai, đánh giá nội dung gì và giới hạn sử dụng.

- Ngày 1: họp GVHD; chốt tên đề tài, phạm vi A2-B2, đối tượng và bối cảnh formative/low-stakes.
- Ngày 2: đọc CEFR Companion Volume; xác định sáu tiêu chí Range, Accuracy, Fluency, Interaction, Coherence và Phonology.
- Ngày 3: chốt câu hỏi nghiên cứu, đầu ra hệ thống, vai trò AI và quyền quyết định cuối cùng của giảng viên.
- Ngày 4: xác nhận 2 rater và 1 adjudicator; soạn consent, quyền rút dữ liệu, mã hóa và thời hạn lưu trữ.
- Ngày 5: lập data plan, risk register, cấu trúc kho mã nguồn và lịch họp cố định.
- Lane viết: hoàn thành Chương 1.
- **G1:** GVHD duyệt phạm vi, RQ, nhân sự chấm, kế hoạch dữ liệu và đạo đức.

## Tuần 2 - Xây rubric và nhiệm vụ nói

**Mục tiêu:** biến mô tả CEFR thành hướng dẫn chấm có thể quan sát và kiểm chứng.

- Ngày 1: mô tả biểu hiện A2, B1 và B2 cho từng tiêu chí bằng ngôn ngữ vận hành.
- Ngày 2: thiết kế Task A kể/mô tả, Task B nêu quan điểm và Task C hội thoại ba lượt.
- Ngày 3: tạo prompt bank, yêu cầu thời lượng, thời gian chuẩn bị và nguyên tắc luân phiên prompt.
- Ngày 4: xây rating form, reason codes, tùy chọn “chưa đủ bằng chứng” và hướng dẫn chấm độc lập.
- Ngày 5: hai rater thử chấm anchor; ghi nguyên nhân bất đồng; sửa rubric.
- Lane viết: hoàn thành Chương 2.
- **G2:** mỗi tiêu chí có nhiệm vụ tạo evidence; rater giải thích được điểm; Task C và latency đã được test.
- Dự phòng: nếu Task C chưa ổn định, loại Task C và tiêu chí Interaction khỏi MVP.

## Tuần 3 - Xây pipeline chạy xuyên suốt

**Mục tiêu:** một bài nói đi được từ thu âm đến báo cáo kỹ thuật.

- Ngày 1: dựng cơ sở dữ liệu, định danh giả, API và giao diện thu âm/tải file.
- Ngày 2: chuẩn hóa audio; kiểm tra thời lượng, im lặng, clipping, nhiễu và định dạng.
- Ngày 3: tích hợp faster-whisper để tạo transcript, timestamp và ASR confidence.
- Ngày 4: trích xuất tốc độ nói, khoảng dừng, voiced time, số từ và độ đa dạng từ vựng.
- Ngày 5: tạo report JSON, log lỗi, phiên bản feature và kiểm thử bằng audio mẫu.
- Lane viết: hoàn thành 70% Chương 3.
- **G3:** một response khoảng hai phút chạy được upload -> QC -> ASR -> feature -> report và không lộ danh tính.

## Tuần 4 - Pilot và hiệu chuẩn người chấm

**Mục tiêu:** phát hiện lỗi thiết kế trước khi thu dữ liệu chính.

- Ngày 1-2: tuyển 10-14 người; lấy consent; thu Task A/B và thử Task C trên nhóm nhỏ.
- Ngày 3: kiểm tra tỷ lệ hoàn thành, chất lượng audio, thời lượng, lỗi prompt và lỗi ASR.
- Ngày 4: hai rater chấm độc lập; tính agreement, QWK và lập danh sách bất đồng.
- Ngày 5: adjudicator phân tích bất đồng; sửa prompt, anchor, rubric và ngưỡng QC; khóa phiên bản v1.
- Lane viết: hoàn thành Chương 3 và pilot protocol.
- **G4:** completion tối thiểu 85% và QWK human-human tối thiểu 0,60.
- Dự phòng: nếu QWK dưới 0,60, dành tuần kế tiếp để sửa rubric và chuyển tuyên bố thành exploratory prototype.

## Tuần 5 - Thu dữ liệu chính giai đoạn 1

**Mục tiêu:** thu 30-40 người đầu tiên bằng quy trình ổn định.

- Mở đăng ký, kiểm tra điều kiện tham gia và phân bổ prompt tương đương.
- Thu Task A/B; QC ngay trong ngày; yêu cầu ghi lại nếu file không hợp lệ.
- Rater chấm cuốn chiếu và không được xem kết quả AI.
- Theo dõi phân bố band, prompt, thiết bị, độ ồn và lượng bài tồn đọng.
- Kiểm tra consent, metadata, mã người nói và file thiếu cuối mỗi ngày.
- Lane viết: hoàn thành 50% Chương 4.
- **G5:** metadata đầy đủ tối thiểu 90%; bài invalid có reason code; không có PII trong model workspace.

## Tuần 6 - Hoàn thành dữ liệu và khóa nhãn

**Mục tiêu:** tạo dataset_v1 đủ điều kiện huấn luyện và kiểm định.

- Tiếp tục thu đến mục tiêu 70-90 người, sàn 60; Task C chỉ áp dụng cho 25-30 người nếu ổn định.
- Hoàn tất double-rating; adjudicator xử lý các bài bất đồng.
- Chép tay 15-20 bài đa dạng về band, thiết bị và độ ồn để tính WER.
- Tính human-human agreement; kiểm tra phân bố nhãn; tạo data dictionary và datasheet.
- Gán fold theo speaker; tách confirmation set; đóng băng pre-registration.
- Lane viết: hoàn thành Chương 4.
- **G6:** dataset_v1 khóa; không speaker leakage; có gold label, manual transcript và fold assignment.

## Tuần 7 - Xây các baseline

**Mục tiêu:** tạo mốc so sánh công bằng cho mô hình chính.

- Xây B0 majority/ordinal baseline.
- Xây B1 audio-only từ Fluency, Phonology và quality features.
- Xây B2 transcript-only từ Range, Accuracy và Coherence.
- Xây B3 local LLM với rubric và prompt đã khóa.
- Chạy nested/repeated GroupKFold; tính QWK với CI, macro-F1, Gross Error Rate và confusion matrix.
- Lane viết: dựng bảng kết quả và cấu trúc Chương 5.
- **G7:** ít nhất một baseline tốt hơn B0; kết quả chạy lại được bằng script, config và seed.

## Tuần 8 - Late fusion, calibration và phân tích lỗi

**Mục tiêu:** xây mô hình M1 và quy tắc chuyển bài cho giảng viên.

- Kết hợp xác suất từ audio, transcript và interaction bằng late fusion.
- Thực hiện Platt calibration và kiểm tra độ tin cậy của confidence.
- Chọn teacher-review threshold cho bài low-confidence, audio kém hoặc ASR nghi sai.
- Thực hiện năm ablation và paired cluster bootstrap theo speaker.
- Phân tích quan hệ WER-error và 25 ca sai điển hình.
- Lane viết: hoàn thành 70% Chương 5.
- **G8:** M1 được so sánh với toàn bộ baseline; khóa model, calibration và threshold.
- Dự phòng: nếu fusion không tốt hơn, chọn baseline đơn giản tốt nhất và giải thích bằng ablation.

## Tuần 9 - Hoàn thiện sản phẩm và Living Lab

**Mục tiêu:** chứng minh hệ thống sử dụng được và phản hồi có bằng chứng.

- Hoàn thiện báo cáo sáu tiêu chí, confidence, timestamp và transcript evidence.
- Hoàn thiện teacher queue, chức năng xác nhận/sửa điểm và audit log.
- Xuất speaking_profile.json; kiểm tra độ ổn định giữa prompt, lần chạy và nhiễu âm thanh.
- Usability test với 6-8 sinh viên và 2 giảng viên.
- Sửa lỗi quan trọng; kiểm thử upload, QC, review, rút và xóa dữ liệu.
- Lane viết: hoàn thành Chương 5 và 60% Chương 6.
- **G9:** workflow hoàn chỉnh; feedback không bịa evidence; low-confidence được chuyển sang teacher review.

## Tuần 10 - Confirmation, đóng gói và bảo vệ

**Mục tiêu:** tạo phiên bản cuối có thể tái lập và không điều chỉnh theo tập kiểm tra.

- Khóa code, model, config và dependency; chạy confirmation set đúng một lần.
- Tạo bảng kết quả, khoảng tin cậy, calibration plot và confusion matrix cuối.
- Hoàn thiện model card, dataset datasheet, feature dictionary, API document và README.
- Hoàn thành Chương 6, Chương 7, tóm tắt, kết luận và giới hạn.
- Hoàn thiện slide, demo offline, câu hỏi hội đồng; chạy thử trên máy sạch và sao lưu.
- **G10:** máy sạch chạy được theo README; slide khớp luận văn; confirmation set không được dùng để huấn luyện lại.

## Quy tắc điều hành

- Cuối mỗi tuần phải có biên bản cổng G1-G10: đạt, chưa đạt, nguyên nhân và hành động tiếp theo.
- Chương 1-3 phải hoàn thành khoảng 90% trước khi thu dữ liệu chính.
- Mỗi experiment phải lưu model version, rubric version, fold, seed và metric.
- Không hy sinh double-rating, speaker-level split, calibration và error analysis để làm thêm chatbot, LMS hoặc giao diện nâng cao.
- Nếu lane viết trễ hai tuần liên tiếp, cắt tính năng mở rộng và chuyển nguồn lực sang hoàn thiện luận văn.
