# Kế hoạch và kết quả kiểm thử D039–D042 — Bằng chứng học tập

| Thuộc tính | Giá trị |
| --- | --- |
| Tính năng | D039 chẩn đoán phát âm theo lỗi đặc trưng của người Việt (FR-75, FR-76); D040 thực nghiệm phản hồi đầy đủ so với chỉ điểm (FR-77, FR-78); D041 thời gian giảng viên và phần máy tự xử lý (FR-79); D042 tiến bộ đáng tin theo sai số đo (FR-80). BR-37..BR-39 |
| Phiên bản mã | nhánh `feat/d039-d042` |
| Người lập | Võ Thanh Sang |
| Ngày | 11/10/2026 |

## 1. Mục tiêu

1. **Chẩn đoán chỉ nói khi có căn cứ.** Một lỗi chỉ có tỉ lệ khi đủ 8 lần gặp; từ giảng viên đã sửa không thành lỗi; bản của lớp không chỉ ra ai.
2. **Phản hồi bị giữ ở máy chủ, đúng người, đúng lúc.** Chỉ người nhóm "Chỉ điểm", chỉ báo cáo bài đánh giá của chính họ, chỉ khi thực nghiệm đang chạy; rời được bất cứ lúc nào.
3. **Kết quả thực nghiệm tái lập được và không lộ người.** Hạt giống lưu lại; người đã rời không vào số; CSV theo mã.
4. **Thời gian giảng viên là số đo, không là khẳng định.** Không nêu trung vị dưới 5 mẫu; phiên bỏ dở không tính.
5. **"Tiến bộ" phải vượt sai số đo**, và sai số đo phải có nguồn.

## 2. Ba tầng kiểm thử

| Tầng | Kiểm cái gì | Công cụ | Môi trường | Chạy ở đâu | Lệnh |
| --- | --- | --- | --- | --- | --- |
| 1. Unit | Luật năm lỗi, hồ sơ phát âm; chia nhóm, cặp đầu–cuối, bootstrap, Hedges g; phút duyệt, Wilson; cặp thử lại, SEM, RCI | pytest | Hàm thuần | Máy và CI | `pytest tests/test_learning_evidence_unit.py` |
| 2. Integration | Bước bài học thật với bộ nhận dạng giả; API phát âm; vòng đời thực nghiệm, giữ phản hồi, rời, rút đồng ý, xoá dữ liệu; phiên duyệt; đặt SEM | pytest, FastAPI TestClient | SQLite thật trên tệp tạm, VAD năng lượng như `tests/test_lessons_integration.py` | Máy và CI | `pytest tests/test_learning_evidence.py` |
| 3. E2E | Mục phát âm trên trang Tiến độ; quản trị viên mở thực nghiệm, người học nhóm "Chỉ điểm" thấy lời giải thích rồi rời; thẻ ở Thống kê lớp; khung sai số đo ở tab Cấu hình | Playwright + Chromium | Máy chủ uvicorn của `test_lessons_e2e.py` | **Chỉ trên máy**; CI tự bỏ qua | `pytest -m e2e tests/e2e/test_learning_evidence_e2e.py` |

## 3. Dữ liệu và môi trường

- Chỉ dữ liệu tổng hợp: âm sin, bản chép giả, điểm đặt tay. Không bản ghi người thật, không số liệu từ Speak & Improve.
- Điểm và phản hồi của bài đánh giá được ghi thẳng vào `report_json` như `tests/test_progress_and_stats.py`: thứ được kiểm là phần giữ lại và tổng hợp, không phải phần chấm.

## 4. Tiêu chí vào và ra

- **Vào:** mã qua `ruff format --check` và `ruff check`.
- **Ra (được merge):** 100% test tầng 1 và 2 qua trên CI; 100% test tầng 3 qua trên máy trước khi merge; mọi tiêu chí AC-75.1..AC-80.6 có ít nhất một test (kiểm bằng `tests/test_product_traceability.py`).

## 5. Truy vết tiêu chí chấp nhận

Tiêu chí chấp nhận AC-75.1..AC-80.6 nằm ở `docs/srs/SRS.md`, mục 3.9j.

| Tiêu chí chấp nhận | Test case |
| --- | --- |
| AC-75.1 | TC-LE-U01 |
| AC-75.2 | TC-LE-U02 |
| AC-75.3 | TC-LE-U04 |
| AC-75.4 | TC-LE-U05 |
| AC-75.5 | TC-LE-I01 |
| AC-75.6 | TC-LE-I02 |
| AC-75.7 | TC-LE-E01 |
| AC-76.1 | TC-LE-I03 |
| AC-76.2 | TC-LE-E03 |
| AC-77.1 | TC-LE-U06 |
| AC-77.2 | TC-LE-I04 |
| AC-77.3 | TC-LE-I05 |
| AC-77.4 | TC-LE-I06 |
| AC-77.5 | TC-LE-I07 |
| AC-77.6 | TC-LE-I08 |
| AC-77.7 | TC-LE-I11 |
| AC-77.8 | TC-LE-E02 |
| AC-77.9 | TC-LE-I16 |
| AC-78.1 | TC-LE-U07 |
| AC-78.2 | TC-LE-U08 |
| AC-78.3 | TC-LE-U09 |
| AC-78.4 | TC-LE-I09 |
| AC-78.5 | TC-LE-I10 |
| AC-79.1 | TC-LE-I12 |
| AC-79.2 | TC-LE-U10 |
| AC-79.3 | TC-LE-U11 |
| AC-79.4 | TC-LE-U12 |
| AC-79.5 | TC-LE-I13 |
| AC-80.1 | TC-LE-U13 |
| AC-80.2 | TC-LE-U14 |
| AC-80.3 | TC-LE-U15 |
| AC-80.4 | TC-LE-I14 |
| AC-80.5 | TC-LE-I15 |
| AC-80.6 | TC-LE-E04 |

## 6. Danh mục test case

### Tầng 1 — Unit (`tests/test_learning_evidence_unit.py`)

| Mã | Test | Truy vết | Kiểm điều gì |
| --- | --- | --- | --- |
| TC-LE-U01 | `test_classify_names_the_pattern_behind_a_spelling_gap` | AC-75.1 | Mười một cặp chữ viết và chữ máy nghe, mỗi cặp ra đúng một trong năm lỗi |
| TC-LE-U02 | `test_classify_stays_silent_when_no_pattern_explains_the_gap` | AC-75.2 | Nghe đúng, từ khác hẳn, không nghe được gì, từ chức năng: không gắn lỗi |
| TC-LE-U03 | `test_opportunities_count_what_a_word_lets_the_speaker_show` | FR-75 | Số lần gặp của mỗi từ: -ed kèm âm cuối, cụm phụ âm, th; e câm không là âm cuối; "bus" không là số nhiều |
| TC-LE-U04 | `test_profile_reports_a_rate_only_from_enough_opportunities` | AC-75.3 | 1 lần gặp: không có tỉ lệ; 8 lần: có tỉ lệ, ví dụ dừng ở 5, lỗi đủ dữ liệu đứng đầu |
| TC-LE-U05 | `test_profile_respects_teacher_corrections_and_skips_unmeasured_steps` | AC-75.4 | Từ giảng viên sửa thành nghe được không là lỗi; bước không đo được không tính |
| TC-LE-U06 | `test_assignment_is_balanced_and_reproducible_from_the_seed` | AC-77.1 | Cùng hạt giống, thứ tự khác: cùng kết quả; lệch tối đa 1 người; hạt giống khác: kết quả khác |
| TC-LE-U07 | `test_pre_post_needs_a_later_score_far_enough_from_the_first` | AC-78.1 | Bỏ điểm trước khi vào; bài cuối phải cách bài đầu đủ `min_days` |
| TC-LE-U08 | `test_effect_size_and_interval_point_the_same_way` | AC-78.2 | Hedges g và khoảng bootstrap cùng chiều, tái lập được với cùng hạt giống |
| TC-LE-U09 | `test_analysis_leaves_out_withdrawn_participants` | AC-78.3 | Người đã rời không vào số nào; một người mỗi nhóm thì không có khoảng và g |
| TC-LE-U10 | `test_idle_review_sessions_are_left_out_and_counted` | AC-79.2 | Phiên quá 30 phút bị bỏ và đếm riêng; phiên chưa xong không tính |
| TC-LE-U11 | `test_wilson_interval_matches_the_textbook_value` | AC-79.3 | Wilson 8/10 = [0,490; 0,943]; 0/0 không có khoảng |
| TC-LE-U12 | `test_kpi_reports_time_saved_only_from_enough_samples` | AC-79.4 | Dưới 5 mẫu không có trung vị; đủ mẫu: tiết kiệm 75 %, tỉ lệ máy tự xử lý 75 % |
| TC-LE-U13 | `test_retest_pairs_use_each_response_once_and_respect_the_window` | AC-80.1 | Mỗi bài một cặp; quá 48 giờ không là cặp |
| TC-LE-U14 | `test_sem_is_sd_of_differences_over_root_two_and_needs_enough_pairs` | AC-80.2 | SEM = SD hiệu / √2; dưới 10 cặp không có SEM |
| TC-LE-U15 | `test_reliable_change_verdicts` | AC-80.3 | Năm kết luận và ngưỡng 1,96 · SEM · √(2/k) |

### Tầng 2 — Integration (`tests/test_learning_evidence.py`)

| Mã | Test | Truy vết | Kiểm điều gì |
| --- | --- | --- | --- |
| TC-LE-I01 | `test_lesson_word_marks_name_the_vietnamese_pattern` | AC-75.5 | Bước nhắc lại: "because" nghe thành "becau" có nhãn `final_consonant` |
| TC-LE-I02 | `test_learner_profile_counts_errors_against_opportunities` | AC-75.6 | Hai lượt cùng lỗi: âm cuối 2 lỗi, đủ dữ liệu, ví dụ dẫn về bài học |
| TC-LE-I03 | `test_class_profile_is_for_staff_and_names_nobody` | AC-76.1 | Bản của lớp: 2 người học, ví dụ chỉ có từ và chữ máy nghe, không bút danh; sinh viên 403 |
| TC-LE-I04 | `test_study_enrols_active_students_half_in_each_arm` | AC-77.2 | Chỉ sinh viên đồng ý nghiên cứu vào nhóm, chia 2–3; thực nghiệm thứ hai 409; nhật ký có hạt giống |
| TC-LE-I05 | `test_study_needs_enough_students` | AC-77.3 | Dưới 4 người: 422 kèm lý do |
| TC-LE-I06 | `test_score_only_arm_gets_the_score_and_nothing_more` | AC-77.4 | Nhóm "Chỉ điểm" chỉ có điểm, mức; nhóm kia và giảng viên thấy đủ |
| TC-LE-I07 | `test_leaving_the_study_or_closing_it_brings_feedback_back` | AC-77.5 | Rời thực nghiệm: phản hồi trở lại ngay; đóng: không ai còn trong thực nghiệm |
| TC-LE-I09 | `test_survey_opens_only_in_the_survey_phase_and_checks_answers` | AC-78.4 | Khảo sát chỉ mở ở giai đoạn khảo sát, kiểm đủ năm câu 1–5; chuyển giai đoạn chỉ đi tới |
| TC-LE-I10 | `test_study_export_carries_codes_not_people` | AC-78.5 | CSV theo mã P001, không bút danh, không mã tài khoản; sinh viên 403 |
| TC-LE-I11 | `test_erasure_takes_the_learner_out_of_every_study` | AC-77.7 | Xoá dữ liệu người học là xoá họ khỏi thực nghiệm |
| TC-LE-I12 | `test_review_lock_and_decision_leave_a_timed_session` | AC-79.1 | Khoá rồi quyết định: một phiên đã kết thúc, đúng bài, đúng người |
| TC-LE-I13 | `test_teacher_kpi_reports_minutes_only_from_enough_sessions` | AC-79.5 | Chưa có phiên: không có trung vị; 5 phiên và 1 phiên bỏ dở: trung vị 4 phút; sinh viên 403 |
| TC-LE-I14 | `test_progress_says_no_error_measured_until_an_admin_sets_one` | AC-80.4 | Chưa có SEM: chưa kết luận; SEM nhập tay kèm nguồn: tiến bộ; thiếu nguồn 422; sinh viên 403 |
| TC-LE-I15 | `test_measured_error_needs_enough_retest_pairs` | AC-80.5 | Dưới 10 cặp: 422; đủ 10 cặp: SEM nguồn `retest` |
| TC-LE-I16 | `test_feedback_stays_held_back_through_the_survey_and_in_the_export` | AC-77.9 | Giai đoạn khảo sát vẫn giữ phản hồi, cả trong bản xuất cá nhân; đóng thì trả lại (thêm sau review 13/10/2026) |

### Tầng 3 — E2E (`tests/e2e/test_learning_evidence_e2e.py`)

| Mã | Test | Truy vết | Kiểm điều gì |
| --- | --- | --- | --- |
| TC-LE-E01 | `test_progress_page_names_the_pronunciation_patterns` | AC-75.7 | Trang Tiến độ: âm cuối 3/12 · 25 %, ví dụ và cách luyện; đuôi -ed chưa đủ dữ liệu |
| TC-LE-E02 | `test_a_score_only_learner_sees_why_and_can_leave` | AC-77.8 | Quản trị viên bắt đầu trên trang; người nhóm "Chỉ điểm" thấy lời giải thích, rời thực nghiệm, nhận lại nhận xét |
| TC-LE-E03 | `test_class_page_shows_teacher_time_and_class_pronunciation` | AC-76.2 | Giảng viên thấy phát âm của cả lớp, không thấy thời gian giảng viên; quản trị viên thấy thẻ thời gian (chưa đủ 5 lần) (D068) |
| TC-LE-E04 | `test_admin_sets_the_measurement_error_with_its_source` | AC-80.6 | Tab Cấu hình: chưa đặt, nút bài thử lại tắt; nhập tay kèm nguồn rồi thấy nguồn |

## 7. Kết quả chạy

| Lệnh | Kết quả |
| --- | --- |
| `pytest tests/test_learning_evidence_unit.py tests/test_learning_evidence.py` | 44 test qua |
| `pytest -m e2e tests/e2e/test_learning_evidence_e2e.py` | 4 test qua |
| `pytest -m "not e2e and not slow"` (hồi quy, có đo độ phủ, sau bản sửa D030-B10) | 1229 test: 1219 qua, 10 bỏ qua theo thiết kế; độ phủ toàn bộ 93% |
| `pytest -m e2e tests/e2e` (hồi quy) | 77 test qua |

## 8. Lỗi tìm thấy trong lúc làm

| Mã | Lỗi | Sửa | Giữ lại bằng |
| --- | --- | --- | --- |
| D039-B1 | `ruff --fix` đổi `Literal["retest","manual"]` thành tên trần, làm hỏng chú thích kiểu của yêu cầu đặt SEM | Dùng `Field(pattern=...)` | TC-LE-I14, TC-LE-I15 |
| D039-B2 | Bí danh `esc(` thay cho `escapeHtml` ở ba tệp giao diện; test hợp đồng giao diện đòi tên đầy đủ ở mọi chỗ chèn HTML | Gọi thẳng `window.escapeHtml` | `tests/test_frontend_contracts.py` |
| D040-B1 | Bản đầu chỉ cho rời thực nghiệm từ trang Tiến độ; người rút đồng ý nghiên cứu vẫn ở nhóm "Chỉ điểm" | Rút đồng ý, ký lại không cho nghiên cứu và xoá dữ liệu đều rời thực nghiệm | TC-LE-I08, TC-LE-I11 |
