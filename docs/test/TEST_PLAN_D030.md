# Kế hoạch và kết quả kiểm thử D030 — Chấm mù kép và báo cáo đồng thuận

| Thuộc tính | Giá trị |
| --- | --- |
| Tính năng | D030: đợt chấm mù, phiếu chấm mù, phân xử, báo cáo đồng thuận và bản xuất (FR-61..FR-64; UC-21, UC-22; BR-05, BR-18..BR-25, BR-27) |
| Phiên bản mã | nhánh `feat/blind-rating` |
| Người lập | Võ Thanh Sang |
| Ngày | 07/10/2026 |

## 1. Mục tiêu

1. **Mù thật.** Phiếu không mang bút danh, mã bài, điểm máy hay điểm người khác; đường vòng qua báo cáo, lịch sử, khoá và hàng đợi cũng đóng. Mù cả theo thời gian: ai đã mở kết quả của máy cho một bài thì không được giao bài đó, phiếu đang nợ của họ không nhận điểm, và quản trị viên làm giám khảo bị che trên màn quản trị. Một lời hứa "không trả điểm máy" không có test thì chỉ là lời hứa.
2. **Đúng giao thức khảo sát.** Hai giám khảo mỗi bài, thứ tự riêng, hạt giống ghi lại; phân xử đúng điều kiện; điểm đối chiếu đúng quy tắc.
3. **Con số đúng và tái lập được.** Kappa trùng scikit-learn, ICC tái lập ví dụ kinh điển, khoảng tin cậy lấy mẫu theo người nói và cho cùng kết quả với cùng hạt giống; báo cáo người–người đứng trước máy–người.
4. **Quyền riêng tư.** Chỉ bài của người đang đồng thuận nghiên cứu; rút đồng thuận là rút khỏi báo cáo; xoá dữ liệu là xoá phiếu.

## 2. Bốn nhóm kiểm thử

| Nhóm | Kiểm cái gì | Công cụ | Chạy ở đâu | Lệnh |
| --- | --- | --- | --- | --- |
| U — Phân phiếu | `research/assign.py`: hai giám khảo, thứ tự, hạt giống, tải đều, bỏ người đã xem kết quả của máy | pytest | Máy và CI | `pytest tests/test_assign_unit.py` |
| S — Thống kê | `research/agreement.py`: kappa, ICC, Pearson, RMSE, phân xử, điểm đối chiếu, bootstrap, báo cáo | pytest (scikit-learn chỉ để đối chiếu) | Máy và CI | `pytest tests/test_agreement.py` |
| I — Tích hợp | API giám khảo và quản trị, chặn đường vòng, người đã xem kết quả của máy, đồng thuận, xoá, CSV, công cụ dòng lệnh | pytest, FastAPI TestClient, SQLite thật | Máy và CI | `pytest tests/test_ratings.py` |
| E — E2E | Giám khảo chấm trên trình duyệt; quản trị viên tạo đợt và đọc báo cáo | Playwright + Chromium | **Chỉ trên máy** | `pytest -m e2e tests/e2e/test_ratings_e2e.py` |

## 3. Dữ liệu và môi trường

- Bài nộp là sóng sin tổng hợp qua pipeline thật với bộ nhận dạng giả lập. Bản chép giả lập quá ngắn để được chấm, nên những test cần điểm máy **ghi điểm máy vào đúng chỗ pipeline ghi** (báo cáo lưu và dòng `response`) và nói rõ điều đó trong test.
- Số liệu thống kê trong nhóm S là dữ liệu dựng tay hoặc ví dụ đã công bố (Shrout & Fleiss 1979); không có số liệu thật nào của người học.

## 4. Tiêu chí vào và ra

- **Vào:** mã qua `ruff format --check` và `ruff check`.
- **Ra:** 100% nhóm U, S, I qua trên CI; 100% nhóm E qua trên máy trước khi merge; mọi tiêu chí chấp nhận AC-61.1..AC-64.6 có test (kiểm bằng `tests/test_product_traceability.py`).

## 5. Truy vết tiêu chí chấp nhận

Tiêu chí chấp nhận AC-61.1..AC-64.6 nằm ở `docs/srs/SRS.md`, mục 3.9e.

| Tiêu chí chấp nhận | Test case |
| --- | --- |
| AC-61.1 | TC-BR-U01, TC-BR-I01 |
| AC-61.2 | TC-BR-U04, TC-BR-I02 |
| AC-61.3 | TC-BR-U07, TC-BR-I17 |
| AC-62.1 | TC-BR-I03, TC-BR-E01 |
| AC-62.2 | TC-BR-I04 |
| AC-62.3 | TC-BR-I05 |
| AC-62.4 | TC-BR-I06 |
| AC-62.5 | TC-BR-I07 |
| AC-62.6 | TC-BR-I08 |
| AC-62.7 | TC-BR-I18 |
| AC-62.8 | TC-BR-I19 |
| AC-62.9 | TC-BR-I20 |
| AC-62.10 | TC-BR-I22 |
| TC-BR-I23 | `test_a_review_decision_keeps_the_ratings_and_who_saw_the_machine` | FR-62 | Quyết định duyệt sau khi đã chấm mù không xoá phiếu, điểm chấm hay bản ghi "đã xem kết quả máy" của bài |
| AC-63.1 | TC-BR-I09 |
| AC-63.2 | TC-BR-I21 |
| AC-64.1 | TC-BR-I10, TC-BR-E02 |
| AC-64.2 | TC-BR-I11 |
| AC-64.3 | TC-BR-I12 |
| AC-64.4 | TC-BR-I13 |
| AC-64.5 | TC-BR-I16 |
| AC-64.6 | TC-BR-I14 |

## 6. Danh mục test case

### Nhóm U — Phân phiếu (`tests/test_assign_unit.py`)

| Mã | Test | Truy vết | Kiểm điều gì |
| --- | --- | --- | --- |
| TC-BR-U01 | `test_two_raters_both_rate_everything_each_in_their_own_order` | AC-61.1 | Hai giám khảo chấm mọi bài, mỗi người một thứ tự |
| TC-BR-U02 | `test_the_same_seed_gives_the_same_plan_and_another_seed_another` | FR-61 | Cùng hạt giống cho cùng kế hoạch |
| TC-BR-U03 | `test_with_more_raters_loads_stay_balanced_and_every_pair_meets` | FR-61 | Nhiều giám khảo: tải đều, mọi cặp đều gặp nhau |
| TC-BR-U04 | `test_one_rater_is_not_a_double_rating` | AC-61.2 | Một giám khảo không phải chấm kép |
| TC-BR-U05 | `test_adjudication_continues_the_adjudicators_own_order` | FR-63 | Phiếu phân xử nối tiếp thứ tự của người phân xử |
| TC-BR-U06 | `test_a_sample_is_a_reproducible_subset` | FR-61 | Mẫu bài tái lập được |
| TC-BR-U07 | `test_a_rater_who_has_seen_the_machine_result_never_gets_that_response` | AC-61.3 | Người đã xem kết quả của máy không được giao bài đó; bài không còn cặp nào thì ra khỏi kế hoạch |

### Nhóm S — Thống kê (`tests/test_agreement.py`)

| Mã | Test | Truy vết | Kiểm điều gì |
| --- | --- | --- | --- |
| TC-BR-S01 | `test_bands_and_criteria_match_the_contracts` | FR-64 | Band và tiêu chí của module trùng với hợp đồng dữ liệu |
| TC-BR-S02 | `test_half_point_categories_cover_the_0_to_6_scale` | FR-64 | Thang nửa điểm 0–6 đủ 13 mức |
| TC-BR-S03 | `test_qwk_is_one_for_perfect_agreement` | FR-64 | Kappa bằng 1 khi hai bên trùng hoàn toàn |
| TC-BR-S04 | `test_qwk_matches_scikit_learn_on_bands` | FR-64 | Kappa trên band trùng scikit-learn |
| TC-BR-S05 | `test_qwk_matches_scikit_learn_on_half_points_with_unused_categories` | FR-64 | Kappa nửa điểm trùng scikit-learn, kể cả mức không ai dùng |
| TC-BR-S06 | `test_qwk_is_none_when_undefined_or_too_small` | FR-64 | Kappa không tính được thì là None, không phải số giả |
| TC-BR-S07 | `test_qwk_rejects_a_value_outside_the_categories` | FR-64 | Giá trị ngoài thang bị từ chối |
| TC-BR-S08 | `test_pearson_and_rmse_on_a_small_example` | FR-64 | Pearson, RMSE trên ví dụ tính tay |
| TC-BR-S09 | `test_pearson_and_rmse_are_none_when_undefined` | FR-64 | Pearson, RMSE không tính được thì là None |
| TC-BR-S10 | `test_icc_reproduces_shrout_and_fleiss_1979` | FR-64 | ICC(1,1) và ICC(2,1) tái lập ví dụ Shrout & Fleiss 1979 |
| TC-BR-S11 | `test_icc_is_none_when_too_small_or_undefined` | FR-64 | ICC không tính được thì là None |
| TC-BR-S12 | `test_confusion_rows_follow_the_first_sequence` | FR-64 | Ma trận nhầm lẫn: hàng theo dãy thứ nhất |
| TC-BR-S13 | `test_per_band_recall_and_precision_on_a_hand_made_example` | FR-64 | Recall, precision từng band trên ví dụ tính tay |
| TC-BR-S14 | `test_needs_adjudication` | FR-63 | Quy tắc phân xử: lệch 1,0, lệch band, một bên không chấm được |
| TC-BR-S15 | `test_reference_is_the_mean_of_two_without_adjudication` | FR-63 | Điểm đối chiếu = trung bình hai người |
| TC-BR-S16 | `test_reference_is_the_median_of_three_after_adjudication` | FR-63 | Điểm đối chiếu = trung vị ba người |
| TC-BR-S17 | `test_reference_is_pending_until_the_third_rating_arrives` | FR-64 | Chưa có phiếu thứ ba thì chờ, không so máy |
| TC-BR-S18 | `test_reference_is_unscorable_when_both_raters_say_so` | FR-64 | Hai người thấy không chấm được thì bài không chấm được |
| TC-BR-S19 | `test_reference_with_two_scorable_of_three_is_their_mean_and_the_lower_band` | FR-64 | Hai trên ba phiếu chấm được: trung bình và band thấp hơn |
| TC-BR-S20 | `test_reference_is_unscorable_when_fewer_than_two_of_three_are_scorable` | FR-64 | Dưới hai phiếu chấm được thì không chấm được |
| TC-BR-S21 | `test_reference_is_incomplete_before_both_primary_ratings` | FR-64 | Chưa đủ hai phiếu thì chưa có điểm đối chiếu |
| TC-BR-S22 | `test_a_third_rating_that_was_not_needed_is_ignored` | FR-64 | Phiếu thứ ba không cần thiết bị bỏ qua và được ghi chú |
| TC-BR-S23 | `test_rating_rejects_inconsistent_input` | FR-64 | Phiếu mâu thuẫn bị từ chối ngay khi dựng |
| TC-BR-S24 | `test_rated_response_rejects_a_repeated_rater_or_a_misplaced_adjudication` | FR-63 | Một người chấm hai lần, hay phân xử sai chỗ, bị từ chối |
| TC-BR-S25 | `test_cluster_bootstrap_is_reproducible_for_a_fixed_seed` | FR-64 | Cùng hạt giống cho cùng khoảng tin cậy |
| TC-BR-S26 | `test_cluster_bootstrap_does_not_depend_on_the_order_of_the_items` | FR-64 | Thứ tự dữ liệu không làm đổi khoảng tin cậy |
| TC-BR-S27 | `test_cluster_bootstrap_resamples_speakers_not_responses` | FR-64 | Lấy mẫu lại theo người nói, không theo bài |
| TC-BR-S28 | `test_cluster_bootstrap_needs_three_speakers` | FR-64 | Dưới ba người nói thì không có khoảng tin cậy |
| TC-BR-S29 | `test_cluster_bootstrap_skips_undefined_resamples_unless_most_are` | FR-64 | Bỏ lần lấy mẫu không tính được, trừ khi quá nửa |
| TC-BR-S30 | `test_report_counts` | FR-64 | Bảng đếm của báo cáo đúng |
| TC-BR-S31 | `test_report_keys_come_in_the_specified_order_humans_first` | FR-64 | Người–người đứng trước máy–người; có tham số bootstrap |
| TC-BR-S32 | `test_report_is_json_ready_with_floats_rounded_to_4_decimals` | FR-64 | Báo cáo là JSON hợp lệ, số làm tròn 4 chữ số, không NaN |
| TC-BR-S33 | `test_report_is_reproducible_with_the_default_bootstrap` | FR-64 | Báo cáo tái lập được |
| TC-BR-S34 | `test_report_human_human_block` | FR-64 | Khối người–người đủ chỉ số |
| TC-BR-S35 | `test_report_leaves_pending_responses_out_of_machine_human` | FR-64 | Bài chờ phân xử không vào khối máy–người |
| TC-BR-S36 | `test_report_routing_compares_flagged_and_unflagged_errors` | FR-64 | RQ4: sai số nhóm bị gắn cờ và không bị gắn cờ |
| TC-BR-S37 | `test_report_rounds_overall_scores_to_half_points_with_ties_up` | FR-64 | Làm tròn nửa điểm, trùng thì làm tròn lên |
| TC-BR-S38 | `test_icc_is_two_way_for_a_fixed_pair_whatever_the_slot_order` | FR-64 | Cùng một cặp giám khảo: ICC(2,1), không phụ thuộc thứ tự |
| TC-BR-S39 | `test_icc_is_one_way_when_rater_pairs_rotate` | FR-64 | Cặp giám khảo thay đổi: ICC(1,1) |
| TC-BR-S40 | `test_report_notes_explain_metrics_left_empty` | FR-64 | Chỉ số trống có ghi chú lý do |
| TC-BR-S41 | `test_report_on_no_responses_is_empty_but_well_formed` | FR-64 | Không có bài thì báo cáo rỗng mà vẫn đúng dạng |

### Nhóm I — Tích hợp (`tests/test_ratings.py`)

| Mã | Test | Truy vết | Kiểm điều gì |
| --- | --- | --- | --- |
| TC-BR-I01 | `test_a_batch_gives_every_eligible_response_two_raters_each_in_their_own_order` | AC-61.1 | Đợt lấy đúng bài đủ điều kiện, hai giám khảo, thứ tự riêng |
| TC-BR-I02 | `test_a_batch_needs_two_raters_and_something_to_rate` | AC-61.2 | Thiếu giám khảo hay thiếu bài thì không tạo đợt |
| TC-BR-I03 | `test_the_rating_sheet_carries_no_pseudonym_response_id_or_machine_score` | AC-62.1 | Phiếu không lộ bút danh, mã bài, điểm máy; bản ghi tên trung tính, có nhật ký |
| TC-BR-I04 | `test_a_rater_cannot_open_another_raters_sheet` | AC-62.2 | Phiếu của người khác trả 404 |
| TC-BR-I05 | `test_the_machine_result_stays_closed_to_a_rater_until_they_have_rated` | AC-62.3 | Đường vòng qua báo cáo, lịch sử, khoá, hàng đợi bị chặn tới khi chấm xong |
| TC-BR-I06 | `test_a_rating_follows_the_rating_sheet_rules` | AC-62.4 | Bảy cách sai bị từ chối; phiếu đúng lưu; nộp lần hai 409 |
| TC-BR-I07 | `test_an_unscorable_recording_is_rated_as_such` | AC-62.5 | Phiếu không chấm được |
| TC-BR-I08 | `test_open_sheets_are_counted_in_the_sidebar_and_a_closed_batch_takes_no_more` | AC-62.6 | Con số phiếu chưa làm; đợt đóng không nhận phiếu |
| TC-BR-I09 | `test_a_disagreement_goes_to_a_third_rater_who_did_not_rate_it` | AC-63.1 | Phân xử bỏ qua người đã chấm; phiếu phân xử vẫn mù |
| TC-BR-I10 | `test_the_report_puts_humans_first_and_compares_the_machine_before_any_review` | AC-64.1 | Báo cáo dùng điểm máy trước duyệt; người–người trước |
| TC-BR-I11 | `test_withdrawn_consent_takes_a_response_out_of_report_and_export` | AC-64.2 | Rút đồng thuận là rút khỏi báo cáo và bản xuất |
| TC-BR-I12 | `test_the_export_lists_every_rating_with_rater_pseudonyms_and_the_machine_score` | AC-64.3 | CSV đủ phiếu, bút danh giám khảo, điểm máy |
| TC-BR-I13 | `test_erasing_a_participant_erases_what_raters_said_about_them` | AC-64.4 | Xoá dữ liệu người học xoá luôn phiếu về bài của họ |
| TC-BR-I14 | `test_only_an_administrator_runs_batches` | AC-64.6 | Giảng viên không quản lý đợt được |
| TC-BR-I15 | `test_the_rater_pages_render` | FR-62 | Hai trang của giám khảo hiển thị |
| TC-BR-I16 | `test_the_command_line_report_gives_the_numbers_of_the_screen` | AC-64.5 | Công cụ dòng lệnh cho cùng con số với màn hình |
| TC-BR-I17 | `test_a_teacher_who_opened_the_machine_result_is_not_drawn_to_rate_that_response` | AC-61.3 | Đã mở báo cáo hay lịch sử thì không được giao bài đó; không còn cặp nào thì 422 hoặc bài để ngoài và được đếm |
| TC-BR-I18 | `test_a_sheet_goes_void_once_its_rater_has_seen_the_machine_result` | AC-62.7 | Đóng đợt, xem báo cáo, mở lại: phiếu không còn mù, nộp 409, không còn tính và không còn che |
| TC-BR-I19 | `test_an_administrator_who_rates_stays_blind_on_the_administration_screens` | AC-62.8 | Quản trị viên làm giám khảo: danh sách che bài, bản xuất và báo cáo đợt 409 tới khi nộp xong |
| TC-BR-I20 | `test_the_waiting_count_leaves_out_what_the_teacher_rates_blind` | AC-62.9 | Con số chờ duyệt không đếm bài bị che khỏi hàng đợi của chính người đó |
| TC-BR-I21 | `test_an_adjudicator_who_opened_the_machine_result_is_passed_over` | AC-63.2 | Người phân xử đã xem kết quả của máy thì bài đó bị bỏ qua và được đếm |
| TC-BR-I22 | `test_a_void_sheet_can_be_handed_to_another_rater` | AC-62.10 | Phiếu không còn mù được giao lại cho giám khảo khác ở đúng chỗ chấm; người đang chấm bài đó hoặc đã xem kết quả máy bị bỏ qua |

### Nhóm E — E2E (`tests/e2e/test_ratings_e2e.py`)

| Mã | Test | Truy vết | Kiểm điều gì |
| --- | --- | --- | --- |
| TC-BR-E01 | `test_a_rater_rates_a_sheet_blind_and_moves_on_to_the_next` | AC-62.1 | Giám khảo mở phiếu, không thấy bút danh nào, nộp, sang phiếu sau; phiếu đã nộp chỉ đọc |
| TC-BR-E02 | `test_an_administrator_creates_a_batch_and_reads_the_report` | AC-64.1 | Tạo đợt trên màn hình quản trị, đọc báo cáo: người–người trước máy–người, mốc chưa ký |

## 7. Kết quả chạy

| Lệnh | Kết quả |
| --- | --- |
| `pytest tests/test_assign_unit.py tests/test_agreement.py` | 58 test qua |
| `pytest tests/test_ratings.py` | 23 test qua |
| `pytest -m e2e tests/e2e/test_ratings_e2e.py` | 2 test qua |

## 8. Lỗi tìm thấy trong lúc làm

| Mã | Lỗi | Sửa | Test giữ lại |
| --- | --- | --- | --- |
| D030-B1 | Giảng viên duyệt bài thì `overall_0_6` bị ghi đè bằng điểm của giảng viên; so máy với người trên cột đó là so người với người | Điểm máy lấy từ `old_score` của lần duyệt đầu tiên khi có duyệt | TC-BR-I10 |
| D030-B2 | Bài trong hàng đợi duyệt hiện band của máy cho chính giám khảo đang phải chấm mù bài đó | Hàng đợi bỏ những bài đó ra cho giám khảo ấy; báo cáo, lịch sử, khoá và quyết định trả 403 | TC-BR-I05 |
| D030-B3 | Quy tắc "hai trên ba phiếu chấm được thì band của người gần trung bình hơn" luôn hoà (hai điểm luôn cách đều trung bình của chúng) | Ghi thẳng quy tắc: lấy band thấp hơn, ghi trong docstring | TC-BR-S19 |
| D030-B4 | Một khoảng lệch đúng 1,0 tính bằng phép trừ số thực có thể ra 0,9999999999999996 và lọt khỏi phân xử | So với dung sai 1e-9 | TC-BR-S14 |
| D030-B5 | Báo cáo không ghi số lần lấy mẫu và hạt giống, nên một tệp JSON lưu lại không tự nói được cách tái lập khoảng tin cậy | Thêm khối `bootstrap` vào báo cáo | TC-BR-S31 |
| D030-B6 | Chặn chỉ bắt đầu khi bài vào đợt: giảng viên đã mở báo cáo hay đã duyệt bài từ trước vẫn có thể được giao chấm mù bài đó | Bảng `machine_seen` ghi ai đã mở kết quả của máy; cùng với quyết định duyệt, kế hoạch phân phiếu bỏ những người đó ra | TC-BR-U07, TC-BR-I17 |
| D030-B7 | Đóng đợt là gỡ chặn, mở lại đợt thì nhận phiếu của người có thể đã xem điểm máy trong lúc đóng | Mở kết quả của máy lúc đợt đóng được ghi lại; phiếu của người đó không còn mù và không nhận điểm | TC-BR-I18 |
| D030-B8 | Màn quản trị không qua `_blind`: quản trị viên được chọn làm giám khảo vẫn thấy điểm máy ở danh sách bài, bản xuất nghiên cứu, báo cáo và CSV của đợt | Danh sách che bài như hàng đợi; bản xuất, báo cáo và CSV trả 409 cho tới khi nộp xong | TC-BR-I19 |
| D030-B9 | Con số chờ duyệt trên thanh điều khiển đếm cả bài bị che khỏi hàng đợi của chính giảng viên đó | `count_waiting_review` trừ các bài bị che | TC-BR-I20 |
| D030-B10 | `Repository.save` ghi bằng `INSERT OR REPLACE`: SQLite xoá dòng cũ rồi chèn lại, và với khoá ngoại bật thì lệnh xoá kéo theo (`ON DELETE CASCADE`) mọi phiếu chấm, điểm chấm và bản ghi "đã xem kết quả máy" của bài mỗi khi giảng viên quyết định. Tìm thấy ngày 11/10/2026 khi rà phụ thuộc giữa các bảng để tách dịch vụ | Ghi bằng `INSERT … ON CONFLICT DO UPDATE`, cập nhật dòng tại chỗ | TC-BR-I23 |

D030-B6 đến D030-B9 tìm được khi đối chiếu mã để viết SDD bản 1.3, sau lần commit đầu của D030.
