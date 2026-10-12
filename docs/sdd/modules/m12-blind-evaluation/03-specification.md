# M12 — Specification

**Version:** v0.1 · **STATUS:** DRAFT.

## Model và lifecycle

- `RatingBatch(DRAFT|OPEN|CLOSED, seed, criteria_version)`.
- `RatingAssignment(OPEN|SUBMITTED|VOID, blind_token, ordinal, rater_id_hash, response_id internal)`.
- `ResearchRating` immutable; `Adjudication` immutable.
- `MachineSeen(response_id, actor_id, seen_at, source)` và audit append-only.

Batch: create → open → close; reopen nếu được cho phép phải không khôi phục sheet đã void. Assignment only eligible khi consent vẫn active và rater chưa machine-seen.

## Authorization/privacy

Public blind identifier là opaque token không suy ra response/account. `BlindAccessPolicy` được gọi trước mọi route có thể lộ machine result. Rater chỉ đọc assignment của mình; admin tổ chức batch nhưng nếu cũng là rater thì screen machine data của response đang nợ vẫn bị che.

## Submission

Server validate half-step 0..6, allowed band, five criteria, bounded rationale hoặc allowed unrateable reason. Unique assignment rating + transaction/CAS bảo đảm one-time submit. Adjudication assignment chỉ tạo một lần.

## Reporting

Analysis snapshot query re-check active consent. Output: human-human metric trước machine-human, sample counts, bootstrap seed/unit=speaker, confidence intervals hoặc explicit insufficient. CSV participant/rater pseudonyms không map ngược trong export.

## APIs/UI

`/api/v1/rating/assignments`, `/assignments/{token}`, `/submit`; admin batch/create/status/replace/adjudicate/report/export. Blind response không trả alias, internal response ID, report, machine score/band/reason/provenance hoặc other-rater value.
