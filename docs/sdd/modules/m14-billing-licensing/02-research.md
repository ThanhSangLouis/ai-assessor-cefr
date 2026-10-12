# M14 — Research và Adaptation Map

**Version:** v0.1 · **STATUS:** DRAFT.
Nguồn: Sang `40907cc`, D034/D035; chỉ đọc.

| REF | Pattern | Decision |
| --- | --- | --- |
| M14-REF-01 | plan/standing/entitlement rules | ADAPT; learning invariant ưu tiên |
| M14-REF-02 | quote/order/settle service | ADAPT với Decimal/minor-unit và repository target |
| M14-REF-03 | sandbox/VNPay/Stripe/MoMo adapters | ADAPT; network ports mocked, test only |
| M14-REF-04 | signature/replay/event persistence | ADOPT security invariant |
| M14-REF-05 | signed license | ADAPT với key version/audit/config target |

External gateway docs/behavior có thể thay đổi; W5 chỉ xác minh adapter contract bằng fixture/mock và sandbox khi credential do user tự cấu hình. Không commit hoặc gửi credential qua chat.
