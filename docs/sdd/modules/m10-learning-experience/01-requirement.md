# M10 — Practice, Lessons, Achievements — Requirement

**SCOPE ID:** M10 · **TYPE:** module · **OWNER:** Sang
**SCOPE ROOT:** `docs/sdd/modules/m10-learning-experience/`
**LIFECYCLE:** proposed · **VERSION:** v0.1 · **STATUS:** DRAFT
**RELATED SCOPES:** M01, M02–M06, M08, M13, M15, M16
**RESEARCH MODE:** `RUN` đề xuất — đối chiếu D023, D025–D027, D032 tại Sang `40907cc`.
**USER VERDICT:** PENDING

## Mục tiêu

Cho sinh viên luyện nói theo nhiệm vụ và lộ trình có bằng chứng, nhận gợi ý/ôn tập/thành tựu theo công sức nhưng tuyệt đối không biến bài luyện thành bài chấm CEFR.

## Functional Requirements

- **M10-FR-001:** ngân hàng 15 nhiệm vụ, 5 tiêu chí × A2/B1/B2, mục tiêu đo bằng luật và versioned seed.
- **M10-FR-002:** practice pipeline có `purpose=PRACTICE`, không scorer/band/teacher queue/assessment metric/research export.
- **M10-FR-003:** recommendation từ tiêu chí yếu nhất + band gần nhất, fallback A2 minh bạch.
- **M10-FR-004:** hierarchy Path → Unit → Lesson → immutable PublishedVersion → Step; seed 18 unit/31 lesson idempotent.
- **M10-FR-005:** bốn bậc Mẫu → Có kiểm soát → Có hướng dẫn → Tự do; chín step type, rule/evidence, practice QC tối thiểu 1 giây.
- **M10-FR-006:** teacher authoring draft/reorder/lint/media/preview/publish/import/export; student không sửa.
- **M10-FR-007:** spaced review 1/3/7 ngày theo Asia/Ho_Chi_Minh; đúng/sai chuyển hộp deterministic.
- **M10-FR-008:** teacher insight/override có audit, không score và không chặn người học.
- **M10-FR-009:** 17 achievement theo effort, seen state, không thu hồi; streak có một ngày nghỉ/tuần và so sánh 7 ngày.
- **M10-FR-010:** owner access, personal export/erasure và deletion của attempt/media đúng policy.

## Acceptance Criteria

- **M10-AC-001:** đủ 15 mission, không lẫn danh sách assessment; seed cùng version không sửa dữ liệu, version mới update đúng phần seed.
- **M10-AC-002:** practice/lesson result không có overall score, band hoặc teacher_verified và không xuất hiện ở queue/export mặc định.
- **M10-AC-003:** recommendation có `reason_code`/explanation và deterministic với cùng history.
- **M10-AC-004:** draft không ảnh hưởng student; publish tạo version mới; attempt giữ `lesson_version` và `rules_version`.
- **M10-AC-005:** alignment/lemma/silence/multi-round xử lý đúng, ASR không nhận transcript mẫu làm prompt.
- **M10-AC-006:** review item đi 1→3→7 ngày hoặc về 1 ngày, tính theo giờ Việt Nam.
- **M10-AC-007:** achievement không đọc score/band/người khác; unlock idempotent, seen chỉ bởi owner và không thu hồi sau deletion.
- **M10-AC-008:** student hoàn thành một lesson và một review item trên desktop/mobile; mọi loading/empty/error/retry state dùng được.

## Out of scope

Leaderboard, XP, paywall học tập, nội dung sinh bởi LLM, social feed, CEFR score từ practice, automatic curriculum claim chưa có nghiên cứu.

## Quyết định cần duyệt

Seed catalogue 18/31; QC practice tối thiểu 1 giây; `simplemma` là dependency runtime; achievement catalogue 17 mục; Research mode RUN.
