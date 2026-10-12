# M16 — Research và Gap Analysis

**Version:** v0.1 · **STATUS:** DRAFT.
Target `3b2d2b7`; reference Sang `40907cc`; D043 `db00fe2` và sau đó bị loại.

## Target facts

Target đã có `aicefr.local`, WSGI, SQLite/blob, synchronous/local worker, pipeline/report/review, CLI và tests. Package data hiện chỉ khai báo `api/static/*.js`; W5 cần mở rộng. Không có practice/lessons/research/billing packages.

## Adaptation Map

| REF | Source pattern | Decision |
| --- | --- | --- |
| M16-REF-01 | Sang monolith repositories/routes | INSPIRE; giữ architecture target |
| M16-REF-02 | feature package/data inventory at 40907cc | ADAPT vào one composition root |
| M16-REF-03 | source tests/packaging | ADAPT required behavior, không copy test counts |
| M16-REF-04 | D043 services/platform/Postgres/RabbitMQ | REJECT |

Main risks: giant migration, three owners editing shared schema/base files, worker duplicate state, clean wheel missing assets, and final evidence from different revisions. Use contract PRs and staged additive migrations; final gate pins one fingerprint.
