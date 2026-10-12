# M10 — Specification

**Version:** v0.1 · **STATUS:** DRAFT.

## Domain model

- `PracticeMission(id, criterion, band, kind, prompt, goals, prompt_version)`.
- `LearningPath > Unit > Lesson > LessonVersion > Step`; published version immutable.
- `StepAttempt(id, owner_id, lesson_version, step_id, rules_version, status, measurements, evidence, teacher_override)`.
- `ReviewItem(owner_id, source_attempt, content_key, box, due_date, status)`.
- `Achievement(owner_id, code, unlocked_at, seen_at)`; facts không có score/band.

`MissionKind` gồm bảy loại rule đã khóa trong catalogue; `StepType` gồm read aloud, listen-repeat, retell, gap, keywords, sentence frame, picture bank, outline, free multi-round.

## Data flow

1. Student chọn mission/lesson version được publish.
2. Server kiểm owner/consent, lưu audio immutable và tạo attempt `QUEUED` với purpose learning.
3. Worker dùng QC practice → VAD → ASR; không gọi scorer.
4. Rule engine tạo measurement/evidence/reason; repository cập nhật attempt idempotently.
5. Progress service cập nhật lesson completion, review items, streak facts và achievement unlock trong transaction.
6. UI đọc result; teacher override tạo audit và result revision mới nhưng không đổi dữ liệu raw.

## API contract

- Student: `GET /api/v1/practice`, `/missions/{id}`, `/attempts/{id}`; `GET /api/v1/learn/path`, `/lessons/{id}`, `/reviews/due`; `POST` attempt/review/seen/delete.
- Teacher/admin: CRUD draft path/unit/lesson/step, reorder, lint, preview, media, publish, import/export, insights và override.
- Foreign resource trả 404; role sai 403; stale version/reorder conflict 409; invalid lesson/lint 422.

## Validation và invariants

- Published content không update/delete tại chỗ; republish tạo version.
- Completion cần threshold bước và đã làm free step.
- Từ ngoài VAD không đếm; missed/unsure/pass phân biệt; no speech là unmeasured, không “failed”.
- Seed dùng stable natural key + seed version, không chạm teacher-created/edited entity.
- Delete attempt dọn owned blob/result/review link theo policy nhưng không thu hồi achievement đã unlock.

## UI states

Roadmap có locked-looking visual nhưng không khóa bằng paywall; lesson player có step rail, recorder, result/retry/continue; review page có batch progress; result luôn gắn nhãn luyện tập và cấm band. Mobile sticky action không che content/focus.
