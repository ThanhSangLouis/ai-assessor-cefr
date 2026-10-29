# Kế hoạch và kết quả kiểm thử D035 — Nhiều cổng thanh toán: Stripe và MoMo

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
| 3. E2E | Ô "Thanh toán qua", biểu ngữ, mua qua cổng được chọn, cột Cổng trong bảng đơn, trang rời trang thanh toán, điện thoại | Playwright + Chromium | Máy chủ uvicorn riêng với Stripe (khoá có dạng khoá thử nhưng không phải khoá thật) và cổng thử | **Chỉ trên máy**; CI tự bỏ qua | `pytest -m e2e tests/e2e/test_gateways_e2e.py` |

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
| AC-71.1 | TC-CT-I09 |
| AC-71.2 | TC-CT-U08 |
| AC-71.3 | TC-CT-I10 |
| AC-71.4 | TC-CT-U09 |
| AC-71.5 | TC-CT-I07 |
| AC-71.6 | TC-CT-E01 |
| AC-71.7 | TC-CT-E03 |
| AC-72.1 | TC-CT-U01 |
| AC-72.2 | TC-CT-I04, TC-CT-U02 |
| AC-72.3 | TC-CT-I01 |
| AC-72.4 | TC-CT-U03 |
| AC-72.5 | TC-CT-U04 |
| AC-72.6 | TC-CT-I02 |
| AC-72.7 | TC-CT-I03 |
| AC-72.8 | TC-CT-I05 |
| AC-72.9 | TC-CT-I06 |
| AC-72.10 | TC-CT-U05 |
| AC-72.11 | TC-CT-E02 |
| AC-73.1 | TC-CT-U06 |
| AC-73.2 | TC-CT-U07 |
| AC-73.3 | TC-CT-I08 |

## 6. Danh mục test case

### Tầng 1 — Unit (`tests/test_gateways_unit.py`)

| Mã | Test | Truy vết | Kiểm điều gì |
| --- | --- | --- | --- |
| TC-CT-U01 | `test_stripe_opens_a_checkout_session_in_dong_for_the_order` | AC-72.1 | `POST /v1/checkout/sessions` với khoá bí mật, khoá chống lặp theo mã đơn, VND bằng đúng số đồng, mã đơn ở `client_reference_id` và metadata, `{CHECKOUT_SESSION_ID}`, `left=1`, hạn 31 phút, `locale=vi` |
| TC-CT-U02 | `test_stripe_refusals_read_as_sentences` | FR-72 | Số tiền quá nhỏ, khoá sai (401), Stripe lỗi (500), mất kết nối, địa chỉ trang không phải `https`, chuyển hướng 302 — mỗi trường hợp một câu tiếng Việt và mã đúng; bộ gọi HTTPS không đi theo chuyển hướng |
| TC-CT-U03 | `test_stripe_return_is_read_back_from_stripe` | AC-72.4 | Đã trả, chưa trả, hết hạn, tiền khác; chỉ giữ mã phiên; mã sai dạng, đường dẫn chèn, phiên thật trên khoá thử bị từ chối mà không hỏi Stripe; mất kết nối thành `GatewayError` |
| TC-CT-U04 | `test_stripe_events_count_only_when_signed_and_fresh` | AC-72.5 | Chữ ký đúng; 299 và 301 giây; sửa một byte; khoá khác; thiếu tiêu đề; nhiều `v1` khi đổi khoá; sự kiện thật trên khoá thử; thời điểm có ký tự lạ hay dài bất thường, chữ ký không phải ASCII; ánh xạ bốn loại sự kiện; sự kiện khác; thiếu khoá webhook; mã trả lời 200, 400, 500 |
| TC-CT-U05 | `test_stripe_keys_decide_the_mode` | AC-72.10 | `sk_test_`, `rk_test_` là thử kèm ghi chú thẻ; `sk_live_` có khoá webhook là thật; ba cách cấu hình sai bị từ chối |
| TC-CT-U06 | `test_momo_signs_the_create_request_as_documented` | AC-73.1 | Địa chỉ thử, JSON, chữ ký tính lại theo thứ tự trường của MoMo; thân không chứa khoá; số tiền quá mức bị chặn trước khi gọi; lời từ chối mã 13 |
| TC-CT-U07 | `test_momo_results_map_to_outcomes_and_forgeries_are_refused` | AC-73.2 | Mã 0, 1006, 1000, 1001, 4001 và một mã lạ (chưa xong); trả về bằng chữ và IPN bằng số; năm cách giả mạo, chữ ký có ký tự lạ; thân không phải JSON hay lồng quá sâu; mã trả lời 204, 400, 500 |
| TC-CT-U08 | `test_the_registry_builds_what_the_settings_ask_for` | AC-71.2 | Danh sách trống trong `.env` là cổng thử, danh sách viết lộn xộn được chuẩn hoá; bốn cổng đủ khoá bật đúng thứ tự; thiếu khoá và tên lạ thành một câu mỗi cổng; tên lặp không báo hai lần; Stripe thiếu khoá webhook vẫn bật kèm cảnh báo |
| TC-CT-U09 | `test_real_money_is_never_a_default` | AC-71.4 | Khoá live của Stripe và địa chỉ thật của MoMo không bật khi chưa đặt `AICEFR_PAYMENTS_LIVE`; đặt rồi thì cổng thử bị bỏ; Stripe khoá thử cạnh trang thật của VNPay bị bỏ |

### Tầng 2 — Integration (`tests/test_gateways.py`)

| Mã | Test | Truy vết | Kiểm điều gì |
| --- | --- | --- | --- |
| TC-CT-I01 | `test_paying_through_stripe_is_read_back_and_counted_once` | AC-72.3 | Trọn vòng Stripe; đơn ghi cổng, chế độ thử, mã phiên; trang trả về đọc lại phiên; webhook rồi trả về lần hai không đổi gì, và lần hai không hỏi Stripe; ba sự kiện, một lần áp dụng; biên nhận |
| TC-CT-I02 | `test_the_stripe_webhook_alone_installs_the_plan` | AC-72.6 | Khoá khác, không chữ ký, GET, tiêu đề có ký tự lạ đều 400; thân quá 256 KiB 413; phiên khác mang mã đơn này 200 mà đơn vẫn chờ; webhook đúng một mình cài gói; sự kiện khác 200 |
| TC-CT-I03 | `test_leaving_stripe_changes_nothing_until_the_session_expires` | AC-72.7 | Rời trang Stripe: đơn vẫn chờ; sự kiện hết hạn làm đơn thành huỷ |
| TC-CT-I04 | `test_a_gateway_that_will_not_open_fails_the_order_with_a_reason` | AC-72.2 | Stripe từ chối, rồi mất kết nối: 502 có lời, đơn không thành công với mã của Stripe, không còn đơn chờ |
| TC-CT-I05 | `test_a_return_stripe_cannot_confirm_says_so` | AC-72.8 | Không hỏi được Stripe: "Chưa xác nhận được với Stripe", đơn vẫn chờ; hỏi lại được thì thành công |
| TC-CT-I06 | `test_stripe_is_asked_only_about_checkouts_this_system_opened` | AC-72.9 | Ba mã phiên không phải của đơn nào: không xác nhận, Stripe không được hỏi lần nào |
| TC-CT-I07 | `test_one_gateway_cannot_settle_another_gateways_order` | AC-71.5 | Kết quả có chữ ký của cổng thử cho đơn Stripe: mã 01, đơn vẫn chờ, sự kiện bị từ chối; trang cổng thử không mở cho đơn Stripe; kết quả của Stripe khi khoá đã đổi chế độ tiền bị từ chối, trở lại đúng chế độ thì được ghi nhận |
| TC-CT-I08 | `test_momo_is_paid_through_its_ipn_answered_204` | AC-73.3 | Yêu cầu tới MoMo có địa chỉ trả về và IPN đúng; IPN 204 cài gói; trang trả về; IPN lặp 204 và được đếm trên dòng của IPN đầu; IPN sửa số tiền 400 |
| TC-CT-I09 | `test_the_administrator_picks_the_gateway_and_sees_what_is_off` | AC-71.1 | Danh sách cổng, ghi chú thẻ thử, câu nói cổng chưa bật; khoá không lộ; MoMo 422; cổng mặc định; cổng thử |
| TC-CT-I10 | `test_real_money_needs_to_be_switched_on` | AC-71.3 | Khoá `sk_live_`: chưa bật thì không có Stripe; bật thì Stripe thật và cổng thử tắt, trang cổng thử 404 |

### Tầng 3 — E2E (`tests/e2e/test_gateways_e2e.py`)

| Mã | Test | Truy vết | Kiểm điều gì |
| --- | --- | --- | --- |
| TC-CT-E01 | `test_the_administrator_sees_each_gateway_and_pays_through_the_one_picked` | AC-71.6 | Biểu ngữ môi trường thử và cảnh báo thiếu khoá webhook; hai thẻ cổng, Stripe chọn sẵn; nút "qua Stripe" rồi "qua Cổng thử"; trả xong, bảng đơn ghi "Cổng thử (thử)" |
| TC-CT-E02 | `test_coming_back_without_paying_says_nothing_was_charged` | AC-72.11 | Trang rời trang thanh toán của Stripe |
| TC-CT-E03 | `test_the_gateway_choice_fits_a_phone` | AC-71.7 | 390 px, không cuộn ngang |

## 7. Kết quả chạy

| Lệnh | Kết quả |
| --- | --- |
| `pytest tests/test_gateways_unit.py` | 9 test qua |
| `pytest tests/test_gateways.py` | 10 test qua |
| `pytest -m e2e tests/e2e/test_gateways_e2e.py` | 3 test qua |
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
