# M04 — 04 Test Plan (Kế hoạch kiểm thử)

> **v0.2 · 26/09/2026 · APPROVED Phase 04 ngày 26/09/2026.** Dựa trên [Specification v0.2 APPROVED](03-specification.md). Mọi test ở đây là **ca dự kiến, chưa chạy**. Không thêm hành vi ngoài Specification.

## Fixture chuẩn (giá trị kỳ vọng tính sẵn từ công thức Spec, 26/09/2026)

**FX-TEXT** — 14 word, `D = 11,0 s`:
`"Um," "I" "think" "that" "the" "city" "is" "nice." "The" "city" "is" "big" "and" "green."`, prob lần lượt `0.5 0.9 0.8 0.9 0.95 0.7 0.9 0.85 0.9 0.8 0.9 0.6 0.95 None`.

**FX-VAD** — segment `(0,5–3,0) (3,4–6,0) (7,5–10,0)`, `D = 11,0 s` → `S = 7,6`; `P = [0,4 ; 1,5 ; 1,0]` (đuôi 1,0 s được tính).

| Đặc trưng | Kỳ vọng (sai số tuyệt đối 1e-6) | Đặc trưng | Kỳ vọng |
| --- | --- | --- | --- |
| `n_words` | 14 | `vad_silence_ratio` | 0,309091 |
| `words_per_sec` | 1,272727 | `vad_mean_pause` | 0,966667 |
| `total_dur` | 11,0 | `vad_pause_per_min` | 16,363636 |
| `mean_word_len` | 3,214286 | `vad_long_pause_ratio` | 0,333333 (1,0 s **không** tính là dài) |
| `ttr` | 0,785714 (11/14) | `vad_pause_sd` | 0,449691 |
| `log_uniq` | 2,484907 | `vad_mean_seg_len` | 2,533333 |
| `asr_conf_mean` | 0,819231 (13 prob, bỏ `None`) | `vad_n_seg_per_min` | 16,363636 |
| `asr_conf_geo` | 0,806303 | `vad_articulation_rate` | 1,842105 |
| | | `vad_onset_delay` | 0,5 |
| | | `vad_speech_sec` | 7,6 |

Fixture chỉ kiểm công thức; không nằm trong khoảng huấn luyện và không phải dữ liệu người học. Unit test dùng `FakeVad` trả segment dựng sẵn, không import `torch`/`silero_vad`.

## FR/AC → Test

| Test ID | FR / AC | Level | Tình huống | Kỳ vọng |
| --- | --- | --- | --- | --- |
| M04-TEST-001 | FR-001 / AC-001 | Unit | FX-TEXT + FX-VAD | 18 giá trị đúng bảng trên; mỗi FeatureValue có `unit` theo catalogue và `missing_reason=None` |
| M04-TEST-002 | FR-001 / AC-001 | Unit (boundary) | Hai segment cách nhau đúng 0,30 s; đuôi đúng 0,30 s | Không khoảng nào thành ngừng (điều kiện `> 0,30`) |
| M04-TEST-003 | FR-001 / AC-001 | Unit (boundary) | Một segment duy nhất phủ gần hết bài, đuôi 0,1 s | `P` rỗng → #10, #12, #13 = `0` (giá trị đo thật), `missing_reason=None` |
| M04-TEST-004 | FR-002 / AC-001 | Unit | Transcript `status=UNRELIABLE` | #1, 2, 4–8, 16 = `None` + `FEATURE_NOT_COMPUTABLE`; #3, 9–15, 17, 18 vẫn tính |
| M04-TEST-005 | FR-002 / AC-001 | Unit (boundary) | 9 token / 10 token | 9 → #4, 5, 6 = `None` + `TOO_FEW_WORDS`; 10 → tính bình thường |
| M04-TEST-006 | FR-002 / AC-001 | Unit | Mọi word `prob=None` | #7, 8 = `None` + `FEATURE_NOT_COMPUTABLE`; không có `0.0` |
| M04-TEST-007 | FR-002 / AC-002 | Unit (regression) | VAD trả danh sách segment rỗng | #9–18 = `None` + `FEATURE_NOT_COMPUTABLE` — regression REF-04 (trước đây ra `0.0`) |
| M04-TEST-008 | FR-002 / AC-001 | Unit (invalid) | `D = 0`; `D < 0` | Cả 18 = `None` + `FEATURE_NOT_COMPUTABLE`; không exception chia 0 |
| M04-TEST-009 | FR-002 / AC-001 | Unit (invalid) | Engine giả cho prob `NaN` làm kết quả NaN | Đặc trưng bị ảnh hưởng = `None` + `FEATURE_NOT_COMPUTABLE` |
| M04-TEST-010 | FR-003 / AC-003 | Unit | Đọc `feature_order` từ `ridge_resp_v2.json` | `values` có đúng 18 tên, **đúng thứ tự** artifact; không có `filler_ratio` — regression REF-05 |
| M04-TEST-011 | FR-003 / AC-003 | Unit | Transcript `UNRELIABLE` (như 004) | Vẫn đủ 18 tên đúng vị trí; tên bị null không bị bỏ |
| M04-TEST-012 | FR-003 / AC-003 | Unit (failure) | Artifact giả có tên `foo_bar` không có trong catalogue | Dừng với lỗi cấu hình; không trả FeatureSet thiếu tên |
| M04-TEST-013 | FR-003 / AC-003 | Unit | Artifact giả `feature_version="v4"` | FeatureSet mang `FEATURE_VERSION_MISMATCH` |
| M04-TEST-014 | FR-004 / AC-004 | Unit | VAD giả tên `silero`, `threshold 0.5`, `min_silence 150` | `vad_name="silero"`, tham số ghi đủ; không reason lệch |
| M04-TEST-015 | FR-004 / AC-004 | Unit | Ba biến thể: `vad_name="energy"`; `threshold 0.6`; `min_silence 200` | Mỗi biến thể → `VAD_VERSION_MISMATCH` |
| M04-TEST-016 | FR-004 / AC-004 | Unit (regression) | Loader Silero raise `ImportError` | **Không** dùng VAD khác; #9–18 và #16 = `None` + `FEATURE_NOT_COMPUTABLE` — regression REF-03 |
| M04-TEST-017 | FR-001 / AC-002 | Unit (privacy) | Transcript chứa `SECRET-NAME-123`; `caplog` + serialize FeatureSet | Chuỗi không xuất hiện trong FeatureSet JSON lẫn log |
| M04-TEST-018 | FR-001 / AC-001 | Unit | Chạy FX-TEXT + FX-VAD hai lần | Hai FeatureSet bằng nhau từng bit; giá trị không làm tròn |
| M04-TEST-S1 | FR-004 / AC-004 | **Smoke** | Silero 6.2.1 thật trên audio có quyền dùng (16 kHz mono), tắt mạng | Evidence: phiên bản gói, license, số segment, 10 giá trị `vad_*`; chạy được khi tắt mạng |

## Bao phủ theo loại

| Loại | Test |
| --- | --- |
| Success | 001, 010, 014, S1 |
| Invalid | 008, 009, 012 |
| Boundary | 002, 003, 005 |
| Failure / recovery | 004, 006, 016 (phục hồi = sửa môi trường Silero rồi chạy lại) |
| Regression | 007 (REF-04), 010 (REF-05), 016 (REF-03) |
| Privacy / tất định | 017, 018 |
| Browser/manual | N/A — M04 không có giao diện |

## Lệnh và coverage

| Mục | Giá trị |
| --- | --- |
| Unit | `python3 -m pytest -q -m "not smoke" tests/features` |
| Coverage | `python3 -m pytest -q -m "not smoke" --cov=aicefr.features --cov-branch --cov-report=term-missing tests/features` |
| Smoke | `AICEFR_SMOKE_AUDIO=<đường dẫn ngoài repo> python3 -m pytest -q -m smoke tests/smoke/test_vad_smoke.py` |
| UT applicability | **YES** cho 18 công thức, bảng dữ liệu thiếu, kiểm nhất quán. **NO** cho lời gọi Silero thật — thay bằng smoke S1 |
| Coverage policy | **TP-D-001** — xem [M03 Test Plan](../m03-asr/04-test-plan.md#quyết-định-cần-user--tp-d-001-chung-m03m04m05) |
| Hiện trạng | Unit chạy trên `main` từ 26/09/2026 (M04-EV-001). TEST-016 (Silero thật không nạp được) và smoke S1 chạy thật 11/10/2026: PASS ([M04-EV-002](evidence/evidence-manifest.md)) |

**CODEX CHECK RESULT:** mỗi FR/AC có test; 18 đặc trưng có giá trị kỳ vọng số; đủ success/invalid/boundary/failure/regression; không thêm requirement. TP-D-001 chốt theo khuyến nghị. **User verdict Phase 04:** APPROVED 26/09/2026 (Sang).

## Lịch sử phiên bản

| Phiên bản | Ngày | Thay đổi |
| --- | --- | --- |
| v0.1 | 25/09/2026 | Bản nháp đầu (3 đặc trưng) |
| v0.2 | 26/09/2026 | **APPROVED** Phase 04. Theo Spec v0.2: fixture chuẩn có giá trị kỳ vọng cho 18 đặc trưng, 18 unit + 1 smoke |
