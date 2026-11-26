## Student · Ba màn đang chờ duyệt

Luyện nói lại, Luyện phát âm và Luyện đoạn đọc chưa được người dùng duyệt. Chưa dùng các mockup này làm thiết kế triển khai đã chốt.

| Ưu tiên | Màn hình | URL | Hướng cải tiến |
| --- | --- | --- | --- |
| 1 | [Luyện nói lại](retell/retell-mockup.html) | `/retell/{response_id}` | Dùng bố cục lesson C, phân biệt rõ từng lượt nói, bản ghi và phản hồi. |
| 2 | [Luyện phát âm](drill/drill-mockup.html) | `/drill/{response_id}` | Từ cần luyện nổi bật, ghi âm và phản hồi theo từ; mascot hướng dẫn ngắn. |
| 3 | [Luyện đoạn đọc](passage/passage-mockup.html) | `/passage` | Đoạn đọc thoáng, từ trọng tâm dễ nhận biết; vùng ghi âm đồng bộ lesson. |

## Student · Đã có hướng thiết kế

| Màn hình | URL | Trạng thái |
| --- | --- | --- |
| [Lộ trình học](practice/) | `/practice` | Đã triển khai trên nhánh `fe`. |
| [Bài học](lesson/README.md) | `/practice/lessons/{lesson_id}` | Mockup C đã chốt. |
| [Nộp bài đánh giá](submit/README.md) | `/` | Mockup B đã chốt. |
| [Tiến độ cá nhân](my-progress/README.md) | `/my-progress` | Đã chốt B2 · Hộ chiếu giọng nói. |
| [Bài đã nộp](my-responses/README.md) | `/my-responses` | Đã chốt C · Nhật ký nộp bài. |
| [Tiến trình xử lý](progress/README.md) | `/progress/{response_id}` | Đã chọn A · Trạm chờ trong cảnh, có ghi chú bàn giao. |
| [Sổ cụm từ](phrases/README.md) | `/phrases` | Đã chốt D · Trạm nghỉ bên đường, có card ôn phiên bản cuối. |

`/my-classes` và `/credits` có route trên `origin/main`. Hai màn này ngoài danh sách redesign đã lên lịch và chưa được đánh giá giao diện trong lượt này.
