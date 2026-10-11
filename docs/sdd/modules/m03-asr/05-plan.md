# M03 — 05 Plan & Task Readiness (Kế hoạch)

> **v0.2 · 26/09/2026 · APPROVED Phase 05 ngày 26/09/2026.** Dựa trên [Requirement v0.2](01-requirement.md), [Research v0.2](02-research.md), [Specification v0.2](03-specification.md), [Test Plan v0.2](04-test-plan.md) — cả bốn APPROVED. Chưa phát prompt Antigravity.

**Owner:** Sang. **Vùng file của M03 (chỉ sửa trong vùng này):** `src/aicefr/asr/`, `tests/asr/`, `tests/smoke/test_asr_smoke.py`. File dùng chung (`pyproject.toml`, contract/reason code, `conftest.py`, pipeline) thuộc Thắng — M03 chỉ **yêu cầu**, không sửa.

## Kiến trúc

```text
DecodedAudio + QCResult (M02) ──► AsrService.transcribe()
                                   ├─ QC gate (REJECT → NOT_RUN)
                                   ├─ AsrEngine port ◄── FasterWhisperEngine (adapter thật)
                                   │                 ◄── FakeAsrEngine (chỉ trong tests/)
                                   ├─ validate_timestamps()
                                   ├─ detect_hallucination()   (config hallucination-v1)
                                   └─ resolve_asr_model()       (bảng ánh xạ, so ==)
                                  ──► Transcript (M04, M06)
```

| Thành phần | File dự kiến | Ghi chú |
| --- | --- | --- |
| Port + service | `asr/service.py` | Không import `faster_whisper` ở mức module |
| Validator timestamp | `asr/validation.py` | Hàm thuần |
| Bộ phát hiện hallucination | `asr/hallucination.py` | Hàm thuần; ngưỡng là hằng có tên, gom trong một config có version |
| Ánh xạ identifier | `asr/identity.py` | Bảng ánh xạ + so `==` với `trained_with.asr_model` |
| Adapter faster-whisper | `asr/faster_whisper_engine.py` | Import lười; `local_files_only`; không tải mạng |

Data flow, trạng thái, lỗi và reason code theo đúng [Specification](03-specification.md); Plan không thêm hành vi.

## Thứ tự triển khai

1. **M03-TASK-003** hallucination và **M03-TASK-004** ánh xạ identifier — hàm thuần, không phụ thuộc nhau.
2. **M03-TASK-001** service + validator, dùng hai hàm trên.
3. **M03-TASK-002** adapter thật + smoke — chỉ sau khi đủ điều kiện ngoài (bảng Dependency).

## Dependency và trạng thái sẵn sàng (26/09/2026)

| ID | Cần gì | Của ai | Trạng thái | Chặn task |
| --- | --- | --- | --- | --- |
| DEP-01 | `pyproject.toml`, layout `src/aicefr/` + `tests/`, `pytest`, `pytest-cov`, marker `smoke` | Thắng (Sang làm thay) | **Đã có** trên `main` a92fafe (PR #6, 26/09/2026) | — |
| DEP-02 | Contract chung có `Word`, `Transcript`, `AsrStatus` theo M03 Spec và reason code `ASR_FAILED`, `ASR_EMPTY_TRANSCRIPT`, `ASR_HALLUCINATION`, `ASR_VERSION_MISMATCH` | Thắng (Sang làm thay) | **Đã có** — `src/aicefr/contracts.py` trên `main` a92fafe (PR #6, 26/09/2026) | — |
| DEP-03 | M02 xác nhận DecodedAudio 16 kHz mono (M03-O-002) | Thắng | **Đạt** 28/09/2026 — PR #11 (M02-TASK-001) đưa `audio/decoder.py` lên `main`: mọi audio ra 16 kHz mono (`_OUTPUT_RATE_HZ = 16_000`, resample bằng soxr) | TASK-002 |
| DEP-04 | Dependency `faster-whisper` trong `pyproject.toml` | Thắng (Sang làm thay) | **Đã có** — extra `asr` trong `pyproject.toml` | — |
| DEP-05 | Weight `whisper-small` dạng CTranslate2 tải có chủ đích, ghi nguồn/license/SHA-256 — **thao tác của Sang**, không giao Antigravity | Sang | **Đã làm** — [M03-EV-001](evidence/evidence-manifest.md#m03-ev-001--weight-whisper-small-ctranslate2), 26/09/2026 | — |
| DEP-06 | Audio có quyền dùng cho smoke, đặt ngoài repo | Sang | **Đạt** 11/10/2026 cho smoke kỹ thuật — giọng tổng hợp do nhóm tạo bằng lệnh `say` của macOS (giọng Samantha, tốc độ 165), đọc một đoạn tiếng Anh nhóm tự viết; WAV 16 kHz mono, 38,541 s, SHA-256 `290f0436…a7427`; đặt ngoài repo (`~/aicefr-smoke/`). Không phải giọng người học, không có PII ([M03-EV-004](evidence/evidence-manifest.md)) | TASK-002 |
| DEP-07 | `trained_with.asr_model` từ loader của M05 | Sang (M05-TASK-002) | **Đã có** — M05-TASK-002 nghiệm thu 27/09/2026 | TASK-004 (có thể dùng dict giả trong test) |

## Required checks mỗi task

- Chạy đúng Test ID của task: `python3 -m pytest -q -m "not smoke" tests/asr -k <tên test>` rồi cả `tests/asr`.
- Coverage theo **TP-D-001**: `--cov=aicefr.asr --cov-branch`; line ≥ 90 %, branch ≥ 85 % trên logic thuần; `faster_whisper_engine.py` loại khỏi ngưỡng (kiểm bằng smoke).
- `ruff` và typecheck nếu `pyproject.toml` của Thắng cấu hình; không tự thêm tool.
- Kiểm diff: chỉ file trong vùng M03; không có audio, transcript, weight, secret.

## Clean Code

Type hints cho mọi API public; hàm thuần tách khỏi I/O; ngưỡng là hằng có tên, không số rải rác; không truyền `dict` vô kiểu giữa module; không bắt `Exception` rồi nuốt — lỗi phải thành status/reason theo Spec.

## Rủi ro, rollback, phục hồi

| Rủi ro | Xử lý |
| --- | --- |
| Engine tự tải model qua mạng | Adapter dùng đường dẫn local; TEST-006 và smoke tắt mạng bắt lỗi này |
| `asr_conf_mean` từ engine local lệch khoảng huấn luyện (Research I-01) | Ghi ở smoke S2; báo owner M05; không chỉnh Spec trong task |
| Contract chung đổi sau khi M03 code xong | M03 chỉ dùng type từ contract; đổi contract → Phase 03 của các scope liên quan stale theo quy tắc SDD |
| Rollback | Mỗi task một commit có Task ID trên nhánh riêng; revert commit, không có migration dữ liệu |

## Evidence và quyền

- Prompt lưu `prompts/`, raw report + lệnh + exit code + coverage lưu `evidence/`, review lưu `reviews/`.
- Handoff: Shared workspace; fingerprint `sdd-workspace-v2` tính lúc phát prompt.
- Antigravity không được: tải model, gọi mạng, sửa file ngoài vùng M03, commit audio/transcript.

## Definition of Ready

| Check (quality-gates §5) | Kết quả |
| --- | --- |
| 1. Trace FR/AC → Test → Task | PASS — xem [06-tasks.md](06-tasks.md) |
| 2. Boundary, data flow, lỗi, dependency | PASS |
| 3. Hợp runtime/package manager/convention | PASS — `pyproject.toml` (Python ≥ 3.11, pytest, pytest-cov, marker smoke) và CI (PR #5) đã có trên `main` |
| 4. Rủi ro, rollback, Clean Code, required checks | PASS |
| 5–6. Task liên kết version đã duyệt; mục tiêu, scope, vùng file rõ | PASS |
| 7. Dependency sẵn sàng | PASS cho TASK-001, 003, 004. **BLOCKED** cho TASK-002: còn DEP-03 (16 kHz, owner M02) và DEP-06 (audio có quyền dùng) |
| 8. Task đủ nhỏ | PASS — 4 task, mỗi task một vòng implement–review |
| 9. Evidence/report và quyền rõ | PASS |

**CODEX CHECK RESULT:** PASS cho TASK-001, 003, 004 (kiểm lại 26/09/2026 sau khi DEP-01/02 có trên `main`); TASK-002 vẫn BLOCKED bởi DEP-03, DEP-06. **CODEX RECOMMENDATION:** RECOMMEND APPROVAL Phase 05; chỉ phát prompt cho task READY, TASK-002 chờ đủ dependency. **User verdict Phase 05:** APPROVED 26/09/2026 (Sang).

**Cập nhật dependency 03/10/2026:** DEP-03 đã đạt (PR #11). M03-TASK-002 chỉ còn BLOCKED bởi DEP-06 (audio có quyền dùng). Bản kiểm Definition of Ready ở trên giữ nguyên như đã ghi ngày 26/09/2026.

## Lịch sử phiên bản

| Phiên bản | Ngày | Thay đổi |
| --- | --- | --- |
| v0.1 | 25/09/2026 | Bản nháp đầu |
| v0.2 | 26/09/2026 | Theo Spec/Test Plan v0.2: kiến trúc 5 thành phần, 4 task, bảng dependency, DoR |
