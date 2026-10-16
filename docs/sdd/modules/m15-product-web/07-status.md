# M15 — Status

| Mục | Trạng thái |
| --- | --- |
| Lifecycle | in_progress |
| Phase | Phase 05 — [Plan v0.2](05-plan.md) + [Tasks v0.2](06-tasks.md) `APPROVED` ngày 2026-10-16 theo xác nhận của chủ dự án rằng các contract/file gates đã được duyệt trong cuộc họp miệng; xem [review Phase 05 A1](reviews/phase-05-review-w5-n01-a1-2026-10-16.md) và addendum verdict. |
| Requirement | v0.2 · APPROVED Phase 01, 2026-10-16 |
| Research mode | `RUN` · chủ dự án chọn 2026-10-16 |
| Research | v0.2 reviewed with Phase 03; package accepted with Phase 03 verdict |
| Specification | v0.2 · APPROVED Phase 03, 2026-10-16 |
| Test Plan | v0.2 · APPROVED Phase 04, 2026-10-16 |
| Plan/Tasks | v0.2 · APPROVED Phase 05, 2026-10-16; oral-meeting approval reported by project owner |
| Implementation | IN_PROGRESS — M15-TASK-001–006 and M11-TASK-006/M13-TASK-005; integrated acceptance NOT_RUN |
| Prompt | NONE ISSUED |

W5-N01 đang được triển khai trong worktree sạch từ `main`, base `d60e8a4b9f63a0b0259ada8971e23bafdb1df041`. Chủ dự án đã duyệt Requirement v0.2 (Phase 01), Research v0.2 + Specification v0.2 (Phase 03), Test Plan v0.2 (Phase 04), giữ full scope và xác nhận các contract/file gates đã được duyệt trong cuộc họp miệng; Phase 05 được `APPROVED` ngày 2026-10-16. Research dùng `RUN`, accessibility theo tiêu chí hành vi không claim mức chuẩn, native HTML/CSS/small JS cùng routes `/`, `/bands`, `/student/account?tab=...`. M08 sở hữu identity/consent/owner boundary; teacher-verified state thuộc M06/M07 theo mapping đã xác nhận. Source work cho các task consumer N01 đang `IN_PROGRESS`; không task nào `DONE` khi acceptance chưa được chạy.

Implementation hiện có design system/public pages, account consumer, assessment input/status/report/history/audio và student progress disclosure. M13 producer chưa có student payload route/service trong runtime, vì vậy trang thể hiện trạng thái không có payload và không suy diễn số liệu. CI run [38869992938](https://github.com/thanglb2005/ai-assessor-cefr/actions/runs/38869992938) của PR #44 pass unit+coverage, Ruff, Markdown guard và kiểm tra file bị cấm; task-level acceptance, browser QA và clean-wheel vẫn `NOT_RUN`, chưa task nào `DONE`. M15-TASK-007/W5-T04 giữ quyền package/browser gate.

W5-N01 đang ở PR [#44](https://github.com/thanglb2005/ai-assessor-cefr/pull/44), đã rebase lên `main` sau khi PR #39 được merge; CI cần chạy lại trên head mới. SCRUM-74/#45, SCRUM-75/#46 và SCRUM-76/#47 đang được tích hợp tuần tự. Chủ dự án xác nhận Phase 05 cho cả ba task và cho phép port/adapt UI trong phạm vi; các giới hạn API được ghi tại hồ sơ chuyển giao từng task. E2E tổng hợp `NOT_RUN`, được chạy đúng một lần sau khi các nhánh đã tích hợp.
