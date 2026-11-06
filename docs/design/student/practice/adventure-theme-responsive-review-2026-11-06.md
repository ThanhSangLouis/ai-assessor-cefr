# Review theme và responsive — 06/11/2026

Phạm vi: bản `/practice` hiện hành, gồm sáu vùng, rừng ngày/đêm v3, mascot, editor lộ trình, popup bỏ lộ trình, cúp và điều hướng mobile. Tự review bằng Chromium/Playwright; không có reviewer độc lập. Chưa thay đổi source giao diện trong lượt review.

## Findings

### R01 — P1: Popup bỏ lộ trình cắt mất nút xác nhận trên mobile

- Tái hiện: có lộ trình, mở editor, bấm icon xóa ở viewport 320/390/600px, cả light và dark. Popup không tràn ra ngoài viewport, nhưng các nút bên trong tràn ngang; một phần lớn nút “Bỏ lộ trình” bị cắt mất.
- Bằng chứng: [ảnh 320px light](evidence/theme-responsive-2026-11-06/roadmap-review-dialog-320-light.png), [ảnh dark](evidence/theme-responsive-2026-11-06/roadmap-review-dialog-320-dark.png), [số đo 16 trường hợp](evidence/theme-responsive-2026-11-06/dialog-measurements.json). Tại 320px: clientWidth 280px, scrollWidth 351px. Tại 390px: 350px so với 421px. Kiểm tra 700/701/768/1024/1440px không tái hiện.
- Nguồn: `src/aicefr/api/static/style.css:7346` áp dụng `button { width:100% }` ở max-width 640px. `src/aicefr/api/static/band_plan.css:300` đặt nút Hủy `flex:0 0 auto`, nên nút giữ nguyên toàn bộ chiều rộng hàng và đẩy nút còn lại ra ngoài. CSS của popup chưa reset width/min-width của hai nút.
- Kỳ vọng: hai hành động đều hiển thị đầy đủ và bấm được trong popup ở mọi kích thước hỗ trợ; nội dung popup không có overflow.
- Hướng sửa: giới hạn trong `.bp-dialog-actions`, reset width về auto, min-width/shrink hợp lý hoặc dùng grid hai cột; giữ nguyên CSS button dùng chung. Kiểm lại 320/390/600/640/641px, hai theme và chữ lớn, đo cả nút bên trong, không chỉ khung dialog.
- Trạng thái: OPEN. Chưa sửa UI trong lượt review.

### R02 — P2, giới hạn đã biết: Nguồn rừng chưa đủ native 2× trên desktop rộng

- Nguồn v3 rộng 1536px; tại viewport 1920, bản đồ rộng 1241 CSS px, DPR 2 cần 2482px. Hiện chỉ có 0.619 pixel nguồn/device pixel. Đã cải thiện so với nguồn cũ, nhưng chưa thể khẳng định nét native 2× ở mọi desktop.
- Hướng xử lý tiếp: nguồn rộng hơn hoặc ghép các mảnh chi tiết ở độ phân giải thực; không upscale ảnh rồi gọi là tăng chi tiết.

## Phần đã kiểm

- 24 mốc chiều rộng từ 320 đến 2560px ở light/dark; thêm các mốc dùng theme hệ thống. Không thấy tràn ngang ổn định của trang, mascot che nút hoặc tiêu đề vùng đè tiến độ.
- 1/5/100 bài × 6 chiều rộng × 2 theme; form mở rộng ở 9 chiều rộng × 3 chế độ theme; font lớn và cửa sổ thấp; focus nút Hủy, Escape và lưu lựa chọn theme. Một lượt chuyển từ desktop rộng xuống 320px báo overflow ở mốc chờ 100ms; kiểm lại sau 300ms không tái hiện overflow ổn định. Không dùng kết quả này để phủ nhận lỗi nội dung popup R01.
- Chạy lại `tools/check_forest_day_night.py`: 60 trường hợp đạt (1/3/5/15/50 bài, 390/1440/1920px, DPR 1/2, light/dark); kiểm system dark và explicit light override; ảnh đầu không fade, đoạn cảnh không đổi tỷ lệ theo số bài và không có khe hở. Không có lỗi JavaScript trong các lượt hoàn tất.
- Ảnh chụp bổ sung editor 320px: [dark](evidence/theme-responsive-2026-11-06/roadmap-review-plan-320-dark.png).
- Test harness rừng được sửa chữ ký callback route (Playwright truyền cả Route và Request), không sửa expected của giao diện. Ruff đạt. Harness audit cũ vẫn kiểm bộ lọc 52% ở pseudo-element đã bỏ; lượt rà dùng bản runtime `/tmp/audit_roadmap_review.py` kiểm đúng ảnh rừng ngày/đêm và filter của vùng legacy, không coi assertion cũ là lỗi sản phẩm.

## Kết luận

Chưa đạt toàn bộ responsive vì R01. Các phần bố cục còn lại được kiểm chưa phát hiện lỗi ổn định mới. Năm vùng ngoài rừng vẫn dùng ảnh ngày giảm sáng khi dark — đúng phạm vi thử nghiệm hiện tại, chưa phải bộ cảnh đêm hoàn chỉnh. Chưa kiểm Safari/Firefox hoặc thiết bị vật lý; chưa định lượng độ tương phản của toàn bộ text trên trang. Không ghi thay quyết định nghiệm thu của người dùng.

## Cập nhật sau khi được giao hoàn thiện

R01 đã sửa trong lượt triển khai tiếp theo: reset width/min-width riêng các nút popup. Kiểm tra tái hiện trước sửa thất bại ở 320px; sau sửa qua kiểm tra nội dung và từng nút trong popup, cả sáng/tối và font lớn. Kết quả cuối, ảnh và ma trận nằm tại `adventure-worlds-v3-verification.md`. Phần findings phía trên giữ nguyên như hồ sơ review ban đầu.

Cả sáu vùng đã có tranh đêm riêng, thay toàn bộ xử lý giảm sáng legacy. R02 vẫn là giới hạn độ phân giải thực của nguồn, không ghi nhận đã giải quyết bằng resize. Desktop rất rộng đã ưu tiên bản 1536px thay vì bản 1280px.
