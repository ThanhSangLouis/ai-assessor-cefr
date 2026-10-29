# Xây dựng hệ thống AI hỗ trợ đánh giá năng lực nói tiếng Anh theo CEFR cho sinh viên đại học Việt Nam ở trình độ A2-B2

## 09. Phạm vi và mục đích sử dụng

| Thuộc tính | Giá trị |
| --- | --- |
| Tuần | W1 - Nền tảng đo lường, phạm vi và điều kiện nghiên cứu |
| Trạng thái | DRAFT - cần thực hiện và xác nhận |
| Người phụ trách | SV3 |
| Người duyệt | GVHD |
| Phiên bản | 1.1 |
| Ngày cập nhật | 02/09/2026 |

## 1. Phạm vi chốt

Hệ thống hỗ trợ đánh giá bài nói tiếng Anh của sinh viên đại học Việt Nam từ 18 tuổi ở dải A2-B2, trong bối cảnh đánh giá quá trình/chẩn đoán và mức độ rủi ro thấp. Đây là constraint bắt buộc của dự án; G1 vẫn phải ghi nhận sign-off chính thức cho D002.

## 2. Trong phạm vi MVP

- Thu/nhận audio cho Task A, B và Task C nếu ổn định.
- QC audio và log metadata.
- ASR local, transcript và timestamp.
- Bằng chứng audio, text và interaction.
- Hồ sơ sáu tiêu chí; `interaction.level=null` và `score_status=insufficient_evidence` khi task không tạo đủ bằng chứng.
- Estimated A2/B1/B2, probability, calibrated confidence.
- Teacher-review flag và report có evidence.
- Double-rating, adjudication, speaker-level validation và error analysis.

## 3. Ngoài phạm vi

- Chứng chỉ CEFR chính thức.
- Tự động quyết định đậu/rớt/xếp lớp/học vụ.
- A1, C1, C2.
- Trẻ vị thành niên hoặc người ngoài nhóm đại học Việt Nam.
- Emotion, personality, gender hoặc socioeconomic inference.
- Chatbot tutor, LMS hoàn chỉnh, AI Orchestrator.
- Mediation scoring nếu không có task riêng.

## 4. Intended use statement

Kết quả được dùng để giúp sinh viên và giảng viên nhận biết hồ sơ Speaking hiện tại, xem bằng chứng, chọn tối đa hai ưu tiên cải thiện và xác định bài cần giảng viên duyệt. Kết quả không dùng độc lập cho quyết định có hậu quả cao.

## 5. Người dùng

| Người dùng | Nhu cầu | Quyền |
| --- | --- | --- |
| Sinh viên | Làm bài, xem phản hồi, yêu cầu giải thích/rút dữ liệu | Không sửa transcript/audio sau nộp |
| Giảng viên | Thiết lập rubric, xem evidence, duyệt/sửa kết quả | Quyết định cuối cùng |
| Nhóm nghiên cứu | Vận hành pipeline, phân tích dữ liệu đã mã hóa | Không xem PII nếu không cần |
| GVHD | Duyệt phạm vi, protocol và release | Truy cập theo data plan |

## 6. Đầu ra hệ thống

- `overall.band`: A2/B1/B2 estimated.
- `overall.probs` và `overall.confidence`.
- Sáu criterion scores/profiles.
- Evidence refs và reason codes.
- Hai ưu tiên cải thiện.
- `teacher_review_required`.
- Rubric/model/calibration version.
- `teacher_verified=false` theo mặc định; chỉ thành `true` sau hành động xác nhận thực tế có audit record.

## 6.1. Prohibited-use controls tối thiểu

- UI/API không có action tự động pass/fail, cấp chứng chỉ hoặc xếp lớp.
- Export ghi rõ `estimated`, population/task scope và trạng thái kiểm duyệt.
- Consumer của `speaking_profile` phải kiểm tra `review_status`; không được suy `teacher_verified` từ confidence cao.
- Ca audio/ASR/evidence không hợp lệ trả reason code và teacher review, không tạo band mặc định.

## 7. Điều kiện thay đổi phạm vi

Mọi thay đổi phải có decision log, ảnh hưởng RQ/dữ liệu/ethics và phê duyệt GVHD. Không thêm tính năng chỉ vì demo đẹp hơn.

**Trạng thái phê duyệt:** D002-D006 và D011-D012 vẫn `PROPOSED`; nội dung file này là baseline để review, không phải biên bản G1.
