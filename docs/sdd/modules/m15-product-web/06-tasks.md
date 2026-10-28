# M15 — Tasks

**Version:** v0.2 · **STATUS:** Phase 05 user verdict `APPROVED` cho `M15-TASK-001A`; project owner confirmed separate `APPROVED` verdicts for SCRUM-74/75/76 (`M15-TASK-003`–`006`) on 16/10/2026. See each task's boundary/evidence addendum; producer-module approval and acceptance remain separately owned.
**Owner triển khai UI:** Hoàng Nguyên; Codex lead/review; Antigravity implementer sau prompt hợp lệ. Mỗi task chỉ có một owner, một vùng file và dependency riêng. Các mã `W5-N01.1`… trong `docs/plan/week-05.md` vẫn là work package bắt buộc của task tuần.

| Task | W5 | Deliverable / trace | Readiness |
| --- | --- | --- | --- |
| `M15-TASK-001A` | W5-N01.1 một phần | semantic shell/tokens/states cho page hiện có; FR-001/008, AC-001/004 phần shell; TEST-001/008/009/012 | `IN_PROGRESS` — chuẩn bị prompt, chưa có implementation report |
| `M15-TASK-001B` | W5-N01.1–N01.3 | assets/font/package, nav, landing/login/bands/consent/account; TEST-001/002/008–012 | `BLOCKED` — route/asset owner và M11 contract |
| `M15-TASK-002` | W5-N01.4–N01.7 | record/upload/preparation/progress/report/history; TEST-002–004/008/012 | `BLOCKED` — M01/M06/M09/M13 contract |
| `M15-TASK-003` | W5-N02.1–N02.6 | practice/lesson/review/result/progress; TEST-005/008/012 | `READY_FOR_REVIEW` — user Phase 05 verdict `APPROVED`; supported practice/lesson/progress routes exercised at 360/390/768/1280; no audio or assessment submitted; producer APIs preserved |
| `M15-TASK-004` | W5-N03.1–N03.6 | review/stats/blind/teach/insights; TEST-006/008/012 | `READY_FOR_REVIEW` — current M07/M12 and M10 APIs integrated; path view and per-owner insights verified; no path-list/cohort-insights API; conflict/blind-submit cases remain untested |
| `M15-TASK-005` | W5-N04.1–N04.5 | admin account/data/rating/study/billing; TEST-007/008/012 | `READY_FOR_REVIEW` — admin routes/responsive states verified; one synthetic local draft created/opened; billing read-only; no eligible ratings or sensitive admin mutation exercised |
| `M15-TASK-006` | W5-N04.6–N04.7 | full cross-role browser/a11y/motion/evidence; TEST-001–012 | `READY_FOR_REVIEW` — integrated role/route viewport matrix and expected student 403 recorded in [E2E evidence](evidence/scrum-74-76/integration-report.md); test-plan cases outside this run remain explicit `NOT_RUN` |
| `M15-TASK-007` | W5-T04 | final package/clean-wheel/integrated browser gate; TEST-010/011 + full | `BLOCKED`; owner Thắng, không nằm trong prompt Nguyên |

The project owner’s Phase 05 approval unblocks SCRUM-74/75/76 (`M15-TASK-003`–`006`) for the scoped UI adaptation. They are ready for independent review; remaining API/policy limitations are surfaced in the UI and report, not recorded as blockers. Phase 09 owner acceptance remains open.

## `SCRUM-103` / W7-N02 — transfer M15 pages and E2E (2026-10-28)

- **Jira scope:** transfer `services/web` (`pages`, `bff`), all `api/templates` and `api/static` assets, and `tests/e2e`; target 79/79 E2E on MongoDB 7 and a PR into `migrate/w7-repo-goc`.
- **Source:** `ThanhSangLouis/ai-assessor-cefr@0853c951e796b299d81dc363c3e0e20616c4e631`.
- **Transferred on:** `feat/SCRUM-103-W7-N02-M15-trang-va-test-E2E`, originally based on `migrate/w7-repo-goc` at `1abd17f0f4ac40bdfe78f8a21672fd302eac7fe0`; the PR branch is now based on `main` at `e840f5f39a58739f5a11b9ecdb9c4c3db37572eb`.
- **Included:** `services/web`, `api/web.py`, `api/main.py` (single-process E2E app), templates, static assets and all 14 E2E modules. Existing project consent PDF and other target-only files were preserved.
- **Verification:** Ruff and Python compilation passed; 47 focused middleware/SCRUM-102 integration tests passed; all 79 E2E cases passed on isolated MongoDB 7.0.45 using synthetic model fixtures. See [transfer checkpoint](reviews/implementation-transfer-scrum-103-2026-10-28.md) and [M16 middleware evidence](../m16-monolith-runtime/evidence/scrum-103-middleware-integration.md).
- **Integration:** after explicit owner authorization, SCRUM-92 foundation PR #66 and SCRUM-102 PR #67 were integrated and are already present in `main`; neither dependency is part of this PR's diff. Integration exposed and fixed the transferred model-list endpoint's import of a nonexistent `MODEL_DIR` symbol; it now uses `artifacts.model_dir()`.
- **State:** implementation and E2E verification are `READY_FOR_REVIEW`; M16 owner review remains pending. Jira remains `In Progress`; no owner acceptance or Jira verdict is recorded.
- **Delivery direction:** the latest owner instruction sets `main` as the PR target, overriding Jira's original `migrate/w7-repo-goc` target. Jira remains `In Progress` and no owner acceptance is recorded.

## `M15-TASK-001A` — Phase 05 readiness candidate

- **Objective:** semantic shell/tokens/state styling cho các page hiện hữu, không đổi URL, auth, payload hoặc business copy. Kết quả xem được trên local HTML tại 1280×800 và 390×844; skip link/main landmark/focus/contrast/light-dark/reduced motion/print có assertion.
- **One owner:** Hoàng Nguyên. **Implementer:** Antigravity sau Phase 05 user verdict. **Review:** Codex actual diff/tests; Thắng kiểm impact auth/runtime, Sang kiểm claim/wording nếu có thay đổi text. Trước khi sửa shared renderer, thông báo owner liên quan và xác nhận source lock.
- **Allowed files:** `src/aicefr/api/templates.py`, `tests/local/test_templates_mobile.py`, test mới dưới `tests/local/` và một script QA M15 riêng dưới `scripts/qa/` nếu cần. Không sửa `src/aicefr/api/wsgi.py`, `src/aicefr/portal/templates.py`, `pyproject.toml`, API/service/storage/SDD khác; nếu cần thì báo `BLOCKED` với diff đề xuất.
- **Input:** Specification v0.3 §§Design tokens/components, Layout/navigation, Assets/motion; Test Plan v0.2 M15-TEST-001/008/009/012; hiện trạng `_document`/`LOCAL_CSS` ở `api/templates.py`. Không phụ thuộc producer contract mới vì không đổi route/role/nav.
- **Expected output:** diff nhỏ có Task ID; targeted/related pytest + lint/format + non-smoke regression; coverage line/branch và critical uncovered branches; browser result JSON ở desktop/mobile với focus/overflow/theme/reduced-motion/print, screenshot SHA-256, console/network/external summary; raw report đúng prompt. Checks chưa chạy phải là `NOT_RUN`/`VERIFICATION_FAILED`, không suy từ code.
- **Done boundary:** chỉ `M15-TASK-001A` có thể qua review/verification. Parent W5-N01.1/W5-N01/M15 chưa `DONE`: Roboto/assets/nav/API/journey và full browser matrix còn trong 001B/002–006. Không dùng prompt 001A để sửa các task khác.

## `M15-TASK-005/006` — SCRUM-76 admin UI and cross-role browser run

- **Owner:** Hoàng Nguyên. **Scope:** transfer/adapt the admin overview, M12 rating batches, M13 study management, and M14 billing presentation in `src/aicefr/api/`; preserve backend/domain APIs and existing role checks.
- **Current contracts:** study create/start/close/report/export are available; there is no study-list endpoint, so the page stores known IDs in browser storage and supports opening a known ID. Billing is read-only. Temporary-password receipt and unsupported billing mutations stay gated. See the [SCRUM-76 transfer record](reviews/implementation-transfer-scrum-76-2026-10-16.md).
- **Acceptance:** M15-TEST-007/008/012 for task 005 and the supported cross-role/regression matrix for task 006, including no student-only badge request from teacher/admin pages. The integrated browser run is recorded at [revision 0827b37](evidence/scrum-74-76/integration-report.md), with role/route/viewport results, screenshot hashes, console/network summary, and synthetic fixture scope. It is evidence for review, not an owner verdict.
- **Status:** `READY_FOR_REVIEW`, unblocked by the owner’s Phase 05 verdict. Phase 09 acceptance remains pending; cases not run are enumerated in the report.
