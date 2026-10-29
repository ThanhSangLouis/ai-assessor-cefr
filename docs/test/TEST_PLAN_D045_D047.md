# Kế hoạch và kết quả kiểm thử D045–D047 — Lược đồ, lộ trình ghép, triển khai

| Thuộc tính | Giá trị |
| --- | --- |
| Thay đổi | D045 lược đồ có phiên bản (FR-83); D046 model lộ trình (FR-81, FR-82, BR-40); D047 triển khai máy chủ (FR-84). Cả ba là **PROPOSED** |
| Phiên bản mã | nhánh `feat/d045-d047` |
| Người lập | Võ Thanh Sang |
| Ngày | 14/10/2026 |

## 1. Mục tiêu

1. **Lược đồ không đổi lén.** Kho mới đúng từng câu với `docs/db/schema_core.sql`; kho của bản trước nâng lên được; nhiều tiến trình cùng khởi động không làm hỏng.
2. **Model chỉ chọn và xếp bài có thật.** Không bài nào ngoài bài đã xuất bản; sinh viên không bao giờ nhận bài của lộ trình nháp; mỗi bài có lý do; cùng đầu vào cho cùng kết quả.
3. **Thứ tự học được là thật.** Model học thứ tự từ các lộ trình hiện có khi đủ dữ liệu, và nói rõ khi phải dùng quy tắc cố định.
4. **Quyền và dữ liệu cá nhân.** Chỉ giảng viên ghép và lưu; chỉ người tạo lưu đề xuất của mình; lộ trình riêng có trong bản xuất và bị xoá cùng dữ liệu.
5. **Triển khai an toàn.** Chỉ Caddy mở cổng; cookie Secure; không chép `.env`.

## 2. Các tầng

| Tầng | Kiểm cái gì | Môi trường | Lệnh |
| --- | --- | --- | --- |
| Unit | Đọc mục tiêu, chấm phù hợp, chọn, học thứ tự | Hàm thuần | `pytest tests/test_path_composer_unit.py` |
| Integration | API lộ trình riêng và ghép lộ trình, quyền, xuất và xoá | SQLite | `pytest tests/test_learning_plans.py` |
| E2E | Hai trang trong trình duyệt thật | Chromium | `pytest -m e2e tests/e2e/test_learning_plans_e2e.py` |
| Lược đồ | Bản chụp, nâng cấp, đồng thời, CLI; thêm PostgreSQL | SQLite, PostgreSQL 16 | `pytest tests/test_schema.py`, thêm `AICEFR_TEST_PG=...` |
| Triển khai | Cấu hình compose production, Caddyfile, kịch bản | Đọc tệp | `pytest tests/test_deploy_config.py` |
| Hệ thống | Bộ production chạy thật sau Caddy với `AICEFR_DOMAIN=localhost` | Docker Compose | `python tools/compose_smoke.py --base-url https://localhost --insecure` |

## 3. Truy vết tiêu chí chấp nhận

| Tiêu chí chấp nhận | Test case |
| --- | --- |
| AC-81.1 | TC-LP-U01 |
| AC-81.2 | TC-LP-U09 |
| AC-81.3 | TC-LP-U10 |
| AC-81.4 | TC-LP-I01 |
| AC-81.5 | TC-LP-I02 |
| AC-81.6 | TC-LP-I04 |
| AC-81.7 | TC-LP-I07 |
| AC-81.8 | TC-LP-E01 |
| AC-81.9 | TC-LP-I03 |
| AC-82.1 | TC-LP-U04 |
| AC-82.2 | TC-LP-U05 |
| AC-82.3 | TC-LP-U12 |
| AC-82.4 | TC-LP-U13 |
| AC-82.5 | TC-LP-I05 |
| AC-82.6 | TC-LP-I06 |
| AC-82.7 | TC-LP-E02 |
| AC-82.8 | TC-LP-U11 |
| AC-83.1 | TC-DB-I02 |
| AC-83.2 | TC-DB-I04 |
| AC-83.3 | TC-DB-I05 |
| AC-83.4 | TC-DB-I06 |
| AC-83.5 | TC-DB-I07 |
| AC-84.1 | TC-DP-U01 |
| AC-84.2 | TC-DP-U03 |
| AC-84.3 | TC-DP-U04 |
| AC-84.4 | TC-DP-U10 |

## 4. Danh mục test case

### Tầng 1 — Unit (`tests/test_path_composer_unit.py`)

| Mã | Test | Truy vết | Kiểm điều gì |
| --- | --- | --- | --- |
| TC-LP-U01 | `test_a_wish_in_vietnamese_names_topics_criteria_sounds_and_bands` | AC-81.1 | Đọc chủ đề, tiêu chí, âm và band từ câu tiếng Việt |
| TC-LP-U02 | `test_marks_do_not_matter_and_short_words_need_a_word_boundary` | FR-81 | Có dấu hay không như nhau; cụm từ khớp nguyên từ ("ẩm thực" không phải âm th) |
| TC-LP-U03 | `test_the_resolved_goal_orders_bands_and_bounds_the_length` | FR-82 | Band đảo chiều được sắp lại; số bài trong 3–30 |
| TC-LP-U04 | `test_the_band_asked_for_comes_first_and_others_only_fill_in` | AC-82.1 | Band đã chọn trước, band liền kề chỉ bù và có cảnh báo, cách hai band không bao giờ |
| TC-LP-U05 | `test_topic_and_criterion_rank_the_matching_lessons_first_with_their_reasons` | AC-82.2 | Bài khớp chủ đề và tiêu chí xếp đầu, kèm hai lý do |
| TC-LP-U06 | `test_english_words_of_a_wish_match_the_lesson_text` | FR-82 | Từ tiếng Anh trong mục tiêu khớp đoạn văn mẫu và được nêu trong lý do |
| TC-LP-U07 | `test_pronunciation_patterns_favour_lessons_with_more_chances_to_practise_them` | FR-81 | Bài có nhiều từ đuôi -ed hơn được ưu tiên khi cần luyện đuôi -ed |
| TC-LP-U08 | `test_a_lesson_copied_into_two_paths_is_picked_once` | FR-82 | Bài trùng ở hai lộ trình chỉ chọn một lần |
| TC-LP-U09 | `test_a_learner_gets_new_lessons_first_and_finished_ones_only_to_fill_up` | AC-81.2 | Bài chưa xong trước; bài đã xong chỉ để bù cho đủ |
| TC-LP-U10 | `test_the_learners_weakest_criterion_is_named_as_the_reason` | AC-81.3 | Lý do nêu tiêu chí yếu nhất của bài đánh giá gần nhất |
| TC-LP-U11 | `test_too_few_lessons_is_said_not_hidden` | AC-82.8 | Thiếu bài và thiếu chủ đề được cảnh báo |
| TC-LP-U12 | `test_the_order_teachers_use_is_learned_from_their_paths` | AC-82.3 | Học thứ tự từ 20 cặp, khớp 100 % |
| TC-LP-U13 | `test_with_few_pairs_the_fixed_order_is_used_and_said` | AC-82.4 | Dưới 12 cặp: quy tắc cố định và cảnh báo |
| TC-LP-U14 | `test_the_plan_follows_the_learned_order_and_rises_through_the_bands` | FR-82 | Lộ trình theo thứ tự đã học và đi lên qua các band |
| TC-LP-U15 | `test_difficulty_comes_from_attempts_once_there_are_enough` | FR-82 | Độ khó lấy từ lượt luyện khi có ít nhất 10 lượt |
| TC-LP-U16 | `test_the_same_input_gives_the_same_plan` | FR-82 | Cùng đầu vào cho cùng lộ trình (tái lập) |

### Tầng 2 — Integration (`tests/test_learning_plans.py`)

| Mã | Test | Truy vết | Kiểm điều gì |
| --- | --- | --- | --- |
| TC-LP-I01 | `test_a_learner_gets_a_path_of_published_lessons_with_reasons` | AC-81.4 | 5 bài đã xuất bản, có lý do, mở được |
| TC-LP-I02 | `test_asking_again_replaces_the_plan_and_closing_it_sets_it_aside` | AC-81.5 | Ghép lại thay lộ trình cũ; bỏ thì không còn lộ trình đang dùng |
| TC-LP-I03 | `test_the_latest_assessment_steers_the_learners_path` | AC-81.9 | Band và tiêu chí yếu nhất của bài đánh giá gần nhất dẫn lộ trình |
| TC-LP-I04 | `test_a_draft_path_never_reaches_a_learners_plan` | AC-81.6 | Bài của lộ trình nháp không vào lộ trình sinh viên, có trong đề xuất giảng viên |
| TC-LP-I05 | `test_a_teacher_saves_the_kept_lessons_as_a_draft_path_of_copies` | AC-82.5 | Lưu 4/6 bài thành lộ trình nháp gồm bản sao; lần hai 409; nhật ký |
| TC-LP-I06 | `test_only_staff_compose_and_only_the_author_saves` | AC-82.6 | Sinh viên 403; giảng viên khác 403; giữ bài lạ 422 |
| TC-LP-I07 | `test_plans_are_in_the_export_and_go_with_erasure` | AC-81.7 | Có trong bản xuất cá nhân; xoá dữ liệu là xoá lộ trình |

### Tầng 3 — E2E (`tests/e2e/test_learning_plans_e2e.py`)

| Mã | Test | Truy vết | Kiểm điều gì |
| --- | --- | --- | --- |
| TC-LP-E01 | `test_a_learner_composes_a_path_and_sets_it_aside` | AC-81.8 | Trang Luyện tập: ghép, tải lại vẫn còn, bỏ |
| TC-LP-E02 | `test_a_teacher_keeps_part_of_a_proposal_as_a_draft_path` | AC-82.7 | Trang Soạn bài: xem đề xuất, bỏ một bài, lưu nháp |

### Lược đồ — Integration (`tests/test_schema.py`)

| Mã | Test | Truy vết | Kiểm điều gì |
| --- | --- | --- | --- |
| TC-DB-I01 | `test_versions_are_numbered_one_by_one` | FR-83 | Phiên bản đánh số liên tục 1..N |
| TC-DB-I02 | `test_a_fresh_store_matches_the_committed_snapshot` | AC-83.1 | Kho mới đúng từng collection và chỉ mục với `schema_core.json` (D048) |
| TC-DB-I03 | `test_migrate_is_idempotent_and_records_every_version` | FR-83 | Chạy hai lần: lần sau không làm gì; mọi phiên bản được ghi |
| TC-DB-I04 | `test_a_store_built_by_d044_reaches_the_same_structure` | AC-83.2 | Kho của D044 nâng lên giống hệt kho mới |
| TC-DB-I05 | `test_processes_starting_together_record_each_version_once` | AC-83.3 | Bốn tiến trình cùng lúc: không lỗi, mỗi phiên bản ghi một lần |
| TC-DB-I06 | `test_status_says_what_is_pending` | AC-83.4 | `db_cli status` nói phiên bản còn chờ |
| TC-DB-I07 | `test_every_collection_is_in_the_data_dictionary` | AC-83.5 | Mọi collection có trong từ điển dữ liệu |
| TC-DB-I08 | `test_every_identifier_a_table_had_as_key_is_unique` | FR-83 | Khoá chính cũ vẫn là chỉ mục duy nhất trên MongoDB (D048) |

### Triển khai — Unit (`tests/test_deploy_config.py`)

| Mã | Test | Truy vết | Kiểm điều gì |
| --- | --- | --- | --- |
| TC-DP-U01 | `test_caddy_is_the_only_public_entry_on_80_and_443` | AC-84.1 | Chỉ Caddy mở 80/443 |
| TC-DP-U02 | `test_the_gateway_publishes_nothing_in_production` | FR-84 | Gateway không mở cổng nào |
| TC-DP-U03 | `test_core_and_web_mark_cookies_secure_and_know_their_https_address` | AC-84.2 | HTTPS_ONLY và PUBLIC_URL https cho core, web |
| TC-DP-U04 | `test_the_domain_is_required_not_defaulted` | AC-84.3 | Thiếu tên miền thì dừng |
| TC-DP-U05 | `test_every_service_rotates_its_log` | FR-84 | Mọi dịch vụ xoay vòng nhật ký |
| TC-DP-U06 | `test_the_gateway_takes_the_client_address_from_caddy` | FR-84 | Gateway lấy địa chỉ người dùng từ Caddy, chỉ tin mạng nội bộ |
| TC-DP-U07 | `test_the_caddyfile_serves_the_domain_and_proxies_to_the_gateway` | FR-84 | Caddy phục vụ tên miền và chuyển tới gateway |
| TC-DP-U08 | `test_the_caddyfile_limits_bodies_like_the_gateway_and_never_overrides_app_headers` | FR-84 | Giới hạn kích thước như gateway; không ghi đè tiêu đề bảo mật của ứng dụng |
| TC-DP-U09 | `test_the_server_scripts_exist_and_stop_at_the_first_error` | FR-84 | Kịch bản máy chủ có `set -euo pipefail` |
| TC-DP-U10 | `test_the_deploy_never_ships_an_env_file` | AC-84.4 | `deploy.sh` không chép `.env` |

## 5. Kết quả chạy

| Lệnh | Kết quả |
| --- | --- |
| `ruff format --check`, `ruff check` | sạch (239 tệp) |
| `pytest -m "not e2e and not slow"` (SQLite) | 1333 test: 1317 qua, 16 bỏ qua theo thiết kế; độ phủ toàn bộ 92 % |
| `AICEFR_TEST_PG=... AICEFR_TEST_AMQP=... pytest -m "not e2e and not slow"` | 1333 test: 1322 qua, 10 bỏ qua, 1 đổ (TC-DB-I05, xem D045-B1); sau khi sửa, `tests/test_schema.py` và `tests/test_learning_plans.py` chạy lại ba lần trên PostgreSQL: 15/15 qua mỗi lần |
| `pytest -m e2e tests/e2e` | 79 test: 78 qua, 1 đổ (D046-B2); sau khi sửa, `test_learning_plans_e2e.py` và `test_lessons_e2e.py` chạy lại: 16/16 qua |
| `docker compose up` trên volume PostgreSQL dựng dưới D044, rồi `db_cli status` và `tools/compose_smoke.py` | `core` tự áp dụng phiên bản 1 và 2 khi khởi động; 18/18 điểm qua |
| Bộ production cục bộ sau Caddy (`AICEFR_DOMAIN=localhost`), `compose_smoke.py --base-url https://localhost --insecure` | 18/18 điểm qua; sao lưu rồi khôi phục đưa số tài khoản và tệp ghi âm về đúng lúc sao lưu (chạy trước khi thêm D045, D046) |

| Mã | Lỗi tìm thấy khi chạy thật | Xử lý |
| --- | --- | --- |
| D045-B1 | Bốn tiến trình cùng dựng phiên bản 1 trên SQLite: "database is locked", "duplicate column" (phiên bản 1 dựng bằng repository nên nằm ngoài giao dịch) | Cả lần nâng chạy dưới một khoá độc quyền mỗi kho: tệp `flock` cạnh SQLite, advisory lock cấp phiên trên PostgreSQL |
| D046-B1 | `form.elements.length` là số ô của form chứ không phải ô "Số bài": mọi yêu cầu ghép bị 422 | Đọc ô qua `querySelector('[name="length"]')` |
| D046-B2 | Trang Luyện tập hiện chữ "band" trong lời giới thiệu, lý do và cảnh báo, vi phạm bất biến của D025 | Dùng "trình độ" ở mọi chữ người học đọc; e2e kiểm thêm khối lộ trình riêng không có chữ "band" |
| D046-B3 | "ẩm thực" bỏ dấu thành "am thuc", chứa "am th" nên bị hiểu là muốn luyện âm th; dấu phẩy làm "du lịch," không khớp | Cụm nhiều từ khớp nguyên từ; bỏ dấu câu trước khi đọc mục tiêu |
| D046-B4 | Người học đã đánh giá B1 vẫn nhận bài A2; bài thêm cho đủ không có lý do | Lộ trình của người học bắt đầu từ trình độ đánh giá gần nhất, trình độ thấp hơn chỉ để bù; mọi bài có lý do |

**Chưa xác minh:** chưa triển khai lên máy chủ thật (chưa có VPS và tên miền); bộ production chưa được chạy lại sau khi thêm D045, D046 (mã ứng dụng đổi, cấu hình triển khai không đổi). Trọng số relevance của model chưa được hiệu chỉnh trên dữ liệu người dùng thật.
