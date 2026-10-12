# M14 — Test Plan

**Version:** v0.1 · **STATUS:** DRAFT · **UT REQUIRED:** YES.

| Test ID | AC | Scenario | Expected | Level |
| --- | --- | --- | --- | --- |
| M14-TEST-001 | 001 | all plans/expiry/grace/student learning | monotonic staff features, learning unchanged | Unit/API |
| M14-TEST-002 | 002 | monthly/yearly/proration/rounding/zero-credit | exact minor units and totals | Unit |
| M14-TEST-003 | 003 | forged signature/amount/currency/gateway/mode/session | rejected, no entitlement | Unit/integration |
| M14-TEST-004 | 003/004 | duplicate/reordered/browser+webhook/late success | one settlement/receipt, legal transition | Repository |
| M14-TEST-005 | 004 | cancel/fail/timeout/expired retry | safe visible state/recovery | Integration/browser |
| M14-TEST-006 | 005 | mock transport/no config/live config | no network, disabled or hard fail | Unit/security |
| M14-TEST-007 | 006 | license valid/forged/expired/wrong key/limits | only valid installs once | Unit/integration |
| M14-TEST-008 | 007 | API/DOM/log/DB/export scan | no secret/instrument/PII | Security |
| M14-TEST-009 | UI | admin sandbox purchase desktop/mobile | quote→paid/failed/pending/receipt | Browser |
| M14-TEST-010 | Migration | existing DB + event uniqueness/rollback | preserve and no duplicate | Migration |
