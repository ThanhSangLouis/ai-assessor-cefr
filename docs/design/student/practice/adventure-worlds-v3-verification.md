# Sáu vùng ngày/đêm v3 — kiểm chứng cuối 06/11/2026

Bản làm việc trên nền commit `1d03967`, chưa commit. Đã tích hợp vào `/practice` sau khi chủ dự án duyệt bản rừng. Đây là tự kiểm chứng bằng Chromium/Playwright, không thay quyết định nghiệm thu của chủ dự án.

## Kết quả

| Kiểm tra thực chạy | Kết quả |
| --- | --- |
| `node --test tests/js/practice_adventure.test.cjs` | 25/25 |
| `.venv/bin/python -m pytest tests/test_practice_ui.py -q --no-cov` | 16/16 |
| `tools/check_adventure_worlds.py` | 360 trường hợp: sáu vùng × hai theme × 1/3/5/15/50 bài × 390/1440/1920px × DPR 1/2 |
| `tools/check_adventure_worlds.py --widths 2560 --counts 1 50 --output /tmp/adventure-worlds-wide-checks` | 48 trường hợp; chọn nguồn 1536px ở cả DPR 1/2 |
| `tools/audit_adventure_display.py` | 135 trường hợp: 58 theme/chiều rộng, 36 dữ liệu ngắn/dài, 27 editor/popup, 10 font lớn/cửa sổ thấp, 4 lưu lựa chọn theme |
| `tools/check_adventure_browser.py` | 40 tổ hợp: 0/1/2/5/12/13/30/100 bài mỗi phần × 1440/1024/700/390/320px |
| Gallery mở bằng file:// | 12 tổ hợp: sáu vùng × 390/1440px, kiểm ảnh ngày/đêm và không tràn ngang |
| Ruff ba tool mới/cập nhật, `git diff --check` | Đạt |

Kiểm tra cảnh xác minh đúng tài nguyên được tải theo theme/DPR, tỉ lệ nguồn, mép đầu không fade, phủ kín chiều cao và ảnh không đổi mức phóng theo số bài. Có đoạn A/B riêng, chỉ mask tại chỗ nối. Kiểm tra giao diện đo mascot và nút học, header/tiến độ, card, editor, từng nút popup, scrollWidth, focus Hủy và Escape. Không ghi tiến độ hoặc xóa lộ trình người học; dùng tài khoản demo và chặn GET bằng fixture.

R01 đã sửa bằng `width:auto; min-width:0` riêng `.bp-dialog-actions button`. Kiểm tra tái hiện trước sửa thất bại ở 320px, sau sửa qua 12 tổ hợp popup sáng/tối ở 320/390/600/640/701/1440px; audit thực tế cũng qua các trường hợp popup và font lớn. Lượt kiểm desktop rộng ban đầu gặp race trong harness khi sửa trực tiếp data-theme cùng lúc OS media event; chuyển sang API lưu preference thật và chờ đúng ảnh. Lượt chạy lại 48 trường hợp hoàn tất, không thay expected về theme.

Không có finding bố cục hoặc lỗi JavaScript trong các lượt hoàn tất. Đã xem ảnh tổng thể sáu vùng ở sáng/tối và section ngắn/dài; các vùng có palette và địa hình riêng. Nguồn và prompt bằng built-in imagegen, xuất WebP bằng Pillow: [manifest mới](adventure-worlds-v3-prompts.json), [manifest rừng](adventure-forest-v3-prompts.json). Có 24 tranh, 120 export; không upscale.

## Bằng chứng

- [Gallery sáu vùng, chọn số bài](adventure-worlds-day-night.html).
- [Ảnh tổng hợp cảnh ngày/đêm](evidence/worlds-v3-2026-11-06/worlds-day-night-contact.webp).
- Toàn trang mobile: [sáng](evidence/worlds-v3-2026-11-06/six-worlds-light-390.webp), [tối](evidence/worlds-v3-2026-11-06/six-worlds-dark-390.webp).
- Toàn trang desktop: [sáng](evidence/worlds-v3-2026-11-06/six-worlds-light-1280.webp), [tối](evidence/worlds-v3-2026-11-06/six-worlds-dark-1280.webp).
- Dữ liệu đo: [360 trường hợp](evidence/worlds-v3-2026-11-06/terrain-checks.json), [48 trường hợp desktop rộng](evidence/worlds-v3-2026-11-06/wide-terrain-checks.json), [audit](evidence/worlds-v3-2026-11-06/display-audit.json).

## Giới hạn

Ảnh gốc rộng 1536px. Tại 1920px/DPR 2, bản đồ rộng khoảng 1241 CSS px, chỉ có 0.619 pixel nguồn/device pixel; desktop 2560px còn vượt mật độ nguồn nhiều hơn. Đã ưu tiên nguồn lớn nhất có thật, không coi resize là tạo thêm chi tiết. R02 vẫn là giới hạn đã biết. Chưa kiểm trên Safari/Firefox hoặc thiết bị thật, chưa đo hiệu năng mạng/CPU trên điện thoại. Bản đồ dùng hai đoạn luân phiên và chưa virtualization; kiểm đến 100 bài/phần không phải cam kết hiệu năng vô hạn.
