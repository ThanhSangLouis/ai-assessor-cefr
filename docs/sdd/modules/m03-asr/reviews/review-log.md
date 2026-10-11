# M03 — Review Records

**Hiện trạng:** Phase 07 attempt A1 **APPROVED** 26/09/2026; attempt A2 (follow-up 07-A1-03) **APPROVED** 03/10/2026 (Sang); attempt A3 (M03-TASK-002) PASS, chờ verdict của Sang.

| Review ID | Prompt ID / Task ID | Base/Head revision | Diff/evidence đã kiểm tra | Finding và resolution | User verdict |
| --- | --- | --- | --- | --- | --- |
| 07-M03-A1 | M03-TASK-003, 004, 001 (SCRUM-18, 19, 20); Claude implement theo yêu cầu chủ dự án (không qua prompt Antigravity) | base `main` `ecb835f` → correction PR `[Phase 07]` | toàn bộ `src/aicefr/asr/*, tests/asr/*`; evidence module; chạy lại test/lint | FINDING-07-A1-01, FINDING-07-A1-02, FINDING-07-A1-03, FINDING-07-A1-07 — xem dưới | APPROVED 26/09/2026 (Sang) |
| 07-M03-A2 | Follow-up 07-A1-03 (SCRUM-50); Claude implement theo yêu cầu chủ dự án | base `main` `2b428ce` → PR #26 → `ae72d57` | `asr/service.py`, `tests/asr/*`, Spec/Test Plan v0.2.1; chạy lại test/lint | FINDING-07-A2-01 NIT ACCEPTED, FINDING-07-A2-02 MINOR follow-up | APPROVED 03/10/2026 (Sang) |
| 07-M03-A3 | M03-TASK-002 (DEP-06, SCRUM-22); adapter từ W3-TASK-005, smoke do Claude viết theo yêu cầu chủ dự án | base `main` `c427983` → nhánh `feat/SCRUM-22-m03-m04-smoke` (PR #32) | `src/aicefr/asr/local.py`, `tests/asr/test_local.py`, `tests/smoke/test_asr_smoke.py`, M03-EV-004; chạy lại test/lint/smoke | FINDING-07-A3-01 MINOR RESOLVED, 07-A3-02 INFO, 07-A3-03 INFO | PENDING |

## Review Record 07-M03-A1

```text
REVIEW ID: 07-M03-A1
TASK/PROMPT ID: M03-TASK-003, 004, 001 (SCRUM-18, 19, 20)
BASE/HEAD/FINGERPRINT: base main ecb835f (PR #7 e92c1cf, PR #8 ecb835f); không có fingerprint sdd-workspace-v2
  vì chủ dự án cho Claude implement trực tiếp, không phát prompt Antigravity — diff kiểm được qua Git
REVIEWED SCOPE/FILES: src/aicefr/asr/*, tests/asr/*
CHECKLIST RESULT: scope/traceability PASS; design PASS; functionality PASS sau correction (còn MINOR follow-up);
  simplicity PASS; responsibility/coupling PASS; duplication/dead code PASS; naming PASS;
  comments/docs MINOR (README, FINDING-05); style PASS (ruff); error/security PASS (log không lộ transcript/vector,
  artifact chỉ JSON có hash ghim); tests PASS (hành vi, biên, regression) sau FINDING-01
FINDINGS: FINDING-07-A1-01 MAJOR RESOLVED, FINDING-07-A1-02 MINOR RESOLVED, FINDING-07-A1-03 MINOR RESOLVED 03/10/2026 (SCRUM-50), FINDING-07-A1-07 NIT RESOLVED
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
FINDING ID: FINDING-07-A1-02
SEVERITY: MINOR
CATEGORY: Functionality
LOCATION: src/aicefr/asr/identity.py `asr_version_reasons`
OBSERVED EVIDENCE: Weight không có trong bảng ánh xạ + `trained_asr_model=None` → `asr_model=None`, reasons rỗng. Spec M03: weight không có trong bảng → null + `ASR_VERSION_MISMATCH`.
RISK/FAILED AC: Lệch M03-FR-003 ở trường hợp biên.
REQUIRED CHANGE: `asr_model is None` luôn trả `ASR_VERSION_MISMATCH`.
STATUS: RESOLVED
RESOLUTION EVIDENCE: Test `test_unmapped_weight_is_mismatch_even_without_trained_model`.
```
```text
FINDING ID: FINDING-07-A1-03
SEVERITY: MINOR
CATEGORY: Functionality
LOCATION: asr/service.py (QC REJECT) → scoring/scorer.py bước 3
OBSERVED EVIDENCE: QC `REJECT` → Transcript `NOT_RUN`, reasons rỗng → Assessment `NOT_EVALUATED` không kèm reason nào.
RISK/FAILED AC: M06 không có lý do để hiển thị. Spec M03 chưa định reason cho nhánh này; mã lỗi QC thuộc M02.
REQUIRED CHANGE: Follow-up: owner M02 (Thắng) công bố reason code QC trong contract, M03 chép sang Transcript.
STATUS: RESOLVED 03/10/2026 — ban đầu ACCEPTED_RISK (26/09/2026); M02 đã công bố mã `QC_*` trong contract, M03 chép `QCResult.reasons` sang Transcript (SCRUM-50)
RESOLUTION EVIDENCE: M03-EV-003 (`asr/service.py`, M03-TEST-005 mở rộng); chờ owner review lại trong PR
```
```text
FINDING ID: FINDING-07-A1-07
SEVERITY: NIT
CATEGORY: Clean Code
LOCATION: src/aicefr/asr/hallucination.py `_token_share`
OBSERVED EVIDENCE: `max(set(tokens), key=tokens.count)` là O(n²).
RISK/FAILED AC: —
REQUIRED CHANGE: Dùng `Counter.most_common`.
STATUS: RESOLVED
RESOLUTION EVIDENCE: M03-TEST-009 vẫn pass.
```

## Khác Test Plan — chủ dự án đã chấp nhận (26/09/2026)

- D1: luật "cụm 3–10 từ lặp ≥ 3 lần" hiện thực là lặp **liền nhau** (lặp rời rạc sẽ gắn cờ nhầm lời nói bình thường).

Codex lưu Phase 07 review record tại đây sau khi kiểm tra actual diff, test và evidence. Chỉ người dùng ghi verdict phê duyệt.

## Review Record 07-M03-A2

```text
REVIEW ID: 07-M03-A2
TASK/PROMPT ID: Follow-up FINDING-07-A1-03 (SCRUM-50); Claude implement theo yêu cầu chủ dự án
BASE/HEAD/FINGERPRINT: base main 2b428ce → PR #26 (merge 60a583f) → main ae72d57 (ae72d57b03de0ae9333e8b549484d026feb3177c); fingerprint sdd-workspace-v2 8835acf872d8c0abd3cc94e897723bc7a9c05fe3956400ee0b6bf577d7ab8af7
REVIEWED SCOPE/FILES: src/aicefr/asr/service.py, tests/asr/test_service.py, tests/asr/fixtures.py;
  Spec M03 v0.2.1, Test Plan M03 v0.2.1; evidence M03-EV-003
CHECKLIST RESULT: scope/traceability PASS (1 dòng src/); design PASS; functionality PASS (QC REJECT →
  NOT_RUN, reasons = QCResult.reasons, giữ thứ tự; engine không được gọi); simplicity PASS; naming PASS;
  duplication NIT (FINDING-07-A2-01); style PASS (ruff); security PASS (log chỉ ghi mã lý do); tests PASS
  (hai test mới FAIL khi bỏ thay đổi ở service.py)
FINDINGS: FINDING-07-A2-01 NIT ACCEPTED, FINDING-07-A2-02 MINOR follow-up liên module
CHECKS RERUN: `env -u AICEFR_MODEL_DIR pytest -q -m "not smoke"` → 192 passed, 11 skipped;
  có artifact → 203 passed; `aicefr.asr` 99–100 %; `ruff check .` sạch; CI run 37113044170 trên ae72d57, Python 3.11: 192 passed, 11 skipped
REVIEWER: Claude — cùng tác nhân đã implement, nên verdict do chủ dự án quyết; PR #26 không có lượt approve
  của thành viên khác trên GitHub
RESULT: PASS — không có BLOCKER/MAJOR
EVIDENCE: evidence/evidence-manifest.md (M03-EV-003, M03-EV-P08-A2)
```

```text
FINDING ID: FINDING-07-A2-01
SEVERITY: NIT
CATEGORY: Duplication
LOCATION: tests/asr/test_service.py::test_qc_reject_reasons_reach_the_scorer
OBSERVED EVIDENCE: Test dựng payload artifact giả inline, trùng một phần `_fake_payload` của tests/scoring/conftest.py
  (fixture của tests/scoring không dùng được từ tests/asr).
RISK/FAILED AC: Khi schema artifact đổi phải sửa hai chỗ.
REQUIRED CHANGE: Không bắt buộc; nếu schema đổi thì chuyển helper sang tests/conftest.py.
STATUS: ACCEPTED (03/10/2026, Sang)
RESOLUTION EVIDENCE: —
```
```text
FINDING ID: FINDING-07-A2-02
SEVERITY: MINOR
CATEGORY: Cross-module contract
LOCATION: Spec M03 Hành vi 1 ↔ src/aicefr/audio/pipeline.py (M02)
OBSERVED EVIDENCE: Spec M03 cho ASR chạy khi QC ∈ {PASS, REVIEW}; `process_audio` của M02 chỉ đưa PASS vào ASR,
  QC REVIEW trả transcript None.
RISK/FAILED AC: Bài QC REVIEW không có transcript/feature nên giảng viên duyệt mà không có gợi ý của máy.
  Không vi phạm AC của M03.
REQUIRED CHANGE: Pipeline coordinator (Thắng, U2) chốt một trong hai: gọi ASR cho QC REVIEW, hoặc sửa Spec M03
  về chỉ PASS. M03 không đổi code khi chưa có quyết định.
STATUS: OPEN — follow-up liên module, chủ dự án chấp nhận (03/10/2026)
RESOLUTION EVIDENCE: —
```

**Khác Spec/Test Plan — chủ dự án đã chấp nhận (03/10/2026):** Spec v0.2.1 (QC REJECT chép `QCResult.reasons`; thêm dòng bảng lỗi) và Test Plan v0.2.1 (mở rộng M03-TEST-005). Không đổi FR/AC.

## Review Record 07-M03-A3 (11/10/2026)

```text
REVIEW ID: 07-M03-A3
TASK/PROMPT ID: M03-TASK-002 (SCRUM-22 cho DEP-06)
BASE/HEAD: base main c427983; head = nhánh feat/SCRUM-22-m03-m04-smoke (PR #32)
REVIEWED SCOPE/FILES: src/aicefr/asr/local.py, tests/asr/test_local.py, tests/smoke/test_asr_smoke.py
CHECKLIST RESULT: scope/traceability PASS (S1, S2 ↔ test smoke); functionality PASS — chỉ đọc weight local,
  kiểm SHA-256 bốn tệp trước khi nạp, `local_files_only=True`, weight lạ giữ identifier để từ chối (M03-FR-003),
  `prob=None` giữ nguyên; error/security PASS — lỗi nạp không lộ đường dẫn máy, smoke không ghi transcript;
  tests PASS (unit offline + smoke thật); duplication/dead code MINOR (FINDING-07-A3-01, đã sửa)
FINDINGS: FINDING-07-A3-01 MINOR RESOLVED; FINDING-07-A3-02 INFO; FINDING-07-A3-03 INFO
CHECKS RERUN: `pytest -q -m "not smoke"` → 309 passed, 13 skipped; có artifact Ridge → 322 passed;
  smoke `-m smoke tests/smoke` (audio DEP-06, chặn mạng) → 2 passed, 0 lần thử kết nối;
  `ruff check src tests scripts`, `check_md_links.py`, `check_forbidden_files.py`, gitleaks sạch
RESULT: PASS — đề xuất APPROVE
USER VERDICT: PENDING
```

```text
FINDING ID: FINDING-07-A3-01
SEVERITY: MINOR
CATEGORY: Simplicity
LOCATION: src/aicefr/asr/local.py `FasterWhisperEngine.transcribe`
OBSERVED EVIDENCE: khối `try: … except Exception: raise` không đổi hành vi.
REQUIRED CHANGE: bỏ khối thừa.
STATUS: RESOLVED
RESOLUTION EVIDENCE: tests/asr 87 passed cùng tests/features; smoke S1/S2 PASS sau khi sửa.
```
```text
FINDING ID: FINDING-07-A3-02
SEVERITY: INFO
CATEGORY: Traceability
LOCATION: 06-tasks.md M03-TASK-002
OBSERVED EVIDENCE: Plan dự kiến tên `asr/faster_whisper_engine.py`; code W3 đặt ở `asr/local.py`.
REQUIRED CHANGE: không đổi tên (coordinator của Thắng import `asr.local`); ghi ánh xạ trong 06-tasks.md.
STATUS: ACCEPTED
```
```text
FINDING ID: FINDING-07-A3-03
SEVERITY: INFO
CATEGORY: Test data
LOCATION: M03-EV-004
OBSERVED EVIDENCE: audio smoke là giọng tổng hợp; asr_conf_mean cao hơn khoảng huấn luyện.
REQUIRED CHANGE: không; smoke chỉ chứng minh chạy thật. Khi có audio người nói thật có đồng ý, chạy lại S2 để quan sát.
STATUS: ACCEPTED
```
