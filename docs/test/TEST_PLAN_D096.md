# Kế hoạch và kết quả kiểm thử D096 — Email cho luồng thanh toán

| Thuộc tính | Giá trị |
| --- | --- |
| Thay đổi | D096: đơn gói lượt kết thúc đã thanh toán thì người mua nhận email biên nhận, không thành công thì nhận email báo; chỉ tới email đã xác minh, mỗi đơn một email. Thanh toán phát `billing.order_settled` trên bus, dịch vụ định danh nhận và gửi (FR-101) |
| Phiên bản mã | nhánh `feat/d095-payos` |
| Người lập | Võ Thanh Sang |
| Ngày | 07/11/2026 |

## 1. Mục tiêu

1. **Đúng người, đúng lúc.** Chỉ người mua, chỉ email đã xác minh, chỉ khi đơn đã thanh toán hoặc không thành công; huỷ và cổng không mở được trang thì không gửi.
2. **Một đơn, một email.** Trình duyệt và máy chủ của cổng cùng báo kết quả, hoặc bus giao lại sự kiện, cũng chỉ có một email.
3. **Không lộ gì.** Không mật khẩu, số thẻ, khoá; không liên kết hỏng khi thiếu địa chỉ công khai.
4. **Email không làm hỏng thanh toán.** Tắt email hay bộ gửi lỗi thì đơn vẫn chốt, lượt vẫn vào ví.

## 2. Các tầng

| Tầng | Kiểm cái gì | Môi trường | Lệnh |
| --- | --- | --- | --- |
| Integration | Đăng ký và xác minh email, mua qua cổng thử, sự kiện trên bus, hộp thư giả, giao lại sự kiện, tắt email | Ứng dụng một tiến trình, `InlineBus`, MongoDB trong bộ nhớ, `AICEFR_EMAIL_PROVIDER=outbox` | `pytest tests/test_d096_payment_email.py` |

## 3. Truy vết tiêu chí chấp nhận

| Tiêu chí chấp nhận | Test case |
| --- | --- |
| AC-101.1 | TC-PE-I01 |
| AC-101.2 | TC-PE-I02 |
| AC-101.3 | TC-PE-I03 |
| AC-101.4 | TC-PE-I04, TC-PE-I07 |
| AC-101.5 | TC-PE-I05 |
| AC-101.6 | TC-PE-I06 |

## 4. Test case — `tests/test_d096_payment_email.py`

| Mã | Test | Truy vết | Kết quả mong đợi |
| --- | --- | --- | --- |
| TC-PE-I01 | `test_a_paid_order_emails_its_buyer_a_receipt_once` | AC-101.1 | Một email tới đúng địa chỉ; tiêu đề "Đã thanh toán gói 10 lượt · <mã đơn>"; có tên, 49.000 đ, cổng, mã đơn, liên kết biên nhận (văn bản và HTML), lưu ý môi trường thử; mở biên nhận không gửi thêm; ví +10 |
| TC-PE-I02 | `test_a_failed_payment_says_so_and_nothing_was_taken` | AC-101.2 | Tiêu đề "Thanh toán chưa thành công"; "Không có lượt nào bị trừ hay được cộng"; liên kết `/credits`, không có biên nhận; ví 0 |
| TC-PE-I03 | `test_only_a_verified_address_hears_and_a_cancel_says_nothing` | AC-101.3 | Huỷ: không email; tài khoản không có email đã xác minh trả tiền: không email, ví +10 |
| TC-PE-I04 | `test_a_second_delivery_of_the_event_sends_no_second_email` | AC-101.4 | Gọi lại bộ xử lý với cùng sự kiện: trả False, hộp thư vẫn một email |
| TC-PE-I05 | `test_the_payment_email_says_what_was_bought_and_nothing_secret` | AC-101.5 | Có số tiền, cổng, mã giao dịch, lời dặn báo quản trị viên; tiền thật thì không có lưu ý thử; không chữ "mật khẩu", "số thẻ", khoá; không có địa chỉ công khai thì không có liên kết |
| TC-PE-I06 | `test_with_email_off_a_payment_still_settles` | AC-101.6 | Email tắt: đơn đã thanh toán, ví +10, hộp thư trống |
| TC-PE-I07 | `test_the_order_event_crosses_redis_and_one_email_goes_out` | AC-101.4 | Chỉ chạy khi có `AICEFR_TEST_REDIS` (CI có): sự kiện đi qua Redis Streams thật với consumer group; gửi cùng sự kiện hai lần, bộ xử lý chạy hai lần, chỉ một email đi |

## 5. Kết quả

| Lệnh | Kết quả |
| --- | --- |
| `pytest tests/test_d096_payment_email.py` | 6 passed |

**Giới hạn (`NOT_RUN`):** chưa gửi qua Resend thật trong kiểm thử (hộp thư giả). Trên production, email đi qua Resend với `AICEFR_EMAIL_FROM` đã cấu hình (D079); với Redis, sự kiện được giao ít nhất một lần và dấu `payment_email:<đơn>:<trạng thái>` chặn email thứ hai.
