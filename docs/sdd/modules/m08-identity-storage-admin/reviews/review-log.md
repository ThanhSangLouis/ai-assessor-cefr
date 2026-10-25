# M08 — Review Records

**Hiện trạng:** Codex đã review diff SCRUM-48/49 và integration; Nguyên và user review còn pending.

| Review ID | Prompt ID / Task ID | Base/Head revision | Diff/evidence đã kiểm tra | Finding và resolution | User verdict |
| --- | --- | --- | --- | --- | --- |
| M08-RV-049 | M08-EXEC-049 / M08-TASK-002 | 2f6a9cb → branch worktree | contracts/storage/test diff; M08-EV-049 | No blocker in scoped diff; Nguyên schema review PENDING | PENDING |
| M08-RV-048 | M08-EXEC-048 / M08-TASK-001 | 55d8952 → branch worktree | contracts/auth/test diff; M08-EV-048 | No blocker in scoped diff; Nguyên schema review PENDING | PENDING |
| M08-RV-SCRUM-87 | Direct Codex / SCRUM-87 | dfb186e → task branch | Consent contract, migration 12, WSGI/upload gate, printable form, focused tests; [evidence](../evidence/scrum-87-implementation.md) | Independent review found stale v1 research consent could preselect broader v2 scope; fixed by clearing both choices for stale versions and adding a regression test. Migration default-deny and withdrawal event assertions added. PDF/web copy manually verified. Retention policy remains proposed; no real-data collection claim. | PENDING |

Codex lưu Phase 07 review record tại đây sau khi kiểm tra actual diff, test và evidence. Phase 08 final verification nằm trong evidence/ trên final revision. Chỉ người dùng ghi verdict phê duyệt.
