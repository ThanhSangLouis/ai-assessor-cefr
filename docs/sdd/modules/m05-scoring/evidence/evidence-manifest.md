# M05 — Evidence Manifest (danh mục bằng chứng)

**Hiện trạng (03/10/2026):** M05-TASK-002 (M05-EV-001), M05-TASK-001 (M05-EV-002) và M05-TASK-004 (M05-EV-003) đều đã qua Phase 07–09; Final Verification ở M05-EV-P08 và M05-EV-P08-A2.

| Evidence ID | Prompt ID / Task ID | Phase | Base/Head revision, fingerprint | Loại / file hoặc link | Check và kết quả thực tế | Trạng thái |
| --- | --- | --- | --- | --- | --- | --- |
| M05-EV-001 | M05-TASK-002 (Jira SCRUM-27); Claude implement theo yêu cầu chủ dự án, không qua prompt Antigravity | 06 | base `9884170` trên `main` | PR `[SCRUM-27]`, xem mục dưới | Test ID 005–007, 015–019 chạy thật; coverage `aicefr.scoring` 100 % line/branch | RECORDED — chờ Phase 07 |
| M05-EV-002 | M05-TASK-001 (Jira SCRUM-28); Claude implement theo yêu cầu chủ dự án | 06 | trên nhánh của M05-EV-001 | `scoring/scorer.py`, `scoring/coverage.py`, `tests/scoring/test_scorer.py` | Test ID 001–004, 008–014, 020, 021 chạy thật; coverage `aicefr.scoring` 100 % line/branch | RECORDED — chờ Phase 07 |
| M05-EV-003 | M05-TASK-004; Claude implement theo yêu cầu chủ dự án, không qua prompt Antigravity | 06 | base `2b428ce` trên `main` | `tests/scoring/test_integration_features.py`, xem mục dưới | M05-TEST-022 chạy thật cả hai chế độ (có và không có ART-REAL) | VERIFIED — Phase 07–09 APPROVED 03/10/2026 |
| M05-EV-P08-A2 | M05-TASK-004 | 08 | main ae72d57 (ae72d57b03de0ae9333e8b549484d026feb3177c); fingerprint `8835acf872d8c0ab…` | Xem mục dưới | 192 passed + 11 skipped (CI), 203 passed (có artifact), 0 failed | APPROVED 03/10/2026 |

Lưu tại đây raw report của Antigravity, command output/test/coverage, ảnh browser QA và final verification khi phát sinh. File lớn có thể lưu ngoài Git nhưng phải có link ổn định, checksum và quyền truy cập cho người review. Mỗi evidence gắn đúng Prompt ID, Task ID, AC/Test ID và revision. Redact secret/PII/audio/transcript thật; không ghi PASS cho lệnh chưa chạy. Cập nhật 07-status.md trỏ tới evidence mới nhất.

## M05-EV-001 — M05-TASK-002 loader artifact + toán chấm Ridge

**Môi trường:** macOS 26.4, Python 3.12.14 (`.venv` qua uv), base `9884170`. Artifact thật đặt ngoài repo (P05-D-001).

| Lệnh | Kết quả |
| --- | --- |
| `env -u AICEFR_MODEL_DIR python -m pytest -q -m "not smoke"` (giống CI, không có artifact) | 32 passed, 5 skipped (5 test cần ART-REAL báo SKIPPED, không tính PASS) |
| `AICEFR_MODEL_DIR=<thư mục chứa ridge_resp_v2.json> python -m pytest -q -m "not smoke" --cov=aicefr --cov-branch` | 37 passed; `scoring/artifact.py` 100 %, `scoring/ridge.py` 100 % (line và branch) |
| `ruff check .` · `ruff format --check src tests` | sạch |

| Test ID | Test | Kết quả |
| --- | --- | --- |
| M05-TEST-005 | `test_load_artifact_missing_file_reports_model_version_missing` | PASS |
| M05-TEST-006 | `test_load_artifact_one_byte_changed_reports_artifact_invalid` (ART-REAL), `…hash_mismatch_on_fake…` | PASS |
| M05-TEST-007 | `test_load_artifact_wrong_unit_of_inference_is_rejected` ×2, `…missing_unit_field…` | PASS |
| M05-TEST-015 | `test_total_dur_just_below_accepted_high_is_not_ood`, `…above_accepted_high_is_ood_with_detail` (ART-REAL) | PASS |
| M05-TEST-016 | `test_to_band_boundaries` ×4 | PASS |
| M05-TEST-017 | `test_near_boundary_with_margin_half` ×4 | PASS |
| M05-TEST-018 | `test_predict_clips_to_score_range` ×2 | PASS |
| M05-TEST-019 | `test_predict_uses_one_when_scale_is_zero` | PASS |

**Ghi chú triển khai:** artifact ghi `unit_of_inference` không dấu (`mot bai noi …`), nên loader chấp nhận cả "một bài nói" và "mot bai noi". Chuỗi đó cũng chứa "khong phai ca bai thi", vì vậy điều kiện là *có* dấu hiệu một bài nói, không phải *không có* "ca bai thi".

## M05-EV-002 — M05-TASK-001 scorer 8 bước + coverage 5 tiêu chí

| Lệnh | Kết quả |
| --- | --- |
| `env -u AICEFR_MODEL_DIR python -m pytest -q -m "not smoke" --cov=aicefr.scoring --cov-branch` (giống CI) | 52 passed, 9 skipped; `artifact.py`, `coverage.py`, `ridge.py`, `scorer.py` đều 100 % line/branch |
| `AICEFR_MODEL_DIR=<thư mục artifact> python -m pytest -q -m "not smoke" --cov=aicefr --cov-branch` | 61 passed; toàn repo 98 % |
| `ruff check src tests` · `ruff format --check src tests` | sạch |

| Test ID | Test | Kết quả |
| --- | --- | --- |
| M05-TEST-001 | `test_golden_vectors_on_real_artifact` ×3 (vector `mean`, `feature_lo`, `feature_hi`; kỳ vọng tính lại từ artifact theo công thức Spec, không chép số S&I vào repo) + provenance đọc từ artifact | PASS (ART-REAL) |
| M05-TEST-002 | `test_score_is_deterministic_apart_from_timestamp` | PASS |
| M05-TEST-003 | `test_full_features_give_full_coverage_without_scores` (fluency = 1,0) | PASS (ART-REAL) |
| M05-TEST-004 | `test_every_assessment_has_insufficient_evidence_interaction` | PASS |
| M05-TEST-008 | `test_transcript_not_ok_is_not_evaluated_and_keeps_m03_reason` | PASS |
| M05-TEST-009/010/012/013 | `test_provenance_mismatch_is_not_evaluated` ×7 (thêm vad_threshold, vad_min_silence_ms, feature_version) | PASS |
| M05-TEST-011 | `test_swapped_feature_order_is_not_evaluated` | PASS |
| M05-TEST-014 | `test_missing_feature_is_not_evaluated_with_null_coverage` | PASS |
| M05-TEST-020 | `test_coverage_with_one_missing_fluency_feature` (0,80) | PASS |
| M05-TEST-021 | `test_log_has_ids_and_status_but_no_feature_values` | PASS |

**Thay đổi contract (phần M05):** thêm `OutOfRangeFeature` và `Assessment.out_of_range` để trả chi tiết OOD như Spec bước 6 yêu cầu; M06 dùng để báo giới hạn cho người học. Test chạy được trên CI nhờ fixture ART-FAKE18 có đúng 18 tên đặc trưng của Ridge v2.

## M05-EV-P08 — Phase 08 Final Verification (M05-TASK-002, 001)

```text
UT EVIDENCE
- Final head/fingerprint: main 74afca9 (74afca9c3315256414f11697f07b717af0e22579); sdd-workspace-v2 7bc236e3a3df18900349d3fcfe16d12bc3398f3397b6c6d446812ac8ac14f81a
  (171 file, git status sạch, không metadata file)
- Test files và AC/Test ID mapping: tests/scoring/ (test_artifact.py, test_ridge.py, test_scorer.py); M05-TEST-001–021 (21/21; M05-TEST-005 kiểm cả cấp loader và cấp Assessment)
- Command: env -u AICEFR_MODEL_DIR pytest -q -m "not smoke" tests/<module>
           AICEFR_MODEL_DIR=<thư mục artifact> python -m pytest -q -m "not smoke" --cov=aicefr --cov-branch
- Passed/failed/skipped: không artifact 44 passed, 9 skipped (test cần artifact thật); có artifact 53 passed; 0 failed
  (toàn repo: 123 passed + 10 skipped / 133 passed)
- Coverage metrics/policy/delta: `scoring/artifact.py`, `ridge.py`, `coverage.py`, `scorer.py` 100 % line/branch; toàn repo 99 % — đạt TP-D-001 (line ≥ 90 %, branch ≥ 85 %)
- Coverage report path: ngoài repo (scratchpad của phiên, coverage.xml + junit.xml); tóm tắt ở đây
- Critical uncovered branches/risk: Không có
- Codex rerun: có — máy Sang (macOS 26.4, Python 3.12.14) và CI GitHub trên main 74afca9
  (run 36257359229, Python 3.11: 123 passed, 10 skipped, 99 %); ruff check / format --check sạch
- CODEX CHECK RESULT: PASS
- CODEX RECOMMENDATION: RECOMMEND APPROVAL
- USER VERDICT: APPROVED (Sang, 27/09/2026)
```

**Ngoài Phase 08 này:** M05-TASK-004 (integration M04→M05, M05-TEST-022) READY, chưa làm — không thuộc W2.

## M05-EV-003 — M05-TASK-004 integration M04 → M05

**Môi trường:** macOS 26.4, Python 3.12.14 (`.venv` qua uv), base `2b428ce`. Artifact thật đặt ngoài repo (P05-D-001), SHA-256 khớp hằng ghim trong `scoring/artifact.py`.

| Lệnh | Kết quả |
| --- | --- |
| `env -u AICEFR_MODEL_DIR python -m pytest -q -m "not smoke" --cov=aicefr --cov-branch` (giống CI) | 191 passed, 11 skipped (bản ART-REAL của M05-TEST-022 báo SKIPPED, không tính PASS); `aicefr.scoring` 100 % line/branch |
| `AICEFR_MODEL_DIR=<thư mục artifact> python -m pytest -q -m "not smoke"` | 202 passed, 0 skipped |
| `ruff check .` | sạch |
| `ruff format --check tests/scoring/test_integration_features.py` | sạch (19 file khác trên `main` chưa format, ngoài vùng M03–M05, CI hiện không kiểm format) |

| Test ID | Test | Kết quả |
| --- | --- | --- |
| M05-TEST-022 (a) | `test_fixture_features_reach_the_real_model_and_only_log_uniq_is_out_of_range` (ART-REAL): `NOT_EVALUATED`, reason duy nhất `OUT_OF_DISTRIBUTION`, đúng một mục OOD `log_uniq` "low"; ngưỡng đọc từ artifact, không ghi số vào test | PASS (ART-REAL) · SKIPPED trên CI |
| M05-TEST-022 (b) | `test_extractor_output_is_accepted_by_the_scorer` (ART-FAKE khoảng nhận rộng): tên/thứ tự/provenance khớp, đi hết 8 bước, `ESTIMATED` B1 | PASS |
| M05-TEST-022 (b) | `test_vad_setting_mismatch_travels_from_m04_to_m05`: VAD ngưỡng 0,3 → M04 gắn `VAD_VERSION_MISMATCH`, M05 trả `NOT_EVALUATED` | PASS |

**Ghi chú:** test chỉ thêm file, không đổi code `src/`. Hai biến thể (b) được thêm vào M05-TEST-022 trong [Test Plan](../04-test-plan.md) để hợp đồng M04→M05 vẫn được kiểm trên CI khi không có artifact thật.

## M05-EV-P08-A2 — Phase 08 Final Verification (M05-TASK-004)

```text
UT EVIDENCE
- Final head/fingerprint: main ae72d57 (ae72d57b03de0ae9333e8b549484d026feb3177c); sdd-workspace-v2 8835acf872d8c0abd3cc94e897723bc7a9c05fe3956400ee0b6bf577d7ab8af7
  (232 file, git status sạch, không metadata file)
- Test files và AC/Test ID mapping: tests/scoring/test_integration_features.py ↔ M05-TEST-022 (a, b);
  M05-TEST-001–021 không đổi
- Command: env -u AICEFR_MODEL_DIR python -m pytest -q -m "not smoke"
           AICEFR_MODEL_DIR=<thư mục artifact> python -m pytest -q -m "not smoke" --cov=aicefr --cov-branch
- Passed/failed/skipped: không artifact 192 passed, 11 skipped; có artifact 203 passed; 0 failed
- Coverage metrics/policy/delta: `aicefr.scoring` 100 % line/branch — đạt TP-D-001. Toàn repo 89 % vì đã có
  code M01/M02/M06/M07/M08 từ W3; không tính vào policy của M05
- Coverage report path: ngoài repo (chạy trên máy Sang); tóm tắt ở đây
- Critical uncovered branches/risk: Không có
- Codex rerun: có — máy Sang (macOS 26.4, Python 3.12.14) và CI GitHub run 37113044170 trên ae72d57, Python 3.11: 192 passed, 11 skipped; ruff check sạch
- CODEX CHECK RESULT: PASS
- CODEX RECOMMENDATION: RECOMMEND APPROVAL
- USER VERDICT: APPROVED (Sang, 03/10/2026)
```
