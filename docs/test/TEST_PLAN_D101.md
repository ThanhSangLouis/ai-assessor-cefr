# Kế hoạch và kết quả kiểm thử D101 — Lượt miễn phí cần email đã xác minh, sinh viên tự xoá tài khoản

| Thuộc tính | Giá trị |
| --- | --- |
| Thay đổi | D101: lượt miễn phí của tháng và bản ghi miễn phí trong ngày chỉ dành cho tài khoản đã xác minh email (FR-103); sinh viên tự xoá tài khoản ở trang Tài khoản (FR-104) |
| Phiên bản mã | nhánh `feat/mien-phi-va-xoa-tai-khoan` |
| Người lập | Võ Thanh Sang |
| Ngày | 08/11/2026 |

## 1. Mục tiêu

1. **Không lấy được lượt miễn phí bằng nhiều tài khoản.** Tài khoản tự đăng ký chưa xác minh email chỉ dùng lượt đã mua.
2. **Xác minh là có lại ngay.** Nhập đúng mã thì có đủ lượt miễn phí của tháng.
3. **Không làm khó tài khoản do quản trị viên tạo** (không có email).
4. **Người học tự xoá được mình**, xoá thật (bài nói, bản ghi âm, tài khoản, phiên), mà sổ sách tiền vẫn còn.
5. **Không xoá nhầm.** Phải gõ lại email; giảng viên và quản trị viên không xoá ở đây.

## 2. Các tầng

| Tầng | Kiểm cái gì | Môi trường | Lệnh |
| --- | --- | --- | --- |
| Integration | Lượt miễn phí theo trạng thái email, tự xoá tài khoản, trang Tài khoản | Ứng dụng một tiến trình, tính lượt bật, email vào hộp thư giả, MongoDB | `pytest tests/test_d101_free_runs_and_delete.py` |

## 3. Truy vết tiêu chí chấp nhận

| Tiêu chí chấp nhận | Test case |
| --- | --- |
| AC-103.1 | TC-FD-I01 |
| AC-103.2 | TC-FD-I02 |
| AC-103.3 | TC-FD-I03 |
| AC-103.4 | TC-FD-I04 |
| AC-103.5 | TC-FD-I05 |
| AC-104.1 | TC-FD-I06 |
| AC-104.2 | TC-FD-I07 |
| AC-104.3 | TC-FD-I08 |
| AC-104.4 | TC-FD-I09 |
| AC-104.5 | TC-FD-I10 |

## 4. Test case

| Mã | Test | Truy vết | Kết quả mong đợi |
| --- | --- | --- | --- |
| TC-FD-I01 | `test_an_unverified_email_gets_no_free_runs` | AC-103.1 | `free_locked` true, 0 lượt miễn phí, `free_runs_per_cycle` 3; báo giá cũng `free_locked`; nộp bài 402 có "Xác minh email" |
| TC-FD-I02 | `test_verifying_the_email_opens_the_free_runs` | AC-103.2 | Sau mã đúng: `free_locked` false, 3 lượt; nộp bài 202 |
| TC-FD-I03 | `test_an_unverified_learner_still_spends_bought_runs` | AC-103.3 | Quản trị viên cộng 2 lượt; nộp bài 202; bút toán `from_free` 0, `from_wallet` > 0 |
| TC-FD-I04 | `test_no_free_lesson_recording_before_verifying` | AC-103.4 | Báo giá bài học `free_locked` true, 0 bản ghi miễn phí; giữ chỗ 402 có "Xác minh email"; hôm nay vẫn 0 bản ghi đã đếm |
| TC-FD-I05 | `test_an_account_made_by_an_administrator_keeps_its_free_runs` | AC-103.5 | Tài khoản không email: `free_locked` false, 3 lượt, nộp được |
| TC-FD-I06 | `test_a_learner_deletes_their_own_account` | AC-104.1 | 200, `responses` 1; không còn bài nói, không còn tài khoản; phiên cũ 401; đăng nhập lại không được |
| TC-FD-I07 | `test_the_confirmation_must_match_the_email` | AC-104.2 | Gõ mã tài khoản thay email: 422, tài khoản còn; gõ email viết hoa, thừa khoảng trắng: 200 |
| TC-FD-I08 | `test_staff_cannot_delete_themselves_here` | AC-104.3 | Giảng viên 403, tài khoản còn |
| TC-FD-I09 | `test_payments_and_the_ledger_stay` | AC-104.4 | Bút toán của bài vẫn còn sau khi xoá |
| TC-FD-I10 | `test_the_account_page_offers_the_delete_card_to_students_only` | AC-104.5 | Trang của sinh viên có `delete-form` và "Xoá vĩnh viễn"; của giảng viên thì không |

## 5. Kết quả

| Lệnh | Kết quả |
| --- | --- |
| `pytest tests/test_d101_free_runs_and_delete.py` | 10 passed |
| Các test tính lượt có sẵn (`test_metering*`, `test_d094_*`, `test_d090_*`, `test_d072_*`, `test_credit_packs`) | passed; hai test so khớp báo giá bài học thêm trường `free_locked` |
