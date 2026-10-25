# M11 — Tasks

**Version:** v0.1 · **STATUS:** DRAFT.

| Task | W5 | Deliverable | Tests | Status |
| --- | --- | --- | --- | --- |
| M11-TASK-001 | W5-T01/T02 | migration + profile/session repositories | 001/003/010 | IN_REVIEW — PR #36/#37; SCRUM-66 backend evidence; module verdict PENDING |
| M11-TASK-002 | W5-T02 | password/temp/lockout/session services | 002/003 | IN_REVIEW — PR #37; SCRUM-66 backend evidence; module verdict PENDING |
| M11-TASK-003 | W5-T02 | admin account atomic operations/audit | 004/005 | IN_REVIEW — PR #37; SCRUM-66 backend evidence; module verdict PENDING |
| M11-TASK-004 | W5-T02 | Google PKCE/signed flow/config | 006/007 | IN_REVIEW — PR #37; live OAuth NOT_RUN; module verdict PENDING |
| M11-TASK-005 | W5-T02 | consent propagation/data contract | 008 | IN_REVIEW — PR #37 + consent-v2/audio-storage extension in SCRUM-87 PR #50 (`ff6d36e`); module verdict PENDING |
| M11-TASK-006 | W5-N01 | account/public auth UI | 007/009 | IN_REVIEW — consumer code in PR #44; M11 owner review/acceptance PENDING |
| M11-TASK-007 | W5-N04 | admin account/config UI | 004–007/009 | IN_REVIEW — consumer surfaces in PR #47; action/security review PENDING |
| M11-TASK-008 | W5-T04 | auth full regression/evidence | full module | BLOCKED — final integrated W5-T04 gate not complete |

Mỗi task phải bàn giao request/response examples, reason codes, authorization matrix và audit/redaction evidence; không chỉ screenshot happy path.

Trạng thái task-local phản ánh code/evidence đã merge; module vẫn `DRAFT/PENDING`. Các dòng này không phê duyệt phase SDD hoặc đóng Jira.

W6-T03 sync baseline: `main` `f540cb88643214cd1d4444f2dd0d81f4463119fa`; current consent screen/PDF use `consent-v2`. SCRUM-87 Jira remains `Testing`; review module/owner and full TASK-008 gate remain open.

## Tiến độ backend theo giao việc SCRUM-66

T01 schema đã có từ PR #36 (main `840efb9`). T02.1–T02.7 đã implement/verified trong product commit `311b029`; [review và gate](evidence/scrum-66/review.md). M11-TASK-001–005 phần backend: READY FOR REVIEW. M11-TASK-006/007 (N01/N04) chờ UI consumer sử dụng [handoff](evidence/scrum-66/ui-handoff.md). TASK-008 full W5 integration thuộc T04. Không coi bảng kế hoạch DRAFT là approval hoặc user acceptance.
