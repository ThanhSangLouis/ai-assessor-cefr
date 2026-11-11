# Thiết kế giao diện

Sắp xếp mockup theo cấu trúc `<role>/<screen>/`, dùng tên role trong hệ thống: `student`, `teacher`, `admin`. Tạo thư mục màn hình khi có thiết kế tương ứng.

- `student/practice/`: màn hình luyện tập / Lộ trình học (`/practice`), gồm 4 ảnh giao diện và 1 mockup HTML.
- `student/lesson/`: thiết kế màn hình bài học (`/practice/lessons/{lesson_id}`), đã chốt C — [mockup bàn giao](student/lesson/lesson-mockup.html).
- `student/submit/`: thiết kế màn hình nộp bài đánh giá (`/`, khi đăng nhập student), đã chốt B — [mockup bàn giao](student/submit/submit-mockup.html).
- `teacher/`: khu giảng viên, thế giới "Thời khoá biểu khoa" (hàng đợi dạng tuần, dải bản ghi, thanh band), chọn 11/11/2026 — [README](teacher/README.md), [mockup](teacher/staff-world-mockup.html).
- `admin/`: khu quản trị, dùng chung thế giới với giảng viên — [README](admin/README.md).
- `week-01/`: sơ đồ lớp tuần 1, giữ riêng vì không thuộc một màn hình hay role cụ thể.
