# M04 — Review Records

**Hiện trạng:** Phase 07 attempt A1 **APPROVED** 26/09/2026 (Sang).

| Review ID | Prompt ID / Task ID | Base/Head revision | Diff/evidence đã kiểm tra | Finding và resolution | User verdict |
| --- | --- | --- | --- | --- | --- |
| 07-M04-A1 | M04-TASK-001, 002 (SCRUM-24, 25); Claude implement theo yêu cầu chủ dự án (không qua prompt Antigravity) | base `main` `ecb835f` → correction PR `[Phase 07]` | toàn bộ `src/aicefr/features/*, tests/features/*, tests/conftest.py`; evidence module; chạy lại test/lint | FINDING-07-A1-01, FINDING-07-A1-04, FINDING-07-A1-05 — xem dưới | APPROVED 26/09/2026 (Sang) |
| 07-M04-A2 | M04-TASK-003 (DEP-06, SCRUM-22); adapter từ W3-TASK-005, TEST-016 và smoke do Claude viết theo yêu cầu chủ dự án | base `main` `c427983` → nhánh `feat/SCRUM-22-m03-m04-smoke` (PR #32) | `src/aicefr/features/local.py`, `tests/features/test_local.py`, `tests/smoke/test_vad_smoke.py`, M04-EV-002; chạy lại test/lint/smoke | FINDING-07-M04-A2-01 MINOR RESOLVED, 07-M04-A2-02 INFO | PENDING |

## Review Record 07-M04-A1

```text
REVIEW ID: 07-M04-A1
TASK/PROMPT ID: M04-TASK-001, 002 (SCRUM-24, 25)
BASE/HEAD/FINGERPRINT: base main ecb835f (PR #7 e92c1cf, PR #8 ecb835f); không có fingerprint sdd-workspace-v2
  vì chủ dự án cho Claude implement trực tiếp, không phát prompt Antigravity — diff kiểm được qua Git
REVIEWED SCOPE/FILES: src/aicefr/features/*, tests/features/*, tests/conftest.py
CHECKLIST RESULT: scope/traceability PASS; design PASS; functionality PASS sau correction (còn MINOR follow-up);
  simplicity PASS; responsibility/coupling PASS; duplication/dead code PASS; naming PASS;
  comments/docs MINOR (README, FINDING-05); style PASS (ruff); error/security PASS (log không lộ transcript/vector,
  artifact chỉ JSON có hash ghim); tests PASS (hành vi, biên, regression) sau FINDING-01
FINDINGS: FINDING-07-A1-01 MAJOR RESOLVED, FINDING-07-A1-04 MINOR OPEN, FINDING-07-A1-05 MINOR OPEN
CHECKS RERUN BY CODEX: `pytest -q -m "not smoke"` → 123 passed, 10 skipped;
  `AICEFR_MODEL_DIR=… python -m pytest -q -m "not smoke" --cov=aicefr --cov-branch` → 133 passed, 99 %;
  `ruff check src tests`, `ruff format --check src tests` sạch
RESULT: PASS — không còn BLOCKER/MAJOR mở; MINOR còn mở là follow-up ngoài phạm vi task
EVIDENCE: evidence/evidence-manifest.md; PR sửa `[Phase 07] fix …`
```

## Findings

```text
FINDING ID: FINDING-07-A1-01
SEVERITY: MAJOR
CATEGORY: Test
LOCATION: pyproject.toml [tool.pytest.ini_options]
OBSERVED EVIDENCE: Chạy `pytest` trơn: 4 lỗi thu thập, `ModuleNotFoundError: No module named 'tests'` (test import `tests.features.fixtures`, `tests.asr.fixtures`); chỉ `python -m pytest` chạy được.
RISK/FAILED AC: Người khác trong nhóm (hoặc Antigravity) chạy `pytest` sẽ thấy lỗi dù code đúng.
REQUIRED CHANGE: Thêm `pythonpath = ["."]`.
STATUS: RESOLVED
RESOLUTION EVIDENCE: `pytest -q -m "not smoke"`: 123 passed, 10 skipped.
```
```text
FINDING ID: FINDING-07-A1-04
SEVERITY: MINOR
CATEGORY: Functionality
LOCATION: src/aicefr/features/pauses.py
OBSERVED EVIDENCE: Segment VAD chồng nhau hoặc vượt `duration_s` không bị kiểm; `vad_silence_ratio` có thể âm.
RISK/FAILED AC: Spec M04 không định; Silero thật trả segment hợp lệ.
REQUIRED CHANGE: Follow-up trong M04-TASK-003: adapter Silero kiểm segment (tăng dần, không chồng, trong [0, D]).
STATUS: ACCEPTED_RISK — chủ dự án chấp nhận để làm follow-up (26/09/2026)
RESOLUTION EVIDENCE: —
```
```text
FINDING ID: FINDING-07-A1-05
SEVERITY: MINOR
CATEGORY: Docs
LOCATION: README.md
OBSERVED EVIDENCE: README chưa hướng dẫn cài `.[dev]`, chạy test, biến `AICEFR_MODEL_DIR`.
RISK/FAILED AC: Người mới không biết đặt artifact ở đâu; test cần artifact bị SKIP mà không rõ lý do.
REQUIRED CHANGE: Follow-up trong SCRUM-44 (build/run guide).
STATUS: ACCEPTED_RISK — chủ dự án chấp nhận để làm follow-up (26/09/2026)
RESOLUTION EVIDENCE: —
```

## Khác Test Plan — chủ dự án đã chấp nhận (26/09/2026)

- D2: so ngưỡng 0,30 s / 1,00 s có sai số 1e-9 (lỗi dấu phẩy động, timestamp VAD ở mức mili-giây).
- D3: M04-TEST-008 chỉ kiểm D = 0 và M04-TEST-009 đưa NaN qua segment VAD, vì contract đã chặn D < 0 và `prob` NaN.
- M04-TEST-016 thuộc M04-TASK-003 (BLOCKED), chưa làm.

Codex lưu Phase 07 review record tại đây sau khi kiểm tra actual diff, test và evidence. Chỉ người dùng ghi verdict phê duyệt.

## Review Record 07-M04-A2 (11/10/2026)

```text
REVIEW ID: 07-M04-A2
TASK/PROMPT ID: M04-TASK-003 (SCRUM-22 cho DEP-06)
BASE/HEAD: base main c427983; head = nhánh feat/SCRUM-22-m03-m04-smoke (PR #32)
REVIEWED SCOPE/FILES: src/aicefr/features/local.py, tests/features/test_local.py, tests/smoke/test_vad_smoke.py
CHECKLIST RESULT: functionality PASS — Silero 6.2.1 bundled JIT (`onnx=False`), threshold 0,5, min_silence 150 ms,
  chỉ nhận float32 mono 16 kHz hữu hạn; lỗi nạp → `VadUnavailableError`, extractor trả 10 đặc trưng `vad_*` rỗng kèm
  FEATURE_NOT_COMPUTABLE, không VAD dự phòng (REF-03, TEST-016); tests PASS; dead code MINOR (đã sửa)
FINDINGS: FINDING-07-M04-A2-01 MINOR RESOLVED; FINDING-07-M04-A2-02 INFO
CHECKS RERUN: `pytest -q -m "not smoke"` → 309 passed, 13 skipped; có artifact Ridge → 322 passed;
  smoke `-m smoke tests/smoke` (audio DEP-06, chặn mạng) → 2 passed, 0 lần thử kết nối;
  `ruff check src tests scripts`, `check_md_links.py`, `check_forbidden_files.py`, gitleaks sạch
RESULT: PASS — đề xuất APPROVE
USER VERDICT: PENDING
```

```text
FINDING ID: FINDING-07-M04-A2-01
SEVERITY: MINOR
CATEGORY: Simplicity
LOCATION: src/aicefr/features/local.py `SileroVadEngine.segments`
OBSERVED EVIDENCE: khối `try: … except Exception: raise` không đổi hành vi.
REQUIRED CHANGE: bỏ khối thừa.
STATUS: RESOLVED
RESOLUTION EVIDENCE: tests/features PASS; smoke M04-TEST-S1 PASS sau khi sửa.
```
```text
FINDING ID: FINDING-07-M04-A2-02
SEVERITY: INFO
CATEGORY: Test data
LOCATION: M04-EV-002
OBSERVED EVIDENCE: giọng tổng hợp không có khoảng ngừng ≥ 0,30 s nên các đặc trưng ngừng nghỉ bằng 0.
REQUIRED CHANGE: không; chạy lại S1 khi có audio người nói thật có đồng ý.
STATUS: ACCEPTED
```
