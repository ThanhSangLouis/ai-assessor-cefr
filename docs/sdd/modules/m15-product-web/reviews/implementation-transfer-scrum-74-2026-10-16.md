# SCRUM-74 — UI source transfer and contract adaptation

**Task:** SCRUM-74 / `M15-TASK-003` / W5-N02
**Owner:** Hoàng Nguyên
**Base revision:** `325d69d`; the adapter and this record follow in the next branch commit.
**Status:** Implementation in progress; acceptance and E2E `NOT_RUN`.

> Historical transfer status. The integrated browser result on revision `0827b37b4f560d5087e1c57e9011ed79acc837dc` supersedes the `NOT_RUN` statement; see [SCRUM-74–76 integration report](../evidence/scrum-74-76/integration-report.md). Owner acceptance remains pending.

## Transferred and adapted

- Moved the completed practice, lesson, review, result, progress, achievement and pronunciation templates/assets into the WSGI presentation package.
- Adapted browser requests to the M10 path, mission, attempt, lesson-step and due-review contracts from PR #39, and to the existing M13 `/api/v1/me/learning/*` endpoints.
- Kept presentation and page dispatch changes inside the SCRUM-74 boundary. No M10/M13 producer, domain, storage, scoring or identity implementation was changed.
- Removed admin page dispatch from this task branch; those pages belong to SCRUM-76.
- Replaced the old practice-result score view with per-goal measurement/status disclosure. No CEFR score or audio download is presented where the M10 public response does not provide one.

## Dependency and verification

PR #39 merged to `main` as `19b7ada` on 2026-10-16 and supplies the M10 routes used by this UI. SCRUM-74 did not change producer code. See the superseding integrated browser report linked above for actual route, viewport, console and network outcomes. Phase 09 acceptance is still pending.
