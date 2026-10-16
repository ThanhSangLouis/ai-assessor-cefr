# SCRUM-75 — teacher UI source transfer and contract adaptation

**Task:** SCRUM-75 / `M15-TASK-004` / W5-N03  
**Owner:** Nguyên  
**Base revision:** `77af5c8` on `feat/SCRUM-75-W5-N03-Teacher-review-blind-rating-authoring-insights-UI`  
**UI transfer commit:** `64991ee`  
**Status:** UI source transferred; M10 authoring/insights and acceptance remain blocked/pending.

## Source transferred

Copied the seven teacher page templates and their seven page scripts from the read-only source archive:

- Review queue and detail: `queue.html`, `review_one.html`, `queue.js`, `review_one.js`.
- Blind rating list and sheet: `rate_list.html`, `rate_one.html`, `rate_list.js`, `rate_one.js`.
- Path authoring, lesson builder and learning insights: `teach_paths.html`, `teach_lesson.html`, `teach_insights.html` and the corresponding scripts.

The SCRUM-74 branch already supplies the shared shell, icons, styles, common browser code and static asset serving. `web_ui.py` now routes teacher pages through role-gated WSGI rendering. The shared teacher stats navigation points to the existing `/teacher/stats` page.

## Adapted against current producer contracts

- The queue reads `GET /api/teacher/reviews`, displays only fields in each `ReviewCandidate`, and links to the existing server-owned review action routes. Review detail renders the current report and audio route, uses optimistic `revision` values for claim/release/decision forms, preserves the blind guard and machine-seen behavior, and does not call the source archive's missing response/history/lock endpoints.
- Blind rating reads `/api/v1/rating/assignments` and `/api/v1/rating/assignments/{token}`; submission uses the target `submit` or `adjudicate` route and its `criteria`, `overall`, `band`, `rationale`, and `unrateable_reason` fields. The UI uses only opaque blind tokens and assignment state; it does not request participant identifiers or machine scores.
- The authoring and aggregate insights templates have been transferred. Their controls are gated while producer contracts are unavailable, so the old source URLs are not called and no changes are submitted.

## Dependency and verification

PR #39, `docs/SCRUM-63-W5-G1-parity-contract`, was still `OPEN` when checked on 2026-10-16. Its current branch does not provide a complete teacher path-list or aggregate learning-insights contract for these pages. SCRUM-75 must resume those UI interactions after the upstream owner merges/provides the contract. No producer API, domain, storage or service module was modified in this task.

M15-TEST-006/008/012, browser QA and the single integrated E2E are `NOT_RUN`. The E2E remains reserved until SCRUM-74–76 and their required upstream API are together. SCRUM-75 acceptance is not marked complete.
