# Bảng kê giấy phép và nguồn nội dung

Bảng này trả lời một câu hỏi: **mỗi thứ hệ thống dùng mà không do nhóm viết ra đến
từ đâu và được dùng theo điều kiện nào.** Định nghĩa hoàn thành (§11.2 mục 15) đòi
có nó; rubric mục 6 coi mã hay nội dung trùng nguồn khác mà không khai là đạo văn.

Cập nhật ngày 07/10/2026 (D028). Giấy phép của thư viện đọc từ metadata của gói
đã cài trong môi trường phát triển (`importlib.metadata`), không chép theo trí nhớ;
chỗ nào chưa kiểm được thì ghi [CẦN XÁC MINH].

## 1. Thư viện chạy cùng ứng dụng

| Gói | Phiên bản đã kiểm | Giấy phép (theo metadata) | Dùng vào việc |
| --- | --- | --- | --- |
| numpy | 2.5.3 | BSD-3-Clause (kèm 0BSD, MIT, Zlib cho phần nhúng) | Xử lý tín hiệu, đặc trưng |
| scipy | 1.18.1 | BSD | Lọc, thống kê |
| scikit-learn | 1.9.1 | BSD-3-Clause | Huấn luyện mô hình chấm (công cụ), kiểm chéo |
| soundfile | 0.14.0 | BSD-3-Clause | Đọc tệp âm thanh |
| pydantic | 2.13.5 | MIT | Hợp đồng dữ liệu |
| fastapi | 0.141.1 | MIT | Tầng API |
| starlette | 1.6.0 | BSD-3-Clause | Nền của FastAPI |
| uvicorn | 0.52.4 | BSD-3-Clause | Máy chủ ASGI |
| python-multipart | 0.0.32 | Apache-2.0 | Nhận tệp tải lên |
| jinja2 | 3.1.6 | BSD | Mẫu trang |
| bcrypt | 5.0.0 | Apache-2.0 | Băm mật khẩu (NFR-07) |
| simplemma | 2.0.0 | MIT | Nhận mọi dạng của từ khoá trong bài học (D025) |

## 2. Thư viện tuỳ chọn (cài thêm khi chạy thật)

| Gói | Phiên bản đã kiểm | Giấy phép | Dùng vào việc |
| --- | --- | --- | --- |
| mlx-whisper | 0.4.3 | MIT | Nhận dạng tiếng nói trên Apple Silicon |
| faster-whisper | chưa cài trên máy kiểm | [CẦN XÁC MINH] MIT theo kho mã nguồn | Nhận dạng tiếng nói trên máy khác |
| silero-vad | 6.2.1 | MIT | Tách đoạn có tiếng nói |
| torch | 2.14.0 | Biểu thức nhiều giấy phép, mở đầu bằng Apache-2.0; xem METADATA của gói | Nền chạy Silero VAD |

## 3. Công cụ phát triển (không đi cùng sản phẩm)

| Gói | Giấy phép | Dùng vào việc |
| --- | --- | --- |
| pytest 9.1.1, pytest-cov 7.1.0 | MIT | Kiểm thử, độ phủ |
| ruff 0.16.x | MIT | Định dạng và soát mã |
| playwright 1.62.0 | Apache-2.0 | Kiểm thử E2E trên trình duyệt |
| httpx2 | [CẦN XÁC MINH] chưa cài trên máy kiểm | Client cho `TestClient` trên CI |

## 4. Mô hình đã huấn luyện sẵn

| Mô hình | Giấy phép | Ghi chú |
| --- | --- | --- |
| Whisper (OpenAI), bản `large-v3-turbo` qua `mlx-community` | MIT | Trọng số **không** nằm trong repo; tải về bộ nhớ đệm của máy khi chạy |
| Silero VAD | MIT | Đi kèm gói `silero-vad` |

## 4b. Dịch vụ bên ngoài

| Dịch vụ | Khi nào dùng | Dữ liệu đi ra | Điều kiện |
| --- | --- | --- | --- |
| VNPay (cổng thanh toán, bản 2.1.0) | Chỉ khi người vận hành đặt `AICEFR_BILLING=on`, có `vnpay` trong `AICEFR_PAYMENT_GATEWAYS` cùng mã website và chuỗi bí mật VNPay cấp (D034, D035), và chỉ khi quản trị viên chọn VNPay rồi bấm thanh toán | Trình duyệt của quản trị viên được chuyển sang trang VNPay với mã đơn, số tiền, nội dung không dấu, địa chỉ trả về và địa chỉ IP; **không** có dữ liệu người học. VNPay gọi lại địa chỉ thông báo với kết quả có chữ ký | Hợp đồng đại lý thanh toán của một pháp nhân với VNPay; mặc định là cổng thử trong ứng dụng, không gọi ra ngoài |
| Stripe (Checkout Sessions API, webhook) | Chỉ khi người vận hành đặt `AICEFR_BILLING=on`, có `stripe` trong `AICEFR_PAYMENT_GATEWAYS` và `AICEFR_STRIPE_SECRET_KEY` (D035), và chỉ khi quản trị viên chọn Stripe rồi bấm thanh toán. Khoá `sk_test_` là chế độ thử; khoá `sk_live_` cần `AICEFR_PAYMENTS_LIVE` | Máy chủ gọi `api.stripe.com` để mở và đọc lại một Checkout Session: mã đơn, số tiền VND, nội dung không dấu, địa chỉ trả về; **không** có dữ liệu người học. Người trả nhập thẻ và email trên trang của Stripe; hệ thống chỉ giữ mã phiên và mã giao dịch. Stripe gọi lại webhook với sự kiện có chữ ký | Điều khoản dịch vụ của Stripe; Stripe chưa mở tài khoản bán hàng cho doanh nghiệp đặt tại Việt Nam (stripe.com/global, 07/10/2026) nên chỉ dùng chế độ thử; không thư viện SDK, gọi bằng thư viện chuẩn; dự phòng là cổng thử trong ứng dụng hoặc cổng khác |
| MoMo (ví điện tử, API v2 `captureWallet`) | Chỉ khi người vận hành đặt `AICEFR_BILLING=on`, có `momo` trong `AICEFR_PAYMENT_GATEWAYS` cùng partner code, access key, secret key MoMo cấp (D035), và chỉ khi quản trị viên chọn MoMo rồi bấm thanh toán. Mặc định gọi môi trường thử `test-payment.momo.vn` | Máy chủ gửi MoMo mã đơn, số tiền, nội dung không dấu, địa chỉ trả về và địa chỉ IPN; **không** có dữ liệu người học. MoMo gọi lại IPN với kết quả có chữ ký | Hợp đồng đối tác của một pháp nhân với MoMo cho môi trường thật; không thư viện SDK; dự phòng như trên |
| Google Identity (OAuth 2.0 / OpenID Connect) | Chỉ khi người vận hành cấu hình `AICEFR_GOOGLE_CLIENT_ID` và `AICEFR_GOOGLE_CLIENT_SECRET` (D029, D036), và chỉ khi người dùng tự bấm đăng nhập hay liên kết bằng Google | Mã uỷ quyền và thông tin OAuth client; **không** gửi bản ghi âm, bản chép hay kết quả. Hệ thống nhận ID token và chỉ giữ mã băm của định danh | Điều khoản dịch vụ của Google APIs; trường đăng ký OAuth client trên tài khoản Google Cloud của mình |

## 5. Dữ liệu

| Nguồn | Điều kiện | Hệ quả cho repo này |
| --- | --- | --- |
| Speak & Improve Corpus (Cambridge University Press & Assessment) | Giấy phép nghiên cứu: không phân phối lại dữ liệu; không công bố thống kê suy ra từ dữ liệu khi chưa được bên cấp phép duyệt | Không commit audio, bản chép hay nhãn. Các hệ số và số đo trong hiện vật mô hình là thống kê suy ra từ corpus: chỉ giữ trong repo **riêng tư** này, không đưa sang repo công khai và không đưa lên giao diện cho người dùng |
| Dữ liệu tự thu trên sinh viên (khảo sát W8–W10) | Theo phiếu đồng thuận có phiên bản (FR-01, FR-35) | Không commit; chỉ xuất qua bản xuất nghiên cứu đã lọc theo đồng thuận |

## 6. Nội dung

| Nội dung | Nguồn | Cách dùng |
| --- | --- | --- |
| Mô tả band A2, B1, B2 ở trang `/bands` (D028) | Khung tham chiếu CEFR, bản bổ sung 2020 (Hội đồng châu Âu), các thang mô tả định tính về ngôn ngữ nói | **Diễn đạt lại bằng tiếng Việt**, không dịch nguyên văn và không chép thang gốc; trang ghi rõ nguồn và ghi là chờ giảng viên Ngoại ngữ duyệt (A-03) |
| Bài học mẫu trong lộ trình (D025, D027) | Nhóm tự soạn | Nội dung mẫu, chờ giảng viên Khoa Ngoại ngữ duyệt |
| Bộ icon `static/icons.svg` (D027, D028) | Nhóm tự vẽ trên lưới 24 px | Không lấy từ bộ icon nào khác |
| Phông Roboto (D031) | Google; bản biến thiên đóng gói bởi Fontsource, gói `@fontsource-variable/roboto` 5.3.0 | **SIL Open Font License 1.1**. Sáu tệp WOFF2 (thẳng và nghiêng; latin, latin-ext, vietnamese) **do ứng dụng tự phục vụ** từ `src/aicefr/api/static/fonts/`, kèm nguyên văn giấy phép `ROBOTO-OFL.txt`; không tải từ CDN (CSP `font-src 'self'`, phòng máy không có mạng). Không sửa tệp phông, nên không phát sinh nghĩa vụ đổi tên theo OFL |
| Logo và favicon (D031) | Nhóm tự vẽ | Bong bóng thoại và ba thanh, vẽ bằng SVG; không lấy từ bộ icon hay logo nào khác |
| Ảnh nền "bậc thang tiếng nói" (D037) | Nhóm tự vẽ bằng mã: `tools/make_art.py` | Ba tệp `static/art/hills.svg`, `static/art/contours.svg`, `templates/_art.html` do script của dự án vẽ ra (đường cong Catmull-Rom, hạt giống cố định); không lấy từ ảnh, bộ hình hay ứng dụng thiết kế nào. Không dùng Rive: chủ dự án chọn vẽ trong mã và không tải bộ cài |
