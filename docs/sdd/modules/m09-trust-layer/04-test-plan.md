# M09 — Test Plan

**Version:** v0.1 · **STATUS:** DRAFT · Phase 04 chưa được duyệt.
**UT REQUIRED:** YES. Logic policy/calibration/guard phải có unit test; pipeline/report dùng integration test.

| Test ID | FR/AC | Kịch bản | Kết quả mong đợi | Cấp |
| --- | --- | --- | --- | --- |
| M09-TEST-001 | FR-001/AC-001 | English, non-English, confidence hai phía và đúng boundary | disposition/reason deterministic | Unit |
| M09-TEST-002 | FR-002/AC-002 | on-topic, off-topic, đọc đề, evidence rỗng | chỉ route/reason; score input/output không đổi | Unit |
| M09-TEST-003 | FR-003/AC-003 | artifact đúng, thiếu, sai hash/schema, one/multi-band | set/reason/failure đúng, không fallback | Unit |
| M09-TEST-004 | FR-004/AC-004 | năm chỉ báo và Interaction | không có criterion score; label/coverage đúng | Unit/API |
| M09-TEST-005 | FR-005/AC-005 | deserialize report cũ và report mới | render an toàn, provenance đúng | Integration |
| M09-TEST-006 | FR-006/AC-006 | chạy tool hai lần cùng seed/manifest | output/hash như nhau; confirmation-set guard | CLI |
| M09-TEST-007 | FR-007 | short/long windows, một window lỗi | aggregate/refusal/review đúng | Integration |
| M09-TEST-008 | AC-007 | retry cùng job/idempotency key | một report/candidate/audit | Repository/integration |
| M09-TEST-009 | Security | oversized/bad JSON/NaN/path/log scan | fail closed, không lộ path/transcript | Security |
| M09-TEST-010 | UI | bốn disposition trên desktop/mobile | wording, focus, recovery và disclosure đúng | Browser |

Commands dự kiến: targeted `pytest tests/asr tests/features tests/scoring tests/pipeline tests/report`; full suite và coverage theo M16. Policy coverage: line ≥90%, branch ≥85% cho logic mới; không chấp nhận critical branch chưa test chỉ vì global coverage đạt.
