# M10 — Plan

**Version:** v0.1 · **STATUS:** DRAFT.

## Package và ownership

- Sang: `src/aicefr/practice/`, `lessons/`, rule/catalogue/service và unit/integration tests.
- Thắng: migrations/repository interfaces/composition wiring trong W5-T01.
- Nguyên: practice/lesson/progress/authoring UI trong W5-N02/N03.

## Build order

1. Freeze enums/domain payload and database keys.
2. Add migrations/repositories with file-SQLite tests.
3. Add mission/step rule engines and no-score branch.
4. Add authoring/version/seed and review scheduling.
5. Add achievement/streak and export/erasure hooks.
6. Freeze API payload; implement student then teacher UI.
7. Run browser, migration, regression and wheel packaging.

## Schema groups

`practice_mission`, `learning_path`, `learning_unit`, `lesson`, `lesson_version`, `lesson_step`, `lesson_media`, `step_attempt`, `review_item`, `achievement`, `learning_meta`. Foreign keys, owner indexes, unique seed/version keys và CAS revision bắt buộc.

## Rollback

Migration chỉ thêm; rollback phục hồi SQLite/blob backup. Feature route có thể tắt nếu migration/readiness fail nhưng dữ liệu attempt/version không bị xóa. Seed upgrade có dry-run summary.
