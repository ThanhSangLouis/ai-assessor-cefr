# Kế hoạch và kết quả kiểm thử D036 — Luồng đăng nhập Google không giả được và cài khoá dễ

| Thuộc tính | Giá trị |
| --- | --- |
| Tính năng | D036: cookie mang `state`, `nonce` và verifier PKCE có chữ ký HMAC-SHA256 theo khoá của bản triển khai; cookie `__Host-` sau TLS; khung "Đăng nhập bằng Google" ở tab Cấu hình (FR-74, BR-36). Luồng PKCE S256 của D029 (FR-59) giữ nguyên |
| Phiên bản mã | nhánh `feat/billing` |
| Người lập | Võ Thanh Sang |
| Ngày | 07/10/2026 |

## 1. Mục tiêu

1. **Không luồng lạ nào đi tiếp.** Cookie không do máy chủ ký — viết tay, sửa, ký bằng khoá khác — bị bỏ, và Google không được hỏi đổi mã.
2. **Tên miền con không đặt được cookie luồng** khi chạy sau TLS.
3. **Khoá ký bền**: chung cho mọi tiến trình, còn nguyên qua lần khởi động lại.
4. **PKCE đúng chuẩn**: thử thách S256 khớp ví dụ của RFC 7636; verifier không rời máy chủ ra trình duyệt.
5. **Cài khoá dễ mà không lộ khoá**: quản trị viên thấy địa chỉ cần đăng ký và việc còn thiếu; client secret không bao giờ xuất hiện trong câu trả lời hay trên trang.

## 2. Ba tầng kiểm thử

| Tầng | Kiểm cái gì | Công cụ | Môi trường | Chạy ở đâu | Lệnh |
| --- | --- | --- | --- | --- | --- |
| 1. Unit | Chữ ký của cookie luồng; thử thách PKCE; tên cookie theo TLS | pytest | Hàm thuần, không mạng | Máy và CI | `pytest tests/test_google_flow_unit.py` |
| 2. Integration | Cookie giả trong trình duyệt của người đang đăng nhập; trọn vòng qua `https` với cookie `__Host-`; khoá qua khởi động lại; trạng thái cho quản trị viên | pytest, FastAPI TestClient | SQLite thật trên tệp tạm; Google thay ở `aicefr.auth.google._post_form` như `tests/test_profile.py`, thêm đếm số lần được gọi | Máy và CI | `pytest tests/test_google_flow.py` |
| 3. E2E | Khung ở tab Cấu hình; nút Google trên trang đăng nhập đưa trình duyệt tới Google với PKCE | Playwright + Chromium | Máy chủ uvicorn riêng với client id và secret không phải của Google; **mọi yêu cầu tới accounts.google.com bị chặn**, và yêu cầu `/auth/google/start` được dừng trước khi trình duyệt đi theo chuyển hướng | **Chỉ trên máy**; CI tự bỏ qua | `pytest -m e2e tests/e2e/test_google_setup_e2e.py` |

**Không test nào gọi Google.** Khoá Google chưa có (chủ dự án sẽ đặt sau), và test phải chạy không có mạng. Điều đã đối chiếu với nguồn chính thức ngày 07/10/2026: tài liệu discovery của Google (`authorization_endpoint`, `token_endpoint`, `code_challenge_methods_supported` gồm `S256`, `token_endpoint_auth_methods_supported` gồm `client_secret_post`); luật địa chỉ chuyển hướng và việc client secret chỉ hiện một lần lúc tạo (tài liệu "Using OAuth 2.0 for Web Server Applications"); RFC 9700 mục 2.1.1 (PKCE được khuyến nghị cả cho client bí mật); RFC 7636 Phụ lục B (ví dụ của S256).

## 3. Dữ liệu và môi trường

- Client secret trong test là chuỗi dựng bằng phép nhân (`"x" * 24`), không phải chuỗi viết sẵn.
- Khoá ký trong test unit là 32 byte cố định; trong integration là khoá do chính ứng dụng tạo trong CSDL tạm.
- Không có dữ liệu người dùng thật.

## 4. Tiêu chí vào và ra

- **Vào:** mã qua `ruff format --check` và `ruff check`.
- **Ra (được merge):** 100% test tầng 1 và 2 qua trên CI; 100% test tầng 3 qua trên máy trước khi merge; mọi tiêu chí AC-74.1..AC-74.8 có ít nhất một test (kiểm bằng `tests/test_product_traceability.py`); test của D029 (`tests/test_google_unit.py`, `tests/test_profile.py`) vẫn qua với cookie có chữ ký.

## 5. Truy vết tiêu chí chấp nhận

Tiêu chí chấp nhận AC-74.1..AC-74.8 nằm ở `docs/srs/SRS.md`, mục 3.9i.

| Tiêu chí chấp nhận | Test case |
| --- | --- |
| AC-74.1 | TC-GG-I01 |
| AC-74.2 | TC-GG-U01 |
| AC-74.3 | TC-GG-I02 |
| AC-74.4 | TC-GG-I03 |
| AC-74.5 | TC-GG-U02 |
| AC-74.6 | TC-GG-I04 |
| AC-74.7 | TC-GG-E01 |
| AC-74.8 | TC-GG-E02 |

## 6. Danh mục test case

### Tầng 1 — Unit (`tests/test_google_flow_unit.py`)

| Mã | Test | Truy vết | Kiểm điều gì |
| --- | --- | --- | --- |
| TC-GG-U01 | `test_the_flow_cookie_is_signed_and_any_change_breaks_it` | AC-74.2 | Đúng khoá đọc ra đúng luồng; khoá khác, không chữ ký, sửa nội dung, sửa chữ ký, luồng viết lại cho tài khoản khác, khoá tự đặt, ký tự không phải ASCII đều cho `None` |
| TC-GG-U02 | `test_the_pkce_challenge_is_s256_as_rfc_7636_shows` | AC-74.5 | Ví dụ Phụ lục B của RFC 7636; verifier 43–128 ký tự không dành riêng, không lặp trong 20 lần; địa chỉ tới Google có S256, không có verifier; tên cookie theo TLS |

### Tầng 2 — Integration (`tests/test_google_flow.py`)

| Mã | Test | Truy vết | Kiểm điều gì |
| --- | --- | --- | --- |
| TC-GG-I01 | `test_a_flow_cookie_this_server_did_not_sign_is_ignored` | AC-74.1 | Luồng "liên kết" viết cho tài khoản của nạn nhân, ký bằng khoá tự đặt hoặc không ký: mã `state`, Google không được gọi lần nào, tài khoản không bị liên kết |
| TC-GG-I02 | `test_behind_tls_the_flow_cookie_is_a_host_cookie` | AC-74.3 | `__Host-aicefr_oauth`, `Secure`, `Path=/`, `HttpOnly`, không `Domain`; đăng nhập trọn vòng qua `https`; cookie luồng bị xoá sau đó |
| TC-GG-I03 | `test_the_signing_key_is_made_once_and_kept` | AC-74.4 | Khoá 32 byte, hai kho đọc ra như nhau, tên khác thì khoá khác; luồng bắt đầu trước khi khởi động lại hoàn tất sau đó |
| TC-GG-I04 | `test_the_administrator_sees_what_to_register_with_google` | AC-74.6 | Trạng thái trên `http://testserver` (lời nhắc về `http://`), với địa chỉ `https` chưa bật TLS (lời nhắc, nút Google từ chối với mã `insecure`, không cookie nào được đặt), với `https` và TLS (không còn lỗi, cookie `__Host-`, nút đi tới Google), với địa chỉ IP (lời nhắc), với `http://[::1]` (loopback, không lỗi), khi chưa đặt khoá (hai biến thiếu); secret không có trong câu trả lời; giảng viên 403, khách 401 |

### Tầng 3 — E2E (`tests/e2e/test_google_setup_e2e.py`)

| Mã | Test | Truy vết | Kiểm điều gì |
| --- | --- | --- | --- |
| TC-GG-E01 | `test_the_config_tab_shows_what_to_register_with_google` | AC-74.7 | Khung ghi Đang bật, địa chỉ chuyển hướng của máy chủ thử, Client ID, "Đã đặt (không bao giờ hiển thị)", PKCE (S256), nút Sao chép; secret không có trên trang |
| TC-GG-E02 | `test_the_google_button_leaves_with_a_pkce_challenge` | AC-74.8 | Địa chỉ tới Google có `response_type=code`, `scope=openid email`, S256 với thử thách 43 ký tự, `state` khác `nonce`, `prompt=select_account`, địa chỉ chuyển hướng; cookie luồng HttpOnly, Lax, `/auth/google`, có chữ ký |

## 7. Kết quả chạy

| Lệnh | Kết quả |
| --- | --- |
| `pytest tests/test_google_flow_unit.py tests/test_google_flow.py` | 6 test qua |
| `pytest -m e2e tests/e2e/test_google_setup_e2e.py` | 2 test qua |
| `pytest tests/test_google_unit.py tests/test_profile.py` (D029, sau khi cookie có chữ ký) | 53 test qua |
| `pytest -m "not e2e and not slow"` (hồi quy, có đo độ phủ, cùng lần với D035, sau các sửa của lần rà bảo mật) | 1149 test: 1139 qua, 10 bỏ qua theo thiết kế; độ phủ toàn bộ 93%; `api/google_api.py` 98%, `auth/google.py` 95%, `storage/auth_repository.py` 96% |
| `pytest -m e2e tests/e2e` (hồi quy) | 65 test qua |

## 8. Lỗi và chỗ hở tìm thấy trong lúc làm

| Mã | Lỗi | Sửa | Giữ lại bằng |
| --- | --- | --- | --- |
| D036-B1 | Cookie luồng của D029 không có chữ ký: ai đặt được cookie cho tên miền có thể ghép phiên của nạn nhân với một luồng do mình viết, kể cả luồng liên kết tài khoản Google của mình vào bút danh của nạn nhân | Chữ ký HMAC-SHA256 theo khoá của bản triển khai; cookie `__Host-` sau TLS | TC-GG-U01, TC-GG-I01, TC-GG-I02 |
| D036-B2 | So chữ ký bằng `hmac.compare_digest` trên chuỗi có ký tự không phải ASCII làm máy chủ lỗi 500 thay vì từ chối | Bỏ giá trị không phải ASCII trước khi so | TC-GG-U01 |
| D036-B3 | Một bản nháp của TC-GG-E02 để trình duyệt đi tới trang thật của Google: một yêu cầu mở trang đăng nhập với client id giả, không có thông tin đăng nhập nào. Lý do: route của Playwright không bắt được đích của một chuyển hướng | Dừng ở `/auth/google/start` trước khi đi theo chuyển hướng, và chặn mọi yêu cầu tới accounts.google.com ở cấp ngữ cảnh trình duyệt | TC-GG-E02 |
| D036-B4 | Nút Sao chép đọc thuộc tính `data-copy` ở `common.js` trong khi thuộc tính được viết ở `admin.js`; test hợp đồng giao diện báo | Đặt phần xử lý cạnh nơi viết thuộc tính | `tests/test_frontend_contracts.py` |
| D036-B5 | Tên máy loopback IPv6 được so với `[::1]` trong khi `urlparse` trả `::1` | So với `::1` | TC-GG-I04 |
| D036-B6 | Rà bảo mật độc lập: chữ ký không chặn được việc cài vào trình duyệt người khác một luồng **thật** do kẻ tấn công bắt đầu, để người đó đăng nhập vào tài khoản của kẻ tấn công — chỉ tiền tố `__Host-` chặn được; docstring của bản đầu nói ngược lại | Địa chỉ chuyển hướng `https` mà chưa bật `AICEFR_HTTPS_ONLY` thì không bắt đầu luồng (mã `insecure`); sửa docstring, SDD bất biến 9, ADR-13 | TC-GG-I04 |
