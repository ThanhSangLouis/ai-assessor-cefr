# W6-S03 — Chạy một bài qua pipeline thật trên `main` (SCRUM-80)

Ngày chạy: 22/10/2026 · base `main` `cabcc44` · người chạy: Sang (thực hiện cùng Claude) · máy macOS, CPU.

## Đầu vào

| Mục | Giá trị |
| --- | --- |
| Audio | Giọng tổng hợp tiếng Anh của macOS (`say -v Samantha`), đọc một đoạn văn tự viết về học trực tuyến và học trên lớp; đổi sang WAV 16 kHz mono. **Không phải giọng người học.** Kế hoạch W6 cho phép dùng giọng tổng hợp. Tệp nằm ngoài Git |
| SHA-256 audio | `8eeb9d094d71885a89dc736c5a9a44773269e2b92cfa8289c216afad3b413002` |
| Thời lượng | 42,7 giây |
| ASR | `faster-whisper@1.2.1`, model `whisper-small` (thư mục model cục bộ, ngoài Git) |
| VAD | Silero (gói `silero-vad`), ngưỡng 0,5, im lặng tối thiểu 150 ms |
| Mô hình chấm | `ridge_resp_v2`, SHA-256 `7cdeb2a04aa0db770d52d6ff20b49cc371b9cb690f0ace89e5233b5d65bb521a` (đúng pin trong `docs/local-run.md`) |
| Hiệu chuẩn CV+ | Artifact tham chiếu ghim, SHA-256 `3c09d2583a26e8cc057c0cf36dfb7637d15dfdc901cf00c4e25faef9ce6ef885` (đúng `PINNED_REFERENCE_SHA256` trong `scoring/conformal.py`), ngoài Git |
| Cấu hình QC | `demo-qc-v1` của `docs/local-run.md`, chưa phải ngưỡng vận hành đã nghiệm thu |

## Lệnh

Script chạy và cấu hình nằm ngoài repo (`aicefr-runtime/w6-s03-2026-10-22/`). Script làm theo `scripts/qa/parity_model_smoke.py` nhưng chỉ cho một audio:

1. `create_runtime` với cấu hình trên;
2. tạo tài khoản fixture và kích hoạt đồng thuận `demo-v1`;
3. nộp audio qua `StudentApi.submit` (đồng bộ);
4. đọc báo cáo, ghi đầy đủ vào `evidence/report.json` (ngoài Git) và tóm tắt vào `evidence/summary.json`.

## Kết quả (không ghi điểm hay band)

| Mục | Kết quả |
| --- | --- |
| Trạng thái bài | `COMPLETED`; báo cáo `PROVISIONAL`, `assessment_status = ESTIMATED` |
| Có ước lượng tổng | Có (giá trị nằm trong evidence ngoài Git, không công bố) |
| `teacher_verified` | `false` (đúng bất biến: máy không tự xác nhận) |
| Reason code của bài | không có |
| Trust Layer · disposition | `CONTINUE`, không reason |
| Nhận diện ngôn ngữ | `faster-whisper-detect-v1` 1.2.1 → `en`, `ENGLISH` |
| Tập dự đoán CV+ | `calibration_id = reference-bf2a9720f023259c`, alpha mặc định; tập gồm **1 band** (không ghi cận dưới/trên vì suy ra từ phần dư S&I) |
| Lá chắn lạc đề / đọc đề | `insufficient_evidence` cả hai: đề `demo-speaking` của cấu hình demo không có từ khoá chủ đề và lời đề để so |
| `evidence_issues` | rỗng |
| `source_versions` | `assessment = ridge_resp_v2`, `feature_version = v3`, `asr_model = whisper-small`, `asr_engine = faster-whisper@1.2.1`, `band_map_version = band-v1`, `qc_config = demo-qc-v1` |
| Thời gian chạy | 13,8 giây (gồm nạp model) |

## Giới hạn và việc còn lại

- **Đây là smoke kỹ thuật, không đo độ chính xác CEFR.** Giọng tổng hợp không đại diện người học Việt Nam; một bài không nói gì về chất lượng chấm. Độ chính xác: `NOT_MEASURED`; độ phủ thực nghiệm của CV+: `NOT_EVALUATED`.
- `source_versions.calibration_version = chua-hieu-chuan` **không mâu thuẫn** với việc Trust Layer đã dùng artifact hiệu chuẩn. Trường này lấy từ artifact Ridge (`scoring/scorer.py` `_provenance`, `ridge_resp_v2.json`) và nói về việc hiệu chuẩn **điểm số** của mô hình, mà điểm số đúng là chưa được hiệu chuẩn. Khoảng dự đoán CV+ của Trust Layer được ghi riêng ở `provenance.calibration_id` và `calibration_sha256`. Đã kiểm lại mã ngày 22/10/2026; không cần sửa.
- Lá chắn lạc đề và đọc đề chưa được thử trên đề thật có từ khoá; cần chạy lại với đề P3/P4 khi cấu hình đề thật có trong runtime cục bộ.
- Không có số liệu Speak & Improve nào trong tệp này.

Đây là bằng chứng kỹ thuật do Sang chạy, không phải verdict; reviewer và chủ dự án ghi verdict Phase 07–09.
