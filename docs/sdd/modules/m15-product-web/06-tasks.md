# M15 — Tasks — W5-N01

- **SCOPE ID / ROOT:** M15 / `docs/sdd/modules/m15-product-web/`
- **VERSION / STATUS:** v0.2 / APPROVED · Phase 05 `APPROVED`, 2026-10-16
- **PLAN:** [05-plan.md](05-plan.md) v0.2 APPROVED Phase 05
- **APPROVED INPUTS:** Requirement v0.2 Phase 01; Specification v0.2 Phase 03; Test Plan v0.2 Phase 04.
- **OWNER:** Nguyên for W5-N01; Thắng owns shared W5-T04/M16 package gate.
- **USER VERDICT PHASE 05:** `APPROVED` — project owner confirmed in chat on 2026-10-16 that the oral meeting approved all listed dependencies and N01 file/package boundaries.

## 1. Task register

| Task ID | W5 | Deliverable | Owner | Test IDs | Status |
| --- | --- | --- | --- | --- | --- |
| M15-TASK-001 | W5-N01 | Design system/shell/navigation and public `/`, `/bands` pages | Nguyên | M15-TEST-001/002/008/009/012/014 | IN_PROGRESS |
| M11-TASK-006 | W5-N01 | Login/account/consent UI consumer | Nguyên, per Week 05 task assignment | M15-TEST-002/013; M11-TEST-007/009 | IN_PROGRESS — consumer UI/routes present; acceptance NOT_RUN |
| M15-TASK-002 | W5-N01 | Assessment input/status/report/history/audio consumer flow | Nguyên | M15-TEST-002–004/008/009/012 | IN_PROGRESS — flow present; producer/browser acceptance NOT_RUN |
| M13-TASK-005 | W5-N01 | Student progress/pronunciation/study evidence blocks | Nguyên, per Week 05 task assignment | M15-TEST-004/012; M13-TEST-004/011 | IN_PROGRESS — progress shell and unavailable state present; runtime has no student M13 payload; acceptance NOT_RUN |
| M15-TASK-007 | W5-T04 | Package and final integrated browser gate | Thắng | M15-TEST-010/011 + required integrated regression | TODO — separate W5-T04 owner handoff after N01 implementation |
| M15-TASK-003 | W5-N02 | Practice/lesson/review/result/progress UI | Future task owner | M15-TEST-005 | BLOCKED — outside W5-N01; no Phase 05 review here |
| M15-TASK-004 | W5-N03 | Teacher/review/blind/authoring UI | Future task owner | M15-TEST-006 | BLOCKED — outside W5-N01; no Phase 05 review here |
| M15-TASK-005/006 | W5-N04 | Admin UI and full cross-role regression | Future task owner | M15-TEST-007 and later full matrix | BLOCKED — outside W5-N01; no Phase 05 review here |

## 2. Task contracts

### M15-TASK-001 — Shell and public pages

- **Owner / reviewers:** Nguyên / Thắng (route, security, asset handoff), Sang (CEFR/AI wording).
- **Scope:** shared N01 shell/navigation, design tokens and reusable visible states; render landing `/` and bands `/bands` with approved evidence-limit wording.
- **Allowed file area:** `src/aicefr/portal/templates.py`, public render functions in `src/aicefr/api/templates.py`, N01 static assets under `src/aicefr/api/static/`, and new UI tests under `tests/web/`. Route registration in `src/aicefr/api/wsgi.py` is shared and requires a W5-T01 owner lock before edit.
- **Dependencies:** Phase 05 user verdict; owner-approved route/file lock; local font/art provenance and package-data handoff from M16/W5-T01; no numerical band thresholds or unapproved model claim.
- **Acceptance:** M15-TEST-001/002/008/009/012/014; relevant M15-N01-AC-001/003/007/009 behavior. M15-TEST-010/M15-N01-AC-010 package result remains with M15-TASK-007.
- **Status:** `IN_PROGRESS`; project owner confirmed route/static/file and local asset gates approved in the oral meeting on 2026-10-16.

### M11-TASK-006 — Login, account and consent UI

- **Owner / reviewer:** Nguyên via W5-N01 / Thắng as M11 producer/contract owner.
- **Scope:** login state, account route `/student/account?tab=profile|security|activity|data`, consent accept/withdraw states, session and Google configured/disabled states. No backend auth or consent policy changes.
- **Allowed file area:** N01/M11 consumer templates in `src/aicefr/api/templates.py`, tab/navigation presentation in `src/aicefr/portal/templates.py` and `src/aicefr/portal/router.py`, and focused tests under `tests/web/`. Shared route registry changes require the owner lock in M15-TASK-001.
- **Dependencies:** M11 owner-approved `ui-handoff.md` version and request/response/error/auth matrix; W5-T02 backend integration examples; approved Phase 05; synthetic configured/disabled fixtures.
- **Acceptance:** M15-TEST-002/013 plus M11-TEST-007/009 as applicable; `M15-N01-AC-002/004/009`.
- **Status:** `IN_PROGRESS`; account tabs/actions consume existing M11 services and routes. Project owner confirms the selected SCRUM-66 UI handoff contract was approved in the oral meeting. M11's formal SDD phase rows remain unchanged; tests are `NOT_RUN`.

### M15-TASK-002 — Student assessment, report and history

- **Owner / reviewers:** Nguyên / Thắng (auth/API and owner boundary), Sang (M09 trust/report disclosure).
- **Scope:** 30-second preparation/skip, supported record/upload, preview/rerecord, submit/status recovery, progress/history/report/audio evidence navigation. Account and consent UI belong to M11-TASK-006; M13 evidence blocks belong to M13-TASK-005.
- **Allowed file area:** student page renderers in `src/aicefr/api/templates.py`, route consumer integration in `src/aicefr/portal/router.py` and `src/aicefr/api/wsgi.py` after route-owner lock, N01 static behavior and `tests/web/`. No changes to auth, QC, scoring, report generation or storage services.
- **Dependencies:** approved M01 task/response/status/idempotency examples; approved M02 media/QC behavior; M06 report/history/audio contract; M07 teacher-review state mapped into the M06 report; M09 trust payload freeze; M11 account/session/consent contract; M08 role/consent/owner authorization boundary; approved Phase 05. The project owner confirmed orally on 2026-10-16 that M07 supplies the teacher-review state in the M06 report and M08 supplies the identity/consent/owner access boundary. Keep the approved Requirement/Specification text unchanged; M08 does not own the teacher decision.
- **Acceptance:** M15-TEST-002–004/008/009/012; `M15-N01-AC-002/005/006/007/009`. Retry behavior is not complete until duplicate-safety has producer evidence.
- **Status:** `IN_PROGRESS`; assessment input/status/report/history/audio consumer flow is present. User confirms the direct producer contracts, M06/M07 mapping, M08 boundary and route edit window were approved in the oral meeting. Duplicate-safety and integrated browser evidence remain `NOT_RUN`.

### M13-TASK-005 — Student learning evidence blocks

- **Owner / reviewers:** Nguyên via W5-N01 / Sang as M13 data/evidence owner; Thắng reviews access boundary.
- **Scope:** display only approved progress/pronunciation/study fields; preserve source, eligibility, sample/threshold, `NOT_EVALUATED` and insufficient-data states. No computation, study assignment or cohort access logic in UI.
- **Allowed file area:** student progress renderers and N01 styles in `src/aicefr/api/templates.py` and `src/aicefr/api/static/`, plus `tests/web/`. Do not edit `src/aicefr/learning/`, research/measurement code, schemas or repositories.
- **Dependencies:** M13 owner-approved student DTO/eligibility/payload examples and M13-TEST-004/011 evidence; applicable consent and authorization contracts; approved Phase 05.
- **Acceptance:** M15-TEST-004/012, M13-TEST-004/011 and `M15-N01-AC-006/009`.
- **Status:** `IN_PROGRESS`; the progress page preserves current assessment data and shows an explicit no-payload state for M13, without inventing metrics. The runtime has no student M13 payload route/service, so evidence-backed M13 values are not integrated. Project owner confirms the payload/eligibility contract was approved orally; M13's formal SDD phase rows remain unchanged and producer tests are `NOT_RUN`.

### M15-TASK-007 — Shared package/integrated browser gate

- **Owner / reviewer:** Thắng via W5-T04/M16 / Nguyên reviews N01 integration and evidence.
- **Scope:** package-data/clean-wheel integration and final N01 browser result on one integrated revision; it is not a parallel N01 source task.
- **Allowed file area:** W5-T04-owned `pyproject.toml`, package/CI/run integration and final harness orchestration; N01 browser harness/evidence inputs are authored by Nguyên under the allowed task window.
- **Dependencies:** all applicable module tasks ready for integration, M16 owner-approved asset/package contract and N01 producer contracts closed.
- **Acceptance:** M15-TEST-010/011 and required full integrated regression; M16/W5-T04 records the joint package verdict.
- **Status:** `TODO` for the separate W5-T04 handoff; final package/browser gate is not yet run.

## 3. Work order and task state rules

1. Resolve Plan section 5 producer and shared-file gates; retain owner review evidence in the relevant module or cross-link it here.
2. After Phase 05 user verdict and task-specific DoR, change exactly one ready task to `TODO`, then `IN_PROGRESS`; issue one task prompt/change window at a time.
3. Implement and review M15-TASK-001 before shared shell work in later tasks; then M11-TASK-006; then M15-TASK-002; then M13-TASK-005. If actual API ownership requires a different order, update this plan and re-review the affected task before code.
4. Hand off N01 to W5-T04/M15-TASK-007 for clean-wheel/browser regression after producer task integration.
5. A task is `DONE` only with scoped actual diff, required tests/evidence, producer integration where applicable, no unresolved `BLOCKER/MAJOR`, and its Test Plan assertions met. A mock/fixture-only task cannot close a server boundary.

Phase 05 is approved based on the project owner's oral-meeting confirmation recorded in the Plan/review. Source implementation is in progress across N01 tasks 001, M11-006, 002 and M13-005, following the approved order. Their acceptance checks are `NOT_RUN`; no implementation task is marked `DONE`. The approval confirms dependency contracts/file ownership and does not change other modules' formal SDD phases. Deferred N02–N04 tasks remain outside W5-N01.
