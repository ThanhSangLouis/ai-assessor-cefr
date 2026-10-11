# M03 — Evidence Manifest (danh mục bằng chứng)

**Hiện trạng (03/10/2026):** M03-EV-001 (weight ASR), M03-EV-002 (TASK-003, 004, 001) và M03-EV-003 (follow-up 07-A1-03, SCRUM-50) đều đã qua Phase 07–09; Final Verification ở M03-EV-P08 và M03-EV-P08-A2.

| Evidence ID | Prompt ID / Task ID | Phase | Base/Head revision, fingerprint | Loại / file hoặc link | Check và kết quả thực tế | Trạng thái |
| --- | --- | --- | --- | --- | --- | --- |
| M03-EV-001 | SCRUM-21 (việc tay M03-O1 / DEP-05) | 05 — chuẩn bị dependency | Không áp dụng (tải ngoài repo, không đổi source) | Weight ASR, xem mục dưới | SHA-256 `model.bin` khớp giá trị LFS chính thức trên Hugging Face | RECORDED |
| M03-EV-002 | M03-TASK-003, 004, 001 (Jira SCRUM-18, 19, 20); Claude implement theo yêu cầu chủ dự án | 06 | base `e92c1cf` trên `main` | `src/aicefr/asr/`, `tests/asr/`, xem mục dưới | Test ID 001–016 chạy thật; coverage `aicefr.asr` ≥ 99 % line/branch | RECORDED — chờ Phase 07 |
| M03-EV-003 | Follow-up 07-A1-03 (Jira SCRUM-50); Claude implement theo yêu cầu chủ dự án, không qua prompt Antigravity | 06 | base `2b428ce` trên `main` | `src/aicefr/asr/service.py`, `tests/asr/test_service.py`, `tests/asr/fixtures.py`, xem mục dưới | M03-TEST-005 mở rộng chạy thật; `asr/service.py` 100 % line/branch | VERIFIED — Phase 07–09 APPROVED 03/10/2026 |
| M03-EV-P08-A2 | Follow-up 07-A1-03 (SCRUM-50) | 08 | main ae72d57 (ae72d57b03de0ae9333e8b549484d026feb3177c); fingerprint `8835acf872d8c0ab…` | Xem mục dưới | 192 passed + 11 skipped (CI), 203 passed (có artifact), 0 failed | APPROVED 03/10/2026 |
| M03-EV-004 | M03-TASK-002 (DEP-06, Jira SCRUM-22); Claude theo yêu cầu chủ dự án | 06 | base `c427983` trên `main` | `tests/smoke/test_asr_smoke.py`, JSON evidence ngoài repo; xem mục dưới | M03-TEST-S1, S2 chạy thật, PASS, 0 lần thử kết nối mạng | RECORDED — chờ Phase 07 |

Lưu tại đây raw report của Antigravity, command output/test/coverage, ảnh browser QA và final verification khi phát sinh. File lớn có thể lưu ngoài Git nhưng phải có link ổn định, checksum và quyền truy cập cho người review. Mỗi evidence gắn đúng Prompt ID, Task ID, AC/Test ID và revision. Redact secret/PII/audio/transcript thật; không ghi PASS cho lệnh chưa chạy. Cập nhật 07-status.md trỏ tới evidence mới nhất.

## M03-EV-001 — Weight `whisper-small` (CTranslate2)

Tải có chủ đích theo M03-D-001 (`whisper-small`), M03-D-002 (không tự tải khi chạy) và M03-O-001 (faster-whisper). Weight **không** nằm trong Git.

| Mục | Giá trị |
| --- | --- |
| Nguồn | Hugging Face `Systran/faster-whisper-small` |
| Revision ghim | `536b0662742c02347bc0e980a01041f333bce120` |
| License | MIT (khai báo trong model card) |
| Ngày tải | 26/09/2026, máy của Sang (macOS 26.4, Apple M5, 24 GiB RAM) |
| Nơi lưu | `~/models/faster-whisper-small/` — ngoài repo; `.gitignore` bỏ qua `models/` và CI chặn `*.bin` |
| Lệnh | `curl -sSfL https://huggingface.co/Systran/faster-whisper-small/resolve/<revision>/<file>` cho từng file, rồi `shasum -a 256` |

| File | Kích thước (byte) | SHA-256 |
| --- | --- | --- |
| `model.bin` | 483 546 902 | `3e305921506d8872816023e4c273e75d2419fb89b24da97b4fe7bce14170d671` |
| `config.json` | 2 370 | `b55496ac7940a7ae47d2c01eab40edfd8701feec1229d9cce3b40014383fb828` |
| `tokenizer.json` | 2 203 239 | `fb7b63191e9bb045082c79fd742a3106a12c99513ab30df4a0d47fa6cb6fd0ab` |
| `vocabulary.txt` | 459 861 | `34ce3fe1c5041027b3f8d42912270993f986dbc4bb34cf27f951e34a1e453913` |

**Kiểm tra:** SHA-256 của `model.bin` trùng giá trị LFS mà API Hugging Face công bố cho revision trên. Chưa chạy model; smoke M03-TEST-S1/S2 vẫn `NOT_RUN` (chờ audio có quyền dùng và DEP-01..04).

## M03-EV-002 — M03-TASK-003, 004, 001 (bộ phát hiện hallucination, ánh xạ identifier, dịch vụ ASR)

**Môi trường:** macOS 26.4, Python 3.12.14, base `e92c1cf`. Unit test dùng `FakeAsrEngine` (test_only), không import faster-whisper, không cần model hay audio.

| Lệnh | Kết quả |
| --- | --- |
| `python -m pytest -q tests/asr` | 44 passed |
| `python -m pytest -q -m "not smoke" --cov=aicefr --cov-branch` (toàn repo, không artifact) | 122 passed, 10 skipped; `asr/service.py`, `identity.py`, `validation.py` 100 %; `hallucination.py` 99 % |
| `ruff check src tests` · `ruff format --check src tests` | sạch |

| Test ID | Test | Kết quả |
| --- | --- | --- |
| M03-TEST-001 | `test_ok_transcript_keeps_order_filler_and_provenance` | PASS |
| M03-TEST-002 | `test_missing_probability_stays_none` (regression REF-03) | PASS |
| M03-TEST-003 | `test_engine_error_or_timeout_is_asr_failed` ×2 | PASS |
| M03-TEST-004 | `test_invalid_words_are_asr_failed_without_words` ×5, `test_invalid_timestamps_are_reported` ×4 | PASS |
| M03-TEST-005 | `test_qc_reject_does_not_call_engine` | PASS |
| M03-TEST-006 | `test_missing_model_is_not_run_without_download` | PASS |
| M03-TEST-007 | `test_empty_transcript_is_unreliable` ×2 | PASS |
| M03-TEST-008 | `test_consecutive_token_repeats` (6 / 7) | PASS |
| M03-TEST-009 | `test_single_token_share` (21/60, 22/60, 59 từ) | PASS |
| M03-TEST-010 | `test_phrase_repeated_back_to_back` (2 / 3) | PASS |
| M03-TEST-011 | `test_low_probability_tail` (4 / 5) | PASS |
| M03-TEST-012 | `test_stalled_clock` (3 / 4) | PASS |
| M03-TEST-013 | `test_mapped_weight_resolves_to_canonical_id`, `test_matching_weight_has_no_mismatch` | PASS |
| M03-TEST-014 | `test_unmapped_weight_is_none_and_mismatch` ×3, `test_english_only_weight_is_mismatch_but_status_unchanged` (regression F-04) | PASS |
| M03-TEST-015 | `test_custom_map_and_other_model_mismatch`, `test_other_model_is_mismatch_but_status_unchanged` | PASS |
| M03-TEST-016 | `test_log_does_not_contain_transcript_text` | PASS |

**Cách hiểu cần owner xác nhận ở Phase 07:** luật "cụm 3–10 từ lặp ≥ 3 lần" được hiện thực là lặp **liền nhau** (như "i like it i like it i like it"). Đếm cả lặp rời rạc sẽ gắn cờ nhầm lời nói bình thường ("i think that" xuất hiện 3 lần trong 60 giây).

## M03-EV-P08 — Phase 08 Final Verification (M03-TASK-003, 004, 001)

```text
UT EVIDENCE
- Final head/fingerprint: main 74afca9 (74afca9c3315256414f11697f07b717af0e22579); sdd-workspace-v2 7bc236e3a3df18900349d3fcfe16d12bc3398f3397b6c6d446812ac8ac14f81a
  (171 file, git status sạch, không metadata file)
- Test files và AC/Test ID mapping: tests/asr/ (test_service.py, test_hallucination.py, test_identity_validation.py); M03-TEST-001–016 (16/16)
- Command: env -u AICEFR_MODEL_DIR pytest -q -m "not smoke" tests/<module>
           AICEFR_MODEL_DIR=<thư mục artifact> python -m pytest -q -m "not smoke" --cov=aicefr --cov-branch
- Passed/failed/skipped: không artifact 45 passed; có artifact 45 passed; 0 failed
  (toàn repo: 123 passed + 10 skipped / 133 passed)
- Coverage metrics/policy/delta: `asr/service.py`, `identity.py`, `validation.py` 100 % line/branch; `hallucination.py` 99 % line/branch; toàn repo 99 % — đạt TP-D-001 (line ≥ 90 %, branch ≥ 85 %)
- Coverage report path: ngoài repo (scratchpad của phiên, coverage.xml + junit.xml); tóm tắt ở đây
- Critical uncovered branches/risk: `hallucination.py` nhánh 84→88 (vòng lặp cụm lặp kết thúc mà không gặp cụm nào — trường hợp thường, không phải hành vi quan trọng chưa kiểm)
- Codex rerun: có — máy Sang (macOS 26.4, Python 3.12.14) và CI GitHub trên main 74afca9
  (run 36257359229, Python 3.11: 123 passed, 10 skipped, 99 %); ruff check / format --check sạch
- CODEX CHECK RESULT: PASS
- CODEX RECOMMENDATION: RECOMMEND APPROVAL
- USER VERDICT: APPROVED (Sang, 27/09/2026)
```

**Ngoài Phase 08 này:** M03-TASK-002 (faster-whisper + smoke S1/S2) BLOCKED — chưa có code, không thuộc Phase 08 này.

## M03-EV-003 — Follow-up 07-A1-03: lý do QC đi theo transcript (SCRUM-50)

**Môi trường:** macOS 26.4, Python 3.12.14 (`.venv` qua uv), base `2b428ce`.

**Thay đổi:** nhánh QC `REJECT` của `AsrService` trả `Transcript(NOT_RUN, reasons=QCResult.reasons)`. Trước đó `reasons` rỗng nên M05 trả `NOT_EVALUATED` không kèm lý do (FINDING-07-A1-03). Theo Spec v0.2.1, Test Plan v0.2.1.

| Lệnh | Kết quả |
| --- | --- |
| `env -u AICEFR_MODEL_DIR python -m pytest -q -m "not smoke" --cov=aicefr --cov-branch` (giống CI) | 190 passed, 10 skipped; `asr/service.py` 100 % line/branch |
| `AICEFR_MODEL_DIR=<thư mục artifact> python -m pytest -q -m "not smoke"` | 200 passed |
| Bỏ riêng thay đổi ở `service.py`, chạy lại `tests/asr` | 2 failed: hai test mới bắt đúng lỗi cũ |
| `ruff check .` | sạch |

| Test ID | Test | Kết quả |
| --- | --- | --- |
| M03-TEST-005 | `test_qc_reject_does_not_call_engine`: engine không được gọi; `reasons` = (`QC_TOO_SHORT`, `QC_SILENCE_REJECT`) đúng thứ tự | PASS |
| M03-TEST-005 (nối M05) | `test_qc_reject_reasons_reach_the_scorer`: `RidgeScorer` trả `NOT_EVALUATED` với reason `QC_TOO_SHORT` | PASS |

**Ghi chú:** `process_audio` của M02 không gọi ASR khi QC không PASS, nên nhánh này chỉ chạy khi coordinator gọi M03 trực tiếp với kết quả REJECT. Sửa ở M03 để hợp đồng đúng dù coordinator gọi theo cách nào.

## M03-EV-P08-A2 — Phase 08 Final Verification (follow-up 07-A1-03)

```text
UT EVIDENCE
- Final head/fingerprint: main ae72d57 (ae72d57b03de0ae9333e8b549484d026feb3177c); sdd-workspace-v2 8835acf872d8c0abd3cc94e897723bc7a9c05fe3956400ee0b6bf577d7ab8af7
  (232 file, git status sạch, không metadata file)
- Test files và AC/Test ID mapping: tests/asr/test_service.py ↔ M03-TEST-005 (hai test); các Test ID khác không đổi
- Command: env -u AICEFR_MODEL_DIR python -m pytest -q -m "not smoke"
           AICEFR_MODEL_DIR=<thư mục artifact> python -m pytest -q -m "not smoke" --cov=aicefr --cov-branch
- Passed/failed/skipped: không artifact 192 passed, 11 skipped; có artifact 203 passed; 0 failed
- Coverage metrics/policy/delta: `asr/service.py` 100 %, `aicefr.asr` 99–100 % line/branch — đạt TP-D-001
- Coverage report path: ngoài repo (chạy trên máy Sang); tóm tắt ở đây
- Critical uncovered branches/risk: Không có
- Codex rerun: có — máy Sang (macOS 26.4, Python 3.12.14) và CI GitHub run 37113044170 trên ae72d57, Python 3.11: 192 passed, 11 skipped; ruff check sạch
- CODEX CHECK RESULT: PASS
- CODEX RECOMMENDATION: RECOMMEND APPROVAL
- USER VERDICT: APPROVED (Sang, 03/10/2026)
```

## M03-EV-004 — Smoke S1/S2: faster-whisper `small` thật, không mạng (11/10/2026)

**Audio (DEP-06):** giọng tổng hợp do nhóm tạo bằng lệnh `say` của macOS (giọng Samantha, tốc độ 165), đọc một đoạn tiếng Anh nhóm tự viết; WAV 16 kHz mono, 38,541 s, SHA-256 `290f0436…a7427`; đặt ngoài repo (`~/aicefr-smoke/`). Không phải giọng người học, không có PII. Dùng cho smoke kỹ thuật; không phải số liệu thực nghiệm, không dùng để nói về độ chính xác.

**Lệnh:** `AICEFR_SMOKE_AUDIO=~/aicefr-smoke/smoke-s1.wav AICEFR_SMOKE_EVIDENCE=~/aicefr-smoke/evidence.json python -m pytest -q -m smoke tests/smoke` (base `c427983`). Exit 0, 2 passed (cùng lượt với M04-TEST-S1). Test chặn `socket.connect`, `connect_ex`, `create_connection`, `getaddrinfo` và đếm số lần bị gọi.

| Trường S1 | Giá trị |
| --- | --- |
| Weight | `whisper-small` — Hugging Face `Systran/faster-whisper-small`, CTranslate2, license MIT; nơi lưu `~/models/faster-whisper-small/` |
| SHA-256 | `model.bin` `3e305921…d170d671`, `config.json` `b55496ac…eab40edfd`, `tokenizer.json` `fb7b6319…d6cb6fd0ab`, `vocabulary.txt` `34ce3fe1…e453913` — khớp M03-EV-001 |
| Engine | faster-whisper 1.2.1, CTranslate2 4.8.2; adapter tự kiểm SHA-256 trước khi nạp |
| Decode config | `asr-decode-v1`: `language=en`, `word_timestamps=True`, `beam_size=5`, `vad_filter=False`, `condition_on_previous_text=False`, CPU `int8` |
| Máy | macOS 26.4 arm64, 10 nhân, 24 GiB RAM, Python 3.12.14 |
| Mạng | 0 lần thử kết nối |
| Thời gian xử lý | 9,5–9,9 s cho 38,5 s audio (gồm nạp model) |
| Kết quả | `status=OK`, `asr_model=whisper-small`, không reason, 136 từ có timestamp hợp lệ, `test_only=false` |

| Trường S2 | Giá trị |
| --- | --- |
| `asr_conf_mean` | 0,990 (136/136 từ có probability) |
| So với khoảng huấn luyện của artifact | Ngoài khoảng, phía cao — hợp lý với giọng tổng hợp sạch |
| So với khoảng M05 chấp nhận | Trong khoảng (`feature_lo/hi` của `ridge_resp_v2` nới thêm `ood_tolerance`): không báo owner M05. Test đọc các giới hạn từ artifact lúc chạy; số cụ thể không chép vào repo public vì suy ra từ S&I. Chạy thử cả chuỗi ASR → M04 → Ridge trên audio này cho `ESTIMATED`, không reason OOD. Điểm đó không có ý nghĩa CEFR: giọng máy đọc kịch bản |

Evidence JSON chỉ chứa metadata (không transcript, không audio); lưu ngoài repo cùng audio. Weight, audio, transcript không vào Git.
