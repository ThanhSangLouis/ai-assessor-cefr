# Thiết kế giao diện

Sắp xếp mockup theo cấu trúc `<role>/<screen>/`, dùng tên role trong hệ thống: `student`, `teacher`, `admin`; phần dùng chung đặt trong `shared`. Mỗi màn hình có thư mục riêng và README ghi URL, hướng thiết kế.

- `student/practice/`: màn hình luyện tập / Lộ trình học (`/practice`), gồm 4 ảnh giao diện và 1 mockup HTML.
- `student/lesson/`: thiết kế màn hình bài học (`/practice/lessons/{lesson_id}`), đã chốt C — [mockup bàn giao](student/lesson/lesson-mockup.html).
- `student/submit/`: thiết kế màn hình nộp bài đánh giá (`/`, khi đăng nhập student), đã chốt B — [mockup bàn giao](student/submit/submit-mockup.html).
- `teacher/`: khu giảng viên, thế giới "Thời khoá biểu khoa" (hàng đợi dạng tuần, dải bản ghi, thanh band), chọn 11/11/2026 — [README](teacher/README.md), [mockup](teacher/staff-world-mockup.html).
- `admin/`: khu quản trị, dùng chung thế giới với giảng viên — [README](admin/README.md).
- `week-01/`: sơ đồ lớp tuần 1, giữ riêng vì không thuộc một màn hình hay role cụ thể.

- `student/my-progress/`: màn Kết quả (`/my-progress`), đã chốt B2 — [mockup](student/my-progress/passport-candy-mockup.html), [bàn giao FE](student/my-progress/handoff.md).
- `student/my-responses/`: Bài đã nộp (`/my-responses`), đã chọn C — [mockup](student/my-responses/responses-c-mockup.html), [bàn giao FE](student/my-responses/handoff.md).
- **Tiến trình xử lý** (`/progress/{response_id}`) — [Mockup A](student/progress/processing-a-mockup.html) · [Bàn giao](student/progress/handoff.md).
- **Sổ cụm từ** (`/phrases`) — [Mockup D](student/phrases/phrases-d-mockup.html) · [Ghi chú FE](student/phrases/README.md).

- [Kế hoạch và trạng thái duyệt](design-plan.md) — ba màn retell/drill/passage đang chờ duyệt.
