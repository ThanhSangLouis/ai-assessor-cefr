# Kiểm tra theme và responsive roadmap

Ngày: 06/11/2026. Phạm vi: `/practice`, sáu vùng phong cảnh, node/card bài học, mascot, trình chỉnh lộ trình và popup bỏ lộ trình. Kiểm tra bằng Playwright Chromium trên máy phát triển; fixture GET không ghi tiến độ hoặc thay lộ trình thật.

## Các lỗi đã sửa

| Vấn đề | Thay đổi |
| --- | --- |
| Mascot chồng node ở một số độ rộng 701–1200px do sidebar làm hẹp roadmap | Dùng một cột trong khoảng này, chuyển các card thông tin lên trên, dành đủ chiều rộng cho đường học |
| Theme tối làm cảnh bạc màu vì giảm opacity trên nền sáng | Giữ opacity, giảm độ sáng/bão hòa ảnh và dùng nền tối có sắc độ theo vùng |
| Theme tối hệ thống khác theme tối chọn trực tiếp | Cả hai dùng cùng token nền, ảnh và đường |
| Icon bài chưa học bị tối trên nền node tối | Dùng màu chữ và viền của theme hiện tại |
| Nhãn cấp độ nhạt, chữ trắng thiếu tương phản | Tăng độ đậm nền nhãn; kiểm tra tương phản tối thiểu 4.5:1 cho cả sáu vùng |
| Nút Hủy trong dialog dùng nền sáng cố định và chữ sáng của theme tối | Dùng token nền/viền theo theme; áp dụng tương tự cho nút disabled và hành động kiểm tra trình độ |

## Ma trận có thể chạy lại

```sh
.venv/bin/python tools/audit_adventure_display.py
.venv/bin/python tools/check_adventure_browser.py
node --test tests/js/practice_adventure.test.cjs
.venv/bin/python -m pytest tests/test_practice_ui.py -q --no-cov
```

- Theme sáng/tối trực tiếp: 320, 360, 390, 430, 600, 699, 700, 701, 768, 899, 900, 901, 1024, 1099, 1100, 1101, 1200, 1250, 1280, 1366, 1440, 1600, 1920, 2560px.
- Theme sáng/tối hệ thống: 390, 701, 1101, 1440, 1920px; kiểm tra thêm lựa chọn trực tiếp được ưu tiên hơn OS và được giữ sau reload.
- Dữ liệu: 1, 5, 13, 100 bài mỗi cấp độ trong audit; bộ kiểm tra bố cục có thêm 0, 2, 12, 30 bài.
- Editor mở và dialog: 320, 390, 701, 1024, 1200, 1280, 1440, 1920, 2560px ở sáng, tối và tối hệ thống. Chỉ mở và hủy, không xác nhận bỏ lộ trình.
- Chữ lớn và cửa sổ thấp: 1366×600, 1366×768, 1920×1080, 390×667, 683×384; kiểm tra dialog nằm trong viewport và focus vào nút Hủy.
- Kiểm tra tràn ngang, chồng mascot/node, chồng tiêu đề/tiến độ, card nằm trong viewport, tỉ lệ nền và sự ổn định chiều dài đường khi mở card.

Audit ghi kết quả chi tiết và screenshot vào `/tmp/adventure-display-audit/`; bộ kiểm tra dữ liệu ghi screenshot vào `/tmp/adventure-checks/`.

Kết quả lượt kiểm tra cuối: 58 tổ hợp theme/độ rộng, 36 trường hợp dữ liệu,
27 trường hợp editor/dialog, 10 trường hợp chữ lớn/cửa sổ thấp và 4 trường hợp
lưu theme sau reload đều qua; không có finding hình học hoặc lỗi JavaScript
trong các trường hợp này. Bộ test bổ sung: 19 Node tests, 16 pytest đều qua.
Số đo và ma trận chi tiết được lưu trong
[adventure-display-verification.json](adventure-display-verification.json).

## Giới hạn

Chưa kiểm tra trên thiết bị vật lý, Firefox hoặc Safari. Kiểm tra tương phản tự động tập trung vào nhãn cấp độ; không coi đây là chứng nhận accessibility cho toàn website. Thẩm mỹ vẫn cần chủ dự án xem trực tiếp và nghiệm thu.
