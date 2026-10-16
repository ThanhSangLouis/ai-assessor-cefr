# SCRUM-74 — Phase 05 verdict and implementation boundary

**Task:** SCRUM-74 / `M15-TASK-003` / W5-N02
**Date:** 2026-10-16 (Asia/Bangkok)
**Owner:** Nguyên
**Decision source:** project owner's direct reply in this Codex conversation: “Đã APPROVED cho cả 3 task”, answering whether Phase 05 had been approved separately for SCRUM-74, SCRUM-75 and SCRUM-76.

## Verdict and scope

The user verdict is recorded as `APPROVED` for the SCRUM-74 UI implementation slice. The authorization covers transferring and adapting the already completed practice, lesson, progress, achievement, streak and pronunciation UI to this repository's Python WSGI presentation layer. It does not approve any M10/M13 producer SDD phase or acceptance on their owners' behalf.

Keep backend/domain APIs and their behavior unchanged. Adapt only page rendering, static assets, browser-side request paths/presentation and the WSGI presentation dispatch needed to serve these pages. The source archive at `D:\LAPTRINH\TLCN\AI\ai-assessor-cefr` remains read-only; do not copy its data/model artifacts.

## File boundary

- Source UI inputs: `src/aicefr/api/templates/{base,_icons,_art,_recorder,practice_path,practice_task,practice_result,lesson,my_progress}.html` and the corresponding `static/` CSS, JavaScript, fonts, SVG artwork and icons.
- Target UI outputs: `src/aicefr/api/web_ui.py`, `src/aicefr/api/templates/`, `src/aicefr/api/static/`, `src/aicefr/api/wsgi.py` (presentation dispatch/static serving only), and `pyproject.toml` (template/static package data and any required renderer dependency).
- Do not edit `src/aicefr/practice/`, `src/aicefr/lessons/`, storage, scoring, identity, review or API producer modules in this task.

## Dependencies and evidence

The practice/lesson UI consumes the M10 routes present on PR #39's SCRUM-63 dependency branch. PR #39 is still open and currently has merge conflicts against `main`; keep that dependency explicit and do not copy its backend changes into this task branch. M13 progress/achievement/pronunciation UI must use the target repository's existing `/api/v1/me/learning/*` contracts. If a required endpoint is not available in the integrated revision, render an honest unavailable state and record the gap; do not invent a producer contract.

`M15-TEST-005/008/012`, browser QA and E2E are `NOT_RUN` until the actual implementation exists on the integrated revision. Run the requested integrated E2E once after SCRUM-74–76 and their required upstream APIs are together. No task is `DONE` until its acceptance evidence is reviewed.
