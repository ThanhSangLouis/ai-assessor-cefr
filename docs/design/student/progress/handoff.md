# Bàn giao thiết kế — Tiến trình xử lý

Hướng A đã được người dùng chọn; bản tinh chỉnh đang chờ duyệt. URL: `/progress/{response_id}`. Phạm vi hiện tại là mockup, chưa thay đổi ứng dụng thật.

## Bố cục

Giữ shell Student chung, cảnh và mascot theo vùng, dùng ảnh ban đêm khi theme tối. Trạng thái là trọng tâm; tên bài là ngữ cảnh phụ. Mobile giảm chiều cao cảnh, ba mốc nằm ngang; nội dung dài được cuộn với khoảng đệm cho thanh điều hướng dưới. Không cố định chiều cao thẻ. Không đưa thanh chọn mẫu/theme/trạng thái và ghi chú dữ liệu mẫu vào sản phẩm.

## Trạng thái và hành động

| Mẫu | Khi hiển thị | Hành động |
| --- | --- | --- |
| checking | Chưa nhận phản hồi trạng thái đầu tiên | Chờ xác minh; không báo đã nhận bài |
| queued | API xác nhận QUEUED | Đã nhận hoàn tất, chờ đến lượt hiện tại; về Bài đã nộp |
| running | API xác nhận RUNNING | Tự cập nhật; có thể rời trang |
| long | Vẫn nhận RUNNING sau ngưỡng chờ lâu được thống nhất khi tích hợp | Tiếp tục theo dõi; không gọi là thất bại |
| offline | Không thể lấy trạng thái | Kiểm tra lại và về danh sách; chỉ hiện trạng thái cũ nếu thực sự có, kèm thời điểm cập nhật nếu có dữ liệu |
| timeout | Đã dừng theo dõi tự động sau giới hạn 5 phút hiện hành | Kiểm tra lại để tiếp tục theo dõi, không chạy lại xử lý |
| session | Phiên đăng nhập hết hạn | Đăng nhập với next trỏ về đúng bài |
| unknown | Payload không có trạng thái hợp lệ hoặc trạng thái chưa hỗ trợ | Kiểm tra lại; không suy luận là DONE |
| done | Trạng thái hoàn tất hợp lệ | Tự mở `/report/{response_id}`, giữ nút dự phòng |
| failed | Hệ thống xác nhận xử lý thất bại | Mở lý do/hướng dẫn ở report đúng bài |
| rejected | Hệ thống xác nhận bản ghi không đạt | Mở lý do/hướng dẫn ở report đúng bài |
| missing | 404 hoặc không truy cập được bài theo contract | Không hiện metadata chưa xác minh; về danh sách |

Mẫu offline hiện có trạng thái cũ minh họa. Nếu lần truy vấn đầu tiên lỗi, không được tự gán trạng thái cũ. Nội dung lỗi cụ thể lấy từ dữ liệu đã kiểm soát, hiển thị bằng textContent; không tự đoán nguyên nhân. Không tạo nút nộp lại/chạy lại xử lý khi chưa có khả năng và quyền tương ứng.

## Tích hợp

Đối chiếu `src/aicefr/api/static/progress.js`, template `progress.html` và login gate hiện hành. Giữ status endpoint, live event, polling fallback, xử lý hết phiên và kiểm soát quyền ở server. Dùng mapping trạng thái tường minh; code cũ chuyển mọi trạng thái ngoài QUEUED/RUNNING sang report cần được xử lý theo contract. Không coi các giai đoạn QC/ASR/chấm hoặc thời gian đã chờ là tiến độ thật.

Hủy timer/request khi rời trang hoặc kết thúc, tránh nhiều vòng poll khi bấm kiểm tra lại; không lặp thông báo live region mỗi lần poll nếu trạng thái không đổi. Sau reconnect phải lấy lại trạng thái từ máy chủ. Nếu hiển thị bộ đếm, phân biệt thời gian mở trang và thời gian xử lý thực tế. Đường dẫn demo trong mockup phải thay bằng response_id đã xác thực; đăng nhập dùng `/login?next=...`. Link Bài đã nộp khi tích hợp là `/my-responses`.

`role=status` thông báo thay đổi, icon trang trí ẩn khỏi trình đọc, trạng thái có chữ ngoài màu, nút tối thiểu 44px và focus rõ. Spinner tôn trọng reduced motion. Không tự xin quyền thông báo, không suy luận thất bại từ mất mạng hoặc timeout.

## Giới hạn

Mockup không gọi server, retry giữ nguyên trạng thái và báo rõ chưa kết nối; chọn trạng thái trên toolbar để duyệt tình huống kế tiếp. Hoàn tất không tự chuyển trang để người duyệt xem được thiết kế. Chưa kiểm thử API thật, đăng nhập hay auto-redirect. B/C là tài liệu so sánh cũ, không phải bản bàn giao chính.
