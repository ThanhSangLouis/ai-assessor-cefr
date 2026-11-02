# Kế hoạch và kết quả kiểm thử D088 — Cài như ứng dụng (PWA) và thông báo đẩy

| Thuộc tính | Giá trị |
| --- | --- |
| Thay đổi | D088: manifest và service worker; học viên bật thông báo cho từng thiết bị; bài chấm xong hay đã được duyệt hiện thành thông báo khi không mở tab nào (FR-96). **APPROVED** |
| Phiên bản mã | nhánh `feat/d088-pwa-push` |
| Người lập | Võ Thanh Sang |
| Ngày | 02/11/2026 |

## 1. Mục tiêu

1. **Cài được, mất mạng không vỡ.** Manifest đủ tên và biểu tượng; service worker phục vụ từ gốc trang; mất mạng khi mở trang thì hiện trang báo mất kết nối, có mạng lại thì không còn gì cũ.
2. **Máy chủ chỉ gửi tới dịch vụ push của trình duyệt.** Địa chỉ khác (mạng nội bộ, siêu dữ liệu đám mây, HTTP thường) bị từ chối khi đăng ký.
3. **Không lộ gì.** Thông báo chỉ có tiêu đề, một câu, đường dẫn báo cáo; được ký và mã hoá để chỉ trình duyệt đọc được; bấm vào chỉ mở trang của SpeakUp.
4. **Không làm hỏng việc chính.** Gửi trên luồng riêng; trình duyệt hỏng không chặn trình duyệt khác; dịch vụ push báo trình duyệt không còn thì xoá.

## 2. Các tầng

| Tầng | Kiểm cái gì | Môi trường | Lệnh |
| --- | --- | --- | --- |
| Unit | Danh sách dịch vụ push, khoá VAPID, ký và mã hoá thật, bộ gửi | Hàm thuần; `pywebpush` với dịch vụ push thay bằng bản ghi | `pytest tests/test_d088_push_unit.py` |
| Integration | Manifest, service worker, API đăng ký, gửi khi chấm và duyệt, xoá dữ liệu | Ứng dụng một tiến trình, MongoDB trong bộ nhớ | `pytest tests/test_d088_push.py` |
| E2E | Service worker trong Chromium thật: cài, trang mất kết nối, thông báo từ một tin đẩy | Chromium chế độ headless mới, MongoDB thật | `AICEFR_TEST_MONGO=… pytest tests/e2e/test_pwa_e2e.py` |

## 3. Truy vết tiêu chí chấp nhận

| Tiêu chí chấp nhận | Test case |
| --- | --- |
| AC-96.1 | TC-PW-I01, TC-PW-E01 |
| AC-96.2 | TC-PW-I02, TC-PW-U01 |
| AC-96.3 | TC-PW-I04, TC-PW-E02 |
| AC-96.4 | TC-PW-I05 |
| AC-96.5 | TC-PW-I06 |
| AC-96.6 | TC-PW-U03 |
| AC-96.7 | TC-PW-I07 |

## 4. Test case

### 4.1. Unit — `tests/test_d088_push_unit.py`

| Mã | Test | Truy vết | Kiểm |
| --- | --- | --- | --- |
| TC-PW-U01 | `test_only_a_browsers_push_service_is_an_endpoint` | AC-96.2 | Nhận Google, Mozilla, Apple, Microsoft qua HTTPS cổng 443; từ chối HTTP, cổng khác, tên miền giả, có mật khẩu trong URL, `localhost`, `169.254.169.254`, tên dịch vụ nội bộ |
| TC-PW-U02 | `test_a_vapid_key_pair_is_a_p256_point_and_its_scalar` | FR-96 | Khoá công khai là điểm P-256 65 byte, khoá riêng 32 byte, base64url không đệm, mỗi lần một cặp mới |
| TC-PW-U03 | `test_a_real_message_is_signed_and_only_the_browser_can_read_it` | AC-96.6 | `pywebpush` thật: `aes128gcm`, TTL 24 giờ, chữ ký VAPID mang khoá công khai của máy chủ; nội dung gửi đi không chứa bản rõ, chỉ khoá của trình duyệt giải mã được |
| TC-PW-U04 | `test_the_sender_reaches_every_browser_and_forgets_the_gone_ones` | FR-96 | Gửi mọi trình duyệt của tài khoản, không gửi tài khoản khác; 404 và 410 thì xoá, 500 thì giữ; một trình duyệt lỗi không chặn trình duyệt khác; tin chỉ có tiêu đề, câu, đường dẫn, nhãn |
| TC-PW-U05 | `test_without_keys_or_an_account_nothing_is_sent` | FR-96 | Không có khoá hay không có tài khoản thì không gửi |

### 4.2. Integration — `tests/test_d088_push.py`

| Mã | Test | Truy vết | Kiểm |
| --- | --- | --- | --- |
| TC-PW-I01 | `test_the_app_is_installable_from_the_sites_root` | AC-96.1 | Manifest đúng loại, tên, `standalone`, biểu tượng 192, 512, maskable có thật trên đĩa; `/sw.js` không lưu đệm, `Service-Worker-Allowed: /`; trang có `link rel="manifest"` và `theme-color` |
| TC-PW-I02 | `test_a_learner_registers_a_browser_on_a_push_service_only` | AC-96.2 | Cần đăng nhập; đăng ký hai lần vẫn một bản; địa chỉ nội bộ, HTTP thường, khoá sai dạng: 422; xoá được |
| TC-PW-I03 | `test_without_vapid_keys_notifications_are_not_offered` | FR-96 | Không có khoá: `enabled` false, đăng ký 503 |
| TC-PW-I04 | `test_a_scored_response_reaches_the_learners_devices_when_no_tab_is_open` | AC-96.3 | Một tin tới đúng trình duyệt, chỉ bốn trường, đường dẫn và nhãn theo mã bài |
| TC-PW-I05 | `test_an_open_tab_hears_it_on_the_live_stream_instead` | AC-96.4 | Đang có luồng D086 thì không gửi tin đẩy |
| TC-PW-I06 | `test_a_teachers_decision_reaches_the_learners_devices` | AC-96.5 | Đóng bài: "Giảng viên đã duyệt bài nói", đường dẫn báo cáo |
| TC-PW-I07 | `test_erasing_a_participant_forgets_their_browsers` | AC-96.7 | Xoá dữ liệu người học xoá luôn trình duyệt của họ |

### 4.3. E2E — `tests/e2e/test_pwa_e2e.py`

| Mã | Test | Truy vết | Kiểm |
| --- | --- | --- | --- |
| TC-PW-E01 | `test_the_worker_installs_and_an_offline_page_replaces_the_browsers_error` | AC-96.1 | Service worker điều khiển trang; mất mạng thì hiện "Bạn đang mất kết nối mạng"; có mạng lại thì trang thật |
| TC-PW-E02 | `test_a_push_message_becomes_a_notification_that_opens_the_report` | AC-96.3 | Tin đẩy (giao qua DevTools) thành thông báo đúng tiêu đề, câu, đường dẫn báo cáo |
| TC-PW-E03 | `test_a_message_cannot_send_the_learner_to_another_site` | FR-96 | Tin trỏ sang trang khác thì thông báo mở trang chủ SpeakUp |
| TC-PW-E04 | `test_without_server_keys_the_account_page_offers_no_switch` | FR-96 | Máy chủ chưa có khoá: trang Tài khoản không hiện công tắc |

## 5. Kết quả

| Lần chạy | Lệnh | Kết quả |
| --- | --- | --- |
| Unit | `pytest tests/test_d088_push_unit.py` | 16 PASS (TC-PW-U01 có 12 trường hợp) |
| Integration | `pytest tests/test_d088_push.py` | 7 PASS |
| E2E | `AICEFR_TEST_MONGO=mongodb://localhost:27041 pytest tests/e2e/test_pwa_e2e.py` (MongoDB 7 trong Docker) | 4 PASS |
| Toàn bộ (không e2e) | `pytest -m "not e2e and not slow"` trên MongoDB và Redis thật | 1.467 PASS, 20 SKIP |
| Toàn bộ e2e | `pytest -m e2e` | 62 PASS. Lần đầu 1 FAIL: `page.route` của Playwright không thấy request do service worker gửi, nên test nút Google thấy trang trống. Sửa: service worker chỉ chuyển tiếp lượt mở trang bằng GET; các test e2e khác chặn service worker (`service_workers="block"`), riêng `test_pwa_e2e.py` cho phép |

Giới hạn (`NOT_RUN`): Chromium của Playwright không có dịch vụ push (thiếu khoá Google), nên chặng máy chủ → dịch vụ push thật → trình duyệt chưa kiểm tự động; hai nửa của nó được kiểm riêng (TC-PW-U03 mã hoá và ký đúng chuẩn, TC-PW-E02 service worker nhận tin). Kiểm thủ công trên production sau khi chủ dự án dán khoá VAPID: bật thông báo trên Chrome Android và Safari iOS (đã thêm vào Màn hình chính), đóng tab, nộp bài.
