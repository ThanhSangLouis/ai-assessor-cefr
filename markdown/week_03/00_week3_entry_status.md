# Xây dựng hệ thống AI hỗ trợ đánh giá năng lực nói tiếng Anh theo CEFR cho sinh viên đại học Việt Nam ở trình độ A2-B2

## 00. Trạng thái vào tuần 3

| Thuộc tính | Giá trị |
| --- | --- |
| Trạng thái W3 | BLOCKED BY G1/G2/V3 |
| Planning baseline | `c0ddd8acd79836fd55badad01ec70b4ae0ebfe7b` |
| Công việc được phép | Requirement/research/survey/spec/test plan/work item draft |
| Công việc chưa được phép | Implement vertical slice, tải model/corpus, xử lý dữ liệu thật, chấm CEFR |
| Ngày kiểm tra | 12/09/2026 |

## 1. Entry gate

| Điều kiện | Hiện trạng | Hệ quả |
| --- | --- | --- |
| Git baseline | PASS - D019 | Có thể audit package/diff mới |
| G1 | NOT HELD | Construct/task/data governance chưa human-approved |
| G2 | NOT HELD | Rubric, reason codes, schema, Task C và fixture chưa khóa |
| V3 work item | DRAFT_V2 | Không tạo prompt implementation |
| Approved storage | Chưa có | Chỉ dùng fixture synthetic trong thiết kế/test |
| External corpus/license | NO DOWNLOAD AUTHORIZED | Loader ngoài scope implementation đầu tiên |

## 2. Scope an toàn của vertical slice đầu tiên

- Nhận audio fixture synthetic/local được caller cho phép.
- Validate container/format/duration và chạy QC deterministic.
- Gọi ASR qua adapter local/fake; lưu provenance/version.
- Tính một nhóm feature kỹ thuật cơ bản có version.
- Trả report kỹ thuật typed với status/reason codes.
- Không tạo criterion score, overall CEFR, feedback học tập hoặc `teacher_verified=true`.

## 3. Stop conditions

- Không implement nếu package chưa được người dùng duyệt đúng work ID + V3.
- Không dùng audio/transcript/PII người thật hoặc external API.
- Không tải faster-whisper model/corpus mặc định trong unit/integration test.
- Không hard-code threshold được mô tả như đã validation.
- Không gọi report kỹ thuật là kết quả đánh giá CEFR.
