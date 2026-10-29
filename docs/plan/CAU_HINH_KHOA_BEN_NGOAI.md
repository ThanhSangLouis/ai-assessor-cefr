# Cài khoá cho dịch vụ bên ngoài: Google, Stripe, MoMo, VNPay

Tài liệu này dành cho người vận hành một bản triển khai: lấy khoá ở đâu, đặt vào đâu, và kiểm tra thế nào là đã đúng. Mã đã làm sẵn cả bốn dịch vụ (D029, D034, D035, D036); **mọi dịch vụ đều tắt cho tới khi có khoá**, và mọi cổng thanh toán mặc định chạy ở môi trường thử của chính nó.

Các bước dưới đây đã được đối chiếu với tài liệu chính thức của Google, Stripe và MoMo ngày 07/10/2026. Giao diện của các trang quản trị đó có thể đổi; khi một nút không còn đúng tên, hãy theo tài liệu gốc ghi ở cuối mỗi mục.

## 0. Ba nguyên tắc

1. **Khoá chỉ nằm trong `.env` hoặc biến môi trường của máy chủ.** Tệp `.env` đã có trong `.gitignore`; sao `.env.example` thành `.env` rồi điền. `demo.sh` tự đọc `.env` nếu có; chạy cách khác thì nạp bằng `set -a; . ./.env; set +a`. Không commit `.env`, không dán client secret hay khoá bí mật vào chat, issue hay ảnh chụp màn hình.
2. **Không có tiền thật trong đồ án.** Cổng thu tiền thật — khoá Stripe `sk_live_`, địa chỉ thật của VNPay hay MoMo — chỉ chạy khi đặt `AICEFR_PAYMENTS_LIVE=on` (khi đó mọi cổng ở môi trường thử tự tắt, để không ai mua gói thật bằng thẻ thử), và việc đó cần một pháp nhân, hợp đồng với cổng, và giải quyết giấy phép dữ liệu huấn luyện (xem `DE_XUAT_GOI_DICH_VU.md`). Trong đồ án, không đặt biến này.
3. **Kiểm tra trên chính ứng dụng.** Sau khi đặt khoá và khởi động lại, đăng nhập bằng tài khoản quản trị: tab **Cấu hình** có khung "Đăng nhập bằng Google", tab **Gói dịch vụ** liệt kê các cổng đang bật và nói rõ cổng nào còn thiếu khoá — bằng tên biến, không bao giờ bằng giá trị.

## 1. Đăng nhập bằng Google (OAuth 2.0, luồng mã uỷ quyền có PKCE)

**Đã làm sẵn.** Luồng là OpenID Connect với PKCE S256, `state` và `nonce` (D029); cookie mang luồng có chữ ký của bản triển khai và là cookie `__Host-` khi chạy sau TLS (D036). Hệ thống chỉ giữ mã băm một chiều của định danh Google, không giữ email hay tên; Google không tạo tài khoản — người dùng đăng nhập bằng bút danh, liên kết Google ở trang Tài khoản, từ đó đăng nhập được bằng Google. Sơ đồ tuần tự: hình 7 của SDD (`docs/sdd/SDD.md`, mục 4.12a).

**Vì sao vừa PKCE vừa client secret.** Ứng dụng là client bí mật (máy chủ giữ secret), và Google yêu cầu `client_secret` khi đổi mã với client loại Web application. PKCE vẫn được dùng thêm vì RFC 9700 (01/2025, mục 2.1.1) khuyến nghị PKCE cả cho client bí mật để chống tiêm mã uỷ quyền; Google công bố hỗ trợ S256 trong tài liệu discovery (`code_challenge_methods_supported`).

### Các bước trên Google Cloud Console

1. Mở <https://console.cloud.google.com/>, chọn hoặc tạo một project.
2. Vào **Google Auth Platform** (trong APIs & Services):
   - **Branding:** tên ứng dụng, email hỗ trợ; khi chạy thật thì thêm tên miền của trường vào authorized domains.
   - **Audience:** *Internal* nếu project thuộc Google Workspace của trường (chỉ tài khoản của trường đăng nhập được, không cần Google xét duyệt); không thì *External* ở trạng thái *Testing* và thêm email những người thử vào **Test users**.
   - **Data Access:** chỉ cần `openid` và email. Đó là toàn bộ phạm vi hệ thống xin (`scope=openid email`).
3. Vào **Clients** → **Create Client** → Application type **Web application**.
4. Ở **Authorized redirect URIs**, thêm đúng từng ký tự:
   - máy mình: `http://localhost:8000/auth/google/callback`
   - máy chủ thật: `https://<tên-miền-của-bạn>/auth/google/callback`

   Không cần "Authorized JavaScript origins". Google chỉ nhận `http://` cho localhost và không nhận địa chỉ IP trần (trừ localhost).
5. Bấm **Create** và **lưu ngay client secret**: Google chỉ hiện secret một lần lúc tạo, sau đó không xem hay tải lại được.
6. Điền `.env`:

   ```bash
   AICEFR_GOOGLE_CLIENT_ID=1234567890-abc...apps.googleusercontent.com
   AICEFR_GOOGLE_CLIENT_SECRET=<secret vừa lưu>
   AICEFR_GOOGLE_DOMAIN=            # tuỳ chọn, ví dụ hcmute.edu.vn: chỉ tài khoản của trường
   AICEFR_PUBLIC_URL=               # máy chủ thật: https://<tên-miền-của-bạn>
   AICEFR_HTTPS_ONLY=               # máy chủ thật: on
   ```

   Máy chủ thật chạy qua `https` **phải** đặt `AICEFR_HTTPS_ONLY=on`; nếu không, nút Google báo "chưa đăng nhập bằng Google được" (mã `insecure`). Đó là chủ ý: chỉ khi biết mình chạy sau TLS, hệ thống mới dùng cookie `__Host-`, thứ chặn người khác cài luồng đăng nhập vào trình duyệt của bạn.

7. Khởi động lại, mở tab **Cấu hình** bằng tài khoản quản trị. Khung "Đăng nhập bằng Google" phải ghi **Đang bật**, không còn mục "Cần xem lại", và địa chỉ chuyển hướng trên khung phải trùng với địa chỉ đã đăng ký ở bước 4 (có nút Sao chép).
8. Thử: đăng nhập bằng bút danh → **Tài khoản** → **Liên kết tài khoản Google** → đăng xuất → **Đăng nhập bằng Google**.

### Lỗi hay gặp

| Thấy gì | Vì sao | Sửa |
| --- | --- | --- |
| Google báo `redirect_uri_mismatch` | Địa chỉ đã đăng ký khác địa chỉ hệ thống gửi: `http` và `https`, cổng, `localhost` và `127.0.0.1`, dấu `/` cuối | Chép địa chỉ từ khung trong tab Cấu hình rồi dán vào Google |
| Google báo ứng dụng chưa được xác minh hoặc chặn truy cập | Audience là External ở Testing mà tài khoản chưa có trong Test users | Thêm email vào Test users, hoặc dùng Internal nếu là Google Workspace |
| Trang đăng nhập báo "Phiên đăng nhập Google đã hết hạn hoặc không khớp" | Quá mười phút giữa lúc bấm nút và lúc quay về; hoặc quay về ở trình duyệt khác; hoặc đổi giữa `http` và `https` giữa chừng | Bấm lại nút Google trong cùng trình duyệt |
| "Tài khoản Google này chưa liên kết với bút danh nào" | Đúng thiết kế: Google không tạo tài khoản | Đăng nhập bằng bút danh rồi liên kết ở trang Tài khoản |
| "Máy chủ chạy qua https nhưng chưa bật AICEFR_HTTPS_ONLY" | Địa chỉ chuyển hướng là `https` mà chưa bật cờ TLS | Đặt `AICEFR_HTTPS_ONLY=on` rồi khởi động lại |

Tài liệu gốc: Google, "Using OAuth 2.0 for Web Server Applications" (developers.google.com/identity/protocols/oauth2/web-server) và tài liệu discovery `accounts.google.com/.well-known/openid-configuration`.

## 2. Stripe (chế độ thử)

**Đã làm sẵn.** Mở Checkout Session bằng API (VND, mã đơn trong `client_reference_id`), trang trả về đọc lại phiên từ API, webhook kiểm `Stripe-Signature` (HMAC-SHA256, năm phút). Sơ đồ: hình 8 của SDD, mục 4.16.

**Giới hạn cần biết.** Stripe chưa có Việt Nam trong danh sách quốc gia mở được tài khoản bán hàng (stripe.com/global, truy cập 07/10/2026). Ở đây Stripe dùng để **thử luồng** bằng chế độ thử; tài khoản thử không cần kích hoạt để nhận tiền. Đừng khai sai thông tin doanh nghiệp để mở tài khoản thật.

1. Đăng ký tài khoản tại <https://dashboard.stripe.com/register>, ở lại chế độ thử (Sandbox / Test mode).
2. **API keys:** chép **Secret key** dạng `sk_test_…`.
3. **Webhook** — chọn một trong hai:
   - *Máy mình, không có địa chỉ công khai:* cài Stripe CLI, chạy `stripe login`, rồi

     ```bash
     stripe listen --forward-to localhost:8000/api/v1/billing/notify/stripe --events checkout.session.completed,checkout.session.async_payment_succeeded,checkout.session.async_payment_failed,checkout.session.expired
     ```

     Lệnh in ra một khoá `whsec_…`; giữ cửa sổ đó mở trong lúc thử.
   - *Máy chủ có `https`:* Workbench → **Webhooks** → **Create an event destination** → *Your account* → định dạng **Snapshot** (hệ thống đọc cả Checkout Session trong `data.object`; định dạng Thin không dùng được) → chọn bốn sự kiện ở trên → *Webhook endpoint* với địa chỉ `https://<tên-miền-của-bạn>/api/v1/billing/notify/stripe` → chép signing secret `whsec_…`.
4. Điền `.env`:

   ```bash
   AICEFR_BILLING=on
   AICEFR_PAYMENT_GATEWAYS=stripe,sandbox
   AICEFR_STRIPE_SECRET_KEY=sk_test_...
   AICEFR_STRIPE_WEBHOOK_SECRET=whsec_...
   ```

   Thiếu khoá webhook thì Stripe ở chế độ thử vẫn chạy, nhưng tab Gói dịch vụ cảnh báo: đơn chỉ được ghi nhận khi trình duyệt quay về. Khoá `sk_live_` thì bắt buộc có khoá webhook.
5. Thử: tab **Gói dịch vụ** → chọn gói → ở "Thanh toán qua" chọn **Stripe** → **Thanh toán** → trang của Stripe → thẻ `4242 4242 4242 4242`, hạn bất kỳ trong tương lai, CVC bất kỳ → về trang kết quả. Thẻ `4000 0000 0000 0002` cho kết quả bị từ chối.

**Số tiền.** Stripe tính VND bằng đúng số đồng (không nhân 100). Mỗi lần trả phải đạt mức tối thiểu của Stripe — 0,50 USD quy đổi theo tiền tệ thanh toán của tài khoản — nên một khoản nâng cấp rất nhỏ có thể bị từ chối; khi đó tab báo lý do và có thể chọn cổng khác.

Tài liệu gốc: docs.stripe.com/api/checkout/sessions/create, docs.stripe.com/webhooks (mục "Verify webhook signatures manually"), docs.stripe.com/currencies.

## 3. MoMo (môi trường thử)

**Đã làm sẵn.** Tạo giao dịch `captureWallet` ở `/v2/gateway/api/create` ký HMAC-SHA256, kết quả trả về và IPN ký theo thứ tự trường MoMo công bố, IPN được trả lời 204. Mặc định gọi môi trường thử `test-payment.momo.vn`.

1. Đăng ký đối tác với MoMo để nhận thông tin tích hợp môi trường thử: **partner code**, **access key**, **secret key** (theo developers.momo.vn).
2. Điền `.env`:

   ```bash
   AICEFR_BILLING=on
   AICEFR_PAYMENT_GATEWAYS=momo,sandbox
   AICEFR_MOMO_PARTNER_CODE=...
   AICEFR_MOMO_ACCESS_KEY=...
   AICEFR_MOMO_SECRET_KEY=...
   ```

3. IPN: máy chủ của MoMo gọi `https://<tên-miền-của-bạn>/api/v1/billing/notify/momo`. Trên máy mình MoMo không gọi tới được; trang trả về vẫn ghi nhận kết quả có chữ ký khi trình duyệt quay về.
4. Thử bằng ứng dụng MoMo bản thử và tài khoản thử theo tài liệu của MoMo.

**Số tiền.** MoMo nhận mỗi giao dịch từ 1.000 đ đến 50.000.000 đ; ngoài khoảng đó hệ thống báo ngay, không gọi MoMo.

Tài liệu gốc: developers.momo.vn/v3/docs/payment/api/wallet/onetime và mục "Result code".

## 4. VNPay (sandbox)

1. Đăng ký môi trường sandbox của VNPay để nhận **mã website (TMN code)** và **chuỗi bí mật (hash secret)**.
2. Điền `.env`: `AICEFR_PAYMENT_GATEWAYS=vnpay,…`, `AICEFR_VNPAY_TMN_CODE`, `AICEFR_VNPAY_HASH_SECRET`. Không đặt `AICEFR_VNPAY_URL` thì dùng địa chỉ sandbox của VNPay.
3. Khai địa chỉ IPN `https://<tên-miền-của-bạn>/api/v1/billing/notify/vnpay` ở trang quản trị của VNPay.
4. Thử bằng thẻ thử trong tài liệu sandbox của VNPay.

## 5. Kiểm tra cuối

- `tab Cấu hình`: khung Google ghi "Đang bật", không có mục "Cần xem lại".
- `tab Gói dịch vụ`: mỗi cổng muốn dùng có trong ô "Thanh toán qua" với nhãn "Thử"; không có khung "Cấu hình cổng thanh toán cần xem lại".
- `git status` không có `.env`.
