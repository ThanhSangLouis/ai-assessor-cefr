# Bài đã nộp — C · Nhật ký nộp bài

- URL: `/my-responses` · Student.
- Người dùng đã chọn **C · Nhật ký nộp bài**.
- [Mở mockup](responses-c-mockup.html).
- [Bàn giao FE](handoff.md).
- `responses-options.css/js`: bố cục và tương tác mockup. Tái dùng theme/shell từ `../my-progress/`; không xóa các file đó.

Giữ dòng thời gian nhóm theo ngày, 23 bài mẫu, sáu bài/trang. Có tìm kiếm, lọc loại/trạng thái, mới/cũ trước, sáng/tối, sáu vùng và các trạng thái tải. Đã xóa A/B và trang chọn phương án.

Đây là mockup, chưa nối API hoặc triển khai app. Bộ chọn trên cùng chỉ phục vụ review. Điểm, tiêu đề và hồ sơ JSON là dữ liệu mẫu.

## Kiểm tra sau khi chốt

Chromium: 56 tổ hợp (2 theme × 7 width 320–1920px × 4 trạng thái) không tràn ngang/lỗi JS. Nhóm ngày đúng; tìm/lọc/reset, bài lỗi không có điểm, phân trang đến cuối, dialog/Escape, 12 cặp vùng/theme và liên kết cục bộ hoạt động. Node kiểm tra cú pháp và git diff --check. Chưa kiểm thử API/app thật.

Tinh chỉnh popup xem trước: bỏ mã kỹ thuật/đoạn giải thích triển khai, tên và ngày rõ hơn, điểm lớn trong nền nhẹ, nhãn xác nhận và nút quay lại. Trạng thái đang chấm/lỗi không hiện điểm. Chromium 36 tổ hợp 2 theme × 3 width × 6 trạng thái, popup không tràn và Escape hoạt động. Đây vẫn là preview; triển khai mở trang report/progress theo handoff.

## Luồng mở bài đã chốt

Bỏ hoàn toàn popup kết quả. Tên bài và CTA là liên kết thật tới `/report/{id}`; QUEUED/RUNNING tới `/progress/{id}`. Mockup dùng ID demo, không bảo đảm URL có dữ liệu trên localhost. Khi tích hợp phải dùng response_id thật. Các kiểm tra dialog và mô tả preview trước đây không còn áp dụng.

## Tinh chỉnh mobile

Bổ sung nút Xem mobile (390px) ngay trong toolbar. Hero dạng trang nhật ký có scenery/mascot, tiêu đề không bị ép cạnh điểm. Mobile dành toàn hàng cho tên và trạng thái bài; điểm/thao tác ở hàng dưới, cỡ chữ và vùng bấm tăng. Tìm kiếm luôn hiện, loại bài/sắp xếp thu trong Bộ lọc & sắp xếp; tab trạng thái cuộn trong hàng. Export toàn chiều rộng, khoảng đệm đáy theo tabbar. Chromium 20 tổ hợp theme × 320/360/390/430/600/768/900/1024/1440/1920px không tràn ngang/lỗi JS; filter, preview390, tabbar và drawer/Escape hoạt động. Đã xem ảnh mobile tối.

Tinh chỉnh sau review: ngày chỉ ở tiêu đề nhóm, từng bài hiện giờ; nhãn xác nhận chỉ hiện một lần. Bài chờ/lỗi không thêm câu Chưa có điểm. Hero nhỏ hơn, danh sách không còn thẻ/hiệu ứng lớp giấy lặp; hồ sơ năng lực một hàng phụ. Chromium 16 theme/width 320–1920px không tràn ngang/lỗi JS; metadata đúng, preview mobile/lọc/phân trang hoạt động.

Điều chỉnh mới nhất theo phản hồi tối giản quá tay: khôi phục hero phong cảnh và thẻ bo góc/nền giấy trước đó, giữ bỏ ngày và nhãn lặp; không dùng biến thể danh sách phẳng. Chromium 10 tổ hợp sáng/tối/width không tràn ngang, kiểm tra thẻ đã khôi phục và ngày không lặp.

Căn phải toàn bộ CTA Xem kết quả/tiến trình/lý do ở cùng mép, không để thiếu điểm đẩy nút vào cột giữa. Chromium 12 tổ hợp theme/width xác nhận mép phải chênh dưới 1px và không tràn ngang.
