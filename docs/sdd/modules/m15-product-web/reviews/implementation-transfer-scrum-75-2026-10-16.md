# SCRUM-75 — teacher UI source transfer and contract adaptation

**Task:** SCRUM-75 / `M15-TASK-004` / W5-N03
**Owner:** Hoàng Nguyên
**Base revision:** `e5fab50` on `feat/SCRUM-74-W5-N02-Practice-lesson-progress-achievement-pronunciation-UI`
**UI transfer commit:** `6b66555`
**Status:** UI transferred and adapted to current contracts; task implementation is in progress and integrated acceptance is pending.

## Source transferred

Copied the seven teacher page templates and their seven page scripts from the read-only source archive:

- Review queue and detail: `queue.html`, `review_one.html`, `queue.js`, `review_one.js`.
- Blind rating list and sheet: `rate_list.html`, `rate_one.html`, `rate_list.js`, `rate_one.js`.
- Path authoring, lesson builder and learning insights: `teach_paths.html`, `teach_lesson.html`, `teach_insights.html` and the corresponding scripts.

The SCRUM-74 branch already supplies the shared shell, icons, styles, common browser code and static asset serving. `web_ui.py` now routes teacher pages through role-gated WSGI rendering. The shared teacher stats navigation points to the existing `/teacher/stats` page.

## Adapted against current producer contracts

- The queue reads `GET /api/teacher/reviews`, displays only fields in each `ReviewCandidate`, and links to the existing server-owned review action routes. Review detail renders the current report and audio route, uses optimistic `revision` values for claim/release/decision forms, preserves the blind guard and machine-seen behavior, and does not call the source archive's missing response/history/lock endpoints.
- Blind rating reads `/api/v1/rating/assignments` and `/api/v1/rating/assignments/{token}`; submission uses the target `submit` or `adjudicate` route and its `criteria`, `overall`, `band`, `rationale`, and `unrateable_reason` fields. The UI uses only opaque blind tokens and assignment state; it does not request participant identifiers or machine scores.
- Path authoring now uses the M10 endpoints merged in PR #39 for create/detail, unit and lesson creation, reorder, publish, import/export and delete. Since the contract has no list endpoint, known path IDs and lesson-to-unit mapping are stored in the teacher's browser storage; IDs created in the current browser are discoverable there.
- Lesson authoring uses typed step payloads plus the current lint, media and publish routes. Lesson-level rubric criterion, pass ratio, model text and keyword fields are disabled because they are absent from the producer contract. The source image-upload control remains unavailable; this UI does not invent an upload route.
- Learning insights read the signed-in teacher from `/api/v1/me` and request that owner's available insights. The current contract does not expose class/cohort aggregation, so the page reports only per-owner results and does not synthesize cohort metrics.

## Dependency and verification

PR #39 (`docs/SCRUM-63-W5-G1-parity-contract`) merged to `main` as `19b7ada` on 2026-10-16 and provides the M10 routes used by path and lesson authoring. Its contract still has no path-list or cohort-insights route; the UI uses browser-local known IDs and per-owner insights for those areas. No producer API, domain, storage or service module was modified in SCRUM-75.

PR #46 CI passed on its original head before the latest base integration; CI must be checked again after rebase. M15-TEST-006/008/012, browser QA and the single integrated E2E remain `NOT_RUN`. The E2E is reserved for the final integrated SCRUM-74–76 revision. SCRUM-75 acceptance is not marked complete.
