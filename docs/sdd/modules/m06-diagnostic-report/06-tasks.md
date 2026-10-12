# M06 — 06 Tasks (W2 task breakdown)

> **BẢN NHÁP W2 (v0.1, 25/09/2026).** Chuẩn bị theo yêu cầu chủ dự án; Phase 01 của M06 vẫn `DRAFT/PENDING`. Nội dung dưới đây chưa là Specification/Plan được duyệt và không cấp quyền phát prompt triển khai.

Task dưới đây là **bản nháp để review**, chưa phát prompt hoặc chuyển sang Antigravity. ID giữ ổn định để liên kết evidence sau này.

| Task ID / owner | FR/AC và Test ID | Phạm vi file dự kiến | Đầu ra kiểm chứng |
| --- | --- | --- | --- |
| M06-TASK-001 / Nguyên | M06-FR-001, M06-AC-001, M06-AC-002 · M06-TEST-001, M06-TEST-002, M06-TEST-003 | report evidence validator + tests | Không tạo comment nếu ref sai/thiếu |
| M06-TASK-002 / Nguyên | M06-FR-002, M06-AC-002, M06-AC-003 · M06-TEST-004, M06-TEST-006 | report builder + presentation contract | Chỉ overall + coverage; tách provisional/final, không band giả |
| M06-TASK-003 / Nguyên | M06-FR-002, M06-AC-002 · M06-TEST-005 | M07 integration W3, chưa phát prompt W2 | Duyệt thật mới đổi verification state |

## Handoff và điều kiện hoàn tất

- Mỗi task khi được duyệt phải có prompt file riêng trong `prompts/`, mã Prompt ID, phạm vi file, artifact versions, baseline/fingerprint, check và format raw report. Không ghi `SENT`/`DONE` trước khi có thao tác và evidence thật.
- Unit test bắt buộc cho logic có thể kiểm thử; integration/API/browser check theo Test Plan. Nếu test không áp dụng, giải thích tại task đã duyệt và dùng alternative evidence.
- Một task chỉ được đánh dấu hoàn thành sau actual diff, kết quả chạy thật, Code/Clean Code Review, Final Verification trên revision cuối và user verdict. Metric/test báo cáo phải gắn với lệnh chạy, revision và evidence của dự án.

**Trạng thái task tại 12/10/2026:** Validator/builder, report SQLite và persisted M07 callback có implementation/test. Fixture không là validation CEFR. [M06-W4-20261012](evidence/M06-W4-20261012.md) dẫn raw suite liên quan 127 passed / 3 skipped / 0 failed và source revision/working diff. Không task nào được ghi DONE/APPROVED thay người dùng. **Phase 05 verdict:** PENDING.
