# Khu giảng viên: thế giới "Thời khoá biểu khoa"

Thiết kế cho mọi trang giảng viên thấy: hàng đợi duyệt (`/review`), duyệt một bài (`/review/{id}`), thống kê lớp (`/review/stats`), thống kê luyện tập (`/teach/insights`), lộ trình và soạn bài (`/teach`, `/teach/lessons/{id}`), đề đánh giá (`/teach/tasks`), lớp học (`/teach/classes`) và báo cáo bài nói khi giảng viên mở (`/report/{id}`). Trang quản trị dùng chung thế giới này, xem [../admin/README.md](../admin/README.md).

Chọn ngày 11/11/2026 qua vòng chọn hướng của Impeccable (máy bốc hướng "Thời khoá biểu khoa", chủ dự án giữ). Ràng buộc chủ dự án đặt: giữ cam thương hiệu và Roboto/Poppins; các quy tắc giao diện khác được làm lại.

## Ý tưởng

Việc của giảng viên xếp như thời khoá biểu dán ở bảng tin khoa: tờ kẻ ô trắng trên nền lạnh, thanh bên màu mực xanh, sáu màu band A1–C2 mang cùng một nghĩa trên mọi trang. Cam dùng cho việc cần làm tiếp, mục đang chọn, vạch "bây giờ" và mọi tiêu đề (Poppins đậm, cam như trang chủ — chủ dự án yêu cầu 11/11/2026); chữ thường, bảng và số liệu giữ màu mực.

## Thành phần chính

| Thành phần | Ở đâu | Quy tắc |
|---|---|---|
| Hàng đợi dạng tuần | `/review`, nút Tuần/Bảng | Cột là 7 ngày gần nhất và "Cũ hơn"; mỗi bài chờ là một khối màu theo band của đề, đặt theo giờ nộp, cao theo độ dài bản ghi. Khối đặc là đang chờ, viền đứt là có người đang xem, gạch chéo là chờ quá 3 ngày. Vạch cam là giờ hiện tại, nhãn nằm ở cột giờ. |
| Dải bản ghi | `/review/{id}`, dưới trình phát | Mỗi dấu dài đúng thời lượng khoảnh khắc nó đánh dấu (ngừng 1,6 giây là 1,6 giây trên dải); bấm để nghe. |
| Thanh band | `/review/stats` | Một thang A1–C2, mỗi band một màu; band trống vẫn giữ hàng của nó. |
| Chip band | mọi trang | `data-band="B1"` đặt màu band; dùng cho bảng, lộ trình, lớp, báo cáo. |
| Nút | mọi trang | Một nút cam cho việc chính; các nút khác nền trắng viền; thao tác phá huỷ chỉ có viền đỏ và đứng tách riêng. |

Màu band (giao diện sáng): A1 `#4a6cc9`, A2 `#2a7a89`, B1 `#3a7d52`, B2 `#85650b`, C1 `#b04a6c`, C2 `#6c4fb5`. Giao diện tối dùng bản sáng hơn với chữ sẫm.

## Tệp

- [staff-world-mockup.html](staff-world-mockup.html): bản phác khung nhìn đầu đã chọn (1440 × 900).
- `evidence/`: ảnh chụp bản build thật trên dữ liệu demo, 1440 px sáng/tối và 390 px.
- Code: `src/aicefr/api/static/staff.css` (chỉ nạp cho vai trò giảng viên và quản trị, phạm vi `body.staff`), `queue.js` (dạng tuần), `review_one.js` (dải bản ghi), `cohort_stats.js` (thanh band).

## Không làm

- Không đặt dòng chữ nhỏ phía trên tiêu đề, không sọc màu bên trái thẻ hay mục điều hướng.
- Không tô nền cam cho thẻ; không đặt ô biểu tượng cạnh tiêu đề trang.
- Không tô một band bằng màu nào khác màu band của nó.
