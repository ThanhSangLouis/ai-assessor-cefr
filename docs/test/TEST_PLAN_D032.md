# Kế hoạch và kết quả kiểm thử D032 — Thành tựu và nhịp luyện của chính mình

| Thuộc tính | Giá trị |
| --- | --- |
| Tính năng | D032: 17 thành tựu ghi công sức luyện tập; kỷ lục chuỗi, ngày nghỉ được tính, bảy ngày qua cạnh bảy ngày trước đó (FR-65, FR-66, BR-28; mở rộng UC-15, UC-19) |
| Phiên bản mã | nhánh `feat/achievements` |
| Người lập | Võ Thanh Sang |
| Ngày | 07/10/2026 |

## 1. Mục tiêu

1. **Không thưởng con số.** Không thành tựu nào đọc được điểm, band, tỷ lệ đạt hay dữ liệu của người khác (BR-28). Điều này kiểm bằng cấu trúc — `Facts` không có trường như vậy — chứ không chỉ bằng vài ví dụ.
2. **Đếm đúng công sức.** Chỉ lượt máy đo được tiếng nói; ngày theo giờ Việt Nam; mục tiêu ngày của chính người học; thử lại tính một lần mỗi bước; ôn tập đếm riêng.
3. **Đã đạt thì giữ, chỉ chủ nhân thấy.** Xoá lượt hay giáo viên sửa nhận định không lấy lại thành tựu; đánh dấu đã xem chỉ chạm thành tựu của mình; xoá dữ liệu người học xoá theo.
4. **Người học thấy đúng điều đã làm**: một lời chúc mừng sau lượt vừa đạt, thẻ trên trang Luyện tập, danh sách ở trang Tiến độ, kỷ lục và ngày nghỉ trên thẻ Hôm nay.

## 2. Ba tầng kiểm thử

| Tầng | Kiểm cái gì | Công cụ | Môi trường | Chạy ở đâu | Lệnh |
| --- | --- | --- | --- | --- | --- |
| 1. Unit | Kỷ lục, ngày nghỉ được tính, đếm dữ kiện, danh mục, thành tựu gần đạt nhất | pytest | Không ứng dụng, không CSDL | Máy và CI | `pytest tests/test_achievements_unit.py` |
| 2. Integration | API thành tựu, lưu khi đạt, đánh dấu đã xem, không lấy lại, ngày Việt Nam, bài và chặng xong, ôn tập, bài đánh giá, trang Luyện tập, bản xuất và xoá | pytest, FastAPI TestClient | SQLite thật trên tệp tạm; bộ nhận dạng giả, âm tổng hợp; lịch sử ngày cũ ghi thẳng qua kho; đồng hồ của API bài học bị ghim | Máy và CI | `pytest tests/test_achievements.py` |
| 3. E2E | Lời chúc mừng, thẻ "1 mới", danh sách với nhãn "Mới" một lần; kỷ lục, ô ngày nghỉ, dòng bảy ngày; cột bên thôi dính khi cao hơn cửa sổ | Playwright + Chromium | Máy chủ uvicorn của `test_lessons_e2e.py` (bộ dò năng lượng, bộ nhận dạng giả) | **Chỉ trên máy**; CI tự bỏ qua | `pytest -m e2e tests/e2e/test_achievements_e2e.py` |

Phần nhìn — thẻ Thành tựu, ô thành tựu đã đạt, chưa đạt và mới, ô ngày nghỉ — kiểm bằng ảnh chụp từ máy chủ tạm ở 1280×820 và 390×844, sáng và tối; ảnh không lưu vào kho mã.

## 3. Dữ liệu và môi trường

- Tài khoản tạo trong từng test; mật khẩu là chuỗi cố định của bộ test, không phải mật khẩu thật.
- Lịch sử nhiều ngày (chuỗi cũ, ngày nghỉ, lượt lúc 00:30 giờ Việt Nam) ghi thẳng bằng `LessonRepository.add_attempt` với `created_at` chọn trước, đúng cách các test lộ trình bài học dựng lịch sử; đồng hồ của API bài học ghim bằng `freeze`.
- Bài đánh giá "có kết quả" lưu bằng `Repository.save` như test gợi ý bài tiếp theo của D025: bản chép của bộ nhận dạng giả quá ngắn để được chấm.
- Không có giọng nói người thật, không có dữ liệu người học thật.

## 4. Tiêu chí vào và ra

- **Vào:** mã qua `ruff format --check` và `ruff check`.
- **Ra (được merge):** 100% test tầng 1 và 2 qua trên CI; 100% test tầng 3 qua trên máy trước khi merge; mọi tiêu chí chấp nhận AC-65.1..AC-66.4 có ít nhất một test (kiểm bằng `tests/test_product_traceability.py`).

## 5. Truy vết tiêu chí chấp nhận

Tiêu chí chấp nhận AC-65.1..AC-66.4 nằm ở `docs/srs/SRS.md`, mục 3.9f.

| Tiêu chí chấp nhận | Test case |
| --- | --- |
| AC-65.1 | TC-TT-I01 |
| AC-65.2 | TC-TT-I02 |
| AC-65.3 | TC-TT-I03 |
| AC-65.4 | TC-TT-I04 |
| AC-65.5 | TC-TT-I05, TC-TT-U04, TC-TT-U06 |
| AC-65.6 | TC-TT-I06 |
| AC-65.7 | TC-TT-I07, TC-TT-U07 |
| AC-65.8 | TC-TT-I08, TC-TT-U10 |
| AC-65.9 | TC-TT-I10 |
| AC-65.10 | TC-TT-E01 |
| AC-66.1 | TC-TT-I09, TC-TT-U12 |
| AC-66.2 | TC-TT-E02 |
| AC-66.3 | TC-TT-U01 |
| AC-66.4 | TC-TT-U02 |
| BR-28 | TC-TT-U08, TC-TT-I02, TC-TT-I04 |

## 6. Danh mục test case

### Tầng 1 — Unit (`tests/test_achievements_unit.py`)

| Mã | Test | Truy vết | Kiểm điều gì |
| --- | --- | --- | --- |
| TC-TT-U01 | `test_the_longest_streak_is_the_best_the_learner_was_ever_shown` | AC-66.3 | Kỷ lục là chuỗi bảy ngày chứ không phải chuỗi có ngày nghỉ; bằng đúng con số lớn nhất từng hiện trên thẻ Hôm nay; không ngày nào thì 0 |
| TC-TT-U02 | `test_the_rest_days_of_the_current_streak_are_named` | AC-66.4 | Nêu đúng ngày nghỉ chuỗi đã dùng; hai ngày nghỉ cách nhau dưới bảy ngày thì chỉ ngày chuỗi thật sự dùng được nêu |
| TC-TT-U03 | `test_only_measured_speech_counts` | FR-65 | Lượt không đo được tiếng nói không thành lượt, giây, ngày luyện hay ngày đủ mục tiêu |
| TC-TT-U04 | `test_goal_days_use_the_learners_own_goal` | FR-65 | Cùng các ngày, mục tiêu 1, 2 và 10 phút cho 3, 1 và 0 ngày đủ mục tiêu |
| TC-TT-U05 | `test_a_step_counts_as_retried_once_a_pass_follows_a_miss` | FR-65 | Qua sau một lần chưa qua tính một lần mỗi bước; qua trước khi trượt, im lặng, và lượt ôn không tính |
| TC-TT-U06 | `test_a_comeback_needs_three_days_without_practice` | FR-65 | Ba ngày không luyện rồi luyện lại là một lần quay lại; hai ngày thì chưa |
| TC-TT-U07 | `test_free_steps_and_reviews_are_counted_apart` | FR-65 | Lượt nói tự do (kể cả ôn một bài nói tự do) và lượt ôn đếm riêng; lượt im lặng không tính |
| TC-TT-U08 | `test_no_achievement_reads_a_score_a_band_or_anyone_else` | FR-65 | BR-28 bằng cấu trúc: `Facts` có đúng mười một trường công sức, không trường nào mang điểm, band, hạng hay người khác; mã nguồn không nhắc `overall_0_6` hay `Band`; mọi thành tựu trên dữ kiện rỗng là 0 |
| TC-TT-U09 | `test_the_catalogue_is_well_formed` | FR-65 | 17 mã không trùng, đủ năm nhóm, mỗi thành tựu có tên, mô tả, đơn vị, mức cần ≥ 1 và một biểu tượng có trong `icons.svg` |
| TC-TT-U10 | `test_the_trend_achievement_matches_the_progress_page` | FR-65 | Mức cần của "Đủ để thấy xu hướng" bằng `MIN_RESULTS_FOR_TREND` của trang Tiến độ, đọc từ mã nguồn |
| TC-TT-U11 | `test_reached_achievements_follow_the_facts` | FR-65 | Một bộ dữ kiện cho đúng tám thành tựu; phút tính theo phút; giá trị không vượt mức cần |
| TC-TT-U12 | `test_the_nearest_achievement_is_the_closest_one_started` | FR-65 | Thành tựu gần đạt nhất là cái có tỷ lệ cao nhất đã bắt đầu; chưa bắt đầu gì thì không có; cái đã đạt (dù chưa lưu) không bao giờ là "sắp đạt" |

### Tầng 2 — Integration (`tests/test_achievements.py`)

| Mã | Test | Truy vết | Kiểm điều gì |
| --- | --- | --- | --- |
| TC-TT-I01 | `test_a_first_recording_is_congratulated_once` | AC-65.1 | Lượt đầu trả đúng "Lượt nói đầu tiên", lượt hai không trả gì; thành tựu lưu là chưa xem |
| TC-TT-I02 | `test_the_list_shows_how_far_each_one_is_without_a_score` | AC-65.2 | 17 mục, năm nhóm theo thứ tự, mức đã làm trên mức cần, phút theo phút; phản hồi không chứa điểm, band hay xếp hạng; chưa đăng nhập nhận 401 |
| TC-TT-I03 | `test_new_achievements_are_marked_seen_by_their_owner_only` | AC-65.3 | Đánh dấu đã xem chỉ chạm của mình; mã không có thật không tính; thân rỗng là mọi cái mới; quá 17 mã nhận 422 |
| TC-TT-I04 | `test_an_achievement_is_never_taken_back` | AC-65.4 | "Thử lại và qua" còn nguyên sau khi giáo viên sửa lượt qua thành chưa qua và người học xoá lượt trượt |
| TC-TT-I05 | `test_habit_achievements_count_vietnam_days_and_the_learners_goal` | AC-65.5 | Lượt lúc 00:30 giờ Việt Nam thuộc ngày Việt Nam, nên chuỗi dài 5 chứ không 4; đổi mục tiêu ngày đổi số ngày đủ mục tiêu; quay lại sau ba ngày được tính |
| TC-TT-I06 | `test_completing_a_lesson_and_a_unit_reach_the_path_achievements` | AC-65.6 | "Bài học đầu tiên" đạt sau bài thứ nhất, "Xong một chặng" chỉ khi xong cả chặng; bước nói tự do tính "Nói tự do" |
| TC-TT-I07 | `test_review_attempts_count_towards_the_review_achievement` | AC-65.7 | Lượt ôn trả danh sách thành tựu và tăng "Mười lượt ôn" |
| TC-TT-I08 | `test_assessments_with_a_result_count_towards_the_assessment_achievements` | AC-65.8 | Bài đánh giá có kết quả thứ nhất và thứ năm mở hai thành tựu; trang Tiến độ bắt đầu nói về xu hướng cùng lúc |
| TC-TT-I09 | `test_the_practice_page_shows_the_record_rest_days_and_last_week` | AC-66.1 | `GET /api/v1/learn`: chuỗi, kỷ lục, ngày nghỉ, giây của hai tuần; thẻ Thành tựu: số đạt, số mới, ba cái gần nhất, cái gần đạt nhất |
| TC-TT-I10 | `test_the_personal_export_and_erasure_cover_achievements` | AC-65.9 | Bản xuất cá nhân có thành tựu và mục đích của trường; xoá dữ liệu người học xoá thành tựu của họ, không chạm người khác |

### Tầng 3 — E2E (`tests/e2e/test_achievements_e2e.py`)

| Mã | Test | Truy vết | Kiểm điều gì |
| --- | --- | --- | --- |
| TC-TT-E01 | `test_a_first_recording_is_congratulated_then_listed_as_new_once` | AC-65.10 | Thông báo "Thành tựu mới: Lượt nói đầu tiên"; thẻ "1 mới"; "Xem tất cả" mở đúng mục; ô mới có nhãn "Mới", ô chưa đạt có thanh tiến độ; tải lại thì hết "Mới"; không có chữ "band" |
| TC-TT-E02 | `test_the_week_shows_the_record_and_the_rest_day` | AC-66.2 | "3 ngày liên tiếp", "Kỷ lục của bạn: 5 ngày", một ô ngày nghỉ có chú thích, "7 ngày qua: 2 phút", thẻ "Sắp đạt: Tròn một tuần"; cột bên cao hơn cửa sổ thì thôi dính và thẻ cuối cuộn tới được |

## 7. Kết quả chạy

| Lệnh | Kết quả |
| --- | --- |
| `pytest tests/test_achievements_unit.py` | 12 test qua |
| `pytest tests/test_achievements.py` | 10 test qua |
| `pytest -m e2e tests/e2e/test_achievements_e2e.py` | 2 test qua |
| `pytest -m "not e2e and not slow"` (hồi quy, có đo độ phủ) | 1065 test qua; độ phủ toàn bộ 92%, `practice/achievements.py` và `practice/streak.py` 100% |
| `pytest -m e2e tests/e2e` (hồi quy) | 57 test qua (55 sẵn có, 2 mới) |

## 8. Lỗi tìm thấy trong lúc làm

| Mã | Lỗi | Sửa | Giữ lại bằng |
| --- | --- | --- | --- |
| D032-B1 | Ảnh chụp ở 1280×820: bốn thẻ của cột bên cao hơn cửa sổ, cột dính lên đầu trang nên thẻ Thành tựu (và nửa dưới thẻ Ôn tập, lỗi có từ trước) bị giấu tới cuối lộ trình | `fitSide`: cột chỉ dính khi vừa cửa sổ, cao hơn thì cuộn cùng trang (lớp `.is-tall`), tính lại khi đổi kích thước cửa sổ | TC-TT-E02, ảnh chụp |
| D032-B2 | Bản nháp của `nearest` có thể chọn một thành tựu đã đạt mà chưa kịp lưu làm "sắp đạt" (100%) | Bỏ mọi thành tựu đã đạt khỏi danh sách "sắp đạt" | TC-TT-U12 |
| D032-B3 | Thẻ Thành tựu trên màn hình hai cột (≤ 900 px) đứng một mình ở cột trái, để trống cột phải | Thẻ trải hết hàng khi cột bên có hai cột | Ảnh chụp 390×844 |

Một rủi ro được chặn từ lúc thiết kế: lỗi khi xét thành tựu không được làm hỏng lượt luyện đã lưu — người học thấy lỗi sẽ ghi lại lượt đó. `_just_reached` chạy sau khi lượt đã lưu, ghi log và trả danh sách rỗng khi lỗi.
