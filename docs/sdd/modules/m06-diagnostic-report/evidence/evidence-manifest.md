# M06 — Evidence Manifest (danh mục bằng chứng)

**Hiện trạng 12/10/2026:** implementation hiện có tại revision `3b2d2b7`, kèm working fix M08 được Nguyên cho phép. Record [M06-W4-20261012](M06-W4-20261012.md) là nguồn technical verification hiện hành; formal/user verdict PENDING. Không có prompt Antigravity được phát trong lượt này.

## Evidence lịch sử — 28/09/2026

Snapshot dưới đây ghi trạng thái tại thời điểm direct implementation, trước khi source hiện hành vào Git. Báo cáo và hình W1 cấp dự án nằm ở docs/reports/week-01/ và docs/design/week-01/.

| Evidence ID | Prompt ID / Task ID | Phase | Base/Head revision, fingerprint | Loại / file hoặc link | Check và kết quả thực tế | Trạng thái |
| --- | --- | --- | --- | --- | --- | --- |
| M06-EVID-DIRECT-20260928 | M06-TASK-001/002/003 | Direct workspace evidence, không phải phase verdict | HEAD `db34379f96d439ace6d504b60c31bc01cab9a902`; fingerprint trong file evidence | [M06-EVID-DIRECT-20260928.md](M06-EVID-DIRECT-20260928.md) | Validator/builder/M07 integration fixture trong selected pytest; không có dữ liệu CEFR thực | TECHNICAL_EVIDENCE; USER_VERDICT_PENDING |

Lưu tại đây raw report của Antigravity, command output/test/coverage, ảnh browser QA và final verification khi phát sinh. File lớn có thể lưu ngoài Git nhưng phải có link ổn định, checksum và quyền truy cập cho người review. Mỗi evidence gắn đúng Prompt ID, Task ID, AC/Test ID và revision. Redact secret/PII/audio/transcript thật; không ghi PASS cho lệnh chưa chạy. Cập nhật 07-status.md trỏ tới evidence mới nhất.


## Current technical evidence — 12/10/2026

Snapshot 28/09 phía trên là lịch sử. Source hiện đã có trong Git; dùng record dưới đây cho W4-N4.

| Evidence ID | Task ID | Revision / loại | Check / status |
| --- | --- | --- | --- |
| [M06-W4-20261012](M06-W4-20261012.md) | M06-TASK-001/002/003; W4-N4 | `3b2d2b7` + working fix M08 được Nguyên cho phép; direct technical evidence | Suite liên quan 127 passed / 3 skipped / 0 failed, Ruff và refresh probe; USER_VERDICT_PENDING |
