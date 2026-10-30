# Kế hoạch kiểm thử D065 — tự đăng ký và quên mật khẩu

**Phạm vi:** `/signup`, `/forgot`, `POST /api/v1/auth/signup`, `POST /api/v1/auth/recover`,
`POST /api/v1/me/recovery-code`, thẻ "Mã khôi phục" ở trang Tài khoản, giới hạn tốc độ của ba
đường đăng nhập/đăng ký/khôi phục. Quyết định: D065 (PROPOSED) trong nhật ký quyết định.

## 1. Rủi ro được kiểm

| Rủi ro | Kiểm bằng |
| --- | --- |
| Đăng ký kèm họ tên, email hay vai trò khác sinh viên | `test_sign_up_takes_no_name_and_no_role` |
| Đoán mã khôi phục không giới hạn | `test_guessing_codes_locks_the_account_like_guessing_passwords`, `test_sign_up_is_rate_limited_apart_from_login` |
| Lộ bút danh nào tồn tại | `test_a_wrong_code_and_a_wrong_pseudonym_read_the_same` |
| Mã dùng lại được, hay sống sót sau khi quản trị viên cấp mật khẩu tạm | `test_the_recovery_code_sets_a_new_password_once`, `test_an_administrator_reset_voids_the_recovery_code` |
| Trình duyệt hay proxy giữ mã | `test_a_sign_up_is_not_kept_by_the_browser` (`Cache-Control: no-store`) |
| Vượt số chỗ của gói | `test_sign_up_respects_the_plan_seats` |

## 2. Danh sách test

Tầng tích hợp (I): `tests/test_signup_recovery.py`, ứng dụng thật qua TestClient, kho riêng mỗi
test. Tầng E2E (E): `tests/e2e/test_signup_e2e.py`, Playwright trên máy chủ thật.

| ID | Test |
| --- | --- |
| TC-SR-I01 | `test_recovery_codes_are_long_unlike_and_read_back_however_typed` |
| TC-SR-I02 | `test_a_student_signs_up_with_a_password_and_is_signed_in` |
| TC-SR-I03 | `test_a_sign_up_is_not_kept_by_the_browser` |
| TC-SR-I04 | `test_a_short_password_opens_no_account` |
| TC-SR-I05 | `test_sign_up_takes_no_name_and_no_role` |
| TC-SR-I06 | `test_sign_up_respects_the_plan_seats` |
| TC-SR-I07 | `test_sign_up_can_be_turned_off` |
| TC-SR-I08 | `test_sign_up_is_rate_limited_apart_from_login` |
| TC-SR-I09 | `test_the_recovery_code_sets_a_new_password_once` |
| TC-SR-I10 | `test_the_code_is_read_however_it_was_typed` |
| TC-SR-I11 | `test_a_wrong_code_and_a_wrong_pseudonym_read_the_same` |
| TC-SR-I12 | `test_guessing_codes_locks_the_account_like_guessing_passwords` |
| TC-SR-I13 | `test_an_unacceptable_new_password_spends_nothing` |
| TC-SR-I14 | `test_an_account_without_a_code_cannot_be_recovered` |
| TC-SR-I15 | `test_a_disabled_account_cannot_be_recovered` |
| TC-SR-I16 | `test_an_administrator_reset_voids_the_recovery_code` |
| TC-SR-I17 | `test_a_signed_in_person_makes_a_new_code_and_the_old_one_stops` |
| TC-SR-I18 | `test_making_a_code_needs_a_session` |
| TC-SR-I19 | `test_the_history_shows_sign_up_and_recovery` |
| TC-SR-I20 | `test_an_account_opened_with_google_gets_a_password_through_a_code` |
| TC-SR-I21 | `test_the_login_page_leads_to_sign_up_and_recovery` |
| TC-SR-I22 | `test_sign_up_and_recovery_pages_are_for_the_signed_out` |
| TC-SR-E23 | `test_a_visitor_signs_up_then_resets_a_forgotten_password` |
| TC-SR-E24 | `test_a_signed_in_learner_makes_a_recovery_code_on_the_account_page` |
| TC-SR-I26 | `test_the_login_page_puts_both_links_inside_the_form_card` |

## 3. Kết quả chạy

Ngày 30/10/2026 trên nhánh `feat/d065-dang-ky-va-quen-mat-khau`: tầng I 24/24 qua; tầng E 2/2 qua
trên MongoDB 7.
