# Kế hoạch và kết quả kiểm thử D029 — Hồ sơ cá nhân, đăng nhập Google, quản lý tài khoản

| Thuộc tính | Giá trị |
| --- | --- |
| Tính năng | D029: hồ sơ cá nhân (ảnh đại diện, mục tiêu ngày, hiển thị), phiên đăng nhập, lịch sử hoạt động, đăng nhập bằng Google cho tài khoản đã liên kết, bảng chi tiết và đổi vai trò cho quản trị viên (FR-56..FR-60; mở rộng UC-10, UC-17) |
| Phiên bản mã | nhánh `feat/product-complete` |
| Người lập | Võ Thanh Sang |
| Ngày | 07/10/2026 |

## 1. Mục tiêu

1. **Google chỉ mở cửa cho đúng người.** Không tạo tài khoản; chỉ tài khoản đã liên kết đăng nhập được; mỗi lần đi qua Google có `state`, `nonce` và PKCE riêng; từng claim sai của ID token đều bị từ chối; không lưu email.
2. **Người dùng thấy và điều khiển được tài khoản của mình**: phiên nào đang mở, ai đã làm gì, đăng xuất từng phiên, sửa hồ sơ trong giới hạn an toàn.
3. **Quản trị viên làm được đủ việc mà không tự khoá mình**: chi tiết tài khoản, đổi vai trò, đăng xuất mọi thiết bị, gỡ Google; không thao tác lên chính mình.

## 2. Ba tầng kiểm thử

| Tầng | Kiểm cái gì | Công cụ | Môi trường | Chạy ở đâu | Lệnh |
| --- | --- | --- | --- | --- | --- |
| 1. Unit | Kiểm ID token, cookie của luồng Google, đường dẫn trở về, tên thiết bị | pytest | Không ứng dụng, không CSDL, không mạng | Máy và CI | `pytest tests/test_google_unit.py` |
| 2. Integration | API hồ sơ, phiên, lịch sử, luồng Google trọn vòng, API quản trị | pytest, FastAPI TestClient | SQLite thật trên tệp tạm; **Google được thay bằng một hàm dựng ID token** ở đúng chỗ gọi điểm cuối token, nên mọi bước kiểm token đều chạy thật | Máy và CI | `pytest tests/test_profile.py` |
| 3. E2E | Chọn ảnh đại diện và mục tiêu rồi thấy trang Luyện tập đổi theo; đăng xuất phiên ở máy khác; quản trị viên đổi vai trò trong bảng chi tiết | Playwright + Chromium | Máy chủ uvicorn riêng, CSDL tạm | **Chỉ trên máy**; CI tự bỏ qua | `pytest -m e2e tests/e2e/test_profile_e2e.py` |

Đăng nhập Google không có test tầng 3: một test trình duyệt thật cần chính Google. Tầng 2 đã đi trọn vòng chuyển hướng, cookie và kiểm token; phần còn lại phụ thuộc cấu hình OAuth client trên Google Cloud của trường và được kiểm thủ công khi bật.

## 3. Dữ liệu và môi trường

- ID token trong test do test tự dựng với `sub` giả; không gọi mạng. Email trong token giả dùng tên miền `example.edu.vn`.
- `AICEFR_GOOGLE_CLIENT_SECRET` trong test được dựng bằng phép nhân chuỗi, không có chuỗi bí mật nào nằm trong mã.
- Hai trình duyệt cùng tài khoản (Chrome macOS, Safari iPhone) được mô phỏng bằng tiêu đề `User-Agent`.

## 4. Tiêu chí vào và ra

- **Vào:** mã qua `ruff format --check` và `ruff check`.
- **Ra (được merge):** 100% test tầng 1 và 2 qua trên CI; 100% test tầng 3 qua trên máy trước khi merge; mọi tiêu chí chấp nhận AC-56.1..AC-60.3 có ít nhất một test (kiểm bằng `tests/test_product_traceability.py`).

## 5. Truy vết tiêu chí chấp nhận

Tiêu chí chấp nhận AC-56.1..AC-60.3 nằm ở `docs/srs/SRS.md`, mục 3.9d.

| Tiêu chí chấp nhận | Test case |
| --- | --- |
| AC-56.1 | TC-PF-I01, TC-PF-E01 |
| AC-56.2 | TC-PF-I02, TC-PF-E01 |
| AC-56.3 | TC-PF-I03, TC-PF-E01 |
| AC-56.4 | TC-PF-I04 |
| AC-57.1 | TC-PF-I05, TC-PF-U11, TC-PF-E02 |
| AC-57.2 | TC-PF-I06 |
| AC-58.1 | TC-PF-I07 |
| AC-58.2 | TC-PF-I08 |
| AC-58.3 | TC-PF-I09 |
| AC-59.1 | TC-PF-I10 |
| AC-59.2 | TC-PF-I11, TC-PF-U08 |
| AC-59.3 | TC-PF-I12, TC-PF-U01 |
| AC-59.4 | TC-PF-I13 |
| AC-59.5 | TC-PF-I14, TC-PF-I15, TC-PF-U02, TC-PF-U05, TC-PF-U06 |
| AC-59.6 | TC-PF-I16 |
| AC-59.7 | TC-PF-I18, TC-PF-U07 |
| AC-59.8 | TC-PF-I19 |
| AC-59.9 | TC-PF-I21 |
| AC-60.1 | TC-PF-I22, TC-PF-E03 |
| AC-60.2 | TC-PF-I23 |
| AC-60.3 | TC-PF-I24 |

## 6. Danh mục test case

### Tầng 1 — Unit (`tests/test_google_unit.py`)

| Mã | Test | Truy vết | Kiểm điều gì |
| --- | --- | --- | --- |
| TC-PF-U01 | `test_a_good_token_gives_a_hash_of_the_subject_and_the_verified_email` | AC-59.3 | Token đúng cho ra mã băm 64 ký tự của `sub`, không chứa `sub`; email đã xác minh và tên (D071) |
| TC-PF-U02 | `test_each_wrong_claim_is_refused` | AC-59.5 | Chín cách sai: issuer, audience, bên được uỷ quyền, hết hạn, cấp ở tương lai, nonce khác hoặc thiếu, thiếu `sub`, thiếu hạn |
| TC-PF-U03 | `test_both_spellings_of_the_google_issuer_are_accepted` | FR-59 | Hai cách viết issuer Google đều nhận |
| TC-PF-U04 | `test_a_token_for_several_audiences_needs_us_as_authorised_party` | FR-59 | Token nhiều audience phải ghi ta là `azp` |
| TC-PF-U05 | `test_a_malformed_token_is_refused` | AC-59.5 | Chuỗi không phải JWT, phần thân không phải JSON object |
| TC-PF-U06 | `test_a_non_ascii_nonce_is_refused_not_crashed` | AC-59.5 | Nonce có dấu bị từ chối thay vì làm máy chủ lỗi 500 |
| TC-PF-U07 | `test_the_domain_rule_needs_the_hd_claim_and_a_verified_email` | AC-59.7 | Giới hạn tên miền cần `hd` và email đã xác minh |
| TC-PF-U08 | `test_a_flow_survives_the_cookie_and_expires_after_ten_minutes` | AC-59.2 | Cookie của luồng đọc lại đúng, quá mười phút thì bỏ, rác thì bỏ |
| TC-PF-U09 | `test_only_same_site_paths_are_kept_as_where_to_go_next` | FR-59 | Không chuyển hướng ra trang ngoài sau khi đăng nhập |
| TC-PF-U10 | `test_a_failed_exchange_says_so_without_leaking_the_reason` | FR-59 | Lỗi mạng hay phản hồi thiếu token thành mã lỗi "exchange" |
| TC-PF-U11 | `test_a_session_gets_a_coarse_device_name_not_a_fingerprint` | AC-57.1 | Tên thiết bị thô cho bảy chuỗi user-agent |
| TC-PF-U12 | `test_an_address_google_has_not_verified_is_not_used` | AC-59.3 | (D071) Email Google chưa xác minh không được dùng để nhận tài khoản |

### Tầng 2 — Integration (`tests/test_profile.py`)

| Mã | Test | Truy vết | Kiểm điều gì |
| --- | --- | --- | --- |
| TC-PF-I01 | `test_a_profile_takes_only_listed_avatars_and_goals` | AC-56.1 | Lưu ba giá trị hợp lệ; ba loại giá trị lạ bị 422; nhật ký ghi trường đã sửa |
| TC-PF-I02 | `test_the_daily_goal_sets_the_target_on_the_path_page` | AC-56.2 | Mục tiêu 10 phút thành 600 giây ở `/api/v1/learn` |
| TC-PF-I03 | `test_the_sidebar_draws_the_chosen_avatar` | AC-56.3 | Trang vẽ đúng lớp màu và biểu tượng đã chọn |
| TC-PF-I04 | `test_the_account_page_has_three_parts_for_a_student_and_two_for_staff` | AC-56.4 | Sinh viên ba mục, giảng viên hai mục; lịch sử nằm trong Bảo mật, mục tiêu ngày ở trang Luyện tập (D068) |
| TC-PF-I05 | `test_a_person_sees_their_sessions_and_ends_one` | AC-57.1 | Hai phiên đúng tên thiết bị; đăng xuất phiên khác, rồi chính phiên này |
| TC-PF-I06 | `test_sessions_of_one_account_cannot_be_ended_by_another` | AC-57.2 | Mã phiên của người khác trả 404 |
| TC-PF-I07 | `test_the_history_shows_sign_ins_failed_attempts_and_changes` | AC-58.1 | Ba sự kiện đúng thứ tự, lý do đăng nhập sai |
| TC-PF-I08 | `test_what_an_administrator_did_shows_as_an_administrator` | AC-58.2 | Việc của quản trị viên không ghi là "bạn" |
| TC-PF-I09 | `test_an_unknown_pseudonym_leaves_nothing_in_the_audit_log` | AC-58.3 | Chuỗi lạ ở ô bút danh không vào nhật ký |
| TC-PF-I10 | `test_google_is_off_until_configured` | AC-59.1 | Không cấu hình thì không có nút, luồng trả về thông báo |
| TC-PF-I11 | `test_start_sends_the_browser_to_google_with_state_nonce_and_pkce` | AC-59.2 | Tham số chuyển hướng và cờ cookie |
| TC-PF-I12 | `test_linking_then_signing_in_with_google` | AC-59.3 | Liên kết, rồi đăng nhập bằng Google; CSDL không có email |
| TC-PF-I13 | `test_with_sign_up_off_an_unlinked_google_account_cannot_sign_in_or_create_one` | AC-59.4 | Tắt đăng ký (`AICEFR_GOOGLE_SIGNUP=0`): tài khoản Google lạ bị từ chối, không tạo tài khoản |
| TC-PF-I25 | `test_an_unlinked_google_account_signs_up_as_a_student` | AC-59.10 | D063: lần đầu tạo sinh viên bút danh ngẫu nhiên, chuyển tới `/terms`; lần sau đăng nhập đúng tài khoản đó |
| TC-PF-I26 | `test_the_login_page_offers_sign_up_only_when_it_is_on` | AC-59.10 | Nút ghi "đăng ký" chỉ khi bật đăng ký |
| TC-PF-I14 | `test_a_forged_or_stale_round_trip_is_refused` | AC-59.5 | Năm cách giả mạo hay quá hạn |
| TC-PF-I15 | `test_a_callback_without_its_cookie_or_after_cancel_is_refused` | AC-59.5 | Thiếu cookie, hoặc người dùng huỷ ở Google |
| TC-PF-I16 | `test_one_google_account_links_to_one_pseudonym` | AC-59.6 | Một tài khoản Google, một bút danh |
| TC-PF-I17 | `test_the_link_must_be_finished_by_the_account_that_started_it` | FR-59 | Đổi phiên giữa chừng thì liên kết bị từ chối |
| TC-PF-I18 | `test_the_domain_restriction_requires_a_verified_school_account` | AC-59.7 | Giới hạn tên miền trọn vòng, tham số `hd` gửi Google |
| TC-PF-I19 | `test_a_disabled_account_cannot_sign_in_with_google` | AC-59.8 | Tài khoản đã tắt bị từ chối |
| TC-PF-I20 | `test_a_temporary_password_still_has_to_be_replaced_after_google` | FR-59 | Google không miễn việc đổi mật khẩu tạm (FR-52) |
| TC-PF-I21 | `test_unlinking_google_by_the_person_or_an_administrator` | AC-59.9 | Gỡ liên kết bởi chính người dùng và bởi quản trị viên |
| TC-PF-I22 | `test_an_administrator_changes_a_role_but_not_their_own` | AC-60.1 | Đổi vai trò có hiệu lực ngay; không tự đổi |
| TC-PF-I23 | `test_an_administrator_signs_an_account_out_everywhere` | AC-60.2 | Đăng xuất mọi phiên; không tự làm |
| TC-PF-I24 | `test_the_account_detail_shows_sessions_link_and_history` | AC-60.3 | Bảng chi tiết đủ dữ liệu, không lộ băm mật khẩu |

### Tầng 3 — E2E (`tests/e2e/test_profile_e2e.py`)

| Mã | Test | Truy vết | Kiểm điều gì |
| --- | --- | --- | --- |
| TC-PF-E01 | `test_a_learner_picks_an_avatar_and_a_daily_goal_and_the_path_follows` | AC-56.1 | Chọn lá và xanh mực, thanh điều khiển đổi ngay; chọn 5 phút, trang Luyện tập ghi /300 |
| TC-PF-E02 | `test_a_session_on_another_device_is_ended_from_the_account_page` | AC-57.1 | Đăng xuất phiên ở máy kia; máy kia bị đưa về trang đăng nhập; lịch sử ghi lại |
| TC-PF-E03 | `test_an_administrator_opens_an_account_and_changes_its_role` | AC-60.1 | Tìm, mở bảng chi tiết, đổi vai trò, lịch sử trong bảng cập nhật |

## 7. Kết quả chạy

| Lệnh | Kết quả |
| --- | --- |
| `pytest tests/test_google_unit.py` | 25 test qua (11 hàm, hai hàm có nhiều trường hợp) |
| `pytest tests/test_profile.py` | 28 test qua (24 hàm, một hàm 5 trường hợp) |
| `pytest -m e2e tests/e2e/test_profile_e2e.py` | 3 test qua |

## 8. Lỗi tìm thấy trong lúc làm

| Mã | Lỗi | Sửa | Test giữ lại |
| --- | --- | --- | --- |
| D029-B1 | So sánh nonce bằng `secrets.compare_digest` trên chuỗi: nonce có ký tự ngoài ASCII làm hàm ném `TypeError`, tức lỗi 500 thay vì từ chối | So sánh trên bytes | TC-PF-U06 |
| D029-B2 | Lần đăng nhập sai hiện "Bạn" trong lịch sử vì nhật ký ghi bút danh bị nhắm tới làm người thực hiện | Lần sai ghi là "Không rõ ai thử" | Kiểm bằng mắt trên trang; TC-PF-I07 giữ lý do |
| D029-B3 | Biến màu ảnh đại diện mặc định có độ ưu tiên CSS cao hơn lớp màu, nên mọi ảnh đại diện đều màu xanh thương hiệu | Đặt giá trị mặc định cùng độ ưu tiên và trước các lớp màu | TC-PF-E01 (kiểm lớp màu trên thanh điều khiển) |
| D029-B4 | Nút "Hiện" mật khẩu rơi xuống dưới ô nhập vì thừa lề trên mặc định của nút | Bỏ lề trong ô mật khẩu | Kiểm bằng mắt trên trang đăng nhập |
| D029-B5 | Test đầu tiên lấy phiên "mới nhất" theo thời điểm tạo, mà hai phiên tạo cùng một giây | Lấy phiên được đánh dấu "máy này" | TC-PF-I12 |
