# SCRUM-76 implementation transfer record

**Date:** 2026-10-16
**Branch:** `feat/SCRUM-76-W5-N04-Admin-UI-full-browser-regression-va-UI-handoff`
**Owner:** Hoàng Nguyên
**Authorization:** [SCRUM-76 UI transfer authorization](phase-05-implementation-authorization-scrum-76-2026-10-16.md)

## Transferred and adapted UI

The completed admin UI supplied for transfer includes the admin overview, ratings, study management and billing presentation. Its target implementation is adapted to the repository's Jinja/WSGI presentation layer and current producer contracts.

The admin landing presentation was adapted into the target Jinja package at `src/aicefr/api/templates/admin.html` and dispatched from `src/aicefr/api/web_ui.py` for authenticated admins only. The page links to existing account, erasure, maintenance, model, QC, audit, runtime and assigned-rating portal pages. The source `admin_ratings.js` and ratings panel were transferred into `src/aicefr/api/static/admin_ratings.js` and `templates/admin_ratings.html`; the adapter now consumes the target M12 shapes (`eligible_responses`, pseudonymous `actor_id`, wrapped `batches`, and batch summary fields) and renders only report metrics returned by the existing report contract. The target API does not persist the submitted batch name, which the UI discloses and replaces in the batch list with the generated ID. `src/aicefr/api/static/admin_portal.js` reads the current M14 billing overview and order-list GET endpoints; it does not create quotes/orders or perform settlement. `style.css` adds only the layout rules used by the landing page.

The `/admin/studies` page is now role-gated in `web_ui.py`. `admin_study.js` consumes the existing M13 create, start, close, report and CSV export routes. M13 has no study-list endpoint, so the UI keeps known study IDs in browser storage and also allows an admin to open a study by ID; it does not invent a server-side list. The participant survey endpoint remains part of the existing M13 API and is not an admin mutation on this page.

The billing panel reads the current M14 billing overview and order list. It does not create quotes/orders or settle payments while the required policy contract is absent. M11 OTP/temporary-password receipt and batch-account behavior remain unavailable through the current UI/API contract. These controls stay gated and are reported as compatibility limits; no producer endpoint or domain behavior was added.

The integrated cross-role review found that the shared navigation requested the student-only `/api/v1/learn/reviews/due` endpoint on teacher/admin pages, producing a 403 console entry. `src/aicefr/api/static/common.js` now makes that request only when the student `reviews_due` badge is present; no endpoint or authorization behavior changed. Browser preflight also found Chromium's `/favicon.ico` request returned 404; `web_ui.py` now serves the existing local `favicon.svg` for that alias.

## Scope and checks

- Changed implementation files: `web_ui.py` (admin routes and local favicon alias), `templates/admin.html`, `templates/admin_ratings.html`, `templates/admin_study.html`, `static/admin_portal.js`, `static/admin_ratings.js`, `static/admin_study.js`, `static/style.css`, `static/common.js` (student-only badge request guard).
- Backend/domain API files: unchanged.
- SCRUM-76 UI adaptation: in progress; current-contract screens are implemented and unsupported mutations remain gated as listed above.
- `git diff --check`: passed for the transferred implementation and task records; no whitespace errors.
- Unit, browser and integrated E2E checks: `NOT_RUN` on the final integrated revision. Run the single E2E after SCRUM-74–76 are integrated.
- M15-TEST-007/008/012 and task acceptance: `NOT_RUN`.
- `M15-TASK-006`: `IN_PROGRESS`; cross-role regression and the single integrated E2E remain pending. No result is inferred from source inspection.

## Base and fingerprint

Implementation base: this task branch at commit `c1baa31` before the SCRUM-76 source transfer. UI transfer commit: `79da8c1`. The WSGI app uses Jinja templates and serves package-local static assets; page requests continue through the existing session and `ActorRole.ADMIN` resolver.
