# Xây dựng hệ thống AI hỗ trợ đánh giá năng lực nói tiếng Anh theo CEFR cho sinh viên đại học Việt Nam ở trình độ A2-B2

## 10. Định nghĩa đối tượng và kế hoạch lấy mẫu

| Thuộc tính | Giá trị |
| --- | --- |
| Tuần | W1 - Nền tảng đo lường, phạm vi và điều kiện nghiên cứu |
| Trạng thái | DRAFT - cần thực hiện và xác nhận |
| Người phụ trách | SV3 |
| Người duyệt | GVHD + phụ trách đạo đức |
| Phiên bản | 1.1 |
| Ngày cập nhật | 02/09/2026 |

## 1. Đối tượng mục tiêu

Sinh viên đang học tại cơ sở giáo dục đại học ở Việt Nam, từ 18 tuổi, dùng tiếng Anh như ngoại ngữ và có năng lực dự kiến trong dải A2-B2.

## 2. Tiêu chí tham gia

- Từ 18 tuổi tại thời điểm consent.
- Là sinh viên đại học trong bối cảnh được phê duyệt. Không tự mở rộng sang cao đẳng nếu chưa sửa tên đề tài, scope và decision log.
- Có thể thực hiện bài nói tiếng Anh.
- Đồng ý thu và xử lý audio/transcript cho mục đích nghiên cứu nêu trong consent.
- Hoàn thành screening/pretest hoặc có bằng chứng band dự kiến.

## 3. Tiêu chí loại trừ

- Dưới 18 tuổi.
- Không đồng ý ghi âm hoặc rút consent trước khi dữ liệu được xử lý.
- Audio không sử dụng được sau lần ghi lại cho phép.
- Không thuộc dải A2-B2 theo quy tắc screening đã chốt.
- Dữ liệu trùng hoặc không xác minh được participant ID.

## 4. Quy mô đề xuất - chưa được phê duyệt

- Mục tiêu lập kế hoạch: 70-90 speakers.
- Sàn quản trị đề xuất: 60 speakers.
- Pilot: 10-14 speakers.
- Task C subset: 25-30 speakers nếu pilot ổn định.
- Manual transcript audit: 15-20 responses đa dạng.

Các con số trên kế thừa đề cương v3.1 nhưng artifact mô phỏng/precision analysis được viện dẫn trong đề cương không có trong workspace hiện tại. Vì vậy chưa được dùng để tuyên bố “đủ mẫu”; phải tái tạo hoặc cung cấp script/config/output, sau đó GVHD duyệt D015.

## 5. Biến cần theo dõi để audit

| Nhóm | Biến |
| --- | --- |
| Học tập | screening band, năm học, kinh nghiệm học tiếng Anh |
| Task | task ID, prompt ID, preparation time, duration |
| Thiết bị | device category, browser/app version, microphone type nếu người học biết |
| Chất lượng | noise, clipping, silence, ASR confidence, WER subset |
| Nhân khẩu tối thiểu | Chỉ thu biến thực sự cần và được consent; tránh dữ liệu nhạy cảm không dùng |

## 6. Kế hoạch cân bằng

- Theo dõi số người theo A2/B1/B2 mỗi ngày.
- Luân phiên prompt tương đương.
- Không tuyển chỉ một lớp nếu có thể mở rộng hợp lý.
- Không loại người chỉ vì accent.
- Ghi rõ subgroup nào quá nhỏ để kết luận fairness.
- Split/fold manifest bắt buộc nhóm theo `speaker_id`; thêm kiểm tra tự động không một speaker xuất hiện ở hơn một split/fold tại cùng vòng đánh giá.

## 7. Screening workflow

1. Cung cấp participant information.
2. Lấy consent.
3. Gán participant ID.
4. Thu screening evidence.
5. Kiểm tra điều kiện.
6. Xếp lịch task; không tiết lộ nhãn AI cho rater.

## 8. Checklist

- [ ] Inclusion/exclusion được ethics/GVHD duyệt.
- [ ] Không thu dữ liệu không cần thiết.
- [ ] Có kế hoạch theo dõi band/prompt/device.
- [ ] Speaker ID dùng xuyên suốt và không chứa MSSV.
- [ ] Quy mô và precision analysis có artifact tái lập, seed/config và reviewer.
- [ ] Kênh tuyển, lớp, người phụ trách và lịch được xác nhận bằng văn bản.
