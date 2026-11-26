# Thiết kế passage · Đang chờ chọn hướng

Ba hướng tại [passage-design-options.html](passage-design-options.html). **CHỜ DUYỆT** — người dùng chưa chọn hướng triển khai. Cập nhật 26/11/2026.

## Nguồn đối chiếu

Tái dùng quy tắc [lesson C](../../student/lesson/implementation-handoff.md), sidebar/header hiện hành và palette sáu vùng. FE lấy shell từ base.html của ứng dụng, bỏ thanh duyệt thiết kế.

## Nội dung và luồng

Đối chiếu template `src/aicefr/api/templates/passage.html` và `static/passage.js` khi tích hợp. Dữ liệu trong mockup là fixture. Giữ hành vi và phân quyền của trang thật. Theme và vùng do ngữ cảnh học quyết định khi triển khai.

Thanh duyệt có sáng/tối, chọn trạng thái, chuyển A/B/C và preview 390px. Chọn vùng tại đầu trang. Mỗi mẫu có file riêng. Mobile xếp nội dung thiết yếu trước thao tác, drawer/Escape và tab bar dùng shell chung.

## Trạng thái

Tải, trống, lỗi tải và mất kết nối có nội dung riêng. Trạng thái gửi/lưu khóa hành động. Lỗi gửi/lưu giữ nội dung và cho phép thử lại. Trạng thái preview do thanh duyệt điều khiển, cần nối với kết quả thực tế khi triển khai.

Ghi âm có sẵn sàng, quyền micro bị chặn, đang thu, đã thu, đang gửi, lỗi gửi và phản hồi. Thu lại cần xóa bản ghi cũ sau khi người dùng xác nhận theo luồng ứng dụng. Timer mô phỏng, không có audio thật. Chỉ hiển thị phản hồi từ dữ liệu trả về.

## Điều kiện bàn giao cuối

Chốt một hướng, hoàn thiện các trạng thái và dữ liệu dài, xóa các hướng bị loại, giữ một nguồn mockup cùng CSS/JS và ảnh đầy đủ desktop/mobile sáng/tối. Kiểm tra route theo ID thật, micro/API, lỗi mạng và quyền truy cập khi tích hợp.
