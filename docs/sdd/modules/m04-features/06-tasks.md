# M04 — 06 Tasks

> **v0.2 · 26/09/2026 · APPROVED Phase 05 ngày 26/09/2026.** Theo [Plan v0.2](05-plan.md). Chưa phát prompt. Owner mọi task: **Sang**.

| Task ID | FR / AC | Test ID | Vùng file | Mục tiêu quan sát được | Dependency | Trạng thái |
| --- | --- | --- | --- | --- | --- | --- |
| M04-TASK-001 | FR-001, FR-002 / AC-001, AC-002 | 001, 002, 003, 005, 006, 007, 008, 009 | `features/text.py`, `features/pauses.py`, `tests/features/test_text.py`, `tests/features/test_pauses.py` | 18 công thức khớp bảng kỳ vọng (1e-6); biên 0,30 s / 1,00 s / 10 token đúng; không có `0.0` giả | — | VERIFIED — nghiệm thu 27/09/2026 |
| M04-TASK-002 | FR-001..004 / AC-001..004 | 004, 010–015, 017, 018 | `features/extractor.py`, `tests/features/test_extractor.py` | FeatureSet 18 tên đúng thứ tự artifact, không `filler_ratio`; bảng dữ liệu thiếu; `FEATURE_VERSION_MISMATCH`, `VAD_VERSION_MISMATCH`; không lộ transcript; tất định | DEP-05 (M05-TASK-002), TASK-001 | VERIFIED — nghiệm thu 27/09/2026 |
| M04-TASK-003 | FR-004 / AC-004 | 016, S1 | `features/local.py` (adapter `SileroVadEngine`, thay tên dự kiến `silero_vad.py`; viết ở W3-TASK-005, unit `tests/features/test_local.py`), `tests/smoke/test_vad_smoke.py` | Silero 0,5 / 150 ms / 16 kHz; lỗi nạp → null, không fallback; smoke offline có evidence | DEP-03, DEP-06, TASK-002 | IMPLEMENTED — TEST-016 và smoke S1 PASS 11/10/2026 ([M04-EV-002](evidence/evidence-manifest.md)); chờ Phase 07 |

**Ghi chú:** TEST-016 là unit (loader giả raise `ImportError`) nên phần unit của TASK-003 không cần Silero thật; chỉ S1 cần DEP-03/04/06.

**Ngoài scope mọi task:** sửa file dùng chung, code M02/M03/M05, thêm hay bớt đặc trưng ngoài `feature_order`.

## Handoff và hoàn tất

Như [M03 Tasks](../m03-asr/06-tasks.md#handoff-và-hoàn-tất).

**Trạng thái (11/10/2026):** TASK-001, 002 VERIFIED (nghiệm thu 27/09/2026). TASK-003 IMPLEMENTED: DEP-06 đạt 11/10/2026; TEST-016 và smoke S1 PASS ([M04-EV-002](evidence/evidence-manifest.md)); chờ Phase 07–09. **Phase 05 verdict:** APPROVED 26/09/2026 (Sang).

## W7 — Chuyển sang kiến trúc ba dịch vụ (W7-S02)

| Task | Deliverable | Tests | Trạng thái |
| --- | --- | --- | --- |
| M04-W7-S02 | `features/extract.py`, `features/relevance.py` | `test_features`, `test_behavior`, `test_validity_shield` | IN_REVIEW: PR `port/m03-m05-m09-cham` vào `migrate/w7-repo-goc` |

Chuyển từ `ThanhSangLouis/ai-assessor-cefr@059fa28`. Artifact Speak & Improve vẫn ngoài Git (`AICEFR_MODEL_DIR`, SHA-256 ghim trong `scoring/artifacts.py`), test dùng bộ tổng hợp. Code cũ của module được gỡ cùng PR; quyết định từng phần ở [kiểm kê W7-G1](../../../evidence/w7-migration/kiem-ke.md).
