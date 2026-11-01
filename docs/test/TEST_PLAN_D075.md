# Kế hoạch và kết quả kiểm thử D075 — Một trung tâm, trả theo lượt; giảng viên soạn bài bằng AI

| Thuộc tính | Giá trị |
| --- | --- |
| Tính năng | D075: bỏ gói dịch vụ, dùng thử, giới hạn chỗ, mã giấy phép; mọi công cụ giảng viên mở; tiền chỉ đến từ gói lượt mua qua Stripe (cổng thử để chạy thử); bỏ giao bài và mã lớp; giảng viên nhờ AI viết nháp bài học, trả bằng lượt như học viên (FR-91, FR-87, FR-88) |
| Phiên bản mã | nhánh `feat/d075-trung-tam-tra-theo-luot` |
| Người lập | Võ Thanh Sang |
| Ngày | 01/11/2026 |

## 1. Mục tiêu

1. **Không còn gì chặn theo gói:** soạn lộ trình, thống kê, chấm mù mở cho mọi giảng viên; không giới hạn số học viên; các API gói trả 404.
2. **Tiền chỉ đến từ gói lượt** và kết quả thanh toán chỉ được tin khi đúng chữ ký, đúng cổng, đúng số tiền.
3. **AI viết nháp bài học** điền đúng form "Bài học mới", không lưu gì, trừ lượt của giảng viên với giá của bản nâng cấp, trả lại khi lỗi, chung giới hạn ngày.

## 2. Ba tầng kiểm thử

| Tầng | Kiểm cái gì | Công cụ | Chạy ở đâu | Lệnh |
| --- | --- | --- | --- | --- |
| 1. Unit | Chữ ký của cổng thử; đọc bản nháp của AI | pytest | Máy và CI | `pytest tests/test_billing_unit.py tests/test_d075_lesson_draft.py -m unit` |
| 2. Integration | Công cụ mở, không giới hạn chỗ, API gói đã gỡ, kết quả giả mạo, nhật ký; bản nháp qua API, tính lượt, giới hạn ngày | pytest, FastAPI TestClient | Máy và CI | `pytest tests/test_billing.py tests/test_d075_lesson_draft.py` |
| 3. E2E | Học viên mua gói lượt qua cổng thử, biên nhận, huỷ, điện thoại | Playwright + Chromium | **Chỉ trên máy** | `pytest -m e2e tests/e2e/test_billing_e2e.py` |

## 3. Truy vết tiêu chí

| Tiêu chí | Test |
| --- | --- |
| AC-91.1 | TC-TL-I01 |
| AC-91.2 | TC-TL-I02 |
| AC-91.3 | TC-TL-I03 |
| AC-91.4 | TC-TL-A04 |
| AC-91.5 | TC-TL-A06 |
| AC-91.6 | TC-TL-E01 |

## 4. Danh sách test

### Tầng 1 — Unit (`tests/test_billing_unit.py`)

| Mã | Test | Truy vết | Kiểm gì |
| --- | --- | --- | --- |
| TC-TL-U01 | `test_the_sandbox_signs_its_results_and_refuses_forgeries` | FR-91 | Cổng thử ký kết quả; đổi số tiền, đổi kết quả, khoá khác bị từ chối |

### Tầng 2 — Integration (`tests/test_billing.py`)

| Mã | Test | Truy vết | Kiểm gì |
| --- | --- | --- | --- |
| TC-TL-I01 | `test_every_staff_tool_is_open_without_a_plan` | AC-91.1 | Giảng viên tạo lộ trình, xem thống kê khi bật thanh toán |
| TC-TL-I02 | `test_accounts_are_not_limited_by_seats` | AC-91.2 | Tạo 60 học viên một lần |
| TC-TL-I03 | `test_the_plan_routes_are_gone` | AC-91.3 | API gói, báo giá, đặt gói, mã giấy phép: 404/405 |
| TC-TL-I04 | `test_a_forged_or_altered_result_is_refused` | FR-91 | Chữ ký giả, số tiền sai, đơn lạ, mã mở trang sai, cổng đã gỡ |
| TC-TL-I05 | `test_payments_are_audited` | FR-91 | Đặt gói lượt vào nhật ký kiểm toán |

### Bản nháp bài học bằng AI (`tests/test_d075_lesson_draft.py`)

| Mã | Test | Truy vết | Kiểm gì |
| --- | --- | --- | --- |
| TC-TL-A01 | `test_keywords_not_in_the_text_are_dropped` | FR-91 | Từ khóa không có trong đoạn văn bị bỏ |
| TC-TL-A02 | `test_an_answer_without_a_title_or_text_is_refused` | FR-91 | JSON hỏng, sai dạng, thiếu đoạn văn: từ chối kèm lý do |
| TC-TL-A03 | `test_the_request_names_the_band_and_its_length` | FR-91 | Yêu cầu nêu band, tiêu chí, chủ đề và độ dài theo band |
| TC-TL-A04 | `test_a_teacher_gets_a_draft_for_the_form` | AC-91.4 | Trả các ô của form, prompt riêng của bản nháp, bộ đếm ngày |
| TC-TL-A05 | `test_learners_cannot_ask_for_a_draft` | FR-91 | Học viên nhận 403 |
| TC-TL-A06 | `test_metered_the_teachers_runs_pay_for_the_draft` | AC-91.5 | 0,3 lượt trừ ví giảng viên, có token, có trong lịch sử |
| TC-TL-A07 | `test_metered_a_failed_draft_costs_nothing` | FR-91 | Mô hình lỗi: hoàn lượt |
| TC-TL-A08 | `test_the_daily_cap_counts_drafts_too` | FR-91 | Giới hạn ngày đếm cả bản nháp |
| TC-TL-A09 | `test_without_a_language_model_no_draft_is_offered` | FR-91 | Không có mô hình: không mời, 503 |

### Tầng 3 — E2E (`tests/e2e/test_billing_e2e.py`)

| Mã | Test | Truy vết | Kiểm gì |
| --- | --- | --- | --- |
| TC-TL-E01 | `test_a_learner_buys_a_pack_and_gets_a_receipt` | AC-91.6 | Trang Lượt của tôi, cổng thử, trang kết quả, biên nhận, đơn đã thanh toán |
| TC-TL-E02 | `test_a_cancelled_payment_credits_nothing` | FR-91 | Huỷ: ví không đổi |
| TC-TL-E03 | `test_the_runs_page_fits_a_phone` | FR-91 | 390 px, không cuộn ngang |
