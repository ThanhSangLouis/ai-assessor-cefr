# Triển khai ba dịch vụ — D043, D044

Hướng dẫn chạy hệ thống dưới dạng microservice trên một máy có Docker. Kiến trúc và lý do: SDD mục 4.18, ADR-15, ADR-16. D043 tách sáu dịch vụ; D044 gộp bốn dịch vụ có dữ liệu thành `core`.

## 1. Thành phần

| Container | Ảnh | Việc | Cổng ra ngoài |
| --- | --- | --- | --- |
| `gateway` | nginx 1.27 | Hỏi `core` ai đang gọi, chuyển API tới `core` và trang tới `web` | 8000 |
| `core` | `aicefr-service` | Tài khoản, phiên, Google, đồng thuận; đề, bài nộp, duyệt, chấm mù, thực nghiệm phản hồi; lộ trình, bài học, thành tựu, phát âm; gói dịch vụ, thanh toán | không |
| `web` | `aicefr-service` | Trang và tệp tĩnh; hỏi `core` qua HTTP nội bộ | không |
| `speech` | `aicefr-speech` | QC, nhận dạng (Whisper), đặc trưng, chấm điểm; không giữ khoá nào | không |
| `mongo` | mongo 7.0 | Một database `aicefr`, một người dùng `core` (D048) | không |
| `redis` | redis 7 | Hàng đợi chấm BullMQ (thử lại, ưu tiên, mỗi bài một việc), sự kiện qua Streams, câu hỏi đo bước (D050); bật AOF và `noeviction` | không |

Volume: `uploads` (bản ghi âm — dữ liệu cá nhân; `core` ghi, `speech` chỉ đọc), `models` (cache Whisper), `mongodata`, `redisdata`.

## 2. Chạy lần đầu

1. Sao `.env.example` thành `.env` (git bỏ qua tệp này). Điền `AICEFR_INTERNAL_TOKEN`, `AICEFR_GATEWAY_TOKEN`, `MONGO_ROOT_PASSWORD`, `CORE_DB_PASSWORD`, `REDIS_PASSWORD` bằng chuỗi ngẫu nhiên dài, chỉ chữ và số, mỗi biến một chuỗi khác nhau:

   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

   Thiếu một biến thì `docker compose` dừng và nói tên biến.
2. Dựng và chạy:

   ```bash
   docker compose up -d --build
   ```

   Lần đầu MongoDB chạy `deploy/mongo/init-core-user.js`: tạo người dùng `core` chỉ đọc ghi database `aicefr`. `core` tự tạo collection và chỉ mục khi khởi động.
3. Tạo quản trị viên đầu tiên (mật khẩu nhập kín):

   ```bash
   docker compose exec core python -m aicefr.accounts_cli them --but-danh QT-01 --vai-tro admin
   ```

4. Mở `http://localhost:8000`. Kiểm tra toàn hệ thống:

   ```bash
   python tools/compose_smoke.py
   ```

   Lệnh tạo hai tài khoản thử với mật khẩu ngẫu nhiên, đi qua gateway như trình duyệt và kiểm từng điểm.

## 3. Chấm thật

Mặc định `speech` dùng bộ nhận dạng giả: điểm không có nghĩa và giao diện cảnh báo. Đặt `AICEFR_ASR=whisper` trong `.env` rồi `docker compose up -d speech`; lần đầu tải khoảng 1,5 GB model vào volume `models`. Thêm Silero VAD: `docker compose build --build-arg VAD=1 speech`.

## 4. Vận hành

- **Nhật ký:** `docker compose logs -f core speech`.
- **Redis/BullMQ:** xem hàng đợi bằng `docker compose exec redis sh -c 'redis-cli -a "$REDIS_PASSWORD" --no-auth-warning keys "aicefr:speech.score:*"'`; việc hỏng nằm trong tập `failed` của hàng đợi (giữ 5.000 việc gần nhất).
- **Sao lưu:** `deploy/vps/backup.sh` (`mongodump` trong container `mongo`), cộng volume `uploads`. `maintenance_cli backup` ghi mọi collection ra một tệp JSON, cho kho nhỏ.
- **Lưu trữ có thời hạn:** `docker compose exec core python -m aicefr.maintenance_cli retention --days 180` (xem trước; thêm `--apply` để thực hiện).
- **Nâng từ PostgreSQL (D048):** chưa có dữ liệu thật nào trên PostgreSQL, nên D048 không kèm công cụ chuyển dữ liệu. Volume `pgdata` cũ có thể xoá (`docker volume rm ai-assessor-cefr_pgdata`). `init-core-user.js` chỉ chạy khi volume `mongodata` mới tạo.
- **Cập nhật cấu hình gateway:** sửa bảng định tuyến ở `src/aicefr/platform/gateway.py`, chạy `python tools/gen_gateway.py`; không sửa tay `deploy/gateway/default.conf.template`.

## 5. Bảo mật

- Chỉ gateway mở cổng. Dịch vụ chỉ tin tiêu đề tài khoản `X-Aicefr-Account` khi đi kèm khoá gateway `X-Aicefr-Gateway`; lời gọi nội bộ của `web` tới `core` dùng khoá riêng `X-Aicefr-Internal`. Gateway không bao giờ chuyển tiếp `/internal/`, xoá `X-Aicefr-Internal` do bên ngoài gửi và luôn ghi đè `X-Forwarded-For` bằng địa chỉ nó thấy.
- `speech` không giữ khoá nào và chỉ đọc bản ghi âm.
- Người dùng MongoDB `core` chỉ có vai trò `readWrite` trên database `aicefr`; tài khoản root chỉ dùng để sao lưu.
- Sau TLS: đặt `AICEFR_HTTPS_ONLY=1` và `AICEFR_PUBLIC_URL`.
- Không đưa `.env`, dữ liệu trong volume hay bản sao lưu lên kho mã.

## 6. Một máy, không Docker

Cả ba dịch vụ chạy trong một tiến trình, kho và bus trong tiến trình:

```bash
uvicorn aicefr.api.main:app --reload
```

`AICEFR_DB` (hoặc `AICEFR_CORE_DB`) chọn kho của `core`: một URL `mongodb://…/aicefr` để giữ dữ liệu, hoặc để trống để dùng kho trong bộ nhớ (mất khi tắt; môi trường production từ chối).


## 7. Kho riêng, object storage, giám sát (D051)

- **Database riêng cho từng dịch vụ:** compose mặc định đặt `AICEFR_LEARNING_DB` và `AICEFR_METERING_DB` sang `aicefr_learning` và `aicefr_metering`. Volume `mongodata` tạo trước D051 thì người dùng `core` chưa có quyền trên hai database mới. Chạy lại lệnh `grantRolesToUser` theo `deploy/mongo/init-core-user.js`, hoặc bỏ hai biến này để dùng chung `aicefr`.
- **Object storage:** `docker compose -f docker-compose.yml -f docker-compose.objectstore.yml up -d`, sau khi đặt `S3_ACCESS_KEY` và `S3_SECRET_KEY` trong `.env`. Ghi âm nằm trong bucket `aicefr-audio` của SeaweedFS (volume `objects`). Sao lưu bucket bằng một công cụ S3 (ví dụ `aws s3 sync`), vì `backup.sh` chỉ chép volume `uploads`.
- **Giám sát:** `docker compose -f docker-compose.yml -f docker-compose.observability.yml up -d`, đặt `GRAFANA_PASSWORD`. Grafana mở ở `http://127.0.0.1:3000`, bảng "AI Assessor CEFR — vận hành". Cảnh báo xem ở trang Alerts của Prometheus (bên trong mạng). Có thể ghép cả ba tệp compose.
