# Thiết kế account · Đang chờ chọn hướng

Ba hướng tại [account-design-options.html](account-design-options.html). Người dùng chưa chọn hướng triển khai.

## Nguồn đối chiếu

Tái dùng quy tắc [lesson C](../../student/lesson/implementation-handoff.md), sidebar/header hiện hành và palette sáu vùng. FE lấy shell từ base.html của ứng dụng, bỏ thanh duyệt thiết kế.

## Nội dung và luồng

Đối chiếu template `src/aicefr/api/templates/account.html` và `static/account.js` khi tích hợp. Dữ liệu trong mockup là fixture. Giữ hành vi và phân quyền của trang thật. Theme và vùng do ngữ cảnh học quyết định khi triển khai.

Thanh duyệt có sáng/tối, chọn trạng thái, chuyển A/B/C và preview 390px. Chọn vùng tại đầu trang. Mỗi mẫu có file riêng. Mobile xếp nội dung thiết yếu trước thao tác, drawer/Escape và tab bar dùng shell chung.

## Trạng thái

Tải, trống, lỗi tải và mất kết nối có nội dung riêng. Trạng thái gửi/lưu khóa hành động. Lỗi gửi/lưu giữ nội dung và cho phép thử lại. Trạng thái preview do thanh duyệt điều khiển, cần nối với kết quả thực tế khi triển khai.

Hồ sơ hiện mới bao phủ họ tên/email, nhắc học, hiển thị và đổi mật khẩu. Avatar, xác minh email, push, Google, danh sách phiên, lịch sử, export và xóa tài khoản còn cần thiết kế tương tác chi tiết trước bàn giao cuối.

## Điều kiện bàn giao cuối

Chốt một hướng, hoàn thiện các trạng thái và dữ liệu dài, xóa các hướng bị loại, giữ một nguồn mockup cùng CSS/JS và ảnh đầy đủ desktop/mobile sáng/tối. Kiểm tra route theo ID thật, micro/API, lỗi mạng và quyền truy cập khi tích hợp.
