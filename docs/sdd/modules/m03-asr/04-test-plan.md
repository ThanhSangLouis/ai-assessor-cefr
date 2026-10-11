# M03 — 04 Test Plan (Kế hoạch kiểm thử)

> **v0.2 · 26/09/2026 · APPROVED Phase 04 ngày 26/09/2026.** Dựa trên [Specification v0.2 APPROVED](03-specification.md). Mọi test ở đây là **ca dự kiến, chưa chạy** — repo dự án chưa có mã nguồn. Không thêm hành vi ngoài Specification.

## Fixture và nguyên tắc

- **Unit:** `FakeAsrEngine` trả `Word` dựng sẵn (không import `faster_whisper`/`torch`); không mạng, không đồng hồ thật, không ngẫu nhiên. Fixture do nhóm tự tạo, không phải audio người học.
- **Smoke:** marker `smoke`, cần weight `whisper-small` đã tải có chủ đích (M03-D-002) và audio có quyền dùng đặt **ngoài repo** (đường dẫn qua biến môi trường). Thiếu một trong hai → `NOT_RUN`, không thay bằng kết quả giả.
- Tên test theo mẫu `test_<chủ thể>_<tình huống>_<kỳ vọng>`, cấu trúc Arrange–Act–Assert.

## FR/AC → Test

| Test ID | FR / AC | Level | Tình huống | Kỳ vọng |
| --- | --- | --- | --- | --- |
| M03-TEST-001 | FR-001 / AC-001 | Unit | Fake engine trả 3 word đủ timestamp/prob | `status=OK`; `words` giữ nguyên thứ tự và filler; có `asr_model`, `engine`, `engine_version`, `decode_config_version="asr-decode-v1"`, `audio_sha256`; `test_only=true` |
| M03-TEST-002 | FR-001 / AC-001 | Unit | Một word không có probability | Word đó `prob is None` (không phải `0.0`); các word khác giữ giá trị — regression REF-03 |
| M03-TEST-003 | FR-002 / AC-001 | Unit (failure) | Engine raise exception; engine timeout | `status=ASR_FAILED`, reason `ASR_FAILED`, `words` rỗng |
| M03-TEST-004 | FR-002 / AC-001 | Unit (invalid) | Bốn biến thể timestamp: `start<0`; `end<start`; word sau bắt đầu trước word trước; `end > duration` | Mỗi biến thể → `ASR_FAILED`; không trả words |
| M03-TEST-005 | FR-002 / AC-001 | Unit | QC `REJECT` có hai lý do | `status=NOT_RUN`; spy xác nhận engine **không** được gọi; `reasons` bằng đúng `QCResult.reasons`, giữ thứ tự; nối sang M05 ra `NOT_EVALUATED` với đúng lý do QC |
| M03-TEST-006 | FR-001 / AC-002 | Unit (failure) | Thư mục model không tồn tại | `NOT_RUN` + `ASR_FAILED`; không có lời gọi tải (loader giả ghi nhận 0 lần tải) |
| M03-TEST-007 | FR-002 / AC-001 | Unit (boundary) | Transcript rỗng khi QC `PASS` | `UNRELIABLE` + `ASR_EMPTY_TRANSCRIPT` |
| M03-TEST-008 | FR-002 / AC-001 | Unit (boundary) | Lặp một token 6 lần / 7 lần liên tiếp | 6 → `OK`; 7 → `UNRELIABLE` + `ASR_HALLUCINATION` |
| M03-TEST-009 | FR-002 / AC-001 | Unit (boundary) | 60 từ, một token chiếm đúng 0,35 / 0,367 (22/60); 59 từ với token chiếm 0,5 | 0,35 → không cờ; 22/60 → cờ; 59 từ → không áp luật |
| M03-TEST-010 | FR-002 / AC-001 | Unit (boundary) | Cụm 3 từ lặp 2 / 3 lần | 2 → không cờ; 3 → cờ |
| M03-TEST-011 | FR-002 / AC-001 | Unit (boundary) | 4 / 5 từ cuối có `prob < 0.05` | 4 → không cờ; 5 → cờ |
| M03-TEST-012 | FR-002 / AC-001 | Unit (boundary) | 3 / 4 từ liên tiếp dài `< 0.05 s` | 3 → không cờ; 4 → cờ |
| M03-TEST-013 | FR-003 / AC-003 | Unit | Weight được ánh xạ về `whisper-small`, `trained_with.asr_model="whisper-small"` | `asr_model="whisper-small"`; không có `ASR_VERSION_MISMATCH` |
| M03-TEST-014 | FR-003 / AC-003 | Unit (regression) | Weight tên `whisper-small.en` (không có trong bảng ánh xạ) | `asr_model=None` + `ASR_VERSION_MISMATCH`; `status` không đổi — regression F-04 (so chuỗi con) |
| M03-TEST-015 | FR-003 / AC-003 | Unit | Weight ánh xạ về `whisper-medium`, artifact đòi `whisper-small` | `ASR_VERSION_MISMATCH`; `status=OK` giữ nguyên |
| M03-TEST-016 | FR-001 / AC-001 | Unit (privacy) | Transcript fixture chứa chuỗi `SECRET-NAME-123`; chạy với `caplog` | Không bản ghi log nào chứa chuỗi đó; log có `response_id` và status |
| M03-TEST-S1 | FR-001 / AC-002 | **Smoke** | faster-whisper `small` trên audio có quyền dùng, **tắt mạng** | Ghi evidence: tên weight, nguồn, license, SHA-256, `engine_version`, decode config, máy (OS/CPU/RAM), thời gian xử lý, `status`. Mạng tắt mà vẫn chạy được |
| M03-TEST-S2 | Rủi ro Spec (Research I-01) | **Smoke — quan sát** | Cùng lượt S1: tính `asr_conf_mean` | **Ghi lại** giá trị và so với khoảng huấn luyện [0,691 ; 0,950]. Không phải tiêu chí pass/fail của M03; nếu nằm ngoài khoảng chấp nhận OOD thì báo owner M05 |

## Bao phủ theo loại

| Loại | Test |
| --- | --- |
| Success | 001, 013, S1 |
| Invalid | 004, 005 |
| Boundary | 007–012 |
| Failure / recovery | 003, 006 (phục hồi = owner tải model có chủ đích rồi chạy lại S1) |
| Regression | 002 (REF-03), 014 (F-04) |
| Privacy | 016 |
| Browser/manual | N/A — M03 không có giao diện |

## Lệnh và coverage

| Mục | Giá trị |
| --- | --- |
| Unit | `python3 -m pytest -q -m "not smoke" tests/asr` |
| Coverage | `python3 -m pytest -q -m "not smoke" --cov=aicefr.asr --cov-branch --cov-report=term-missing tests/asr` |
| Smoke | `AICEFR_SMOKE_AUDIO=<đường dẫn ngoài repo> python3 -m pytest -q -m smoke tests/smoke/test_asr_smoke.py` |
| UT applicability | **YES** cho ánh xạ identifier, kiểm timestamp, bộ phát hiện hallucination, xử lý `prob`. **NO** cho lời gọi thật vào faster-whisper — thay bằng smoke S1 |
| Coverage policy | Theo quyết định chung **TP-D-001** (xem cuối file) |
| Hiện trạng | Unit chạy trên `main` từ 26/09/2026 (M03-EV-002, 003). Smoke S1/S2 chạy thật 11/10/2026: PASS, 0 lần thử kết nối mạng ([M03-EV-004](evidence/evidence-manifest.md)) |

## Evidence Phase 06/08

Command, thời điểm, exit code, số test pass/fail/skip, coverage report, revision; với smoke thêm các trường của S1. Không đưa audio, transcript hay weight vào Git/log.

## Quyết định cần user — TP-D-001 (chung M03/M04/M05)

**Đã chốt 26/09/2026 theo khuyến nghị.** Coverage đo bằng `pytest-cov` (coverage.py), **bật branch**, phạm vi = code thay đổi của `aicefr.asr`, `aicefr.features`, `aicefr.scoring`. **Khuyến nghị:** line ≥ 90 % và branch ≥ 85 % trên phần logic thuần; loại trừ hai adapter gọi thư viện nặng (faster-whisper, Silero) khỏi ngưỡng vì được kiểm bằng smoke; ngoài con số, mọi dòng trong bảng FR/AC → Test phải có test tương ứng. Lý do: ba module quyết định việc có phát band hay không, nhánh từ chối là nơi lỗi nguy hiểm nhất.

**CODEX CHECK RESULT:** mỗi FR/AC có test; đủ success/invalid/boundary/failure/regression; UT applicability và alternative evidence (smoke) rõ; không thêm requirement. TP-D-001 chốt theo khuyến nghị. **User verdict Phase 04:** APPROVED 26/09/2026 (Sang).

## Lịch sử phiên bản

| Phiên bản | Ngày | Thay đổi |
| --- | --- | --- |
| v0.1 | 25/09/2026 | Bản nháp đầu (5 ca) |
| v0.2 | 26/09/2026 | **APPROVED** Phase 04. Theo Spec v0.2: 16 unit + 2 smoke, ca biên cho từng luật hallucination, regression REF-03/F-04 |
| v0.2.1 | 03/10/2026 | Mở rộng M03-TEST-005 theo Spec v0.2.1 (lý do QC đi theo transcript). Chờ owner xác nhận ở Phase 07 |
