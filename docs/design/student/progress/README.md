# Tiến trình xử lý bài nói

Đã chọn **A · Trạm chờ trong cảnh** cho `/progress/{response_id}` (Student).

- [Mở mockup A](processing-a-mockup.html).
- [Ghi chú bàn giao FE](handoff.md).
- [Trang chọn mẫu](processing-design-options.html); B/C giữ lại để đối chiếu, không phải hướng triển khai.

Mục tiêu: xác nhận bài đã nhận, hiển thị trạng thái thật, cho biết có thể rời trang và dẫn đến báo cáo đúng bài. Không hiển thị điểm tại màn chờ, phần trăm hay ETA giả.

Mockup có 12 trạng thái, sáu vùng cảnh ngày/đêm, responsive và nút xem mobile390. Tái dùng shell/palette từ màn Kết quả. Không gọi API, không tự chuyển trang; tên bài và demo-23 là dữ liệu mẫu. Toolbar không thuộc giao diện sản phẩm.

Kiểm tra Chromium: 192 tổ hợp A × 2 theme × 8 chiều rộng (320,390,600,768,900,1024,1440,1920) × 12 trạng thái, không tràn ngang/lỗi JS. Kiểm tra retry không tự đổi trạng thái, metadata ẩn khi chưa xác minh bài, sáu mascot tải được và preview390. Đã xem ảnh A mobile sáng và desktop tối. Đây là kiểm tra mockup, chưa kiểm thử tích hợp API hoặc tự chuyển báo cáo.
