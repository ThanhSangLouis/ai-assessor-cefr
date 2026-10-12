# M13 — Test Plan

**Version:** v0.1 · **STATUS:** DRAFT · **UT REQUIRED:** YES.

| Test ID | AC | Scenario | Expected | Level |
| --- | --- | --- | --- | --- |
| M13-TEST-001 | 001 | all patterns/priority/no-match/correction/unmeasured | exact classification/count | Unit |
| M13-TEST-002 | 001/002 | exposure 7/8/cap5/sort/cohort two users | null/rate/examples/redaction đúng | Unit/API |
| M13-TEST-003 | 003 | same/different seed, consent, role, minimum 4 | reproducible/balanced/422 | Unit/integration |
| M13-TEST-004 | 003/004 | score-only report via HTML/API; withdraw/consent/close | server gate, immediate restore | Integration/browser |
| M13-TEST-005 | 005 | survey phase/repeat/invalid/missing | 409/422/store đúng | API |
| M13-TEST-006 | 005 | pre-post min_days, bootstrap, Hedges, n=1 | deterministic metrics/null reasons | Unit |
| M13-TEST-007 | 005/008 | CSV after withdrawal | P-codes, no identifiers, counts match | Security |
| M13-TEST-008 | 006 | review lifecycle, 4/5 samples, >30m, Wilson | session/KPI boundaries đúng | Unit/integration |
| M13-TEST-009 | 007 | retest pairing 48h/n9/n10/manual source | SEM and validation đúng | Unit/API |
| M13-TEST-010 | 007 | all reliable-change states | formula/verdict/source đúng | Unit |
| M13-TEST-011 | 008 | role screens/mobile/wording | authorization, disclosure, no overclaim | Browser |
| M13-TEST-012 | Data | erasure/withdraw/audit | links removed, minimal audit preserved | Integration |
