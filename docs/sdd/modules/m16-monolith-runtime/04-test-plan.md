# M16 — Test Plan

**Version:** v0.1 · **STATUS:** DRAFT · **UT REQUIRED:** YES for worker/migration/data policy.

| Test ID | AC | Scenario | Expected | Level |
| --- | --- | --- | --- | --- |
| M16-TEST-001 | 001 | fresh + v4 migration + rerun | schema/count/hash preserved/idempotent | Migration |
| M16-TEST-002 | 002 | injected failure each migration group | rollback and restored boot | Migration/ops |
| M16-TEST-003 | 003 | two workers/lease expiry/crash/retry/max retry | one claim/result, legal states | Repository/integration |
| M16-TEST-004 | 003 | duplicate enqueue/callback/audit | idempotent no duplicates | Integration |
| M16-TEST-005 | 004 | clean wheel install/boot/model present-absent | correct journey/readiness/no fake | Packaging/smoke |
| M16-TEST-006 | 005 | export/erase preview-confirm/blob failure/retry | correct manifest, no orphan/secret | Integration |
| M16-TEST-007 | 005 | retention dry/apply + backup/restore | safe counts/hash/readability | Ops |
| M16-TEST-008 | 006 | health/error/log/metric sensitive scan | no path/PII/secret, bounded labels | Security |
| M16-TEST-009 | 007 | format/lint/tests/coverage/build on final revision | all PASS/no hidden skip | CI |
| M16-TEST-010 | 008 | repository dependency/path/config scan | no D043 artifact | Static |
| M16-TEST-011 | 007 | full three-role browser matrix | same revision result/evidence | Browser |

Coverage policy: no regression from measured G0 baseline; new critical worker/migration/auth/payment/privacy logic has success + refusal/failure branch tests; global floor 70% is only a floor.
