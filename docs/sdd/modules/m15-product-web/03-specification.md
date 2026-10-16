# M15 — Specification (Đặc tả) — W5-N01

- **SCOPE ID / TYPE:** M15 / module
- **SCOPE ROOT:** `docs/sdd/modules/m15-product-web/`
- **VERSION / STATUS:** v0.2 / APPROVED — PHASE 03, 2026-10-16
- **BASE:** `d60e8a4b9f63a0b0259ada8971e23bafdb1df041`
- **INPUT:** Requirement v0.2 Phase 01 APPROVED; Research v0.2 RUN.
- **ACTIVE TASK:** W5-N01 · **USER VERDICT PHASE 03:** APPROVED, 2026-10-16

## 1. Product boundary

N01 provides the public/student experience from landing/login and consent through speaking-task submission, progress, report/evidence, history and account. The web layer renders server-owned actor, consent, task, response, report and learning-evidence state. It does not implement authorization, scoring, QC, report generation, research metrics or billing.

W5-N02 lesson/practice pages, W5-N03 teacher/blind-rating pages, and W5-N04 admin/billing pages are outside this specification. Shared shell/components must allow those later slices to extend the system without implementing their workflows in N01.

## 2. Proposed route/page contract

Existing paths below are observed in source. New public/account paths are proposals for Phase 03 owner review. API paths marked `observed` are implementation inputs, not an owner-approved cross-module contract.

| Page | Proposed/current route | Actor and input | Required visible states | Main behavior and boundary |
| --- | --- | --- | --- | --- |
| Landing | `GET /` (proposed; currently redirects to `/login`) | Anonymous | normal, asset/config error | Explain the low-stakes learning use; link to login and bands page. No certificate, pass/fail or unmeasured accuracy claim. |
| Bands explanation | `GET /bands` (proposed) | Anonymous | normal, content unavailable | Explain estimate/evidence limits using approved wording. Do not imply official certification or a guarantee. |
| Login | `GET/POST /login` (existing) | Anonymous; credentials submitted to server | idle, submitting, invalid credentials, rate-limited, unavailable | Keep password/session in server boundary; successful login follows server consent/session state. Do not store credential/token in browser storage. |
| Consent | `GET /student/consent`; POST accept/withdraw (existing) | Student session; M11 consent DTO | required, active, withdrawn, outdated version, saving, error | The server’s effective consent/version controls submission. Withdrawal updates server state and directs to a safe next step. |
| Assessment input | `GET /student/upload`; POST `/student/responses` (existing browser route); POST `/api/student/responses` (existing API route) | Student session, open task/version, consent and allowed audio | task unavailable, preparation, recording, preview, selected file, upload in progress, rejected/error, retry-ready, submitted | Preparation is 30 seconds with explicit skip. Student can listen, record again or submit. Server enforces role/owner/consent/QC and supplies safe reason. UI does not infer permission from a hidden link. |
| Processing status | `/student/responses/{response_id}` (existing); GET `/api/student/responses/{response_id}/status` (existing) | Own response ID | queued, running, report unavailable, completed, review required, rejected, failed, not found/forbidden | Render status/reason from M01. Pending can refresh or offer retry where contract allows. Foreign/unavailable IDs use privacy-safe response. No invented completion or score. |
| Report | `/student/responses/{response_id}/report` (existing); GET `/api/student/responses/{response_id}/report` (existing) | Own report DTO from M06/M09 | loading/unavailable, evidence available/insufficient, provisional, teacher verified, error/retry | Show one overall score/band only when present; show criterion evidence/coverage separately. Preserve null and `insufficient_evidence`; for a monologue `Interaction=null`. Audio seek uses report evidence references and the owner-scoped audio route. |
| History | `GET /student/responses` (existing) | Student-scoped response list | loading, empty, populated, filter/page, error | Show only own responses. Distinguish report/audio availability and allow navigation to status/report. |
| Progress | `GET /student/progress` (existing) | Student-scoped aggregate plus optional M13 disclosures | loading, no responses, measured data, insufficient/unavailable, error | Do not manufacture a trend or improvement claim. M13 blocks appear only with approved payload/provenance and valid sample state. |
| Account | `GET /student/account?tab=profile|security|activity|data` (proposed) | Student session; M11 and M16 APIs | loading, empty, disabled/not configured, success, validation/session error, confirm/recovery | Four tabs: profile, security, activity and data. Consent remains a separately addressable page. Password/session/Google/data actions use server contracts only. |

### 2.1 Server contract handoff — provisional until owner review

| Flow | Current observed contract/source | Required consumer behavior | Contract owner/status |
| --- | --- | --- | --- |
| Login/session/consent/account/Google | `src/aicefr/api/identity.py`; SCRUM-66 UI handoff lists `/api/v1/me`, profile, password, sessions, activity, consent and Google operations | Use DTOs and safe error classes; temporary-password state blocks protected routes; Google `503` becomes disabled/unavailable UI | M11 technical handoff exists; M11 SDD remains DRAFT/PENDING. Confirm payload/error revision with Thắng before Phase 05. |
| Task/upload/status/response owner | `src/aicefr/api/wsgi.py`, `src/aicefr/api/student.py`, `src/aicefr/portal/router.py` | Server derives actor from session; task-open and consent/version gates are enforced; status/report output stays owner scoped | M01 SDD remains DRAFT/PENDING. Confirm retry/idempotency and reason-code contract with Thắng. |
| Audio/QC | M02 approved Requirement/Specification plus runtime API | Render producer reason/status, never convert missing measurement to zero or infer CEFR | M02 QC tasks have an open cross-owner review; confirm the shared response revision with Thắng/Sang. |
| Report/audio/history | `src/aicefr/api/templates.py`, `src/aicefr/portal/router.py`; M06 draft spec | Render only report DTO/evidence refs and available audio; preserve provisional vs teacher-final values | M06 SDD DRAFT/PENDING. Confirm M06 DTO and link ownership with Nguyên/Thắng. |
| Trust/refusal | M09 Requirement v0.1 | Only approved reason/evidence/provenance is rendered | M09 DRAFT/PENDING; Sang must supply the contract. |
| Reliable change/pronunciation/study | M13 Requirement v0.1 | Show `NOT_EVALUATED`/insufficient/no data without creating a sample count or result | M13 DRAFT/PENDING; Sang must supply producer contract and evidence rules. |
| Local assets/package | `pyproject.toml` currently packages JS and migration SQL; M16 W5 evidence is on a different base | Include CSS, fonts, icons/art and license/provenance metadata in the clean wheel; no external asset dependency | M16 review/approval pending; Thắng confirms package-data and clean-wheel handoff. |

These rows document present implementation and required handoff. They do not freeze shared API contracts or approve a change to another module. If an owner-reviewed contract is missing or disagrees with observed source, stop Phase 05 readiness and resolve it with that owner.

## 3. User journey and state transitions

1. Anonymous user opens the landing page; can read the band explanation or go to login.
2. Login success establishes an HttpOnly server session. If consent is absent/outdated, the server directs the student to consent before upload; otherwise the student enters the N01 navigation.
3. Student chooses an open task, sees its prompt and a 30-second preparation state with a clear skip control. Student records or selects audio, listens to the preview, can record again, then submits once.
4. Submission response supplies a server response ID and state. While request is pending the client disables repeat submit. Automatic retry is permitted only when producer contract supplies an idempotency guarantee; otherwise recovery first looks up response/status and never blindly resubmits.
5. Status follows the server state. `QUEUED`/`RUNNING` remains pending. If the response is marked complete before report availability, keep the report-unavailable state; do not synthesize score or mark local completion.
6. Student opens own report/history/progress. A present report shows provisional and teacher-final values distinctly, one overall score/band at most, and per-criterion coverage/evidence. A missing criterion/evidence value remains null/insufficient, never numeric zero.
7. Account changes use the server’s account/session/activity/consent/Google/data contract. Confirmation is required for irreversible actions; errors retain safe context and an actionable recovery path.

### 3.1 State and recovery rules

| State/error | Student-facing response | Recovery rule |
| --- | --- | --- |
| Loading/pending | Clear status text and non-color indicator; pending action may be disabled | Do not hide page navigation or imply a result. |
| Empty/history with no responses | Explain that no submissions exist yet and offer the open-task action when allowed | No invented progress baseline or trend. |
| `401 SESSION_REQUIRED` | Session ended; link to login | Re-authenticate; do not resend a mutation automatically. |
| `403 ACCESS_DENIED` / consent required | Explain unavailable action without identifying a foreign owner | Return to authorized page or consent action per server response. |
| `404 RESOURCE_UNAVAILABLE` | Generic unavailable message | Do not disclose whether a foreign response/session exists. |
| `409` stale/duplicate/conflict | Explain that current state changed | Refresh producer state; preserve safe form input; never retry a conflicting mutation blindly. |
| `422 INVALID_REQUEST` / QC rejection | Identify the safe field/reason and next step | Keep fields that can be corrected; replace audio when requested. Do not echo stack trace/path. |
| `429` | Rate-limited message with wait instruction when supplied | Respect server `Retry-After`; no tight polling. |
| `503`/not configured | Explicit unavailable or disabled state (not a success-looking control) | Continue unrelated account/report use; retry only if server indicates it is safe. |
| report unavailable | Keep processing state and link to status/history | Retry read after a bounded user action or server-provided interval; no fake score. |

Exact API codes beyond those observed must be aligned with producer-owner contract; this table is product behavior, not a new backend error enum.

## 4. Shared shell and design system

### 4.1 Navigation and responsive layout

- Use server-authenticated role data to choose navigation. Anonymous pages do not expose student/admin links; student navigation does not show teacher/admin actions. Server remains the authorization boundary for direct URLs and mutations.
- Desktop at 1024 CSS px and above: persistent sidebar; 600–1023: compact rail or accessible drawer; 360–599: top bar plus bottom navigation. These breakpoints follow the existing M15 module-level navigation requirement; preserve keyboard access and current-page indication.
- Main content has one `<main>`, one page-level `<h1>`, a skip link, logical headings and visible focus. Dialog close/return restores focus to the triggering control.
- Page changes at 360, 390, 768 and 1280 CSS px; 200% browser zoom, print and reduced-motion checks follow approved AC-007. No claim of named accessibility-standard conformance is made.

### 4.2 Semantic tokens and reusable components

Use central semantic tokens for page/surface/text/muted/border/focus/status colors; typography scale; spacing; radius; elevation; motion duration/easing; breakpoints and z-index. Theme values can change while component meaning and state text stay the same. Product CSS, Roboto font, icon and art assets are local and packaged with license/provenance metadata.

Shared components for N01: shell/skip link/nav; button/link/icon button; labeled field/select/checkbox; tabs; status/badge; card/list/table; confirmation dialog; toast/alert/status message; loading/skeleton/empty/error; pagination/disclosure; audio player/evidence seek; recorder/progress. Each interactive component defines idle, hover, keyboard focus, disabled, pending, invalid/error and success where relevant. Icons alone never carry an action label; color alone never carries a status.

Default implementation option is semantic server-rendered HTML with CSS and small browser JS that calls the existing WSGI endpoints. This matches current runtime/package boundaries and avoids a new build runtime. A framework/build pipeline is outside this N01 specification unless the owner requests it during Phase 03 review.

### 4.3 Theme, typography, art and motion

- Light and dark themes provide equivalent contrast/readability and semantic state; persist only a non-sensitive preference.
- Bundle Roboto locally with license notice and fallback. Icons/art are local SVG/bitmap assets with source/license metadata and must be replaceable without route logic changes.
- Art is decorative, hidden from the accessibility tree, does not intercept pointer actions or cause overflow, and is omitted from print. Motion never communicates unique state; reduced-motion preference removes non-essential motion and smooth movement.
- No third-party font/CDN/analytics/image request is required for any N01 route.

## 5. Accessibility, privacy and quality behavior

The target is behavior-specific as selected by the owner. No `WCAG 2.2 AA/AAA` or other conformance claim is part of this Specification.

- Every control can be reached/operated by keyboard with a visible, persistent focus indicator; order follows the reading/action sequence. Dialogs manage focus and return it on close.
- Inputs have visible labels/instructions; validation errors identify the affected field and corrective action. Dynamic pending/success/error states are programmatically announced.
- Status is conveyed by text/icon/shape in addition to color. Light/dark theme, focus, disabled, loading and error states retain their meaning.
- Zoom/reflow/responsive behavior preserves content and primary actions at the approved widths; no horizontal overflow or bottom-nav overlap. Print hides decorative art and nonessential navigation.
- `prefers-reduced-motion: reduce` removes non-essential animation/transitions and does not remove information.
- No secret, session token, password, client secret, internal filesystem path, foreign transcript/audio or data denied by role/consent appears in DOM, URL or client log.

## 6. Acceptance trace

| Requirement | Specification sections | Observable result to be designed into Phase 04 cases |
| --- | --- | --- |
| M15-N01-FR-001 / AC-001 | 4, 5 | Shared semantic tokens/components; keyboard labels/focus and state across theme. |
| M15-N01-FR-002 / AC-002 | 2, 4.1, 5 | Role-appropriate links with server-enforced direct URL/owner/consent boundary. |
| M15-N01-FR-003 / AC-003 | 2 (Landing/Bands), 5 | No certificate/pass-fail/unmeasured accuracy claim. |
| M15-N01-FR-004 / AC-004 | 2 (Consent/Account), 2.1, 3.1 | Four account tabs and consent states from M11/M16-owned contracts; safe disabled/error recovery. |
| M15-N01-FR-005 / AC-005 | 2 (Assessment), 3 | Thirty-second prep/skip, preview/rerecord, upload recovery and server idempotency dependency. |
| M15-N01-FR-006,007 / AC-006 | 2 (Status/Report/History/Progress), 3 | Owner-scoped status/report/history; overall-only plus evidence/coverage; preserve null/insufficient. |
| M15-N01-FR-001,008 / AC-007 | 4, 5 | Local assets, approved viewports, zoom, print, reduced motion and no clipping/overflow. |
| M15-N01-FR-009 / AC-008 | Phase 06 evidence package | Browser JSON, revision, route/role/viewport/assertion, screenshot hash and console/network summary. |
| M15-N01-FR-001,004–006 / AC-009 | 2.1, 5 | No secret/path/foreign-owner leakage across pages and requests. |
| M15-N01-FR-001,008 / AC-010 | 2.1, 4.2–4.3 | Clean wheel contains local CSS/JS/font/icon/art and license/provenance metadata; coordinate with M16. |

## 7. Out of scope and readiness dependencies

- W5-N02 practice/lesson, W5-N03 teacher/blind rating, W5-N04 admin/billing, native mobile application and public deployment.
- New backend authorization, consent policy, QC/scoring/report/statistics/research computation or database schema.
- Third-party assets/services; any rubric/band mapping change.
- Route, payload, error-code, idempotency or evidence-source changes owned by M01/M02/M06/M09/M11/M13/M16.

Phase 05 cannot be ready until the applicable route/method/role/consent/error matrices and payload examples are versioned and reviewed by producer owners, including submit retry/idempotency semantics and M13/M09 insufficient-data rules. M16 must confirm local assets/package behavior. UI mock/fixture tests alone cannot close those dependencies or the Task Done Gate.

## 8. Phase 03 decisions and owner verdict

1. Native server-rendered HTML, CSS and small browser JavaScript: `APPROVED`.
2. Public routes `/` and `/bands`, and account route `/student/account?tab=...`: `APPROVED`.
3. State/report/security behavior and boundaries match Requirement v0.2: `APPROVED` as part of the Phase 03 verdict.

The project owner recorded `APPROVED theo đề xuất` on 2026-10-16. Producer contract owner reviews remain separate Phase 05 readiness items.

## Version history

- 2026-10-16 — v0.2 Phase 03 approved by project owner; native HTML/CSS/small JS and proposed public/account routes accepted. Proceed to Phase 04.

| Version | Date | Change |
| --- | --- | --- |
| v0.1 | 2026-09-25 | Broad M15 draft spanning N01–N04; not approved. |
| v0.2 | 2026-10-16 | Bounded to approved W5-N01 Requirement and Research; Phase 03 owner-approved native HTML/CSS/small JS and routes; route/state and cross-module inputs distinguished by approval status. |
