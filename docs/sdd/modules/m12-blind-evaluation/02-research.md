# M12 — Research và Adaptation Map

**Version:** v0.1 · **STATUS:** DRAFT.
Nguồn: Sang `40907cc`, D030 (`research/assign.py`, `agreement.py`, rating repository/API/tests).

| REF | Finding/Pattern | Decision |
| --- | --- | --- |
| M12-REF-01 | seed-based two-rater assignment | ADAPT vào repository M16 |
| M12-REF-02 | central blind guard + `machine_seen` | ADOPT invariant, triển khai middleware/service target |
| M12-REF-03 | immutable one-time rating | ADAPT với unique/CAS transaction |
| M12-REF-04 | adjudication/reference rules | ADOPT sau user approval |
| M12-REF-05 | speaker bootstrap/agreement CLI | ADAPT, bắt buộc n/seed/insufficient state |

Threat model gồm IDOR, URL guessing, badge/count leakage, error text/timing, admin page leakage, stale open tab, export leakage và cache/back navigation. Blindness phải được bảo vệ ở service/repository query, không chỉ template.
