# Bàn giao FE — Kết quả cá nhân

## Thiết kế được chốt

Nguồn chuẩn duy nhất: [passport-candy-mockup.html](passport-candy-mockup.html), B2 Hành trình kẹo ngọt. Người dùng chốt bố cục và sáu theme; đồng hoa là chuẩn màu đã duyệt, đặc biệt bản tối. Không dùng lại các hướng thử trước đây. Đây là bàn giao thiết kế, chưa phải màn ứng dụng đã triển khai.

Giữ thứ bậc: nhận diện hành trình và mascot → hộ chiếu đánh giá/luyện tập → thông tin bài được chọn → phần phụ. Ưu tiên số liệu, giảm câu dẫn khi đưa dữ liệu thật vào. Không thêm hàng dấu mốc/tổng quan trùng với hộ chiếu. Hộ chiếu có sáu dấu mỗi trang, bản mẫu mặc định 23 bài để xem bốn trang. Không render toàn bộ lịch sử không giới hạn.

## Thành phần và dữ liệu

| Thành phần | Nguồn/ý nghĩa khi triển khai |
| --- | --- |
| Dấu đánh giá | Một bài có kết quả; ID ổn định, điểm tổng thể, ngày nộp và tên bài |
| Thứ tự | Thời gian nộp giảm dần, gồm giờ; dùng khóa phụ ổn định khi trùng thời gian |
| Số bài và phân trang | Tổng bài đánh giá thực tế, sáu bài/trang; lấy từ dữ liệu/API, không đếm trang hiện tại |
| Dấu được chọn | Bài đầu trang khi đổi trang; thông tin bên dưới phải cùng ID, một dấu active |
| Mở bài đã nộp | Khi triển khai dùng nhãn **Xem kết quả chi tiết** và dẫn đến báo cáo đúng ID; URL localhost trong mockup chỉ là placeholder |
| Điểm/band | Lấy kết quả đã lưu; không tự suy band từ điểm bằng công thức mới |
| Dấu luyện tập | Thành tựu không chấm điểm; số đếm và trạng thái độc lập với đánh giá |
| Xu hướng | Điểm bài thật theo thời gian, từ cũ sang mới, cùng thang 0–6; chưa đủ hai bài thì giải thích thay vì suy xu hướng |
| Gợi ý từ/thói quen | Mockup dùng fixture; chỉ hiển thị nếu có dữ liệu hỗ trợ, nếu không thì bỏ, không đưa khẳng định mẫu vào sản phẩm |

Bản mẫu chưa hiển thị điểm từng tiêu chí. Báo cáo bài chi tiết cần dữ liệu Range, Accuracy, Fluency, Coherence, Phonology cùng nhận xét/dẫn chứng hiện có của hệ thống. Không thay đổi rubric; Interaction giữ quy tắc nghiệp vụ hiện hành.

Các điểm, ngày, tiêu đề, 12 thành tựu và từ mẫu trong JS chỉ là fixture. Không dùng mảng tuần hoàn làm dữ liệu ứng dụng, không gửi fixture tới backend.

## Sáu vùng và theme

| Khóa | Vùng | Màu nhận diện |
| --- | --- | --- |
| `forest` | Rừng | Xanh lá, tối xanh khói |
| `volcano` | Núi lửa | Đỏ cam, tối mận khói với mực đào |
| `snow` | Tuyết | Xanh bạc, tối xanh chàm với mực xanh pastel |
| `river` | Sông | Xanh ngọc, tối xanh khói với mực ngọc nhạt |
| `desert` | Sa mạc | Vàng cát, tối tím khói với mực cát |
| `flowers` | Đồng hoa | Hồng tím đã chốt; mặc định khi chưa có nguồn vùng |

Token nằm trong `passport-refinements.css`, selector `data-world` và `data-theme`. Giữ màu đồng hoa đã duyệt. Mỗi vùng có palette sáng và tối riêng; không chỉ phủ đen ảnh ngày. Sidebar dùng màu chung, không đổi theo vùng. Vùng cảnh chỉ là trình bày, không làm thay đổi điểm hay thành tựu.

Tái dùng font và asset từ `src/aicefr/api/static/`: cảnh `{world}-{day|night}-a-v3-960.webp`, mascot `mascot-{world}-v3.webp`. Khi đưa vào app dùng URL static hiện có, không giữ đường dẫn tương đối của docs. Mockup dùng bộ chọn vùng; nguồn vùng trong app phải nối từ ngữ cảnh lộ trình hiện có, nếu không có thì dùng đồng hoa. Không thêm thiết lập tài khoản mới vì mockup.

## Shell, responsive và tương tác

Kế thừa `base.html` và navigation chung; không copy sidebar riêng vào trang thật. Hai file shell chỉ cho mockup độc lập. Sidebar desktop 256px, hàng 44px; breakpoint drawer 900px. Mục Lớp của tôi được đối chiếu main, local fe có thể chưa có; bám layout/phân quyền của revision triển khai. Lượt của tôi tuân theo cấu hình metered thực tế.

Mobile dùng hai cột tem, không tràn ngang, CTA đủ chỗ, tránh tab bar che nội dung. Cảnh/mascot không che điểm hoặc nút. Có focus nhìn thấy, chọn dấu bằng bàn phím, giữ/trả focus khi phân trang và đóng drawer; Escape đóng menu. Chế độ giảm chuyển động cần được tôn trọng.

Bỏ toolbar review, bộ chọn dữ liệu/theme/vùng, nút khung mobile và tài khoản giả khi triển khai. Theme dùng điều khiển chung của website. Đăng xuất mockup không gọi endpoint.

## Trạng thái

Có dữ liệu, chưa có bài, đang tải và tải lỗi phải tách biệt. Retry phải gọi lại nguồn dữ liệu thực tế. Tab luyện tập vẫn có thể xem khi đánh giá rỗng/lỗi; không để lỗi một nguồn làm mất nguồn còn lại. Với một bài không kết luận xu hướng. Khi tổng bài thay đổi cần kẹp trang và lựa chọn về ID hợp lệ.

## Kiểm chứng và tiêu chí bàn giao

Kiểm tra mockup cuối: hai theme, bảy chiều rộng 320/390/768/900/1024/1440/1920px, ba lượng bài 1/5/23, bốn trạng thái. Kiểm tra sáu vùng/mascot, phân trang tới trang cuối, chọn bài, hai tab, drawer/Escape và liên kết nội bộ. Kết quả cụ thể ghi ở README sau chạy cuối.

Khi FE tích hợp cần kiểm tra thêm API thật, timestamp/timezone, report theo đúng ID, dữ liệu rỗng/thiếu điểm/band, lỗi từng nguồn, navigation/phân quyền thật và mobile trên ứng dụng. Chưa thực hiện các kiểm tra tích hợp này trong task thiết kế. Không coi quyết định duyệt thiết kế là nghiệm thu implementation.
