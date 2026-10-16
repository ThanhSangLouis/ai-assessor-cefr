# SCRUM-75 — Phase 05 verdict and implementation boundary

**Task:** SCRUM-75 / `M15-TASK-004` / W5-N03
**Date:** 2026-10-16 (Asia/Bangkok)
**Owner:** Nguyên
**Decision source:** project owner's direct confirmation in this Codex conversation that Phase 05 is `APPROVED` for SCRUM-74, SCRUM-75 and SCRUM-76. The same conversation authorized porting/adapting the source UI to this repository while preserving backend/domain APIs.

## Approved UI scope

Transfer and adapt the completed teacher review queue, review detail, blind rating, learning-path authoring, lesson authoring and learning insights UI to the repository's WSGI presentation package. Keep producer APIs and domain behavior unchanged. The task may update page dispatch, templates and browser-side code needed to consume an existing, explicitly identified contract.

## File boundary

- Source inputs: `src/aicefr/api/templates/{queue,review_one,rate_list,rate_one,teach_paths,teach_lesson,teach_insights}.html` and corresponding `src/aicefr/api/static/*.js` from the read-only source archive `D:\LAPTRINH\TLCN\AI\ai-assessor-cefr`.
- Target files: `src/aicefr/api/web_ui.py`, the seven named templates and seven named JavaScript files under `src/aicefr/api/static/`, plus this M15 task evidence and the Nguyên W05 AI log.
- Do not change `src/aicefr/api/review.py`, `src/aicefr/api/research.py`, `src/aicefr/api/learning.py`, any service/domain/storage implementation, or producer-module SDD files in SCRUM-75.

## Contract and verification boundary

- Review queue/detail consume the existing M07 queue and form routes. Blind rating consumes the current M12 token-scoped `/api/v1/rating/assignments` routes and must not expose participant identity or machine scores.
- M10 authoring and learning-insight integration depends on PR #39, which remains open. The current PR branch does not provide a complete teacher path-list/aggregate-insights contract for the transferred pages. Keep those interactions `BLOCKED` until the producer contract is available; do not add a consumer-facing or domain endpoint in this task.
- Browser, security, M15-TEST-006/008/012 and integrated E2E evidence remain `NOT_RUN`. Run the single integrated E2E after the approved source/UI tasks and required upstream API dependency are present together. Task acceptance remains pending review of that final revision.
