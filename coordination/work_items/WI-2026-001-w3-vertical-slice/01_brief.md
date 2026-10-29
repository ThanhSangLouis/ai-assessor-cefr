# WI-2026-001 W3 vertical slice - Brief

| Field | Value |
| --- | --- |
| `work_id` | `WI-2026-001-w3-vertical-slice` |
| `version` | `V2` |
| `status` | `DRAFT_V2` |
| `request_ref` | Yêu cầu người dùng ngày 12/09/2026: tiếp tục các phần chưa làm của tuần 1-3 |
| `approval_ref` | `null` |
| `planning_baseline` | `c0ddd8acd79836fd55badad01ec70b4ae0ebfe7b` |
| `owner_spec_review` | `Codex` |
| `implementer` | `Antigravity` sau V3 approval/prompt lock |

## Problem

Repo chưa có codebase chạy xuyên suốt. Roadmap W3 yêu cầu audio đi tới report, nhưng W1/G1 và W2/G2 chưa khóa scoring construct, task/schema hoặc dữ liệu.

## Outcome

Tạo vertical slice local, typed và testable cho audio synthetic/non-sensitive: ingest → QC → ASR adapter → features cơ bản → technical report. Không chấm CEFR.

## In scope

- Module `ResponseProcessor` và typed contracts.
- Fake adapters/test fixtures deterministic.
- Local adapters cho audio/ASR ở mức được V3 duyệt.
- Safe logging, provenance, reason codes và documentation.

## Out of scope

- CEFR score/feedback, Task C Interaction inference, dữ liệu thật, corpus download, cloud/external API và production deployment.

## Constraints

- G1/G2 vẫn là human gate; package này không thay approval.
- Không implement trước `APPROVE WI-2026-001-w3-vertical-slice V3` và prompt lock.
- Unit/integration mặc định offline, deterministic và không tải model.
