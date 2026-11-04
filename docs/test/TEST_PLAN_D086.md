# Kế hoạch và kết quả kiểm thử D086 — Thông báo trực tiếp (Server-Sent Events)

| Thuộc tính | Giá trị |
| --- | --- |
| Thay đổi | D086: luồng `GET /api/v1/me/events` báo bài đã chấm xong, bài đã được duyệt, hàng chờ duyệt đổi (FR-95). **APPROVED** |
| Phiên bản mã | nhánh `feat/d086-live-events` |
| Người lập | Võ Thanh Sang |
| Ngày | 02/11/2026 |

## 1. Mục tiêu

1. **Đúng người.** Sự kiện chỉ tới tài khoản nó nói tới; giảng viên chỉ được báo về học viên các lớp mình dạy, quản trị viên được báo mọi bài (D071). Sự kiện chỉ mang mã bài và trạng thái.
2. **Đến ngay, đi qua gateway.** Gateway xác thực luồng như mọi API và không giữ lại dữ liệu; nhiều tiến trình `core` vẫn nhận đủ (Redis pub/sub).
3. **Không làm hỏng việc gì.** Kênh sự kiện lỗi thì việc gây ra sự kiện vẫn thành công; trang vẫn chạy như trước khi không có luồng.
4. **Không giữ chân deploy.** Luồng tự đóng sau thời hạn và đóng ngay khi tiến trình nhận SIGTERM.

## 2. Các tầng

| Tầng | Kiểm cái gì | Môi trường | Lệnh |
| --- | --- | --- | --- |
| Unit | Hub, luồng, kênh, bảng định tuyến gateway | Hàm thuần, asyncio | `pytest tests/test_d086_live_unit.py` |
| Integration | API luồng, sự kiện khi chấm, giữ khoá, quyết định, quét quá hạn; Redis thật khi có `AICEFR_TEST_REDIS` | Ứng dụng một tiến trình, MongoDB trong bộ nhớ | `pytest tests/test_d086_live_events.py` |
| Hệ thống (thủ công) | Cả chuỗi Caddy → nginx → core → Redis → trình duyệt | `docker compose` trên máy, mục 5 | — |

## 3. Truy vết tiêu chí chấp nhận

| Tiêu chí chấp nhận | Test case |
| --- | --- |
| AC-95.1 | TC-LV-I03 |
| AC-95.2 | TC-LV-I04 |
| AC-95.3 | TC-LV-I02 |
| AC-95.4 | TC-LV-U06 |
| AC-95.5 | TC-LV-U04, TC-LV-I07 |

## 4. Test case

### 4.1. Unit — `tests/test_d086_live_unit.py`

| Mã | Test | Truy vết | Kiểm |
| --- | --- | --- | --- |
| TC-LV-U01 | `test_an_event_reaches_its_accounts_and_roles_and_nobody_else` | FR-95 | Sự kiện tới đúng tài khoản và đúng vai trò; học viên khác không nhận gì |
| TC-LV-U02 | `test_an_account_holds_a_bounded_number_of_streams_and_a_full_queue_drops` | FR-95 | Quá 8 luồng một tài khoản bị từ chối; luồng đóng thì trả chỗ; hàng đợi đầy thì bỏ khung, không lỗi |
| TC-LV-U03 | `test_a_stream_says_ready_carries_events_and_heartbeats_and_ends_on_time` | FR-95 | Mở bằng `ready` và `retry`, có sự kiện và nhịp giữ kết nối, tự đóng đúng hạn và trả chỗ |
| TC-LV-U04 | `test_publishing_never_raises_and_an_event_for_nobody_is_not_sent` | AC-95.5 | Kênh lỗi không làm lỗi việc gây ra sự kiện; sự kiện không có người nhận thì không gửi |
| TC-LV-U05 | `test_an_event_crosses_processes_unchanged_and_the_channel_follows_the_bus` | FR-95 | Sự kiện qua Redis không đổi; bus Redis thì kênh Redis, không thì trong tiến trình |
| TC-LV-U06 | `test_the_gateway_streams_the_events_to_core_unbuffered` | AC-95.4 | Gateway chuyển luồng tới `core`, có `auth_request`, tắt đệm và chờ đọc 1 giờ; chỉ riêng đường này |
| TC-LV-U07 | `test_stopping_the_process_ends_every_stream_at_once_even_a_full_one` | FR-95 | SIGTERM đóng mọi luồng ngay, kể cả luồng có hàng đợi đầy |

### 4.2. Integration — `tests/test_d086_live_events.py`

| Mã | Test | Truy vết | Kiểm |
| --- | --- | --- | --- |
| TC-LV-I01 | `test_the_stream_needs_a_session` | FR-95 | Chưa đăng nhập: 401 |
| TC-LV-I02 | `test_a_signed_in_tab_receives_its_own_events_on_the_stream` | AC-95.3 | `text/event-stream`, `X-Accel-Buffering: no`; nhận sự kiện của mình, không của người khác; tự đóng sau `AICEFR_LIVE_MAX_SECONDS` |
| TC-LV-I03 | `test_a_scored_response_tells_its_owner_by_id_only` | AC-95.1 | Chấm xong: đúng một sự kiện tới học viên, chỉ mã bài và trạng thái; bài cần duyệt thì hàng chờ được báo |
| TC-LV-I04 | `test_locking_and_deciding_tell_the_reviewers_and_the_student` | AC-95.2 | Giữ khoá báo giảng viên của lớp và quản trị viên; đóng bài báo học viên `REJECTED` rồi báo hàng chờ |
| TC-LV-I05 | `test_a_response_closed_by_the_timeout_sweep_tells_its_owner` | FR-95 | Bài quá hạn bị đóng `FAILED` cũng báo học viên |
| TC-LV-I06 | `test_an_event_published_in_one_process_reaches_the_streams_of_another` | FR-95 | Với Redis thật: sự kiện phát ở tiến trình này tới luồng ở tiến trình khác |
| TC-LV-I07 | `test_a_failed_lookup_of_whom_to_tell_never_fails_the_action` | AC-95.5 | Tra chủ bài hay giảng viên của lớp lỗi: bài vẫn được chấm và lưu một lần, quyết định không thành 500 |

## 5. Kết quả

| Lần chạy | Lệnh | Kết quả |
| --- | --- | --- |
| Unit và integration | `pytest tests/test_d086_live_unit.py tests/test_d086_live_events.py` | 14 PASS, 1 SKIP (TC-LV-I06 cần Redis) |
| Redis thật | `AICEFR_TEST_REDIS=redis://localhost:6390/0 pytest tests/test_d086_live_events.py -k another` (Redis 7 trong Docker) | TC-LV-I06 PASS |
| Hệ thống, thủ công, 02/11/2026 | `docker compose` (nginx, core, web, speech, MongoDB, Redis) build từ nhánh, thêm Caddy 2.11 trước gateway; tài khoản mẫu, ASR giả lập | Xem dưới |

Kiểm thủ công trên hệ thống chạy thật:

- Học viên nộp bài, bài chấm xong thì học viên nhận `response.finished` và quản trị viên nhận `queue.changed` trong cùng một mili giây, khoảng 1,5 giây sau khi nộp; qua Caddy (HTTP/2, có nhận nén) cũng tới ngay, Caddy không nén `text/event-stream`.
- Giữ khoá thì quản trị viên nhận `queue.changed`; quyết định thì học viên nhận `review.done` trạng thái `COMPLETED`; nhịp giữ kết nối đều 20 giây.
- Trình duyệt: trang chờ chấm (dịch vụ chấm tạm dừng) hỏi trạng thái 10 giây một lần khi luồng mở; khi chấm xong, trang hỏi ngay ngoài lịch và mở báo cáo. Trang khác hiện "Giảng viên đã duyệt bài nói của bạn. Xem nhận xét", số trên thanh bên tăng; đang mở đúng báo cáo đó thì hiện "Giảng viên vừa duyệt bài này. Tải lại để xem". Hàng chờ của quản trị viên tự từ 0 lên 2 bài và tự hiện "Đang được QT-01 duyệt" khi bài bị giữ khoá.
- Dừng `core` khi có luồng mở: 0,6 giây, không có dòng lỗi; trước khi đóng luồng bằng SIGTERM là 5,9 giây kèm lỗi `CancelledError`.

Chưa kiểm (`NOT_RUN`): trình duyệt Safari và Firefox; hai tiến trình `core` thật sau một gateway (chỉ kiểm bằng TC-LV-I06).
