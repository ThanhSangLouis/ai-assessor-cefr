# M15 — Plan — W5-N01

- **SCOPE ID / TYPE / ROOT:** M15 / module / `docs/sdd/modules/m15-product-web/`
- **ACTIVE TASK:** W5-N01
- **OWNER:** Nguyên
- **REVIEWERS:** Thắng — auth/API/shared route and data boundary; Sang — CEFR/AI wording and evidence disclosure.
- **VERSION / STATUS:** v0.2 / APPROVED · PHASE 05 `APPROVED`, 2026-10-16
- **BASE REVISION:** `d60e8a4b9f63a0b0259ada8971e23bafdb1df041` (`main`)
- **APPROVED INPUTS:** Requirement v0.2 Phase 01; Research v0.2 + Specification v0.2 Phase 03; Test Plan v0.2 Phase 04.
- **SCOPE DECISION:** Project owner retained the full W5-N01 scope on 2026-10-16; no narrowing requested.
- **USER VERDICT PHASE 05:** `APPROVED` — project owner confirmed in chat on 2026-10-16 that the owner contracts and file/package gates were approved in the oral meeting.

## 1. Goal and scope boundary

Deliver the W5-N01 design system, public pages, account/consent surfaces and student assessment journey defined by Requirement v0.2, Specification v0.2 and Test Plan v0.2. The accepted implementation boundary is server-rendered HTML/CSS with small browser JavaScript. The accepted public/account routes are `/`, `/bands` and `/student/account?tab=...`.

M15 renders state supplied by approved producer contracts. It does not implement authentication, consent policy, authorization, audio QC, scoring, report/evidence computation, statistics, database schema or billing. W5-N02–N04 and M15 tasks 003–006 remain outside this plan. M15-TASK-007 is the shared W5-T04 integration/package gate, owned by Thắng.

The Phase 04 verdict permits preparation of this plan. It does not approve M11/M01/M02/M06/M08/M09/M13/M16 contracts, alter their ownership or authorize edits to their source/SDD.

## 2. Delivery sequence

| Step | Work | Exit condition |
| --- | --- | --- |
| 0 — Contract and ownership handoff | Obtain producer-reviewed route/method/role/consent/error and payload examples for the applicable UI states; record route-registry/static-package file lock from W5-T01/T04 owners. | Every direct dependency used by the selected M15 task has an approved, versioned contract and an owner-approved file boundary. |
| 1 — Shared shell and public pages | M15-TASK-001: common navigation/tokens/components and public landing/bands pages; keep content within approved wording and local asset provenance. | M15-TEST-001/002/008/009/012/014 for public/shell states have actual evidence. |
| 2 — Identity/account consumer | M11-TASK-006 under W5-N01: login/account/consent UI against the reviewed M11 UI handoff. | M15-TEST-002/013 plus applicable M11 UI checks have actual evidence; no credential/token appears in DOM or client logs. |
| 3 — Assessment consumer | M15-TASK-002: preparation, record/upload, preview, submit, processing, report, history and audio navigation. | M15-TEST-002–004/008/009/012 pass against approved producer behavior; retry follows approved idempotency rules. |
| 4 — Student evidence consumer | M13-TASK-005 under W5-N01: approved student progress/pronunciation/study evidence blocks only. | M13 producer tests and M15-TEST-004/012 confirm eligibility, privacy and insufficient-data display. |
| 5 — Integrated package/browser gate | M15-TASK-007 under W5-T04, owned by Thắng; Nguyên supplies N01 asset inventory, route list and browser evidence inputs. | M15-TEST-010/011 and full in-scope browser matrix run on one final integrated revision; joint M16/W5-T04 gate is recorded. |

Steps 1–4 are serialized by the single W5-N01 owner. Shared templates/static routes are not edited concurrently by another task/agent. Step 5 is a separate W5-T04 owner handoff; it is not a second M15 implementation owner for N01.

## 3. Task-to-acceptance and test trace

| Task | Requirement / AC | Test Plan IDs | W5 owner and review |
| --- | --- | --- | --- |
| M15-TASK-001 | M15-N01-FR-001–003,008; M15-N01-AC-001,003,007,009 | M15-TEST-001/002/008/009/012/014 | Nguyên; Thắng reviews route/security and asset handoff; Sang reviews public claims. |
| M11-TASK-006 | M15-N01-FR-002,004; M15-N01-AC-002,004,009 | M15-TEST-002/013 and applicable M11 UI tests | Nguyên via W5-N01; Thắng owns/reviews identity API and contract. |
| M15-TASK-002 | M15-N01-FR-002,005,006; M15-N01-AC-002,005,006,009 | M15-TEST-002–004/008/009/012 | Nguyên; Thắng reviews auth/API; Sang reviews trust/evidence wording. |
| M13-TASK-005 | M15-N01-FR-006,007; M15-N01-AC-006,009 | M13-TEST-004/011 and M15-TEST-004/012 | Nguyên via W5-N01; Sang owns measurement/data eligibility contract. |
| M15-TASK-007 | M15-N01-FR-001,008,009; M15-N01-AC-001,007,008,010 | M15-TEST-010/011 plus all required integrated regressions | Thắng via W5-T04; Nguyên reviews N01 UI/evidence handoff. |

AC-003 and AC-010 are additionally reviewed at the shared copy/package gate; no package or browser result is credited before actual evidence exists. Tests 005–007 remain deferred to W5-N02–N04.

## 4. File ownership and implementation boundaries

### Nguyên — W5-N01/M15 UI consumer files

- Existing renderers/shared navigation: `src/aicefr/api/templates.py`, `src/aicefr/portal/templates.py`.
- Existing student route consumer: `src/aicefr/portal/router.py` and view integration in `src/aicefr/api/wsgi.py` only after the route-registry owner grants the W5-N01 change window.
- N01 local CSS/JS/SVG/font assets under `src/aicefr/api/static/`; asset files need local provenance/license metadata. Third-party network assets are excluded.
- Focused UI/template and route presentation tests under the planned `tests/web/` directory.
- Browser harness/report inputs for N01 under `scripts/qa/m15_n01_browser.py` and `docs/sdd/modules/m15-product-web/evidence/w5-n01/`.

The tasks run serially because renderer/router files overlap. Each prompt/change window must identify one task and one owner. `src/aicefr/api/wsgi.py` is a shared route registry: no edit until the W5-T01 owner confirms the lock and allowed hunk. If route wiring must instead be owned by W5-T01, that owner supplies the approved route and M15 consumes it.

### Shared or producer-owned files — no M15 write without owner handoff

- `pyproject.toml`, composition root, static package-data and clean-wheel/CI integration: Thắng/W5-T01 or W5-T04 (M16).
- `src/aicefr/auth/`, consent/session/account service, repositories and identity API contract: Thắng/W5-T02 (M11).
- Assessment/audio/report services, schemas, database/migrations and producer payloads: their M01/M02/M06/M08/M09/M13 owners.
- Rubric, CEFR mapping, statistical computation and band thresholds: owning domain modules; M15 only displays approved values and explanations.

## 5. Dependency and readiness register

| Dependency | Needed by | Current evidence/state | Readiness gate |
| --- | --- | --- | --- |
| W5-T01/M16 route registry, runtime/static serving and file lock | M15-TASK-001/002 | M16 formal SDD remains `DRAFT/PENDING`; project owner reports route/static ownership and N01 edit window approved in the oral meeting. | Approved for N01 files under this Plan; W5-T04 owns package integration and final clean-wheel gate. |
| M11 / W5-T02 identity UI contract | M11-TASK-006 and consent/account states | SCRUM-66 UI handoff is the selected technical base; M11 formal SDD remains `DRAFT/PENDING`; project owner reports the handoff contract approved in the oral meeting. | Use the approved handoff/version and route/method/DTO/error/auth matrix; Thắng owns M11 producer contract. |
| M01 assessment task/response/status/retry contract | M15-TASK-002 | M01 formal SDD remains `DRAFT/PENDING`; Nguyên is the documented owner; project owner reports the consumer contract approved in the oral meeting. | Use the approved task/response/status/error and duplicate-submit/idempotency behavior; Thắng reviews auth/authorization boundary. |
| M02 accepted audio/QC contract | M15-TASK-002 | M02 Phase 01/03/04/05 is approved; current approved contract is the source for format/QC behavior. | Confirm selected upload/record routes consume that contract unchanged; record producer test examples in the task prompt. |
| M06 report/history/audio contract | M15-TASK-002 | M06 formal SDD remains `DRAFT/PENDING`; Nguyên is the documented owner; project owner reports DTO/state behavior approved in the oral meeting. | Use the approved report/history/audio DTO, route/method/ownership/error and unavailable/retry behavior. |
| M09 student trust/refusal state | M15-TASK-002 | M09 formal SDD remains `DRAFT/PENDING`; project owner reports Sang's student-state/reason payload approval from the oral meeting. | Use the approved frozen trust/refusal payload and wording; do not infer additional evidence. |
| M13 learning evidence eligibility/payload | M13-TASK-005 | M13 formal SDD remains `DRAFT/PENDING`; project owner reports Sang's field/eligibility/threshold/insufficient-state approval from the oral meeting. | Render only the approved fields and eligibility/access boundary. |
| M07 teacher-review state in student report | M15-TASK-002 | M15 Specification requires provisional vs teacher-verified values; M06 Plan identifies M07 as the verification boundary. M07 owner Nguyên; formal SDD remains `DRAFT/PENDING`; project owner confirms the M06/M07 mapping was approved orally. | Treat M07 as the source of teacher-review state mapped into the M06 report DTO. M15 Requirement's optional M08 reference is resolved as M08 access control; do not change approved Requirement/Specification wording in this implementation. |
| M08 identity/consent/owner authorization boundary | M15-TASK-002 | M08 Phases 01/03/04/05 are approved; Thắng owns M08; project owner reports the cross-owner review by Nguyên and report-visibility application were approved orally. | Apply M08 authorization/consent/owner checks to report access. M08 does not own the teacher-review decision state. |
| M16 asset provenance/package inclusion | M15-TASK-001 and M15-TASK-007 | M16 formal SDD remains `DRAFT/PENDING`; project owner reports local asset provenance and N01 package-data ownership approved in the oral meeting. | Use only approved local asset sources; W5-T04/Thắng retains clean-wheel/package integration and final gate. |

Every row is a direct consumer dependency from the approved Specification/Test Plan or the Week 05 task map. The project owner reports the listed producer approvals and N01 file window were confirmed in an oral meeting; this Plan records that confirmation, without claiming formal approval of the other modules' SDD phases. W5-T04 still owns the final integrated package gate.

## 6. Required checks and evidence handoff

- Run commands from approved Test Plan v0.2 after implementation, replacing placeholders with task evidence paths. No command/result in this Plan is marked as already run.
- M15-TASK-001/002 and M11/M13 consumer tasks capture targeted pytest evidence; M15-TASK-007 runs the non-smoke regression, package and integrated browser checks on final revision.
- The browser run is loopback-only and uses synthetic fixtures; no production accounts, personal learner data or real audio are committed.
- Evidence under `docs/sdd/modules/m15-product-web/evidence/w5-n01/` records task ID, final revision, route, role/session/consent, viewport, assertion, screenshot SHA-256, console/network and API mismatch closure. Restricted or large artifacts follow the module manifest.
- Coverage follows Test Plan v0.2: report line/branch coverage for changed Python logic, inspect uncovered behavior and do not introduce a global threshold. HTML/CSS/browser behavior uses its specified alternative evidence.
- A package/build change is accepted only with W5-T04/M16 owner evidence; N01 screenshots do not close the wheel gate.

## 7. Risk, recovery and code-quality controls

| Risk | Control / recovery |
| --- | --- |
| Producer DTO/error semantics change during UI work | Stop the affected task; producer updates versioned examples/tests first; M15 rechecks its mapped tests and captures the new contract revision. |
| Shared route/static/package files are concurrently edited | Use one owner lock per file; pause N01 route/package changes until W5-T01/T04 completes its window; do not resolve by choosing an entire conflict side. |
| Submission times out after server commit | Never blind-resubmit; query approved status/idempotency contract and show recovery state. |
| Asset/license or external dependency is missing | Keep the asset out of the package and leave affected acceptance blocked until M16 approves a distributable local source. |
| UI reveals a forbidden field or owner data | Remove the field at the consumer and report the producer boundary finding; verify with synthetic canary fixtures before review. |

Templates must escape untrusted content, keep domain/authorization logic out of browser JavaScript, reuse existing dependency/runtime conventions and avoid broad cleanup. Roll back a task by reverting only its reviewed change set to the task base; preserve other worktree changes. Required lint/test/build commands remain those in Test Plan and current repo configuration.

## 8. Phase 05 readiness result

| Readiness check | Result | Reason |
| --- | --- | --- |
| Scope and FR/AC/Test trace | READY | Sections 1 and 3 retain approved N01 scope and map tasks to Test Plan IDs. |
| Runtime/file boundaries | READY FOR N01 | Project owner reports the route/static edit window approved; W5-T04 continues to own package/CI integration. |
| Producer route/payload/error/idempotency contracts | READY FOR N01 | Project owner reports M01/M06/M07/M09/M11/M13 contracts and the M08 authorization cross-review approved; formal SDD phases in those modules retain their recorded status. |
| Asset/license and clean-package handoff | READY FOR N01 | Project owner reports local provenance and package-data ownership approved; final clean-wheel evidence remains with W5-T04. |
| Task owner, file scope, evidence and recovery | READY | W5-N01 owner is Nguyên; W5-T04 package gate remains with Thắng; task evidence and boundaries are recorded. |

**Conclusion:** Phase 05 is `APPROVED` based on the project owner's confirmation on 2026-10-16 that the oral meeting approved the full-scope contracts, M06/M07 teacher-state mapping, M08 access boundary and N01 route/asset ownership. Implementation may start in the ordered task sequence. This Plan does not change Requirement v0.2 or other module SDD phase verdicts.
