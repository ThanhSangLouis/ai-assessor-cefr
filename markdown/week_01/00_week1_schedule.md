# Xây dựng hệ thống AI hỗ trợ đánh giá năng lực nói tiếng Anh theo CEFR cho sinh viên đại học Việt Nam ở trình độ A2-B2

## 00. Lịch làm việc chi tiết tuần 1

| Thuộc tính | Giá trị |
| --- | --- |
| Tuần | W1 - Nền tảng đo lường, phạm vi và điều kiện nghiên cứu |
| Trạng thái | DRAFT - cần thực hiện và xác nhận |
| Người phụ trách | SV2 điều phối; cả nhóm thực hiện |
| Người duyệt | GVHD |
| Phiên bản | 1.2 |
| Ngày cập nhật | 12/09/2026 |

## 1. Kết quả cuối tuần

Tuần 1 chỉ hoàn thành khi nhóm có một bộ tài liệu thống nhất về construct, phạm vi, câu hỏi nghiên cứu, dữ liệu, nhân sự và đạo đức. Không dùng tuần này để huấn luyện mô hình chính thức.

## 1.1. Requirement và tiêu chí nghiệm thu của lần làm lại

| Trường | Nội dung |
| --- | --- |
| Mục tiêu | Tạo lại baseline tuần 1 đúng construct CEFR, intended use low-stakes và quy tắc quản trị dự án |
| Trong phạm vi | Desk research; construct/scope/RQ/spec/governance draft; biểu mẫu và kế hoạch thực hiện G1 |
| Ngoài phạm vi | Giả lập kết quả sorting/quiz/workshop; tự chỉ định rater; tự phê duyệt ethics/G1; huấn luyện/chạy model |
| Acceptance | Nguồn truy vết được; mọi lựa chọn chưa duyệt ghi `PROPOSED`; các conflict/blocker có owner; không có claim đo lường bịa đặt |
| Cổng hoàn tất | Chỉ `PASS`/`CONDITIONAL PASS` sau cuộc họp G1 thực tế có biên bản và người xác nhận |

## 1.2. Điểm kiểm soát hiện tại

| Hạng mục | Trạng thái 12/09/2026 | Bằng chứng còn thiếu |
| --- | --- | --- |
| Desk research và audit hồ sơ | COMPLETED | Xem `02` và `24` |
| Descriptor sorting | NOT STARTED | Phiếu cá nhân và bảng tổng hợp |
| Familiarisation check | NOT STARTED | Bài làm/chấm của từng thành viên |
| Pedagogy workshop | NOT STARTED | Biên bản và xác nhận GV Ngoại ngữ |
| Rater/adjudicator | BLOCKED | Tên, cam kết thời gian và vai trò được xác nhận |
| Data/ethics review | PREPARED / NOT HELD | Synthetic DMP checks đã chạy; còn mẫu trường, reviewer, storage/encryption/access và quyết định |
| G1 review | NOT HELD | Cuộc họp thật, attendance, decision và approval reference trong `22` |
| Repository integrity | COMPLETED - NEW BASELINE | D019; branch `main`, baseline `c0ddd8a`; lịch sử cũ không được coi là đã phục hồi |

## 2. Lịch theo ngày

| Ngày | Khung giờ | Công việc | Người chính | Đầu ra | Trạng thái ban đầu |
| --- | --- | --- | --- | --- | --- |
| Ngày 1 | 08:00-09:30 | Kickoff, phân vai, giải thích mục tiêu G1 | SV2 | Lịch, RACI sơ bộ | NOT STARTED |
| Ngày 1 | 09:45-12:00 | Đọc CEFR/Companion theo nhóm | Cả nhóm | Reading log cá nhân | NOT STARTED |
| Ngày 1 | 13:30-15:30 | Descriptor sorting A2/B1/B2 | SV2 | Sorting result | NOT STARTED |
| Ngày 1 | 15:45-17:00 | Familiarisation check và thảo luận lỗi hiểu | SV2 | Quiz + answer key | NOT STARTED |
| Ngày 2 | 08:00-10:00 | Workshop construct với GV Ngoại ngữ | SV2 | Construct draft | NOT STARTED |
| Ngày 2 | 10:15-12:00 | Duyệt sáu tiêu chí và ranh giới construct | GV Ngoại ngữ | Criterion definitions | NOT STARTED |
| Ngày 2 | 13:30-16:00 | Lập construct-evidence matrix | SV1 + SV2 | Evidence matrix | DRAFT PREPARED |
| Ngày 2 | 16:00-17:00 | Ghi câu hỏi mở và người trả lời | SV3 | Open-question list | DRAFT PREPARED |
| Ngày 3 | 08:00-10:00 | Duyệt intended use và target population | SV3 | Scope draft | DRAFT PREPARED |
| Ngày 3 | 10:15-12:00 | Duyệt claims/non-claims | SV2 | Claims table | DRAFT PREPARED |
| Ngày 3 | 13:30-15:30 | Rà soát RQ1-RQ6 | SV2 | RQ v1 | DRAFT PREPARED |
| Ngày 3 | 15:45-17:00 | Duyệt Definition of Done | Cả nhóm | DoD | DRAFT PREPARED |
| Ngày 4 | 08:00-11:30 | Điền ALTE Speaking Grid bản nháp | SV3 | ALTE Grid draft | DRAFT PREPARED |
| Ngày 4 | 13:30-14:45 | Lập validation argument map | SV2 | Validation map | DRAFT PREPARED |
| Ngày 4 | 15:00-17:00 | Data plan, consent, privacy và risk register | SV3 | DMP + consent + risks | DRAFT PREPARED |
| Ngày 5 | 08:00-10:30 | Kiểm tra chéo toàn bộ hồ sơ | Cả nhóm | Review comments | NOT STARTED |
| Ngày 5 | 10:45-12:00 | Hoàn thiện Chương 1 | Cả nhóm | Chapter 1 draft | DRAFT PREPARED |
| Ngày 5 | 13:30-15:00 | Họp G1 với GVHD/GV Ngoại ngữ | SV2 trình bày | G1 minutes | NOT HELD |
| Ngày 5 | 15:15-17:00 | Sửa quyết định, khóa v1 và lập backlog W2 | SV3 | Decision log + W2 backlog | BLOCKED BY G1 |

## 3. Các cuộc họp bắt buộc

| Cuộc họp | Thành phần | Thời lượng | Điều phải quyết định |
| --- | --- | --- | --- |
| Kickoff | 3 SV + GVHD nếu có thể | 60-90 phút | Tên đề tài, mục tiêu tuần, cách phân vai |
| Pedagogy workshop | 3 SV + ít nhất 1 GV Ngoại ngữ | 120 phút | Construct, sáu tiêu chí, Production/Interaction/Mediation |
| Data/ethics review | SV3 + GVHD | 60 phút | Consent, PII, quyền rút dữ liệu, nơi lưu |
| G1 review | 3 SV + GVHD + GV Ngoại ngữ | 60-90 phút | PASS/REVISE/BLOCKING cho toàn bộ hồ sơ |

## 4. Nhịp điều hành hằng ngày

1. 08:00: cập nhật ba việc quan trọng nhất trong ngày.
2. 12:00: ghi quyết định mới vào `21_week1_decision_log.md`.
3. 16:30: kiểm tra đầu ra, người duyệt và trở ngại.
4. 17:00: commit tài liệu, không commit PII hoặc audio.

## 5. Quy tắc ưu tiên

- P0: construct, intended use, rater, ethics và G1.
- P1: descriptor map, ALTE Grid, validation map và Chương 1.
- P2: trình bày đẹp, tự động hóa biểu mẫu và tài liệu mở rộng.
- Khi trễ, cắt P2 trước; không cắt rater independence, consent hoặc construct review.

## 6. Checklist cuối ngày

- [ ] File trong ngày có người sở hữu và ngày cập nhật.
- [ ] Quyết định quan trọng đã ghi log.
- [ ] Vấn đề chưa rõ có owner và deadline.
- [ ] Tên đề tài và phạm vi A2-B2 nhất quán.
- [ ] Không có PII/audio trong kho mã nguồn.
