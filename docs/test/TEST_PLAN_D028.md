# Kế hoạch và kết quả kiểm thử D028 — Hoàn thiện sản phẩm

| Thuộc tính | Giá trị |
| --- | --- |
| Tính năng | D028: đổi mật khẩu và quản lý phiên, quản trị tài khoản trên web với mật khẩu tạm in thành phiếu, đếm việc đang chờ trên thanh điều khiển, trang giải thích band, chuẩn bị 30 giây trước khi nói (FR-51..FR-55; mở rộng UC-01, UC-04, UC-05, UC-10, UC-17) |
| Phiên bản mã | nhánh `feat/product-complete` |
| Người lập | Võ Thanh Sang |
| Ngày | 07/10/2026 |

## 1. Mục tiêu

Chứng minh bằng kiểm thử tự động bốn lời hứa:

1. **Mật khẩu chỉ một người biết.** Mật khẩu do quản trị viên cấp là mật khẩu tạm, hiện một lần, không lưu bản rõ, và không mở được gì ngoài việc đổi sang mật khẩu riêng. Đổi mật khẩu cần mật khẩu hiện tại, kết thúc mọi phiên khác, và lần nhập sai bị tính vào khoá đăng nhập.
2. **Quản trị viên làm được mọi việc về tài khoản mà không cần dòng lệnh**, và không làm hỏng được gì không sửa được: tạo cả dãy hoặc không tạo gì, không tự tắt hay tự cấp lại mật khẩu cho mình, mọi thao tác có nhật ký.
3. **Con số trên thanh điều khiển đúng** với việc đang chờ thật, và về 0 khi người dùng đã xem.
4. **Trang band không nói quá điều máy làm được**: mặt nào máy không đo thì ghi là không đo; ngưỡng band đọc từ mô hình đang chấm.

## 2. Hai tầng kiểm thử

Logic thuần của D028 nhỏ (chính sách mật khẩu, sinh mật khẩu tạm, đánh số bút danh) và được kiểm qua tầng 2 cùng với đường đi thật của nó, nên kế hoạch này chỉ có hai tầng.

| Tầng | Kiểm cái gì | Công cụ | Môi trường | Chạy ở đâu | Lệnh |
| --- | --- | --- | --- | --- | --- |
| 2. Integration | API tài khoản, cổng mật khẩu tạm, nhật ký kiểm toán, con số đang chờ, trang band, trang nộp bài | pytest, FastAPI TestClient | SQLite thật trên tệp tạm, bộ nhận dạng giả lập, sóng sin tổng hợp | Máy và CI | `pytest tests/test_accounts.py` |
| 3. E2E | Quản trị viên cấp tài khoản trên phiếu, người mới đăng nhập lần đầu và đổi mật khẩu; con số sau quyết định của giảng viên; đồng hồ chuẩn bị rồi ghi âm bằng micro giả; trang band | Playwright + Chromium (micro giả) | Máy chủ uvicorn riêng, CSDL tạm | **Chỉ trên máy**; CI tự bỏ qua | `pytest -m e2e tests/e2e/test_accounts_e2e.py` |

## 3. Dữ liệu và môi trường

- Không dùng giọng người thật. Bài nộp là sóng sin tổng hợp 35 giây; ghi âm ở tầng 3 dùng micro giả của Chromium.
- Mật khẩu trong test là hằng số của chính bộ test; mật khẩu tạm do hệ thống sinh trong lúc chạy và chỉ sống trong CSDL tạm của lần chạy đó.
- Giới hạn đăng nhập theo địa chỉ (10 lần/phút) vẫn bật ở tầng 2; mỗi test dùng một ứng dụng mới nên bộ đếm bắt đầu lại.

## 4. Tiêu chí vào và ra

- **Vào:** mã qua `ruff format --check` và `ruff check`.
- **Ra (được merge):** 100% test tầng 2 qua trên CI; 100% test tầng 3 qua trên máy trước khi merge; mọi tiêu chí chấp nhận AC-51.1..AC-55.2 có ít nhất một test (kiểm bằng `tests/test_product_traceability.py`); mỗi lỗi tìm được có test hồi quy hoặc ghi rõ vì sao không cần.

## 5. Truy vết tiêu chí chấp nhận

Tiêu chí chấp nhận AC-51.1..AC-55.2 nằm ở `docs/srs/SRS.md`, mục 3.9c.

| Tiêu chí chấp nhận | Test case |
| --- | --- |
| AC-51.1 | TC-PC-I01 |
| AC-51.2 | TC-PC-I02 |
| AC-51.3 | TC-PC-I03 |
| AC-51.4 | TC-PC-I04 |
| AC-51.5 | TC-PC-I05 |
| AC-52.1 | TC-PC-I06, TC-PC-E01 |
| AC-52.2 | TC-PC-I07, TC-PC-E01 |
| AC-52.3 | TC-PC-I09 |
| AC-52.4 | TC-PC-I10 |
| AC-52.5 | TC-PC-I08 |
| AC-52.6 | TC-PC-I12 |
| AC-52.7 | TC-PC-I11 |
| AC-53.1 | TC-PC-I13, TC-PC-E02 |
| AC-53.2 | TC-PC-I14 |
| AC-53.3 | TC-PC-I15 |
| AC-54.1 | TC-PC-I16, TC-PC-E04 |
| AC-54.2 | TC-PC-I17 |
| AC-55.1 | TC-PC-I18 |
| AC-55.2 | TC-PC-E03 |

## 6. Danh mục test case

### Tầng 2 — Integration (`tests/test_accounts.py`)

| Mã | Test | Truy vết | Kiểm điều gì |
| --- | --- | --- | --- |
| TC-PC-I01 | `test_password_change_needs_the_current_password_and_ends_other_sessions` | AC-51.1 | Đổi mật khẩu: phiên khác 401, phiên này còn, mật khẩu cũ hết dùng, nhật ký không chứa mật khẩu |
| TC-PC-I02 | `test_a_wrong_current_password_is_refused_and_counts_towards_the_lockout` | AC-51.2 | Năm lần sai mật khẩu hiện tại thì khoá như đăng nhập sai |
| TC-PC-I03 | `test_the_password_policy_says_what_is_wrong` | AC-51.3 | Bốn trường hợp bị từ chối, mỗi trường hợp một lý do |
| TC-PC-I04 | `test_signing_out_other_devices_keeps_this_one` | AC-51.4 | Đăng xuất thiết bị khác, giữ phiên này |
| TC-PC-I05 | `test_the_account_page_needs_a_login_and_shows_the_pseudonym` | AC-51.5 | Khách bị đưa về đăng nhập; người dùng thấy bút danh |
| TC-PC-I06 | `test_a_series_continues_the_numbering_with_one_time_passwords` | AC-52.1 | Dãy đánh số tiếp nối, mật khẩu tạm đúng mẫu và khác nhau, `no-store`, không lộ băm |
| TC-PC-I07 | `test_a_temporary_password_opens_nothing_but_the_password_change` | AC-52.2 | Cổng mật khẩu tạm ở API và ở trang; đổi xong về trang chính của vai trò |
| TC-PC-I08 | `test_creating_accounts_is_all_or_nothing_and_checks_names` | AC-52.5 | Bút danh trùng, ký tự lạ, giống mã số sinh viên, tiền tố sai, quá 200: không tạo gì |
| TC-PC-I09 | `test_a_reset_ends_the_sessions_and_issues_a_new_one_time_password` | AC-52.3 | Cấp lại mật khẩu tạm kết thúc phiên; không tự cấp cho mình; 404 khi không có tài khoản |
| TC-PC-I10 | `test_a_disabled_account_is_signed_out_and_cannot_sign_in` | AC-52.4 | Tắt thì đăng xuất ngay; không tự tắt; bật lại thì đăng nhập được |
| TC-PC-I11 | `test_an_administrator_lifts_a_lockout` | AC-52.7 | Gỡ khoá sau năm lần đăng nhập sai |
| TC-PC-I12 | `test_only_an_administrator_manages_accounts` | AC-52.6 | Sinh viên và giảng viên nhận 403 ở mọi API quản lý tài khoản |
| TC-PC-I13 | `test_a_teacher_decision_is_new_until_the_student_opens_their_list` | AC-53.1 | Con số "kết quả mới" tăng khi giảng viên quyết định, về 0 khi đã xem |
| TC-PC-I14 | `test_a_teacher_sees_how_many_responses_wait_for_review` | AC-53.2 | Con số hàng đợi bằng số bài chờ duyệt |
| TC-PC-I15 | `test_the_sidebar_carries_a_slot_for_each_count` | AC-53.3 | Chỗ hiện con số có trên thanh điều khiển của mỗi vai trò |
| TC-PC-I16 | `test_the_band_page_labels_what_the_machine_does_not_measure` | AC-54.1 | Ngưỡng của mô hình, nhãn "máy không đo" và "không đánh giá", giới hạn với người nói lắp |
| TC-PC-I17 | `test_the_report_links_its_band_to_the_band_page` | AC-54.2 | Báo cáo dẫn tới `/bands` |
| TC-PC-I18 | `test_the_submit_page_offers_thirty_seconds_of_preparation` | AC-55.1 | Khối chuẩn bị 30 giây trên trang nộp bài |
| TC-PC-I19 | `test_temporary_passwords_avoid_characters_people_confuse` | FR-52 | 300 mật khẩu tạm khác nhau, đúng mẫu, không có i, l, o, 0, 1 |
| TC-PC-A01 | `test_the_guards_are_where_the_paths_say` | AC-52.6 | Mọi route `/api/v1/admin/*` chỉ cho quản trị viên; mọi route API khác có lớp chặn, trừ bốn route phải công khai (đăng nhập, đăng xuất, callback thanh toán) |
| TC-PC-A02 | `test_a_visitor_is_asked_to_sign_in_everywhere_guarded` | FR-52 | Khách gọi mọi route có lớp chặn đều nhận 401 |
| TC-PC-A03 | `test_a_student_is_refused_every_admin_and_staff_route` | AC-52.6 | Sinh viên nhận 403 "không có quyền" ở mọi route quản trị và giảng viên |
| TC-PC-A04 | `test_a_teacher_is_refused_every_admin_and_student_route` | AC-52.6 | Giảng viên nhận 403 ở mọi route quản trị và route riêng của sinh viên |
| TC-PC-A05 | `test_an_admin_on_a_temporary_password_reaches_nothing_admin` | FR-52 | Quản trị viên còn mật khẩu tạm nhận 403 ở mọi route quản trị |
| TC-PC-A06 | `test_an_admin_passes_every_admin_route` | AC-52.6 | Quản trị viên không bị 401 hay lời từ chối vai trò ở route quản trị nào |
| TC-PC-A07 | `test_an_admin_is_refused_every_student_route` | FR-52 | Quản trị viên nhận 403 ở route riêng của sinh viên |
| TC-PC-A08 | `test_a_disabled_admin_is_signed_out_at_once` | FR-52 | Tắt tài khoản quản trị: phiên đang mở nhận 401 ngay, đăng nhập lại bị từ chối |
| TC-PC-A09 | `test_a_demoted_admin_loses_admin_routes_on_the_next_call` | FR-52 | Hạ vai trò: lần gọi kế tiếp nhận 403 |
| TC-PC-A10 | `test_an_admin_cannot_lock_themself_out` | FR-52 | Quản trị viên không tự tắt, tự hạ vai trò, tự cấp mật khẩu tạm hay tự đăng xuất mọi nơi (409) |
| TC-PC-A11 | `test_admin_pages_open_only_for_an_admin` | AC-52.6 | `/admin`, `/admin/study`: khách về trang đăng nhập, vai trò khác về trang của mình, mật khẩu tạm về `/account` |

### Tầng 3 — E2E (`tests/e2e/test_accounts_e2e.py`)

| Mã | Test | Truy vết | Kiểm điều gì |
| --- | --- | --- | --- |
| TC-PC-E01 | `test_an_administrator_hands_out_an_account_and_its_first_login_sets_a_password` | AC-52.1 | Tạo tài khoản, đọc mật khẩu tạm trên phiếu, ẩn phiếu; người mới đăng nhập ở trình duyệt khác bị đưa về `/account` dù định đi đâu, đổi mật khẩu rồi về hàng đợi |
| TC-PC-E02 | `test_a_teacher_decision_is_a_count_until_the_student_opens_their_list` | AC-53.1 | Sinh viên nộp bài, giảng viên quyết định; con số hiện trên thanh điều khiển, mở "Bài của tôi" thì có nhãn "Mới xác nhận" và con số ẩn |
| TC-PC-E03 | `test_thirty_seconds_of_preparation_then_the_answer_is_recorded` | AC-55.2 | Đồng hồ chạy, huỷ về 30; "Nói ngay" bật ghi âm bằng micro giả, dừng để nghe lại |
| TC-PC-E04 | `test_the_band_page_says_what_the_machine_does_not_measure` | AC-54.1 | Trang band cho khách: hai mặt "máy không đo", ba bậc band, đường dẫn ở chân trang |

## 7. Kết quả chạy

| Lệnh | Kết quả |
| --- | --- |
| `pytest tests/test_accounts.py` | 23 test qua (19 hàm; một hàm 4 trường hợp, một hàm 2 trường hợp) |
| `pytest -m e2e tests/e2e/test_accounts_e2e.py` | 4 test qua |
| `pytest -m "not e2e"` (toàn bộ) | 853 test qua, 10 bỏ qua có chủ ý |
| `pytest -m e2e` (toàn bộ) | 45 test qua |

## 8. Lỗi tìm thấy trong lúc làm

| Mã | Lỗi | Sửa | Test giữ lại |
| --- | --- | --- | --- |
| D028-B1 | Mật khẩu tạm trên phiếu bị bẻ xuống dòng khi khung hẹp, dễ gõ sai | Hai mã trên phiếu xếp dọc, mỗi mã một dòng không ngắt | TC-PC-E01 đọc mã từ phiếu và đăng nhập được bằng nó |
| D028-B2 | Trang `/account` của tài khoản dùng mật khẩu tạm gọi API con số và nhận 403, làm bẩn bảng điều khiển trình duyệt | Không hiện chỗ con số khi đang dùng mật khẩu tạm, nên trang không gọi API đó | TC-PC-I07 (API vẫn từ chối), TC-PC-I15 (tài khoản thường vẫn có chỗ) |
| D028-B3 | Ruff 0.16.10 trên CI và 0.16.7 trên máy xếp một dòng import khác nhau, CI của PR trước đỏ | Ghim `known-first-party = ["aicefr"]` trong `pyproject.toml` | Bước `ruff check` của CI |
| D028-B4 | Bút danh chèn bằng template literal trong hộp xác nhận bị kiểm tra escape bắt | Ghép chuỗi cho `confirm()` và `toast()`, vốn không đọc HTML | `test_values_from_other_users_are_escaped` |
| D028-B5 | Quy tắc "không tắt quản trị viên cuối cùng" không bao giờ chạy được (người yêu cầu luôn là một quản trị viên đang bật khác) | Bỏ mã chết, giữ quy tắc "không tự tắt" và ghi lý do trong docstring | TC-PC-I10 |
| D028-B6 | Trang "Bài của tôi" không bao giờ yên mạng trên Chromium: lệnh đánh dấu "đã xem" chỉ đọc mã trạng thái, không đọc thân phản hồi, nên trình duyệt giữ yêu cầu mở mãi | Đọc thân phản hồi rồi mới ẩn con số | `test_phone_student_pages_keep_a_bottom_tab_bar_and_no_sideways_scroll[/my-responses]` (D024, đợi trang yên mạng) |
| D028-B7 | Con số 0 bị ẩn nhưng chữ "0, 0 mục ôn tập hôm nay" vẫn nằm trong nội dung của đường dẫn "Luyện tập" | Ở số 0, chỗ con số để trống chứ không chỉ ẩn | `test_navigation_is_a_sidebar_on_the_left_with_icons` (D027) |
