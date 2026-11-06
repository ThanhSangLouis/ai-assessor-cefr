# Kế hoạch và kết quả kiểm thử D094 — Tính lượt cho bản ghi trong lộ trình học

| Thuộc tính | Giá trị |
| --- | --- |
| Thay đổi | D094: trên bản triển khai tính lượt (kênh NetID), mỗi bản ghi trong lộ trình (bước bài học, ôn tập, kể lại, luyện từ, đọc đoạn) được tính lượt. 5 bản ghi đầu mỗi ngày (giờ Việt Nam) miễn phí; từ bản thứ 6 trả 0,1 lượt (200 IDPoint) cho mỗi phút nói đã bắt đầu, trừ lượt miễn phí của tháng trước rồi tới ví; tối đa 30 bản ghi mỗi ngày. Bản ghi máy không đo được hoặc lỗi thì trả lại cả suất trong ngày lẫn lượt (FR-99). Chủ dự án chọn phương án D ngày 07/11/2026 |
| Phiên bản mã | nhánh `feat/d094-lesson-metering` |
| Người lập | Võ Thanh Sang |
| Ngày | 07/11/2026 |

## 1. Mục tiêu

1. **Thu đúng.** Bản ghi miễn phí không giữ gì. Bản ghi trả phí giữ giá của thời lượng tối đa của bước, rồi chỉ thu theo số giây nói thật (VAD), làm tròn lên từng phút, ít nhất một phút.
2. **Không thu oan.** Bản ghi bị QC loại (im lặng, không phải tiếng Anh, quá ngắn) hoặc máy chấm lỗi thì trả lại cả suất trong ngày lẫn lượt; suất miễn phí trả lại thì bản ghi kế tiếp lại được miễn phí.
3. **Không vượt giới hạn.** Nhiều bản ghi cùng lúc không lấy quá số suất miễn phí, quá trần ngày hay quá số lượt trong ví. Bị từ chối (402, 429) thì không đo gì, không lưu gì.
4. **Không lọt đường nào.** Cả năm endpoint gửi bản ghi của học viên tới máy đo đều đi qua tính lượt; bản xem thử và audio mẫu của giảng viên thì không.
5. **Bản của trường không đổi.** Tắt tính lượt (`AICEFR_METERING`) thì không giữ, không đếm, không từ chối gì (BR-29, BR-30).

## 2. Các tầng

| Tầng | Kiểm cái gì | Môi trường | Lệnh |
| --- | --- | --- | --- |
| Unit | Giá theo phút nói, mặc định, kiểm số không hợp lệ, bảng giá hiển thị | Hàm thuần | `pytest tests/test_d094_lesson_metering_unit.py` |
| Integration | Sổ lượt (suất trong ngày, trần, trả lại, sang ngày mới, chạy đồng thời), facade, năm endpoint qua ứng dụng, trang quản trị giá | Ứng dụng một tiến trình, MongoDB trong bộ nhớ; máy nhận dạng giả chạy qua đúng đường đo thật | `pytest tests/test_d094_lesson_metering.py` |

## 3. Truy vết tiêu chí chấp nhận

| Tiêu chí chấp nhận | Test case |
| --- | --- |
| AC-99.1 | TC-LM-I01, TC-LM-I15 |
| AC-99.2 | TC-LM-U02, TC-LM-I02, TC-LM-I06, TC-LM-I11 |
| AC-99.3 | TC-LM-I04, TC-LM-I10, TC-LM-I15 |
| AC-99.4 | TC-LM-I03, TC-LM-I09, TC-LM-I18 |
| AC-99.5 | TC-LM-I05, TC-LM-I16, TC-LM-I17 |
| AC-99.6 | TC-LM-I19, TC-LM-I20, TC-LM-I21 |
| AC-99.7 | TC-LM-I13, TC-LM-I22, TC-LM-I23 |
| AC-99.8 | TC-LM-I14, TC-LM-I24 |

## 4. Test case

### 4.1. Unit — `tests/test_d094_lesson_metering_unit.py`

| Mã | Test | Truy vết | Kiểm |
| --- | --- | --- | --- |
| TC-LM-U01 | `test_the_defaults_are_the_owners_choice` | FR-99 | Mặc định 0,1 lượt mỗi phút nói, 5 bản ghi miễn phí, trần 30 |
| TC-LM-U02 | `test_a_recording_pays_per_started_minute_of_speech_at_least_one` | AC-99.2 | 0 và 4,5 giây đều là một phút (100 phần nghìn lượt = 200 IDPoint); 60,5 giây là hai phút; tối đa năm phút |
| TC-LM-U03 | `test_a_typical_lesson_costs_less_than_one_assessment` | FR-99 | Bài học trung vị 4 bản ghi dưới một phút nói: 800 IDPoint, rẻ hơn một bài đánh giá (2.000) |
| TC-LM-U04 | `test_the_seller_sets_the_lesson_price` | FR-99 | Giá 0,25 lượt/phút cho 61 giây là 500; giá 0 thì miễn phí |
| TC-LM-U05 | `test_impossible_lesson_numbers_are_refused` | FR-99 | Giá âm, trần 0, số miễn phí âm hay lớn hơn trần đều bị từ chối |
| TC-LM-U06 | `test_the_price_list_shows_the_lesson_numbers` | FR-99 | `PriceList.as_dict()` có ba số của bài học |

### 4.2. Integration — `tests/test_d094_lesson_metering.py`

| Mã | Test | Truy vết | Kiểm |
| --- | --- | --- | --- |
| TC-LM-I01 | `test_the_first_recordings_of_a_day_are_free_and_hold_nothing` | AC-99.1 | 5 bản ghi đầu ngày giữ 0, ghi `free_slot` và ngày; lượt miễn phí của tháng không bị đụng |
| TC-LM-I02 | `test_past_the_free_ones_the_months_free_runs_pay_first_then_the_wallet` | AC-99.2 | Từ bản thứ 6 giữ 0,1 lượt từ lượt miễn phí tháng; hết 3 lượt tháng thì lấy ví |
| TC-LM-I03 | `test_no_runs_left_refuses_and_gives_the_place_back` | AC-99.4 | Hết lượt: `InsufficientCredits`, không có bút toán, suất trong ngày được trả lại |
| TC-LM-I04 | `test_past_the_cap_nothing_more_is_counted_or_taken` | AC-99.3 | Đủ trần thì `DailyCapReached`; số đếm và lượt không đổi |
| TC-LM-I05 | `test_a_recording_with_no_result_gives_its_place_and_runs_back` | AC-99.5 | Không có kết quả: bút toán `released`, suất và lượt trả lại; suất miễn phí trả lại nên bản sau lại miễn phí |
| TC-LM-I06 | `test_a_measured_recording_keeps_its_place_and_pays_what_was_said` | AC-99.2 | Bản miễn phí thu 0; bước 150 giây giữ ba phút nhưng nói 40 giây chỉ thu một phút, phần thừa trả lại |
| TC-LM-I07 | `test_holding_the_same_key_twice_counts_once` | FR-99 | Giữ lại cùng khoá trả đúng bút toán cũ, chỉ đếm một lần |
| TC-LM-I08 | `test_a_new_day_starts_afresh_and_yesterday_never_comes_back` | FR-99 | Ngày mới đếm lại từ 0; yêu cầu tính trước nửa đêm được đếm vào ngày mới; trả lại bản ghi hôm qua không đụng số đếm hôm nay |
| TC-LM-I09 | `test_twelve_recordings_at_once_never_overrun_the_free_places_or_the_wallet` | AC-99.4 | 12 bản ghi cùng lúc, 5 suất miễn phí, ví đủ 2 bản: đúng 7 qua, 5 bị từ chối vì hết lượt, ví về 0 |
| TC-LM-I10 | `test_twelve_recordings_at_once_never_overrun_the_cap` | AC-99.3 | 12 bản ghi cùng lúc, trần 6: đúng 6 qua, 6 bị từ chối vì trần |
| TC-LM-I11 | `test_the_charge_follows_the_speech_not_the_steps_limit` | AC-99.2 | Facade: giữ ba phút cho bước 150 giây; nói 61 giây thu hai phút, ghi token âm thanh ước tính |
| TC-LM-I12 | `test_the_facade_refuses_as_data_with_the_status_to_answer` | FR-99 | Từ chối là dữ liệu: 402 "Nạp thêm IDPoint", 429 "đủ 1 bản ghi"; câu 402 không nhắc "0 bản ghi miễn phí" |
| TC-LM-I13 | `test_the_quote_says_what_is_left_today` | AC-99.7 | Báo giá: 0,1 lượt / 200 IDPoint mỗi phút, còn 5/5 miễn phí, trần 30; sau 6 bản ghi còn 0 miễn phí, 24 suất, 2,9 lượt |
| TC-LM-I14 | `test_with_metering_off_the_facade_holds_counts_and_refuses_nothing` | AC-99.8 | Tắt tính lượt: không giữ, không chốt, không báo giá, không bút toán |
| TC-LM-I15 | `test_steps_are_free_then_charged_by_speech_then_capped` | AC-99.1 | Qua ứng dụng (2 miễn phí, trần 4): báo giá đúng; 2 bản miễn phí, 2 bản thu 0,1 lượt; bản thứ 5 nhận 429 và không có lượt học nào được lưu; trang Lượt của tôi có báo giá bài học và lịch sử "miễn phí trong ngày" |
| TC-LM-I16 | `test_a_recording_nothing_could_be_measured_from_costs_nothing` | AC-99.5 | Bản ghi 0,5 giây bị QC loại: bút toán `released`, vẫn còn 2/2 bản miễn phí và 4 suất |
| TC-LM-I17 | `test_a_failure_of_the_speech_service_gives_everything_back` | AC-99.5 | Máy đo lỗi (503): bút toán `released`, suất trả lại |
| TC-LM-I18 | `test_no_runs_left_is_a_402_and_a_top_up_lets_the_learner_go_on` | AC-99.4 | Quản trị viên đặt 0 lượt miễn phí tháng, 1 bản miễn phí ngày, 0,2 lượt/phút: bản thứ 2 nhận 402 và không lưu gì; nạp 1 lượt thì học tiếp, ví còn 0,8 |
| TC-LM-I19 | `test_a_drill_take_is_a_lesson_recording_too` | AC-99.6 | Một lần luyện từ (D089) có bút toán `lesson` |
| TC-LM-I20 | `test_every_recording_endpoint_of_the_lesson_path_is_metered` | AC-99.6 | Năm endpoint chạy qua `_metered`; ngoài chúng chỉ còn bản xem thử và audio mẫu của giảng viên gọi máy đo |
| TC-LM-I21 | `test_a_teachers_preview_is_never_charged` | AC-99.6 | Giảng viên xem thử một bước: không có bút toán nào |
| TC-LM-I22 | `test_a_price_list_saved_before_d094_keeps_the_defaults` | AC-99.7 | Bảng giá quản trị viên lưu trước D094 vẫn đọc được, ba số lấy theo cấu hình của bản triển khai |
| TC-LM-I23 | `test_the_admin_form_refuses_impossible_lesson_numbers` | AC-99.7 | Số miễn phí lớn hơn trần, trần 0: 422 |
| TC-LM-I24 | `test_with_metering_off_lessons_are_never_held_counted_or_refused` | AC-99.8 | Tắt tính lượt với trần 1: 3 bản ghi đều qua, không bút toán, báo giá `metering: false` |

## 5. Kết quả

| Lần chạy | Lệnh | Kết quả |
| --- | --- | --- |
| Unit | `pytest tests/test_d094_lesson_metering_unit.py` | PASS |
| Integration | `pytest tests/test_d094_lesson_metering.py` | PASS |
| Toàn bộ unit và integration | `pytest --ignore=tests/e2e tests` | PASS |
| Kiểm tay trên máy cục bộ (07/11/2026) | Server bật tính lượt, 2 bản miễn phí, trần 3; giọng thật tạo bằng `say` | PASS: dòng giá dưới bộ ghi âm đổi đúng sau mỗi lần nộp; bản thứ 3 trừ 0,1 lượt; bản thứ 4 nhận 429 và toast "Hôm nay bạn đã nói đủ 3 bản ghi…"; trang Lượt của tôi có "Miễn phí trong ngày"; quản trị viên đổi số miễn phí và trần, áp dụng ngay; khổ 390 px không cuộn ngang |

**Giới hạn (`NOT_RUN`):** chưa có e2e trình duyệt cho dòng giá và toast từ chối (ghi âm cần micro); đã kiểm tay như trên. Ba e2e lộ trình (`test_new_learner_sees_the_path_and_the_first_lesson_next`, `test_a_coin_on_the_trail_opens_its_card_and_then_the_lesson`, `test_students_see_the_published_version_until_the_teacher_publishes_again`) đỏ giống hệt trên `main`, không do D094.
