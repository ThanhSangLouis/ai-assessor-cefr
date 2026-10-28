# Kế hoạch và kết quả kiểm thử D043, D044 — Dịch vụ

> **Cập nhật D050 (22/10/2026):** RabbitMQ đã được thay bằng Redis/BullMQ. `tests/test_bus_rabbitmq.py` đổi thành `tests/test_bus_redis.py` (chạy với `AICEFR_TEST_REDIS`), thêm kiểm "mỗi bài một việc, bài đánh giá đi trước"; `tests/test_services_split.py` có thêm bài kiểm ba dịch vụ nối qua Redis thật. Các mục bên dưới giữ nguyên làm lịch sử.

| Thuộc tính | Giá trị |
| --- | --- |
| Thay đổi | D043: sáu dịch vụ sau gateway, PostgreSQL mỗi dịch vụ một schema, RabbitMQ. Không thêm FR; mọi FR, NFR, BR giữ hành vi |
| Phiên bản mã | nhánh `refactor/microservices` |
| Người lập | Võ Thanh Sang |
| Ngày | 11/10/2026 |

## 1. Mục tiêu

1. **Hành vi không đổi.** Toàn bộ bộ kiểm thử có sẵn qua trên dạng một tiến trình, với mỗi dịch vụ một kho riêng.
2. **Không SQL chéo dịch vụ.** Kiểm thử đặt mỗi dịch vụ một tệp SQLite (hoặc một schema PostgreSQL); câu nào đọc bảng của dịch vụ khác sẽ đổ.
3. **Cùng mã chạy trên PostgreSQL.** Toàn bộ bộ kiểm thử chạy lại với mỗi dịch vụ một schema PostgreSQL.
4. **Dịch vụ tách rời vẫn làm việc cùng nhau.** Sáu ứng dụng gọi nhau qua HTTP sau một gateway giả lập; mọi route tới đúng dịch vụ.
5. **Bus thật.** Hàng đợi bền, mỗi việc một worker, sự kiện tới mọi bên đăng ký, hỏi–đáp có hạn giờ, thông điệp hỏng không chặn hàng đợi.
6. **Hệ thống chạy thật.** `docker compose` dựng đủ chín container; đi qua gateway kiểm các đường giữa dịch vụ và tính cô lập của schema.

## 2. Các tầng

| Tầng | Kiểm cái gì | Môi trường | Lệnh |
| --- | --- | --- | --- |
| Unit | Dịch SQL hai phương ngữ, bus trong tiến trình, lời gọi nội bộ bị từ chối, tiêu đề tài khoản, bảng định tuyến, ghép nhật ký | Hàm thuần | `pytest tests/test_platform_unit.py` |
| Integration, một tiến trình | Toàn bộ bộ kiểm thử, mỗi dịch vụ một kho | SQLite | `pytest -m "not e2e and not slow"` |
| Integration, PostgreSQL | Như trên | PostgreSQL 16, mỗi kiểm thử bốn schema | `AICEFR_TEST_PG=postgresql://... pytest -m "not e2e and not slow"` |
| Integration, tách dịch vụ | Sáu ứng dụng, `RemoteFacade` qua HTTP, gateway giả lập | SQLite, bus trong tiến trình | `pytest tests/test_services_split.py` |
| Integration, RabbitMQ | Bus `RabbitBus` | RabbitMQ 4 | `AICEFR_TEST_AMQP=amqp://... pytest tests/test_bus_rabbitmq.py` |
| E2E | Toàn bộ kiểm thử Playwright trên dạng một tiến trình | Chromium | `pytest -m e2e tests/e2e` |
| Hệ thống | Chín container qua gateway | Docker Compose | `python tools/compose_smoke.py` |

## 3. Danh mục kiểm thử mới

| Tệp | Test | Kiểm điều gì |
| --- | --- | --- |
| `test_platform_unit.py` | 13 test (28 trường hợp) | Dấu `?` thành tham số PostgreSQL ngoài chuỗi trích dẫn; `INSERT OR IGNORE`, `BEGIN IMMEDIATE`; kiểu cột giữ giá trị như SQLite; hàng PostgreSQL đọc như `sqlite3.Row`; bus trong tiến trình; lời gọi nội bộ bị từ chối và không tới được; tiêu đề tài khoản; 16 đường dẫn tới đúng dịch vụ; ghép nhật ký đúng thứ tự |
| `test_services_split.py` | `test_every_route_of_every_service_reaches_that_service_through_the_gateway` | Mọi route của mọi dịch vụ, qua bảng định tuyến, tới đúng dịch vụ đó; `/internal/` không bao giờ được chuyển tiếp |
| | `test_the_committed_gateway_configuration_is_generated_from_the_table` | Tệp nginx đã commit đúng bằng tệp sinh từ bảng |
| | `test_an_account_header_without_the_internal_key_is_anonymous` | Tiêu đề tài khoản giả, không có khoá: 401 |
| | `test_internal_calls_need_the_key` | Lời gọi nội bộ thiếu hoặc sai khoá: 403; phương thức không `@exposed`: 404 |
| | `test_the_gateway_never_forwards_internal_paths` | Gateway không chuyển `/internal/` |
| | `test_a_student_submits_practises_and_is_erased_across_the_services` | Đăng nhập, đồng thuận, nộp bài được `speech` chấm, bước bài học được `speech` đo, thanh bên, bản xuất cá nhân gom từ ba dịch vụ, nhật ký ghép, xoá dữ liệu tới `learning` |
| | `test_withdrawing_research_consent_reaches_the_study_over_the_bus` | Rút đồng ý ở `identity` đưa người học ra khỏi thực nghiệm ở `assessment` qua sự kiện |
| `test_bus_rabbitmq.py` | 5 test | Việc gửi khi chưa có worker chờ trong hàng đợi; mỗi việc một worker; sự kiện tới mọi dịch vụ đăng ký; hỏi–đáp và hết giờ; thông điệp hỏng không chặn hàng đợi |
| `test_ratings.py` | `test_a_review_decision_keeps_the_ratings_and_who_saw_the_machine` (từ PR D039–D042) | Giữ lại sau khi đổi `save` sang upsert |

Kiểm thử có sẵn được sửa theo cấu trúc mới (đường dẫn module, quét bài quá hạn đọc từ cơ sở dữ liệu, worker `speech` thay hàm chấm trong `main`), không nới tiêu chí.

## 4. Kết quả chạy

| Lệnh | Kết quả |
| --- | --- |
| `pytest -m "not e2e and not slow"` (SQLite, mỗi dịch vụ một tệp) | 1269 test: 1254 qua, 15 bỏ qua theo thiết kế (gồm 5 test RabbitMQ khi không có broker); độ phủ toàn bộ 91% |
| `AICEFR_TEST_PG=... AICEFR_TEST_AMQP=... pytest -m "not e2e and not slow"` | 1269 test: 1259 qua, 10 bỏ qua theo thiết kế, 8 phút 11 giây |
| `AICEFR_TEST_AMQP=... pytest tests/test_bus_rabbitmq.py` | 5 qua |
| `pytest -m e2e tests/e2e` | 77 qua |
| `python tools/compose_smoke.py` trên `docker compose up` | 17/17 điểm qua |

## 5. Lỗi tìm thấy trong lúc làm

| Mã | Lỗi | Sửa |
| --- | --- | --- |
| D043-B1 | `ON CONFLICT ... DO UPDATE SET repeats = repeats + 1`: PostgreSQL báo cột mơ hồ (bảng đích hay `excluded`) | Ghi rõ `billing_event.repeats` |
| D043-B2 | `(? IS NULL OR a.created_at > ?)`: PostgreSQL không đoán được kiểu của tham số chỉ so với NULL | Hai câu lệnh tuỳ `since` |
| D043-B3 | `CREATE SCHEMA IF NOT EXISTS` bị từ chối với vai trò không có quyền tạo schema, kể cả khi schema đã có | Tra `pg_namespace` trước, chỉ tạo khi thiếu |
| D043-B4 | Gateway giữ địa chỉ IP phân giải lúc khởi động; sau khi dịch vụ được tạo lại, địa chỉ cũ của `identity` đã thuộc về `web` | `resolver 127.0.0.11` và `proxy_pass` qua biến: phân giải lúc chuyển tiếp |
| D043-B5 | Gateway nối thêm vào `X-Forwarded-For` của trình duyệt: người dùng chọn được địa chỉ của mình để lách giới hạn đăng nhập | Ghi đè bằng `$remote_addr` |
| D043-B6 | Nhật ký của các dịch vụ ghi cùng một giây ghép sai thứ tự | Đóng dấu đến micro giây |
| D043-B7 | Mỗi lời gọi kho mở một kết nối PostgreSQL mới: bộ kiểm thử chậm gấp 2,5 lần | Pool kết nối theo máy chủ, đặt `search_path` mỗi lần lấy |

## 6. D044 — Gộp còn ba dịch vụ (13/10/2026)

Chủ dự án chọn gộp `identity`, `assessment`, `learning`, `billing` thành `core`, một schema PostgreSQL (SDD mục 4.18, ADR-16). Không thêm FR; mọi FR, NFR, BR giữ hành vi. Nhánh `fix/review-d039-d043`.

**Kiểm thử sửa theo cấu trúc mới.** `test_services_split.py` chạy ba ứng dụng: `core` với facade cục bộ, `speech`, `web` gọi `core` qua `RemoteFacade`; gateway giả lập dùng khoá gateway. `conftest.py` cho mỗi test một kho (một tệp SQLite hoặc một schema PostgreSQL). Bảng định tuyến trong `test_platform_unit.py` trỏ API về `core`. `compose_smoke.py` kiểm vai trò `core` không ghi được ra ngoài schema của mình và thêm điểm trang web có tên tài khoản (18 điểm).

**Kiểm thử thêm cho các lỗi tìm thấy khi review D039–D043** (`tests/test_review_d039_d043.py`, cộng TC-LE-I16):

| Test | Kiểm điều gì |
| --- | --- |
| `test_orphan_cleanup_refuses_a_store_without_its_tables` | `maintenance_cli orphans --delete` trên địa chỉ kho gõ sai: từ chối, mã 2, tệp ghi âm còn nguyên |
| `test_orphan_cleanup_runs_on_the_real_store` | Kho đúng thì chạy bình thường |
| `test_the_overdue_sweep_does_not_fail_a_response_that_just_finished` | `set_status(only_from=...)` không ghi FAILED lên bài vừa xong |
| `test_the_sweep_still_fails_a_response_that_waits` | Bài còn chờ vẫn bị đóng FAILED |
| `test_a_second_worker_result_does_not_replace_the_first` | Việc chấm giao lại lần hai không ghi đè kết quả đầu (`save(must_exist=True)`) |
| `test_words_spelt_like_an_ending_are_not_endings` | D039: need, hundred, was, this... không tính là đuôi -ed, -s |
| `test_letters_that_are_not_said_are_not_final_consonants` | D039: how, for, high, oh không có âm cuối; much, fish, with có |
| `test_only_reviews_that_ended_in_a_decision_are_timed` | D041: chỉ phiên kết thúc bằng quyết định được tính giờ |
| `test_idle_rating_sheets_are_left_out_like_idle_reviews` | D041: phiếu chấm mù mở quá 30 phút bị bỏ như phiên duyệt |
| `test_retest_pairs_never_span_two_scoring_models` | D042: cặp thử lại không ghép hai mô hình chấm |
| `test_feedback_stays_held_back_through_the_survey_and_in_the_export` (TC-LE-I16, AC-77.9) | D040: giai đoạn khảo sát vẫn giữ phản hồi, cả trong bản xuất cá nhân; đóng thì trả lại |

**Kết quả chạy**

| Lệnh | Kết quả |
| --- | --- |
| `ruff format --check`, `ruff check` | sạch |
| `pytest -m "not e2e and not slow"` (SQLite) | 1280 test: 1265 qua, 15 bỏ qua theo thiết kế; độ phủ toàn bộ 91% |
| `AICEFR_TEST_PG=... AICEFR_TEST_AMQP=... pytest -m "not e2e and not slow"` | 1280 test: 1270 qua, 10 bỏ qua theo thiết kế, 7 phút 53 giây |
| `pytest -m e2e tests/e2e` | 77 qua |
| `python tools/compose_smoke.py` trên `docker compose up` | 18/18 điểm qua |

Hai lượt chạy toàn bộ đầu tiên còn một test truy vết chưa có TC-LE-I16; đã thêm vào kế hoạch D039–D042 và SRS (AC-77.9) rồi chạy lại riêng test đó và tệp của nó: qua.

| Mã | Lỗi tìm thấy khi chạy thật | Xử lý |
| --- | --- | --- |
| D044-B1 | Volume `pgdata` dựng dưới D043 không có vai trò `core`: `core` khởi động lỗi xác thực | Ghi cách nâng cấp ở `docs/plan/TRIEN_KHAI_DICH_VU.md` mục 4 |

