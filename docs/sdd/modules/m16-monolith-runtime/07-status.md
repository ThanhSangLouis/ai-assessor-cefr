# M16 — Status

| Mục | Trạng thái |
| --- | --- |
| Lifecycle | proposed |
| Phase | 01 — Requirement review |
| Requirement | DRAFT v0.1 · PENDING |
| Research mode | RUN đề xuất · PENDING |
| Artifacts 02–06 | DRAFT planning packet |
| Implementation | TASK-001–003: SCRUM-65 technical review PASS, Sang/G1 PENDING; TASK-004: SCRUM-67 data-ops code/evidence merged, review pending; TASK-005/006: BLOCKED |
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

## SCRUM-84 / W6-T03 — Đồng bộ với code đã merge (25/10/2026)

Trên `main` `f540cb88643214cd1d4444f2dd0d81f4463119fa`, PR #35 (SCRUM-65, merge `9968abc`) đưa M16-TASK-001–003 vào `main`; evidence SCRUM-65 ghi 358 passed, 2 smoke deselected, changed-file lint/format, clean-wheel/browser và migration/restore checks. PR #50 tiếp tục đổi consent/storage migration và data-operation compatibility; #51/#52 bổ sung task docs/materials. G1/Sang review vẫn `PENDING`; global formatter legacy, ASR/VAD và Windows native có các giới hạn được nêu trong review.

M16-TASK-004 có data-operations code/test trong SCRUM-67 PR #38 (`d60e8a4`); [M14 verification](../m14-billing-licensing/evidence/scrum-67/verification.md) ghi kiểm tra erase/export/retention/restore cùng synthetic fixture. PR #50 cập nhật privacy/migration paths; SCRUM-67 results vẫn gắn historical reviewed SHA, không phải regression mới trên `f540cb8`. TASK-005/006 chưa có final route/package/CI/browser gate trên một revision và vẫn `BLOCKED`. Xem [SCRUM-84 sync evidence](evidence/w6-t03-sync.md). Không chạy test lại và không thay verdict Phase 01–05, G1, user acceptance hay Jira status.

## W7-T01 / SCRUM-98 — Nền kiến trúc ba dịch vụ (25/10/2026)

- Nhánh tích hợp `migrate/w7-repo-goc` tạo từ `main` `5a170db`. PR nền `port/m16-nen-w7` chép phần nền từ `ThanhSangLouis/ai-assessor-cefr@059fa28`; danh sách tệp ở [06-tasks](06-tasks.md#w7--nền-kiến-trúc-ba-dịch-vụ-w7-t01-scrum-98).
- Người làm: Sang; người review và chủ trì kiến trúc: Thắng (SCRUM-98, chấp thuận cấu trúc nền).
- Trên riêng nhánh tích hợp, test chưa chạy được cho tới khi mọi module đã chuyển (kho MongoDB `storage/migrations.py` và `services/core/app.py` cần kho và dịch vụ của cả ba người). Kết quả kiểm bằng cách phủ tạm phần còn thiếu từ repo gốc ghi trong mô tả PR.

## SCRUM-103 middleware integration support (2026-10-28)

- M16's `api/middleware.py` is present on the SCRUM-103 branch from source revision `0853c95`, after explicit project-owner scope expansion.
- The generic 500 fallback now receives the same security and API cache headers as normal responses. Five focused middleware tests, Ruff and compilation pass.
- The M16 task lifecycle and verdicts are unchanged. M16 owner review remains pending; see [integration evidence](evidence/scrum-103-middleware-integration.md).
