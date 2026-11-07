# Kế hoạch và kết quả kiểm thử D095 — Bán gói lượt qua payOS

| Thuộc tính | Giá trị |
| --- | --- |
| Thay đổi | D095: thêm payOS (chuyển khoản VietQR, Napas 24/7) làm một cổng bán gói lượt, cạnh Stripe và cổng thử. Link thanh toán ký bằng checksum key; trả về được đọc lại từ API payOS; webhook chỉ tin khi chữ ký đúng; payOS không có môi trường thử nên chỉ chạy khi `AICEFR_PAYMENTS_LIVE` bật (FR-100) |
| Phiên bản mã | nhánh `feat/d095-payos` |
| Người lập | Võ Thanh Sang |
| Ngày | 07/11/2026 |

## 1. Mục tiêu

1. **Đúng giao thức payOS.** Link mở bằng `x-client-id`, `x-api-key`; chữ ký HMAC-SHA256 trên `amount`, `cancelUrl`, `description`, `orderCode`, `returnUrl` xếp theo tên, tính lại độc lập trong test; mã đơn đổi sang số nguyên và đổi ngược không mất gì.
2. **Không tin địa chỉ trả về.** Trạng thái ghi trong địa chỉ không được dùng: link được đọc lại từ API payOS; link không thuộc đơn nào thì không hỏi payOS.
3. **Webhook có chữ ký.** Chữ ký sai, sửa số tiền, link khác của cùng đơn hay gửi lại đều không cộng lượt thêm; mẫu payOS gửi khi lưu địa chỉ webhook được trả 2xx.
4. **Tiền thật không bao giờ là mặc định.** Thiếu `AICEFR_PAYMENTS_LIVE` thì payOS không được mời; bật lên thì cổng thử tắt.
5. **Không gửi dữ liệu người trả** (BR-32): không có trường `buyer*` nào đi tới payOS.

## 2. Các tầng

| Tầng | Kiểm cái gì | Môi trường | Lệnh |
| --- | --- | --- | --- |
| Unit | Đổi mã đơn, chữ ký link, lời từ chối, đọc lại khi trả về, chữ ký webhook, registry | Bộ chuyển đổi với transport giả, không mạng | `pytest tests/test_d095_payos_unit.py` |
| Integration | Đặt gói, trả qua payOS giả, trang trả về, webhook, bật hay tắt tiền thật | Ứng dụng một tiến trình, MongoDB trong bộ nhớ, `FakePayos` thay API payOS | `pytest tests/test_d095_payos.py` |

## 3. Truy vết tiêu chí chấp nhận

| Tiêu chí chấp nhận | Test case |
| --- | --- |
| AC-100.1 | TC-PO-U01, TC-PO-U02, TC-PO-U07 |
| AC-100.2 | TC-PO-U04, TC-PO-I01 |
| AC-100.3 | TC-PO-U05, TC-PO-I02 |
| AC-100.4 | TC-PO-U04, TC-PO-I03 |
| AC-100.5 | TC-PO-U06, TC-PO-I04 |
| AC-100.6 | TC-PO-U03 |

## 4. Test case

### 4.1. Unit — `tests/test_d095_payos_unit.py`

| Mã | Test | Truy vết | Kết quả mong đợi |
| --- | --- | --- | --- |
| TC-PO-U01 | `test_order_ids_and_payos_order_codes_turn_into_each_other` | AC-100.1 | Mã đơn `DLyymmddXXXXXX` thành số nguyên dưới 2⁵³ và đổi ngược đúng; mã đơn khác dạng bị từ chối; số không thuộc đơn nào cho chuỗi rỗng |
| TC-PO-U02 | `test_the_payment_link_is_signed_the_way_payos_documents` | AC-100.1 | `POST /v2/payment-requests` với hai header khoá; nội dung `SU` + 6 số hex (≤ 9 ký tự); `cancelUrl` có `left=1`; hết hạn sau 16 phút; chữ ký đúng HMAC tính lại; không có trường `buyer*` |
| TC-PO-U03 | `test_payos_refusals_read_as_sentences` | AC-100.6 | 401, mã payOS khác "00", 5xx, không kết nối được, link không phải https đều thành câu tiếng Việt; thiếu khoá nào thì không dựng được cổng |
| TC-PO-U04 | `test_the_return_is_read_back_from_payos_and_its_address_is_not_believed` | AC-100.2 | Địa chỉ ghi PAID nhưng payOS ghi PENDING, trả thiếu tiền hay CANCELLED thì theo payOS; id không phải link payOS thì không gọi API |
| TC-PO-U05 | `test_a_webhook_counts_only_when_its_data_is_signed_with_the_checksum_key` | AC-100.3 | Chữ ký đúng thì là PAID đúng đơn, số tiền, link; khoá khác, sửa số tiền, thân rác đều bị loại; mã khác "00" không thuộc đơn nào; mẫu đơn 123 không trùng đơn thật; webhook không gọi API |
| TC-PO-U06 | `test_payos_moves_real_money_so_it_runs_only_when_switched_on` | AC-100.5 | Chưa bật tiền thật: chỉ còn cổng thử, có câu nhắc `AICEFR_PAYMENTS_LIVE`; bật: chỉ payOS, cổng thử tắt; thiếu checksum key thì có câu nhắc tên biến |
| TC-PO-U07 | `test_every_call_names_this_system_so_cloudflare_lets_it_through` | AC-100.1 | Mọi lời gọi HTTPS mang `User-Agent: SpeakUp/1.0`, không phải `Python-urllib` (Cloudflare của payOS trả 403, lỗi 1010); 403 đọc thành câu có chữ Cloudflare |

### 4.2. Integration — `tests/test_d095_payos.py`

| Mã | Test | Truy vết | Kết quả mong đợi |
| --- | --- | --- | --- |
| TC-PO-I01 | `test_paying_through_payos_is_read_back_and_credited_once` | AC-100.2 | Link 49.000 đồng, địa chỉ trả về `/billing/return/payos`; trả xong trang "Thanh toán thành công", ví +10 lượt; mở lại không hỏi payOS và không cộng thêm |
| TC-PO-I02 | `test_the_payos_webhook_alone_credits_the_runs_once` | AC-100.3 | Chữ ký sai 400; sai số tiền, link khác: 200 và không cộng; đúng: cộng 10 lượt một lần; gửi lại và mẫu của bảng điều khiển không cộng thêm |
| TC-PO-I03 | `test_a_return_address_alone_proves_nothing` | AC-100.4 | Địa chỉ ghi PAID khi payOS chưa nhận tiền không cộng lượt; link lạ không hỏi payOS; `left=1` không hỏi payOS, đơn vẫn chờ |
| TC-PO-I04 | `test_payos_is_offered_only_when_real_money_is_switched_on` | AC-100.5 | Thiếu `AICEFR_PAYMENTS_LIVE`: danh sách cổng chỉ có cổng thử, đặt qua payOS bị từ chối, ví không đổi |

## 5. Kết quả

| Lệnh | Kết quả |
| --- | --- |
| `pytest tests/test_d095_payos_unit.py` | 7 passed |
| `pytest tests/test_d095_payos.py` | 4 passed |

**Giới hạn (`NOT_RUN`):** chưa thử với payOS thật. payOS không có môi trường thử; muốn thử thật phải bật `AICEFR_PAYMENTS_LIVE`, điền ba khoá của kênh thanh toán và chuyển một khoản nhỏ bằng tiền thật. Công thức chữ ký webhook theo trang "Kiểm tra dữ liệu với signature" của payOS ngày 07/11/2026; đối chiếu lại nếu payOS đổi tài liệu.
