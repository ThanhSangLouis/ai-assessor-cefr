# Kế hoạch và kết quả kiểm thử D089 — Luyện lại từ máy nghe chưa rõ

| Thuộc tính | Giá trị |
| --- | --- |
| Thay đổi | D089: từ tô cam của một bài nói thành bài luyện bốn bước (nghe lại mình, nghe mẫu, mẹo, nói lại để máy chấm); hai lượt rõ liền là xong, chưa rõ thì vào ôn ngắt quãng; tỉ lệ từ máy nghe chưa rõ trên trang Tiến độ (FR-97). **APPROVED** |
| Phiên bản mã | nhánh `feat/d089-word-drill` |
| Người lập | Võ Thanh Sang |
| Ngày | 02/11/2026 |

## 1. Mục tiêu

1. **Đúng từ, đúng chỗ.** Chỉ từ máy nghe chưa rõ, từ chữ cái thường, mỗi chính tả một lần, tối đa 8; mỗi từ có đoạn ghi âm và cụm 3–4 từ không vắt qua quãng ngừng dài.
2. **Chấm công bằng.** Lượt nói lại đo như bước đọc to; chỉ tính khi đo được; hai lượt rõ liền mới xong, xong rồi thì giữ xong; lượt chưa rõ vào ôn ngắt quãng.
3. **Riêng tư.** Chỉ chủ bài luyện được; bản ghi của lượt nói lại không lưu; xoá dữ liệu người học thì xoá các từ luyện lại.
4. **Nói thật.** Giao diện nói từ màu cam là máy nghe chưa rõ, không phải phát âm sai; số báo cáo là tỉ lệ từ chưa rõ qua các bài, không phải band.

## 2. Các tầng

| Tầng | Kiểm cái gì | Môi trường | Lệnh |
| --- | --- | --- | --- |
| Unit | Chọn từ, dựng cụm, mẹo, bước đọc to, chấm một lượt, chuỗi lượt rõ, tỉ lệ từ chưa rõ, lưu trữ | Hàm thuần; MongoDB trong bộ nhớ | `pytest tests/test_d089_drill_unit.py` |
| Integration | Quyền, danh sách từ, lượt nói lại, ôn ngắt quãng, trang Tiến độ, xoá dữ liệu | Ứng dụng một tiến trình, MongoDB trong bộ nhớ; dịch vụ speech thật (bộ nhận dạng giả) hoặc thay bằng kết quả cố định | `pytest tests/test_d089_drill.py` |

## 3. Truy vết tiêu chí chấp nhận

| Tiêu chí chấp nhận | Test case |
| --- | --- |
| AC-97.1 | TC-DR-I01 |
| AC-97.2 | TC-DR-I02, TC-DR-U01 |
| AC-97.3 | TC-DR-I03, TC-DR-U10 |
| AC-97.4 | TC-DR-I04, TC-DR-U11 |
| AC-97.5 | TC-DR-I06, TC-DR-U14 |
| AC-97.6 | TC-DR-I07 |

## 4. Test case

### 4.1. Unit — `tests/test_d089_drill_unit.py`

| Mã | Test | Truy vết | Kiểm |
| --- | --- | --- | --- |
| TC-DR-U01 | `test_unsure_plain_words_are_offered_least_clear_first_in_speaking_order` | AC-97.2 | Bỏ từ ngập ngừng và số; một chính tả một lần, giữ chỗ kém rõ nhất; xếp theo thứ tự nói |
| TC-DR-U02 | `test_at_most_max_words_and_the_least_clear_win` | FR-97 | Tối đa 8 từ, là 8 từ kém rõ nhất |
| TC-DR-U03 | `test_a_sure_or_unscored_word_is_never_offered` | FR-97 | Từ rõ hay không có xác suất thì không vào danh sách |
| TC-DR-U04 | `test_the_phrase_is_one_before_two_after_and_the_word_is_located_in_it` | FR-97 | Cụm một từ trước, hai từ sau, bỏ dấu câu, bỏ qua từ ngập ngừng; biết vị trí của từ trong cụm; đoạn nghe lại thêm 0,2 giây hai đầu |
| TC-DR-U05 | `test_the_phrase_stops_at_a_long_pause` | FR-97 | Cụm không vắt qua quãng ngừng dài hơn 1 giây |
| TC-DR-U06 | `test_the_first_word_has_no_word_before_it` | FR-97 | Từ đầu bài: cụm bắt đầu từ chính nó |
| TC-DR-U07 | `test_the_tip_is_the_most_specific_pattern_the_spelling_allows` | FR-97 | -ed, -s, th, cụm phụ âm, âm cuối; từ không rơi vào mẫu nào thì không có mẹo |
| TC-DR-U08 | `test_the_take_is_measured_as_a_read_aloud_step_with_the_word_highlighted` | FR-97 | Lượt nói lại là bước đọc to, văn bản là cụm, từ gợi ý là từ đó |
| TC-DR-U09 | `test_heard_clearly_passes_unsure_or_missed_does_not` | FR-97 | Nghe rõ thì đạt; nghe không chắc hay không nghe ra thì chưa, kèm máy nghe thành gì và mẫu lỗi |
| TC-DR-U10 | `test_two_clear_takes_in_a_row_and_a_miss_starts_again` | AC-97.3 | Hai lượt rõ liền mới xong; một lượt chưa rõ đếm lại từ đầu |
| TC-DR-U11 | `test_a_take_with_nothing_measured_does_not_count` | AC-97.4 | Lượt không đo được thì không đạt và không tính |
| TC-DR-U12 | `test_the_unsure_share_counts_plain_words_with_a_probability` | FR-97 | Tỉ lệ tính trên từ có xác suất, kể cả từ ngắn, bỏ số và từ ngập ngừng; không có xác suất thì không có số |
| TC-DR-U13 | `test_the_clarity_line_reads_lower_as_better` | FR-97 | Đường "Từ máy nghe chưa rõ": thấp hơn là tốt, hướng đi đúng khi giảm |
| TC-DR-U14 | `test_takes_are_kept_on_the_drill_and_a_closed_word_stays_closed` | AC-97.5 | Lượt lưu trên từ, giữ tối đa 20; xong rồi thì giữ xong; đếm số từ đã luyện, đã rõ; xoá theo tài khoản |
| TC-DR-U15 | `test_a_word_sent_to_review_points_back_to_its_drill` | FR-97 | Từ đưa vào ôn không có bài học, trỏ về `drill_id`; một từ chỉ một hàng ôn |

### 4.2. Integration — `tests/test_d089_drill.py`

| Mã | Test | Truy vết | Kiểm |
| --- | --- | --- | --- |
| TC-DR-I01 | `test_only_the_owner_of_a_scored_response_practises_its_words` | AC-97.1 | Bài chưa có điểm: 404; người khác: 404; giảng viên: 403; trang `/drill/{mã}` mở cho chủ bài |
| TC-DR-I02 | `test_the_unclear_words_are_offered_with_their_place_phrase_and_tip` | AC-97.2 | Hai từ cam, bỏ "um"; cụm, đoạn ghi âm, mẹo -ed và th; tỉ lệ từ chưa rõ; câu nói rõ máy nghe chưa rõ không phải phát âm sai |
| TC-DR-I03 | `test_two_clear_takes_close_a_word_and_a_miss_sends_it_to_review` | AC-97.3 | Lượt chưa rõ: máy nghe thành "work", mẹo "Đuôi -ed", từ vào ôn; hai lượt rõ sau đó: xong; từ không thuộc bài: 404 |
| TC-DR-I04 | `test_a_take_nothing_could_be_measured_from_does_not_count` | AC-97.4 | Lượt không đo được trả lời nhắc nói lại, không tạo bản ghi |
| TC-DR-I05 | `test_a_real_take_goes_through_the_speech_service` | FR-97 | Lượt nói lại đi qua dịch vụ speech thật (bộ nhận dạng giả), trả đủ trường |
| TC-DR-I06 | `test_progress_shows_the_unclear_share_and_the_open_words` | AC-97.5 | `/api/v1/me/progress` có đường `unsure_share` (22,2%); `/api/v1/learn/drill` có từ đang luyện dở kèm mã bài |
| TC-DR-I07 | `test_erasing_a_participant_forgets_their_drills` | AC-97.6 | Bản xuất dữ liệu cá nhân có các từ đã luyện lại kèm lượt nói; xoá dữ liệu người học xoá luôn `word_drill` của họ |

## 5. Kết quả

| Lần chạy | Lệnh | Kết quả |
| --- | --- | --- |
| Unit | `pytest tests/test_d089_drill_unit.py` | 20 PASS (TC-DR-U07 có 6 trường hợp) |
| Integration | `pytest tests/test_d089_drill.py` | 7 PASS |
| Toàn bộ (không e2e) | `pytest --ignore=tests/e2e` | 1.493 PASS, 29 SKIP |
| Toàn bộ e2e | `AICEFR_TEST_MONGO=mongodb://localhost:27041 pytest -m e2e tests/e2e` (MongoDB 7 trong Docker) | 62 PASS |
| Trình duyệt, bằng tay | Bản chạy một tiến trình, Chromium của Playwright | Báo cáo hiện nút luyện lại; trang luyện liệt kê 4 từ, cụm, mẹo, bộ ghi âm; lượt gửi đi qua dịch vụ speech thật (tiếng beep: "chưa nghe thấy tiếng nói", không tính); điện thoại 390 px không tràn. Sửa sau lần xem: cụm từng lấy cả "um", nay bỏ qua từ ngập ngừng |

Giới hạn (`NOT_RUN`): chưa có test e2e trong trình duyệt cho trang `/drill` (ghi âm cần micro); giao diện được kiểm bằng tay trên bản chạy cục bộ. Chưa đo trên người học thật: tỉ lệ từ máy nghe chưa rõ giảm sau khi luyện là giả thuyết cần dữ liệu thu ở các tuần sau, không phải kết quả.
