# M15 — Phase 05 review: final correction amendment for 001A

**PHASE RECORD ID:** `M15-05-001A-A2R3`
**SCOPE:** `M15-TASK-001A` / W5-N01.1 một phần
**SUBJECT:** [Phase 05 Amendment v0.3](../05-001a-final-correction-amendment-v0.3.md)
**BASE WHILE DRAFTING:** `1236d151a225d9b9ce2bde95f4218cd69b40c98a`; the prompt base will be the full HEAD after this approval record is committed.
**SOURCE REVIEWED:** Phase 07 A2R2 Review Record and current committed implementation/evidence on SCRUM-73 branch.
**USER VERDICT:** `APPROVED` — project owner response “APPROVED Phase 05 Amendment v0.3” on 15/10/2026 (Asia/Bangkok). **CODEX RECOMMENDATION:** `RECOMMEND APPROVAL`.

## Phase 05 checks

| Check | Result | Evidence / boundary |
| --- | --- | --- |
| Finding-to-test trace | PASS | R01–R03 remain tied to existing TEST-001/008/011 and AC-001/004/008. The amendment adds measurable assertions without changing product behavior. |
| Scope and ownership | PASS | Allowed files and forbidden `identity.py`/EDUZ/other-module files are explicit. Existing M11 lock is preserved. |
| Implementation DoR | PASS | A2R2 code exists in the branch; the exact A2R3 base SHA is deferred until after amendment verdict and before prompt creation. |
| Verification reproducibility | PASS with gates | Clean-base and final runs share one environment; exact fail-ID sets, exact lint sets, raw output/exit codes, distinct start/tested fingerprints, and QA self-verification are required. |
| Browser assertions | PASS | All eight fixture routes have required primary selectors/counts; hidden/missing/disabled/clipped/obscured controls fail. Existing test matrix remains. |
| Contract and phase impact | PASS | No route/API/auth/payload/rubric changes; Phase 03/04 remain unchanged. Producer-dependent tasks remain blocked and out of scope. |
| Correction budget / model | PASS with user decision | One final A2R3 correction only. Project owner explicitly authorized Gemini 3.8 Flash (High) as a one-attempt runner override after this amendment is approved. |

## Findings and residual gates

The amendment correctly refuses to recast a nonzero full-suite/coverage gate as `PASS`. Even an exact match with the clean-base failure set must be reported with its real exit code and exact IDs; the Phase 07 reviewer and project owner decide whether the remaining environment limitation prevents acceptance. If test IDs differ or evidence cannot establish source identity, the attempt remains `VERIFICATION_FAILED`/`CHANGES_REQUIRED`.

The report page currently renders no `[data-seek-second]` control for the A2R2 QA fixture because it supplies no evidence reference/comment. The amendment closes that test gap by requiring one deterministic fixture comment/evidence reference; this is test data only and does not change report behavior.

## Decision

**CODEX CHECK RESULT:** `PASS` for amendment readiness.
**CODEX RECOMMENDATION:** `RECOMMEND APPROVAL` for the Phase 05 amendment only.
**USER VERDICT:** `APPROVED` on 15/10/2026 (Asia/Bangkok), for this amendment and one A2R3 attempt only. This does not approve Phase 07/08 or complete `M15-TASK-001A`.
**NEXT:** Codex records the final post-approval base SHA, creates and logs the A2R3 prompt, captures the starting workspace fingerprint with the specified options, then hands the single attempt to Antigravity using the explicitly authorized Gemini 3.8 Flash (High). No further correction attempt is authorized by this verdict.
