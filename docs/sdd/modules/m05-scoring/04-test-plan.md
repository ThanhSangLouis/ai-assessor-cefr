# M05 — 04 Test Plan (Kế hoạch kiểm thử)

> **v0.2 · 26/09/2026 · APPROVED Phase 04 ngày 26/09/2026.** Dựa trên [Specification v0.2 APPROVED](03-specification.md). Mọi test ở đây là **ca dự kiến, chưa chạy**. Không thêm hành vi ngoài Specification.

## Fixture

- **ART-REAL:** `ridge_resp_v2.json` thật (SHA-256 `7cdeb2a0…b521a`). Vị trí file chốt ở Phase 05.
- **ART-FAKE:** artifact JSON nhỏ do nhóm tạo (2 đặc trưng, hệ số dễ tính) cho ca clip và ca lỗi; hash ghim riêng trong fixture.
- **FS(v):** FeatureSet hợp lệ với vector `v`, `asr_model="whisper-small"`, `vad_name="silero"`, `vad_threshold=0.5`, `vad_min_silence_ms=150`, `feature_version="v3"`, transcript `OK`.

### Giá trị vàng trên ART-REAL (tính từ công thức Spec ngày 26/09/2026, sai số 1e-4)

Ba vector: `mean` của artifact (mọi `z = 0`), `feature_lo`, `feature_hi`. Kỳ vọng được test tính lại từ chính artifact theo công thức Spec:
`overall = clip(intercept + Σ coef·(x − mean)/scale, 1, 6)`; band theo `band_thresholds`; `status = REVIEW_REQUIRED` khi điểm cách một ngưỡng không quá `boundary_margin`, ngược lại `ESTIMATED`. Với `mean`, `overall` phải bằng `intercept`.

Không ghi số cụ thể ở đây: chúng suy ra từ S&I, license không cho công bố khi chưa được CUP&A duyệt (W4-S4, SCRUM-51). Cả ba vector nằm trong khoảng chấp nhận OOD. Đây là giá trị kiểm công thức, **không** phải metric chất lượng model.

## FR/AC → Test

| Test ID | FR / AC | Level | Tình huống | Kỳ vọng |
| --- | --- | --- | --- | --- |
| M05-TEST-001 | FR-001 / AC-002 | Unit | Ba vector vàng trên ART-REAL | Score, band, status đúng bảng; provenance đủ 8 trường, đọc từ artifact |
| M05-TEST-002 | FR-001 / AC-002 | Unit (tất định) | Chấm `FS(mean)` hai lần | Hai Assessment bằng nhau trừ `scored_at` |
| M05-TEST-003 | FR-001 / AC-002 | Unit | `FS(hi)` | Đúng 5 `CriterionCoverage`, mỗi dòng `coverage=1.0`, **không** có trường score/band; fluency = 1,0 — regression F-05 (`filler_ratio`) |
| M05-TEST-004 | FR-002 / AC-001 | Unit | Mọi Assessment trong file test | `interaction.level is None`, `score_status="insufficient_evidence"` |
| M05-TEST-005 | FR-001 / AC-001 | Unit (failure) | File artifact không tồn tại | `NOT_EVALUATED` + `MODEL_VERSION_MISSING`; `overall_*=None` |
| M05-TEST-006 | FR-001 / AC-001 | Unit (failure) | Artifact bị sửa 1 byte (hash lệch) | `NOT_EVALUATED` + `MODEL_ARTIFACT_INVALID`; không fallback band |
| M05-TEST-007 | FR-001 / AC-001 | Unit (failure) | ART-FAKE với `unit_of_inference="ca bai thi"` và bản thiếu trường này | Cả hai → `MODEL_ARTIFACT_INVALID` |
| M05-TEST-008 | FR-001 / AC-001 | Unit | Transcript `UNRELIABLE` + `ASR_HALLUCINATION` | `NOT_EVALUATED`, giữ reason của M03 |
| M05-TEST-009 | FR-003 / AC-003 | Unit | `FS(mean)` nhưng `asr_model="whisper-medium"` | `NOT_EVALUATED` + `ASR_VERSION_MISMATCH`; `overall_*=None` |
| M05-TEST-010 | FR-003 / AC-003 | Unit | `FS(mean)` nhưng `vad_name="energy"` | `NOT_EVALUATED` + `VAD_VERSION_MISMATCH` |
| M05-TEST-011 | FR-003 / AC-003 | Unit | Hai tên đầu `feature_order` đổi chỗ trong FeatureSet | `NOT_EVALUATED` + reason lệch `feature_order` (`FEATURE_VERSION_MISMATCH`) |
| M05-TEST-012 | FR-003 / AC-003 | Unit | `asr_model` và `vad_name` cùng lệch | Cả hai reason có mặt (gộp mọi mục lệch) |
| M05-TEST-013 | FR-003 / AC-003 | Unit (regression) | `asr_model="whisper-small.en"` | `ASR_VERSION_MISMATCH` — regression F-09 (so chuỗi con) |
| M05-TEST-014 | FR-002 / AC-001 | Unit | `FS(mean)` với `vad_pause_sd=None` | `NOT_EVALUATED` + `FEATURE_NOT_COMPUTABLE`; `criteria` đều `coverage=None` |
| M05-TEST-015 | FR-002 / AC-001 | Unit (boundary) | `FS(mean)` với `total_dur` = 77,78 (dưới giới hạn) và 80,0 | 77,78 → không OOD; 80,0 → `NOT_EVALUATED` + `OUT_OF_DISTRIBUTION`, chi tiết có `feature="total_dur"`, `accepted_high≈77,780`, `too="high"` |
| M05-TEST-016 | FR-002 / AC-001 | Unit (boundary) | Hàm band: 2,7499 / 2,75 / 3,7499 / 3,75 | A2 / B1 / B1 / B2 |
| M05-TEST-017 | FR-002 / AC-001 | Unit (boundary) | Near-boundary margin 0,5: 2,25 / 2,2499 / 4,25 / 4,2501 | có / không / có / không |
| M05-TEST-018 | FR-001 / AC-002 | Unit (boundary) | ART-FAKE cho `raw = 7,2` và `raw = 0,4` | Clip 6,0 và 1,0 |
| M05-TEST-019 | FR-001 / AC-001 | Unit | ART-FAKE có `scale = 0` cho một đặc trưng | Dùng 1 thay cho scale; không chia 0 |
| M05-TEST-020 | FR-002 / AC-001 | Unit | Hàm tính coverage (gọi trực tiếp, vì Assessment có đặc trưng thiếu luôn là `NOT_EVALUATED`) với một đặc trưng fluency `None` | fluency = 0,80 (4/5) + `FEATURE_NOT_COMPUTABLE` trên dòng đó |
| M05-TEST-021 | FR-001 / AC-001 | Unit (privacy) | `caplog` khi chấm `FS(mean)` có `response_id` | Log có `response_id`, status, reason, `model_version`; không có vector đặc trưng |
| M05-TEST-022 | FR-001 / AC-002 | Integration (không model nặng) | FeatureSet do M04 dựng từ fixture chuẩn (M04 FX) → M05. (a) ART-REAL, SKIP khi thiếu artifact; (b) hai biến thể ART-FAKE chạy trên CI: khoảng nhận rộng và VAD lệch cấu hình | (a) `NOT_EVALUATED` + `OUT_OF_DISTRIBUTION` với **đúng một** đặc trưng lệch: `log_uniq` của fixture (2,4849, chỉ 11 từ khác nhau) thấp hơn `accepted_low` đọc từ artifact. (b) Tên/thứ tự/provenance khớp nên đi hết 8 bước; VAD lệch thì `VAD_VERSION_MISMATCH` đi từ M04 sang M05. Kiểm hợp đồng M04→M05, không kiểm điểm |

Metric chất lượng model (PCC/RMSE trên pipeline dự án) cần dữ liệu có quyền dùng và protocol được duyệt → **không** thuộc Test Plan W2; báo cáo chỉ trích metric của artifact kèm nguồn.

## Bao phủ theo loại

| Loại | Test |
| --- | --- |
| Success | 001, 003 |
| Invalid | 007, 009–012 |
| Boundary | 015–018 |
| Failure / recovery | 005, 006, 008, 014 (phục hồi = sửa artifact/cấu hình rồi chấm lại) |
| Regression | 003 (F-05), 013 (F-09) |
| Tất định / privacy | 002, 021 |
| Liên module | 022 |
| Browser/manual | N/A — M05 không có giao diện |

## Lệnh và coverage

| Mục | Giá trị |
| --- | --- |
| Unit + integration | `python3 -m pytest -q -m "not smoke" tests/scoring` |
| Coverage | `python3 -m pytest -q -m "not smoke" --cov=aicefr.scoring --cov-branch --cov-report=term-missing tests/scoring` |
| UT applicability | **YES** cho toàn bộ M05 (logic thuần, chỉ đọc JSON) — không cần smoke |
| Coverage policy | **TP-D-001** — xem [M03 Test Plan](../m03-asr/04-test-plan.md#quyết-định-cần-user--tp-d-001-chung-m03m04m05) |
| Hiện trạng | `NOT_RUN` — chưa có mã nguồn; hai reason code mới chờ Thắng đưa vào contract chung |

**CODEX CHECK RESULT:** mỗi FR/AC có test; 8 bước kiểm của Spec đều có ca; giá trị vàng tính sẵn; không thêm requirement. TP-D-001 chốt theo khuyến nghị. **User verdict Phase 04:** APPROVED 26/09/2026 (Sang).

## Lịch sử phiên bản

| Phiên bản | Ngày | Thay đổi |
| --- | --- | --- |
| v0.1 | 25/09/2026 | Bản nháp đầu (6 ca) |
| v0.2 | 26/09/2026 | **APPROVED** Phase 04. Theo Spec v0.2: 21 unit + 1 integration, giá trị vàng trên artifact thật, ca biên band/near-boundary/OOD |
| v0.2.1 | 03/10/2026 | Chỉ sửa dòng M05-TEST-022: thêm hai biến thể ART-FAKE chạy trên CI (hợp đồng tên/thứ tự/provenance, VAD lệch) và đọc `accepted_low` từ artifact thay vì ghi số. Không đổi FR/AC; chờ owner xác nhận khi review Phase 07 của M05-TASK-004 |
