# Sổ cụm từ · D / Trạm nghỉ bên đường

Đã chốt hướng D. URL ứng dụng: `/phrases` · Role Student.

[Mở mockup](phrases-d-mockup.html). File triển khai thiết kế: `phrases.css`, `phrases.js`. Các hướng A/B/C/E/F và trang so sánh đã xóa.

## Bố cục và tương tác

Một phiên ôn nổi bật giữa cảnh của vùng, mascot nằm trong khung cảnh; thẻ nội dung trắng ở theme sáng, tối theo palette chung. Sáu vùng có ảnh ngày/đêm riêng. Mobile đưa mascot lên cạnh phần giới thiệu, thẻ ôn nằm dưới; bộ sưu tập thu gọn mặc định.

Card ôn nhấn cụm tiếng Anh, đặt nút nghe cạnh cụm và tô đậm cách dùng trong câu mẫu. Phần tự luyện nằm dưới đường phân cách. [Ảnh card](previews/phrases-d-study-card.png).

Mở nghĩa và câu mẫu → tự nói một câu → Chưa nhớ / Nói được. Tiến trình là số cụm đã ôn, không phải điểm. Bộ sưu tập có tìm kiếm, lọc, mở ví dụ và nghe cụm. Giữ trạng thái mở bộ sưu tập, tìm kiếm và bộ lọc khi chuyển thẻ. Tìm không thấy có nút xóa điều kiện. Sáu trạng thái duyệt: có dữ liệu, tải, trống, xong hôm nay, lỗi tải, lỗi lưu. Lỗi lưu giữ nguyên thẻ và thao tác để thử lại.

## Bàn giao FE

- Dữ liệu fixture: 8 cụm, 3 cụm đến hạn, không lưu qua reload. Toolbar chỉ dùng duyệt thiết kế. Không ghi âm, không chấm điểm.
- API hiện có: GET `/api/v1/me/phrases`, POST `/api/v1/me/phrases/review` với `{key, remembered}`. Dùng tổng số, lịch ôn, due và learned từ server; khóa thao tác khi request đang lưu, chỉ chuyển thẻ sau thành công. Không biến số 3 của fixture thành hạn mức sản phẩm.
- Đã thuộc từ box >= 3; tự đánh giá Chưa nhớ cần cập nhật lại box theo server. Mockup chỉ minh họa phiên, chưa đồng bộ thuật toán đầy đủ.
- Thay shell mockup bằng base/menu ứng dụng và xác minh mục active. Liên kết sản phẩm dùng route thật localhost:8000; dữ liệu mẫu không thể mở báo cáo thật.
- SpeechSynthesis phụ thuộc thiết bị và giọng cài sẵn. Có thông báo khi không hỗ trợ/lỗi; chưa kiểm chứng chất lượng tiếng đọc.
- Search/filter và ẩn nghĩa trước khi ôn là đề xuất UX mới. Không có request/API thật trong mockup.

## Kiểm chứng

Chromium: 84 tổ hợp (7 kích thước 320/390/650/768/1024/1440/1920 × sáng/tối × 6 trạng thái), kiểm tra không tràn ngang cả khi mở bộ sưu tập, lỗi lưu giữ nguyên cụm, tự đánh giá và hoàn tất phiên, tìm rỗng/xóa điều kiện, giữ bộ sưu tập khi chuyển thẻ. Đã decode mascot của cả 6 vùng, không có lỗi JavaScript. Node syntax và diff whitespace check đạt. Ảnh full-page trong `previews/`; thanh điều hướng fixed có thể nằm giữa ảnh full-page do cách trình duyệt chụp, trên màn hình thật nó bám đáy viewport. Chưa kiểm thử API, tiếng đọc thật hoặc thử nghiệm người dùng.
