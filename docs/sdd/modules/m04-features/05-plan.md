# M04 — 05 Plan & Task Readiness (Kế hoạch)

> **v0.2 · 26/09/2026 · APPROVED Phase 05 ngày 26/09/2026.** Dựa trên [Requirement v0.2](01-requirement.md), [Specification v0.2](03-specification.md), [Test Plan v0.2](04-test-plan.md) — cả ba APPROVED; Research SKIPPED (M04-D-003). Chưa phát prompt Antigravity.

**Owner:** Sang. **Vùng file của M04:** `src/aicefr/features/`, `tests/features/`, `tests/smoke/test_vad_smoke.py`. File dùng chung thuộc Thắng — M04 chỉ yêu cầu.

## Kiến trúc

```text
Transcript (M03) ─┐
DecodedAudio (M02)┼─► FeatureExtractor.extract()
artifact (M05) ───┘     ├─ text_features(words, D)        (#1–8)
                        ├─ SileroVad.segments(pcm) ◄── FakeVad (tests/)
                        ├─ vad_features(segments, D, n)    (#9–18)
                        ├─ áp bảng dữ liệu thiếu
                        └─ sắp theo feature_order, kiểm feature_version / tham số VAD
                     ──► FeatureSet (M05)
```

| Thành phần | File dự kiến | Ghi chú |
| --- | --- | --- |
| Công thức text | `features/text.py` | Hàm thuần, chuẩn hóa token theo Spec |
| Công thức VAD | `features/pauses.py` | Hàm thuần trên danh sách segment |
| Extractor | `features/extractor.py` | Ghép, áp bảng dữ liệu thiếu, sắp thứ tự, kiểm nhất quán |
| Adapter Silero | `features/silero_vad.py` | Import lười; lỗi nạp → không fallback |

## Thứ tự triển khai

1. **M04-TASK-001** công thức text + VAD (hàm thuần).
2. **M04-TASK-002** extractor — cần `feature_order` từ loader M05 (M05-TASK-002).
3. **M04-TASK-003** adapter Silero + smoke.

## Dependency và trạng thái sẵn sàng (26/09/2026)

| ID | Cần gì | Của ai | Trạng thái | Chặn task |
| --- | --- | --- | --- | --- |
| DEP-01 | Skeleton `pyproject.toml`/`tests/`, `pytest-cov`, marker `smoke` | Thắng (Sang làm thay) | **Đã có** trên `main` a92fafe (PR #6, 26/09/2026) | — |
| DEP-02 | Contract chung có `FeatureValue`, `FeatureSet` theo M04 Spec; reason code `FEATURE_NOT_COMPUTABLE`, `TOO_FEW_WORDS`, `VAD_VERSION_MISMATCH` và **mới** `FEATURE_VERSION_MISMATCH` | Thắng (Sang làm thay) | **Đã có** — `src/aicefr/contracts.py` | — |
| DEP-03 | M02 xác nhận DecodedAudio 16 kHz mono (M03-O-002); Thắng review M04 là consumer thứ hai | Thắng | **Đạt** 28/09/2026 — PR #11 (M02-TASK-001) đưa `audio/decoder.py` lên `main`: mọi audio ra 16 kHz mono (`_OUTPUT_RATE_HZ = 16_000`, resample bằng soxr) | TASK-003 |
| DEP-04 | Dependency `silero-vad==6.2.1`, `numpy` trong `pyproject.toml` | Thắng (Sang làm thay) | **Đã có** — extra `vad` và lõi `numpy` trong `pyproject.toml` | — |
| DEP-05 | Loader artifact M05 trả `feature_order`, `feature_version`, `trained_with` | Sang (M05-TASK-002) | **Đã có** — M05-TASK-002 nghiệm thu 27/09/2026 | TASK-002 |
| DEP-06 | Audio có quyền dùng cho smoke, ngoài repo | Sang | **Đạt** 11/10/2026 cho smoke kỹ thuật — cùng audio với M03 ([M03-EV-004](../m03-asr/evidence/evidence-manifest.md)) | TASK-003 |

## Required checks mỗi task

- Test ID của task, rồi `python3 -m pytest -q -m "not smoke" tests/features`.
- Coverage **TP-D-001**: `--cov=aicefr.features --cov-branch`; line ≥ 90 %, branch ≥ 85 %; `silero_vad.py` loại khỏi ngưỡng (smoke S1).
- So 18 giá trị với bảng kỳ vọng của Test Plan, sai số 1e-6.
- `ruff`/typecheck nếu được cấu hình; kiểm diff chỉ trong vùng M04, không có token/transcript.

## Clean Code

Hàm công thức thuần, một công thức một chỗ; hằng `PAUSE_MIN_S = 0.30`, `LONG_PAUSE_S = 1.00`, `MIN_WORDS = 10` có tên; không lặp danh sách 18 tên trong code (đọc từ artifact — M04-FR-003); `None` không bao giờ thành `0.0` ngoài ba trường hợp `P` rỗng mà Spec quy định.

## Rủi ro, rollback, phục hồi

| Rủi ro | Xử lý |
| --- | --- |
| Silero kéo theo `torch` nặng vào unit test | Import lười; unit test dùng `FakeVad`; chỉ smoke nạp Silero |
| Engine local chép filler khác CTM huấn luyện (M03 Research I-02) | Ghi ở smoke; không đổi công thức trong task |
| Rollback | Một commit mỗi task; revert, không có dữ liệu cần di chuyển |

## Evidence và quyền

Như M03: prompt `prompts/`, raw report/coverage `evidence/`, review `reviews/`; Shared workspace, fingerprint `sdd-workspace-v2`; Antigravity không tải gì qua mạng, không sửa ngoài vùng M04.

## Definition of Ready

| Check | Kết quả |
| --- | --- |
| 1–2. Trace; boundary/data flow/lỗi | PASS |
| 3. Runtime/convention | PASS — `pyproject.toml` và CI đã có trên `main` |
| 4–6, 8–9 | PASS |
| 7. Dependency sẵn sàng | PASS cho TASK-001, 002 (TASK-002 làm sau M05-TASK-002 vì DEP-05). **BLOCKED** cho TASK-003: còn DEP-03 (16 kHz) và DEP-06 (audio) |

**CODEX CHECK RESULT:** PASS cho TASK-001, 002 (kiểm lại 26/09/2026); TASK-003 vẫn BLOCKED bởi DEP-03, DEP-06. **CODEX RECOMMENDATION:** RECOMMEND APPROVAL Phase 05; chỉ phát prompt cho task READY. **User verdict Phase 05:** APPROVED 26/09/2026 (Sang).

**Cập nhật dependency 03/10/2026:** DEP-03 đã đạt (PR #11). M04-TASK-003 chỉ còn BLOCKED bởi DEP-06 (audio có quyền dùng). Bản kiểm Definition of Ready ở trên giữ nguyên như đã ghi ngày 26/09/2026.

## Lịch sử phiên bản

| Phiên bản | Ngày | Thay đổi |
| --- | --- | --- |
| v0.1 | 25/09/2026 | Bản nháp đầu |
| v0.2 | 26/09/2026 | Theo Spec/Test Plan v0.2: 4 thành phần, 3 task, bảng dependency, DoR |
