# M15 — Status

| Mục | Trạng thái |
| --- | --- |
| Lifecycle | proposed |
| Phase | 06 — chuẩn bị handoff `M15-TASK-001A`; producer contract/route vẫn là dependency cho integration task |
| Requirement | v0.2 · chủ dự án APPROVED ngày 15/10/2026; [Phase 01 record](reviews/phase-01-review-2026-10-15.md) |
| Research mode | RUN · chủ dự án chọn cùng Phase 01 verdict |
| Research | v0.3 DRAFT; hai read-only lane W5-N01/N02 và W5-N03/N04; source `40907cc` static, browser `NOT_RUN` |
| Specification | v0.3; Phase 03 user verdict APPROVED ngày 15/10/2026; Codex check khi review vẫn BLOCKED |
| Artifacts 04–06 | Test Plan v0.2 APPROVED, [Phase 04 review](reviews/phase-04-review-2026-10-15.md); Plan/Tasks v0.2 APPROVED chỉ cho 001A, [Phase 05 review](reviews/phase-05-review-2026-10-15.md) |
| Implementation | NOT_STARTED |
| Prompt | `M15-W5-N01-001A-A1` đang chuẩn bị; chưa giao Antigravity |

UI work bắt đầu sau khi backend payload/error/authorization contract tương ứng freeze; mock có thể dùng cho component test nhưng không đủ để đánh dấu task DONE.

Sau pull `d60e8a4` ngày 15/10/2026, backend SCRUM-65/66/67 đã merge. M11/M14 có handoff API/UI và technical task `READY FOR REVIEW`, nhưng approval module/reviewer vẫn PENDING; M10/M12/M13/M16 cũng chưa cấp contract được duyệt cho M15. Không suy backend browser smoke thành QA N01–N04.

Chủ dự án chọn hướng giải quyết M15-P03-01–05, duyệt Phase 03/04 và Phase 05 riêng cho 001A ngày 15/10/2026, và sẽ cung cấp contract đã duyệt cho các phần còn lại. [Phase 03 review](reviews/phase-03-review-2026-10-15.md) giữ nguyên Codex check `BLOCKED` và finding cần kiểm lại trước task integration. Quyết định giữ SDD: subagent Codex chỉ nghiên cứu/review đọc-only, Antigravity implementer. Prompt 001A phải có file/log/fingerprint trước khi giao; chưa phát prompt cho 001B/002–006.

## SCRUM-74 / `M15-TASK-003` — Phase 05 precheck (16/10/2026)

- Codex revalidated route, persistence, M10/M13 Status and W5-T01 records at SCRUM-74 branch HEAD `818fcbc46e62ee057fcbe980800e01f934d72179`.
- [Phase 05 readiness review](reviews/phase-05-readiness-scrum-74-2026-10-16.md): Codex result/recommendation `BLOCKED`; user verdict `PENDING`. Findings: M10 contract, M13 pronunciation/disclosure contract, W5-T01 persistence acceptance/G2, and M15 task-level file/API→DOM boundary.
- `M15-TASK-003` remains `BLOCKED`; tests/browser QA `NOT_RUN`; no implementation prompt issued. The existing Phase 05 approval covers `M15-TASK-001A` only.
- Resume after upstream owners record approved contract revisions and persistence handoff; then update the task Plan and obtain a new user Phase 05 verdict before creating a prompt.

## SCRUM-74 — superseding project-owner verdict (16/10/2026)

The project owner later confirmed in this conversation that Phase 05 is `APPROVED` for SCRUM-74, SCRUM-75 and SCRUM-76, superseding the earlier pending-user-verdict finding for this task. [Task-specific verdict and boundary](reviews/phase-05-implementation-authorization-scrum-74-2026-10-16.md) records the exact scope: port/adapt UI only and preserve backend/domain APIs. M10/M13 producer SDD statuses and acceptance remain owned by their modules. SCRUM-74 implementation is now `IN_PROGRESS`; acceptance and browser/E2E evidence remain `NOT_RUN` until the integrated revision is available.

The completed source UI has been transferred into the WSGI presentation package and browser requests are being adapted to the existing M10/M13 contracts. See the [SCRUM-74 implementation transfer record](reviews/implementation-transfer-scrum-74-2026-10-16.md). PR #39 remains an upstream dependency; no producer code was copied or changed. The single integrated E2E is still `NOT_RUN` and is reserved until SCRUM-74–76 and the dependency are together.
