# Xây dựng hệ thống AI hỗ trợ đánh giá năng lực nói tiếng Anh theo CEFR cho sinh viên đại học Việt Nam ở trình độ A2-B2

## 01. Đặc tả draft vertical slice W3

| Thuộc tính | Giá trị |
| --- | --- |
| Trạng thái | DRAFT_V2 - NOT APPROVED FOR IMPLEMENTATION |
| Work item | `WI-2026-001-w3-vertical-slice` |
| Ngày | 12/09/2026 |

## 1. Outcome

Một request audio synthetic/non-sensitive đi qua ingest → QC → ASR adapter → basic features → report kỹ thuật mà không thao tác tay, không lộ danh tính và không tạo điểm CEFR giả.

## 2. Thiết kế module sâu

External seam của vertical slice là module `ResponseProcessor`. Caller và test chỉ cần học một interface:

```python
class ResponseProcessor(Protocol):
    def process(self, request: ProcessingRequest) -> ProcessingReport: ...
```

Interface bao gồm typed request/result, invariant, error mode và performance metadata. Implementation che giấu audio probing, normalization workspace, QC, ASR, feature extraction, artifact hashing và cleanup. Nếu xóa module này, toàn bộ complexity sẽ tràn lại vào HTTP/CLI/test callers; vì vậy seam tạo leverage và locality.

Các dependency thật sự thay đổi được đặt ở internal seam:

- `AudioDecoder`: FFmpeg adapter khi chạy local và deterministic fake adapter trong test.
- `AsrEngine`: faster-whisper adapter khi chạy smoke local và fake adapter trong test.
- `ArtifactStore`: local filesystem adapter và temporary in-memory/local adapter trong test.

Không đưa từng extractor nhỏ ra external interface. Pure QC/feature calculation nằm trong implementation và test chủ yếu đi qua interface `ResponseProcessor`.

## 3. Typed contracts candidate

### `ProcessingRequest`

| Field | Kiểu | Quy tắc |
| --- | --- | --- |
| `response_id` | string | Pseudonymous stable ID |
| `speaker_id` | string | Pseudonymous; không chứa MSSV/tên/email |
| `task_id` | string | Ref task/prompt đã version |
| `audio_ref` | string | Local approved reference; không phải remote URL |
| `prompt_version` | string | Bắt buộc |
| `pipeline_config_version` | string | Bắt buộc |
| `task_mode` | enum | `MONOLOGUE/INTERACTION` |

### `ProcessingReport`

| Field | Quy tắc |
| --- | --- |
| Identifiers | `response_id`, `task_id`; không trả direct identity |
| Status | `COMPLETED/REVIEW_REQUIRED/REJECTED/FAILED` |
| Provenance | audio hash, pipeline/ASR/feature version và run ID |
| QC | measured technical values, flags và reason codes |
| ASR | artifact ref, timestamps availability, engine/model/config version; không ghi transcript vào log |
| Features | versioned values + validity status; invalid feature là null có reason code |
| Interaction | Chỉ technical turn/timing evidence nếu có; không có CEFR score |
| Scoring | Cố định `not_scored_vertical_slice`; không có band/confidence giả |
| Verification | `teacher_verified=false`, `review_audit_ref=null` |

## 4. Error behavior

- Unsupported/corrupt audio: `REJECTED` + `AUDIO_UNSUPPORTED`; không gọi ASR.
- Quá ngắn/đa số silence/clipping nghiêm trọng: `REVIEW_REQUIRED` hoặc `REJECTED` theo config candidate; không tạo feature thiếu hợp lệ.
- ASR adapter fail: `FAILED` hoặc `REVIEW_REQUIRED` + `ASR_FAILED`; không tạo transcript rỗng rồi tiếp tục như thành công.
- Missing version/provenance: request validation fail với reason code; không default âm thầm.
- Internal exception: map sang safe error chứa run ID/reason code, không chứa path nhạy cảm/transcript.

Threshold QC là config versioned candidate và không được gọi là ngưỡng đã validation. Giá trị candidate cùng dependency research nằm tại [work item research](../../coordination/work_items/WI-2026-001-w3-vertical-slice/04_research.md); pilot có thể thay bằng version mới.

## 5. HTTP/CLI adapters candidate

- HTTP adapter mỏng nhận upload/local session ref, validate transport và gọi `ResponseProcessor.process`.
- CLI adapter dùng cùng interface cho fixture smoke.
- Business rules không lặp lại trong HTTP/CLI.
- Endpoint scoring/teacher review nằm ngoài work item đầu tiên.

## 6. Test surface

Test qua `ResponseProcessor` với fake adapters:

- happy path trả report typed, deterministic và đủ version/hash;
- corrupt/short/silence/clipping trả status/reason code đúng;
- ASR failure không bị nuốt;
- transcript/audio/PII không xuất hiện trong log;
- monologue không có Interaction score;
- `teacher_verified` luôn false;
- cùng config/fixture cho cùng output phần deterministic;
- temporary artifacts được cleanup, raw input không bị sửa.

Một smoke test riêng có thể dùng FFmpeg/faster-whisper local khi dependency/model đã được duyệt và có marker; không chạy mặc định, không cần internet.

## 7. Ngoài phạm vi

- CEFR scoring, calibration, feedback hoặc LLM.
- UI hoàn chỉnh, authentication production và cloud deployment.
- Collection/consent workflow người thật.
- Download L2-ARCTIC/Speak & Improve/model lớn.
- Database migration production.
- Task C scoring hoặc inference Interaction.

## 8. Quyết định còn mở trước V3

- Artifact storage config và retention cho synthetic/dev data.
- Exact Pydantic schema và reason-code enum đồng bộ W2.
- Mức smoke integration được phép và model cache location.
