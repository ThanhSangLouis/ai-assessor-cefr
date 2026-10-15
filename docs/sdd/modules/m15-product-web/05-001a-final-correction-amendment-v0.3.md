# M15-TASK-001A — Phase 05 Amendment v0.3 (final correction candidate)

**PHASE:** 05 — Plan & Task Readiness
**TASK:** `M15-TASK-001A` / W5-N01.1 một phần
**AMENDMENT:** `M15-05-001A-A2R3`
**PROPOSED PROMPT ID:** `M15-W5-N01-001A-A2R3` (not created or sent)
**STATUS:** `DRAFT` — Codex recommendation `RECOMMEND APPROVAL`; user verdict `PENDING`
**DATE:** 15/10/2026 (Asia/Bangkok)
**CURRENT CODE BASE:** branch `feat/SCRUM-73-W5-N01-Design-system-public-pages-account-assessment-student-flow`; A2R2 implementation is committed through `059984a`. Current repository HEAD while drafting is `072d101dd8614ee0bd1c8c95fd5db347a16d74a9`. The exact base revision for the eventual prompt must be the full HEAD recorded after this amendment receives its Phase 05 verdict.

## 1. Decision requested

Approve one final, bounded correction attempt `A2R3` for the open Phase 07 findings `M15-A2R2-R01`, `R02`, and `R03`. This amendment re-plans verification and evidence handling for `M15-TASK-001A`; it does not approve the still-pending Phase 07 verdict, mark the task complete, or start Phase 08.

The project owner authorized this one final correction using **Gemini 3.8 Flash (High)**, overriding the runner skill's Gemini 3.6 requirement, only after this Phase 05 amendment is approved. The eventual prompt must use that exact model for this attempt. If the CLI no longer offers it, stop and report `BLOCKED`; do not silently choose another model. No further correction attempt is included in this approval.

## 2. Inputs and unchanged product contract

- M15 Requirement v0.2, Research v0.3 (`RUN`), Specification v0.3, Test Plan v0.2, and Plan/Tasks v0.2 remain the approved product basis for 001A.
- Phase 05 amendment v0.2a remains limited to the earlier F06 markup change in `identity.py`; it does not authorize editing that file in A2R3.
- Phase 07 A2R2 Review Record is the source for R01–R03 and the unresolved evidence: [review](reviews/phase-07-review-a2r2-2026-10-15.md).
- No new route, API, payload, role, consent rule, form behavior, copy, score/rubric behavior, or producer contract is introduced. Existing FR/AC and Test Plan IDs remain in force; this amendment tightens TEST-008/011 evidence within the approved browser and traceability strategy.

## 3. Correction scope and file boundary

### Allowed writes

- `src/aicefr/api/templates.py` only if browser measurement proves an existing shell/layout defect prevents an approved action from being usable; limit any product change to the smallest CSS/semantic-shell fix.
- `scripts/qa/m15_shell_browser.py` for self-verified fingerprint capture and required-action/browser assertions.
- Existing or new focused tests under `tests/local/` for the amended QA contract.
- New attempt evidence under `docs/sdd/modules/m15-product-web/evidence/m15-task-001a-a2r3/`.
- The A2R3 implementation report inside that evidence directory.

### Forbidden writes

- `src/aicefr/api/identity.py`, `src/aicefr/portal/templates.py`, route/auth/service/storage code, `wsgi.py`, contracts, dependency/package configuration, other modules' files, `EDUZ/**`, and any unrelated task files.
- Do not edit Phase 01/03/04 artifacts or broaden W5-N01.1/001A into 001B, 002, or any W5-N02–N04 task. If a required fix crosses this boundary, stop and return `BLOCKED` with the observed diff and dependency.
- Preserve the existing M11 source lock. No AI session may edit `identity.py` during A2R3.

Any `templates.py` product change must preserve existing route, auth, payload, copy, and business behavior. If no product defect is measured, leave product source untouched and correct only QA/tests/evidence.

## 4. Required correction for each finding

### R01 — test failures, baseline comparison, and accurate coverage

1. Run the approved targeted test set and changed-file lint/format gates. Save command, working directory, Python/Ruff versions, exact environment, raw stdout/stderr, and exit code.
2. Run the exact non-smoke regression command on a clean worktree at the full A2R3 prompt base revision and on final A2R3 source in the same Windows environment and dependency set. Do not use `git reset`, `git clean`, or overwrite the shared task branch; use a separate temporary worktree for the clean base.
3. Save complete raw logs and normalized failed-test-ID lists for both runs. Compare exact ID sets in the report. Any final-only failure remains unclassified until reproduced or supported by direct evidence. A matching ID set shows no newly observed failing IDs; it does not turn exit code 1 into `PASS`.
4. To correct A2R2's disputed baseline claim, reproduce these three IDs from Review A2R2 R01—two reported final-only and one baseline-only—on clean worktrees at `6baf720f173b440eb961676b09ea290058a39b35` and the A2R3 prompt base: `tests/billing/test_billing_repository.py::test_distinct_connections_settle_one_event_once`, `tests/storage/test_jobs.py::test_two_connections_cannot_claim_same_job`, and `tests/storage/test_w5_storage_foundation.py::test_w5_restore_rejects_incomplete_or_escaping_manifests`. Save each exact raw command/output/exit code. If the results do not support the earlier claim, state that plainly; do not label the failures a Windows baseline without evidence.
5. Run the approved coverage command on final source and save raw log plus resulting JSON. Report statements and branches separately from JSON fields (`num_statements`, `covered_lines`, `missing_lines`, `num_branches`, `covered_branches`, `missing_branches`, `num_partial_branches`). Do not label partial branches as missing branches or combine unrelated percentages. If the command exits nonzero, mark the gate `VERIFICATION_FAILED` even when target-file coverage data exists.
6. Run repo `ruff check` and `ruff format --check` on clean A2R3 base and final source with the same tool version; compare exact formatted-file sets. Also report changed-file checks separately. Never describe a nonzero required gate as `PASS`.

Suggested regression commands (record the exact expanded command and temp path actually used):

```text
python -m pytest -q -m "not smoke" --basetemp <unique-a2r3-base-temp>
python -m pytest -q -m "not smoke" --basetemp <unique-final-temp>
python -m pytest -q -m "not smoke" --cov=aicefr --cov-branch --cov-report=term-missing --cov-report=json:<attempt-evidence>/coverage.json --basetemp <unique-final-coverage-temp>
ruff check src tests scripts
ruff format --check src tests scripts
```

### R02 — bind every result to the source that was actually tested

1. Before handoff, Codex records the full base revision, exact `sdd-workspace-v2` options, starting fingerprint, and helper's raw output. The start value is only a preflight value; do not present it as the final tested-source fingerprint.
2. At the end of all source edits and immediately before final gates, compute a distinct `tested_source_fingerprint`. Run the helper again with `--expect <tested_source_fingerprint>` and save its complete command/output. Freeze code after this point. If code changes, recompute and rerun every affected gate.
3. The browser QA script must calculate its own fingerprint with the same helper/options immediately before and after browser execution. It must compare both calculations to `--expected-source-fingerprint`, fail closed on mismatch, and write the computed value (not a caller-trusted pass-through value) into `browser-qa-results.json`. It must not emit a successful result JSON if either check fails.
4. Use one exact option set for all handoff/final verification commands: exclude `EDUZ/**`, `docs/sdd/modules/m15-product-web/evidence/m15-task-001a-a2r3/**`, and `docs/sdd/modules/m15-product-web/reviews/phase-07-review-a2r3-*.md`; designate the A2R3 prompt, `prompts/prompt-log.md`, and `07-status.md` as metadata files. Record the options verbatim in prompt, raw logs, report, browser JSON, and Codex Review Record. Do not add/remove an exclusion during this attempt. In the prompt and prompt log, store the starting value on the exact `WORKSPACE FINGERPRINT:` field that the helper normalizes. Store the tested value on the exact `WORKSPACE FINGERPRINT:` field in `07-status.md`; do not duplicate either value in other included metadata text.
5. Prompt, final report, browser JSON, final fingerprint log, and prompt/status records must distinguish `starting_workspace_fingerprint` from `tested_source_fingerprint`. All final-source references must match byte-for-byte. Codex independently recomputes the tested-source fingerprint on the received workspace before writing Phase 07 review/status updates. A mismatch means the evidence is not traceable and the task remains `CHANGES_REQUIRED`.

### R03 — route-specific primary actions, clipping, and hit testing

The QA script must assert expected selector count before filtering by visibility. Each required control must be present at the expected count, visible, enabled, have positive bounds, fit the active viewport after scrolling into view, avoid clipping by relevant ancestors, and pass a center-point `document.elementFromPoint` hit test (the hit may be the control or its descendant). Check every form's bounds and ancestor clipping as well. Keep the existing overflow, focus, contrast, color-scheme, reduced-motion, print, console/network, viewport, and screenshot checks.

Fixture routes and expected primary selectors/counts:

| Route | Required selector | Expected count | Fixture condition |
| --- | --- | ---: | --- |
| `/student/upload` | `form[data-recorder][action="/student/responses"] button[type="submit"]` | 1 | Existing upload form; direct-record controls may remain hidden when recording is disabled. |
| `/login` | `form[action="/login"] button[type="submit"]` | 1 | Existing login form. |
| `/student/consent` | `form[action="/student/consent/accept"] button[type="submit"]`; `form[action="/student/consent/withdraw"] button[type="submit"]` | 1 each | Both explicit consent choices are shown and checked. |
| `/student/status` | `main#main a[href^="/student/responses/"][href$="/report"]` | 1 | Fixture has `report_available=True`. |
| `/student/report` | `main#main button[data-seek-second]` | 1 | Add a deterministic evidence reference/comment to the QA fixture so this existing report action is rendered. |
| `/teacher/reviews` | `form[action$="/claim"] button[type="submit"]`; `main#main li a[href*="/teacher/reviews/"]:not([href$="/audio"])` | 1 each | One deterministic `PENDING` candidate. |
| `/teacher/review-detail` | `form[action$="/claim"] button`; `form[action$="/decision"] button[type="submit"]` | 1 each | Same deterministic `PENDING` candidate. |
| `/password-change` | `form[action="/password-change"] button[type="submit"]` | 1 | Existing F06-rendered page; QA-only, `identity.py` remains frozen. |

The JSON must include per route/viewport/color mode: required selector, expected/actual count, visibility/enabled state, bounds, ancestor-clipping result, hit-test result, form checks, and assertion result. A missing, hidden, disabled, clipped, off-viewport, or overlay-obscured required action must fail the run. Do not count navigation links as substitutes for a missing primary form action. Browser assertions remain UI fixture evidence; they do not assert backend integration or server authorization.

## 5. Gates, evidence, and stopping conditions

- Keep all previously approved targeted tests, changed-file lint/format, repository regression, coverage, and browser QA gates. Browser QA remains local loopback only, with the existing viewport/theme/accessibility matrix from Test Plan v0.2.
- Evidence must include raw per-gate logs, base/final failure-ID files, clean-base commit and environment details, coverage JSON, browser JSON, screenshot hashes, fingerprint preflight/final logs, and a concise report. The report may only claim what those artifacts support.
- If Playwright/browser dependencies are absent, a required command fails, a fingerprint mismatches, a required action is not rendered, or source lock is unclear, stop and record `NOT_RUN`, `BLOCKED`, or `VERIFICATION_FAILED` as appropriate. Do not infer `PASS` from a partial run.
- After the fingerprint is frozen, any source change requires a new final fingerprint and rerunning affected targeted, lint, regression, coverage, and browser gates. Codex reviews the actual diff and independently checks the recorded fingerprint before writing Phase 07.
- This is the one final correction attempt covered by this amendment. If any R01–R03 finding remains open, return `CHANGES_REQUIRED`; no additional correction attempt is authorized here. Phase 08 remains `NOT_STARTED` until the project owner supplies a Phase 07 verdict and all required gates have supported results.

## 6. Phase impact and Codex recommendation

No product requirement or behavior changes, so Phase 03 Specification and Phase 04 Test Plan do not need reapproval. The amendment narrows implementation to evidence/test corrections plus a minimal shell fix only if directly required by measured R03 failure. Existing Phase 05 approval for base 001A remains; this document amends only its execution/evidence plan for the final A2R3 attempt.

**CODEX CHECK:** `PASS` for bounded scope, finding trace, measurable checks, and stopping conditions.
**CODEX RECOMMENDATION:** `RECOMMEND APPROVAL` for this amendment only.
**USER VERDICT:** `PENDING` — no prompt or Antigravity implementation until explicit Phase 05 approval.
