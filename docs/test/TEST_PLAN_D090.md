# Kế hoạch và kết quả kiểm thử D090 — Đoạn đọc viết quanh từ đang luyện dở

| Thuộc tính | Giá trị |
| --- | --- |
| Thay đổi | D090: 3–5 từ đang luyện dở (D089) được đặt vào một đoạn đọc. Mô hình ngôn ngữ viết theo band; học viên trả 0,1 lượt mỗi đoạn mới, đọc lại miễn phí. Khi không dùng được mô hình thì ghép đoạn từ cụm của chính học viên, miễn phí. Mỗi lần đọc là một lượt của từng từ (FR-98). **APPROVED** |
| Phiên bản mã | nhánh `feat/d090-drill-passage` |
| Người lập | Võ Thanh Sang |
| Ngày | 03/11/2026 |

## 1. Mục tiêu

1. **Gửi ít, tốn ít.** Chỉ gửi band và các từ cho mô hình. Mỗi yêu cầu có trần token ra và mức suy nghĩ thấp. Một bộ từ chỉ viết một lần; đọc lại không gọi mô hình.
2. **Thu đúng.** Thu đúng giá đoạn đọc, chỉ khi đoạn có đủ mọi từ. Mô hình lỗi hay viết thiếu từ thì trả lại lượt. Phần đoạn đọc trong giới hạn ngày không lấn phần của bản nâng cấp.
3. **Chấm công bằng.** Một từ chỉ rõ khi máy nghe rõ nó ở mọi chỗ nó xuất hiện. Mỗi lần đọc là một lượt của từng từ, theo đúng luật hai lượt rõ liên tiếp của D089.
4. **Riêng tư.** Bản ghi của các lần đọc không lưu. Bản xuất dữ liệu cá nhân có các đoạn đọc. Xoá dữ liệu người học thì xoá luôn các đoạn đọc.

## 2. Các tầng

| Tầng | Kiểm cái gì | Môi trường | Lệnh |
| --- | --- | --- | --- |
| Unit | Yêu cầu gửi mô hình, kiểm đoạn, vị trí từ, ghép từ cụm, chấm một lần đọc, giá, tham số gọi nhà cung cấp, lưu trữ | Hàm thuần; MongoDB trong bộ nhớ; HTTP của nhà cung cấp thay bằng câu trả lời cố định | `pytest tests/test_d090_passage_unit.py` |
| Integration | Điều kiện đủ từ, viết một lần rồi đọc lại, tính lượt, một lần đọc, không có mô hình, giới hạn ngày, xuất và xoá dữ liệu | Ứng dụng một tiến trình, MongoDB trong bộ nhớ; mô hình và dịch vụ speech thay bằng bản giả | `pytest tests/test_d090_passage.py` |

## 3. Truy vết tiêu chí chấp nhận

| Tiêu chí chấp nhận | Test case |
| --- | --- |
| AC-98.1 | TC-PS-I01 |
| AC-98.2 | TC-PS-I02, TC-PS-U01, TC-PS-U02 |
| AC-98.3 | TC-PS-I03, TC-PS-U07 |
| AC-98.4 | TC-PS-I04, TC-PS-U05 |
| AC-98.5 | TC-PS-I05, TC-PS-U04 |
| AC-98.6 | TC-PS-I06 |
| AC-98.7 | TC-PS-I07, TC-PS-U09 |

## 4. Test case

### 4.1. Unit — `tests/test_d090_passage_unit.py`

| Mã | Test | Truy vết | Kiểm |
| --- | --- | --- | --- |
| TC-PS-U01 | `test_the_request_names_the_band_the_words_and_the_length` | AC-98.2 | Yêu cầu chỉ có band, các từ và độ dài theo band; band lạ hoặc thiếu thì dùng B1 |
| TC-PS-U02 | `test_a_passage_is_kept_only_with_every_word_as_asked` | AC-98.2 | Đoạn phải có đúng dạng của mọi từ ("work" không thay được "worked") và không quá dài; câu trả lời không đọc được thì bị từ chối |
| TC-PS-U03 | `test_the_places_of_each_word_follow_the_written_words` | FR-98 | Vị trí của từ theo cách tách từ của bước đọc to, kể cả khi dính dấu câu hay xuất hiện hai lần |
| TC-PS-U04 | `test_the_learners_own_phrases_make_a_passage_without_the_model` | AC-98.5 | Mỗi cụm thành một câu, viết hoa đầu câu; đoạn chứa mọi từ |
| TC-PS-U05 | `test_a_word_passes_only_where_every_place_was_heard_clearly` | AC-98.4 | Một chỗ nghe chưa rõ là từ chưa rõ, kèm máy nghe thành gì và mẫu lỗi; lần đọc không đo được thì không chấm |
| TC-PS-U06 | `test_the_passage_is_read_aloud_with_its_words_highlighted` | FR-98 | Đoạn là bước đọc to 90 giây, các từ là từ gợi ý |
| TC-PS-U07 | `test_a_passage_has_its_own_price_kept_in_the_versions` | AC-98.3 | 0,1 lượt = 100 phần nghìn = 200 IDPoint; giá âm bị từ chối; bảng giá lưu từ trước D090 vẫn đọc được, giá đoạn đọc lấy mặc định |
| TC-PS-U08 | `test_the_provider_is_asked_to_write_little` | FR-98 | Gọi đoạn đọc có `max_tokens`; Gemini thêm `reasoning_effort: low`; Groq không nhận tham số đó; bản nâng cấp và bản soạn bài không đổi |
| TC-PS-U09 | `test_passages_are_found_again_for_the_same_words_and_erased` | AC-98.7 | Tìm lại đoạn theo đúng bộ từ, không phụ thuộc thứ tự; đoạn ghép không tính vào giới hạn của mô hình; lưu lần đọc; xoá theo tài khoản |

### 4.2. Integration — `tests/test_d090_passage.py`

| Mã | Test | Truy vết | Kiểm |
| --- | --- | --- | --- |
| TC-PS-I01 | `test_a_passage_needs_three_open_words_and_is_for_learners` | AC-98.1 | Hai từ đang dở thì chưa đủ (409), mô hình không bị hỏi; giảng viên nhận 403; trang `/passage` mở cho học viên |
| TC-PS-I02 | `test_the_model_writes_a_passage_once_and_it_is_read_again_for_free` | AC-98.2 | Chọn từ mới nhất trước, mỗi chính tả một lần; mô hình nhận band B1, các từ, độ dài, `max_tokens`; xin lại thì nhận đúng đoạn cũ, mô hình chỉ bị hỏi một lần; dashboard AI đếm 1 đoạn đọc và số token |
| TC-PS-I03 | `test_metered_a_passage_costs_its_own_price_and_a_failure_nothing` | AC-98.3 | Giá hiện là 0,1 lượt / 200 IDPoint; đoạn viết xong thu 100 phần nghìn lượt kèm token; đoạn thiếu từ và mô hình lỗi đều trả lại lượt; lịch sử lượt có "Đoạn đọc (AI)" |
| TC-PS-I04 | `test_a_reading_is_one_take_of_each_word` | AC-98.4 | Lần đọc đầu: hai từ rõ (chuỗi 1), "three" máy nghe thành "tree" và vào ôn; lần đọc hai: hai từ đã xong, "three" chuỗi 1; đoạn ghi từ chưa rõ của mỗi lần đọc; mã đoạn lạ thì 404 |
| TC-PS-I05 | `test_without_the_model_the_learners_phrases_make_a_free_passage` | AC-98.5 | Mô hình tắt: không có giá, xin mô hình nhận 503; ghép từ cụm thành đoạn và không có bút toán nào |
| TC-PS-I06 | `test_the_caps_keep_the_upgrades_share_and_the_learners_own` | AC-98.6 | Hết phần đoạn đọc của cả hệ thống thì 429 "số đoạn đọc trong ngày"; hết phần của một học viên thì 429 "tối đa 1 đoạn", số còn lại là 0; hết giới hạn AI chung thì 429 kèm gợi ý ghép đoạn từ cụm, và ghép vẫn được |
| TC-PS-I07 | `test_erasing_a_participant_forgets_their_passages` | AC-98.7 | Bản xuất dữ liệu cá nhân có đoạn đọc; xoá dữ liệu người học xoá `drill_passage` của họ |

## 5. Kết quả

| Lần chạy | Lệnh | Kết quả |
| --- | --- | --- |
| Unit | `pytest tests/test_d090_passage_unit.py` | 9 PASS |
| Integration | `pytest tests/test_d090_passage.py` | 7 PASS |

**Giới hạn (`NOT_RUN`):**
- **Chưa gọi Gemini thật.** Phải gửi dữ liệu ra ngoài nên chờ chủ dự án cho phép. Chưa biết số token thật, và chưa biết Gemini 3.5 Flash-Lite có nhận `reasoning_effort: low` qua cổng tương thích OpenAI hay không. Nếu không nhận, yêu cầu sẽ lỗi, lượt được trả lại, và dashboard ghi lỗi.
- **Chưa có e2e trình duyệt cho trang `/passage`**, vì phần ghi âm cần micro.
