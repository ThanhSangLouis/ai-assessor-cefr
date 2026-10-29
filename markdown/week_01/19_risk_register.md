# Xây dựng hệ thống AI hỗ trợ đánh giá năng lực nói tiếng Anh theo CEFR cho sinh viên đại học Việt Nam ở trình độ A2-B2

## 19. Sổ đăng ký rủi ro

| Thuộc tính | Giá trị |
| --- | --- |
| Tuần | W1 - Nền tảng đo lường, phạm vi và điều kiện nghiên cứu |
| Trạng thái | DRAFT - cần thực hiện và xác nhận |
| Người phụ trách | Cả nhóm; SV3 quản lý |
| Người duyệt | GVHD |
| Phiên bản | 1.2 |
| Ngày cập nhật | 12/09/2026 |

## 1. Thang đánh giá

- Xác suất/tác động: 1 thấp, 2 vừa, 3 cao.
- Điểm = xác suất x tác động.
- Điểm 6-9 phải có contingency cụ thể và owner.

## 2. Risk register

| ID | Rủi ro | XS | TĐ | Trigger | Phòng ngừa | Dự phòng | Owner | Trạng thái |
| --- | --- | ---: | ---: | --- | --- | --- | --- | --- |
| R01 | Không có đủ rater | 2 | 3 | Chưa xác nhận cuối W1 | Mời sớm, có danh sách dự phòng | Giảm scope thành pilot; không bỏ double-rating | SV3/GVHD | OPEN |
| R02 | Human QWK thấp | 2 | 3 | Pilot <0.60 | Familiarisation, anchor, manual rõ | Dành W5 hiệu chuẩn; hạ claim exploratory | SV2 | OPEN |
| R03 | Ethics/consent trễ | 2 | 3 | Chưa được phép cuối W3 | Nộp từ W1, dùng mẫu trường | Phát triển bằng public data; giảm local sample | SV3 | OPEN |
| R04 | Tuyển dưới sàn | 2 | 3 | <25 W5 hoặc <45 W6 | Nhiều lớp/kênh, theo dõi hằng ngày | Cắt Task C; báo CI rộng; pilot study | SV3 | OPEN |
| R05 | ASR sai accent Việt | 3 | 3 | WER/confidence xấu | Local ASR, manual subset, QC | Mask text feature, teacher review, audio-only | SV1 | OPEN |
| R06 | Noise/device bias | 2 | 3 | Error tăng theo quality | QC, hướng dẫn ghi, metadata | Re-record, stratify, quality flag | SV1 | OPEN |
| R07 | Prompt floor/ceiling | 2 | 3 | Completion/score dồn band | Prompt review và pilot | Thay prompt trước lock v1 | Pedagogy | OPEN |
| R08 | Interaction không ổn định/không authentic | 2 | 3 | Latency/prompt tree lỗi hoặc response không contingent | Pedagogy review và test W2-W4 | Cắt Task C/Interaction hoặc thu hẹp claim | SV3/SV1 | OPEN |
| R09 | Accent bị chấm như lỗi | 2 | 3 | Comment rater tập trung native-like | Intelligibility guideline | Recalibration, audit cases | SV2 | OPEN |
| R10 | Speaker leakage | 2 | 3 | Cùng ID ở nhiều split | Fold manifest và tests | Hủy run, tạo lại split, rerun | SV2 | OPEN |
| R11 | LLM feedback bịa evidence | 2 | 3 | Không tìm được ref | Evidence-only prompt/schema | Tắt free generation; template feedback | SV3 | OPEN |
| R12 | Fusion không hơn baseline | 2 | 2 | G8 delta không rõ | Baselines mạnh, ablation | Chọn baseline đơn giản tốt nhất | SV2 | OPEN |
| R13 | Sáu tiêu chí quá tải rater | 2 | 2 | Rating lâu/halo | Two-pass workflow | Gom UI, luyện từng criterion | SV2 | OPEN |
| R14 | Lane viết trễ | 2 | 3 | Trễ 2 tuần | Viết song song, owner chương | Cắt stretch, SV3 hỗ trợ viết | Cả nhóm | OPEN |
| R15 | PII/audio/transcript lộ vào workspace/log | 2 | 3 | Tên/email/MSSV/nội dung nói trong repo/log | Identity separation, ignore rules, log schema test | Incident response, revoke/rotate access, đánh giá nghĩa vụ thông báo | SV3 | OPEN |
| R16 | Confirmation set bị dùng sớm | 1 | 3 | Truy cập prediction trước freeze | Access lock, hash, prereg | Tạo tập mới nếu khả thi; báo deviation | GVHD/SV2 | OPEN |
| R17 | Mất/ghi đè dữ liệu | 1 | 3 | File thiếu/corrupt hoặc snapshot đổi checksum | Backup + version + hash | Restore backup; re-collect theo consent | SV3 | OPEN |
| R18 | Demo không chạy | 2 | 2 | End-to-end fail W9 | Offline test, clean machine | Video demo minh bạch + static report | SV3 | OPEN |
| R19 | Claim quy mô/metric không tái lập | 3 | 3 | Không có script/config/output precision analysis | Đóng gói artifact trước khi duyệt D015 | Hạ thành planning assumption; không claim đủ mẫu | SV2 | TRIGGERED |
| R20 | Giả lập completion/sign-off | 2 | 3 | File ghi completed/approved nhưng không có biên bản/bài làm | Tách document/activity/gate status | Reopen item, sửa log và thông báo deviation | SV3/GVHD | MITIGATING |
| R21 | So sánh model trên tập speaker khác nhau | 2 | 3 | Interaction model chỉ có Task C subset nhưng so trực tiếp với A/B full set | Common-fold/common-response comparison spec | Rerun paired comparison trên common subset | SV2 | OPEN |
| R22 | Repository metadata không hoàn chỉnh | 3 | 2 | `git status` từng báo not a repository dù có thư mục `.git` | Metadata hỏng đã được sao lưu; baseline mới có commit/hash rõ; mọi work item dùng base/head cụ thể | Nếu baseline mất, phục hồi từ bản sao workspace/remote mới sau khi được cấu hình; không tuyên bố có lịch sử trước D019 | Chủ repo | MITIGATED 12/09/2026 |

## 3. Review hằng tuần

- Cập nhật trigger/status vào cuối mỗi tuần.
- Risk điểm 6-9 được báo trong gate review.
- Khi contingency được kích hoạt, ghi decision log và cập nhật claims.

## 4. Trạng thái

| Trạng thái | Nghĩa |
| --- | --- |
| OPEN | Đang theo dõi |
| MITIGATING | Đang thực hiện phòng ngừa |
| TRIGGERED | Đã xảy ra, dùng contingency |
| CLOSED | Không còn hoặc đã xử lý xong |
