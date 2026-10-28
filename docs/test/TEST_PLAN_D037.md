# Kế hoạch và kết quả kiểm thử D037 — Ảnh nền vẽ bằng mã: bậc thang tiếng nói

| Thuộc tính | Giá trị |
| --- | --- |
| Tính năng | D037: ảnh nền sau mọi trang, cảnh đồi có chuyển động ở trang giới thiệu và trang đăng nhập, dải đồi ở trạng thái rỗng (đặc tả web 1.7, Đợt 16; W-NFR-2, W-NFR-3, W-NFR-4) |
| Phiên bản mã | nhánh `feat/ui-art` |
| Người lập | Võ Thanh Sang |
| Ngày | 07/10/2026 |

## 1. Mục tiêu

1. **Hình không mất đi mà không ai biết.** Một tệp bị bỏ khỏi gói cài, một trang quên phần nền, một tệp SVG bị sửa tay rồi bị script ghi đè: mỗi trường hợp đó có một test bắt.
2. **Hình không cản người dùng (W-NFR-3, W-NFR-4).**
   - Người chọn giảm chuyển động không thấy hình chuyển động.
   - Hình không nhận cú bấm hay chạm, không làm trang cuộn ngang trên điện thoại, không in ra giấy, và ẩn với trình đọc màn hình.
   - Không chữ nào đứng trên hình bị giảm xuống dưới mức tương phản AA.
3. **Hình đúng ở mọi khổ màn hình.**
   - Màn hình rộng thấy trọn đồi xa, mặt trời vẫn tròn.
   - Điện thoại thấy phần bên phải của cảnh.
   - Hai giao diện sáng và tối có màu riêng.
4. **Không tải gì từ ngoài (W-NFR-2).** Mọi hình đều do ứng dụng tự phục vụ hoặc nằm thẳng trong trang. Không có thư viện mới.

## 2. Bốn nhóm kiểm thử

| Nhóm | Kiểm cái gì | Công cụ | Chạy ở đâu | Lệnh |
| --- | --- | --- | --- | --- |
| U — Đơn vị | Hình học của `tools/make_art.py`: đường cong, khung hình, bờ ruộng, thứ tự các tầng; kế hoạch và mã khớp nhau | pytest | Máy và CI | `pytest tests/test_art_unit.py` |
| I — Tích hợp | Tệp đã commit đúng bằng tệp script vẽ ra, SVG an toàn, mọi trang có nền, cảnh nhúng trong trang, gói cài, luật chuyển động, in, tương tác, màu theo giao diện | pytest, FastAPI TestClient, đọc `style.css` | Máy và CI | `pytest tests/test_art.py` |
| E — E2E | Hình hiển thị ở hai giao diện, đường tự vẽ, giảm chuyển động, trôi theo con trỏ, bốn khổ màn hình, điện thoại, in, độ tương phản đo trên điểm ảnh | Playwright + Chromium | **Chỉ trên máy** | `pytest -m e2e tests/e2e/test_art_e2e.py` |
| R — Hồi quy | Toàn bộ test sẵn có khi đã có hình nền | pytest, Playwright | Máy (E2E) và CI | `pytest -m "not e2e"`, `pytest -m e2e tests/e2e` |

Phần nhìn được kiểm bằng ảnh chụp từ máy chủ tạm, ở cả giao diện sáng và tối, ảnh không lưu vào kho mã:

- 13 trang ở 1280×860 và 390×860;
- trang giới thiệu và trang đăng nhập ở 390, 1280, 1440 và 1920 px.

## 3. Dữ liệu và môi trường

- Tài khoản tạo trong test: sinh viên, giảng viên và quản trị viên mang bút danh tổng hợp. Không có dữ liệu người học thật.
- Hình vẽ hoàn toàn bằng mã, có hạt giống cố định, nên chạy lại cho kết quả giống hệt.

## 4. Tiêu chí vào và ra

- **Vào:** mã qua `ruff format --check` và `ruff check`.
- **Ra:**
  - 100% nhóm U và I qua trên CI.
  - 100% nhóm E và R qua trên máy trước khi merge.

## 5. Truy vết

| Mục | Test case |
| --- | --- |
| W-NFR-2 — không tải tài nguyên từ ngoài | TC-ART-I02, TC-ART-I04, TC-ART-I05, TC-ART-E01 |
| W-NFR-3 — chuyển động là trang trí | TC-ART-I04, TC-ART-I06, TC-ART-E02, TC-ART-E03 |
| W-NFR-4 — ảnh nền không cản việc đọc | TC-ART-I07, TC-ART-E06, TC-ART-E07, TC-ART-E08 |
| Đợt 16 — mọi trang | TC-ART-I03, TC-ART-I08, TC-ART-E01 |
| Đợt 16 — trang giới thiệu và trang đăng nhập | TC-ART-I04, TC-ART-E02, TC-ART-E04, TC-ART-E05 |
| Đợt 16 — trạng thái rỗng | TC-ART-E07, TC-ART-E08 |
| Đợt 16 — cách làm (script xác định) | TC-ART-U01, TC-ART-U02, TC-ART-U03, TC-ART-U04, TC-ART-I01 |
| Kế hoạch khớp mã | TC-ART-U05 |

## 6. Danh mục test case

### Nhóm U — Đơn vị (`tests/test_art_unit.py`)

| Mã | Test | Kiểm điều gì |
| --- | --- | --- |
| TC-ART-U01 | `test_the_curve_passes_through_every_point_it_was_given` | Đường cong Catmull-Rom đi qua đúng mọi điểm; sau đoạn đầu chỉ dùng lệnh rút gọn `S`; không bao giờ ghi "-0" |
| TC-ART-U02 | `test_every_ridge_and_wall_stays_inside_the_picture` | Mọi sống đồi và bờ ruộng nằm trong khung, cách mép trên ít nhất 10% chiều cao |
| TC-ART-U03 | `test_the_walls_run_below_the_ridge_and_only_the_ridge_speaks` | Bờ ruộng luôn nằm dưới sống đồi và không có gợn âm tiết. Ngoài đoạn có câu nói, sống đồi trùng với đồi im lặng. Mỗi âm tiết nâng sống đồi ít nhất bằng độ lớn của nó. Cùng hạt giống thì ra cùng câu |
| TC-ART-U04 | `test_far_bands_sit_higher_and_paler_than_near_ones` | Tầng xa nằm cao hơn và nhạt hơn tầng gần; mỗi tầng có câu nói riêng |
| TC-ART-U05 | `test_the_plan_and_the_code_name_the_same_cases` | Mọi test trong ba tệp có một dòng trong bảng này và ngược lại; không mã nào bị dùng hai lần |

### Nhóm I — Tích hợp (`tests/test_art.py`)

| Mã | Test | Kiểm điều gì |
| --- | --- | --- |
| TC-ART-I01 | `test_the_committed_art_is_what_the_script_draws` | `hills.svg`, `contours.svg` và `_art.html` giống từng byte với tệp `tools/make_art.py` vẽ ra |
| TC-ART-I02 | `test_the_drawings_are_inert_and_small` | Hai tệp SVG là XML hợp lệ, có `viewBox`, mỗi tệp dưới 12 KB. Không có DOCTYPE hay ENTITY. Chỉ gồm hình và dải màu: không script, không thuộc tính `on*`, không liên kết |
| TC-ART-I03 | `test_every_page_stands_on_the_ground` | Trang khách, trang của sinh viên, giảng viên và quản trị viên đều có đúng một phần nền `aria-hidden` gồm đường đồng mức và dãy đồi, và `body` mang lớp vai trò. Trang giới thiệu và trang đăng nhập chỉ giữ đường đồng mức |
| TC-ART-I04 | `test_the_product_and_sign_in_pages_carry_the_scene` | Cảnh nằm trong phần mở đầu, trước tiêu đề, và `aria-hidden`. Cảnh có mặt trời, 4 tầng, 4 sống đồi `pathLength="1"`, 8 bờ ruộng, `preserveAspectRatio="none"`. Không có liên kết, nút, ô nhập, ảnh, script hay `url(`; dưới 16 KB |
| TC-ART-I05 | `test_the_art_is_served_as_svg_and_carried_in_the_wheel` | Mọi `url("art/…")` trong CSS trỏ tới tệp có thật, trả 200 kiểu `image/svg+xml`. `package-data` có `art/*.svg` và các template |
| TC-ART-I06 | `test_motion_plays_only_when_welcome` | Bốn hoạt ảnh `art-*` và nét đứt chờ vẽ chỉ nằm trong `prefers-reduced-motion: no-preference` |
| TC-ART-I07 | `test_the_art_stays_out_of_the_way` | Nền, cảnh đồi và dải đồi của trạng thái rỗng đặt `pointer-events: none`. Nền cố định, `z-index: -1`, đứng yên khi chuyển trang. Khi in, mọi phần đều `display: none` |
| TC-ART-I08 | `test_each_theme_colours_the_art` | Năm biến màu của hình khai báo ở `:root` và khai báo lại ở cả hai bộ chọn giao diện tối. Trang giảng viên và quản trị viên nhạt hơn |

### Nhóm E — E2E (`tests/e2e/test_art_e2e.py`)

| Mã | Test | Kiểm điều gì |
| --- | --- | --- |
| TC-ART-E01 | `test_the_ground_is_drawn_in_both_themes` | Ở cả giao diện sáng và tối: hai tệp hình tải về với mã 200; đường đồng mức nằm góc trên bên phải, dãy đồi góc dưới bên phải, đủ lớn; mỗi giao diện một màu |
| TC-ART-E02 | `test_the_ridges_draw_themselves_in_when_motion_is_welcome` | Bốn tầng trồi lên, bốn sống đồi tự vẽ, mặt trời mọc, tầng gần "thở" mãi. Vẽ xong thì đường vẫn còn nguyên |
| TC-ART-E03 | `test_with_reduced_motion_the_scene_is_simply_there` | Khi chọn giảm chuyển động: không hoạt ảnh `art-*` nào, đường không đứt nét, con trỏ không làm cảnh dịch đi |
| TC-ART-E04 | `test_the_terraces_drift_against_the_scene` | Đưa con trỏ sang phải thì cảnh 3D xoay theo và đồi trượt sang trái |
| TC-ART-E05 | `test_any_width_gets_the_whole_far_hill_and_a_round_sun` | Ở 390, 1280, 1920 và 2560 px: không tầng nào bị cắt ở mép trên; mặt trời tròn và nằm trong khung; trang đăng nhập không có mặt trời |
| TC-ART-E06 | `test_on_a_phone_the_art_takes_no_tap_and_no_room` | Ở 390 px, trang giới thiệu, trang đăng nhập và trang band không cuộn ngang. Không điểm nào trên lưới 23 px (đầu và chân trang) rơi vào hình. Nút đăng nhập nhận được cú chạm |
| TC-ART-E07 | `test_printing_leaves_the_art_out` | Khi in, phần nền, cảnh đồi và dải đồi của trạng thái rỗng đều biến mất; trên màn hình thì dải đồi vẫn hiện |
| TC-ART-E08 | `test_the_words_on_the_art_keep_their_contrast` | Đo trên điểm ảnh ở bốn trang (giới thiệu, đăng nhập, band, tiến độ), hai khổ màn hình và hai giao diện. Chụp trang với chữ trong suốt, một lần có hình, một lần không. Mỗi dòng chữ được so với từng điểm ảnh nằm sau nó. Có hình thì chữ vẫn đạt AA (4,5:1; chữ lớn 3:1); chỗ nào chưa đạt khi không có hình thì hình không làm tệ hơn |

## 7. Kết quả chạy

| Lệnh | Kết quả |
| --- | --- |
| `pytest tests/test_art_unit.py tests/test_art.py` | 13 test qua |
| `pytest -m e2e tests/e2e/test_art_e2e.py` | 8 test qua |
| `pytest -m "not e2e"` | 1153 test qua, 10 bỏ qua theo thiết kế; độ phủ 93% |
| `pytest -m e2e tests/e2e` | 73 test qua (65 sẵn có, 8 mới) |

**Kiểm độ nhạy của TC-ART-E08.** Đã thử tạm làm sai stylesheet để xem test có bắt được không:

- Tầng đồi nằm sau dòng "Bài học 10–15 phút" bị đẩy từ 13% lên 70% mực và bỏ phần mờ bên trái: test báo lỗi.
- Tầng đồi xa bị đẩy lên 70%: test vẫn qua. Kết quả đo đúng, vì ở đó tầng xa chỉ là một dải hẹp nằm giữa các dòng chữ, không nằm sau chữ nào.

Sau khi thử, stylesheet đã được trả lại nguyên như cũ.

## 8. Lỗi tìm thấy trong lúc làm

| Mã | Lỗi | Sửa | Giữ lại bằng |
| --- | --- | --- | --- |
| D037-B1 | Bản vẽ đầu nặng 17–23 KB, gợn âm tiết lấy mẫu thưa nên bị gãy khúc | Chỉ lấy mẫu dày ở đoạn có câu nói; dùng lệnh rút gọn `S`; toạ độ nguyên. Còn 8–14 KB | TC-ART-I02, TC-ART-I04, TC-ART-U01 |
| D037-B2 | Mặt trời của phần nền ló ra giữa các thẻ ở các trang bên trong | Bỏ mặt trời khỏi phần nền; chỉ cảnh của trang giới thiệu có mặt trời | TC-ART-I03, ảnh chụp |
| D037-B3 | Đường đồng mức chạy sau chữ ở bên trái | Đường đồng mức mờ dần về bên trái theo dải màu trong chính tệp SVG | TC-ART-E08, ảnh chụp |
| D037-B4 | Các tầng đồi trông như hình vẽ nét, bờ ruộng đậm hơn mặt ruộng | Bốn tầng đậm dần 8/13/18/24%, bờ ruộng nhạt | Ảnh chụp sáng và tối |
| D037-B5 | Trang đăng nhập, giao diện tối: phần mờ dần thẳng tạo một mép chữ nhật ở bên trái; nửa mặt trời ló ra ở cạnh khung đăng nhập; sống đồi chạy sau danh sách chữ | Mờ dần theo đường cong êm và bắt đầu từ 34% bề ngang; trang đăng nhập không có mặt trời | TC-ART-E05, TC-ART-E08 |
| D037-B6 | Màn hình rộng hơn khoảng 1550 px: cảnh co theo chiều ngang (`slice`) nên đồi xa bị cắt phẳng ở mép trên, mặt trời ra khỏi khung | Cảnh giãn theo khung (`preserveAspectRatio="none"`); mặt trời là phần tử riêng, tròn bằng CSS | TC-ART-E05 ở 390, 1280, 1920 và 2560 px |
| D037-B7 | Lỗi của chính test: lần đo đầu tính cả chữ trong mục "Quên mật khẩu?" đang đóng, vốn có hộp bố cục nhưng không được vẽ | Bỏ chữ mà `checkVisibility()` báo là không hiện; cắt theo các phần tử cha có ẩn phần tràn | TC-ART-E08 |
