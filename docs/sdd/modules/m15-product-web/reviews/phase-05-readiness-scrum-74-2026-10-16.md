# Phase 05 — Readiness Review: SCRUM-74 / M15-TASK-003

**PHASE RECORD ID:** `M15-TASK-003-05-A1`
**SCOPE ID/TYPE/ROOT:** `M15-TASK-003` / UI integration task / `docs/sdd/modules/m15-product-web/`
**SUBJECT:** Plan & Task Readiness v0.2 candidate for `W5-N02.1–N02.6`
**BASE/HEAD REVISION:** `818fcbc46e62ee057fcbe980800e01f934d72179` (branch `feat/SCRUM-74-W5-N02-Practice-lesson-progress-achievement-pronunciation-UI`; clean at review entry)
**WORKSPACE FINGERPRINT:** `N/A` — pre-prompt Phase 05 review; no implementation/source changes. The pinned clean HEAD is the reviewed revision.
**FINGERPRINT ALGORITHM / METADATA / EXCLUSIONS:** `N/A` — no prompt is ready or issued.

## Phạm vi kiểm tra

Đối chiếu `M15-FR-005`, `M15-AC-004/005`, `M15-TEST-005/008/012`, `M15-TASK-003`, các package `W5-N02.1–N02.6`, producer contracts M10/M13 và persistence/API của W5-T01. Đây là review readiness; không sửa source, không chạy test/browser QA, không tạo prompt và không ghi verdict thay chủ dự án hay owner module.

## Kết quả tự review của Codex

| Check | Kết quả | Bằng chứng / ghi chú |
| --- | --- | --- |
| Trace `FR → AC → Test → Task` | `PASS` cho traceability | M15 Requirement v0.2, Specification v0.3 §Traceability, Test Plan v0.2 và `06-tasks.md` nối `FR-005 → AC-004/005 → TEST-005/008/012 → M15-TASK-003`; Week 5 phân rã thành sáu package. |
| Scope và owner | `PASS` cho phân công ở mức kế hoạch | Week 5 §9.3 giao UI cho Nguyên; W5-S02/S03 cho Sang; W5-T01 cho Thắng. Phân công chưa xác định được source lock cụ thể vì API/page boundary còn thiếu. |
| M10 producer contract | `BLOCKED` | M10 Status: Phase 01, Requirement v0.1 `DRAFT/PENDING`; API/payload, enum, lifecycle, permission và error contract chưa được freeze. |
| M13 pronunciation contract | `BLOCKED` | M13 Status: Phase 01, Requirement v0.1 `DRAFT/PENDING`; chưa có owner-approved metric payload, source/`n`, threshold, insufficient state và disclosure. |
| W5-T01 persistence handoff | `BLOCKED` | M16 `06-tasks.md` giữ M16-TASK-001–003 `IN_REVIEW`, chờ Sang/G1; `07-status.md` giữ user acceptance pending; W5-G2 còn `DRAFT/IN_REVIEW`. Schema/repository có mặt là technical evidence, chưa phải accepted contract. |
| Route, view-model, allowed files, source lock | `BLOCKED` | `portal/router.py` có student tasks/progress route; chưa có student practice/lesson/review-due route. Không thể chốt page→API→view-model→DOM hay file list an toàn từ source hiện tại. |
| Test/runtime evidence | `NOT_RUN` | Chưa có implementation được phép để chạy M15-TEST-005/008/012 hay browser journey. Đây không phải kết quả `PASS`; test plan yêu cầu chạy sau khi contract và task readiness được chốt. |

## Đối chiếu hiện trạng implementation tại revision

Research ngày 15/10 được ghi trên commit `6baf720`, không phải ancestor của nhánh SCRUM-74. Đã kiểm lại source tại HEAD `818fcbc`: trong phạm vi `portal/`, `storage/` và template cũ, diff giữa hai revision chỉ có `src/aicefr/api/templates.py`; route và storage learning được kiểm lại trực tiếp dưới đây. Browser QA và test vẫn `NOT_RUN`.

| Hạng mục | Fact tại HEAD `818fcbc` | Hệ quả cho readiness |
| --- | --- | --- |
| Student route | `src/aicefr/portal/router.py:176–188` có `/student/tasks`, `/student/responses`, `/student/progress`; không thấy route `/practice/*`, `/learn/path`, lesson hoặc `/reviews/due`. | Không có API route thực tế để khóa method/role/state cho W5-N02. |
| Learning schema | `src/aicefr/storage/migrations.py:16` đặt `SCHEMA_VERSION = 10`; `006_learning.sql:1–19` có path/unit/lesson/version/step, practice/step attempts, review items, achievements, streak days và media; trigger bảo vệ lesson đã publish. | Có nền persistence cho một phần domain; schema không quy định đầy đủ consumer payload, status enum, lifecycle hoặc authorization. |
| Repository/service | `src/aicefr/storage/providers.py:130–156` có `save_path/get_path`; `:158–185` có lưu/đọc practice attempt. Không thấy learning service/API cho query roadmap, lesson steps, due reviews, achievement/streak hoặc pronunciation. | Chưa có producer handoff cho UI; không suy payload từ table hoặc record type. |
| Pronunciation | Không tìm thấy pronunciation route/service trong `src/aicefr`; M13 spec còn DRAFT. | Không được tự đặt source, threshold, `n`, null/insufficient state hay text disclosure trong UI. |
| Ownership/delete | Schema gắn `owner_id` cho attempt/review/achievement/streak; task vẫn cần contract server-side cho read/delete, foreign ID, teacher correction và cleanup. | UI/browser permission test chưa thể xác nhận bằng persistence schema đơn lẻ. |

## API → DOM state matrix cần chốt trước khi khóa Plan

| Package | Required mapping | Contract tối thiểu còn thiếu |
| --- | --- | --- |
| `W5-N02.1` roadmap 18 chặng/31 bài | order, locked/next/review, empty/loading/error | API route + ordered path/unit/lesson payload, seed/version, access rule và meaning của nhãn A2/B1/B2. |
| `W5-N02.2` lesson player | step rail, media/recorder, result, retry/continue, multi-round | `StepType`/attempt state-result enums, media shape, QC/no-speech state, retry/version conflict và owner/teacher correction policy. |
| `W5-N02.3` ôn hôm nay | due batch, empty/overdue, feedback 1/3/7 | schedule transition và timezone boundary, owner permission, retry/delete/conflict semantics; trace M10-AC-006 / TEST-007. |
| `W5-N02.4` practice result | recommendation, previous comparison, no-band invariant | mission/result/reason payload, null/insufficient behavior, retry and error enums; API plus rendered-DOM assertion for M15-AC-005. |
| `W5-N02.5` achievement/streak/pronunciation | unlock/seen, timezone, sufficient/insufficient evidence | M10 achievement/streak payload and M13 pronunciation `status`, `n`, source/config version, disclosure, allowed examples and privacy rule. Any threshold in Week 5 remains draft until owner approval. |
| `W5-N02.6` mobile/delete/correction | sticky action/focus, own/foreign/delete-denied, teacher note | canonical route and server authorization for attempt delete and teacher correction; exact responsive/browser evidence. |

## Findings

### `M15-003-P05-F01` — M10 API/domain contract not ready

- **Severity:** `BLOCKER` · **Category:** Contract / Dependency · **Status:** `OPEN`
- **Observed:** M10 Status is Phase 01 `DRAFT/PENDING`; M10 Tasks 002–005 that provide mission, lesson, review, achievement and API are `BLOCKED`. M10 Specification/Test Plan v0.1 are drafts and do not freeze consumer schema/examples.
- **Risk / failed readiness condition:** UI could commit to wrong route, ordering, enum, retry/recommendation state or delete/teacher-override behavior.
- **Required to resolve:** owner-approved M10 revision with method/route, schema/examples, enums, errors, ordering/version, permission/consent, review lifecycle, delete policy and contract tests; then recheck M15 impact.

### `M15-003-P05-F02` — M13 pronunciation contract not ready

- **Severity:** `BLOCKER` · **Category:** Contract / Privacy · **Status:** `OPEN`
- **Observed:** M13 Status is Phase 01 `DRAFT/PENDING`; M13 Tasks 001–002 and student UI Task 005 remain `BLOCKED`. Current spec provides a draft metric envelope but not owner-approved response examples or pronunciation thresholds/disclosure.
- **Risk / failed readiness condition:** UI may display a metric or example without the approved source, sample sufficiency, privacy boundary or null/insufficient meaning.
- **Required to resolve:** owner-approved M13 payload and fixtures for sufficient/insufficient/no-match, `n`, source/config revision, exposure threshold, example cap/permissions and exact disclosure. The Week 5 values (exposure 8, maximum 5 examples) are proposals until approved.

### `M15-003-P05-F03` — W5-T01 persistence/API handoff not accepted

- **Severity:** `BLOCKER` · **Category:** Dependency / Data · **Status:** `OPEN`
- **Observed:** M16 T01 technical code exists, but M16-TASK-001–003 remain `IN_REVIEW` awaiting Sang/G1, M16 Status says acceptance is pending, and G2 is `DRAFT/IN_REVIEW`.
- **Risk / failed readiness condition:** no accepted revision tying migration, repository methods, transaction/deletion behavior and API lifecycle together for M15.
- **Required to resolve:** Thắng/M16 and Sang/G1 record accepted persistence/repository contract, revision, migration/schema ownership, transactional/delete semantics and API handoff; reconcile M16 task and status records before M15 consumes it.

### `M15-003-P05-F04` — task file boundary and page/API state map cannot be frozen

- **Severity:** `MAJOR` · **Category:** Scope / Design · **Status:** `OPEN`
- **Observed:** No current learning route/service/template provides a concrete route/view-model seam; `05-plan.md` has no task-level allowed-file list for `M15-TASK-003`.
- **Risk / failed readiness condition:** assigning router, storage or template files to the UI task could cross M10/M16 ownership or create concurrent edits.
- **Required to resolve:** after F01–F03, write route→role→API→view-model→DOM state map, one allowed-file list, source lock, rollback and exact test/browser commands into the M15 task readiness candidate.

### `M15-003-P05-F05` — task-specific Phase 05 verdict pending

- **Severity:** `BLOCKER` · **Category:** Approval / Process · **Status:** `OPEN`
- **Observed:** M15 Phase 05 record dated 15/10 approves only `M15-TASK-001A`; it explicitly excludes tasks 001B/002–006 and W5-N02 as a whole.
- **Risk / failed readiness condition:** implementation prompt would bypass the required task-level checkpoint.
- **Required to resolve:** after dependency and file-boundary findings close, present the updated Phase 05 package for the project owner’s `APPROVED` verdict. This record does not imply approval.

## Lệnh, applicability và evidence

- Source/SDD inspection: read-only review at branch `feat/SCRUM-74-W5-N02-Practice-lesson-progress-achievement-pronunciation-UI`, HEAD `818fcbc46e62ee057fcbe980800e01f934d72179`.
- M15 targeted tests, coverage, browser QA: `NOT_RUN` — no implementation attempt and Phase 05 remains blocked.
- No Antigravity prompt was created or issued. No source files were changed.
- Evidence: this record; M15 `01-requirement.md`, `03-specification.md`, `04-test-plan.md`, `05-plan.md`, `06-tasks.md`; `docs/plan/week-05.md` §§9.1–9.6; M10/M13 Status/SDD; M16 `06-tasks.md`, `07-status.md`, `W5-G2-migration-rollback.md`; source locations above.

**CODEX CHECK RESULT:** `BLOCKED`
**CODEX RECOMMENDATION:** `BLOCKED` — chưa đủ Definition of Ready cho `M15-TASK-003`.
**USER VERDICT:** `PENDING`
**VERIFIED/APPROVED BY:** User verdict not recorded.
**NEXT ACTION:** M10/M13 owners và W5-T01 owners hoàn tất, duyệt/freeze các contracts nêu trên; sau đó M15 cập nhật Plan/Task boundary và API→DOM matrix, Codex review lại Phase 05. Chỉ tạo prompt bằng workspace fingerprint helper sau user verdict Phase 05 `APPROVED`.
