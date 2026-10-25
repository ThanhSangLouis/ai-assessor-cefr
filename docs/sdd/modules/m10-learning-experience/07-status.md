# M10 — Status

| Mục | Trạng thái |
| --- | --- |
| Lifecycle | proposed |
| Phase hiện tại | 01 — Requirement review |
| Requirement | v0.1 DRAFT · PENDING |
| Research mode | RUN đề xuất · PENDING |
| Artifacts 02–06 | planning packet v0.1 DRAFT; chưa có hiệu lực phase |
| Implementation | CODE_MERGED trên `main` (PR #41, #42, theo chỉ dẫn trực tiếp của user; đồng bộ 21/10/2026) · review/acceptance PENDING |
| Prompt | NONE ISSUED |

Task chỉ được chuyển khỏi `BLOCKED/TODO` sau approval tuần tự Phase 01, 03, 04, 05 và dependency contract tương ứng đã freeze.

## SCRUM-70 task-local implementation — 15/10/2026

User chỉ định thực thi S02 sau S01, với Luna implement/root review và PR riêng. Actual base51eff1f; [authority](evidence/scrum-70/authority.md) và prompt lưu trước dispatch. Task-local implementation IN_PROGRESS; global phase và user/reviewer acceptance vẫn PENDING, không tự đổi approval hoặc JiraDone.

### SCRUM-70 verification package

Final source/test e792ae6; full889PASS, pure coverage96,091%statement/88,821%branch; clean wheel129/129bytes và browser API handoff107/107PASS. [Final verification](evidence/scrum-70/final-verification.md), [review](reviews/SCRUM-70-review.md). Task-local implementation READY_FOR_REVIEW; reviewer/user acceptance vẫn PENDING, không đổi global DRAFT. Tạo PR riêng rồi dừng; chưa thực thi SCRUM-71/72.

PR đã tạo: [#41 — SCRUM-70](https://github.com/thanglb2005/ai-assessor-cefr/pull/41), base nhánh G1. Dừng tại đây sau kiểm tra publication/CI; không bắt đầu S03/S04. Jira/reviewer acceptance PENDING.

## Đồng bộ W6-S02 / SCRUM-79 — 21/10/2026

Code của module đã merge vào `main` qua PR #41 (SCRUM-70, merge `425bb4f`), #42 (SCRUM-71, merge `3a0dba1`) theo chỉ dẫn trực tiếp của user, trong khi verdict Phase 01–05 vẫn PENDING. Bảng task đã cập nhật trạng thái code ([06-tasks](06-tasks.md)); chạy lại test trên `main` `cabcc44`: 121 passed ([bằng chứng](evidence/w6-s02-sync.md)). Lần đồng bộ này không đổi phase, không ghi APPROVED/DONE; review, verification và acceptance chờ reviewer/user.

## W7-S03 — Chuyển M10 sang kiến trúc ba dịch vụ (25/10/2026)

- PR `port/m10-m12-m13-hoc-tap` vào `migrate/w7-repo-goc`, xếp trên `port/m03-m05-m09-cham` (W7-S02). Người làm: Sang. Chưa có verdict.
- Kết quả test ghi trong mô tả PR. Lý do: trên riêng nhánh tích hợp, test chưa chạy được cho tới khi mọi module đã chuyển, nên kết quả được đo bằng cách phủ tạm phần của người khác từ repo gốc.
