# M04 — Evidence Manifest (danh mục bằng chứng)

**Hiện trạng (11/10/2026):** M04-EV-001 (TASK-001, 002) và M04-EV-P08 đã qua Phase 07–09; M04-EV-002 (TASK-003) chờ Phase 07. Báo cáo và hình W1 cấp dự án nằm ở docs/reports/week-01/ và docs/design/week-01/.

| Evidence ID | Prompt ID / Task ID | Phase | Base/Head revision, fingerprint | Loại / file hoặc link | Check và kết quả thực tế | Trạng thái |
| --- | --- | --- | --- | --- | --- | --- |
| M04-EV-001 | M04-TASK-001, 002 (Jira SCRUM-24, 25); Claude implement theo yêu cầu chủ dự án | 06 | base `e92c1cf` trên `main` | `src/aicefr/features/`, `tests/features/`, xem mục dưới | Test ID 001–015, 017, 018 chạy thật; coverage `aicefr.features` 100 % | RECORDED — chờ Phase 07 |
| M04-EV-002 | M04-TASK-003 (DEP-06, Jira SCRUM-22); Claude theo yêu cầu chủ dự án | 06 | base `c427983` trên `main` | `tests/features/test_local.py`, `tests/smoke/test_vad_smoke.py`; xem mục dưới | M04-TEST-016 và S1 chạy thật, PASS, 0 lần thử kết nối mạng | RECORDED — chờ Phase 07 |
| M04-EV-P08-W4 | M04-TASK-003 | 08 | main `35d3514` (merge PR #32) | Xem mục dưới | CI 305 passed + 17 skipped; máy Sang 322 passed (có artifact), smoke 2 passed; 0 failed | RECORDED — chờ verdict |

Lưu tại đây raw report của Antigravity, command output/test/coverage, ảnh browser QA và final verification khi phát sinh. File lớn có thể lưu ngoài Git nhưng phải có link ổn định, checksum và quyền truy cập cho người review. Mỗi evidence gắn đúng Prompt ID, Task ID, AC/Test ID và revision. Redact secret/PII/audio/transcript thật; không ghi PASS cho lệnh chưa chạy. Cập nhật 07-status.md trỏ tới evidence mới nhất.

## M04-EV-001 — M04-TASK-001 (18 công thức) và M04-TASK-002 (FeatureExtractor)

**Môi trường:** macOS 26.4, Python 3.12.14, base `e92c1cf`. Unit test dùng `FakeVad`, không import torch/silero.

| Lệnh | Kết quả |
| --- | --- |
| `python -m pytest -q tests/features` (không artifact) | 26 passed, 1 skipped (M04-TEST-010 cần ART-REAL) |
| `AICEFR_MODEL_DIR=<thư mục artifact> python -m pytest -q -m "not smoke"` (toàn repo) | 132 passed |
| coverage `aicefr.features` | `text.py`, `pauses.py`, `extractor.py` 100 % line/branch |

| Test ID | Test | Kết quả |
| --- | --- | --- |
| M04-TEST-001 | `test_text_features_match_expected_table`, `test_pause_features_match_expected_table`, `test_full_fixture_gives_18_values_with_units` (sai số 1e-6) | PASS |
| M04-TEST-002 | `test_gap_and_tail_of_exactly_030_s_are_not_pauses` | PASS |
| M04-TEST-003 | `test_no_pause_gives_measured_zero_not_missing` | PASS |
| M04-TEST-004, 011 | `test_unreliable_transcript_nulls_transcript_features_only` | PASS |
| M04-TEST-005 | `test_lexical_features_need_ten_tokens` (9 / 10) | PASS |
| M04-TEST-006 | `test_no_probability_gives_missing_confidence_not_zero` | PASS |
| M04-TEST-007 | `test_empty_segments_give_missing_vad_features_not_zero` (regression REF-04) | PASS |
| M04-TEST-008 | `test_zero_duration_nulls_all_18` | PASS |
| M04-TEST-009 | `test_nan_timestamp_propagates_only_to_affected_features`, `test_nan_becomes_none_with_reason` | PASS |
| M04-TEST-010 | `test_order_follows_real_artifact_without_filler_ratio` | PASS (ART-REAL) |
| M04-TEST-012 | `test_unknown_feature_name_is_config_error` | PASS |
| M04-TEST-013 | `test_model_feature_version_mismatch_is_flagged` | PASS |
| M04-TEST-014 | `test_silero_parameters_recorded_without_mismatch` | PASS |
| M04-TEST-015 | `test_other_vad_configuration_is_flagged` ×3 | PASS |
| M04-TEST-017 | `test_feature_set_and_log_do_not_leak_transcript` | PASS |
| M04-TEST-018 | `test_extraction_is_deterministic_and_unrounded` | PASS |

**Khác biệt so với Test Plan, cần owner xác nhận ở Phase 07:**
- M04-TEST-008: contract `DecodedAudio` chặn `duration_s < 0` ngay khi tạo, nên chỉ kiểm được D = 0.
- M04-TEST-009: contract `Word` chặn `prob` NaN, nên NaN được đưa vào qua timestamp segment VAD.
- So ngưỡng 0,30 s và 1,00 s có sai số 1e-9 (timestamp VAD ở mức mili-giây), để khoảng đúng 0,30 s không bị tính là ngừng do lỗi dấu phẩy động.
- M04-TEST-016 thuộc M04-TASK-003 (Silero, BLOCKED), chưa làm.

## M04-EV-P08 — Phase 08 Final Verification (M04-TASK-001, 002)

```text
UT EVIDENCE
- Final head/fingerprint: main 74afca9 (74afca9c3315256414f11697f07b717af0e22579); sdd-workspace-v2 7bc236e3a3df18900349d3fcfe16d12bc3398f3397b6c6d446812ac8ac14f81a
  (171 file, git status sạch, không metadata file)
- Test files và AC/Test ID mapping: tests/features/ (test_text_pauses.py, test_extractor.py); M04-TEST-001–015, 017, 018 (17/17)
- Command: env -u AICEFR_MODEL_DIR pytest -q -m "not smoke" tests/<module>
           AICEFR_MODEL_DIR=<thư mục artifact> python -m pytest -q -m "not smoke" --cov=aicefr --cov-branch
- Passed/failed/skipped: không artifact 26 passed, 1 skipped (M04-TEST-010 cần artifact thật); có artifact 27 passed; 0 failed
  (toàn repo: 123 passed + 10 skipped / 133 passed)
- Coverage metrics/policy/delta: `features/text.py`, `pauses.py`, `extractor.py` 100 % line/branch; toàn repo 99 % — đạt TP-D-001 (line ≥ 90 %, branch ≥ 85 %)
- Coverage report path: ngoài repo (scratchpad của phiên, coverage.xml + junit.xml); tóm tắt ở đây
- Critical uncovered branches/risk: Không có
- Codex rerun: có — máy Sang (macOS 26.4, Python 3.12.14) và CI GitHub trên main 74afca9
  (run 36257359229, Python 3.11: 123 passed, 10 skipped, 99 %); ruff check / format --check sạch
- CODEX CHECK RESULT: PASS
- CODEX RECOMMENDATION: RECOMMEND APPROVAL
- USER VERDICT: APPROVED (Sang, 27/09/2026)
```

**Ngoài Phase 08 này:** M04-TASK-003 (Silero + smoke, M04-TEST-016, S1) BLOCKED.

## M04-EV-002 — TEST-016 và smoke S1: Silero thật, không mạng (11/10/2026)

**Audio (DEP-06):** cùng tệp với [M03-EV-004](../../m03-asr/evidence/evidence-manifest.md) — giọng tổng hợp do nhóm tạo bằng lệnh `say` của macOS (giọng Samantha, tốc độ 165), đọc một đoạn tiếng Anh nhóm tự viết; WAV 16 kHz mono, 38,541 s, SHA-256 `290f0436…a7427`; đặt ngoài repo (`~/aicefr-smoke/`). Không phải giọng người học, không có PII.

| Test ID | Test | Kết quả |
| --- | --- | --- |
| M04-TEST-016 | `test_m04_test_016_silero_import_failure_nulls_pause_features_without_fallback`: gói `silero_vad` không import được → 10 đặc trưng `vad_*` `None` + `FEATURE_NOT_COMPUTABLE`; `n_words`, `asr_conf_mean` vẫn có; không VAD dự phòng | PASS |
| M04-TEST-S1 | `test_s1_silero_segments_the_audio_offline_and_gives_every_pause_feature` | PASS |

**Lệnh smoke:** như M03-EV-004 (base `c427983`), exit 0. `vad_articulation_rate` cần số từ: lấy từ transcript whisper-small thật của cùng lượt, không dùng transcript viết sẵn.

| Trường S1 | Giá trị |
| --- | --- |
| Gói | silero-vad 6.2.1 (MIT, model đi kèm gói), torch 2.14.1 |
| Cấu hình | threshold 0,5; min_silence 150 ms; 16 kHz mono |
| Mạng | 0 lần thử kết nối |
| Số đoạn | 9; thời gian VAD 1,9 s cho 38,5 s audio |
| 10 giá trị `vad_*` | silence_ratio 0,0296; mean_pause 0,0; pause_per_min 0,0; long_pause_ratio 0,0; pause_sd 0,0; mean_seg_len 4,1556 s; n_seg_per_min 14,0109; articulation_rate 3,6364; onset_delay 0,0; speech_sec 37,4 |

**Ghi chú:** giọng tổng hợp gần như không có khoảng ngừng từ 0,30 s trở lên, nên các đặc trưng ngừng nghỉ bằng 0. Đó là tính chất của audio, không phải lỗi công thức; smoke chỉ chứng minh Silero chạy thật và đủ 10 giá trị. Cần audio người nói thật có quyền dùng nếu muốn quan sát ngừng nghỉ.

## M04-EV-P08-W4 — Phase 08 Final Verification (M04-TASK-003, 11/10/2026)

```text
UT EVIDENCE
- Final revision: main 35d3514cf3279f2cd6d87ce2db2f1d0d23de725b (merge PR #32; mã trùng head c541f31 đã kiểm)
- CI GitHub run 38150517851 trên 35d3514, Python 3.11: 305 passed, 17 skipped; ruff sạch; kiểm tài liệu và file cấm PASS
- Máy Sang (macOS, Python 3.12.14): không artifact 309 passed, 13 skipped; có artifact Ridge 322 passed;
  smoke `-m smoke tests/smoke` với audio DEP-06, chặn mạng: 2 passed, 0 lần thử kết nối
- Coverage aicefr.asr/features/scoring: 96 % (line + branch); adapter asr/local.py, features/local.py loại khỏi ngưỡng
  theo TP-D-001 (kiểm bằng smoke)
- CODEX CHECK RESULT: PASS
- CODEX RECOMMENDATION: RECOMMEND APPROVAL
- USER VERDICT: PENDING — chủ module ghi
```
