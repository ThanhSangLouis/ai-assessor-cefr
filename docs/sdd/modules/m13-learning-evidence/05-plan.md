# M13 — Plan

**Version:** v0.1 · **STATUS:** DRAFT.

- Code: `src/aicefr/pronunciation/`, `research/`, review session hooks, study/measurement repositories, portal/API and UI blocks.
- Build order: pure math/rules → schema/repository → consent/report gate → APIs → UI → privacy/statistical regression.
- Inject clock/random seed; never use global RNG/time in pure functions.
- Schema includes study, participant, survey, review_session, measurement_error; indexes for consent-aware/report queries; no raw PII.
- All results serialize nullable metrics with explicit insufficient reason; UI cannot infer zero from null.
- Rollback closes study feature and preserves immutable events; withdrawing/consent safety path remains functional.

Review responsibilities: Sang validates math/rules; Thắng validates storage/privacy/consent; Nguyên validates wording/states; no one may claim field-study evidence from test fixtures.
