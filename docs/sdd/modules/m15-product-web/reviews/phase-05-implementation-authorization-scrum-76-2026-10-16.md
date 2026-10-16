# SCRUM-76 UI transfer authorization

**Date:** 2026-10-16
**Owner:** Hoàng Nguyên
**Tasks:** SCRUM-76 / `M15-TASK-005` and `M15-TASK-006`

## Project-owner verdict and scope

The project owner confirmed in this conversation that Phase 05 is `APPROVED` for SCRUM-74, SCRUM-75 and SCRUM-76. The owner also authorized porting/adapting UI within scope. This record captures only the SCRUM-76 authorization; it does not approve producer modules or acceptance criteria owned by M11–M16.

Port and adapt the completed admin presentation into the existing WSGI/Jinja package. Preserve current backend/domain APIs, authorization, role checks and data policy. Do not add routes or alter API/service/storage/domain modules. Do not expose an interaction when its current contract or policy is absent; show its dependency instead.

## Allowed files for this slice

- `src/aicefr/api/web_ui.py` — authenticated admin page dispatch only.
- `src/aicefr/api/templates/admin.html`, `admin_ratings.html` — adapted admin landing and M12 batch pages.
- `src/aicefr/api/static/admin_portal.js` — read-only rendering against existing M14 GET routes.
- `src/aicefr/api/static/admin_ratings.js` — adapted source UI against existing M12 routes.
- `src/aicefr/api/static/style.css` — styles scoped to the transferred admin page.
- This task's M15 task/status/plan records and AI usage log.

Any need to change `src/aicefr/api/identity.py`, `billing.py`, `portal/router.py`, service, storage or domain modules is outside this authorization and requires a separate owner decision.

## Acceptance boundary

- Keep the page admin-only using the existing session resolver.
- Current account, data erasure, maintenance, model, QC, audit, health and assigned blind-rating screens remain linked through their existing portal routes.
- The M12 batch screen may use existing `ResearchApi` routes after adapting current response shapes; no producer API changes are authorized.
- Billing is read-only in this slice and uses the current `GET /api/v1/admin/billing` and `GET /api/v1/admin/billing/orders` contracts.
- Do not wire the source's legacy study, temporary-password-receipt or billing mutation requests to the repo's APIs.
- `M15-TASK-005` cannot be accepted until its remaining producer/policy gates, browser checks and evidence are resolved.
- `M15-TASK-006` can run only on the reviewed integrated revision after N01–N03. Run the user's requested integrated E2E exactly once at that final gate; until then record `NOT_RUN`.
