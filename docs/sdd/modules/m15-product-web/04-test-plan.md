# M15 — Test Plan — W5-N01

- **PHASE RECORD ID:** `M15-04-W5-N01-TP1`
- **SCOPE ID / TYPE / ROOT:** M15 / module / `docs/sdd/modules/m15-product-web/`
- **TASK:** W5-N01
- **VERSION / STATUS:** v0.2 / APPROVED — PHASE 04, 2026-10-16
- **BASE REVISION:** `d60e8a4b9f63a0b0259ada8971e23bafdb1df041` (`main`)
- **INPUT:** Requirement v0.2 `APPROVED` Phase 01; Research v0.2 reviewed with Phase 03; Specification v0.2 `APPROVED` Phase 03 (2026-10-16).
- **USER VERDICT PHASE 04:** `APPROVED`, 2026-10-16

## 1. Test objective and boundaries

This plan defines how to verify M15 N01 behavior after implementation and integration. It does not claim any result has already passed. All evaluation accounts, responses, audio and report payloads used by the tests must be synthetic fixtures created for testing.

M15 tests the rendered view, navigation, client interaction, packaging integration and browser evidence. The producer remains the authority for role, ownership, consent, submission/QC, score, report and evidence policy. UI fixtures can test presentation states; they cannot close a producer contract or prove server authorization. Those boundaries require the producer-owned tests and integrated local-server checks listed in section 5.

Accessibility checks are behavior-based: keyboard operation, visible focus, labels and instructions, readable state in both themes, status not conveyed by color alone, responsive/zoom behavior, reduced motion and print. This plan makes no WCAG or other conformance claim and sets no numeric contrast threshold.

## 2. Test levels and execution order

| Level | Purpose | Evidence |
| --- | --- | --- |
| Unit / template | Verify view-model rendering, semantic markup, state copy, local asset references and safe omission of unavailable fields. Any new deterministic N01 Python presentation logic gets focused tests. | pytest result and fixture identifiers. |
| Route / integration | Exercise actual WSGI routes with anonymous/student sessions, producer-owned response data and the approved route/method/role/consent contracts. Verify server decisions as well as rendered output. | pytest result, request/response assertions with secrets and personal data redacted. |
| Browser E2E | Run the public-to-student journey against the integrated local runtime. Exercise keyboard, errors, responsive states, audio controls where runtime permits, and inspect console/network behavior. | Browser JSON, screenshots with SHA-256, console/network summary and final revision. |
| Package | Build a wheel, inspect its contents, install it into a clean environment and confirm packaged pages/assets work without undeclared external asset requests. | Wheel inventory, install/startup result and local request log. This is shared with M16/W5-T04. |
| Manual behavior review | Inspect reading/action order, focus return, reduced-motion behavior, print output and legibility where automation cannot make a reliable judgment. | Checklist tied to route, viewport, revision and screenshot when applicable. |

Execution order: focused unit/template and route tests; relevant existing producer suites; full non-smoke suite; package check; integrated browser matrix; manual review. Do not mark a journey complete from a mocked page alone.

## 3. Acceptance trace and test cases

| Test ID | FR / AC trace | Scenario and assertions | Expected result | Level / owner boundary |
| --- | --- | --- | --- | --- |
| M15-TEST-001 | N01-FR-001 / AC-001 | Render every in-scope page's shared shell and controls in light/dark themes; exercise normal, disabled, loading, empty, success, validation-error and server-error states; tab and activate controls; inspect visible labels, instructions, focus order/visibility, text/control contrast and non-color status. | Common semantic tokens/components are used; keyboard actions work; text and controls remain readable and each state distinguishable without color alone; errors identify recovery action. No numeric contrast or conformance threshold is claimed. | Template + browser; M15. |
| M15-TEST-002 | N01-FR-002,004 / AC-002,004,009 | Open public/student routes directly as anonymous, signed-in student, missing-consent student and wrong/foreign owner; request own and foreign response IDs. Check both navigation and server result. | Navigation follows approved route/role contract. Server allows or denies independently of hidden links; foreign/private data is not rendered. Exact status/body expectations come from the versioned producer contract. | Route + integrated browser/security; M11/M01/M06 own server rules, M15 verifies presentation and boundary. |
| M15-TEST-003 | N01-FR-005 / AC-005 | With controlled clock, verify preparation counts 30 seconds and can be skipped; exercise supported recording/upload, preview, rerecord, submit, permission/device failure, rejected upload, interrupted request, retry/status recovery and rapid repeated submit. | Skip is explicit; student can preview, rerecord or submit; failure has a safe recovery step; no blind resubmit. A retry reuses an approved idempotency mechanism if M01 provides one; otherwise the UI checks status before offering another submit. | Browser + producer integration; M01/M02 own submit/QC/idempotency/format limits. |
| M15-TEST-004 | N01-FR-006,007 / AC-006,009 | Exercise progress/history/report loading, empty, unavailable, retry and completed states using own and foreign fixture IDs. Check overall result, criterion evidence/coverage, nulls, `insufficient_evidence`, monologue `Interaction=null`, audio evidence links and playback failure. | Only owner-authorized data is shown. Overall score/band is separate from per-criterion evidence/coverage; no missing value becomes zero; monologue Interaction stays null with `insufficient_evidence`; unavailable audio/report has a recovery state. | Template + route + integrated browser; M01/M06/M09/M13 and M08 when teacher-verified state is exposed. |
| M15-TEST-005 | M15-FR-005 / deferred N02 | Learning lesson/review/result/achievement/pronunciation flows. | Not in W5-N01; retain for N02 specification and review. | Deferred; no N01 verdict. |
| M15-TEST-006 | M15-FR-006 / deferred N03 | Teacher review, blind-rating, authoring and override/conflict. | Not in W5-N01; retain for N03 specification and review. | Deferred; no N01 verdict. |
| M15-TEST-007 | M15-FR-007 / deferred N04 | Admin accounts/configuration/data/rating/study/billing. | Not in W5-N01; retain for N04 specification and review. | Deferred; no N01 verdict. |
| M15-TEST-008 | N01-FR-001,008 / AC-001,007 | Check 360, 390, 768 and 1280 CSS-pixel widths, including 390×844 and 1280×800; test 200% zoom and long labels/errors. Inspect primary actions, bottom navigation, dialogs, focus and horizontal overflow. | Content and primary actions are not clipped, covered or unreachable; no horizontal page overflow; dialog focus remains usable. | Browser + manual; M15. |
| M15-TEST-009 | N01-FR-001,008 / AC-001,007 | Use keyboard only; open/close dialogs and verify focus return; inspect labels/status announcements; emulate `prefers-reduced-motion: reduce`; print each in-scope page. | Reading/action order is usable; focus is visible and restored; state is not color-only; nonessential motion stops without losing information; decorative art and nonessential navigation do not print. | Browser + manual behavior review; M15. |
| M15-TEST-010 | N01-FR-001,008 / AC-010 | Build a wheel from the integrated revision; inspect package inventory for templates, CSS, JS, font, icons/art and license/provenance metadata; install in a clean test environment and request packaged pages with external network blocked/observed. | Required product assets are present and locally served. Missing license/provenance or external asset dependency fails the package gate. Joint evidence and acceptance belong to M16/W5-T04, not N01 alone. | Packaging; M15 + M16. |
| M15-TEST-011 | N01-FR-009 / AC-008 | Validate browser-result JSON and screenshot hashes for every required route/role/viewport; compare stored hash with the screenshot bytes; inspect console, failed-request and external-request lists. | Result records exact final revision, route, role, viewport and assertions; each screenshot SHA-256 matches; console errors, failed requests and undeclared external requests are zero for required flows. | QA harness/tooling + evidence review; M15. |
| M15-TEST-012 | N01-FR-003,006,007 / AC-003,006,009 | Scan rendered DOM, URLs and captured client logs with synthetic canary secrets, paths and foreign-owner content. Check score/report wording, criterion output and all insufficient/null states. | No credential, token, client secret, internal filesystem path or foreign-owner content is present. No certificate/pass-fail/unmeasured-accuracy claim; no criterion score is inferred from aggregate; null/insufficient is never rendered as zero. | Static/template + route + browser/security; M15 presentation, producer owns server redaction/data policy. |
| M15-TEST-013 | N01-FR-004 / AC-004,009 | Visit all four approved account tabs (`profile`, `security`, `activity`, `data`) and consent accept/withdraw/version states; exercise loading, empty, configured, not-configured/disabled, success, session expiry and error/recovery. | Account/Google/session and consent content reflects M11's approved DTO/state contract; all four tabs are navigable; secrets/config values are not disclosed; withdrawal and expired session have a safe next step. | Template + route + browser; M11 owns account/session/consent behavior. |
| M15-TEST-014 | N01-FR-003 / AC-003 | Review landing, login and `/bands` copy against approved product wording; scan for prohibited promises and manually inspect claims where negation/context could produce a false match. | Pages explain the estimate/supporting-evidence purpose where relevant and make no certificate, pass/fail or unmeasured accuracy promise. A raw keyword match is reviewed in context; it is not by itself evidence of a violation. | Static copy check + owner/content review; M15, wording dependent on evidence owners. |

### 3.1 Scenario partitions

For every in-scope page, cover normal, empty, loading, unavailable/disabled, validation error, server/network error, retry/recovery and success where the page contract defines those states. Exercise boundary inputs from the approved DTOs (for example, absent/null evidence, stale consent version, expired session and foreign resource identifier); do not invent upload size, audio format, response-code or score limits in the UI test oracle.

Use both guest and student sessions, own and foreign synthetic resource IDs, and consent active/withdrawn/stale states where applicable. Producer-owned services must supply the expected result for direct unauthorized requests. Fixtures must be labeled as test data and must not be reported as CEFR evaluation evidence.

## 4. Test data, environment and evidence

- Run against the clean local package/application using loopback only. No production account, real learner record, personal audio or external API is allowed.
- Pin the tested git revision and record Python/runtime, browser and harness versions. Record fixture IDs and whether a state is mocked or returned by an integrated producer.
- Required browser evidence fields: revision, run timestamp, route, actor role/session state, viewport and zoom, theme/motion setting, assertion IDs/results, screenshot path and SHA-256, console errors, failed requests and external requests.
- Store restricted or bulky screenshots according to the module evidence manifest; the repo record must link to the controlled evidence and must not commit real audio or personal data.
- A test result is `NOT_RUN` until command output/evidence is captured. Do not report `PASS` from this plan or from the Phase 04 document review.

## 5. Dependencies and gates

| Producer / owner | Contract needed before integrated oracle is fixed | Verification boundary |
| --- | --- | --- |
| M11 identity | Account/session/Google state DTOs, consent version and accept/withdraw behavior, routes and failure states. | M11 verifies server/session policy; M15 verifies rendering and journey. |
| M01 assessment | Task/response/status/report routes, ownership errors, retry/idempotency semantics and example payloads. | M01 verifies persistence, ownership and no duplicate submission; M15 verifies user-facing flow and status recovery. |
| M02 audio/QC | Accepted media types/limits and rejection reason contract. | M02 verifies decoding/QC; M15 displays the contract reason/recovery. |
| M06 report/history/audio | Report/history/audio DTOs, route permissions and evidence references. | M06 verifies report data/ownership; M15 verifies display and audio navigation. |
| M08 review (if exposed) | Student-visible teacher verification and status contract. | M08 verifies review policy; M15 renders only the approved state. |
| M09 trust/evidence | Refusal, insufficiency and trust disclosures allowed in student report. | M09 verifies policy/provenance; M15 preserves approved wording/state. |
| M13 learning evidence | Source/sample/threshold and `NOT_EVALUATED`/insufficient states. | M13 verifies measurement contract; M15 only displays producer-approved values. |
| M16 runtime/package | Static asset/package inclusion and clean-install runtime path. | Shared M16/W5-T04 package gate; M15 cannot claim it independently. |

These are Phase 05 readiness dependencies, not reasons to invent mock contract behavior in Phase 04. Until reviewed contracts are available, only isolated presentation tests can be authored; the corresponding integrated tests remain blocked and cannot satisfy the task Done Gate.

## 6. Planned commands

The repository configures `python -m pytest`, `pytest-cov` and branch coverage in `pyproject.toml`. The targeted N01 web test directory and browser harness below are planned implementation deliverables; they do not exist yet and no command has been run for this plan.

```text
python -m pytest -q tests/web tests/api/test_student.py tests/api/test_identity_api.py tests/auth/test_w5_consent.py tests/auth/test_w5_accounts.py tests/auth/test_w5_account_security.py
python -m pytest -q -m "not smoke"
python -m pytest -q tests/web --cov=aicefr.portal --cov=aicefr.api.templates --cov-branch --cov-report=term-missing --cov-report=json:<evidence-dir>/m15-n01-coverage.json
python scripts/qa/m15_n01_browser.py --base-url http://127.0.0.1:8000 --evidence-dir <evidence-dir>
python -m pip wheel . --no-deps --wheel-dir <wheel-dir>
```

Replace angle-bracket paths with dedicated temporary/evidence directories. The browser harness must be implemented with the package/runtime integration, restricted to loopback, and must emit the schema in M15-TEST-011. Startup/fixture setup follows the reviewed producer/runtime contracts; this plan does not assume an unapproved API shape.

The existing coverage configuration enables branch measurement but defines no `fail-under` threshold. For Python logic added by N01, capture line/branch coverage for the changed modules and inspect uncovered branches; no project-wide percentage or threshold is introduced by this plan. HTML/CSS and browser-only behavior have no meaningful Python statement-coverage denominator and are verified through the template/browser/manual evidence above.

## 7. Phase 04 self-check and verdict

| Check | Result | Evidence |
| --- | --- | --- |
| Each N01 FR/AC has explicit test trace | PASS | Sections 3 and 3.1; test IDs 001–004, 008–014. |
| Test levels, states, negative paths and recovery defined | PASS | Sections 2–3. |
| Producer-owned behavior separated from M15 presentation | PASS | Sections 1 and 5; exact contract limits are not invented. |
| Commands, coverage applicability and alternative evidence defined | PASS | Sections 2, 4 and 6; no new threshold is claimed. |
| Accessibility target preserves owner decision | PASS | Section 1 and M15-TEST-001/008/009; behavior-based, no conformance claim. |
| Browser/package evidence schema and ownership defined | PASS | M15-TEST-010/011 and section 4; package jointly gated with M16. |
| Product implementation or tests executed | NOT_RUN | This is a Phase 04 documentation review; no product source, test or browser command was run. |

- **CODEX RECOMMENDATION:** `RECOMMEND APPROVAL` for Test Plan v0.2.
- **USER VERDICT (at initial review):** `PENDING`.
- **NEXT ACTION (at initial review):** Await project owner verdict; implementation prompt remains unissued.

## Addendum — Phase 04 verdict

- **Ngày:** 2026-10-16.
- **Verdict:** `APPROVED — chuyển Phase 05`.
- **Kết quả:** Phase 04 `APPROVED`; Phase 05 Plan/Tasks may be prepared. This verdict does not approve producer contracts or remove their readiness gates.
