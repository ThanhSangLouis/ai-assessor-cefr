# Sidebar, responsive và mốc chiến thắng — 06/11/2026

Bản làm việc chưa commit trên nền `1d03967`. Tự kiểm chứng bằng Chromium, không thay nghiệm thu của chủ dự án.

- Sidebar dùng chung kiểu chữ, chiều cao 44px, khoảng cách và màu cam nhẹ; bỏ CSS ghi đè riêng của roadmap.
- Điều hướng mobile dùng chung trong base template cho học viên; active theo trang, hiện đến 900px và có khoảng đệm cuối nội dung.
- Sửa max-width trên mobile: không trừ chiều rộng sidebar khi drawer đã ẩn, bao gồm workspace nộp bài. Lưới thành tựu co theo chiều rộng khả dụng.
- Mobile: tên lộ trình/trạng thái và tiến độ tách hai hàng; card học tiếp có nút toàn hàng và chữ dễ đọc hơn; header từng vùng có ba cột ổn định, số đếm rút gọn.
- Bài cuối **mỗi phần** dùng nút tròn cúp vàng nhạt trên cảnh. Bỏ cúp lớn bên ngoài. Trạng thái khóa vẫn có khóa nhỏ và popup không có liên kết học; số bài, thứ tự và BE không đổi.

## Kiểm tra thực chạy

| Kiểm tra | Kết quả |
| --- | --- |
| Tái hiện sidebar trước sửa (`/tmp/repro_navigation.py`) | Thất bại: font/padding khác giữa practice và ba trang khác |
| `tools/check_student_navigation.py` | 64 lượt: 4 trang × 8 chiều rộng 320/390/700/768/900/1024/1440/1920 × sáng/tối; không tràn ngang, nav active đúng, drawer mở/Escape, sidebar cùng kích thước |
| Trong lượt trên | Mỗi phần đúng một cúp (6 phần), không có cúp ngoài, popup cúp khóa không có link học; heading không đè trạng thái ở mobile |
| `tools/audit_adventure_display.py` | 135 trường hợp; findings rỗng, không lỗi JavaScript |
| `tools/check_adventure_browser.py` | 40 tổ hợp 0/1/2/5/12/13/30/100 bài × 1440/1024/700/390/320; không lỗi JavaScript |
| `node --test tests/js/practice_adventure.test.cjs` | 25/25 |
| `.venv/bin/python -m pytest tests/test_practice_ui.py -q --no-cov` | 16/16; cập nhật assertion cúp cũ theo giao diện mới |
| Ruff tool mới, JS syntax hai file, `git diff --check` | Đạt |

Bộ kiểm dùng tài khoản demo, chặn GET học bằng fixture, không lưu tiến độ/lộ trình/cài đặt tài khoản. Đã xem ảnh desktop và mobile ở cả sáng/tối. Safari/Firefox và thiết bị thật: NOT_RUN. Kiểm tra nội dung chi tiết các trang giảng viên/quản trị: NOT_RUN; sidebar dùng chung nhưng không thêm thanh tab học viên cho các vai trò này.

Bằng chứng: [kết quả điều hướng](evidence/navigation-2026-11-06/navigation-results.json), [audit roadmap](evidence/navigation-2026-11-06/roadmap-audit.json), [mobile sáng](evidence/navigation-2026-11-06/light-390.webp), [mobile tối](evidence/navigation-2026-11-06/dark-390.webp), [desktop sáng](evidence/navigation-2026-11-06/light-1440.webp), [desktop tối](evidence/navigation-2026-11-06/dark-1440.webp).

## Cập nhật huy hiệu sau khi chốt mẫu

Áp dụng mẫu 7 từ `reward-state-options.html` vào bài cuối mỗi phần. Chưa mở khóa dùng xanh lá nhạt và khóa; đã mở khóa dùng cam đậm; bài tiếp theo/đang học giữ nhãn Bắt đầu/Học tiếp và vòng sáng. Hoàn thành dùng phương án A đang được chọn trong bản thử khi người dùng nói “chốt”: xanh lá tươi, dấu tick nằm trên thân cúp thay ngôi sao. Không thêm node hay đổi điều kiện học. Các phần và theme dùng cùng quy tắc trạng thái.

Điều chỉnh theo phản hồi tiếp theo: trạng thái hoàn thành chỉ đổi màu xanh, giữ ngôi sao trên cúp như các trạng thái khác; bỏ dấu tick trên thân cúp.

Bản thử mới cho cúp chưa mở khóa: bạc xanh, viền liền, dấu khóa tích hợp trên thân cúp thay ngôi sao; bỏ ô khóa bên ngoài. Mở khóa vẫn cam, hoàn thành vẫn xanh.

Chốt điều chỉnh tiếp: cúp chưa mở khóa giữ màu bạc xanh hiện tại, trả lại ngôi sao trên thân cúp, không hiển thị biểu tượng khóa. Trạng thái khóa vẫn được mô tả bằng aria-label và popup không có liên kết học.


### Node C và đường sao 05 — giãn khoảng cách

Áp dụng bộ huy hiệu C và đường sao 05, đồng bộ màu khóa của cúp cuối theo theme. Tăng khoảng cách dọc thêm 12px: mobile 84 → 96px, desktop 108 → 120px; giữ kích thước node. Giữ vùng bấm ổn định khi hover.

Kiểm chứng sau chỉnh spacing: Node tests 25/25, pytest UI 16/16. Browser audit không thực hiện được vì localhost:8000 từ chối kết nối; chưa kết luận audit responsive cuối cùng.
