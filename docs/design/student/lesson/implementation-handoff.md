# Bàn giao thiết kế lesson · C — Sân khấu luyện nói

## Quyết định đã chốt

Người dùng chọn hướng C. Nguồn thiết kế duy nhất: [lesson-mockup.html](lesson-mockup.html). Những hướng A/B/D đã loại bỏ. Phạm vi bàn giao là thiết kế, chưa triển khai ứng dụng hoặc thay đổi contract.

## Bố cục và component

| Thành phần | Quy tắc |
| --- | --- |
| Shell | Tái sử dụng sidebar/header của ứng dụng thật trong `base.html`; sidebar vẽ trong mockup chỉ để tham khảo tỷ lệ. |
| Header | Phong cảnh gọn, tên bài và band thật; mascot tương ứng vùng. Ảnh đêm riêng khi theme tối. |
| Tiến trình | Một hàng các bước, trạng thái đã qua/hiện tại/chưa tới; số bước thật lấy từ dữ liệu. Nếu nhiều bước cần cuộn ngang hoặc nhóm gọn, không ép mọi nhãn vào một hàng. |
| Thẻ nội dung | Thứ bậc: loại hoạt động → tiêu đề → hướng dẫn → câu mẫu/học liệu → ghi âm → phản hồi → điều hướng. |
| Ghi âm | Nút cam ưu tiên, trạng thái/đồng hồ đọc được; khi thu chuyển màu đỏ và có chữ “Dừng ghi âm”. Sóng âm thật chỉ xuất hiện khi có tín hiệu micro. |
| Ghi chú | Bên phải trên desktop rộng; ẩn ở khung hẹp. Thông tin thiết yếu phải nằm trong thẻ chính, không chỉ ở ghi chú. |
| Hoàn thành | Huy hiệu xanh, tóm tắt nội dung và nút về roadmap. Chỉ hiển thị sau khi backend xác nhận hoàn thành. |

## Nguồn dữ liệu và mã hiện có

- Trang: `src/aicefr/api/templates/lesson.html`.
- Luồng học: `src/aicefr/api/static/lesson.js`.
- Ghi âm dùng chung: `src/aicefr/api/static/recorder.js`, template `_recorder.html`.
- Vùng A1/A2/B1/B2/C1/C2 lần lượt forest/volcano/snow/river/desert/flowers; tái sử dụng mapping roadmap, không đoán vùng từ chỉ số bước.
- Cảnh: `static/art/adventure/{world}-{day|night}-a-v3-{width}.webp`; mascot `mascot-{world}-v3.webp`.
- Chọn cỡ ảnh theo khung và mật độ màn hình; không kéo giãn theo số bước, không giảm sáng cảnh ngày để giả cảnh đêm.

CSS/JS mockup phục vụ thiết kế và review. Khi implement, nối vào renderer hiện có, tái sử dụng component và token hệ thống, không thay toàn bộ lesson bằng dữ liệu ví dụ trong mockup.

## Trạng thái và tương tác cần giữ

| Trạng thái | Hành vi ứng dụng cần có |
| --- | --- |
| Loading/trống/không có quyền | Theo dữ liệu thật, có thông báo và đường quay về; không hiện nội dung fixture. |
| Sẵn sàng | Có hướng dẫn và giới hạn từ cấu hình của bước. Không báo “đã lưu” nếu chưa lưu. |
| Đang ghi | Timer, nút dừng; không đổi bước âm thầm làm mất bản ghi. Xử lý rời trang theo luồng hiện có. |
| Nghe lại | Audio thật, ghi lại và gửi; kiểm tra thời lượng/kích thước theo backend. |
| Đang gửi | Khóa thao tác gửi lặp, thể hiện đang xử lý và phục hồi khi lỗi. |
| Phản hồi | Nội dung từ kết quả thật; không biến lời động viên thành kết luận chấm điểm. |
| Lỗi micro/mạng | Giải thích cụ thể, có thử lại hoặc lựa chọn tải bản ghi nếu được hỗ trợ. |
| Hoàn thành | Theo kết quả backend; giữ quy tắc tiến trình/mở khóa FE và BE hiện có. |

Mockup mô phỏng sáu trạng thái hình ảnh chính. Loading, gửi mạng và quyền truy cập cần nối với trạng thái thực tế khi triển khai. Không coi việc bấm chuyển bước tự do trong mockup là thay đổi nghiệp vụ.

## Responsive, theme và khả năng truy cập

- Header gọn; nội dung chính không bị mascot/khung thoại che.
- Thẻ ghi chú phụ biến mất khi không đủ chỗ; tiến trình vẫn nhìn thấy trên mobile.
- Hỗ trợ tiêu đề dài, nhiều bước, câu mẫu dài, bản dịch và nội dung phản hồi dài.
- Theme sáng/tối và tùy chọn theo hệ thống phải dùng cơ chế theme thật của website.
- Label rõ, `aria-current="step"`, trạng thái động qua live region; tab bằng bàn phím và focus nhìn rõ.
- Tôn trọng `prefers-reduced-motion`; animation ăn mừng một lần và không làm dịch chuyển thao tác.

## Kiểm chứng mockup đã thực hiện

Playwright: 12 tổ hợp theme/viewport × 6 trạng thái, không lỗi JavaScript/tràn ngang. Các viewport: 320, 390, 768, 1024, 1440, 1920px. Ảnh desktop/mobile sáng/tối ở `evidence/`. Chưa kiểm chứng kết nối API, micro thật, teacher preview, ôn tập hay nghiệp vụ mở khóa trên bản triển khai mới.
