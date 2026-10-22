# M09 — Tasks

**Version:** v0.1 · **STATUS:** DRAFT · chưa được phép implement theo trình tự phase. Code đã merge theo chỉ dẫn trực tiếp của user (xem [07-status](07-status.md)); bảng dưới ghi trạng thái code trên `main`, không phải verdict.

Chú giải: `CODE_MERGED` = code + test đã có trên `main`, review/acceptance của reviewer và user vẫn PENDING. `PARTIAL` = mới có một phần deliverable. `PENDING_OWNER` = phần thuộc module/owner khác, chờ owner xác nhận.

| Task ID | W5 owner task | Nội dung | Test bắt buộc | Dependency | Trạng thái (đồng bộ 21/10/2026) |
| --- | --- | --- | --- | --- | --- |
| M09-TASK-001 | W5-S01 | Domain models, LID, guards, reason policy | M09-TEST-001/002/009 | M03/M04 contract | CODE_MERGED — PR #40 (`532dda1`): `trust/contracts.py`, `trust/policy.py`; test `tests/trust/` |
| M09-TASK-002 | W5-S01 | Conformal loader/set và provenance | M09-TEST-003 | M05 artifact contract | CODE_MERGED — PR #40: `scoring/conformal.py`, `trust/service.py`; test `tests/scoring/test_conformal.py` |
| M09-TASK-003 | W5-S01 | Pipeline/report compatibility, retry | M09-TEST-004/005/007/008 | W5-T01 schema/job | CODE_MERGED — PR #40; test `tests/local/test_trust_integration.py`, `tests/api/test_trust_api.py` |
| M09-TASK-004 | W5-S01 | Calibration/refusal CLI và evidence | M09-TEST-006 | approved manifest/artifact | CODE_MERGED — PR #40: `tools/calibrate_conformal.py`, `tools/refusal_benchmark.py`; test `tests/tools/test_trust_tools.py`. Chưa chạy với artifact thật (W6-S03) |
| M09-TASK-005 | W5-N01, W5-N03 | Student/teacher trust states | M09-TEST-010 | TASK-003 payload freeze | PENDING_OWNER — UI ở PR #44/#46 (Nguyên xác nhận) |
| M09-TASK-006 | W5-T04 | Full integration, coverage và final evidence | full M09 + regression | TASK-001–005 | PENDING — SCRUM-68 (W5-T04) đang In Review |

Mỗi task phải ghi file được phép sửa, base/fingerprint, actual commands, coverage, changed-behavior matrix và evidence path khi Phase 05 được duyệt. Không gộp M09-TASK-001..004 thành một commit không review được.

Bằng chứng chạy lại test trên `main` `cabcc44`: [evidence/w6-s02-sync.md](evidence/w6-s02-sync.md).
