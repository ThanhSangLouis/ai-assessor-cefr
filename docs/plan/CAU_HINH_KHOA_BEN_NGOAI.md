# Cài khoá cho dịch vụ bên ngoài: Google, Stripe

> **D075 (01/11/2026):** hệ thống phục vụ một trung tâm, học viên (và giảng viên, cho bản soạn bài bằng AI) mua **gói lượt** qua **Stripe**; không còn gói dịch vụ của trường. VNPay và MoMo đã gỡ khỏi mã: mục 3 và 4 chỉ còn làm lịch sử.

Tài liệu này dành cho người vận hành một bản triển khai: lấy khoá ở đâu, đặt vào đâu, và kiểm tra thế nào là đã đúng. Mã đã làm sẵn cả bốn dịch vụ (D029, D034, D035, D036); **mọi dịch vụ đều tắt cho tới khi có khoá**, và mọi cổng thanh toán mặc định chạy ở môi trường thử của chính nó.

Các bước dưới đây đã được đối chiếu với tài liệu chính thức của Google, Stripe và MoMo ngày 07/10/2026. Giao diện của các trang quản trị đó có thể đổi; khi một nút không còn đúng tên, hãy theo tài liệu gốc ghi ở cuối mỗi mục.

## 0. Ba nguyên tắc

1. **Khoá chỉ nằm trong `.env` hoặc biến môi trường của máy chủ.** Tệp `.env` đã có trong `.gitignore`; sao `.env.example` thành `.env` rồi điền. `demo.sh` tự đọc `.env` nếu có; chạy cách khác thì nạp bằng `set -a; . ./.env; set +a`. Không commit `.env`, không dán client secret hay khoá bí mật vào chat, issue hay ảnh chụp màn hình.
2. **Không có tiền thật trong đồ án.** Cổng thu tiền thật — khoá Stripe `sk_live_`, địa chỉ thật của VNPay hay MoMo — chỉ chạy khi đặt `AICEFR_PAYMENTS_LIVE=on` (khi đó mọi cổng ở môi trường thử tự tắt, để không ai mua gói thật bằng thẻ thử), và việc đó cần một pháp nhân, hợp đồng với cổng, và giải quyết giấy phép dữ liệu huấn luyện (xem `DE_XUAT_GOI_DICH_VU.md`). Trong đồ án, không đặt biến này.
3. **Kiểm tra trên chính ứng dụng.** Sau khi đặt khoá và khởi động lại, đăng nhập bằng tài khoản quản trị: tab **Cấu hình** có khung "Đăng nhập bằng Google", trang **Lượt của tôi** của học viên liệt kê các cổng đang bật; cổng nào còn thiếu khoá thì nhật ký của dịch vụ `core` ghi rõ tên biến, không bao giờ ghi giá trị.

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
   AICEFR_METERING=1
   AICEFR_PAYMENT_GATEWAYS=stripe
   AICEFR_STRIPE_SECRET_KEY=sk_test_...
   AICEFR_STRIPE_WEBHOOK_SECRET=whsec_...
   ```

   Thiếu khoá webhook thì Stripe ở chế độ thử vẫn chạy, nhưng nhật ký cảnh báo: đơn chỉ được ghi nhận khi trình duyệt quay về. Khoá `sk_live_` thì bắt buộc có khoá webhook.
5. Thử: đăng nhập học viên → **Lượt của tôi** → **Mua gói này** → trang của Stripe → thẻ `4242 4242 4242 4242`, hạn bất kỳ trong tương lai, CVC bất kỳ → về trang kết quả. Thẻ `4000 0000 0000 0002` cho kết quả bị từ chối.

**Số tiền.** Stripe tính VND bằng đúng số đồng (không nhân 100). Mỗi lần trả phải đạt mức tối thiểu của Stripe — 0,50 USD quy đổi theo tiền tệ thanh toán của tài khoản — nên gói lượt quá rẻ có thể bị từ chối; khi đó trang báo lý do.

Tài liệu gốc: docs.stripe.com/api/checkout/sessions/create, docs.stripe.com/webhooks (mục "Verify webhook signatures manually"), docs.stripe.com/currencies.

## 2b. Email qua Resend (D079)

**Đã làm sẵn.** Gửi mã 6 số khi quên mật khẩu (dùng được 10 phút, 5 lần thử, mỗi phút gửi một lần), mã xác minh email khi đăng ký và ở trang Tài khoản, và thư nhắc học mỗi tối cho học viên đã xác minh email, chưa luyện trong ngày, đang có chuỗi ngày hoặc bài ôn đến hạn. Mỗi thư nhắc có liên kết tắt nhắc, không cần đăng nhập.

**Cần một tên miền riêng.** Resend chỉ gửi tới mọi địa chỉ khi tên miền của người gửi đã được xác minh. Địa chỉ `sslip.io` hiện tại không xác minh được, vì mình không sửa được DNS của nó. Chưa có tên miền thì Resend chỉ gửi tới chính email chủ tài khoản Resend.

1. Mua tên miền, ví dụ trên Namecheap.
2. Đăng ký tại <https://resend.com/signup>.
3. **Domains → Add domain**: nhập tên miền, nên dùng tên miền con như `mail.ten-mien.app`, vùng *Tokyo (ap-northeast-1)*. Resend hiện các bản ghi DNS (TXT cho SPF và DKIM, MX cho phản hồi).
4. Ở Namecheap: **Domain List → Manage → Advanced DNS → Add new record**. Thêm đúng từng bản ghi Resend đưa (loại, Host, Value). Quay lại Resend bấm **Verify**, thường xong trong vài phút đến vài giờ.
5. **API Keys → Create API Key**: quyền *Sending access*, chỉ cho tên miền vừa xác minh. Chép chuỗi `re_…`; Resend chỉ hiện chuỗi này một lần.
6. Điền `.env` trên máy chủ:

   ```bash
   AICEFR_EMAIL_PROVIDER=resend
   AICEFR_RESEND_API_KEY=re_...
   AICEFR_EMAIL_FROM="AI Assessor CEFR <no-reply@mail.ten-mien.app>"
   AICEFR_PUBLIC_URL=https://ten-mien.app
   AICEFR_REMINDER_HOUR=19
   ```

   `AICEFR_PUBLIC_URL` là địa chỉ người học mở trang web; liên kết trong thư nhắc dùng nó. Thiếu biến này thì hệ thống không gửi thư nhắc (nhật ký ghi lý do), nhưng mã OTP vẫn gửi được.
7. Khởi động lại dịch vụ `core`. Thử: trang **Quên mật khẩu** → nhập email → thư có mã 6 số → đặt mật khẩu mới.

**Gói miễn phí của Resend:** 3.000 thư mỗi tháng, 100 thư mỗi ngày. Mỗi học viên nhận nhiều nhất một thư nhắc mỗi ngày.

Tài liệu gốc: resend.com/docs/api-reference/emails/send-email, resend.com/docs/dashboard/domains/introduction.

## 3. MoMo (đã gỡ bởi D075)

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

## 4. VNPay (đã gỡ bởi D075)

1. Đăng ký môi trường sandbox của VNPay để nhận **mã website (TMN code)** và **chuỗi bí mật (hash secret)**.
2. Điền `.env`: `AICEFR_PAYMENT_GATEWAYS=vnpay,…`, `AICEFR_VNPAY_TMN_CODE`, `AICEFR_VNPAY_HASH_SECRET`. Không đặt `AICEFR_VNPAY_URL` thì dùng địa chỉ sandbox của VNPay.
3. Khai địa chỉ IPN `https://<tên-miền-của-bạn>/api/v1/billing/notify/vnpay` ở trang quản trị của VNPay.
4. Thử bằng thẻ thử trong tài liệu sandbox của VNPay.

## 5. Kiểm tra cuối

- `tab Cấu hình`: khung Google ghi "Đang bật", không có mục "Cần xem lại".
- Trang `Lượt của tôi` (học viên): có các gói lượt và ghi "Môi trường thử"; nhật ký `core` không có dòng "billing: Stripe chưa bật".
- Trang `Quên mật khẩu` có ô "Gửi mã qua email"; thư tới hộp thư trong khoảng một phút.
- `git status` không có `.env`.
