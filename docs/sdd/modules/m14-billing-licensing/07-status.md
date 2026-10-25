# M14 — Status

| Mục | Trạng thái |
| --- | --- |
| Global lifecycle/Requirement | proposed · DRAFT v0.1 · PENDING |
| Global artifacts 02–06 | DRAFT planning packet; không tự phê duyệt |
| Local task authority | User giao SCRUM-67, Luna implement/Codex review, tạo PR |
| Local phase | Implementation review SCRUM-67; final local verification hoàn tất |
| Implementation | SCRUM-67 TASK-001–004 merged in PR #38; task table is IN_REVIEW, while historical verification recommends READY_FOR_REVIEW; TASK-005 billing UI is read-only/partial; TASK-006 final integration BLOCKED |
| User/Sang/Nguyên acceptance | PENDING |
| External/live payment authority | KHÔNG CÓ; W5 hard-off |
| Prompt | [Ba lane A1 và prompt log](prompts/SCRUM-67-prompt-log.md) |
| Baseline/authority | [Record](evidence/scrum-67/authority.md) |
| Review/finding/design | [Review record](evidence/scrum-67/review-record.md) |
| Billing evidence | [Core](evidence/scrum-67/billing-core-report.md), [gateway/license](evidence/scrum-67/LANE-report.md) |
| Data/API handoff | [Data report](evidence/scrum-67/data-api-report.md), [API](evidence/scrum-67/data-api-contract.md), [UI handoff](evidence/scrum-67/ui-handoff.md) |

Historical target `3b2d2b7`; Sang `40907cc`; actual base `bab5f25` gồm T01 main và T02 `754ee9a`. Migration v10 cộng thêm để erasure có guard, không sửa checksum v5–v9. Task chưa được đặt Verified/DONE; record kỹ thuật và PR không thay verdict của reviewer/user.

Final reviewed code `5c6397ffaf804a3cb08c17aef1017fa3884737ca`; [Verification](evidence/scrum-67/verification.md). Docs/log commit phía sau không đổi source. Global phase/user acceptance vẫn PENDING.

## SCRUM-84 / W6-T03 — Đồng bộ với code đã merge (25/10/2026)

Trên `main` `82fe708af80f0b50eb540c65b5c583f64868d2c8`, PR #38 (SCRUM-67, merge `d60e8a4`) chứa implementation backend M14-TASK-001–004 và data-operations handoff. Verification lịch sử gắn final reviewed code `5c6397f`, ghi 600 passed, clean-wheel/browser và giới hạn riêng cho global format, Windows native, model inference, live payment. Không chạy lại test trong lượt đồng bộ này.

PR #47 (SCRUM-76, merge `cabcc44`) có billing overview/order read surfaces; không chứng minh billing UI mutation/receipt journey hoàn chỉnh. Mapping chi tiết nằm trong [SCRUM-84 sync evidence](evidence/w6-t03-sync.md). TASK-005 giữ `BLOCKED`, TASK-006 giữ `BLOCKED`; global Phase 01–05 và user/Sang/Nguyên acceptance vẫn `DRAFT/PENDING`/`PENDING`.
