# M05 — 06 Tasks

> **v0.2 · 26/09/2026 · APPROVED Phase 05 ngày 26/09/2026.** Theo [Plan v0.2](05-plan.md). Chưa phát prompt. Owner mọi task: **Sang**.

| Task ID | FR / AC | Test ID | Vùng file | Mục tiêu quan sát được | Dependency | Trạng thái |
| --- | --- | --- | --- | --- | --- | --- |
| M05-TASK-001 | FR-001..003 / AC-001..003 | 001–004, 008–014, 020, 021 | `scoring/scorer.py`, `scoring/coverage.py`, `tests/scoring/test_scorer.py`, `tests/scoring/test_coverage.py` | Thứ tự 8 bước; 3 status; provenance lệch → `NOT_EVALUATED`; 5 dòng coverage không có score, fluency = 1,0 khi đủ; Interaction null; tất định; log không có vector | TASK-002 | VERIFIED — nghiệm thu 27/09/2026 |
| M05-TASK-002 | FR-001, FR-002 / AC-001, AC-002 | 005, 006, 007, 015–019 | `scoring/artifact.py`, `scoring/ridge.py`, `tests/scoring/test_artifact.py`, `tests/scoring/test_ridge.py` | Loader kiểm hash và `unit_of_inference`; OOD kèm chi tiết; band/near-boundary/clip đúng tại biên; `scale=0` không chia 0 | — | VERIFIED — nghiệm thu 27/09/2026 |
| M05-TASK-003 | — | — | — | **Rút lại** (v0.2): metric chất lượng model ngoài phạm vi W2 | — | WITHDRAWN |
| M05-TASK-004 | FR-001 / AC-002 | 022 | `tests/scoring/test_integration_features.py` | FeatureSet từ extractor M04 đi qua scorer; ra `NOT_EVALUATED` + `OUT_OF_DISTRIBUTION` chỉ vì `log_uniq` | DEP-04 (M04-TASK-002), TASK-001 | VERIFIED — nghiệm thu 03/10/2026 |

**Ngoài scope mọi task:** sửa file dùng chung, code M03/M04, chép artifact vào repo (P05-D-001 = Option B), huấn luyện lại hay đổi hệ số.

## Handoff và hoàn tất

Như [M03 Tasks](../m03-asr/06-tasks.md#handoff-và-hoàn-tất).

**Trạng thái (03/10/2026):** TASK-002, 001 VERIFIED (27/09/2026); TASK-004 VERIFIED (03/10/2026); TASK-003 WITHDRAWN. **Phase 05 verdict:** APPROVED 26/09/2026 (Sang).

## W7 — Chuyển sang kiến trúc ba dịch vụ (W7-S02)

| Task | Deliverable | Tests | Trạng thái |
| --- | --- | --- | --- |
| M05-W7-S02 | `scoring/` (`artifacts`, `scorer`, `conformal`, `windows`), hiệu chuẩn band D052, `tools/{train_scorer,derive_model_v2,calibrate_bands,make_fake_models}.py`, artifact giả `tests/fixtures/models` | `test_artifacts`, `test_scorer`, `test_calibrated_scorer`, `test_windows`, `test_review_medium` | IN_REVIEW: PR `port/m03-m05-m09-cham` vào `migrate/w7-repo-goc` |

Chuyển từ `ThanhSangLouis/ai-assessor-cefr@059fa28`. Artifact Speak & Improve vẫn ngoài Git (`AICEFR_MODEL_DIR`, SHA-256 ghim trong `scoring/artifacts.py`), test dùng bộ tổng hợp. Code cũ của module được gỡ cùng PR; quyết định từng phần ở [kiểm kê W7-G1](../../../evidence/w7-migration/kiem-ke.md).
