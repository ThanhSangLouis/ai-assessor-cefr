# M15 — Status

## Current W7 checkpoint — SCRUM-103 (2026-10-28)

- **Implementation:** M15 pages, static assets and all 14 E2E modules are on `feat/SCRUM-103-W7-N02-M15-trang-va-test-E2E`. The owner-authorized SCRUM-92 foundation PR #66 and SCRUM-102 PR #67 are already in the `main` base and are not part of this PR diff.
- **E2E:** all 79 cases passed on isolated MongoDB 7.0.45 with synthetic fixtures. The practice, lesson and billing server fixtures pass the pinned model directory into their child processes; the admin model-list endpoint now reads the folder through `artifacts.model_dir()`.
- **Focused checks:** 47 middleware/SCRUM-102 integration tests passed. M16 middleware regression coverage is 5 tests; M16 owner review remains pending.
- **Delivery:** the latest owner instruction overrides Jira's original `migrate/w7-repo-goc` target. [PR #68](https://github.com/thanglb2005/ai-assessor-cefr/pull/68) targets `main`; SCRUM-103 remains `In Progress` in Jira, and no owner acceptance or workflow verdict is recorded.
- **Acceptance:** M16 owner review remains pending. Merging PR #68 does not record owner acceptance or a Jira workflow verdict.

Evidence: [SCRUM-103 transfer checkpoint](reviews/implementation-transfer-scrum-103-2026-10-28.md).

| Mục | Trạng thái |
| --- | --- |
| Lifecycle | in_progress |
| Phase | Phase 07 — SCRUM-74–76 implementation and cross-role browser evidence ready for review; Phase 08 CI pending; Phase 09 owner acceptance pending |
| Requirement | v0.2 · chủ dự án APPROVED ngày 15/10/2026; [Phase 01 record](reviews/phase-01-review-2026-10-15.md) |
| Research mode | RUN · chủ dự án chọn cùng Phase 01 verdict |
| Research | v0.3 DRAFT; hai read-only lane W5-N01/N02 và W5-N03/N04; source `40907cc` static, browser `NOT_RUN` |
| Specification | v0.3; Phase 03 user verdict APPROVED ngày 15/10/2026; broader M15 Codex findings remain recorded and do not block the separately approved SCRUM-74–76 UI lane |
| Artifacts 04–06 | Test Plan v0.2 APPROVED, [Phase 04 review](reviews/phase-04-review-2026-10-15.md); Phase 05 APPROVED cho 001A và SCRUM-74–76/M15-TASK-003–006 |
| Implementation | READY_FOR_REVIEW — M15-TASK-003–006; no owner acceptance claimed |
| Prompt | Không phát Antigravity prompt cho SCRUM-74–76; triển khai UI trực tiếp theo chỉ dẫn chủ dự án |

UI work in the separately approved SCRUM-74–76 lane adapts only the current producer contracts. Unsupported API operations remain gated; this task verdict does not approve or change producer contracts.

## Current SCRUM-74–76 integration and verification — 16/10/2026

- Project-owner Phase 05 verdicts for SCRUM-74, SCRUM-75 and SCRUM-76 remain `APPROVED`; all four tasks `M15-TASK-003`–`006` are unblocked and `READY_FOR_REVIEW`. Phase 09 acceptance remains pending with the project owner.
- PR #39 is merged. PR #45 (SCRUM-74) and PR #46 (SCRUM-75) are in `main`; PR #47 carries SCRUM-76 and the final UI compatibility fixes. No producer/domain API was changed.
- The integrated cross-role browser run was executed against revision `0827b37b4f560d5087e1c57e9011ed79acc837dc`, using local synthetic fixtures only. Public, student, teacher and admin routes were checked at 360, 390, 768 and 1280 CSS pixels; the supported pages returned HTTP 200 with no horizontal document overflow. Student-to-admin access returned the expected 403. Per-role console results and route/API detail are in [integration report](evidence/scrum-74-76/integration-report.md) and [machine-readable results](evidence/scrum-74-76/integration-report.json).
- Admin study creation was exercised once as a local draft; it has zero participants and was not started. No rating batch was created because no eligible assessment responses exist. No audio was uploaded or submitted and no assessment score/CEFR outcome was generated.
- This browser run covers the supported route/responsive journeys. Audio submission/report-state matrices, reviewer conflict cases, keyboard/200% zoom/reduced-motion/print checks, complete semantic/security scans, and the separate W5-T04 clean-wheel gate are explicitly not claimed as passed; see the report. These remaining verification items do not reinstate a blocker on the approved UI transfer scope.

All dated status notes below record the state at their respective checkpoints and are retained as history. The current readiness state is the revision-specific summary above; later dated checkpoints below are also superseded by the integrated browser evidence.

Sau pull `d60e8a4` ngày 15/10/2026, backend SCRUM-65/66/67 đã merge. M11/M14 có handoff API/UI và technical task `READY FOR REVIEW`, nhưng approval module/reviewer vẫn PENDING; M10/M12/M13/M16 cũng chưa cấp contract được duyệt cho M15. Không suy backend browser smoke thành QA N01–N04.

Chủ dự án chọn hướng giải quyết M15-P03-01–05, duyệt Phase 03/04 và Phase 05 riêng cho 001A ngày 15/10/2026, và sẽ cung cấp contract đã duyệt cho các phần còn lại. [Phase 03 review](reviews/phase-03-review-2026-10-15.md) giữ nguyên Codex check `BLOCKED` và finding cần kiểm lại trước task integration. Quyết định giữ SDD: subagent Codex chỉ nghiên cứu/review đọc-only, Antigravity implementer. Prompt 001A phải có file/log/fingerprint trước khi giao; chưa phát prompt cho 001B/002–006.

## SCRUM-74 / `M15-TASK-003` — Phase 05 precheck (16/10/2026)

> Historical precheck; superseded by the project-owner verdict and implementation status below.

- Codex revalidated route, persistence, M10/M13 Status and W5-T01 records at SCRUM-74 branch HEAD `818fcbc46e62ee057fcbe980800e01f934d72179`.
- [Phase 05 readiness review](reviews/phase-05-readiness-scrum-74-2026-10-16.md): Codex result/recommendation `BLOCKED`; user verdict `PENDING`. Findings: M10 contract, M13 pronunciation/disclosure contract, W5-T01 persistence acceptance/G2, and M15 task-level file/API→DOM boundary.
- `M15-TASK-003` remains `BLOCKED`; tests/browser QA `NOT_RUN`; no implementation prompt issued. The existing Phase 05 approval covers `M15-TASK-001A` only.
- Resume after upstream owners record approved contract revisions and persistence handoff; then update the task Plan and obtain a new user Phase 05 verdict before creating a prompt.

## SCRUM-74 — superseding project-owner verdict (16/10/2026)

At that checkpoint, the project owner had confirmed Phase 05 `APPROVED` for SCRUM-74, SCRUM-75 and SCRUM-76, superseding the earlier pending-user-verdict finding. [Task-specific verdict and boundary](reviews/phase-05-implementation-authorization-scrum-74-2026-10-16.md) records the scope: port/adapt UI only and preserve backend/domain APIs. M10/M13 producer SDD statuses and acceptance remain owned by their modules. Implementation was `IN_PROGRESS` and integrated browser evidence was `NOT_RUN` at that time; the current result appears above.

At the pre-integration checkpoint, the UI had been transferred into the WSGI presentation package and browser requests consumed the current M10/M13 contracts. See the [SCRUM-74 implementation transfer record](reviews/implementation-transfer-scrum-74-2026-10-16.md). PR #39 later merged to `main` as `19b7ada`; no producer code was copied or changed. The single integrated E2E was `NOT_RUN` at that time.

At the pre-integration checkpoint, the project owner had also confirmed Phase 05 `APPROVED` for SCRUM-75 and SCRUM-76 and authorized UI-only port/adaptation with producer APIs preserved. SCRUM-75 used available M07/M12 review/rating routes and the M10 authoring APIs from merged PR #39. Path discovery had no list endpoint, and insights exposed no cohort aggregate; those UI views used known browser-local IDs and per-owner data. SCRUM-76 adapted current admin study, rating and read-only billing routes. Unsupported M11/billing mutations remained gated. `M15-TASK-004/005/006` were `IN_PROGRESS`; acceptance and integrated E2E were `NOT_RUN` at that checkpoint.

## Current integration status

The dated implementation notes above are superseded by the revision-specific result in `evidence/scrum-74-76/integration-report.md`. SCRUM-74/75/76 are unblocked and ready for independent review; final owner acceptance is still pending. `M15-TASK-007` remains a separate W5-T04 task owned by Thắng.
