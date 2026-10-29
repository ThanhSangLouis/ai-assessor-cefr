# Xây dựng hệ thống AI hỗ trợ đánh giá năng lực nói tiếng Anh theo CEFR cho sinh viên đại học Việt Nam ở trình độ A2-B2

## 13. Definition of Done

| Thuộc tính | Giá trị |
| --- | --- |
| Tuần | W1 - Nền tảng đo lường, phạm vi và điều kiện nghiên cứu |
| Trạng thái | DRAFT - cần thực hiện và xác nhận |
| Người phụ trách | Cả nhóm |
| Người duyệt | GVHD |
| Phiên bản | 1.1 |
| Ngày cập nhật | 02/09/2026 |

## 1. Definition of Done cho một tài liệu

Một file chỉ được xem là `DONE` khi:

- Có owner, approver, version và ngày.
- Nội dung không mâu thuẫn với tên đề tài/phạm vi.
- Các quyết định không chắc chắn được đánh dấu, không viết như đã chốt.
- Có nguồn hoặc rationale cho claim quan trọng.
- Có checklist và người duyệt xác nhận.
- Thay đổi ảnh hưởng file khác đã cập nhật decision log.

## 2. Definition of Done cho W1

- CEFR familiarisation hoàn tất.
- Construct và sáu tiêu chí được Pedagogy Lab duyệt.
- Production/Interaction/Mediation boundary rõ.
- Scope, intended use, population và non-claims rõ.
- 2 rater + 1 adjudicator được xác nhận dự kiến.
- DMP/consent requirements đủ để nộp ethics.
- ALTE Grid bản nháp hoàn tất.
- Validation argument map hoàn tất.
- Chương 1 hoàn thành bản 1.
- G1 không còn item BLOCKING.

## 3. Definition of Done cho từng nhóm đầu ra

| Nhóm | Điều kiện |
| --- | --- |
| Construct | Có định nghĩa, exclusions, evidence map, confounders |
| Task | Có purpose, discourse, response, interaction và coverage |
| Human rating | Có owner rubric, rater independence, adjudication plan |
| Data | Có ID, PII separation, access, retention, deletion |
| Research | RQ có data, analysis, uncertainty và limitation |
| Governance | Decision log, RACI, G1 minutes và versioning |

## 3.1. Invariant test bắt buộc trước khi gọi implementation DONE

- Không một `speaker_id` xuất hiện ở nhiều split/fold trong cùng evaluation run.
- Mọi artifact có đủ version/provenance phù hợp; mọi `evidence_id` tham chiếu tới evidence tồn tại.
- Interaction thiếu bằng chứng giữ `null`/`insufficient_evidence`, không biến thành điểm giả.
- `teacher_verified` không tự bật; mặc định `false` và cần review audit record.
- Lỗi QC/ASR trả status/reason code, không bị nuốt để tạo band mặc định.
- Baseline/fusion dùng cùng fold manifest, preprocessing và seed; confirmation set chưa từng được dùng để tune.
- Test/log/fixture không chứa audio người thật, transcript/PII, secret hoặc credential.

## 4. Không được đánh dấu DONE khi

- Chỉ có nội dung do AI sinh nhưng chưa có người chuyên môn duyệt.
- File còn `[Điền]` ở trường blocking.
- Có claim “CEFR-certified”.
- Rubric tự chấm Interaction từ monologue.
- Chưa có consent/data plan nhưng đã tuyển người.
- Chỉ có desk research nhưng ghi sorting/quiz/workshop/G1 là đã hoàn thành.
- Precision/sample-size claim chưa có script/config/output tái lập.
- Còn conflict C001-C004 hoặc câu hỏi `BLOCKING` chưa có quyết định/owner/deadline.

## 5. Trạng thái W1 hiện tại

**NOT DONE / G1 NOT HELD.** Desk research và draft artifact đã được dựng lại, nhưng còn thiếu hoạt động con người, sign-off, rater/adjudicator, retention/encryption cụ thể, thiết kế parallel-form và bằng chứng precision analysis. Không được đổi trạng thái này chỉ vì các file Markdown đã đầy nội dung.

## 6. Sign-off

| Vai trò | Họ tên | Xác nhận | Ngày |
| --- | --- | --- | --- |
| SV1 | [Điền] | [ ] | [ ] |
| SV2 | [Điền] | [ ] | [ ] |
| SV3 | [Điền] | [ ] | [ ] |
| GV Ngoại ngữ | [Điền] | [ ] | [ ] |
| GVHD | [Điền] | [ ] | [ ] |
