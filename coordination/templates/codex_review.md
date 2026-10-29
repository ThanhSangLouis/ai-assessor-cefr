# Codex implementation review

| Field | Value |
| --- | --- |
| `work_id` | `[required]` |
| `review_status` | `CODEX_REVIEW_PASSED/CODEX_REVIEW_FAILED/BLOCKED` |
| `base_commit` | `[verified]` |
| `head_commit` | `[verified]` |
| `report_ref` | `[05_antigravity_raw_report.md]` |
| `reviewer` | `Codex` |

## 1. Evidence inspected

- Actual diff command/result: [Điền]
- Working tree status: [Điền]
- Test commands rerun: [Điền]
- Artifacts/schema/migrations reviewed: [Điền]

## 2. Acceptance matrix

| Acceptance ID | Result | Evidence | Notes |
| --- | --- | --- | --- |
| [ID] | PASS/FAIL/BLOCKED | [file/test/artifact] | [Điền] |

## 3. Findings

| Finding ID | Priority | File/line | Problem | Required correction |
| --- | --- | --- | --- | --- |
| F001 | P0/P1/P2 | [path:line] | [Điền] | [Điền] |

## 4. Research/privacy review

- Speaker leakage: [PASS/FAIL/N/A + evidence]
- Evidence references/missingness: [PASS/FAIL/N/A + evidence]
- `teacher_verified`: [PASS/FAIL/N/A + evidence]
- PII/audio/secret/logging: [PASS/FAIL/N/A + evidence]
- Reproducibility/versioning: [PASS/FAIL/N/A + evidence]

## 5. Decision

[Why the implementation passes, fails, or is blocked. A pass means technical acceptance only; final user acceptance is still required.]

