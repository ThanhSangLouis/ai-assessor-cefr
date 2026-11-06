# Nộp bài đánh giá · Student

**Đã chốt B · Từng bước tự tin.** Đã bỏ bộ chọn hướng, code riêng và ảnh của A/C. Chưa thay đổi trang ứng dụng thật.

- URL ứng dụng: `/` khi đăng nhập student.
- Mở [submit-mockup.html](submit-mockup.html) trực tiếp bằng trình duyệt.
- [Tài liệu bàn giao triển khai](implementation-handoff.md).
- CSS/JS: `submit-mockup.css`, `submit-mockup.js`.

Bố cục: header cảnh gọn và mascot, tiến trình ba bước, một vùng thao tác chính tại mỗi thời điểm: chọn đề → chuẩn bị/nói → nghe lại/gửi. Dùng cùng hệ thống thẻ, nút và phong cảnh của lesson C/roadmap.

Thanh review chỉ còn sáu vùng cảnh, sáng/tối, khung mobile và chín trạng thái. Thử chọn đề → chuẩn bị 30 giây hoặc nói ngay → dừng → nghe lại/gửi mô phỏng → quay lại chọn đề. Gửi chuyển sang thành công sau khoảng 1,8 giây; chọn trạng thái đang gửi trên thanh review để xem riêng. Nút đổi bộ đề chỉ luân chuyển giữa ba đề mẫu.

Không truy cập micro, không phát âm thanh, không đọc hoặc gửi nội dung file. Nội dung đề, thời lượng và hạn mức trong mockup là fixture, không phải thay đổi nghiệp vụ. Bộ chọn vùng chỉ đổi cảnh để review, không đổi band đề.

CSS import `../lesson/lesson-mockup.css`; giữ đường dẫn này và các asset tương đối khi chuyển file. Mở qua file:// không cần server. Dùng trình duyệt hỗ trợ container queries.

Kiểm chứng sau khi dọn A/C: 12 tổ hợp (2 theme × 320/390/768/1024/1440/1920px), chín trạng thái mỗi tổ hợp; luồng nộp mô phỏng đạt, không tràn ngang hoặc lỗi JavaScript. Ảnh tại [evidence/](evidence/). Chưa kiểm tra micro/API thật.
