# Kế hoạch và kết quả kiểm thử D035 — Nhiều cổng thanh toán: Stripe và MoMo

> **D075 (01/11/2026):** chỉ còn Stripe và cổng thử; VNPay, MoMo và các test của chúng (TC-CT-U06, U07, I08; AC-73.x) đã gỡ. Người mua là học viên hay giảng viên mua gói lượt, không còn quản trị viên mua gói của trường: TC-CT-I02, I09, E01 đổi tên theo đó.

> **D097 (07/11/2026):** Stripe đã gỡ khỏi hệ thống; payOS (D095) là cổng thật duy nhất. Test của riêng Stripe (TC-CT-U01..U05, I01..I03, I06, I10) và e2e chọn cổng (TC-CT-E01..E03) đã gỡ, cùng AC-71.1, 71.3, 71.6, 71.7 và AC-72.x. Các luật chung của mọi cổng (TC-CT-U08, U09, U10, I04, I05, I07, I09) chạy với payOS.

| Thuộc tính | Giá trị |
| --- | --- |
| Tính năng | D035: nhiều cổng thanh toán cùng lúc, quản trị viên chọn cổng cho từng đơn; Stripe Checkout ở chế độ thử (mở phiên bằng API, đọc lại phiên, webhook có chữ ký); ví MoMo ở môi trường thử (yêu cầu, kết quả và IPN có chữ ký); tiền thật phải bật riêng (FR-71..FR-73, BR-34, BR-35, UC-23) |
| Phiên bản mã | nhánh `feat/billing` |
| Người lập | Võ Thanh Sang |
| Ngày | 07/10/2026 |

## 1. Mục tiêu

1. **Chỉ tin điều cổng xác nhận.** Kết quả của Stripe chỉ đến từ chính API của Stripe (đọc lại phiên bằng khoá bí mật) hoặc từ webhook có chữ ký đúng trong năm phút; kết quả của MoMo chỉ khi chữ ký, mã đối tác và số tiền đều đúng. Mã phiên trên địa chỉ là lời khai, không phải bằng chứng.
2. **Một cổng không ghi nhận đơn của cổng khác**, và hệ thống chỉ hỏi Stripe về phiên do chính nó mở (BR-35).
3. **Tiền thật không bao giờ là mặc định** (BR-34): mọi cổng ở môi trường thử của nó; cổng thu tiền thật cần một biến riêng; cổng thử không chạy cạnh cổng thật.
4. **Lỗi của cổng thành câu người đọc hiểu**: cổng từ chối, mất kết nối, rời trang cổng, chưa xác nhận được — mỗi trường hợp có một câu và đơn ở đúng trạng thái.
5. **Không giữ gì của người trả** (BR-32): chỉ mã phiên và mã giao dịch, không email, tên hay thẻ.

## 2. Ba tầng kiểm thử

| Tầng | Kiểm cái gì | Công cụ | Môi trường | Chạy ở đâu | Lệnh |
| --- | --- | --- | --- | --- | --- |
| 1. Unit | Yêu cầu mở phiên Stripe, cách đọc lại phiên, chữ ký webhook, chế độ theo khoá; yêu cầu và kết quả MoMo; dựng các cổng từ cấu hình | pytest | Không ứng dụng, không CSDL, không mạng: mỗi bộ chuyển đổi nhận một `transport` giả | Máy và CI | `pytest tests/test_gateways_unit.py` |
| 2. Integration | Trọn vòng Stripe qua API giả (trả về, webhook, rời trang, hết hạn, không mở được, không xác nhận được, chỉ hỏi phiên của mình); trọn vòng MoMo qua IPN; chọn cổng; tiền thật; một cổng không ghi nhận đơn của cổng khác | pytest, FastAPI TestClient | SQLite thật trên tệp tạm; `FakeStripe` giữ phiên như API của Stripe, `FakeMomo` trả lời như điểm tạo giao dịch của MoMo; sự kiện và IPN ký trong test theo cách mỗi cổng công bố | Máy và CI | `pytest tests/test_gateways.py` |
| 3. E2E | Đã gỡ bởi D097 (chỉ còn một cổng chạy mỗi lúc) | — | — | — | — |

**Không test nào gọi Stripe hay MoMo thật.** Cần khoá của chủ dự án, và test phải chạy không có mạng (AGENTS.md). Các chi tiết của hai cổng đã đối chiếu với tài liệu chính thức ngày 07/10/2026 — với Stripe: tham số Checkout Session (`expires_at` 30 phút tới 24 giờ, `locale=vi`, `{CHECKOUT_SESSION_ID}` trong `success_url`), cách ký webhook (`t`, `v1`, HMAC-SHA256 trên `<t>.<thân>`, dung sai năm phút, bỏ mọi lược đồ khác `v1`), VND không có đơn vị lẻ; với MoMo: đường dẫn `/v2/gateway/api/create`, thứ tự trường của hai chuỗi ký, mức 1.000–50.000.000 đ, bảng mã kết quả, trả lời IPN bằng 204 trong 15 giây. Test tính lại chữ ký bằng thư viện chuẩn theo đúng mô tả đó thay vì tin bộ chuyển đổi. Chạy với khoá thử thật là bước của chủ dự án theo `docs/plan/CAU_HINH_KHOA_BEN_NGOAI.md`.

## 3. Dữ liệu và môi trường

- Khoá trong test là chuỗi dựng bằng phép nối (ví dụ `"sk_test_51Thu" + "x" * 20`), không phải khoá thật và không có chuỗi dài nào để bộ quét lộ khoá báo nhầm.
- Giá là giá minh hoạ (Chuẩn 10.000 đ mỗi sinh viên mỗi tháng); đơn thử 50 sinh viên 6 tháng là 3.000.000 đ.
- Không có dữ liệu người học thật. Phiên Stripe giả có `customer_details` với email và tên bịa, để kiểm rằng hệ thống không giữ chúng.

## 4. Tiêu chí vào và ra

- **Vào:** mã qua `ruff format --check` và `ruff check`.
- **Ra (được merge):** 100% test tầng 1 và 2 qua trên CI; 100% test tầng 3 qua trên máy trước khi merge; mọi tiêu chí AC-71.1..AC-73.3 có ít nhất một test (kiểm bằng `tests/test_product_traceability.py`).

## 5. Truy vết tiêu chí chấp nhận

Tiêu chí chấp nhận AC-71.1..AC-73.3 nằm ở `docs/srs/SRS.md`, mục 3.9h.

| Tiêu chí chấp nhận | Test case |
| --- | --- |
| AC-71.2 | TC-CT-U08 |
| AC-71.4 | TC-CT-U09 |
| AC-71.5 | TC-CT-I07 |

## 6. Danh mục test case

### Tầng 1 — Unit (`tests/test_gateways_unit.py`)

| Mã | Test | Truy vết | Kiểm điều gì |
| --- | --- | --- | --- |
| TC-CT-U08 | `test_the_registry_builds_what_the_settings_ask_for` | AC-71.2 | Dòng trống trong `.env` là mặc định (`sandbox`); tên viết hoa, khoảng trắng được chuẩn hoá; thiếu khoá payOS nêu tên biến; `stripe`, `momo`, `vnpay` là tên lạ (D075, D097); tên lặp chỉ báo một lần |
| TC-CT-U09 | `test_real_money_is_never_a_default` | AC-71.4 | payOS đủ khoá nhưng chưa bật `AICEFR_PAYMENTS_LIVE`: chỉ còn cổng thử, có câu nhắc biến; bật: chỉ payOS, cổng thử tắt |
| TC-CT-U10 | `test_a_gateway_call_never_follows_a_redirect` | FR-71 | Bộ gọi HTTPS trả chuyển hướng về chứ không đi theo (khoá của cổng không bị mang tới máy khác); chỉ gọi `https://` (D035-B12) |

### Tầng 2 — Integration (`tests/test_gateways.py`)

| Mã | Test | Truy vết | Kiểm điều gì |
| --- | --- | --- | --- |
| TC-CT-I04 | `test_a_gateway_that_will_not_open_fails_the_order_with_a_reason` | FR-71 | payOS từ chối mở link (mã 231), rồi không kết nối được: 502 với câu bắt đầu bằng "payOS: ", đơn thành không thành công với mã của cổng, không đơn nào còn chờ |
| TC-CT-I05 | `test_a_return_the_gateway_cannot_confirm_says_so` | FR-71 | Trình duyệt quay về lúc không hỏi được payOS: "Chưa xác nhận được với payOS", đơn vẫn chờ; hỏi lại được thì thành công |
| TC-CT-I07 | `test_one_gateway_cannot_settle_another_gateways_order` | AC-71.5 | Kết quả có chữ ký của cổng thử cho một đơn payOS: không có địa chỉ thông báo của cổng thử cạnh tiền thật, `settle` trả `not_found`, đơn vẫn chờ và có sự kiện `rejected`; cùng payOS nhưng khác chế độ tiền cũng không chốt |
| TC-CT-I09 | `test_the_problems_of_the_gateways_are_logged` | FR-71 | Cấu hình `stripe, momo, payos, sandbox` không có khoá: chỉ còn cổng thử; nhật ký nêu `stripe`, `momo` là tên lạ và payOS thiếu `AICEFR_PAYOS_CLIENT_ID`; đặt qua `stripe` bị từ chối (422); đơn không nêu cổng đi cổng đầu tiên |

### Tầng 3 — E2E

Đã gỡ bởi D097: ba test chọn cổng và rời trang Stripe không còn ý nghĩa khi chỉ một cổng chạy mỗi lúc. Trang kết quả và biên nhận vẫn có e2e ở `tests/e2e/test_billing_e2e.py`.

## 7. Kết quả chạy

| Lệnh | Kết quả |
| --- | --- |
| `pytest tests/test_gateways_unit.py` (sau D097) | 3 test qua |
| `pytest tests/test_gateways.py` (sau D097, với payOS giả) | 4 test qua |
| `pytest tests/test_billing_unit.py tests/test_billing.py` (D034, sau khi cổng đổi hình) | 36 test qua |
| `pytest -m "not e2e and not slow"` (hồi quy, có đo độ phủ, cùng lần với D036, sau các sửa của lần rà bảo mật) | 1149 test: 1139 qua, 10 bỏ qua theo thiết kế (kiểm tra sơ đồ chỉ áp cho một loại hình); độ phủ toàn bộ 93%; `billing/registry.py`, `billing/payments.py` 100%, `storage/billing_repository.py` 99%, `billing/stripe_gateway.py` 98%, `billing/service.py` 96%, `billing/gateways.py` 96%, `billing/momo_gateway.py` 93%, `api/billing_api.py` 93%; `billing/transport.py` 63% — phần còn lại là lời gọi mạng thật, không test nào được chạm |
| `pytest -m e2e tests/e2e` (hồi quy, cùng lần với D036) | 65 test qua (60 sẵn có, 3 của D035, 2 của D036) |

## 8. Lỗi và chỗ hở tìm thấy trong lúc làm

| Mã | Lỗi | Sửa | Giữ lại bằng |
| --- | --- | --- | --- |
| D035-B1 | Một tên cổng lặp trong cấu hình mà thiếu khoá bị báo hai lần | Dựng mỗi tên một lần | TC-CT-U08 |
| D035-B2 | Tên cổng trên nút thanh toán được chèn trong một chuỗi mẫu; test hợp đồng giao diện coi đó là chèn HTML không escape | Ghép chữ thuần ngoài chuỗi mẫu rồi đặt bằng `textContent` | `tests/test_frontend_contracts.py` |
| D035-B3 | Trang trả về hỏi Stripe về **bất kỳ** mã phiên đúng dạng nào: người ngoài gửi mã bịa liên tục là tiêu hạn mức gọi API của hệ thống | Chỉ hỏi khi mã phiên là của một đơn (`order_by_checkout`) | TC-CT-I06 |
| D035-B4 | Một dòng `AICEFR_PAYMENT_GATEWAYS=` trống trong `.env` nghĩa là không có cổng nào | Trống được hiểu như không đặt: cổng thử | TC-CT-U08 |
| D035-B5 | Một ghi chú trong sơ đồ tuần tự Stripe có dấu `;`, Mermaid hiểu là hết câu lệnh nên không vẽ được | Đổi dấu | `test_every_mermaid_source_is_rendered_and_shown` |
| D035-B6 | Đổi nghĩa có chủ ý: địa chỉ sandbox của VNPay nay được ghi là môi trường thử (không có tiền thật), nên trang kết quả của VNPay sandbox có dòng "Môi trường thử của VNPay" | Sửa AC-69.9 trong SRS 1.7 và test TC-GD-I18 của D034 | TC-GD-I18 |
| D035-B7 | Rà bảo mật độc lập (mức cao): bật tiền thật mà vẫn để Stripe ở khoá thử cạnh VNPay thật thì trả bằng thẻ thử 4242 ra gói thật — luật cũ chỉ bỏ cổng thử trong ứng dụng, và `settle` không so chế độ tiền | Có cổng thật thì bỏ **mọi** cổng ở môi trường thử; `settle` từ chối kết quả khi chế độ tiền của cổng khác của đơn | TC-CT-U09, TC-CT-I07 |
| D035-B8 | Rà bảo mật: webhook ghi nhận đơn theo `client_reference_id` mà không so mã phiên, nên một phiên do tích hợp khác trên cùng tài khoản Stripe mở trả được đơn này | `PaymentResult.checkout` phải là `checkout_ref` của đơn | TC-CT-I02 |
| D035-B9 | Rà bảo mật: phát lại địa chỉ trả về của một đơn Stripe đã xong vẫn gọi Stripe mỗi lần và thêm một dòng sự kiện mỗi lần — tiêu hạn mức gọi API và làm phình bảng | Đơn đã xong hiện từ CSDL; thông điệp lặp y hệt được đếm (`repeats`) | TC-CT-I01, TC-CT-I08, TC-GD-I07 |
| D035-B10 | Rà bảo mật: giới hạn 256 KiB của thân thông báo chỉ xét sau khi đã giữ hết thân trong bộ nhớ | Xét `Content-Length`, rồi đếm byte khi đọc | TC-CT-I02 |
| D035-B11 | Rà bảo mật: tiêu đề `Stripe-Signature` có `t=²`, chữ ký MoMo, VNPay hay cổng thử có ký tự không phải ASCII, thân MoMo lồng quá sâu làm máy chủ lỗi 500 thay vì từ chối | `same_text`, `digits`; bắt mọi lỗi khi đọc thông điệp từ ngoài như sai chữ ký | TC-CT-U04, TC-CT-U07, TC-GD-U15, TC-GD-U16, TC-CT-I02 |
| D035-B12 | Rà bảo mật: bộ gọi HTTPS đi theo chuyển hướng và mang `Authorization: Bearer sk_…` theo | Không đi theo chuyển hướng; 3xx là một lời từ chối | TC-CT-U02 |
| D035-B13 | Rà bảo mật (chưa xác minh, đã xác minh lại với bảng mã của MoMo): mọi mã ngoài danh sách chờ đều thành không thành công, là trạng thái cuối, nên một kết quả thành công đến sau sẽ không được ghi nhận | Chỉ các mã MoMo ghi là thất bại cuối mới là không thành công; mã khác là chưa xong | TC-CT-U07 |
