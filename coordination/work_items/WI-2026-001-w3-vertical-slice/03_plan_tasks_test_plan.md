# WI-2026-001 W3 vertical slice - Plan, Tasks and Test Plan

| Field | Value |
| --- | --- |
| `work_id` | `WI-2026-001-w3-vertical-slice` |
| `version` | `V2` |
| `status` | `DRAFT_V2` |
| `approval_ref` | `null` |

## Plan

| Step | Module/files candidate | Dependency | Risk | Verification |
| --- | --- | --- | --- | --- |
| 1 | Project scaffold/config | V3 runtime decision | Dependency drift | Import/config tests |
| 2 | Typed contracts/reason codes | W2 candidate schema | Semantic mismatch | Schema tests |
| 3 | `ResponseProcessor` + fake adapters | Contracts | Shallow pass-through | Interface-level tests |
| 4 | QC/audio adapter | FFmpeg research | Platform variance | Synthetic fixture tests |
| 5 | ASR adapter | Approved local model config | Download/heavy runtime | Fake default + marked smoke |
| 6 | Feature/report/provenance | QC/ASR results | Invalid evidence propagation | Failure-path/invariant tests |
| 7 | HTTP/CLI thin adapter + docs | Processor stable | Rule duplication | Integration test |

## Tasks

- [ ] Resolve V1 open items and produce V2.
- [ ] Produce V3 with exact allowed files, dependencies and commands.
- [ ] Obtain explicit user approval for work ID + V3.
- [ ] Lock prompt against a resolvable base commit.
- [ ] Antigravity implements and records raw report.
- [ ] Codex reviews actual diff and reruns tests.
- [ ] User performs final acceptance.

## Test Plan

| ID | Path | Check | Expected result |
| --- | --- | --- | --- |
| T01 | Happy path | Valid synthetic fixture through interface | Completed report with version/hash |
| T02 | Invalid audio | Unsupported/corrupt/short/silence/clipping | Safe status + reason code; no fake score |
| T03 | ASR failure | Fake adapter raises controlled error | Error mapped; no empty-success transcript |
| T04 | Privacy | Log capture scan | No PII/audio/transcript/path leakage |
| T05 | Missingness | Monologue/invalid feature | Interaction/feature null with reason code |
| T06 | Verification | Attempt implicit verification | `teacher_verified` remains false |
| T07 | Reproducibility | Repeat same fixture/config | Deterministic observable output |
| T08 | Raw preservation | Hash before/after | Input unchanged; temp artifacts cleaned |
| T09 | Speaker leakage | N/A to single-response processing; schema guard test | No split logic added; pseudonymous speaker retained |
| T10 | Marked smoke | Optional local FFmpeg/ASR adapters | Offline run when dependency/model already present |

## Acceptance

- All required tests pass with raw evidence.
- No out-of-scope diff or prohibited data/dependency.
- Module has one small external interface; HTTP/CLI remain thin adapters.
- Technical report is not represented as CEFR assessment.
- Documentation/status remain honest about G1/G2 and human validation.
