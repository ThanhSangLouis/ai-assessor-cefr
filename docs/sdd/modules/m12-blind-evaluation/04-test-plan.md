# M12 — Test Plan

**Version:** v0.1 · **STATUS:** DRAFT · **UT REQUIRED:** YES.

| Test ID | AC | Scenario | Expected | Level |
| --- | --- | --- | --- | --- |
| M12-TEST-001 | 001 | assignment same seed/order variants/collisions | deterministic, two distinct raters | Unit/repository |
| M12-TEST-002 | 001/006 | consent/status/audio eligibility and withdrawal | include/exclude/recheck đúng | Integration |
| M12-TEST-003 | 002 | direct routes, queue/report/history/admin/export | no forbidden field/status leak | Security/API |
| M12-TEST-004 | 003 | machine seen before/after assignment, reopen, replace | excluded/void/reassigned safely | Integration |
| M12-TEST-005 | 004 | half-step/band/rationale/unrateable/replay/race | validate, one immutable row | Unit/repository |
| M12-TEST-006 | 005 | disagreement boundaries/conflict | adjudication đúng, distinct rater | Unit/integration |
| M12-TEST-007 | 006 | human-human/machine-human/reference/bootstrap | order/math/n/CI/seed đúng | Unit |
| M12-TEST-008 | 006 | n too small, all withdrawn | explicit insufficient, no fake metric | Unit/API |
| M12-TEST-009 | 007 | teacher/admin desktop/mobile conflict | usable, no DOM/network leakage | Browser |
| M12-TEST-010 | Data | erasure/export/audit | cascade allowed, minimal audit preserved | Integration |
