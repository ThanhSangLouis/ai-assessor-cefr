# Quy trình thực nghiệm phản hồi — D040

| Thuộc tính | Giá trị |
| --- | --- |
| Câu hỏi | Nhận xét gắn bằng chứng (báo cáo đầy đủ) có giúp người học tăng điểm và luyện nhiều hơn so với chỉ xem điểm và mức không? |
| Thiết kế | Thực nghiệm ngẫu nhiên hai nhóm song song, trong một lớp, thăm dò |
| Yêu cầu | FR-77, FR-78, BR-37 (`docs/srs/SRS.md` mục 3.9j) |
| Duyệt | GVHD duyệt hướng làm (theo chủ dự án, 11/10/2026). Bản quy trình này cần GVHD xem trước khi mở thực nghiệm với sinh viên thật |
| Phiên bản | 1.0 · 11/10/2026 |

## 1. Người tham gia

- **Đủ điều kiện:** sinh viên có tài khoản đang hoạt động và **đang cho phép dùng dữ liệu cho nghiên cứu** ở trang Đồng ý (FR-33) tại thời điểm mở thực nghiệm. Không ai được chia nhóm khi chưa đồng ý.
- **Không đủ điều kiện:** giảng viên, quản trị viên, tài khoản bị khoá.
- **Thông tin trước khi tham gia:** giảng viên nói rõ với lớp rằng có thực nghiệm, có hai nhóm chia ngẫu nhiên, một nhóm tạm thời chỉ thấy điểm và mức, thời gian dự kiến, và có thể rời bất cứ lúc nào ở trang Tiến độ mà không ảnh hưởng gì tới việc học hay điểm của môn.
- **Cỡ mẫu:** một lớp 20–30 người. Đủ cho thăm dò, không đủ để khẳng định hiệu quả nhỏ; kết quả đọc theo khoảng tin cậy.

## 2. Can thiệp

| Nhóm | Báo cáo bài đánh giá trong thời gian chạy |
| --- | --- |
| Phản hồi đầy đủ | Như mọi người học: điểm, mức, khoảng; nhận xét; bằng chứng trên bản ghi; ưu tiên; khía cạnh nên luyện trước và nút luyện ngay; chỉ số |
| Chỉ điểm | Điểm, mức và khoảng. Phần còn lại do máy chủ giữ lại, trang báo cáo nói vì sao |

Bài học, luyện tập, thành tựu và mục phát âm (D039) giống nhau ở hai nhóm. Giảng viên luôn thấy đủ.

## 3. Chia nhóm

Ngẫu nhiên cân bằng: danh sách người đủ điều kiện được xáo theo một hạt giống ngẫu nhiên, rồi chia luân phiên; hai nhóm lệch nhau tối đa một người. Hạt giống được lưu cùng thực nghiệm và ghi vào nhật ký, nên phép chia tái lập được.

## 4. Lịch

1. **Đang chạy** — tối thiểu `min_days` ngày (mặc định 14), khuyến nghị 3–4 tuần. Người học làm bài đánh giá như bình thường; đề nghị ít nhất một bài ở tuần đầu và một bài ở tuần cuối.
2. **Khảo sát** — quản trị viên chuyển giai đoạn; người tham gia trả lời 5 câu ở trang Tiến độ. Phản hồi **vẫn giữ lại** trong giai đoạn này: khảo sát hỏi về thực nghiệm như người học đã trải qua, và người vừa được trao hết nhận xét sẽ trả lời về một điều khác. Điểm của bài làm sau thời điểm chuyển sang khảo sát không tính vào kết quả.
3. **Đã đóng** — quản trị viên đóng; mọi người thấy lại phản hồi đầy đủ; kết quả và CSV vẫn đọc được.

## 5. Đo lường

- **Kết quả chính:** mức tăng điểm = điểm bài đánh giá cuối cùng cách bài đầu tiên (trong giai đoạn đang chạy, tức trước khi chuyển sang khảo sát) ít nhất `min_days` ngày, trừ điểm bài đầu tiên. Điểm là ước lượng của máy.
- **Kết quả phụ:** số lần luyện bài học trong thời gian thực nghiệm; năm câu khảo sát Likert 1–5: biết cần luyện gì, hiểu kết quả, tin kết quả, đã luyện thêm, muốn dùng tiếp.
- **Phân tích:** chênh lệch mức tăng trung bình "Phản hồi đầy đủ − Chỉ điểm", khoảng tin cậy bootstrap 95 % (2000 lần, lấy lại người trong từng nhóm, hạt giống của thực nghiệm), Hedges g. Người đã rời hoặc không còn đồng ý bị loại khỏi mọi con số. Không có p-value làm kết luận chính.
- **Đọc kết quả:** khoảng nằm trọn trên 0 là có dấu hiệu nhận xét giúp tăng điểm; khoảng chứa 0 là chưa thấy khác biệt, không phải bằng chứng rằng nhận xét vô ích. Mọi báo cáo kết quả phải ghi cỡ mẫu từng nhóm và số người bị loại.

## 6. Đạo đức và dữ liệu

- Không ai bị giữ phản hồi mà không biết: trang báo cáo nói rõ vì sao và chỉ cách rời.
- Rời thực nghiệm, rút đồng ý nghiên cứu, ký lại không cho nghiên cứu, bị xoá dữ liệu (FR-35): người học ra khỏi thực nghiệm ngay và nhận lại phản hồi đầy đủ.
- Xoá dữ liệu cũng xoá dòng tham gia và câu trả lời khảo sát.
- CSV xuất theo mã P001…, không bút danh, không mã tài khoản, không bản chép lời, không audio. Không đưa CSV lên kho công khai.
- Nếu giữa chừng thấy nhóm "Chỉ điểm" bị thiệt rõ (ví dụ nhiều người phàn nàn không biết luyện gì), GVHD có thể dừng sớm: chuyển sang khảo sát.

## 7. Thao tác

1. Kiểm tra số sinh viên đã đồng ý nghiên cứu (tab Xoá dữ liệu → Xuất tập dữ liệu nghiên cứu cho biết số người).
2. Vào `/admin/study`, đặt tên và số ngày tối thiểu, bấm **Chia nhóm và bắt đầu**.
3. Hết thời gian chạy: **Chuyển sang khảo sát**; nhắc lớp trả lời.
4. Đủ khảo sát: **Đóng thực nghiệm**; **Xem kết quả**, tải **CSV** để phân tích thêm.
