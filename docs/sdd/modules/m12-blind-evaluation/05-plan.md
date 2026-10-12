# M12 — Plan

**Version:** v0.1 · **STATUS:** DRAFT.

- Sang owns assignment/agreement/statistical pure logic; Thắng owns schema/repository/privacy integration; Nguyên owns rate/admin screens.
- Schema: batch, assignment, rating, adjudication, machine_seen with unique constraints and consent-aware query indexes.
- Implement order: models/math → repository migration → central blind policy → APIs → report CLI → UI → security/browser/full regression.
- Blind payload gets snapshot/contract tests before UI work. Error and badge counts are part of leakage review.
- Rollback closes batch feature, retains immutable records and restores database backup; never expose machine data as fallback.

Coverage target for pure assignment/agreement ≥90% line/85% branch; all blind paths need negative authorization tests.
