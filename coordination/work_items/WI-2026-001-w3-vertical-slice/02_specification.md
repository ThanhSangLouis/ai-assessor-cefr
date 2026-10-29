# WI-2026-001 W3 vertical slice - Specification

| Field | Value |
| --- | --- |
| `work_id` | `WI-2026-001-w3-vertical-slice` |
| `version` | `V2` |
| `status` | `DRAFT_V2` |
| `approval_ref` | `null` |

Nguồn đặc tả: `markdown/week_03/01_vertical_slice_draft_spec.md` và `markdown/week_02/04_ai_pedagogical_candidate_package.md`.

## Expected behavior

Một caller truyền `ProcessingRequest` hợp lệ qua interface `ResponseProcessor.process` và nhận `ProcessingReport` typed. Implementation xử lý QC/ASR/features/provenance/cleanup. Mọi failure được biểu diễn bằng status + reason code; không tạo score mặc định.

## Invariants

- Không PII/audio/transcript trong log.
- Không sửa hoặc xóa raw input.
- Không criterion/overall CEFR score trong work item.
- Monologue không tạo Interaction score.
- `teacher_verified=false` và không có audit giả.
- Artifact/ref/version/hash đầy đủ theo trạng thái.
- Cùng fixture/config/fake adapters cho output deterministic.

## Compatibility

Greenfield; không migration. Các schema là candidate cho V3 và phải đồng bộ reason-code source duy nhất trước implement.

## Candidate operational configuration

- Python `>=3.11,<3.14`; direct dependencies theo `04_research.md` và chỉ được thêm sau V3 approval.
- Upload tối đa 25 MiB; duration tối đa 300 giây; dưới 15 giây là `REVIEW_REQUIRED` candidate.
- Working PCM 16 kHz mono; raw input immutable.
- Silence ratio từ 0.80 và clipping ratio từ 0.01 là review flags candidate, không phải band threshold.
- `faster-whisper` là optional adapter; default test không tải model. Adapter chỉ nhận local model directory và chặn implicit remote download.

## Open items blocking V3

- G1/G2 quyết định nào được phép đưa vào schema mà không khóa scoring.
- Exact allowed-file list và command khi nâng package lên V3.
- Approved local model/storage path policy cho optional ASR smoke; có thể để ngoài V3 đầu nếu chưa duyệt.
