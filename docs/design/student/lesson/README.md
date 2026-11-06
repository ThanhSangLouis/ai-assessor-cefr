# Bài học · Student

**Đã chốt: C · Sân khấu luyện nói.** Chỉ giữ một hướng thiết kế; đã xóa selector, bộ chọn, mô tả và ảnh xem trước của A/B/D. Chưa thay đổi trang lesson thật.

- URL ứng dụng: `/practice/lessons/{lesson_id}`.
- Mở [lesson-mockup.html](lesson-mockup.html) trực tiếp bằng trình duyệt.
- [Tài liệu bàn giao triển khai](implementation-handoff.md).
- CSS/JS riêng: `lesson-mockup.css`, `lesson-mockup.js`.

Bố cục: header phong cảnh gọn và mascot của vùng học; tiến trình ngang; thẻ luyện nói rộng; thẻ ghi chú bên phải ở desktop rộng, được ẩn khi chật. Mobile xếp dọc, giữ bốn bước gọn phía trên nội dung.

Thanh điều khiển chỉ phục vụ review: sáu vùng cảnh, sáng/tối, khung mobile và sáu trạng thái (sẵn sàng, ghi âm, nghe lại, phản hồi, hoàn thành, lỗi micro). Không có bộ chọn hướng thiết kế nữa. Nội dung A1 dùng chung để so sánh phong cảnh, không phải nội dung thật của các band.

Mockup không truy cập micro, không phát âm thanh và không lưu tiến độ. Điều hướng bước và hoàn thành mô phỏng không đại diện cho quy tắc mở khóa thật. Dùng lại ảnh và font nội bộ của roadmap; mở file:// không cần server. Cần trình duyệt hỗ trợ container queries.

Kiểm tra sau khi dọn hướng cũ: 12 tổ hợp (2 theme × 320/390/768/1024/1440/1920px), sáu trạng thái mỗi tổ hợp; không tràn ngang hoặc lỗi JavaScript. Ảnh tại [evidence/](evidence/). Đây là kiểm chứng mockup, không phải nghiệm thu lesson thật.
