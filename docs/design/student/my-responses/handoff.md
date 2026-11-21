# Bàn giao FE — Bài đã nộp

## Quyết định thiết kế

Người dùng chọn **C · Nhật ký nộp bài**. Nguồn chuẩn: [responses-c-mockup.html](responses-c-mockup.html). Giữ nhóm ngày trên dòng thời gian, mỗi bài có tên, thời điểm, loại, trạng thái, kết quả hợp lệ và một thao tác rõ ràng. Không dùng lại lưới thẻ B hoặc danh sách A.

Tái dùng sáu palette sáng/tối và navigation đã duyệt của màn Kết quả. Trong app kế thừa `base.html`, theme dùng điều khiển chung; bỏ toolbar review. Đồng hoa là vùng mặc định khi chưa có ngữ cảnh vùng. Các vùng không làm thay đổi điểm. Không sao chép shell mockup vào app thật.

## Dữ liệu và hành vi

- Bám `src/aicefr/api/templates/my_responses.html` và `static/my_responses.js` hiện hành, tái sử dụng API và phân quyền. Tên bài từ nguồn task; thời điểm từ timestamp thật, định dạng theo locale/timezone của app.
- Mặc định mới nhất trước; sắp theo timestamp, dùng khóa phụ ổn định khi bằng nhau. Nhóm theo ngày hiển thị; một ngày có thể tiếp tục ở trang kế tiếp.
- Sáu bài/trang; tìm theo tên, lọc loại và trạng thái, đổi mới/cũ trước. Khi thay bộ lọc về trang đầu. Phân trang cần tổng kết quả thực, không lấy độ dài trang làm tổng.
- `QUEUED/RUNNING`: không hiển thị điểm, thao tác **Xem tiến trình** mở `/progress/{response_id}`.
- `FAILED/REJECTED`: không hiển thị điểm/band, **Xem lý do** mở trang báo cáo theo logic hiện có và thông báo thật; không tự đặt lý do.
- Bài có kết quả: **Xem kết quả** mở `/report/{response_id}`; phân biệt rõ ước lượng/chưa xác nhận và giảng viên xác nhận. Band chỉ lấy từ dữ liệu đã lưu, không tự quy đổi.
- Luyện tập trong fixture không chấm điểm; khi tích hợp cần bám contract thật cho loại bài. Không trộn thành điểm đánh giá.
- Giữ đánh dấu quyết định mới của giảng viên nếu backend cung cấp `reviewed_at`, theo hành vi hiện có; mockup chưa mô phỏng cơ chế đã xem.
- Tải hồ sơ năng lực giữ API hiện hành, chỉ lấy bài giảng viên xác nhận. JSON mẫu có `mockup: true`, tuyệt đối không dùng làm hồ sơ thật.

## Trạng thái và responsive

Có dữ liệu, chưa nộp bài, không có kết quả khớp bộ lọc, đang tải và lỗi tải phải khác nhau. Nút xóa bộ lọc giữ dữ liệu, retry gọi nguồn thật. Xử lý thiếu tiêu đề, điểm, band và timestamp mà không bịa giá trị. Không có popup trung gian: tên bài và CTA dẫn thẳng tới report/progress theo ID. Mockup dùng mã demo, nên liên kết localhost có thể không tồn tại trên dữ liệu thật.

Mobile giữ tên, trạng thái, điểm và CTA rõ ràng; không cuộn ngang; drawer chung ở 900px, tab bar không che nội dung. Các nút cần dùng được bằng bàn phím, focus rõ. Phân trang giữ focus hợp lệ; Escape và trả focus khi đóng drawer.

## Giới hạn kiểm chứng

Mockup dùng 23 bài giả lập, không gọi API, không phát audio. Khi FE tích hợp phải kiểm tra quyền student, đường dẫn đúng ID, search/sort/pagination trên toàn bộ dữ liệu, thời gian, luồng giảng viên xác nhận và xuất JSON thật. Kết quả kiểm tra mockup cuối ghi ở README; chưa nghiệm thu implementation.

## Đối chiếu link theo mã nguồn local

Đã kiểm tra `services/web/pages.py`: `/my-responses`, `/my-progress`, `/progress/{response_id}` và `/report/{response_id}` là route hiện có, yêu cầu đăng nhập. Cách phân luồng theo trạng thái khớp `static/my_responses.js`. Tên bài và CTA cùng trỏ tới một ID. URL mẫu có origin localhost để mở được khi xem HTML qua file://; khi tích hợp dùng link tương đối theo origin app. ID `demo-*` không có báo cáo thật.

Tab Tiến độ trong mockup mở HTML Kết quả đã duyệt để so sánh; khi triển khai dùng `/my-progress`. Tab Bài đã nộp trỏ về mockup hiện tại, không dùng `#`. Mục Lớp của tôi là shell thiết kế đối chiếu main trước đây; revision local hiện không có `/my-classes`, nên không coi link này đã được xác minh hoạt động. FE cần lấy nguyên navigation được hỗ trợ của base.html ở revision tích hợp, không tự thêm route. Các mục khác practice/account/credits có route local.

Mobile đã bổ sung layout riêng: tên/trạng thái toàn hàng, điểm và CTA hàng dưới, lọc nâng cao thu gọn (search luôn hiện), export full width. Nút Xem mobile chỉ phục vụ duyệt mockup, không thuộc app. Giữ cỡ chữ/vùng bấm theo CSS mới; không chỉ thu nhỏ desktop.

Tinh chỉnh sau review: ngày chỉ ở tiêu đề nhóm, từng bài hiện giờ; nhãn xác nhận chỉ hiện một lần. Bài chờ/lỗi không thêm câu Chưa có điểm. Hero nhỏ hơn, danh sách không còn thẻ/hiệu ứng lớp giấy lặp; hồ sơ năng lực một hàng phụ. Chromium 16 theme/width 320–1920px không tràn ngang/lỗi JS; metadata đúng, preview mobile/lọc/phân trang hoạt động.

Điều chỉnh mới nhất theo phản hồi tối giản quá tay: khôi phục hero phong cảnh và thẻ bo góc/nền giấy trước đó, giữ bỏ ngày và nhãn lặp; không dùng biến thể danh sách phẳng. Chromium 10 tổ hợp sáng/tối/width không tràn ngang, kiểm tra thẻ đã khôi phục và ngày không lặp.
