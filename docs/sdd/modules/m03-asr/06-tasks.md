# M03 — 06 Tasks

> **v0.2 · 26/09/2026 · APPROVED Phase 05 ngày 26/09/2026.** Theo [Plan v0.2](05-plan.md). Chưa phát prompt. Owner mọi task: **Sang**.

| Task ID | FR / AC | Test ID | Vùng file | Mục tiêu quan sát được | Dependency | Trạng thái |
| --- | --- | --- | --- | --- | --- | --- |
| M03-TASK-001 | FR-001, FR-002 / AC-001, AC-002 | 001–007, 016 | `asr/service.py`, `asr/validation.py`, `tests/asr/test_service.py`, `tests/asr/test_validation.py` | `AsrService` trả Transcript đúng status/reason cho QC gate, lỗi engine, timestamp sai, `prob=None`, transcript rỗng, model thiếu; log không chứa transcript | TASK-003, TASK-004 | VERIFIED — nghiệm thu 27/09/2026 |
| M03-TASK-002 | FR-001 / AC-002 | S1, S2 | `asr/local.py` (adapter `FasterWhisperEngine`, thay tên dự kiến `faster_whisper_engine.py`; viết ở W3-TASK-005, unit `tests/asr/test_local.py`), `tests/smoke/test_asr_smoke.py` | Adapter faster-whisper `small` chạy offline; evidence smoke đủ trường S1; ghi `asr_conf_mean` (S2) | DEP-03, DEP-06, TASK-001 | IMPLEMENTED — smoke S1/S2 PASS 11/10/2026 ([M03-EV-004](evidence/evidence-manifest.md)); chờ Phase 07 |
| M03-TASK-003 | FR-002 / AC-001 | 008–012 | `asr/hallucination.py`, `tests/asr/test_hallucination.py` | 5 luật cho đúng kết quả tại và quanh ngưỡng; ngưỡng gom trong config `hallucination-v1` | — | VERIFIED — nghiệm thu 27/09/2026 |
| M03-TASK-004 | FR-003 / AC-003 | 013–015 | `asr/identity.py`, `tests/asr/test_identity.py` | Ánh xạ weight → identifier chuẩn; so `==`; `whisper-small.en` và weight lạ → `ASR_VERSION_MISMATCH` | — | VERIFIED — nghiệm thu 27/09/2026 |

**Ngoài scope mọi task:** sửa `pyproject.toml`, contract/reason code chung, pipeline, code của M02/M04/M05; tải model; dữ liệu người học.

**Thao tác của owner (không giao Antigravity):** DEP-05 tải weight `whisper-small` (CTranslate2) có chủ đích và ghi nguồn, license, SHA-256 vào `evidence/`; DEP-06 chuẩn bị audio có quyền dùng ngoài repo.

## Handoff và hoàn tất

- Mỗi task một prompt trong `prompts/` (mẫu `antigravity-handoff.md` §3), có base revision và fingerprint `sdd-workspace-v2`.
- Task chỉ xong khi có actual diff, lệnh test/coverage chạy thật, Phase 07 review, Phase 08 trên revision cuối và user verdict.

**Trạng thái (11/10/2026):** TASK-001, 003, 004 VERIFIED (nghiệm thu 27/09/2026). TASK-002 IMPLEMENTED: DEP-06 đạt 11/10/2026, smoke S1/S2 chạy thật và PASS ([M03-EV-004](evidence/evidence-manifest.md)); chờ Phase 07–09. **Phase 05 verdict:** APPROVED 26/09/2026 (Sang).

## W7 — Chuyển sang kiến trúc ba dịch vụ (W7-S02)

| Task | Deliverable | Tests | Trạng thái |
| --- | --- | --- | --- |
| M03-W7-S02 | `asr/` (`base`, `fake`, `vad`, `whisper_adapter`, `hallucination`), phần nhận dạng của `pipeline.py`, `services/speech/`, `tools/bench_asr.py` | `test_pipeline`, `test_behavior`, `test_reliability` | IN_REVIEW: PR `port/m03-m05-m09-cham` vào `migrate/w7-repo-goc` |

Chuyển từ `ThanhSangLouis/ai-assessor-cefr@059fa28`. Artifact Speak & Improve vẫn ngoài Git (`AICEFR_MODEL_DIR`, SHA-256 ghim trong `scoring/artifacts.py`), test dùng bộ tổng hợp. Code cũ của module được gỡ cùng PR; quyết định từng phần ở [kiểm kê W7-G1](../../../evidence/w7-migration/kiem-ke.md).
