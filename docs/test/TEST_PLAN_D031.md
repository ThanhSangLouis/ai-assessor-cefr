# Kế hoạch và kết quả kiểm thử D031 — Phông Roboto, logo mới, chiều sâu và chuyển động

| Thuộc tính | Giá trị |
| --- | --- |
| Tính năng | D031: phông Roboto tự phục vụ, logo và favicon mới, trang giới thiệu 3D, chiều sâu và chuyển động trên mọi trang, khối 3D dùng chung (đặc tả web 1.3, Đợt 12; W-NFR-2, W-NFR-3) |
| Phiên bản mã | nhánh `feat/ui-depth` |
| Người lập | Võ Thanh Sang |
| Ngày | 07/10/2026 |

## 1. Mục tiêu

1. **Không lỗi lặng lẽ.** Phần lớn D031 là một tệp CSS, và CSS hỏng mà không báo: tệp phông thiếu trong gói thì trang về Arial, thẻ tải trước lệch địa chỉ thì phông tải hai lần, trùng tên lớp thì logo méo, bộ lọc nền đặt sai chỗ thì thanh tab của điện thoại rời khỏi đáy màn hình. Mỗi chuyện đó có một test.
2. **Chuyển động là trang trí (W-NFR-3).** Người chọn giảm chuyển động không thấy gì chuyển động; hình 3D ẩn với trình đọc màn hình; không con số nào chỉ nằm trong hình.
3. **Không tải gì từ ngoài (W-NFR-2).** Phông lấy từ chính ứng dụng.
4. **Không làm hỏng gì đã có.** Toàn bộ test E2E cũ vẫn qua với hộp thoại, mục gập, chuyển trang có hiệu ứng.

## 2. Ba nhóm kiểm thử

| Nhóm | Kiểm cái gì | Công cụ | Chạy ở đâu | Lệnh |
| --- | --- | --- | --- | --- |
| I — Tích hợp | Tệp phông, gói, thẻ tải trước, logo, cấu trúc trang giới thiệu, luật giảm chuyển động, thanh bên mờ kính | pytest, FastAPI TestClient, đọc `style.css` | Máy và CI | `pytest tests/test_ui_depth.py` |
| E — E2E | Cảnh 3D theo con trỏ, thẻ nghiêng, giảm chuyển động, bục band trên báo cáo, phông đang hiển thị | Playwright + Chromium | **Chỉ trên máy** | `pytest -m e2e tests/e2e/test_ui_depth_e2e.py` |
| R — Hồi quy | Mọi test E2E sẵn có với các hiệu ứng mới | Playwright + Chromium | **Chỉ trên máy** | `pytest -m e2e tests/e2e` |

Phần nhìn — bố cục, màu ở hai giao diện, điện thoại — kiểm bằng ảnh chụp từ máy chủ tạm ở 1280×820 và 390×844, sáng và tối; ảnh không lưu vào kho mã.

## 3. Dữ liệu và môi trường

- Tài khoản và bài nộp tổng hợp qua pipeline thật với bộ nhận dạng giả lập. Bản chép giả lập quá ngắn để được chấm, nên test bục band **ghi điểm máy vào đúng chỗ pipeline ghi** (báo cáo lưu và dòng `response`), như các test tích hợp của D030.
- Không có dữ liệu người học thật.

## 4. Tiêu chí vào và ra

- **Vào:** mã qua `ruff format --check` và `ruff check`.
- **Ra:** 100% nhóm I qua trên CI; 100% nhóm E và R qua trên máy trước khi merge.

## 5. Truy vết

| Mục | Test case |
| --- | --- |
| W-NFR-2 — không tải tài nguyên từ ngoài | TC-UI-I01, TC-UI-E05 |
| Đợt 12 — phông và logo | TC-UI-I01, TC-UI-I02, TC-UI-I03, TC-UI-I04, TC-UI-E05 |
| Đợt 12 — trang giới thiệu | TC-UI-I05, TC-UI-E02 |
| Đợt 12 — khối 3D dùng chung | TC-UI-I06, TC-UI-E04 |
| Đợt 12 — mọi trang | TC-UI-I08, nhóm R |
| W-NFR-3 — chuyển động là trang trí | TC-UI-I05, TC-UI-I06, TC-UI-I07, TC-UI-E03 |

## 6. Danh mục test case

### Nhóm I — Tích hợp (`tests/test_ui_depth.py`)

| Mã | Test | Kiểm điều gì |
| --- | --- | --- |
| TC-UI-I01 | `test_roboto_is_served_by_the_app_itself` | Sáu tệp WOFF2 mà `@font-face` nêu đều có trên đĩa và trả 200 kiểu `font/woff2`; CSS không trỏ tới máy chủ phông nào bên ngoài; có `font-display: swap` |
| TC-UI-I02 | `test_the_wheel_carries_the_fonts_and_their_licence` | `package-data` có `fonts/*.woff2` và `fonts/*.txt`; giấy phép OFL đi kèm |
| TC-UI-I03 | `test_the_preloaded_fonts_are_the_ones_the_stylesheet_asks_for` | Hai thẻ tải trước trỏ đúng địa chỉ của `@font-face`, không có `?v=`; có tập vietnamese |
| TC-UI-I04 | `test_the_mark_is_drawn_inline_with_names_of_its_own` | Logo nội tuyến có một bong bóng và ba thanh mang lớp `logo-*`, không mang lớp `bar`; favicon có ba thanh và bản màu tối |
| TC-UI-I05 | `test_the_product_page_keeps_its_words_out_of_the_3d_scene` | Trang chủ không còn cảnh 3D (D078); tiêu đề và các phần vẫn đủ |
| TC-UI-I06 | `test_the_blocks_on_other_screens_are_hidden_from_screen_readers` | Hàng khối ở trang đăng nhập và trang band đều `aria-hidden` |
| TC-UI-I07 | `test_reduced_motion_stops_the_motion` | Luật giảm chuyển động dừng mọi hoạt ảnh và chuyển tiếp, tắt chuyển trang mờ dần; hiệu ứng khi cuộn và khi vào trang chỉ chạy khi người dùng không chọn giảm chuyển động; `landing.js` thoát ngay khi giảm chuyển động hoặc không có con trỏ chính xác |
| TC-UI-I08 | `test_the_sidebar_is_frosted_only_where_it_holds_no_fixed_tab_bar` | Mọi luật đặt `backdrop-filter` cho thanh bên nằm trong `@media (min-width: 901px)` |

### Nhóm E — E2E (`tests/e2e/test_ui_depth_e2e.py`)

| Mã | Test | Kiểm điều gì |
| --- | --- | --- |
| TC-UI-E02 | `test_a_step_card_leans_toward_the_pointer_and_settles` | Thẻ bước nghiêng về phía con trỏ (cạnh phải tiến ra), rời đi thì trả lại cho stylesheet |
| TC-UI-E03 | `test_with_reduced_motion_nothing_follows_the_pointer` | Chọn giảm chuyển động: cảnh và thẻ không nhúc nhích |
| TC-UI-E04 | `test_the_report_marks_the_estimated_band_among_the_three` | Bục band trên báo cáo: B1 là band ước lượng, B2 trong khoảng tin cậy, A2 nhạt nhất; bục ẩn với trình đọc màn hình, band vẫn viết ra bên cạnh |
| TC-UI-E05 | `test_roboto_is_the_face_on_the_screen` | Roboto thật sự được tải (ít nhất hai tập) và là phông của trang; mọi tệp phông tải từ chính máy chủ |

## 7. Kết quả chạy

| Lệnh | Kết quả |
| --- | --- |
| `pytest tests/test_ui_depth.py` | 8 test qua |
| `pytest -m e2e tests/e2e/test_ui_depth_e2e.py` | 5 test qua |
| `pytest -m e2e tests/e2e` | 55 test qua (50 sẵn có, 5 mới) |

## 8. Lỗi tìm thấy trong lúc làm

| Mã | Lỗi | Sửa | Giữ lại bằng |
| --- | --- | --- | --- |
| D031-B1 | Ba thanh của logo bẹp thành ba chấm: lớp `.bar` trùng tên lớp thanh tiến độ, và SVG2 cho CSS đặt chiều cao của `rect` | Đổi sang `logo-bubble`, `logo-bar` | TC-UI-I04 |
| D031-B2 | Tiêu đề trang giới thiệu ngắt thành "Nói. Nghe / lại. Tiến bộ." vì `text-wrap: balance` chia đều hai dòng | Mỗi vế một dòng (`.lp-line`) | Ảnh chụp |
| D031-B3 | Phối cảnh đặt trên cả lưới ba thẻ làm biểu tượng của hai thẻ ngoài lệch ra ngoài mép thẻ ngay cả khi đứng yên | Mỗi thẻ mang phối cảnh của riêng nó; các lớp bên trong chỉ nổi lên khi thẻ đang nghiêng | TC-UI-E02, ảnh chụp |
| D031-B4 | Thanh đầu trang của khách trên điện thoại chiếm ba hàng | Ẩn các liên kết neo (tên sản phẩm đã dẫn về trang giới thiệu), nút giao diện thành biểu tượng có nhãn ẩn | Ảnh chụp |
| D031-B5 | Ở giao diện tối, số trên khối nhạt gần như không đọc được | Khối pha màu với `--border-strong` thay vì nền trang | Ảnh chụp |
| D031-B6 | Khối thấp nhất của bậc thang trên điện thoại không chứa nổi số của nó | Số đặt giữa khối, nhỏ hơn | Ảnh chụp |
| D031-B7 | Cột band không có bài nào ở thống kê lớp làm tràn con số 0 | Chiều cao tối thiểu 58 px | Ảnh chụp |
| D031-B8 | Khối cao nhất ở trang đăng nhập đè lên danh sách bên dưới | Thêm khoảng cách dưới hàng khối | Ảnh chụp |
| D031-B9 | Chủ dự án góp ý giao diện "nhìn bị nhựa": lớp sáng trên nút và ô biểu tượng, viền sáng bên trong, bóng đổ có màu, chữ chuyển màu, khối 3D màu đậm có chuyển sắc, vật trôi bồng bềnh | Bề mặt mờ: ô biểu tượng nền nhạt viền mảnh; nút một màu, bóng mảnh, không nhấc lên; bóng đổ trung tính và nhẹ; tiêu đề một màu; khối 3D màu nhạt viền mảnh, mỗi hàng chỉ một khối đậm; thẻ nghiêng tối đa 5°; trôi 4 px thay vì 10 px; vào trang trồi 6 px | Ảnh chụp sáng và tối |

Một rủi ro được chặn từ lúc thiết kế, không phải lỗi đã xảy ra: `backdrop-filter` trên thanh bên ở điện thoại sẽ biến thanh bên thành khối chứa của thanh tab cố định ở đáy và kéo nó lên đầu trang. Thanh bên chỉ mờ kính ở màn rộng (TC-UI-I08).
