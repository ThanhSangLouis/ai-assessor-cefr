# Kết quả cá nhân — bản bàn giao FE

- URL: `/my-progress` · role Student.
- Người dùng đã chốt **B2 · Hành trình kẹo ngọt**, bao gồm sáu vùng và hai chế độ sáng/tối.
- [Mở mockup đã chốt](passport-candy-mockup.html).
- [Hướng dẫn triển khai và nghiệm thu](handoff.md).

| File | Vai trò |
| --- | --- |
| `passport-candy-mockup.html` | Mockup duy nhất; mở trực tiếp trong trình duyệt |
| `passport-refinements.css` | Bố cục hộ chiếu, responsive, sáu palette sáng/tối |
| `passport-refinements.js` | Dữ liệu mẫu, phân trang, chọn bài, tab và trạng thái |
| `passport-shell.css` / `passport-shell.js` | Navigation mô phỏng trong mockup; app thật kế thừa shell chung |
| `handoff.md` | Quyết định thiết kế, ánh xạ dữ liệu, giới hạn và checklist |

Đã xóa các phương án và snapshot cũ theo yêu cầu chốt màn hình. Chưa triển khai vào ứng dụng hoặc nối API. Các bộ chọn trên cùng chỉ phục vụ review, không thuộc UI sản phẩm.

## Kiểm tra bản bàn giao

Chromium: 168 tổ hợp theme/width/số bài/trạng thái không tràn ngang hoặc lỗi JS; 12 cặp cảnh ngày/đêm tải mascot được. Phân trang 23 bài đến trang cuối, chọn dấu, hai tab và drawer/Escape hoạt động. Liên kết và asset cục bộ tồn tại; không còn tham chiếu tới mockup đã xóa trong HTML/Markdown thiết kế. Cú pháp hai file JS và `git diff --check` hợp lệ. Chưa kiểm thử tích hợp API/app thật.
