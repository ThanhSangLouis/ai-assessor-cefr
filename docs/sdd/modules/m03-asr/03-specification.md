# M03 — 03 Specification (Đặc tả)

> **v0.2 · 26/09/2026 · APPROVED Phase 03 ngày 26/09/2026.** Dựa trên [Requirement v0.2 APPROVED](01-requirement.md) và [Research v0.2](02-research.md). Chưa cấp quyền phát prompt triển khai (cần Phase 04, 05).

**Owner:** Sang. **Mục tiêu W2:** Transcript local từ `whisper-small`, có provenance, word timestamp/confidence nullable và trạng thái bất định; smoke trên audio có quyền dùng khi model đã được tải có chủ đích.

## Boundary và hợp đồng

| Artifact | Trường / invariant | Owner → consumer |
| --- | --- | --- |
| AsrInput | `response_id`; `DecodedAudio` (PCM float32, mono, **16 kHz** — chờ M03-O-002); `QCResult.status ∈ {PASS, REVIEW}`; `language="en"` | M02 → M03 |
| Word | `text`; `start_s`, `end_s` (float, giây); `prob` ∈ [0,1] **hoặc `null`** | M03 → M04/M06 |
| Transcript | `response_id`; `status` (dưới); `text` verbatim; `words: list[Word]`; `asr_model` (identifier chuẩn, xem bảng ánh xạ); `engine` + `engine_version`; `decode_config_version`; `audio_sha256`; `reasons: list[ReasonCode]` | M03 → M04/M06 |
| AsrStatus | `OK` · `UNRELIABLE` · `ASR_FAILED` · `NOT_RUN` | M03 → pipeline/M07 |
| AsrEngine port | `transcribe(audio) -> Transcript`; adapter local; test double mang `test_only=true` | nội bộ M03 |

### Bảng ánh xạ identifier (M03-FR-003)

`asr_model` là **identifier chuẩn**, không phải tên repo weight. Config ánh xạ tường minh, ví dụ `{"<tên weight đã tải>": "whisper-small"}`. So khớp với `trained_with.asr_model` là **so bằng tuyệt đối** (`==`). Weight không có trong bảng → `asr_model = null` + `ASR_VERSION_MISMATCH`. `whisper-small.en` **không** ánh xạ về `whisper-small` (Research F-04).

## Hành vi

1. Chỉ chạy khi `QCResult.status ∈ {PASS, REVIEW}`; `REJECT` → `NOT_RUN`, không gọi engine, `reasons` = `QCResult.reasons` của M02 (chép nguyên, giữ thứ tự) để M05/M06 báo được lý do.
2. Decode config khởi đầu (có version `asr-decode-v1`): `word_timestamps=true`, `language="en"`, `condition_on_previous_text=false`, `compression_ratio_threshold=2.4`, log-prob threshold `-1.0`, `no_speech_threshold=0.6` (Research F-02). Engine: faster-whisper (CTranslate2) model `small` cho mọi môi trường (M03-O-001); tham số riêng của engine (ví dụ `vad_filter`) ghi trong `asr-decode-v1` và evidence smoke.
3. Giữ filler và thứ tự lời nói trong `text`/`words`; không chuẩn hóa, không thêm từ.
4. Engine không trả probability cho một word → `prob = null` (không bao giờ 0.0 — REF-03).
5. Model không có sẵn local → `NOT_RUN` + `ASR_FAILED`; **không tự tải** (D-002).
6. Sau decode chạy bộ phát hiện (REF-04), ngưỡng trong config `hallucination-v1`:

| Luật | Ngưỡng khởi đầu | Kết quả |
| --- | --- | --- |
| Lặp một token liên tiếp | `> 6` lần | `UNRELIABLE` + `ASR_HALLUCINATION` |
| Một token chiếm tỷ lệ | `> 0.35` khi `≥ 60` từ | như trên |
| Cụm 3–10 từ lặp | `≥ 3` lần | như trên |
| Đuôi prob thấp | `≥ 5` từ cuối có `prob < 0.05` | như trên |
| Đồng hồ đứng | `≥ 4` từ liên tiếp `< 0.05 s/từ` | như trên |

7. Transcript rỗng khi QC báo có tiếng → `UNRELIABLE` + `ASR_EMPTY_TRANSCRIPT`.
8. `asr_model ≠ trained_with.asr_model` của artifact M05 đang cấu hình → thêm `ASR_VERSION_MISMATCH`; `status` giữ nguyên (lệch phiên bản không làm transcript sai, chỉ chặn band ở M05-FR-003).

## Lỗi và phục hồi

| Tình huống | Status | Reason | Phục hồi |
| --- | --- | --- | --- |
| Engine exception / timeout | `ASR_FAILED` | `ASR_FAILED` | Chạy lại thủ công; không tạo transcript |
| Timestamp âm, `end < start`, không đơn điệu, vượt duration | `ASR_FAILED` | `ASR_FAILED` | Giữ diagnostic metadata, không giữ words |
| Hallucination (bảng trên) | `UNRELIABLE` | `ASR_HALLUCINATION` | M04 không tính đặc trưng text (M03-FR-002); chuyển review |
| Model không có local | `NOT_RUN` | `ASR_FAILED` | Owner tải có chủ đích, ghi evidence |
| QC `REJECT` | `NOT_RUN` | Các mã `QC_*` của M02, chép từ `QCResult.reasons` | Sinh viên thu lại; M02 bảo đảm REJECT luôn có ít nhất một lý do |

## Bảo mật, riêng tư, accessibility

- Không gọi mạng khi chạy (cả engine lẫn tải model); smoke kiểm bằng cách chạy khi tắt mạng.
- Log chỉ ghi `response_id`, status, reason, thời gian xử lý; không log `text`/`words`/audio.
- Transcript lưu qua M08 với quyền truy cập của bài nộp.
- Accessibility: N/A — M03 không có giao diện.

## Reason code dùng (đề nghị Thắng đưa vào contract chung)

`ASR_FAILED`, `ASR_EMPTY_TRANSCRIPT`, `ASR_HALLUCINATION`, `ASR_VERSION_MISMATCH` — cả bốn đã có trong hồ sơ tham chiếu (Research F-09).

## Trace Requirement → AC

| Requirement | AC | Quan sát |
| --- | --- | --- |
| M03-FR-001 | M03-AC-001, M03-AC-002 | Provenance đủ trường; `prob=null` khi engine không trả |
| M03-FR-002 | M03-AC-001 | Fixture lỗi → `ASR_FAILED`; fixture lặp → `UNRELIABLE` |
| M03-FR-003 | M03-AC-003 | Ánh xạ khớp → không reason; `whisper-small.en` hoặc weight lạ → `ASR_VERSION_MISMATCH` |

## Giả định, phụ thuộc, câu hỏi mở

| Loại | Nội dung |
| --- | --- |
| Phụ thuộc | M05 cung cấp `trained_with.asr_model` từ artifact đang cấu hình |
| Rủi ro → Test Plan | Phân phối `asr_conf_mean` từ engine local so với khoảng huấn luyện ghi trong artifact (`feature_lo`/`feature_hi`, ngoài repo) (Research I-01) |
| Quyết định | **M03-O-001** — faster-whisper `small` cho mọi môi trường (user chốt 26/09/2026) |
| Phụ thuộc | **M03-O-002** — yêu cầu 16 kHz mono giữ nguyên; Thắng xác nhận phía M02 trước Phase 05 |

**CODEX CHECK RESULT:** FR/AC trace đủ; success/invalid/failure/recovery có; security/privacy có, accessibility N/A có lý do. **User verdict Phase 03:** APPROVED 26/09/2026 (Sang), theo khuyến nghị.

## Lịch sử phiên bản

| Phiên bản | Ngày | Thay đổi |
| --- | --- | --- |
| v0.1 | 25/09/2026 | Bản nháp đầu |
| v0.2 | 26/09/2026 | **APPROVED** Phase 03. Theo Requirement v0.2: `whisper-small`, bảng ánh xạ identifier, `prob=null`, bộ phát hiện hallucination có ngưỡng, bảng lỗi; M03-O-001 chốt, M03-O-002 thành phụ thuộc M02 |
| v0.2.1 | 03/10/2026 | Follow-up 07-A1-03 (SCRUM-50): QC `REJECT` chép `QCResult.reasons` sang Transcript; thêm dòng bảng lỗi. Không đổi FR/AC; chờ owner xác nhận ở Phase 07 |
