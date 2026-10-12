# M14 — Specification

**Version:** v0.1 · **STATUS:** DRAFT.

## Model/lifecycle

- `PlanCode`: FREE/TRIAL/STANDARD/ADVANCED.
- `Entitlement`: feature set, student limit, warning quota, effective/grace expiry.
- `Quote`: immutable inputs, subtotal/discount/credit/total minor units, expiry.
- `Order`: PENDING/PAID/FAILED/CANCELLED/EXPIRED, gateway/mode/idempotency/checkout ref.
- `PaymentEvent`: normalized hash, signature result, payload redacted, received/processed status.
- `Receipt`: only from PAID order; immutable.

## Settlement transaction

Parse bounded payload → identify adapter → verify signature → normalize event → match order/gateway/mode/currency/amount/session → insert/dedupe event → compare-and-set order → install entitlement/receipt → audit, in one database transaction where possible. External redirect/session creation happens before local commit with recoverable pending state.

## Gateway boundary

`PaymentGateway.create_session`, `parse_return`, `parse_webhook`, optional `query_session`; adapters cannot update repository. HTTP client blocks redirects carrying authorization, enforces HTTPS/timeout/body caps, and is injected.

## License

Canonical payload + HMAC-SHA256; constant-time compare; key version lookup; expiry/organization/features/seat validation. Raw signing secret never leaves config boundary.

## API/UI

Admin plan overview, quote, order, checkout return, notification/webhook, receipt, license install/status and gateway setup status. Student routes never show plan upsell or deny learning.
