# M10 — Test Plan

**Version:** v0.1 · **STATUS:** DRAFT · **UT REQUIRED:** YES.

| Test ID | AC | Scenario | Expected | Level |
| --- | --- | --- | --- | --- |
| M10-TEST-001 | AC-001 | catalogue 5×3, version bump/same version | đủ, deterministic, không overwrite sai | Unit/repository |
| M10-TEST-002 | AC-002 | practice success/reject/retry | không scorer/band/queue/export, một result | Integration |
| M10-TEST-003 | AC-003 | no assessment, weakest criterion, completed path | fallback/rule/reason đúng | Unit |
| M10-TEST-004 | AC-004 | draft-edit-publish-republish-old attempt | immutable version và trace đúng | Repository/API |
| M10-TEST-005 | AC-005 | alignment, lemma, gap, VAD boundary, silence, free rounds | evidence/measurement đúng | Unit |
| M10-TEST-006 | AC-004 | seed fresh/rerun/version upgrade/teacher edits | 18/31, idempotent, không mất dữ liệu | Migration |
| M10-TEST-007 | AC-006 | due around VN midnight, pass/fail boxes | 1/3/7 deterministic | Unit/repository |
| M10-TEST-008 | AC-007 | achievement unlock/retry/delete/seen/cross-owner | effort-only, one unlock, owner only | Unit/API |
| M10-TEST-009 | AC-008 | lesson + review desktop/mobile, error/retry | journey hoàn tất, no-band DOM | Browser |
| M10-TEST-010 | Security | student authoring, foreign attempt/media, stale version | 403/404/409, no leak | API/security |
| M10-TEST-011 | Data | export/erasure/cleanup retry | đủ owned data, no secret/orphan | Integration |

Coverage: pure learning logic line ≥90%, branch ≥85%; repository/API/browser evidence bổ sung cho transaction, permission và user state.
