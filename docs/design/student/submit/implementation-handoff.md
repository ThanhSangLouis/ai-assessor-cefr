# Bàn giao thiết kế submit · B — Từng bước tự tin

Người dùng đã chọn B. Nguồn thiết kế duy nhất: [submit-mockup.html](submit-mockup.html); không triển khai A/C. Bàn giao thiết kế, chưa thay đổi ứng dụng/contract.

## Luồng và bố cục

| Bước | Nội dung và thao tác |
| --- | --- |
| 1 · Chọn đề | Hiển thị danh sách đề thật, lựa chọn radio, đổi bộ đề nếu có; không hiển thị studio khi chưa chọn. |
| 2 · Chuẩn bị & nói | Đề đã chọn, gợi ý thu gọn, chuẩn bị tùy chọn, ghi âm nổi bật và thời lượng rõ. |
| 3 · Nghe lại & gửi | Audio thật, ghi lại, gửi một lần; trạng thái upload và xác nhận vào hàng đợi. |

Header phong cảnh gọn và mascot đồng bộ roadmap/lesson C. Một thẻ chính đặt giữa, không để khoảng trống do cột ẩn. Mobile dùng cùng thứ tự; ba bước ở một hàng, nhãn ngắn. Theme tối dùng ảnh đêm riêng và surface dễ đọc. Thanh chọn theme/vùng/trạng thái phía trên chỉ dùng review, không đưa vào sản phẩm.

## Nguồn triển khai

- Trang hiện tại: `src/aicefr/api/templates/submit.html`.
- Logic: `src/aicefr/api/static/submit.js`.
- Ghi âm: `recorder.js` và `_recorder.html`; tái sử dụng thay vì viết recorder mới từ mockup.
- Shell và điều hướng: `base.html`. Sidebar mockup chỉ minh họa tỷ lệ.
- Mockup dùng chung CSS lesson tại `../lesson/lesson-mockup.css`, ảnh/font có sẵn trong `src/aicefr/api/static/`.

Dữ liệu đề, band, thời gian chuẩn bị, thời lượng hợp lệ, định dạng/kích thước file, quyền ghi âm và lượt nộp phải lấy từ contract/API hiện hành. Không hardcode fixture 30/40–60/120 giây của mockup vào nghiệp vụ. Bộ chọn vùng trong mockup không xác định band đề.

## Trạng thái và hành vi cần triển khai

- Tải đề, chưa có đề, lỗi tải/thử lại: thông báo rõ và đường quay về.
- Chuẩn bị: có nói ngay, countdown và hành vi hết thời gian theo luồng hiện tại; khi đổi đề reset chuẩn bị.
- Micro: xin quyền khi cần, xử lý từ chối/không có thiết bị; chỉ báo micro sẵn sàng khi đã kiểm tra thật. Waveform phản ánh tín hiệu thật.
- Ghi âm: nút dừng và đồng hồ rõ, kiểm tra giới hạn thực tế. Khi đổi đề/rời bước có bản ghi, không âm thầm mất dữ liệu; giữ lại hoặc xác nhận bỏ bản ghi.
- Nghe lại: phát audio thật; kiểm tra bản ghi quá ngắn/dài/kích thước/định dạng trước gửi. Tải file tuân thủ cùng giới hạn.
- Gửi: ngăn gửi lặp, báo lỗi mạng và cho thử lại giữ bản ghi; không tự báo thành công theo timer giả.
- Thành công: xác nhận từ API, dẫn đến `/progress/{response_id}` thật hoặc bài đã nộp. Không giả điểm/band hay hứa thời gian có kết quả.
- Lượt nộp/hết lượt và quyền truy cập giữ theo backend; không thay đổi quy tắc đánh giá.

Mockup có chín trạng thái chính và luồng giả lập; các lỗi gửi, validation audio, hết lượt cần ghép vào dữ liệu và xử lý thật khi implement. Chuyển trạng thái qua thanh review không đại diện cho quyền bỏ qua các bước.

## Responsive và kiểm chứng

Đã kiểm tra mockup 320/390/768/1024/1440/1920px ở sáng/tối, chín trạng thái; không lỗi JS/tràn ngang, luồng chọn → ghi → nghe lại → gửi → chủ đề mới đạt. Screenshot trong `evidence/`. Khi implement cần kiểm tra thêm bàn phím, focus khi đổi bước, live region, nội dung đề dài, nhiều đề, zoom và micro/API thật. Tôn trọng reduced motion, dùng radio native và thông báo trạng thái không phụ thuộc màu.
