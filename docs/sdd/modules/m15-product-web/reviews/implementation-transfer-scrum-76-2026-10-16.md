# SCRUM-76 implementation transfer record

**Date:** 2026-10-16
**Branch:** `feat/SCRUM-76-W5-N04-Admin-UI-full-browser-regression-va-UI-handoff`
**Owner:** Hoàng Nguyên
**Authorization:** [SCRUM-76 UI transfer authorization](phase-05-implementation-authorization-scrum-76-2026-10-16.md)

## Transferred and adapted UI

The source archive is `D:\LAPTRINH\TLCN\AI\ai-assessor-cefr`. The source admin presentation is `src/aicefr/api/templates/admin.html`; its browser behavior is in `src/aicefr/api/static/admin.js`, `admin_ratings.js`, `admin_study.js` and `admin_billing.js`.

The admin landing presentation was adapted into the target Jinja package at `src/aicefr/api/templates/admin.html` and dispatched from `src/aicefr/api/web_ui.py` for authenticated admins only. The page links to existing account, erasure, maintenance, model, QC, audit, runtime and assigned-rating portal pages. The source `admin_ratings.js` and ratings panel were transferred into `src/aicefr/api/static/admin_ratings.js` and `templates/admin_ratings.html`; the adapter now consumes the target M12 shapes (`eligible_responses`, pseudonymous `actor_id`, wrapped `batches`, and batch summary fields) and renders only report metrics returned by the existing report contract. The target API does not persist the submitted batch name, which the UI discloses and replaces in the batch list with the generated ID. `src/aicefr/api/static/admin_portal.js` reads the current M14 billing overview and order-list GET endpoints; it does not create quotes/orders or perform settlement. `style.css` adds only the layout rules used by the landing page.

The archive's study-lifecycle screen was not wired: M13 currently exposes study creation and start, survey, close, report, and CSV actions, but has no study-list endpoint for the source screen's list workflow. Billing mutations await the required policy handoff. Temporary-password receipt and batch-account behavior are similarly gated. These are explicit compatibility boundaries, not evidence that those flows are complete.

## Scope and checks

- Changed implementation files: `web_ui.py`, `templates/admin.html`, `templates/admin_ratings.html`, `static/admin_portal.js`, `static/admin_ratings.js`, `static/style.css`.
- Backend/domain API files: unchanged.
- SCRUM-76 source/UI adaptation: partial; remaining gates are listed above and in M15 status.
- `git diff --check`: passed for the transferred implementation and task records; no whitespace errors.
- Unit, browser and E2E checks: `NOT_RUN`. Per user instruction, run the single integrated E2E only after the final integrated revision and dependency gate are ready.
- M15-TEST-007/008/012 and task acceptance: `NOT_RUN`.
- `M15-TASK-006`: `BLOCKED` until N01–N03 review and final integration. No result is inferred from source inspection.

## Base and fingerprint

Implementation base: this task branch at commit `d6b617270fda91f5fae4dc96b155c65b40201c51` before the SCRUM-76 source transfer. UI transfer commit: `d2e9689`. The WSGI app uses Jinja templates and serves package-local static assets; page requests continue through the existing session and `ActorRole.ADMIN` resolver.
