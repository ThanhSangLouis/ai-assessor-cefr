# Kế hoạch và kết quả kiểm thử D034 — Gói dịch vụ của trường và thanh toán

| Thuộc tính | Giá trị |
| --- | --- |
| Tính năng | D034: thang gói Miễn phí, Dùng thử, Chuẩn, Nâng cao; giới hạn số sinh viên và công cụ của giảng viên theo gói; mua, nâng cấp, gia hạn qua cổng thanh toán (cổng thử, VNPay); mã giấy phép theo hợp đồng (FR-67..FR-70, BR-29..BR-33, UC-23). Mô hình bán cho trường của D033 vẫn là đề xuất |
| Phiên bản mã | nhánh `feat/billing` |
| Người lập | Võ Thanh Sang |
| Ngày | 07/10/2026 |

## 1. Mục tiêu

1. **Không chạm tới việc học.** Ở mọi gói, kể cả khi gói hết hạn, sinh viên luyện, nộp bài, xem tiến độ, thành tựu và tải dữ liệu như cũ (BR-29, BR-31). Kiểm bằng cấu trúc — công cụ của gói chỉ là ba công cụ của giảng viên — và bằng luồng thật sau khi hết dùng thử.
2. **Mỗi bậc thêm đúng thứ đã hứa.** Miễn phí không có công cụ nào, Chuẩn có soạn lộ trình riêng và thống kê lớp, Nâng cao có thêm chấm mù kép; dùng thử có tất cả; gói trả tiền có ân hạn rồi về Miễn phí.
3. **Tiền chỉ đổi gói khi đúng.** Kết quả của cổng chỉ được ghi nhận khi đúng chữ ký, đúng số tiền, một lần; giả, sửa, lặp hay tới muộn đều được xử lý đúng (BR-33). Không có số thẻ, tài khoản ngân hàng hay tên người trả nào trong hệ thống (BR-32).
4. **Tắt là như cũ.** Không bật thu phí thì không giới hạn gì, không tạo giấy phép nào.

## 2. Ba tầng kiểm thử

| Tầng | Kiểm cái gì | Công cụ | Môi trường | Chạy ở đâu | Lệnh |
| --- | --- | --- | --- | --- | --- |
| 1. Unit | Trạng thái giấy phép theo ngày, thang gói, báo giá (mua mới, gia hạn, nâng cấp có trừ, hạ gói, giảm theo năm, phần miễn), mã giấy phép, chữ ký của VNPay và của cổng thử | pytest | Không ứng dụng, không CSDL, không mạng | Máy và CI | `pytest tests/test_billing_unit.py` |
| 2. Integration | Tắt thu phí; dùng thử; về Miễn phí; ân hạn; giới hạn sinh viên; cảnh báo bài đánh giá; mua qua cổng thử; huỷ, lỗi, giả mạo, sai số tiền, lặp, tới muộn; nâng cấp, gia hạn; công cụ theo gói; mã giấy phép; VNPay; quyền; nhật ký | pytest, FastAPI TestClient | SQLite thật trên tệp tạm; cổng thử như ứng dụng nối; thông điệp VNPay dựng và ký trong test bằng chuỗi bí mật thử; đồng hồ của dịch vụ thanh toán bị ghim | Máy và CI | `pytest tests/test_billing.py` |
| 3. E2E | Bảng so sánh, mua qua trang cổng thử, trang kết quả, biên nhận; huỷ; điện thoại; sinh viên không thấy gói | Playwright + Chromium | Máy chủ uvicorn riêng với `AICEFR_BILLING=on` | **Chỉ trên máy**; CI tự bỏ qua | `pytest -m e2e tests/e2e/test_billing_e2e.py` |

Không có test nào gọi VNPay thật: cần mã website và chuỗi bí mật VNPay cấp cho một pháp nhân, và là dịch vụ bên ngoài chưa được duyệt dùng. Thuật toán ký được kiểm lại bằng thư viện chuẩn theo đúng mô tả của VNPay cho bản 2.1.0 (khoá xếp theo thứ tự, giá trị mã hoá kiểu form, HMAC-SHA512).

## 3. Dữ liệu và môi trường

- Tài khoản tạo trong từng test; mật khẩu là chuỗi cố định của bộ test.
- Giá là giá minh hoạ đặt bằng biến môi trường (Chuẩn 10.000 đ, Nâng cao 15.000 đ mỗi sinh viên mỗi tháng), không phải bảng giá.
- Chuỗi bí mật của mã giấy phép và của VNPay trong test là chuỗi thử viết trong mã kiểm thử, không dùng ở đâu khác.
- Không có dữ liệu người học thật.

## 4. Tiêu chí vào và ra

- **Vào:** mã qua `ruff format --check` và `ruff check`.
- **Ra (được merge):** 100% test tầng 1 và 2 qua trên CI; 100% test tầng 3 qua trên máy trước khi merge; mọi tiêu chí chấp nhận AC-67.1..AC-70.5 có ít nhất một test (kiểm bằng `tests/test_product_traceability.py`).

## 5. Truy vết tiêu chí chấp nhận

Tiêu chí chấp nhận AC-67.1..AC-70.5 nằm ở `docs/srs/SRS.md`, mục 3.9g.

| Tiêu chí chấp nhận | Test case |
| --- | --- |
| AC-67.1 | TC-GD-I01 |
| AC-67.2 | TC-GD-I02 |
| AC-67.3 | TC-GD-I05, TC-GD-U02 |
| AC-67.4 | TC-GD-I06, TC-GD-U02 |
| AC-67.5 | TC-GD-I15 |
| AC-67.6 | TC-GD-U03 |
| AC-68.1 | TC-GD-I03 |
| AC-68.2 | TC-GD-I04 |
| AC-69.1 | TC-GD-I07, TC-GD-U16 |
| AC-69.2 | TC-GD-I08, TC-GD-U05 |
| AC-69.3 | TC-GD-I09 |
| AC-69.4 | TC-GD-I10, TC-GD-U15, TC-GD-U16 |
| AC-69.5 | TC-GD-I11, TC-GD-U06, TC-GD-U07 |
| AC-69.6 | TC-GD-I12, TC-GD-U10 |
| AC-69.7 | TC-GD-I13 |
| AC-69.8 | TC-GD-I14 |
| AC-69.9 | TC-GD-I18, TC-GD-U14, TC-GD-U15 |
| AC-69.10 | TC-GD-E01 |
| AC-69.11 | TC-GD-E02 |
| AC-70.1 | TC-GD-I16, TC-GD-U12 |
| AC-70.2 | TC-GD-I17 |
| AC-70.3 | TC-GD-I19 |
| AC-70.4 | TC-GD-I20 |
| AC-70.5 | TC-GD-E03 |

## 6. Danh mục test case

### Tầng 1 — Unit (`tests/test_billing_unit.py`)

| Mã | Test | Truy vết | Kiểm điều gì |
| --- | --- | --- | --- |
| TC-GD-U01 | `test_the_licence_that_started_last_is_in_force` | FR-67 | Giấy phép bắt đầu sau cùng có hiệu lực; cùng ngày cùng giây thì cái cài sau; giấy phép tương lai là đặt trước; chưa có gì thì là Miễn phí 30 sinh viên |
| TC-GD-U02 | `test_a_paid_plan_runs_out_into_grace_then_the_free_plan` | FR-67 | Gói trả tiền: hiệu lực tới ngày cuối, ân hạn 14 ngày đủ công cụ, rồi Miễn phí kèm gói vừa hết; dùng thử không có ân hạn |
| TC-GD-U03 | `test_each_step_up_adds_something_and_none_locks_learning` | AC-67.6 | Công cụ của gói chỉ là ba công cụ của giảng viên; Miễn phí ⊂ Chuẩn ⊂ Nâng cao; dùng thử bằng Nâng cao; số bài dự kiến tăng theo bậc |
| TC-GD-U04 | `test_a_first_purchase_starts_today` | FR-69 | Từ dùng thử hay Miễn phí: mua mới từ hôm nay, đúng ngày kết thúc, đúng giá |
| TC-GD-U05 | `test_a_school_year_paid_at_once_is_cheaper` | FR-69 | 12 tháng giảm 15%: 12.000.000 đ, giảm 1.800.000 đ, trả 10.200.000 đ |
| TC-GD-U06 | `test_a_renewal_follows_the_current_licence` | FR-69 | Cùng gói cùng số sinh viên: gia hạn nối tiếp ngày sau khi gói hiện tại hết |
| TC-GD-U07 | `test_an_upgrade_starts_today_with_credit_for_the_unused_days` | FR-69 | Nâng cấp từ hôm nay, trừ phần chưa dùng theo ngày, làm tròn nghìn; nhiều sinh viên hơn cũng là nâng cấp; đang ân hạn thì không trừ |
| TC-GD-U08 | `test_a_smaller_plan_waits_for_the_current_one_to_end` | FR-69 | Gói thấp hơn hay ít sinh viên hơn bắt đầu khi gói hiện tại kết thúc |
| TC-GD-U09 | `test_a_quote_refuses_what_cannot_be_sold` | FR-69 | Không bán dùng thử hay Miễn phí, sai thời hạn, số sinh viên ngoài 10–5000, đang có gói đặt trước |
| TC-GD-U10 | `test_a_difference_smaller_than_a_gateway_takes_is_waived` | FR-69 | Phần phải trả dưới 10.000 đ được miễn; phần trừ đủ trả thì 0 đ |
| TC-GD-U11 | `test_months_are_added_on_the_calendar` | FR-69 | Cộng tháng theo lịch: 31/8 + 6 tháng là 28/2, năm nhuận 29/2 |
| TC-GD-U12 | `test_a_licence_key_round_trips_and_any_change_breaks_it` | FR-70 | Mã cấp ra đọc lại đúng; đổi một ký tự, thêm ký tự, sai tiền tố, sai khoá đều bị từ chối kèm lý do |
| TC-GD-U13 | `test_a_key_with_impossible_contents_is_refused` | FR-70 | Mã ghi gói dùng thử hay Miễn phí, 0 sinh viên, kết thúc trước khi bắt đầu bị từ chối |
| TC-GD-U14 | `test_vnpay_builds_a_payment_address_it_documents` | FR-69 | Địa chỉ trang thử của VNPay, chữ ký tính lại khớp, số tiền nhân 100, giờ Việt Nam, hết hạn sau 15 phút |
| TC-GD-U15 | `test_vnpay_results_map_to_outcomes_and_a_changed_byte_is_refused` | FR-69 | Mã 00 là thành công, 24 là huỷ, mã khác là không thành công; chỉ giữ mã ngân hàng, số giao dịch, loại thẻ, thời điểm; chữ ký sai, đổi số tiền, thiếu chữ ký, khoá khác đều bị từ chối |
| TC-GD-U16 | `test_the_sandbox_signs_its_results_and_refuses_forgeries` | FR-69 | Cổng thử ký kết quả như cổng thật; đổi số tiền, đổi kết quả, khoá khác bị từ chối; mã mở trang riêng cho từng đơn và số tiền |

### Tầng 2 — Integration (`tests/test_billing.py`)

| Mã | Test | Truy vết | Kiểm điều gì |
| --- | --- | --- | --- |
| TC-GD-I01 | `test_with_billing_off_nothing_changes` | AC-67.1 | Tắt thu phí: 200 sinh viên, soạn lộ trình, thống kê đều được; báo giá và đặt đơn 409; không tạo giấy phép |
| TC-GD-I02 | `test_the_first_look_starts_one_trial_with_everything` | AC-67.2 | Một gói dùng thử 30 ngày, đủ công cụ; bảng so sánh đúng công cụ từng gói |
| TC-GD-I03 | `test_the_plan_limits_new_student_accounts_only` | AC-68.1 | Giới hạn chỉ chặn tài khoản sinh viên mới, bật lại, đổi vai trò sang sinh viên; tất cả hoặc không; tài khoản có sẵn vẫn đăng nhập |
| TC-GD-I04 | `test_assessments_over_the_monthly_figure_only_warn` | AC-68.2 | Đếm bài của tháng bỏ người đồng thuận nghiên cứu; cảnh báo 80% rồi 100%; sinh viên vẫn nộp được |
| TC-GD-I05 | `test_after_the_trial_the_free_plan_closes_staff_tools_but_never_learning` | AC-67.3 | Hết dùng thử: Miễn phí, soạn lộ trình và thống kê 403 nêu gói mở chúng; hàng đợi, đọc lộ trình và mọi việc của sinh viên vẫn chạy |
| TC-GD-I06 | `test_a_paid_plan_keeps_its_tools_through_grace_then_falls_back_to_free` | AC-67.4 | Ngày ân hạn cuối còn gói Chuẩn đủ công cụ; ngày sau về Miễn phí |
| TC-GD-I07 | `test_buying_through_the_sandbox_installs_the_plan_once` | AC-69.1 | Mua qua cổng thử trọn vòng; báo lại không đổi gì; biên nhận; mỗi thông điệp khác nhau được lưu một lần, thông báo đầu được áp dụng, mỗi lần lặp y hệt được đếm trên dòng của nó (sửa ở D035) |
| TC-GD-I08 | `test_a_school_year_is_discounted_and_shown_on_the_receipt` | AC-69.2 | Giảm 15% khi trả 12 tháng, có trên biên nhận |
| TC-GD-I09 | `test_a_failed_or_cancelled_payment_changes_nothing` | AC-69.3 | Thanh toán không thành công hay huỷ: trang kết quả đúng, gói không đổi, không có biên nhận |
| TC-GD-I10 | `test_a_forged_or_altered_result_is_refused` | AC-69.4 | Sai chữ ký 97, sai số tiền 04, không có đơn 01; đơn vẫn chờ; mã mở trang sai thì 404 |
| TC-GD-I11 | `test_an_upgrade_is_credited_and_a_renewal_waits` | AC-69.5 | Nâng cấp sau 91 ngày được trừ 1.500.000 đ; gia hạn đặt trước; không mua thêm khi có gói đặt trước |
| TC-GD-I12 | `test_an_upgrade_the_credit_covers_needs_no_payment` | AC-69.6 | Đơn 0 đ kích hoạt không qua cổng |
| TC-GD-I13 | `test_pending_orders_expire_and_a_late_payment_still_counts` | AC-69.7 | Đơn quá 15 phút hiện hết hạn chờ; thanh toán tới muộn vẫn được ghi nhận |
| TC-GD-I14 | `test_a_new_order_retires_the_one_still_waiting` | AC-69.8 | Đơn mới chuyển đơn đang chờ sang hết hạn chờ |
| TC-GD-I15 | `test_each_plan_opens_its_staff_tools` | AC-67.5 | Dùng thử, Chuẩn, Nâng cao mở đúng ba công cụ; đợt chấm mù đã có vẫn xem được |
| TC-GD-I16 | `test_a_licence_key_is_installed_once` | AC-70.1 | Cài mã đúng; cài lại 409; mã giả 422 |
| TC-GD-I17 | `test_without_a_licence_secret_keys_are_refused` | AC-70.2 | Chưa đặt chuỗi bí mật: không cài được mã |
| TC-GD-I18 | `test_vnpay_is_redirected_to_and_its_messages_are_checked` | AC-69.9 | Địa chỉ VNPay; thông báo "Confirm Success"; trang kết quả có dòng môi trường thử của VNPay (sửa ở D035: địa chỉ thử của VNPay là môi trường thử); huỷ trên VNPay |
| TC-GD-I19 | `test_only_an_administrator_deals_with_plans` | AC-70.3 | Quyền theo vai trò; sinh viên không thấy gói hay thanh toán |
| TC-GD-I20 | `test_plan_actions_are_audited` | AC-70.4 | Nhật ký đổi tên, đặt đơn, kết quả thanh toán |

### Tầng 3 — E2E (`tests/e2e/test_billing_e2e.py`)

| Mã | Test | Truy vết | Kiểm điều gì |
| --- | --- | --- | --- |
| TC-GD-E01 | `test_an_administrator_buys_a_plan_and_gets_a_receipt` | AC-69.10 | Bảng so sánh ba gói đúng dấu tích; chọn gói Chuẩn; báo giá; trang cổng thử; trang kết quả; biên nhận; tab ghi gói đang dùng |
| TC-GD-E02 | `test_a_cancelled_payment_leaves_the_plan_as_it_was` | AC-69.11 | Huỷ ở trang cổng: gói không đổi, đơn ghi đã huỷ |
| TC-GD-E03 | `test_the_tab_fits_a_phone_and_students_see_no_plan` | AC-70.5 | Tab không cuộn ngang ở 390 px; sinh viên không thấy gói hay thanh toán |

## 7. Kết quả chạy

| Lệnh | Kết quả |
| --- | --- |
| `pytest tests/test_billing_unit.py` | 16 test qua |
| `pytest tests/test_billing.py` | 20 test qua |
| `pytest -m e2e tests/e2e/test_billing_e2e.py` | 3 test qua |
| `pytest -m "not e2e and not slow"` (hồi quy, có đo độ phủ) | 1112 test qua; độ phủ toàn bộ 93%; `billing/payments.py`, `storage/billing_repository.py` 100%, `billing/plans.py` 99%, `billing/service.py` 96%, `billing/gateways.py` 96% |
| `pytest -m e2e tests/e2e` (hồi quy) | 60 test qua (57 sẵn có, 3 mới) |

## 8. Lỗi tìm thấy trong lúc làm

| Mã | Lỗi | Sửa | Giữ lại bằng |
| --- | --- | --- | --- |
| D034-B1 | Mua gói xong mà gói đang dùng vẫn là dùng thử: hai giấy phép bắt đầu cùng ngày và được cài trong cùng một giây, và khi hoà thì giấy phép cài trước thắng | Hoà thì xét thứ tự cài | TC-GD-U01, TC-GD-I07 |
| D034-B2 | Bản đầu dùng chữ "chỗ" cho số tài khoản sinh viên, chủ dự án không hiểu; và bậc gói ngược: đang dùng thử có chấm mù kép, mua gói Chuẩn lại mất | Thang mới Miễn phí → Chuẩn → Nâng cao, mỗi bậc chỉ thêm; dùng thử 30 ngày đủ tính năng rồi về Miễn phí thay vì "hết hạn"; đổi "chỗ" thành "sinh viên"; bảng so sánh ba gói; giảm 15% khi trả theo năm | TC-GD-U03, TC-GD-I02, TC-GD-I05, TC-GD-E01 |
| D034-B3 | Bảng so sánh tràn khỏi thẻ, cột Nâng cao bị cắt: cột nhãn không xuống dòng | Bảng cố định độ rộng cột, nhãn xuống dòng | Ảnh chụp 1280×820 |
| D034-B4 | Thông điệp lặp lại của cổng (trình duyệt quay lại lần hai, cổng báo lại) không được lưu, nên đối soát không thấy hết những gì cổng đã nói | Mọi thông điệp có chữ ký về một đơn được lưu kèm cờ đã áp dụng hay chưa. Ở D035 đổi thành: lặp y hệt thì đếm trên dòng đã có (`repeats`), vì ai giữ một địa chỉ có chữ ký cũng gửi lại được nó vô số lần | TC-GD-I07 |
| D034-B5 | Enum mới tên `Feature` trùng tên lớp `Feature` trên sơ đồ lớp, làm test sơ đồ đọc nhầm | Đổi thành `PlanFeature`, `LicenseState` | `tests/test_diagrams.py` |
| D034-B6 | Cổng `PaymentGateway` chưa có trên sơ đồ nào | Vẽ cổng và hai bộ chuyển đổi vào hình 2b | `test_every_port_appears_on_a_diagram` |
