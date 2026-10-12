# M14 — Plan

**Version:** v0.1 · **STATUS:** DRAFT.

- Package `src/aicefr/billing/`: plans, quote, payments, licenses, gateway ports/adapters, service; repository in storage boundary.
- Build order: pure money/plan/license rules → schema → sandbox adapter → settlement → optional gateway adapters → APIs/UI → security/full tests.
- Store monetary values as integer minor units, timestamps UTC, display locale at UI only.
- CI injects fake HTTP and test keys; any outbound request causes test failure.
- Feature flag defaults billing off or sandbox; live mode requires separate user authorization beyond this plan.
- Rollback disables new orders, keeps paid license/receipt records readable and restores backup; never downgrade learning.
