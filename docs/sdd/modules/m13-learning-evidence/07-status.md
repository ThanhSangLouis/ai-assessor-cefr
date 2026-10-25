# M13 — Status

| Mục | Trạng thái |
| --- | --- |
| Lifecycle | proposed |
| Phase | 01 — Requirement review |
| Requirement | DRAFT v0.1 · PENDING |
| Research mode | RUN đề xuất · PENDING |
| Artifacts 02–06 | DRAFT planning packet |
| Implementation | CODE_MERGED trên `main` (PR #42, #43, đồng bộ 21/10/2026); SCRUM-88 local trên branch `feat/SCRUM-88-W6-N03-De-bai-rubric-cham-ke-hoach-thu` @ `6de3206` · review/acceptance PENDING |
| Prompt | NONE ISSUED |

M13 chỉ có thể tuyên bố implementation/test correctness; kết luận thực nghiệm người học vẫn `NOT_EVALUATED` nếu chưa có dữ liệu/protocol/evidence được phép.

## Đồng bộ W6-S02 / SCRUM-79 — 21/10/2026

Code của module đã merge vào `main` qua PR #42 (SCRUM-71, merge `3a0dba1`), #43 (SCRUM-72, merge `36ab740`) theo chỉ dẫn trực tiếp của user, trong khi verdict Phase 01–05 vẫn PENDING. Bảng task đã cập nhật trạng thái code ([06-tasks](06-tasks.md)); chạy lại test trên `main` `cabcc44`: 44 passed ([bằng chứng](evidence/w6-s02-sync.md)). Lần đồng bộ này không đổi phase, không ghi APPROVED/DONE; review, verification và acceptance chờ reviewer/user.

## SCRUM-88 / W6-N03 — 25/10/2026

Theo xác nhận trực tiếp của chủ dự án, GVHD đã đồng ý duyệt; chủ dự án được ủy quyền chốt và không cần biên bản riêng. Commit `6de3206` bổ sung hai prompt fixture version hóa, rubric A2–B2 trên phiếu chấm mù và xử lý placeholder `demo-speaking` trong data-dir cũ. Placeholder chưa được dùng được cập nhật an toàn; nếu đã có bài nộp, v1 được giữ lịch sử và wording mới mở ở v2.

Browser QA trên Chromium xác nhận danh sách đề, form nộp và phiếu chấm mù hiển thị đúng prompt/timing/rubric. Chromium vẫn ghi lỗi ViewTransition trong lúc chuyển sang trang giáo viên; trang và control tiếp tục hoạt động. [Báo cáo và ảnh chụp](evidence/scrum-88/report.md). Không có người tham gia hoặc audio thật; phiếu fixture chưa được nộp. Kiểm thử local có một lỗi môi trường `WinError 1314` ở kiểm tra symlink; các kiểm tra liên quan SCRUM-88 qua. Phase/acceptance vẫn chờ verdict của owner.
