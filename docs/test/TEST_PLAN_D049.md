# Kế hoạch và kết quả kiểm thử D049 — Tính lượt trên kênh NetID

| Thuộc tính | Giá trị |
| --- | --- |
| Thay đổi | D049 dịch vụ `metering`: sổ lượt, giữ chỗ → thu hoặc hoàn, lượt miễn phí mỗi chu kỳ, cộng lượt (FR-85). **PROPOSED** |
| Phiên bản mã | nhánh `feat/d049-metering` (xếp trên `feat/d048-mongodb`) |
| Người lập | Võ Thanh Sang |
| Ngày | 21/10/2026 |

## 1. Mục tiêu

1. **Không thu sai.** Chỉ thu khi người học có kết quả, thu theo thời lượng thật, không bao giờ thu hai lần một bài.
2. **Không vượt số dư** khi nhiều bài nộp cùng lúc.
3. **Bản của trường không đổi.** Tắt `AICEFR_METERING` thì không giữ, không thu, không từ chối gì (BR-29, BR-30).
4. **Không trộn tiền với nghiên cứu.** Bản tính lượt không chạy thực nghiệm.

## 2. Các tầng

| Tầng | Kiểm cái gì | Môi trường | Lệnh |
| --- | --- | --- | --- |
| Unit | Bảng giá theo bài và phút, token đo kèm, chu kỳ ngày 16 | Hàm thuần | `pytest tests/test_metering_unit.py` |
| Integration | Sổ lượt trên kho, đồng thời, API nộp bài và trang lượt | MongoDB trong bộ nhớ; thêm `AICEFR_TEST_MONGO` | `pytest tests/test_metering.py` |

## 3. Truy vết tiêu chí chấp nhận

| Tiêu chí chấp nhận | Test case |
| --- | --- |
| AC-85.1 | TC-ME-U01 |
| AC-85.2 | TC-ME-I01 |
| AC-85.3 | TC-ME-I02 |
| AC-85.4 | TC-ME-I03 |
| AC-85.5 | TC-ME-I04 |
| AC-85.6 | TC-ME-I12 |
| AC-85.7 | TC-ME-I09 |
| AC-85.8 | TC-ME-I10 |
| AC-85.9 | TC-ME-I13 |
| AC-85.10 | TC-ME-I15 |

## 4. Test case

### 4.1. Unit — `tests/test_metering_unit.py`

| Mã | Test | Truy vết | Kiểm |
| --- | --- | --- | --- |
| TC-ME-U01 | `test_a_recording_up_to_a_minute_is_one_run` | AC-85.1 | 1, 35, 60 giây đều là 1 lượt = 2.000 IDPoint (D057) |
| TC-ME-U02 | `test_every_further_minute_adds_seven_tenths_of_a_run_up_to_five` | AC-85.1 | 61 và 120 giây là 3.400; 300 giây và dài hơn là 7.600 |
| TC-ME-U03 | `test_practice_pays_half` | FR-85 | Bài luyện tập 0,5 lượt = 1.000 IDPoint |
| TC-ME-U04 | `test_a_cycle_starts_on_the_sixteenth` | FR-85 | Chu kỳ đổi lúc 0 giờ ngày 16, qua năm đúng |
| TC-ME-U05 | `test_counted_output_tokens_win_over_the_estimate_from_words` | FR-85 | Token do bộ nhận dạng đếm được dùng trước; không có thì ước lượng từ số từ và ghi là ước lượng (D057) |
| TC-ME-U06 | `test_audio_tokens_are_whispers_windows_plus_the_language_check` | FR-85 | 1.500 token mỗi cửa sổ 30 giây, thêm 1 cửa sổ kiểm tra ngôn ngữ; ghi kèm bút toán để tính giá vốn |
| TC-ME-U07 | `test_the_seller_sets_the_prices` | FR-85 | Giá do người bán đặt; giá âm hay hệ số luyện tập 0 bị từ chối (D057) |
| TC-ME-U08 | `test_a_hold_is_the_longest_the_task_allows` | FR-85 | Giữ chỗ theo thời lượng tối đa của đề: 90 giây là 1,7 lượt |

### 4.2. Integration — `tests/test_metering.py`

| Mã | Test | Truy vết | Kiểm |
| --- | --- | --- | --- |
| TC-ME-I01 | `test_free_runs_are_used_before_the_wallet` | AC-85.2 | 30 đơn vị miễn phí trước, 10 từ ví |
| TC-ME-I02 | `test_a_hold_beyond_free_and_wallet_is_refused_and_takes_nothing` | AC-85.3 | Từ chối, số dư và lượt miễn phí giữ nguyên, không có bút toán |
| TC-ME-I03 | `test_holding_the_same_key_twice_takes_once` | AC-85.4 | Cùng bút toán, chỉ lấy một lần |
| TC-ME-I04 | `test_a_result_charges_what_was_used_and_returns_the_rest` | AC-85.5 | Giữ 5 lượt, thu 2, trả 3 vào ví trước |
| TC-ME-I05 | `test_no_result_releases_everything` | FR-85 | Hoàn đủ, lượt miễn phí quay lại |
| TC-ME-I06 | `test_settling_twice_changes_nothing` | FR-85 | Chốt lần hai không đổi trạng thái hay số dư |
| TC-ME-I07 | `test_stale_holds_are_released` | FR-85 | Chỗ giữ quá hạn được hoàn, quét lại không làm gì |
| TC-ME-I08 | `test_a_top_up_is_credited_once_per_reference` | FR-85 | Một số tham chiếu chỉ cộng một lần; số lượt phải dương |
| TC-ME-I09 | `test_concurrent_holds_never_overdraw` | AC-85.7 | 12 luồng, đúng 5 qua, số dư về 0 |
| TC-ME-I10 | `test_with_metering_off_nothing_is_held_or_refused` | AC-85.8 | 5 bài trên bản của trường, sổ trống |
| TC-ME-I11 | `test_a_submission_is_held_then_charged_and_shows_in_my_credits` | FR-85 | Bài 35 giây thu 1 lượt, bút toán ghi số token; trang lượt không lộ mã nội bộ |
| TC-ME-I12 | `test_a_failed_scoring_releases_the_hold` | AC-85.6 | Báo lỗi từ máy chấm: FAILED và hoàn |
| TC-ME-I13 | `test_a_submission_without_runs_left_is_refused_with_402` | AC-85.9 | 402, không lưu bài, không để lại tệp |
| TC-ME-I14 | `test_only_an_administrator_grants_runs` | FR-85 | Giảng viên 403; một phiếu chỉ cộng một lần; bút danh lạ 404 |
| TC-ME-I15 | `test_the_metered_deployment_runs_no_research_study` | AC-85.10 | Tạo thực nghiệm trả 404 (gỡ bởi D078) |
| TC-ME-I16 | `test_granting_on_the_school_deployment_is_refused` | FR-85 | Bản của trường không cộng lượt |
| TC-ME-I17 | `test_the_submission_screen_quotes_the_most_a_task_costs` | FR-85 | Trang Nộp bài báo giá tối đa: đề 90 giây là 1,7 lượt = 3.400 IDPoint (D057) |

## 5. Kết quả

| Lệnh | Kết quả |
| --- | --- |
| `pytest tests/test_metering_unit.py tests/test_metering.py` | 20 qua |

## 6. Chưa kiểm

- Gọi API IDPoint thật của NetID: chưa có tài liệu, adapter chưa viết.
- Đối soát mỗi ngày với bảng kê NetID.
- Bước luyện trong bài học và tạo lộ trình chưa bị tính lượt (mục 9.3 của thiết kế để pha sau).
