# Kế hoạch và kết quả kiểm thử D025 — Lộ trình bài học do giáo viên soạn

| Thuộc tính | Giá trị |
| --- | --- |
| Tính năng | D025, lộ trình bài học do giáo viên soạn (FR-45..FR-50, UC-19, UC-20); giao diện D026 |
| Phiên bản mã | nhánh `feat/lesson-path` |
| Người lập | Võ Thanh Sang |
| Ngày | 06/10/2026 |

## 1. Mục tiêu

Chứng minh bốn lời hứa của lộ trình bài học bằng kiểm thử tự động:

1. Mỗi bước được đo bằng luật cố định trên bản chép **không gợi văn bản** cho máy nhận dạng; từ máy không nghe ra hiện là "máy chưa nghe ra", không bao giờ là "sai"; thứ không đo được thì nói "chưa đo được".
2. Sinh viên chỉ thấy phiên bản đã xuất bản; mỗi lượt luyện ghi phiên bản bài học và phiên bản luật đo; lượt luyện không vào hàng đợi duyệt, thống kê chấm hay bản xuất nghiên cứu.
3. Giáo viên soạn được bài từ một đoạn văn, được cảnh báo những chỗ dễ làm máy nghe nhầm, xuất bản, xem thử, theo dõi lớp và sửa nhận định của máy mà không chặn sinh viên, không tạo điểm, có nhật ký.
4. Người học đi trọn luồng trên trình duyệt thật: mở lộ trình, học từng bước, nói tự do nhiều lượt, hoàn thành bài, thấy tiến độ ngày và lịch ôn.

## 2. Ba tầng kiểm thử

| Tầng | Kiểm cái gì | Công cụ | Môi trường | Chạy ở đâu | Lệnh |
| --- | --- | --- | --- | --- | --- |
| 1. Unit | Logic thuần: mô hình bài học, chuẩn hoá chữ, căn chỉnh, bộ đo chín dạng bước, bộ dựng bài, bộ soát lỗi, hộp Leitner, tiến độ, lộ trình mẫu | pytest | Không CSDL, không HTTP, không âm thanh | Máy và CI | `pytest -m unit` |
| 2. Integration | Kho dữ liệu SQLite thật trên tệp tạm + API qua `TestClient` + bộ chạy bước (QC, VAD, nhận dạng giả lập) | pytest, FastAPI TestClient | Bộ nhận dạng giả lập, sóng sin tổng hợp, VAD năng lượng cố định | Máy và CI | `pytest -m integration` |
| 3. E2E | Người dùng thật trên trình duyệt thật: đăng nhập qua form, chọn file, nộp, đọc chữ trên màn hình; giáo viên soạn và sửa nhận định | Playwright + Chromium | Máy chủ uvicorn riêng, CSDL tạm, VAD năng lượng, bản chép giả lập là đoạn văn của bài A2 mẫu | **Chỉ trên máy**; CI tự bỏ qua | `pytest -m e2e` |

## 3. Dữ liệu và môi trường

- **Không dùng giọng người thật** (AGENTS.md). Âm thanh là sóng sin tổng hợp; bộ nhận dạng giả lập trả bản chép biết trước, nên luật đo được kiểm trên văn bản biết trước. Chất lượng nhận dạng thật trên giọng Việt không thuộc phạm vi kế hoạch này và vẫn là [CẦN ĐO].
- **VAD năng lượng ở cả tầng 2 và tầng 3.** Silero (có khi cài torch) không coi sóng sin là tiếng nói; để mặc định thì mọi bước thành "chưa đo được" trên máy có torch. Máy chủ E2E của D025 khởi động qua một đoạn mã nhỏ thay `default_vad` như tầng 2 làm, không thêm cấu hình vào sản phẩm.
- **Bản chép giả lập ở tầng 3** là nguyên văn đoạn đọc của bài "Khu phố của tôi", để sinh viên đạt được các bước có văn bản và hoàn thành bài; bài B1 thì lệch, nên có từ gợi ý bị bỏ để thử lịch ôn.

## 4. Tiêu chí vào và ra

- **Vào:** mã qua `ruff format --check` và `ruff check`; dữ liệu test tổng hợp sinh trong fixture.
- **Ra (được merge):** 100% test tầng 1 và 2 qua trên CI; 100% test tầng 3 qua trên máy trước khi merge; mọi tiêu chí chấp nhận AC-45.1..AC-50.2 có ít nhất một test (kiểm bằng `tests/test_lessons_traceability.py`); mỗi lỗi tìm được có test hồi quy.

## 5. Truy vết tiêu chí chấp nhận

Tiêu chí chấp nhận AC-45.1..AC-50.2 nằm ở `docs/srs/SRS.md`, mục 3.9b.

| Tiêu chí chấp nhận | Test case |
| --- | --- |
| AC-45.1 | TC-LS-I02, TC-LS-E09 |
| AC-45.2 | TC-LS-I03 |
| AC-45.3 | TC-LS-U36, TC-LS-I01 |
| AC-45.4 | TC-LS-U32, TC-LS-U33, TC-LS-E04 |
| AC-46.1 | TC-LS-U08, TC-LS-U09, TC-LS-E02 |
| AC-46.2 | TC-LS-U06, TC-LS-U11 |
| AC-46.3 | TC-LS-U12, TC-LS-U13, TC-LS-U14, TC-LS-U15 |
| AC-46.4 | TC-LS-U16 |
| AC-46.5 | TC-LS-U23, TC-LS-I10, TC-LS-E03 |
| AC-46.6 | TC-LS-I06 |
| AC-47.1 | TC-LS-U24, TC-LS-E08 |
| AC-47.2 | TC-LS-U28 |
| AC-47.3 | TC-LS-I11, TC-LS-E11 |
| AC-47.4 | TC-LS-I15 |
| AC-47.5 | TC-LS-I18, TC-LS-I19, TC-LS-I20 |
| AC-48.1 | TC-LS-U03, TC-LS-I22, TC-LS-E06 |
| AC-48.2 | TC-LS-U31, TC-LS-I23 |
| AC-49.1 | TC-LS-I25, TC-LS-I26, TC-LS-E10 |
| AC-49.2 | TC-LS-I28 |
| AC-50.1 | TC-LS-U34, TC-LS-I08, TC-LS-I36 |
| AC-50.2 | TC-LS-I37 |

Những test ghi FR-4x thay vì AC kiểm hành vi của yêu cầu đó ngoài các tiêu chí đã đánh số (ca biên, ca âm, hồi quy).

## 6. Danh mục test case

Tổng 91 test case: 38 unit, 39 integration, 14 E2E. Theo loại: 45 ca thuận, 24 ca âm, 22 ca biên. Một số hàm có tham số nên chạy thành nhiều ca.

### 6.1. Tầng 1 — Unit

| ID | Hàm test | AC / FR | Loại | Nội dung kiểm |
| --- | --- | --- | --- | --- |
| TC-LS-U01 | `test_student_view_of_a_lesson_never_carries_gap_answers` | FR-46 | Âm | Bản bài học gửi sinh viên không có đáp án chỗ trống |
| TC-LS-U02 | `test_step_and_lesson_reject_inconsistent_configuration` | FR-45 | Âm | Bước và bài có cấu hình mâu thuẫn bị từ chối ngay khi tạo |
| TC-LS-U03 | `test_missed_words_collect_unheard_items_and_wrong_gaps_once` | AC-48.1 | Thuận | Từ cần ôn gồm từ máy chưa nghe ra và đáp án chỗ trống sai, mỗi từ một lần |
| TC-LS-U04 | `test_tokens_unify_numbers_contractions_and_spelling` | FR-46 | Biên | Chữ số, viết tắt, cách viết Anh/Mỹ được quy về cùng một dạng (nhiều cặp) |
| TC-LS-U05 | `test_recogniser_number_formats_match_spelled_out_numbers` | FR-46 | Biên | "1,000" và "21st" của máy nhận dạng khớp "one thousand", "twenty-first" |
| TC-LS-U06 | `test_same_word_accepts_other_forms_and_spellings_only` | AC-46.2 | Thuận | Khác dạng hay khác cách viết vẫn là một từ; từ khác nghĩa gần âm thì không |
| TC-LS-U07 | `test_alignment_is_a_minimal_edit_sequence` | FR-46 | Thuận | Căn chỉnh Levenshtein cho dãy sửa tối thiểu: khớp, thay, bỏ, thêm |
| TC-LS-U08 | `test_read_aloud_marks_each_reference_word_heard_missed_or_unsure` | AC-46.1 | Thuận | "the people friendly": "are" là máy chưa nghe ra, ba từ còn lại nghe ra |
| TC-LS-U09 | `test_low_confidence_or_another_form_is_unsure_not_missed` | AC-46.1 | Biên | Độ tin cậy thấp hoặc dạng khác của từ là "chưa chắc", không phải "chưa nghe ra" |
| TC-LS-U10 | `test_read_aloud_ignores_spelling_convention_numbers_and_contractions` | FR-46 | Biên | Bước đọc to không trừ vì cách viết, chữ số hay viết tắt |
| TC-LS-U11 | `test_keyword_counts_any_form_of_the_word` | AC-46.2 | Thuận | Từ khóa "go" được tính khi máy nghe "went" |
| TC-LS-U12 | `test_gap_classifies_each_blank` | AC-46.3 | Thuận | Một chỗ trống điền đúng, một chỗ điền từ gây nhiễu: mỗi chỗ đúng loại |
| TC-LS-U13 | `test_gap_marks_a_word_outside_the_bank_and_an_unsaid_opening_blank` | AC-46.3 | Âm | Từ ngoài ngân hàng là "từ khác"; chỗ trống đầu câu không nói là "chưa nghe ra" |
| TC-LS-U14 | `test_gap_left_unsaid_is_missing_and_keeps_the_word_before_it` | AC-46.3 | Biên | Bỏ một chỗ trống: chỗ đó là chưa nghe ra, từ đứng trước vẫn được tính |
| TC-LS-U15 | `test_speech_after_the_sentence_is_not_pulled_into_the_last_blank` | AC-46.3 | Biên | Nói thêm sau câu không bị đếm vào chỗ trống cuối (hồi quy D025-B1) |
| TC-LS-U16 | `test_words_outside_speech_are_not_counted` | AC-46.4 | Biên | Từ nằm ngoài mọi đoạn có tiếng nói theo VAD không được đếm |
| TC-LS-U17 | `test_nothing_heard_is_unmeasured_never_marked_wrong` | FR-46 | Âm | Không nghe được gì thì là "chưa đo được", không bao giờ tô từ thành chưa nghe ra (mọi dạng bước) |
| TC-LS-U18 | `test_strictness_moves_the_pass_mark` | FR-46 | Biên | Cùng một lượt: mức Dễ đạt, mức Chặt chưa đạt |
| TC-LS-U19 | `test_look_up_counts_only_content_words` | FR-46 | Thuận | Bước đọc rồi nói lại chỉ tính từ mang nghĩa, a/the/of chỉ để tham khảo |
| TC-LS-U20 | `test_starter_needs_the_frame_at_the_start_and_enough_words_after_it` | FR-46 | Âm | Bước khung câu cần khung ở đầu câu trả lời và đủ số từ sau khung |
| TC-LS-U21 | `test_outline_counts_linking_words_in_outline_order` | FR-46 | Thuận | Bước dàn ý đếm từ nối theo đúng thứ tự dàn ý |
| TC-LS-U22 | `test_picture_step_does_not_pass_a_recited_word_bank` | FR-46 | Âm | Đọc thuộc lòng ngân hàng từ không đạt bước mô tả tranh |
| TC-LS-U23 | `test_free_step_compares_rounds` | AC-46.5 | Thuận | Lượt 3 có quãng ngừng dài nhất ngắn hơn lượt 1: kết quả nêu thay đổi đó |
| TC-LS-U24 | `test_generator_builds_the_four_stage_ladder_from_one_text` | AC-47.1 | Thuận | Một đoạn văn và sáu từ khóa: đủ bốn bậc theo thứ tự, bước cuối nói tự do ba lượt (A2, B1, B2) |
| TC-LS-U25 | `test_generated_gap_blanks_key_words_and_mixes_in_distractors` | FR-47 | Thuận | Bước chỗ trống dựng tự động xoá đúng từ khóa và trộn từ gây nhiễu |
| TC-LS-U26 | `test_generator_gives_each_controlled_step_its_own_sentence` | FR-47 | Biên | Các bước nhắc lại, chỗ trống, đọc rồi nói lại dùng câu khác nhau (hồi quy D025-B16) |
| TC-LS-U27 | `test_word_lesson_practises_keywords_in_threes_then_reuses_them_in_free_speech` | FR-47 | Thuận | Bài chỉ có từ khóa: bước ghép câu theo nhóm ba từ, rồi nói tự do có mục tiêu dùng lại từ |
| TC-LS-U28 | `test_linter_warns_about_asr_traps` | AC-47.2 | Thuận | Chữ số và "colour": một mục soát lỗi cho từng chỗ |
| TC-LS-U29 | `test_linter_flags_gap_answers_that_cannot_be_told_apart_by_ear` | FR-47 | Âm | Đáp án và từ gây nhiễu chỉ khác đuôi từ, hay đồng âm: bị cảnh báo |
| TC-LS-U30 | `test_linter_warns_about_a_missing_free_step_and_absent_keywords` | FR-47 | Âm | Thiếu bước nói tự do, từ khóa không có trong văn bản: bị cảnh báo |
| TC-LS-U31 | `test_review_boxes_follow_leitner_intervals` | AC-48.2 | Thuận | Hộp 1 ôn đạt hẹn sau 3 ngày, rồi 7 ngày, rồi xong; ôn không đạt về hộp 1 |
| TC-LS-U32 | `test_lesson_completes_only_with_enough_passed_steps_and_the_free_step` | AC-45.4 | Biên | Bài 5 bước: đạt 4 bước chưa làm bước tự do thì chưa xong; làm thêm thì xong |
| TC-LS-U33 | `test_free_step_is_done_only_when_speech_was_measured` | AC-45.4 | Âm | Một lượt im lặng ở bước tự do không làm bài hoàn thành (hồi quy D025-B8) |
| TC-LS-U34 | `test_today_counts_seconds_spoken_per_vietnam_day` | AC-50.1 | Biên | Mục tiêu ngày cộng giây đã nói theo ngày giờ Việt Nam, bỏ lượt không đo được |
| TC-LS-U35 | `test_next_lesson_without_assessment_follows_path_order_and_says_why` | FR-50 | Thuận | Chưa có bài đánh giá: bài nên học theo thứ tự lộ trình, kèm câu giải thích |
| TC-LS-U36 | `test_sample_path_runs_by_level_and_topic_with_one_lesson_per_practice_task` | AC-45.3 | Thuận | Lộ trình mẫu đi A2 → B1 → B2, mỗi trình độ ít nhất năm chủ đề khác nhau; 16 bài soạn đủ và một bài cho mỗi nhiệm vụ D023 (D027) |
| TC-LS-U37 | `test_sample_lessons_raise_no_linter_warnings` | FR-47 | Thuận | Ba mươi mốt bài mẫu không có cảnh báo soát lỗi nào |
| TC-LS-U38 | `test_passed_reading_with_a_missed_word_names_it_in_the_tip` | FR-46 | Thuận | Bước đọc đạt nhưng thiếu một từ mang nghĩa: gợi ý nêu đúng từ đó (D025-B19) |

Tệp: `tests/test_lessons_unit.py`.

### 6.2. Tầng 2 — Integration

| ID | Hàm test | AC / FR | Loại | Nội dung kiểm |
| --- | --- | --- | --- | --- |
| TC-LS-I01 | `test_fresh_install_seeds_the_sample_path` | AC-45.3 | Thuận | Bản cài mới có lộ trình mẫu đã xuất bản, 18 bài, bài nào cũng kết thúc bằng nói tự do |
| TC-LS-I02 | `test_students_see_the_published_version_until_republished` | AC-45.1 | Thuận | Sửa và lưu nháp chưa xuất bản: sinh viên vẫn nhận phiên bản 1 |
| TC-LS-I03 | `test_attempt_records_lesson_version_and_rules_version` | AC-45.2 | Thuận | Lượt luyện ghi phiên bản bài học và phiên bản luật đo |
| TC-LS-I04 | `test_archived_lesson_is_hidden_from_learners_but_its_attempts_stay_readable` | FR-45 | Biên | Bài lưu trữ biến khỏi lộ trình, lượt luyện cũ vẫn đọc được |
| TC-LS-I05 | `test_attempts_on_a_lesson_of_a_draft_path_are_refused` | FR-45 | Âm | Lộ trình nháp, đã lưu trữ hay bài chưa xuất bản thì không nhận lượt luyện (hồi quy D025-B2) |
| TC-LS-I06 | `test_practice_clip_qc_accepts_short_recordings_assessment_does_not` | AC-46.6 | Biên | Bản ghi 3 giây: lượt luyện được nhận, bài đánh giá bị từ chối vì quá ngắn |
| TC-LS-I07 | `test_step_runner_says_why_a_recording_was_not_measured` | FR-46 | Âm | Im lặng, quá ngắn, không phải tiếng Anh: chưa đo được, kèm lý do và gợi ý |
| TC-LS-I08 | `test_recorded_step_counts_its_speaking_time_and_an_unmeasured_one_does_not` | AC-50.1 | Biên | Lượt đo được cộng giây đã nói; lượt không đo được cộng 0 |
| TC-LS-I09 | `test_learner_lesson_view_never_carries_gap_answers_but_attempts_use_them` | FR-46 | Âm | API sinh viên không trả đáp án chỗ trống, nhưng bộ đo vẫn dùng đáp án |
| TC-LS-I10 | `test_free_round_three_result_carries_the_comparison_with_round_one` | AC-46.5 | Thuận | Qua API: kết quả lượt 3 có so sánh với lượt 1 |
| TC-LS-I11 | `test_students_cannot_edit_paths` | AC-47.3 | Âm | Sinh viên gọi API soạn bài nhận 403 |
| TC-LS-I12 | `test_lesson_endpoints_check_login_and_role` | FR-47 | Âm | Mọi endpoint bài học đòi đăng nhập; endpoint soạn bài đòi vai trò giảng viên |
| TC-LS-I13 | `test_keywords_without_a_text_build_a_word_lesson` | FR-47 | Thuận | Tạo bài: có đoạn văn, chỉ có từ khóa, hay để trống, mỗi trường hợp ra đúng loại bài |
| TC-LS-I14 | `test_lesson_page_is_a_preview_for_teachers_and_the_lesson_for_students` | FR-47 | Thuận | Trang bài học là xem thử với giảng viên, là bài học với sinh viên |
| TC-LS-I15 | `test_model_audio_that_does_not_match_its_text_is_flagged` | AC-47.4 | Âm | Giọng mẫu lệch văn bản: cảnh báo kèm tỷ lệ từ máy nghe ra |
| TC-LS-I16 | `test_teacher_cannot_inject_media_keys_through_the_lesson_form` | FR-47 | Âm | Khoá giọng mẫu và ảnh chỉ đến từ tải lên, biểu mẫu không gài được |
| TC-LS-I17 | `test_teacher_preview_attempt_stores_nothing` | FR-47 | Thuận | Lượt xem thử của giảng viên được đo rồi bỏ, không lưu gì |
| TC-LS-I18 | `test_path_export_import_roundtrip` | AC-47.5 | Thuận | Xuất rồi nhập lại: cùng chặng, bài, bước, ở trạng thái nháp |
| TC-LS-I19 | `test_import_rejects_a_file_that_is_not_a_path_object` | AC-47.5 | Âm | Tệp không phải lộ trình trả 422 thay vì 500 (hồi quy D025-B11) |
| TC-LS-I20 | `test_rejected_import_leaves_no_half_built_path` | AC-47.5 | Âm | Tệp lỗi ở chặng sau không để lại lộ trình nửa chừng (hồi quy D025-B12) |
| TC-LS-I21 | `test_import_gives_new_ids_and_drops_media_keys` | FR-47 | Biên | Tệp nhập được cấp mã bài mới và bỏ khoá media của nơi khác (hồi quy D025-B17) |
| TC-LS-I22 | `test_missed_words_are_scheduled_for_tomorrow` | AC-48.1 | Thuận | Từ khóa máy chưa nghe ra được hẹn ôn ngày hôm sau theo giờ Việt Nam |
| TC-LS-I23 | `test_review_session_moves_words_through_the_leitner_boxes` | AC-48.2 | Thuận | Buổi ôn qua API chuyển từ qua các hộp Leitner |
| TC-LS-I24 | `test_review_items_of_an_archived_lesson_are_closed` | FR-48 | Biên | Mục ôn của bài đã lưu trữ được đóng, không bị đếm mãi (hồi quy D025-B15) |
| TC-LS-I25 | `test_teacher_override_updates_the_result_and_is_audited` | AC-49.1 | Thuận | Giáo viên đổi một từ thành nghe ra: sinh viên thấy nhận định mới, dấu đã xem lại; nhật ký có dòng |
| TC-LS-I26 | `test_passed_steps_and_the_teacher_view_respect_overrides` | AC-49.1 | Biên | Kết luận do giáo viên sửa được tính vào bước đã đạt, cả hai chiều |
| TC-LS-I27 | `test_teacher_word_correction_keeps_its_status_type` | FR-49 | Biên | Nhận định giáo viên sửa giữ đúng kiểu, không phát cảnh báo khi xuất (hồi quy D025-B10) |
| TC-LS-I28 | `test_lesson_attempts_stay_out_of_queue_and_research_export` | AC-49.2 | Âm | Lượt luyện không vào hàng đợi duyệt, bản xuất nghiên cứu hay danh sách bài nộp |
| TC-LS-I29 | `test_attempt_recordings_belong_to_their_learner` | FR-49 | Âm | Chỉ chủ lượt luyện và giảng viên nghe được; người khác nhận 404; chủ xoá được cả tệp |
| TC-LS-I30 | `test_listening_to_a_lesson_recording_is_audited` | FR-49 | Thuận | Giảng viên nghe bản ghi luyện tập thì nhật ký có dòng (hồi quy D025-B14) |
| TC-LS-I31 | `test_deleting_an_attempt_is_audited_without_its_content` | FR-45 | Thuận | Sinh viên xoá lượt luyện của mình: nhật ký ghi ai xoá, không ghi nội dung (hồi quy D025-B9) |
| TC-LS-I32 | `test_orphan_cleanup_keeps_lesson_recordings_and_teacher_media` | FR-45 | Âm | Lệnh dọn tệp mồ côi không coi bản ghi luyện tập và tệp của giảng viên là mồ côi (hồi quy D025-B18) |
| TC-LS-I33 | `test_retention_sweep_covers_lesson_attempts` | FR-45 | Thuận | Quét thời hạn lưu trữ xoá bản ghi và lời máy nghe được của lượt luyện quá hạn, giữ kết quả từng từ |
| TC-LS-I34 | `test_a_learner_records_a_step_straight_after_signing_in` | FR-46 | Âm | Chưa đồng thuận lưu bản ghi thì không ghi được bước nào |
| TC-LS-I35 | `test_personal_export_and_erasure_cover_lesson_attempts` | FR-45 | Thuận | Bản xuất dữ liệu cá nhân và lệnh xoá theo người học có cả lượt luyện |
| TC-LS-I36 | `test_daily_goal_counts_seconds_spoken` | AC-50.1 | Thuận | Hai lượt tổng 95 giây: mục tiêu ngày hiện 95 trên 180 giây |
| TC-LS-I37 | `test_next_lesson_follows_the_weakest_criterion` | AC-50.2 | Thuận | Band B1, tiêu chí yếu nhất Range: bài nên học là bài chưa xong đầu tiên của chặng Range B1 |
| TC-LS-I38 | `test_units_carry_their_topic_through_the_api_export_and_import` | FR-47 | Thuận | Chủ đề của chặng đi qua API, sửa được, chủ đề lạ bị từ chối, giữ nguyên khi xuất rồi nhập (D027) |
| TC-LS-I39 | `test_an_older_sample_path_is_laid_out_by_topic_once` | FR-45 | Biên | Cơ sở dữ liệu có lộ trình mẫu kiểu cũ (chưa có chủ đề) được xếp lại theo chủ đề đúng một lần: lượt luyện giữ nguyên, chặng của giảng viên giữ nguyên, lần khởi động sau không đè thay đổi của giảng viên (D027) |

Tệp: `tests/test_lessons_integration.py`.

### 6.3. Tầng 3 — E2E

| ID | Hàm test | AC / FR | Loại | Nội dung kiểm |
| --- | --- | --- | --- | --- |
| TC-LS-E01 | `test_new_learner_sees_the_path_and_the_first_lesson_next` | FR-50 | Thuận | Sinh viên mới: ba phần A2, B1, B2; bài nên học là bài A2 đầu tiên, có cờ Bắt đầu; 31 bài đều chưa học; mục tiêu 0/180 giây; 0 mục ôn; không có chữ band |
| TC-LS-E02 | `test_read_aloud_step_marks_words_and_moves_on` | AC-46.1 | Thuận | Bước đọc to: 6 từ gợi ý tô đậm; nộp file, khung kết quả ghi rõ là kết quả giả lập (máy chủ E2E dùng bộ nhận dạng giả lập), kết luận Đạt, từng từ được tô, không từ nào "máy chưa nghe ra"; Bước tiếp mở bước nhắc lại |
| TC-LS-E03 | `test_free_step_runs_in_shrinking_rounds_and_compares_them` | AC-46.5 | Thuận | Bước nói tự do: lượt 1 45 giây, lượt 2 35 giây; sau lượt 2 có mục "So với lượt 1" nêu số từ mỗi phút |
| TC-LS-E04 | `test_completing_a_lesson_marks_it_done_on_the_path` | AC-45.4 | Thuận | Làm đủ bảy bước: trang lộ trình hiện bài đã hoàn thành, 1/31 bài, mục tiêu ngày khác 0, bài nên học chuyển sang bài khác |
| TC-LS-E06 | `test_review_page_without_due_items_says_when_the_next_one_comes` | AC-48.1 | Biên | Từ gợi ý bị bỏ được hẹn ôn ngày mai: hôm nay trang ôn tập báo không có mục đến hạn và nêu đúng ngày ôn tới |
| TC-LS-E07 | `test_phone_layout_of_the_path_and_a_lesson_has_no_sideways_scroll` | FR-45 | Biên | Màn 375 px: trang lộ trình và trang bài học không tràn ngang; dãy bước thành một hàng |
| TC-LS-E08 | `test_teacher_builds_a_lesson_from_a_text_and_publishes_it` | AC-47.1 | Thuận | Giáo viên tạo lộ trình, chặng B1, bài từ đoạn văn: sáu bước, bước cuối nói tự do; gõ chữ số thì bộ soát lỗi báo; xuất bản v1; xem thử |
| TC-LS-E09 | `test_students_see_the_published_version_until_the_teacher_publishes_again` | AC-45.1 | Thuận | Đổi tên bài trong bản nháp: sinh viên vẫn thấy tên cũ; xuất bản v2 thì thấy tên mới |
| TC-LS-E10 | `test_teacher_corrects_a_word_and_the_learner_sees_the_review` | AC-49.1 | Thuận | Giáo viên mở lượt luyện, đổi nhận định một từ, ghi chú; sinh viên mở lại bài thấy "Giáo viên đã xem lại", ghi chú và từ được đánh dấu |
| TC-LS-E11 | `test_students_get_no_authoring_rights` | AC-47.3 | Âm | Sinh viên mở trang soạn bài: báo không có quyền; gọi API soạn bài nhận 403 |
| TC-LS-E12 | `test_teacher_pages_fit_a_phone` | FR-47 | Biên | Màn 375 px: ba trang của giảng viên không tràn ngang |
| TC-LS-E13 | `test_a_coin_on_the_trail_opens_its_card_and_then_the_lesson` | FR-45 | Thuận | Bấm một bài trên đường đi: hiện thẻ bài, Esc đóng thẻ, nút Bắt đầu mở bài học (D027) |
| TC-LS-E14 | `test_navigation_is_a_sidebar_on_the_left_with_icons` | FR-45 | Thuận | Thanh điều khiển nằm bên trái, nội dung trang bắt đầu sau nó; mỗi mục có icon từ bộ icon của hệ thống, mục hiện tại được đánh dấu (D027) |

Tệp: `tests/e2e/test_lessons_e2e.py`.

## 7. Kết quả lần chạy ngày 06/10/2026

| Tầng | Số ca chạy | Qua | Lỗi | Thời gian |
| --- | --- | --- | --- | --- |
| Unit | 49 | 49 | 0 | dưới 1 giây |
| Integration | 39 | 39 | 0 | khoảng 25 giây |
| E2E (máy, Playwright 1.62, Chromium) | 14 | 14 | 0 | khoảng 16 giây |

Toàn bộ bộ test của repo trên máy (lần chạy ngày 07/10/2026, sau D027): 821 qua, 10 bỏ qua (không gồm E2E); 41 ca E2E của cả ba tầng giao diện (D023, D024, D025) đều qua. Độ phủ dòng: gói `aicefr.lessons` 83–100% từng tệp (`align`, `model`, `review`, `seed` 100%; `checks` 94%; `lint` 83%), `lesson_repository` 84%, `lessons_api` 78%; toàn repo 90%.

Bảy ca từng được đánh dấu `xfail(strict=True)` khi viết bộ test (D025-B8 đến D025-B13) nay chạy như ca hồi quy thường sau khi sửa lỗi.

## 8. Lỗi tìm được khi kiểm thử

| Mã | Mức | Lỗi | Tìm bằng | Sửa | Test hồi quy |
| --- | --- | --- | --- | --- | --- |
| D025-B1 | Major | Chỗ trống khớp không tốn chi phí với **mọi** từ, nên khi người học nói thêm sau câu ("... a park nearby, okay"), phép căn chỉnh (giải hoà từ cuối) đặt từ cuối cùng vào chỗ trống cuối và chấm "từ khác" | Ca E2E hoàn thành bài (TC-LS-E04) | Chỗ trống chỉ khớp không tốn chi phí với đáp án hoặc từ trong ngân hàng; từ khác tốn một phép thay | TC-LS-U15 |
| D025-B2 | Major | Nộp lượt luyện vào bài của lộ trình **chưa xuất bản** vẫn được nhận nếu biết mã bài (trang bài học thì đã chặn) | Rà bảo mật API | Một cổng chung `_live` cho cả đọc bài và nộp lượt | TC-LS-I05 |
| D025-B3 | Major | `escapeHtml` dùng chung không thoát dấu nháy, nên giá trị chèn vào thuộc tính (`title="…"`, `data-name="…"`) có thể đóng thuộc tính và thêm thuộc tính khác | Rà mã giao diện | Thoát `"` và `'` | `tests/test_frontend_contracts.py` (quy ước thoát), kiểm bằng mắt |
| D025-B4 | Minor | Tô từ gợi ý thay lần lượt từng từ trên HTML đã chèn thẻ, nên từ gợi ý như "word" khớp vào `class="hint-word"` và làm vỡ đoạn văn | Rà mã giao diện | Một lượt duy nhất trên văn bản gốc, thoát từng mảnh | TC-LS-E02 (đếm đúng 6 từ tô đậm) |
| D025-B5 | Minor | Ở màn 375 px trang soạn lộ trình rộng 506 px: nhãn ẩn của cột thao tác (`position: absolute`) thoát khỏi khung cuộn của bảng | Đo bằng trình duyệt | Khung `.table-scroll` thành khối định vị | TC-LS-E12 |
| D025-B6 | Minor | Đồng hồ hiện câu và đồng hồ chuẩn bị vẫn chạy khi người học đã sang bước khác, rồi kéo focus về nút ghi âm | Rà mã giao diện | Dừng mọi đồng hồ của bước khi đổi bước | Kiểm bằng tay |
| D025-B7 | Minor | Trang lộ trình dùng lẫn hai bộ tên tiêu chí ("vốn từ" trong câu gợi ý của máy chủ, "Phạm vi ngôn ngữ" trên nhãn bài) | Xem giao diện thật | Phần luyện tập dùng một bộ tên của D023; biểu mẫu giảng viên ghi kèm tên CEFR gốc | Kiểm bằng mắt |
| D025-B8 | Major | Một lượt im lặng hay bị từ chối ở bước nói tự do (không đo được, 0 giây nói) vẫn làm bài hoàn thành, vì mọi lượt đã lưu đều tính là "đã làm" | Viết ca unit | Bước tự do chỉ tính là đã làm khi có giây nói đo được; xem thử cũng theo luật đó | TC-LS-U33 |
| D025-B9 | Major | Sinh viên xoá lượt luyện của mình mà không có dòng nhật ký (AC-35.5 đòi có, như với bài đánh giá) | Viết ca integration | Ghi `ERASE_OWN_LESSON_ATTEMPT`: ai xoá, xoá gì, không ghi nội dung | TC-LS-I31 |
| D025-B10 | Minor | Nhận định giáo viên sửa được nạp lại dưới dạng chuỗi chứ không phải trạng thái, nên mỗi lần xuất kết quả có cảnh báo Pydantic | Viết ca integration | Đổi về `WordStatus` khi áp sửa đổi | TC-LS-I27 |
| D025-B11 | Major | Nhập một tệp JSON không phải đối tượng lộ trình (một mảng, một chặng không phải đối tượng) trả 500 | Viết ca integration | Kiểm kiểu từng phần, báo 422 | TC-LS-I19 |
| D025-B12 | Major | Tệp nhập có band sai ở chặng sau vẫn để lại một lộ trình nháp nửa chừng | Viết ca integration | Kiểm toàn bộ tệp trước khi ghi bất cứ thứ gì | TC-LS-I20 |
| D025-B13 | Major | Máy nhận dạng viết "1,000" hay "21st" thì không khớp "one thousand", "twenty-first" trong văn bản, nên từ đọc đúng hiện "máy chưa nghe ra" | Viết ca unit | Bỏ dấu phân cách hàng nghìn; số thứ tự dựng cho mọi số | TC-LS-U05 |
| D025-B14 | Minor | Giảng viên nghe bản ghi luyện tập không để lại dòng nhật ký (bản ghi bài đánh giá thì có `AUDIO_ACCESS`) | Rà quyền riêng tư | Ghi `AUDIO_ACCESS` cho mọi lần nghe bản ghi luyện tập | TC-LS-I30 |
| D025-B15 | Minor | Mục ôn "bài nói" của bài đã lưu trữ không vào được buổi ôn nhưng vẫn được đếm, nên số mục đến hạn không bao giờ về 0 | Rà mã | Đóng mục đó khi dựng buổi ôn; số trên trang lộ trình là số mục của buổi ôn hôm nay | TC-LS-I24 |
| D025-B16 | Minor | Bộ dựng bài dùng lại câu: ở B1 bước đọc rồi nói lại trùng câu của bước chỗ trống; ở A2 bước nhắc lại và bước chỗ trống trùng câu | Rà mã | Theo dõi câu gốc đã dùng; chỗ trống ưu tiên câu chưa dùng | TC-LS-U26 |
| D025-B17 | Minor | Tệp nhập có thể mang mã bài trùng với bài đã có (lỗi 500) hoặc khoá giọng mẫu, ảnh của nơi khác | Rà bảo mật | Bài nhập luôn nhận mã mới; bỏ mọi khoá media | TC-LS-I21 |
| D025-B18 | **Critical** | Lệnh `orphans --delete` coi mọi bản ghi luyện tập và giọng mẫu, ảnh của giảng viên (cùng thư mục tải lên) là tệp mồ côi và xoá; quét thời hạn lưu trữ thì bỏ sót lượt luyện | Rà quyền riêng tư | Lệnh dọn tệp đọc thêm khoá của `step_attempt` và `lesson_media`; quét lưu trữ xoá bản ghi và lời máy nghe được của lượt luyện quá hạn | TC-LS-I32, TC-LS-I33 |
| D025-B19 | Minor | Bước đọc đạt nhưng thiếu một từ mang nghĩa thì gợi ý vẫn khen chung chung, không nói từ nào cần đọc lại | Thử bằng Whisper thật với bản đọc tổng hợp thiếu một từ | Gợi ý nêu từ mang nghĩa đầu tiên máy chưa nghe ra | TC-LS-U38 |
| D025-B20 | Major | Khi máy chủ chạy bộ nhận dạng giả lập, khung kết quả trông như một nhận xét thật (3/54 từ, "chưa đạt"); chủ dự án đọc thử và tưởng hệ thống hỏng | Chủ dự án thử trên localhost | Ghi "Kết quả giả lập, không phải của bạn" ngay trong khung kết quả; kiểm tra giọng mẫu cũng báo không đo được | TC-LS-E02 |
| D025-B21 | Minor | Ca E2E chọn tệp ngay khi trang bài học vừa mở; khi bài tải xong, trang dựng bước và đặt lại bộ ghi âm nên tệp vừa chọn mất (người thật không gặp vì khung ghi âm ẩn cho tới khi bài tải xong) | Chạy E2E sau D027 | Ca E2E chờ bước hiện ra và bộ ghi âm sẵn sàng rồi mới chọn tệp | TC-LS-E06, TC-LS-E04 |

## 9. Giới hạn còn lại

- Tầng 3 không chạy trên CI, như D023 và D024.
- Chưa kiểm với Whisper thật và giọng Việt thật. Ngưỡng đạt (75% số từ ở bước đọc) dựa trên số liệu công bố (McGuire 2025), chưa đo trên người học của dự án: [CẦN ĐO] với bản ghi thử có đồng thuận trước khi mở cho sinh viên thật.
- Ghi giọng mẫu bằng micro thật và tải ảnh cho bước mô tả tranh mới kiểm bằng API và bằng tay; tầng 3 chưa có ca riêng.
- Nội dung 18 bài của lộ trình mẫu cần giảng viên Khoa Ngoại ngữ duyệt; kiểm thử chỉ chứng minh luật đo và luồng chạy đúng, không chứng minh bài hay.
