# Kế hoạch và kết quả kiểm thử D099 — Lưới an toàn khi bán lượt bằng tiền thật

| Thuộc tính | Giá trị |
| --- | --- |
| Thay đổi | D099: tự đối soát đơn còn mở với payOS, giới hạn đơn chờ, tab Đơn hàng cho quản trị viên, trang điều khoản và hoàn tiền (FR-102); Lượt của tôi và form giá làm lại; E2E payOS với payOS giả cục bộ |
| Phiên bản mã | nhánh `feat/thanh-toan-an-toan` |
| Người lập | Võ Thanh Sang |
| Ngày | 07/11/2026 |

## 1. Mục tiêu

1. **Không mất tiền.** Khoản đã chuyển mà webhook không tới và người mua đóng trang vẫn được cộng lượt, đúng một lần.
2. **Không mở link vô hạn.** Một người không giữ quá năm đơn chờ trong mười phút.
3. **Quản trị viên thấy tiền.** Doanh thu từng ngày, đơn theo trạng thái, sự kiện của từng đơn; người khác không đọc được.
4. **Người mua biết luật trước khi trả.** Trang điều khoản mở cho mọi người và có liên kết ở chỗ mua.
5. **Cả luồng chạy trong trình duyệt** với payOS giả, không request nào ra ngoài.

## 2. Các tầng

| Tầng | Kiểm cái gì | Môi trường | Lệnh |
| --- | --- | --- | --- |
| Unit | Bộ gọi HTTP chỉ cho http tới 127.0.0.1; trang http chỉ nhận từ payOS cục bộ; `look_up` | Không ứng dụng, không mạng | `pytest tests/test_d099_payment_safety_unit.py` |
| Integration | Đối soát, giới hạn, API quản trị, trang điều khoản | Ứng dụng một tiến trình, payOS giả trên transport, MongoDB | `pytest tests/test_d099_payment_safety.py` |
| E2E | Mua gói → trang payOS → trang thành công → biên nhận → ví | Uvicorn thật, Chromium, payOS giả là máy chủ HTTP trên 127.0.0.1 | `pytest -m e2e tests/e2e/test_d099_payos_e2e.py` |

## 3. Truy vết tiêu chí chấp nhận

| Tiêu chí chấp nhận | Test case |
| --- | --- |
| AC-102.1 | TC-PG-I01 |
| AC-102.2 | TC-PG-I02 |
| AC-102.3 | TC-PG-I04 |
| AC-102.4 | TC-PG-I06 |
| AC-102.5 | TC-PG-I07 |
| AC-102.6 | TC-PG-I08 |

## 4. Test case

| Mã | Test | Truy vết | Kết quả mong đợi |
| --- | --- | --- | --- |
| TC-PG-U01 | `test_plain_http_reaches_only_this_machine` | FR-102 | `http://127.0.0.1:9/` được thử (không có ai nghe nên `Unreachable`); `localhost`, `127.0.0.1.example.com`, `10.0.0.1` bị từ chối trước khi gửi |
| TC-PG-U02 | `test_a_payment_page_over_http_comes_only_from_a_payos_on_this_machine` | FR-102 | payOS thật trả link `http://` thì `GatewayError`; payOS cục bộ thì nhận, và gọi đúng địa chỉ cục bộ |
| TC-PG-U03 | `test_look_up_reads_a_link_back_by_its_id` | FR-102 | GET `/v2/payment-requests/{id}`; đọc ra mã đơn, đã trả, mã link; id không đúng dạng thì `None`, không gọi |
| TC-PG-I01 | `test_reconcile_credits_a_payment_nobody_reported` | AC-102.1 | Lần đầu trả về mã đơn, lần hai rỗng; ví +10; có sự kiện `reconcile` và `credited` |
| TC-PG-I02 | `test_reconcile_leaves_an_unpaid_link_waiting` | AC-102.2 | Đơn vẫn `pending`; sự kiện chỉ có `created` |
| TC-PG-I03 | `test_reconcile_skips_a_gateway_that_cannot_be_asked` | FR-102 | Đơn cổng thử vẫn `pending`, đối soát trả rỗng |
| TC-PG-I04 | `test_too_many_waiting_orders_are_refused` | AC-102.3 | Đơn thứ sáu 429 "đơn chờ thanh toán"; payOS giả chỉ có năm link; người khác đặt được |
| TC-PG-I05 | `test_a_paid_order_frees_its_place` | FR-102 | Năm đơn chờ, trả một đơn, đặt thêm được |
| TC-PG-I06 | `test_the_administrator_sees_every_order_and_the_money_of_each_day` | AC-102.4 | Đơn mới nhất trước, người mua `SV-001`, `{paid: 1, pending: 1}`, 14 ngày với hôm nay 1 đơn 49.000 đ; lọc `paid`; sự kiện `created`, `return`; trạng thái lạ 422 |
| TC-PG-I07 | `test_only_the_administrator_reads_the_orders` | AC-102.5 | Sinh viên và giảng viên: 403 cho danh sách và sự kiện |
| TC-PG-I08 | `test_the_terms_are_open_and_linked_from_the_buy_page` | AC-102.6 | 200 không cần đăng nhập; có "Hoàn tiền 7 ngày", email liên hệ, "không phải hoá đơn VAT"; `/credits` có liên kết |
| TC-PG-E01 | `test_a_learner_pays_through_payos_and_gets_a_receipt` | FR-102 | Nhãn "Không hết hạn" và liên kết điều khoản; trang payOS giả hiện 49000; quay về "Thanh toán thành công", "10 lượt"; biên nhận 49.000; Lượt của tôi có "Đã thanh toán" và 10 lượt đã mua |

## 5. Kết quả

| Lệnh | Kết quả |
| --- | --- |
| `pytest tests/test_d099_payment_safety_unit.py` | 3 passed |
| `pytest tests/test_d099_payment_safety.py` (MongoDB thật) | 8 passed |
| `pytest -m e2e tests/e2e/test_d099_payos_e2e.py` | 1 passed |

**Giới hạn (`NOT_RUN`):** chưa đối soát với payOS thật trong kiểm thử (payOS không có môi trường thử). Vòng đối soát chỉ chạy khi `AICEFR_JOB_MODE` khác `inline`, tức trên production. Bảy ngày hoàn tiền, 30 phút và 5 ngày làm việc trên trang điều khoản là mặc định chờ chủ dự án xác nhận.
