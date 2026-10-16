# SCRUM-74 / W5-N02 — Kết quả nghiên cứu đọc-only của Codex

**Ngày:** 15/10/2026
**Record type:** Đối chiếu implementation và dependency phục vụ Phase 05; không phải Phase 05 verdict hay quyền implement.
**Baseline:** HEAD `6baf720f173b440eb961676b09ea290058a39b35` cùng working-tree diff A2R1 M15.
**Phạm vi:** `M15-TASK-003` / `W5-N02.1–N02.6`. Không sửa source, không chạy test/browser QA, không phát prompt.

## Kết luận readiness

`M15-TASK-003` tiếp tục `BLOCKED`. Hiện có persistence/schema nền cho một số learning entities, nhưng chưa có learning API/service, student learning route, template/view-model hoặc DOM. M10/M13 vẫn Phase 01 `DRAFT/PENDING`; M16/W5-T01 có technical implementation/evidence nhưng task/owner acceptance và contract freeze chưa đầy đủ. Không thể lập allowed-file list hay prompt implementation cuối trước các quyết định này.

## API → DOM state matrix

| Journey / trace | Tình trạng UI/API hiện hành | Persistence/technical facts | Contract/data cần có trước khi dựng DOM |
| --- | --- | --- | --- |
| Roadmap A2→B1→B2, 18 chặng/31 bài — `M15-FR-005`, `M15-AC-004/005`, `M15-TEST-005/008/012`, `W5-N02.1` | Chưa có route `/practice/*`, `/learn/path`, roadmap template hoặc API query. `/student/tasks` là catalogue task đánh giá; `/student/progress` là thống kê assessment (`portal/router.py:176–188`). | Migration learning có `learning_paths`, `learning_units`, `learning_lessons`, lesson version/steps (`storage/migrations/006_learning.sql:1–10`). Repository hiện chỉ có `save_path/get_path`, chưa có path/unit/lesson query/ordering service (`storage/providers.py:129–156`). | Path/order/lock/next/review payload, route, empty/error/retry, label A2/B1/B2 không mang nghĩa band và server permission. M10 Spec v0.1 Draft nêu domain/API, chưa có owner-approved schema/example. |
| Lesson player/step rail/media/result/retry — `W5-N02.2` | Không có student lesson/player route, API hoặc template. `recorder.js` là assessment upload recorder, không lesson player (`api/static/recorder.js`). | Có `lesson_versions`, `lesson_steps`, `step_attempts`, `learning_media`; trigger chặn sửa nội dung published (`006_learning.sql:4–14,19`). | Step/media view-model, `StepType`, `StepAttempt.status`/result enums, version conflict, QC/no-speech behavior, retries/continue, attempt permissions và teacher correction/audit. M10 Spec v0.1 mô tả flow ở mức ý định; chưa có payload/error example/test contract. |
| Review-due/1–3–7 ngày — `W5-N02.3` | Không có `/api/v1/learn/reviews/due`, trang ôn hôm nay hay DOM state. `/teacher/reviews` là queue bài assessment, không phải spaced review. | Có `review_items`, owner/source/box/due/state và index theo owner/state/due (`006_learning.sql:15–16`); chưa thấy learning repository method đọc/ghi schedule. | Due batch, empty/due/overdue, feedback interval, schedule transition, attempt relation, delete/retry/conflict behavior, owner check và consent. M10 Spec liệt kê endpoint nhưng chưa khóa lifecycle/payload. |
| Practice result/recommendation/previous comparison — `W5-N02.4` | Không có `/api/v1/practice`, mission/result page, recommendation UI hay DOM assertion. | `practice_attempts` table và `PracticeAttemptRecord` có attempt/owner/mission/prompt/status/measurements/evidence/timestamps; repository hỗ trợ save/get (`006_learning.sql:11–12`; `storage/providers.py:34–43,158–185`). `status` là `TEXT`; chưa có enum/constraint trong schema này. | Mission/result/recommendation fields, outcome/reason, retry/previous comparison, status/error enum, role/consent/delete permission. No-band rule phải được enforce và có M15-TEST-005/012 API + DOM assertion; storage alone không chứng minh rule. |
| Achievement/streak/seen — `W5-N02.5` | Không có progress/achievement/streak service, API hoặc cards. | Có `achievements` và `streak_days`; dữ liệu đã được personal export và admin erasure preview liệt kê (`006_learning.sql:17–18`; `portal/service.py:290–313,377`; `portal/data.py:165–178`). Export/erase không phải learning UI/API. | Unlock/seen/retention rules, timezone/day boundary, empty/near-achievement payload, 7-day comparison, owner/consent, no leaderboard/pressure copy; cần version/source state và insufficient semantics nếu metric được trình bày. |
| Pronunciation profile — `W5-N02.5` | Không có route, metric/service hoặc pronunciation DOM được tìm thấy trong `src/aicefr`. | M13 Spec v0.1 Draft mô tả normalized expected/heard labels và pattern priority, nhưng source metric chưa có trong implementation hiện hành. | `status`, `n`, source/config version, disclosure, null/insufficient rule, exposure threshold, allowed examples and privacy. M13 Spec chỉ chốt envelope chung; W5 plan đề xuất dưới 8 exposure là insufficient và tối đa 5 examples (`week-05.md:347–356`), vẫn cần owner verdict. |

M15-TEST-005 đòi success/failure/retry/continue, đủ-thiếu data, 409/422, no-band và mobile sticky action. Hiện không có API→view-model→DOM state map để assertion có thể truy vết.

## Contract và persistence readiness

- M10 `03-specification.md` v0.1 `DRAFT` liệt kê Student API `/api/v1/practice`, `/missions/{id}`, `/attempts/{id}`, `/api/v1/learn/path`, `/lessons/{id}`, `/reviews/due`, cùng các lỗi 404/403/409/422 (`m10-learning-experience/03-specification.md:24–28`). Đây là draft, không có producer verdict; M10 `07-status.md` ghi Phase 01 `PENDING`.
- M13 `03-specification.md` v0.1 `DRAFT` yêu cầu metric payload gồm `status`, `n`, source/config version và disclosure, nhưng không cung cấp schema/enum/payload examples hay owner-approved thresholds (`m13-learning-evidence/03-specification.md:25–27`). M13 `07-status.md` ghi Phase 01 `PENDING`.
- Technical persistence đã hiện diện trong current source: `storage/migrations.py` ghi `SCHEMA_VERSION = 10`; `006_learning.sql` định nghĩa tables/constraints trên; `LearningRepository` hiện hữu cho path và practice-attempt persistence. Tuy nhiên M16 `06-tasks.md` còn `IN_REVIEW` chờ Sang/G1 và `07-status.md` ghi formal owner/user acceptance pending; `W5-G2-migration-rollback.md` vẫn là `DRAFT/IN_REVIEW`. Vì vậy code/schema là technical evidence, chưa phải contract freeze của M10/M13 hoặc task-level permission để M15 giả định enum/payload.
- Có thể thấy một lệch trạng thái cần Thắng/M16 làm rõ: M16 `06-tasks.md` ghi T01 `IN_REVIEW`, trong khi `07-status.md:28` ghi T01.2–T01.6 `IN_PROGRESS`; cùng status cũng ghi SCRUM-65 technical verification PASS ở `:30–34` nhưng Sang/user verdict vẫn pending. Cần thống nhất implementation state và acceptance state riêng trong Status/G2.

## Permission, delete và evidence gaps

- Schema learning mang `owner_id` cho attempts/review/achievement/streak; hiện không có learning route/service để chứng minh server-side owner/role/consent checks cho read, delete, teacher override hoặc seen-state.
- Personal export đã chọn cột learning và lọc `measurements/evidence`; admin erasure preview nhận diện attempt/review/achievement/streak. Chưa có student delete-attempt endpoint hoặc UI xác nhận; M10 Spec chỉ nói xóa owned blob/result/review link và giữ achievement, nhưng chưa khóa exact transactional cleanup/policy (`m10-learning-experience/03-specification.md:30–36`).
- Evidence cần cho W5-N02: lesson success/failure/retry/multi-round; review due/empty and 1/3/7 transition; no-band assertion trong API + rendered DOM; achievement seen; insufficient pronunciation with source/n/disclosure; delete allowed/foreign/denied; teacher correction; mobile sticky focus/scroll; console/network và screenshot hash. Trace tới `M15-TEST-005/008/012`, `M10-TEST-007/009` và `W5-N02.1–N02.6`.
- M15 Test Plan command cho tests/browser là candidate: `python -m pytest -q tests/api tests/local tests/web -m "not smoke"`; `tests/web/` và M15 Playwright script chưa tồn tại theo `m15-product-web/04-test-plan.md:8–9,33–39`. Không chạy test/browser QA trong lượt này; kết quả hiện tại `NOT_RUN`.

## Candidate boundary và câu hỏi owner

`M15-TASK-003` hiện chưa đủ dữ kiện để chốt allowed files: route/view/API chưa tồn tại, còn phụ thuộc M10 service/storage và M13 metric producer. Candidate theo vùng trách nhiệm trong W5 plan là M15-owned route/template/static UI và test/browser evidence; không đưa domain/rule/repository vào router/template. M10/Sang sở hữu learning API/service/rule; M13/Sang sở hữu metric/disclosure; M16/Thắng sở hữu migration/runtime; Nguyên sở hữu page/view-model. Không gán file mới cho owner trước khi source lock được thống nhất.

1. **Sang/M10:** cung cấp approved revision/schema/examples cho mission/path/lesson/step/attempt/review/recommendation; enum/state, ordering/version, retry/error, role/consent, teacher override và attempt-delete lifecycle.
2. **Sang/M13:** duyệt pronunciation source/threshold/exposure `n`, insufficient/null states, examples, disclosure và metric config version.
3. **Thắng/M16 + Sang/G1:** xác nhận T01 persistence/migration revision và owner verdict; tách technical pass, implementation status, user acceptance; làm rõ trạng thái T01 và G2 trong `06-tasks.md`, `07-status.md`, `W5-G2-migration-rollback.md`.
4. **Nguyên/M15:** sau khi producer contract freeze, chốt route-method-role-consent, API→view-model→DOM matrix, allowed files/source locks, fixtures và exact browser/API commands cho `003`.

**Codex readiness recommendation:** `BLOCKED` cho Phase 05 của `M15-TASK-003`. Chưa phát prompt; chưa tuyên bố API, UI, persistence hoặc metric đã được owner nghiệm thu.

## Revalidation on the SCRUM-74 branch — 16/10/2026

The prior read-only report used `6baf720`, which is not an ancestor of the SCRUM-74 branch. I rechecked the relevant routes, storage, M10/M13 statuses and W5-T01 records at HEAD `818fcbc46e62ee057fcbe980800e01f934d72179` on `feat/SCRUM-74-W5-N02-Practice-lesson-progress-achievement-pronunciation-UI`. The worktree was clean at review entry. The source comparison showed `src/aicefr/api/templates.py` as the only difference in the inspected `portal/`, `storage/` and template paths; `portal/router.py` and learning storage findings were also inspected directly at the current HEAD.

Findings remain unchanged: student tasks/progress routes exist, but there is no student practice/lesson/review-due route or learning UI; schema version 10 and migration 006 provide partial learning persistence, while repository support is limited to saving/getting paths and practice attempts; M10/M13 remain Phase 01 `DRAFT/PENDING`; M16 T01 acceptance/G1 and G2 remain pending. The task-specific readiness review is [Phase 05 SCRUM-74 review, 16/10/2026](phase-05-readiness-scrum-74-2026-10-16.md).

**Revalidation checks:** read-only source and SDD inspection only. Tests/browser QA `NOT_RUN`; no code changed; no implementation prompt issued. Current Codex recommendation remains `BLOCKED` for `M15-TASK-003`.
