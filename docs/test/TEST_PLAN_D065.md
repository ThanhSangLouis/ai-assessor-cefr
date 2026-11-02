# Kế hoạch kiểm thử D065 — tự đăng ký và quên mật khẩu

**Phạm vi:** `/signup`, `/forgot`, `POST /api/v1/auth/signup`, giới hạn tốc độ của đăng nhập và
đăng ký. Quyết định: D065, D071 trong nhật ký quyết định. D081 (01/11/2026) gỡ mã khôi phục:
quên mật khẩu chỉ còn mã gửi qua email, kiểm ở `tests/test_d079_email.py`.

## 1. Rủi ro được kiểm

| Rủi ro | Kiểm bằng |
| --- | --- |
| Đăng ký tự chọn bút danh hay vai trò khác sinh viên | `test_sign_up_chooses_no_pseudonym_and_no_role` |
| Mở tài khoản hàng loạt | `test_sign_up_is_rate_limited_apart_from_login` |
| Trình duyệt hay proxy giữ phản hồi đăng ký | `test_a_sign_up_is_not_kept_by_the_browser` (`Cache-Control: no-store`) |
| Đường mã khôi phục còn sót sau D081 | `test_the_recovery_code_routes_are_gone`, `test_migration_12_removes_the_stored_codes` |

## 2. Danh sách test

Tầng tích hợp (I): `tests/test_signup.py`, ứng dụng thật qua TestClient, kho riêng mỗi
test. Tầng E2E (E): `tests/e2e/test_signup_e2e.py`, Playwright trên máy chủ thật.

| ID | Test |
| --- | --- |
| TC-SR-I01 | `test_a_student_signs_up_with_a_password_and_is_signed_in` |
| TC-SR-I02 | `test_a_sign_up_is_not_kept_by_the_browser` |
| TC-SR-I03 | `test_a_short_password_opens_no_account` |
| TC-SR-I04 | `test_sign_up_chooses_no_pseudonym_and_no_role` |
| TC-SR-I05 | `test_sign_up_can_be_turned_off` |
| TC-SR-I06 | `test_sign_up_is_rate_limited_apart_from_login` |
| TC-SR-I07 | `test_the_recovery_code_routes_are_gone` |
| TC-SR-I08 | `test_migration_12_removes_the_stored_codes` |
| TC-SR-I09 | `test_the_login_page_leads_to_sign_up_and_a_forgotten_password` |
| TC-SR-I10 | `test_sign_up_and_forgot_pages_are_for_the_signed_out` |
| TC-SR-I11 | `test_the_login_page_puts_both_links_inside_the_form_card` |
| TC-SR-E12 | `test_a_visitor_signs_up_and_a_forgotten_password_names_whom_to_ask` |

## 3. Kết quả chạy

Ngày 01/11/2026 trên nhánh `feat/d081-remove-recovery-code` (D081): tầng I chạy cùng toàn bộ test; tầng E chạy trên MongoDB 7 trước khi mở PR.
