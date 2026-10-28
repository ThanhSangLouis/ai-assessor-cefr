# Kế hoạch và kết quả kiểm thử D023 — Chế độ luyện tập

| Thuộc tính | Giá trị |
| --- | --- |
| Tính năng | D023, chế độ luyện tập "Đánh giá để học" (FR-40..FR-44, UC-18) |
| Phiên bản mã | nhánh `feat/che-do-luyen-tap`, PR #5 |
| Người lập | Võ Thanh Sang |
| Ngày | 06/10/2026 |

## 1. Mục tiêu

Chứng minh ba lời hứa của chế độ luyện tập bằng kiểm thử tự động:

1. Mỗi mục tiêu luyện tập được đo đúng luật, có chỗ trong bản ghi làm căn cứ; thứ không đo được thì nói "chưa đo được", không bao giờ thành "chưa hoàn thành".
2. Bài luyện tập **không** có band, **không** vào hàng đợi giảng viên, bản xuất nghiên cứu hay số liệu máy chấm của lớp; chỉ chủ bài xem được.
3. Người học đi trọn luồng trên trình duyệt thật: nhận gợi ý, xem mục tiêu, nộp file hoặc ghi âm, đọc kết quả, quay lại lộ trình.

## 2. Ba tầng kiểm thử

| Tầng | Kiểm cái gì | Công cụ | Môi trường | Chạy ở đâu | Lệnh |
| --- | --- | --- | --- | --- | --- |
| 1. Unit | Logic thuần: ngân hàng đề, bộ đo mục tiêu, luật gợi ý, chuỗi ngày, lời khuyên | pytest | Không CSDL, không HTTP, không âm thanh | Máy và CI | `pytest -m unit` |
| 2. Integration | Pipeline thật (QC, VAD, trích đặc trưng, bộ đo) + SQLite thật trên tệp tạm + API qua `TestClient` | pytest, FastAPI TestClient | Bộ nhận dạng giả lập, âm thanh sóng sin tổng hợp, VAD năng lượng cố định | Máy và CI | `pytest -m integration` |
| 3. E2E | Người dùng thật trên trình duyệt thật: đăng nhập qua form, bấm nút, chọn file, ghi âm micro giả, đọc chữ trên màn hình | Playwright 1.62 + Chromium | Máy chủ uvicorn riêng, CSDL tạm, `AICEFR_JOB_MODE=inline` | **Chỉ trên máy** (chủ dự án chọn ngày 06/10/2026); CI tự bỏ qua vì không cài extra `e2e` | `pytest -m e2e` |

Tầng 3 cần: `pip install -e ".[dev,e2e]"` rồi `playwright install chromium` (một lần). Không có Playwright thì `pytest.importorskip` bỏ qua cả tệp, bộ test còn lại vẫn chạy.

## 3. Dữ liệu và môi trường

- **Không dùng giọng người thật** (AGENTS.md). Tầng 2 dùng sóng sin 10, 25, 35, 40 giây; tầng 3 dùng tệp WAV sóng sin và micro giả của Chromium.
- **Bộ nhận dạng giả lập** trả bản chép cố định, nên bộ đếm từ được kiểm trên văn bản biết trước. Chất lượng nhận dạng thật không thuộc phạm vi kế hoạch này.
- **VAD cố định là VAD năng lượng ở tầng 2.** Silero (có khi cài torch) không coi sóng sin là tiếng nói, nên để mặc định thì kết quả mục tiêu khoảng lặng khác nhau giữa máy có torch và CI.
- **Máy chủ E2E** đặt `AICEFR_LOGIN_RATE=1000`, vì mỗi test đăng nhập một lần từ cùng 127.0.0.1. Giới hạn thật 10 lần/phút có test riêng ở `tests/test_security.py`.

## 4. Tiêu chí vào và ra

- **Vào:** mã qua `ruff format --check` và `ruff check`; dữ liệu test tổng hợp đã sinh trong fixture.
- **Ra (được merge):** 100% test tầng 1 và 2 qua trên CI; 100% test tầng 3 qua trên máy trước khi merge; độ phủ dòng của `aicefr.practice` ≥ 90%; không còn lỗi mức Critical/Blocker; mỗi lỗi tìm được có test hồi quy.

## 5. Truy vết tiêu chí chấp nhận

Tiêu chí chấp nhận AC-40.1..AC-44.4 nằm ở `docs/srs/SRS.md`, mục 3.9.

| Tiêu chí chấp nhận | Test case |
| --- | --- |
| AC-40.1 | TC-PR-U01, TC-PR-U02 |
| AC-40.2 | TC-PR-I01, TC-PR-I22 |
| AC-40.3 | TC-PR-U03 |
| AC-40.4 | TC-PR-I02 |
| AC-41.1 | TC-PR-I11, TC-PR-E04 |
| AC-41.2 | TC-PR-U11, TC-PR-U15, TC-PR-U26, TC-PR-U31 |
| AC-41.3 | TC-PR-U23, TC-PR-U24 |
| AC-41.4 | TC-PR-I12, TC-PR-I13, TC-PR-I14 |
| AC-42.1 | TC-PR-U33, TC-PR-I21 |
| AC-42.2 | TC-PR-U34, TC-PR-I38 |
| AC-42.3 | TC-PR-I10 |
| AC-43.1 | TC-PR-U53, TC-PR-I05, TC-PR-I30 |
| AC-43.2 | TC-PR-U43, TC-PR-U44, TC-PR-U45 |
| AC-43.3 | TC-PR-U46 |
| AC-44.1 | TC-PR-I07, TC-PR-I25 |
| AC-44.2 | TC-PR-I08, TC-PR-I35 |
| AC-44.3 | TC-PR-I31, TC-PR-E11 |
| AC-44.4 | TC-PR-I03 |

Những test ghi FR-4x thay vì AC kiểm hành vi của yêu cầu đó ngoài các tiêu chí đã đánh số (ca biên, ca âm, hồi quy).

## 6. Danh mục test case

Tổng 107 test case: 53 unit, 41 integration, 13 E2E. Theo loại: 45 ca thuận, 37 ca âm, 25 ca biên. Một số hàm có tham số nên chạy thành nhiều ca (ghi rõ trong cột nội dung).

### 6.1. Tầng 1 — Unit

| ID | Hàm test | AC / FR | Loại | Nội dung kiểm |
| --- | --- | --- | --- | --- |
| TC-PR-U01 | `test_bank_has_one_task_per_criterion_and_band` | AC-40.1 | Thuận | Ngân hàng đủ 15 ô, mỗi tiêu chí × band đúng một đề, mã đề đúng quy ước |
| TC-PR-U02 | `test_every_task_has_missions_tips_and_a_duration_above_the_qc_floor` | AC-40.1 | Biên | Mọi đề có mục tiêu, mẹo; thời lượng tối thiểu ≥ 30 giây (sàn QC) |
| TC-PR-U03 | `test_read_aloud_passages_have_no_digits_or_dual_spellings` | AC-40.3 | Âm | Đoạn đọc to không có chữ số, không có từ hai cách viết Anh/Mỹ |
| TC-PR-U04 | `test_no_practice_topic_overlaps_an_assessment_task` | FR-40 | Âm | Chủ đề luyện không trùng đề đánh giá P3/P4 |
| TC-PR-U05 | `test_malformed_missions_are_rejected_at_construction` | FR-40 | Âm | Mục tiêu sai hình dạng (thiếu danh sách từ, tỉ lệ > 1, ngưỡng 0, nhãn rỗng) bị từ chối |
| TC-PR-U06 | `test_normalize_strips_punctuation_keeps_apostrophes_and_splits_hyphens` | FR-41 | Thuận | Tách từ: bỏ dấu câu, giữ nháy trong từ, tách gạch nối |
| TC-PR-U07 | `test_normalize_of_empty_or_punctuation_only_text_is_empty` | FR-41 | Biên | Chuỗi rỗng hoặc chỉ có dấu câu ra danh sách rỗng |
| TC-PR-U08 | `test_speaking_time_ignores_silence_at_both_ends` | FR-41 | Thuận | Thời lượng nói không tính im lặng ở hai đầu |
| TC-PR-U09 | `test_speaking_time_exactly_at_target_is_met` | FR-41 | Biên | Đúng bằng ngưỡng là hoàn thành; thiếu 0,01 giây là chưa (2 ca) |
| TC-PR-U10 | `test_speaking_time_falls_back_to_word_timestamps_without_segments` | FR-41 | Biên | Không có đoạn VAD thì lấy mốc từ của bản chép |
| TC-PR-U11 | `test_speaking_time_is_unmeasured_without_segments_or_words` | AC-41.2 | Âm | Không đoạn nói, không từ: chưa đo được, kèm lý do |
| TC-PR-U12 | `test_longest_pause_counts_only_inner_gaps_and_points_at_the_second` | FR-41 | Thuận | Khoảng lặng dài nhất chỉ tính ở giữa, chỉ ra giây bắt đầu |
| TC-PR-U13 | `test_pause_exactly_at_target_is_met` | FR-41 | Biên | Khoảng lặng đúng bằng ngưỡng là hoàn thành (2 ca) |
| TC-PR-U14 | `test_single_segment_means_no_pause` | FR-41 | Biên | Một đoạn nói duy nhất: khoảng lặng bằng 0 |
| TC-PR-U15 | `test_pause_is_unmeasured_without_segments_rather_than_zero` | AC-41.2 | Âm | Không có đoạn nói: khoảng lặng chưa đo được, không phải 0 |
| TC-PR-U16 | `test_use_words_counts_distinct_items_including_phrases_with_times` | FR-41 | Thuận | Đếm từ khác nhau, kể cả cụm nhiều từ, kèm giây |
| TC-PR-U17 | `test_a_word_used_many_times_counts_once` | FR-41 | Biên | Một từ dùng nhiều lần chỉ tính một |
| TC-PR-U18 | `test_no_listed_word_means_zero_and_no_evidence` | FR-41 | Âm | Không dùng từ nào: bằng 0, không có căn cứ |
| TC-PR-U19 | `test_unique_words_ignore_fillers_and_case` | FR-41 | Thuận | Số từ khác nhau bỏ từ đệm, không phân biệt hoa thường |
| TC-PR-U20 | `test_past_verbs_count_irregular_and_ed_forms_but_not_adjectives_or_present_lookalikes` | FR-41 | Thuận | Đếm động từ quá khứ bất quy tắc và -ed, bỏ tính từ và dạng trùng hiện tại |
| TC-PR-U21 | `test_past_verbs_skip_short_words_and_excluded_words` | FR-41 | Âm | Bỏ từ ngắn và từ trong danh sách loại trừ |
| TC-PR-U22 | `test_evidence_per_mission_is_capped_at_max_hits` | FR-41 | Biên | Căn cứ mỗi mục tiêu tối đa 8 chỗ |
| TC-PR-U23 | `test_conditionals_need_if_and_a_modal_in_the_same_sentence` | AC-41.3 | Âm | Câu điều kiện cần if và động từ khuyết thiếu trong cùng câu (hồi quy D023-B1) |
| TC-PR-U24 | `test_conditional_modal_must_be_within_12_words_of_if` | AC-41.3 | Biên | Động từ khuyết thiếu cách if 12 từ: tính; 13 từ: không (2 ca) |
| TC-PR-U25 | `test_read_aloud_scores_matched_share_and_lists_unheard_words` | FR-41 | Thuận | Đọc to: tỉ lệ từ khớp và danh sách từ máy chưa nghe ra |
| TC-PR-U26 | `test_read_aloud_without_reference_is_unmeasured` | AC-41.2 | Âm | Không có đoạn mẫu: chưa đo được |
| TC-PR-U27 | `test_text_only_transcript_still_counts_but_evidence_has_no_time` | FR-41 | Biên | Bản chép không có mốc từ vẫn đếm, căn cứ không có giây |
| TC-PR-U28 | `test_result_keeps_task_id_and_rules_version` | FR-41 | Thuận | Kết quả giữ mã đề và phiên bản bộ luật |
| TC-PR-U29 | `test_attempt_conclusion_is_derived_from_missions` | FR-41 | Thuận | Kết luận cả lần luyện suy ra từ các mục tiêu (ba trạng thái) |
| TC-PR-U30 | `test_practice_result_needs_at_least_one_mission` | FR-41 | Âm | Kết quả luyện phải có ít nhất một mục tiêu |
| TC-PR-U31 | `test_unmeasured_mission_needs_a_reason_and_no_conclusion` | AC-41.2 | Âm | Chưa đo được thì phải có lý do và không có kết luận |
| TC-PR-U32 | `test_measure_description_per_mission_kind` | FR-41 | Thuận | Câu mô tả số đo theo từng loại mục tiêu |
| TC-PR-U33 | `test_without_assessment_start_at_fluency_a2` | AC-42.1 | Thuận | Chưa có bài đánh giá: gợi ý độ trôi chảy A2 |
| TC-PR-U34 | `test_weakest_criterion_and_band_of_assessment_drive_suggestion` | AC-42.2 | Thuận | Tiêu chí yếu nhất và band của bài đánh giá quyết định gợi ý |
| TC-PR-U35 | `test_after_current_band_go_up_then_down` | FR-42 | Biên | Xong band hiện tại thì lên band trên rồi mới xuống band dưới |
| TC-PR-U36 | `test_after_weakest_criterion_continue_the_path` | FR-42 | Thuận | Xong tiêu chí yếu nhất thì tiếp lộ trình |
| TC-PR-U37 | `test_band_without_indicators_follows_path_from_that_band` | FR-42 | Biên | Có band nhưng không có chỉ báo tiêu chí: đi lộ trình từ band đó |
| TC-PR-U38 | `test_tried_but_not_completed_is_suggested_again` | FR-42 | Thuận | Đã thử chưa hoàn thành thì vẫn được gợi ý lại |
| TC-PR-U39 | `test_everything_completed_reviews_the_oldest` | FR-42 | Biên | Xong cả lộ trình: gợi ý ôn đề lâu nhất |
| TC-PR-U40 | `test_empty_bank_or_assessment_only_tasks_give_no_suggestion` | FR-42 | Âm | Ngân hàng rỗng hoặc chỉ có đề đánh giá: không gợi ý |
| TC-PR-U41 | `test_review_list_is_latest_not_completed_oldest_first` | FR-43 | Thuận | Mục Ôn lại: lần gần nhất chưa hoàn thành, cũ nhất trước |
| TC-PR-U42 | `test_streak_counts_consecutive_days_and_survives_until_today_ends` | FR-43 | Thuận | Chuỗi ngày đếm ngày liên tiếp, hôm nay chưa luyện vẫn giữ |
| TC-PR-U43 | `test_one_rest_day_per_week_keeps_streak_but_does_not_count` | AC-43.2 | Biên | Một ngày nghỉ mỗi tuần giữ chuỗi; nghỉ hai ngày liền hoặc hai lần trong 7 ngày thì đứt |
| TC-PR-U44 | `test_rest_days_exactly_seven_days_apart_are_allowed` | AC-43.2 | Biên | Hai ngày nghỉ cách đúng 7 ngày: được; cách 6 ngày: đứt |
| TC-PR-U45 | `test_rest_yesterday_while_today_is_open_keeps_streak` | AC-43.2 | Biên | Hôm qua nghỉ, hôm nay còn mở: chuỗi vẫn còn |
| TC-PR-U46 | `test_days_follow_vietnam_time` | AC-43.3 | Biên | Ngày tính theo giờ Việt Nam, mốc 17:00 UTC (3 ca) |
| TC-PR-U47 | `test_summary_counts_today_and_seven_days` | FR-43 | Thuận | Tóm tắt ngày: số lần hôm nay, mục tiêu, bảy ngày |
| TC-PR-U48 | `test_summary_before_practising_today` | FR-43 | Biên | Chưa luyện hôm nay: mục tiêu chưa đạt, chuỗi tính tới hôm qua |
| TC-PR-U49 | `test_takeaway_comes_from_first_unmet_mission_and_suggests_missing_words` | FR-43 | Thuận | Lời khuyên lấy từ mục tiêu chưa đạt đầu tiên, gợi ý từ còn thiếu |
| TC-PR-U50 | `test_every_unmet_mission_kind_gets_specific_advice` | FR-43 | Thuận | Mỗi loại mục tiêu chưa đạt có lời khuyên chỉ ra chỗ cụ thể (7 ca) |
| TC-PR-U51 | `test_takeaway_when_all_met_and_when_unmeasured` | FR-43 | Biên | Lời khuyên khi xong hết và khi có mục tiêu chưa đo được |
| TC-PR-U52 | `test_takeaway_does_not_suggest_words_from_a_changed_task` | FR-43 | Âm | Đề đổi mục tiêu thì không gợi ý từ của đề khác |
| TC-PR-U53 | `test_previous_measures_compare_only_same_kind` | AC-43.1 | Biên | So với lần trước chỉ khi cùng loại mục tiêu |

Tệp: `tests/test_practice_unit.py`.

### 6.2. Tầng 2 — Integration

| ID | Hàm test | AC / FR | Loại | Nội dung kiểm |
| --- | --- | --- | --- | --- |
| TC-PR-I01 | `test_task_repository_seeds_15_practice_tasks_and_lists_assessment_by_default` | AC-40.2 | Thuận | Seed 15 đề luyện; danh sách mặc định chỉ có đề đánh giá |
| TC-PR-I02 | `test_bank_version_bump_updates_the_row_and_same_version_leaves_it` | AC-40.4 | Biên | Tăng phiên bản thì cập nhật; cùng phiên bản thì không đụng tới |
| TC-PR-I04 | `test_later_save_without_purpose_keeps_the_stored_purpose` | FR-44 | Âm | Lần ghi sau không truyền purpose vẫn giữ purpose cũ |
| TC-PR-I05 | `test_attempts_keep_submission_order_within_one_second_and_filter_by_task` | AC-43.1 | Biên | Thứ tự nộp giữ đúng kể cả cùng một giây; lọc theo đề (hồi quy D023-B2) |
| TC-PR-I06 | `test_latest_assessment_ignores_practice_and_unscored_rows` | FR-42 | Âm | Bài đánh giá gần nhất bỏ qua bài luyện và bài chưa có band |
| TC-PR-I07 | `test_teacher_queue_never_holds_practice_even_if_marked_for_review` | AC-44.1 | Âm | Hàng đợi giảng viên không nhận bài luyện kể cả khi bị đánh dấu chờ duyệt |
| TC-PR-I08 | `test_research_rows_exclude_practice` | AC-44.2 | Âm | Tầng lưu trữ: bản xuất nghiên cứu không có bài luyện |
| TC-PR-I09 | `test_practice_summary_counts_processed_attempts_per_criterion` | FR-44 | Thuận | Thống kê luyện tập chỉ đếm lần đã xử lý xong, theo tiêu chí |
| TC-PR-I10 | `test_speaking_profile_carries_the_practice_task_for_the_weakest_criterion` | AC-42.3 | Thuận | Hồ sơ năng lực có next_task_id; không có chỉ báo thì để rỗng |
| TC-PR-I11 | `test_practice_attempt_is_measured_not_scored_and_not_routed` | AC-41.1 | Thuận | Pipeline: bài luyện được đo mục tiêu, không chấm, không chuyển giảng viên |
| TC-PR-I12 | `test_non_english_practice_is_rejected_not_sent_to_a_teacher` | AC-41.4 | Âm | Bài luyện không phải tiếng Anh bị từ chối kèm lý do |
| TC-PR-I13 | `test_non_english_assessment_still_goes_to_a_teacher` | AC-41.4 | Âm | Hồi quy: bài đánh giá không phải tiếng Anh vẫn chờ giảng viên |
| TC-PR-I14 | `test_practice_with_empty_transcript_is_rejected_with_its_reason` | AC-41.4 | Âm | Bài luyện không có lời bị từ chối kèm lý do |
| TC-PR-I15 | `test_too_short_practice_is_rejected_by_qc_without_calling_asr` | FR-41 | Âm | Bài luyện quá ngắn bị QC từ chối, không gọi nhận dạng |
| TC-PR-I16 | `test_practice_flagged_by_qc_is_still_measured_and_keeps_the_qc_reason` | FR-41 | Biên | Bài 25 giây bị QC gắn cờ vẫn được đo, giữ lý do QC |
| TC-PR-I17 | `test_looping_transcript_is_measured_on_the_trimmed_part` | FR-41 | Âm | Bản chép lặp từ: đo trên phần đã cắt, giữ cờ ASR_HALLUCINATION |
| TC-PR-I18 | `test_read_aloud_matching_the_reference_is_completed` | FR-41 | Thuận | Đọc to khớp đoạn mẫu thì hoàn thành |
| TC-PR-I19 | `test_assessment_response_has_no_practice_result` | FR-44 | Âm | Hồi quy: bài đánh giá không mang kết quả luyện tập |
| TC-PR-I20 | `test_every_practice_endpoint_requires_login` | FR-44 | Âm | Mọi endpoint luyện tập cần đăng nhập (401) |
| TC-PR-I21 | `test_new_learner_gets_an_a2_suggestion_and_the_full_path` | AC-42.1 | Thuận | API: người mới được gợi ý A2 và thấy đủ lộ trình |
| TC-PR-I22 | `test_practice_tasks_never_appear_in_the_assessment_task_list` | AC-40.2 | Âm | API: đề luyện không lọt vào danh sách đề đánh giá |
| TC-PR-I23 | `test_task_detail_returns_missions_tips_and_passage` | FR-40 | Thuận | API chi tiết đề trả mục tiêu, mẹo, đoạn văn, danh sách từ |
| TC-PR-I24 | `test_task_detail_rejects_assessment_and_unknown_tasks` | FR-40 | Âm | API chi tiết đề: đề đánh giá và đề không tồn tại trả 404 (2 ca) |
| TC-PR-I25 | `test_practice_submission_gets_a_result_without_band_and_skips_the_queue` | AC-44.1 | Thuận | Nộp bài luyện: có kết quả, không band, không vào hàng đợi, lộ trình cập nhật |
| TC-PR-I26 | `test_completing_the_suggested_task_moves_the_suggestion_on` | FR-42 | Thuận | Hoàn thành nhiệm vụ gợi ý thì gợi ý chuyển sang nhiệm vụ kế |
| TC-PR-I27 | `test_practice_without_the_terms_is_refused` | FR-44 | Âm | Chưa đồng thuận thì không nộp được bài luyện (403) |
| TC-PR-I28 | `test_submission_to_an_unknown_task_is_refused` | FR-40 | Âm | Nộp vào đề không tồn tại bị từ chối (422) |
| TC-PR-I29 | `test_qc_rejected_practice_counts_toward_neither_goal_nor_path` | FR-43 | Âm | Bài bị QC từ chối không tính vào mục tiêu ngày và lộ trình |
| TC-PR-I30 | `test_second_attempt_compares_with_the_previous_one_on_the_same_task` | AC-43.1 | Biên | Lần sau so với lần trước cùng đề, kể cả nộp cùng một giây |
| TC-PR-I31 | `test_only_the_owner_can_open_a_practice_result` | AC-44.3 | Âm | Chỉ chủ bài xem được; sinh viên khác và giảng viên nhận 404 |
| TC-PR-I32 | `test_assessment_response_cannot_be_opened_as_practice` | FR-44 | Âm | Bài đánh giá và mã không tồn tại không mở được bằng trang luyện |
| TC-PR-I33 | `test_deleting_your_practice_attempt_removes_it_from_the_path` | FR-44 | Thuận | Tự xoá bài luyện thì biến mất khỏi lộ trình |
| TC-PR-I34 | `test_class_stats_keep_practice_apart_from_scoring_numbers` | FR-44 | Thuận | Thống kê lớp tách bài luyện khỏi số liệu máy chấm |
| TC-PR-I35 | `test_admin_research_export_excludes_practice` | AC-44.2 | Âm | Endpoint xuất nghiên cứu của quản trị không có bài luyện |
| TC-PR-I36 | `test_personal_export_includes_practice_and_explains_the_field` | FR-44 | Thuận | Bản xuất dữ liệu cá nhân có bài luyện và giải thích trường practice |
| TC-PR-I37 | `test_progress_and_profile_ignore_practice` | FR-44 | Âm | Trang tiến độ và hồ sơ năng lực không tính bài luyện |
| TC-PR-I38 | `test_suggestion_follows_the_weakest_criterion_of_the_latest_assessment` | AC-42.2 | Thuận | API: gợi ý theo tiêu chí yếu nhất của bài đánh giá gần nhất |
| TC-PR-I39 | `test_practice_pages_mark_navigation_and_load_their_scripts` | FR-40 | Thuận | Trang luyện tập đánh dấu mục điều hướng, nạp đúng script; khách không thấy mục |
| TC-PR-I40 | `test_progress_page_sends_practice_to_the_practice_result` | FR-41 | Thuận | Trang chờ xử lý chuyển bài luyện tới trang kết quả luyện |
| TC-PR-I41 | `test_practice_report_json_round_trips_into_a_response` | FR-41 | Thuận | JSON báo cáo của bài luyện nạp lại được thành Response |

Tệp: `tests/test_practice_integration.py`.

### 6.3. Tầng 3 — E2E

| ID | Hàm test | AC / FR | Loại | Nội dung kiểm |
| --- | --- | --- | --- | --- |
| TC-PR-E02 | `test_task_page_shows_missions_before_speaking` | FR-40 | Thuận | Trang nhiệm vụ hiện đúng đề và các mục tiêu trước khi ghi âm |
| TC-PR-E03 | `test_word_task_shows_chips_and_read_aloud_task_shows_passage` | FR-40 | Thuận | Đề dùng từ hiện thẻ từ; đề đọc to hiện đoạn văn |
| TC-PR-E04 | `test_uploading_a_file_leads_to_a_result_with_evidence` | AC-41.1 | Thuận | Chọn file, nộp, tự chuyển sang kết quả: hoàn thành 2/2, có chip căn cứ |
| TC-PR-E05 | `test_clicking_evidence_seeks_the_recording` | FR-41 | Thuận | Bấm chip căn cứ thì trình phát tua đúng giây |
| TC-PR-E06 | `test_continue_button_opens_the_next_suggested_task` | FR-42 | Thuận | Nút Luyện tiếp mở nhiệm vụ gợi ý kế tiếp |
| TC-PR-E08 | `test_too_short_file_is_rejected_with_reason_and_not_counted` | FR-43 | Âm | File 10 giây bị từ chối, nói lý do, không tính vào mục tiêu ngày của D023 |
| TC-PR-E09 | `test_fake_microphone_recording_is_submitted_and_processed` | FR-41 | Âm | Ghi âm bằng micro giả, chuyển mã, xử lý; bản 3 giây bị từ chối có lý do |
| TC-PR-E10 | `test_without_the_terms_a_warning_shows_and_submit_is_disabled` | FR-44 | Âm | Chưa đồng thuận: hiện cảnh báo, nút ghi âm và ô chọn file bị tắt |
| TC-PR-E11 | `test_another_learner_cannot_see_your_result` | AC-44.3 | Âm | Người khác mở link kết quả thì không thấy gì |
| TC-PR-E12 | `test_my_responses_tags_practice_and_opens_its_result` | FR-44 | Thuận | Bài của tôi gắn nhãn Luyện tập, Không chấm, mở đúng trang kết quả |
| TC-PR-E13 | `test_teacher_sees_class_practice_without_per_student_rows` | FR-44 | Thuận | Giảng viên thấy khối Luyện tập của lớp, không có dòng theo sinh viên |
| TC-PR-E14 | `test_phone_layout_of_a_task_has_no_horizontal_scroll` | FR-43 | Biên | Màn 375 px: trang nhiệm vụ không tràn ngang, một cột |
| TC-PR-E15 | `test_states_are_readable_by_screen_readers` | FR-43 | Thuận | Trạng thái mục tiêu trên trang kết quả đọc được bằng trình đọc màn hình (chữ ẩn) |

Tệp: `tests/e2e/test_practice_e2e.py`.

TC-PR-E01 và TC-PR-E07 đã bỏ ngày 06/10/2026: D025 thay trang chính luyện tập (gợi ý, vòng mục tiêu, lộ trình 15 ô) bằng lộ trình bài học. Ca tương ứng nay là TC-LS-E01 và TC-LS-E04 trong `docs/test/TEST_PLAN_D025.md`. Mã các ca còn lại giữ nguyên.

## 7. Kết quả lần chạy ngày 06/10/2026

| Tầng | Số ca chạy | Qua | Lỗi | Thời gian |
| --- | --- | --- | --- | --- |
| Unit | 64 | 64 | 0 | dưới 1 giây |
| Integration | 42 | 42 | 0 | khoảng 10 giây |
| E2E (máy, Chromium 151) | 15 | 15 | 0 | khoảng 15 giây |

Toàn bộ bộ test của repo: xem log CI của PR #5. Độ phủ dòng của gói `aicefr.practice`: 96–100% từng tệp.

## 8. Lỗi tìm được khi kiểm thử

| Mã | Mức | Lỗi | Tìm bằng | Sửa | Test hồi quy |
| --- | --- | --- | --- | --- | --- |
| D023-B1 | Major | Luật câu điều kiện đếm nhầm "If so, fine." vì "would" của câu trước nằm trong cửa sổ 12 từ | Viết ca unit | Chỉ tìm động từ khuyết thiếu trong cùng câu | TC-PR-U23, TC-PR-U24 |
| D023-B2 | Major | Hai lần nộp trong cùng một giây thì không so được với lần trước (so `created_at` chỉ tới giây) | Ca integration | Xếp theo `rowid`, tìm lần trước theo vị trí | TC-PR-I05, TC-PR-I30 |
| D023-B3 | Minor | Vòng mục tiêu ngày hiện "1" và "/2" trên hai dòng | Xem giao diện thật | Đổi bố cục ô số sang flex | Kiểm bằng mắt; trang này nay là lộ trình bài học D025, vòng mục tiêu kiểm ở TC-LS-E01 và TC-LS-E04 |
| D023-B4 | Minor | Nhãn mục tiêu lặp lại danh sách từ đã hiện thành thẻ | Xem giao diện thật | Bỏ danh sách khỏi nhãn | TC-PR-E03 |
| D023-B5 | Minor | URL và comment của tính năng viết bằng tiếng Việt, trái quy ước 10b của `SPEC_WEB.md` | Chủ dự án review | Đổi sang `/practice`, `/practice/{task_id}`, `/practice/results/{id}`; đổi luôn `/tien-do` → `/my-progress`, `/review/thong-ke` → `/review/stats` | `tests/test_web.py`, TC-PR-I39 |

Ba vấn đề của chính bộ test E2E cũng đã sửa, ghi lại để người sau khỏi vấp:

- Đợi URL theo đuôi: `/login?next=/practice` cũng kết thúc bằng `/practice`. Nay so đường dẫn.
- `wait_for_function` bị CSP của app chặn (không có `unsafe-eval`). Nay hỏi lặp qua `evaluate`.
- Giới hạn đăng nhập 10 lần/phút làm test sau bị chặn. Nay máy chủ E2E đặt `AICEFR_LOGIN_RATE`.

## 9. Giới hạn còn lại

- Tầng 3 không chạy trên CI. Muốn có bằng chứng E2E trong log pipeline thì thêm một job cài Chromium (khoảng 2 phút).
- Chưa kiểm với Whisper thật. Bộ đếm phụ thuộc chất lượng bản chép; trang kết quả có ghi rõ điều này.
- Giao diện tối và bản điện thoại mới kiểm bằng mắt và bằng một ca E2E bố cục (TC-PR-E14); chưa có so sánh ảnh chụp.
- Nội dung 15 nhiệm vụ cần giảng viên Khoa Ngoại ngữ duyệt; kiểm thử chỉ chứng minh luật đếm đúng, không chứng minh nhiệm vụ hay.
