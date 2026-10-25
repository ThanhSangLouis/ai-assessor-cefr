# M11 — Status

| Mục | Trạng thái |
| --- | --- |
| Lifecycle | proposed |
| Phase | 01 — Requirement review |
| Requirement | v0.1 DRAFT · user PENDING |
| Research mode | RUN đề xuất · PENDING |
| Artifacts 02–06 | v0.1 DRAFT planning packet |
| Implementation | Backend M11-TASK-001–005 merged and IN_REVIEW; consumer UI M11-TASK-006/007 appears in PR #44/#47 and remains IN_REVIEW; M11-TASK-008 BLOCKED |
| Prompt | NONE ISSUED |

M11 không thay verdict lịch sử M08. Dependency hoặc impact sang M08 chỉ được cập nhật sau khi user duyệt scope và compatibility plan.

## SCRUM-66 — Backend task verification 15/10/2026

Theo [quyền giao task trực tiếp](evidence/scrum-66/authority.md), backend T02 đã implement và được Codex kiểm độc lập: 425 test PASS; pure auth services đạt target coverage; clean-wheel/browser PASS. Xem [review](evidence/scrum-66/review.md), [prompt log](prompts/SCRUM-66-prompt-log.md).

Trạng thái task: READY FOR REVIEW. Bảng DRAFT/PENDING phía trên là trạng thái approval module gốc, không bị tự đổi thành APPROVED. N01/N04 UI và review Nguyên/Sang còn PENDING; không tự đóng Jira.

## SCRUM-84 / W6-T03 — Đồng bộ với code đã merge (25/10/2026)

Đối chiếu trên `main` `f540cb88643214cd1d4444f2dd0d81f4463119fa`. PR #36 (SCRUM-65, merge `840efb9`) và PR #37 (SCRUM-66, merge `febf7f9`) đưa backend M11-TASK-001–005 vào `main`; evidence SCRUM-66 ghi 425 passed cùng lint/changed-file format/clean-wheel/browser checks. PR #50 (SCRUM-87, merge `bfd1206`, code `ff6d36e`) bổ sung `consent-v2`, migration consent và lựa chọn lưu audio riêng; task-local UI/API evidence nằm ở [SCRUM-87 implementation](evidence/scrum-87-implementation.md). Jira SCRUM-87 vẫn `Testing`; việc merge không thay review/acceptance module. Consumer code có trong PR #44 (SCRUM-73, merge `0fc428a`) và PR #47 (SCRUM-76, merge `cabcc44`); browser report chỉ xác nhận supported route/role journeys, không thay thế review đầy đủ M11-TEST-009 hoặc owner acceptance.

Mapping, revision lịch sử và giới hạn được ghi tại [SCRUM-84 sync evidence](evidence/w6-t03-sync.md). Không chạy lại test trong lượt đồng bộ tài liệu này. Global Phase 01–05 vẫn `DRAFT/PENDING`; live OAuth `NOT_RUN`; M11-TASK-008 và nghiệm thu owner vẫn mở.
