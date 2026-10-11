# M03 — 02 Research (khảo sát ASR)

> **v0.2 · 26/09/2026 · APPROVED cùng Phase 03 ngày 26/09/2026.** `RESEARCH MODE: RUN` đã được chọn tại Phase 01 (v0.2 APPROVED). File này tách **fact** (đọc/đo được), **inference** (suy luận), **option** và **quyết định cần user**; không thêm requirement mới ngoài M03-FR-001..003.

## Câu hỏi nghiên cứu

1. Engine nào chạy `whisper-small` (M03-D-001) local, offline, trên máy dev và máy triển khai của nhóm?
2. Engine trả word timestamp và word confidence với định nghĩa nào; M04 cần gì từ đó?
3. Phát hiện ASR lỗi/hallucination thế nào để M03-FR-002 kiểm được?
4. So khớp `asr_model` với `trained_with.asr_model` (M03-FR-003) chính xác đến mức nào?

## Reference contract

```text
TARGET REPO: thanglb2005/ai-assessor-cefr (repo dự án của nhóm)
REFERENCE SOURCE(S): hồ sơ kỹ thuật nội bộ do nhóm tạo (bản local mới nhất trên máy Sang;
  docs/sources gọi là ../ai-assessor-cefr-thamchie, bản chụp cũ hơn) — src/aicefr/asr/
  whisper_adapter.py, hallucination.py, pipeline.py (_version_mismatches);
  scoring/models/ridge_resp_v2.json (trained_with)
REFERENCE SCOPE: adapter ASR, decode options, bộ phát hiện lặp/hallucination, kiểm lệch phiên bản
MỨC TÁI SỬ DỤNG: ADAPT — dùng làm bằng chứng thiết kế; code dự án viết theo Spec này
PHẦN KHÔNG MANG SANG: model mặc định large-v3-turbo; mặc định 0.0 khi thiếu probability;
  so khớp phiên bản bằng chuỗi con
SOURCE ACCESS: đọc local, không chạy model, không tải gì qua mạng
HANDOFF MODE: tài liệu SDD; Antigravity chỉ nhận prompt sau Phase 05
```

## Fact đã kiểm (26/09/2026)

| ID | Fact | Nguồn / cách đo |
| --- | --- | --- |
| M03-F-01 | Hồ sơ tham chiếu mặc định `mlx-community/whisper-large-v3-turbo` (MLX, Apple Silicon) và `large-v3` (faster-whisper/CTranslate2, `compute_type=int8`) — **không phải** `whisper-small`. | `whisper_adapter.py` |
| M03-F-02 | Cả hai nhánh gọi `word_timestamps=True`, `language="en"`, `condition_on_previous_text=False`, `compression_ratio_threshold=2.4`, log-prob threshold `-1.0`, `no_speech_threshold=0.6`; MLX thêm `hallucination_silence_threshold=2.0`; CT2 thêm `vad_filter=True`. | `whisper_adapter.py` |
| M03-F-03 | Nhánh MLX đọc `w.get("probability", 0.0)`: word thiếu probability thành **0.0**. | `whisper_adapter.py` dòng 129 |
| M03-F-04 | Kiểm lệch ASR là `expected_asr not in asr.model_version` (chuỗi con). `"whisper-small"` cũng là chuỗi con của `whisper-small.en` — một model khác (chỉ tiếng Anh, trọng số khác). | `pipeline.py` `_version_mismatches` |
| M03-F-05 | Bộ phát hiện lặp có ngưỡng: `MAX_CONSECUTIVE_REPEATS=6`; token chiếm `>0.35` khi `≥60` từ; cụm 3–10 từ lặp `≥3` lần; đuôi `≥5` từ có prob `<0.05`; `≥4` từ liên tiếp có `<0.05 s/từ` (đồng hồ đứng). | `hallucination.py` |
| M03-F-06 | `trained_with` của Ridge v2: `asr_model="whisper-small"`, `asr_source="corpus pre-norm CTM"`; ghi chú trong artifact: chạy bằng hệ nhận dạng khác sẽ làm lệch `asr_conf_mean`, **đặc trưng có hệ số lớn nhất** theo trị tuyệt đối. Hệ số và khoảng huấn luyện của `asr_conf_mean` ghi trong artifact (`coef`, `feature_lo/hi`); không chép vào repo public vì là thống kê suy ra từ S&I. | `ridge_resp_v2.json` |
| M03-F-07 | HF cache trên máy Sang có `whisper-large-v3-mlx`, `whisper-large-v3-turbo`, `whisper-medium.en-mlx`; **không có `whisper-small`**. | `ls ~/.cache/huggingface/hub` |
| M03-F-08 | Máy dev của Sang: Apple M5, arm64, 24 GiB RAM. `mlx-whisper` 0.4.3 (MIT) đã cài trong môi trường tham chiếu. | `uname -m`, `sysctl`, `pip show` |
| M03-F-09 | Enum tham chiếu đã có `ASR_FAILED`, `ASR_EMPTY_TRANSCRIPT`, `ASR_LOW_CONFIDENCE`, `ASR_HALLUCINATION`, `ASR_VERSION_MISMATCH`. Enum dùng chung của dự án do Thắng phát hành (week-02 mục 2). | `contracts.py`; [week-02](../../../plan/week-02.md) |
| M03-F-10 | M02 Spec v0.1 chưa chốt sample rate (câu hỏi mở "có resample về sample rate cố định không"). Whisper nhận audio 16 kHz mono. | [M02 Spec](../m02-audio-qc/03-specification.md) |

## Inference (suy luận, chưa đo)

- **I-01.** Training dùng CTM do corpus cung cấp, không phải transcript nhóm tự chạy. Dù dùng đúng `whisper-small`, engine/decode khác có thể cho phân phối word probability khác → `asr_conf_mean` lệch mà không vi phạm FR-003. Chỉ đo được bằng smoke trên audio có quyền dùng (đưa vào Test Plan Phase 04, không khẳng định trước).
- **I-02.** `filler_ratio` là hằng 0 trong toàn tập huấn luyện (lý do Ridge v2 bỏ nó). Có thể CTM "pre-norm" không chứa filler, hoặc whisper hiếm khi chép filler. Nếu engine local chép `um/uh`, `n_words`/`ttr` sẽ lệch nhẹ. Chưa đo; ghi làm rủi ro cho M04.
- **I-03.** Máy triển khai đề xuất là VPS Linux; MLX chỉ chạy Apple Silicon, nên nếu dev dùng MLX và deploy dùng CT2 thì hai môi trường có hai phân phối confidence (theo I-01).

## Adaptation Map

| REF-ID | Nguồn | Evidence | Giá trị | Cách áp dụng | Thay đổi bắt buộc | Quyết định |
| --- | --- | --- | --- | --- | --- | --- |
| M03-REF-01 | `whisper_adapter.py` | F-01, F-02 | Adapter hai backend, decode options chống hallucination | Một port `AsrEngine`, adapter local | Model = `whisper-small` (D-001); decode config ghi version | **ADAPT** |
| M03-REF-02 | `whisper_adapter.py` | F-02 | `word_timestamps=True` có ở cả hai engine | Transcript luôn yêu cầu word-level | Không suy word-level khi engine chỉ trả segment | **ADOPT** |
| M03-REF-03 | `whisper_adapter.py` | F-03 | — | — | Thiếu probability → `null`, không phải 0.0 (M04-FR-002) | **REJECT** |
| M03-REF-04 | `hallucination.py` | F-05 | Năm luật đo được, có ngưỡng số | Bộ phát hiện với ngưỡng trong config có version | Ngưỡng giữ nguyên làm giá trị khởi đầu | **ADAPT** |
| M03-REF-05 | `pipeline.py` | F-04 | Ý tưởng kiểm lệch model | So khớp chính xác qua bảng ánh xạ identifier | Bỏ so chuỗi con | **ADAPT** |
| M03-REF-06 | `whisper_adapter.py` | F-01, F-07 | — | — | Không mang model mặc định large-v3-turbo; không tự tải (D-002) | **REJECT** |
| M03-REF-07 | Engine cho `whisper-small` | F-07, F-08, I-03 | Chọn một engine chung dev/deploy | faster-whisper `small` cho mọi môi trường (Option A) | Chạy CPU trên Mac; ghi weight/nguồn/license/SHA-256 khi tải | **ADOPT** — user chốt M03-O-001 ngày 26/09/2026 |
| M03-REF-08 | Sample rate đầu vào | F-10 | Whisper cần 16 kHz mono | M03/M04 yêu cầu DecodedAudio 16 kHz mono | M02 owner (Thắng) xác nhận | **ADAPT** — yêu cầu phía consumer do Sang chốt; xác nhận của Thắng là phụ thuộc liên module, phải có trước Phase 05 |

## Option cho M03-O-001 (engine)

| Option | Chạy trên | Ưu | Nhược |
| --- | --- | --- | --- |
| A. faster-whisper `small` (CTranslate2) cho mọi môi trường | macOS CPU và Linux VPS | Một engine = một phân phối confidence ở dev và deploy (tránh I-03) | Chậm hơn MLX trên Mac; cần tải weight CT2 có chủ đích |
| B. mlx-whisper `whisper-small` ở dev, faster-whisper ở deploy | Mac (MLX) / Linux (CT2) | Nhanh trên máy Sang | Hai engine, hai phân phối confidence; smoke ở dev không đại diện cho deploy |
| C. mlx-whisper cho mọi môi trường | Chỉ Apple Silicon | Nhanh | Không chạy trên VPS Linux |

**Khuyến nghị (Codex role):** Option A — lý do là I-01/I-03: `asr_conf_mean` là đặc trưng nặng ký nhất, nên dev và deploy phải cùng engine. Tên weight cụ thể, nguồn tải, license và SHA-256 được ghi vào evidence khi owner tải có chủ đích (D-002); lúc này **chưa tải, smoke `NOT_RUN`**.

**CODEX CHECK RESULT:** fact/inference/option tách riêng. **User decision (26/09/2026):** M03-O-001 → Option A (faster-whisper `small`); M03-O-002 → giữ yêu cầu 16 kHz mono, chờ Thắng xác nhận phía M02 trước Phase 05.
