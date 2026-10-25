# SCRUM-86 — Đối chiếu backlog Jira W06

**Task:** SCRUM-86 / W6-T05 · **Ngày rà:** 25/10/2026 · **Owner theo nhánh:** Thắng  
**Baseline local:** `82fe708af80f0b50eb540c65b5c583f64868d2c8`  
**Kết quả:** đã lập disposition theo evidence repo; chưa sửa issue/status trên Jira vì phiên Atlassian chưa kết nối.

## Phạm vi xác minh

Hai ảnh người dùng cung cấp hiển thị tiêu đề và `To Do` cho SCRUM-81, SCRUM-83–89. Không có mô tả, Acceptance Criteria, project URL, workflow transitions hoặc lịch sử issue. Repo có kế hoạch W06 `DRAFT`; mapping `W6-T02` trong plan (`Backend task closeout`) khác tiêu đề SCRUM-83 trong ảnh (`Bằng chứng nền tảng của DoD W5`), còn `W6-T03–T05` không có trong plan đó. Do đó không coi tiêu đề ảnh là đủ căn cứ để đóng, xóa, đổi assignee hoặc đổi status issue.

## Disposition theo bằng chứng hiện có

| Issue | Trạng thái thấy trong ảnh | Bằng chứng trong repo/task branch | Đề xuất disposition; chưa áp dụng Jira |
| --- | --- | --- | --- |
| SCRUM-81 — W6-S04 chấm mù phục vụ tập huấn | `To Do` · avatar ST | M12 còn `DRAFT/PENDING`, implementation một phần; chưa có roster, buổi tập huấn hoặc calibration người thật. | Giữ owner Sang; không đóng. Chốt AC và dependency với SCRUM-88/89 trước khi chuyển trạng thái. |
| SCRUM-83 — W6-T02 evidence DoD W5 | `To Do` · avatar LT | Evidence index local commit `f6a8ef0`; W5 DoD có điều kiện mở, W5 vẫn `PENDING`. Branch chưa push/merge. | Có thể đề nghị `In Review` sau khi push/PR và xác nhận Jira AC; tuyệt đối chưa `Done`. |
| SCRUM-84 — W6-T03 sync SDD M11/M14/M16 | `To Do` · avatar LT | SDD/task evidence local commit `2126039`; global phases/acceptance vẫn pending. Branch chưa push/merge. | Có thể đề nghị `In Review` sau khi push/PR; chưa `Done` hoặc `Approved`. |
| SCRUM-85 — W6-T04 data cho pilot W7 | `To Do` · avatar LT | Readiness report local commit `c159fd8`; protocol/consent chưa duyệt, dataset không có. | Đề nghị dùng transition `Blocked` nếu workflow có; nếu không, ghi blocker sau khi xem AC. Không tạo dữ liệu người thật. |
| SCRUM-86 — W6-T05 dọn backlog Jira | `To Do` · avatar LT | Chỉ có task title trong ảnh và disposition trong file này; chưa có Jira read/write. | Chưa thể đóng task dọn backlog khi chưa truy cập và đối chiếu các issue thật. |
| SCRUM-87–89 — W6-N02–N04 | `To Do` trong ảnh trước · avatar HN | Ba branch local ahead 6 commit, chưa push; phiếu/protocol/tập huấn đều còn khoảng trống theo audit. | Không đổi status thay Nguyên; giữ làm dependency của SCRUM-81/85, chờ review/owner verdict. |

## Hành động Jira chưa thực hiện

- Không transition status, xóa ticket, đổi owner/assignee, sửa due date hoặc thêm comment.
- Không đánh dấu `Done` dựa trên commit local chưa push/merge hoặc test/evidence của revision cũ.
- Không đổi SCRUM-81 vì thuộc owner Sang.
- Không gộp SCRUM-83 vào task backend chỉ vì plan W06 dùng trùng mã `W6-T02`; cần reconcile Jira description/AC với owner trước.

## Điều kiện tiếp tục SCRUM-86

1. Kết nối Atlassian/Jira hoặc cung cấp URL board/project và quyền đọc/ghi phù hợp.
2. Đọc description, AC, parent/epic, assignee và workflow hiện hành của SCRUM-81, SCRUM-83–89.
3. Đối chiếu các commit/PR sau khi branch được push; áp dụng disposition theo workflow Jira thật, giữ trạng thái chờ review/blocked khi thiếu gate.
4. Chỉ sau khi từng issue khớp evidence và owner, chủ dự án mới đưa verdict/đóng task theo quy trình.

Đây là báo cáo chuẩn bị backlog, không phải Jira change log hoặc bằng chứng task SCRUM-86 đã hoàn tất.
