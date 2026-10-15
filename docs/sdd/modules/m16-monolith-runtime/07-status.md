# M16 — Status

| Mục | Trạng thái |
| --- | --- |
| Lifecycle | proposed |
| Phase | 01 — Requirement review |
| Requirement | DRAFT v0.1 · PENDING |
| Research mode | RUN đề xuất · PENDING |
| Artifacts 02–06 | DRAFT planning packet |
| Implementation | SCRUM-65 technical review PASS; còn chờ Sang/G1; các task M16 khác chưa triển khai |
| Baselines | target `3b2d2b7`; reference `40907cc`; D043 excluded |
| Prompt | SCRUM-65 migrations/jobs/integration A1 — Luna, theo direct user authority |

M16 là integration gate, không thay acceptance từng module. Full PASS trên runtime không tự nghiệm thu behavior module nếu AC local chưa có evidence.

## Hồ sơ G0/G2 ngày 15/10/2026

- [G0 evidence](evidence/w5-g0-2026-10-15/W5-G0.md): kiểm tra baseline và backup/restore đã chạy; reviewer PENDING, format FAIL được ghi rõ.
- [G2 contract](W5-G2-migration-rollback.md): DRAFT/IN_REVIEW, forward migration W5 chưa chạy.
- [Sáu task readiness và gói Phase 01](W5-task-readiness.md): Requirement M11/M14/M16 chờ user verdict; Research RUN là đề xuất.
- Baseline giữ 3b2d2b7; local branch feat/W5-product-parity-baseline được chuẩn bị, bảo toàn nhánh remote cũ. Chưa implementation, không ghi approval hoặc DONE thay reviewer.

## SCRUM-65 — Implementation theo chỉ dẫn trực tiếp ngày 15/10/2026

- Actual branch base 9968abc; historical target 3b2d2b7 và reference 40907cc giữ để traceability.
- Người dùng chỉ định Luna implement, Codex prompt/review; [authority](evidence/scrum-65/authority.md), [task contract](evidence/scrum-65/contract.md), [prompt log](prompts/SCRUM-65-prompt-log.md).
- G0/G2 Done theo Jira đọc thực tế; PR35 đã merge. G1 To Do, Sang review/acceptance PENDING. Không suy ra approval toàn M16 hoặc đổi verdict module khác.
- W5-T01.1 baseline actual branch: 323 passed, 2 smoke deselected; backup SQLite v4/11 tables/4 blobs giữ ngoài Git. W5-T01.2–T01.6 IN_PROGRESS theo direct task authority, chưa có final PASS.

### SCRUM-65 final verification

- Code/tests reviewed: 61a5353 (implementation 514fb02). [Review/evidence](evidence/scrum-65/review.md).
- Full non-smoke: 358 passed, 0 failed/skip, 2 smoke deselected; combined/line/branch coverage đều không regression. Lint/changed-file format, clean-wheel real CLI/HTTP, browser 11 checks, v4→v9 preserve/restore và D043 scan PASS.
- Global formatter còn 23 legacy files ngoài scope; ASR/VAD audio inference NOT_RUN; Windows native NOT_RUN. Sang/user verdict PENDING, Jira không tự đổi Done, G1 To Do theo lần đọc cuối.
