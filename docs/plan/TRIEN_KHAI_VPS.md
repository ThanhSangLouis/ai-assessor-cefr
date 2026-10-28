# Triển khai lên một VPS — D047

Hướng dẫn đưa hệ thống lên một máy chủ Ubuntu 24.04 có tên miền và HTTPS. Bộ triển khai gồm:

| Tệp | Việc |
| --- | --- |
| `docker-compose.prod.yml` | Lớp chồng lên `docker-compose.yml`: thêm Caddy (cổng 80, 443), bỏ cổng 8000 của gateway, bật `AICEFR_HTTPS_ONLY=1` và `AICEFR_PUBLIC_URL`, xoay vòng nhật ký mọi container |
| `deploy/Caddyfile` | Caddy: chứng chỉ Let's Encrypt tự động, nén, vài tiêu đề bảo mật, giới hạn 30 MiB mỗi yêu cầu, nhật ký truy cập |
| `deploy/vps/bootstrap.sh` | Chuẩn bị máy chủ mới: Docker, người dùng `aicefr`, tường lửa, cập nhật bảo mật tự động, swap |
| `deploy/vps/deploy.sh` | Chạy trên máy của bạn: chép mã lên máy chủ, dựng và chạy, chờ `/healthz` |
| `deploy/vps/backup.sh`, `restore.sh` | Sao lưu và phục hồi cơ sở dữ liệu cùng bản ghi âm |
| `.env.production.example` | Mẫu `.env` cho máy chủ |

Kiến trúc dịch vụ bên trong không đổi so với `TRIEN_KHAI_DICH_VU.md`; chỉ thêm Caddy đứng trước gateway:

```
Internet ──443──▶ caddy ──▶ gateway (nginx) ──▶ core / web ──▶ mongo, redis, speech
```

## 1. Chọn VPS

- **Hệ điều hành:** Ubuntu 24.04 LTS, 64 bit.
- **RAM:**
  - khoảng **4 GB** đủ khi dùng bộ nhận dạng giả (`AICEFR_ASR` khác `whisper`): chạy thử, demo giao diện; điểm không có nghĩa và giao diện báo như vậy.
  - **từ 8 GB** khi chấm thật bằng Whisper (`AICEFR_ASR=whisper`): riêng container `speech` được phép dùng tới 6 GB.
- **CPU:** từ 2 vCPU; Whisper chạy trên CPU nên càng nhiều nhân, chấm càng nhanh.
- **Ổ đĩa:** từ 40 GB (ảnh Docker khoảng 5 GB, model Whisper 1,5 GB, bản ghi âm và sao lưu 14 ngày).
- Có địa chỉ IPv4 cố định, cho mở cổng 80 và 443.

## 2. Trỏ tên miền

Tạo bản ghi DNS loại **A** cho tên miền (ví dụ `cefr.example.org`) trỏ về địa chỉ IPv4 của VPS. Chờ bản ghi có hiệu lực:

```bash
dig +short cefr.example.org     # phải ra đúng IP của VPS
```

Caddy chỉ xin được chứng chỉ khi tên miền đã trỏ đúng và cổng 80/443 mở từ Internet.

## 3. Chuẩn bị máy chủ

Đăng nhập được bằng khoá SSH vào `root`, rồi từ thư mục kho mã trên máy của bạn:

```bash
scp deploy/vps/bootstrap.sh root@<IP>:/root/
ssh root@<IP> bash /root/bootstrap.sh
```

Script chạy lại bao nhiêu lần cũng được. Nó cài Docker Engine và compose plugin từ kho apt chính thức của Docker; tạo người dùng `aicefr` thuộc nhóm `docker` (chép khoá SSH của `root` sang); tạo `/srv/aicefr` và `/srv/aicefr-backups`; tường lửa `ufw` chỉ mở OpenSSH, 80, 443; bật cập nhật bảo mật tự động; thêm swap 4 GB nếu máy chưa có.

Script không đổi cấu hình SSH. Nên tự tắt đăng nhập bằng mật khẩu (`PasswordAuthentication no` trong `/etc/ssh/sshd_config`) sau khi chắc chắn vào được bằng khoá với người dùng `aicefr`.

## 4. Tạo `.env` trên máy chủ

`.env` chỉ nằm trên máy chủ; `deploy.sh` không bao giờ chép `.env` của máy bạn lên.

```bash
scp .env.production.example aicefr@<IP>:/srv/aicefr/.env
ssh aicefr@<IP>
chmod 600 /srv/aicefr/.env
nano /srv/aicefr/.env
```

Điền:

- `AICEFR_DOMAIN`: tên miền ở bước 2, không có `https://`.
- `AICEFR_INTERNAL_TOKEN`, `AICEFR_GATEWAY_TOKEN`, `MONGO_ROOT_PASSWORD`, `CORE_DB_PASSWORD`, `REDIS_PASSWORD`: mỗi biến một chuỗi ngẫu nhiên **khác nhau**, chỉ chữ và số:

  ```bash
  python3 -c "import secrets; print(secrets.token_hex(32))"
  ```

- `AICEFR_ASR=whisper` khi máy có từ 8 GB RAM; để trống trên máy 4 GB.
- Google, thanh toán: để trống nếu chưa dùng. Thanh toán chỉ dùng môi trường thử (mục 11).

Không cần đặt `AICEFR_PUBLIC_URL` và `AICEFR_HTTPS_ONLY`: `docker-compose.prod.yml` tự đặt `https://<AICEFR_DOMAIN>` và `1` cho `core` và `web`. Dòng `COMPOSE_FILE` trong mẫu giúp mọi lệnh `docker compose` gõ tay trên máy chủ tự dùng cả hai tệp compose.

Lưu một bản `.env` ở nơi an toàn ngoài máy chủ (trình quản lý mật khẩu): mất `MONGO_ROOT_PASSWORD`/`CORE_DB_PASSWORD` thì bản sao lưu vẫn phục hồi được nhưng phải đặt lại mật khẩu người dùng MongoDB.

## 5. Triển khai

Từ thư mục kho mã trên máy của bạn (cần `rsync`, `ssh`, `curl`):

```bash
deploy/vps/deploy.sh aicefr@<IP>            # thư mục mặc định /srv/aicefr
deploy/vps/deploy.sh aicefr@<IP> /srv/aicefr
```

Script:

1. dừng ngay nếu máy chủ chưa có `/srv/aicefr/.env` hoặc `.env` thiếu `AICEFR_DOMAIN`;
2. `rsync` mã nguồn lên, bỏ qua `.git`, `.venv`, `.env`, tệp cơ sở dữ liệu cũ (`*.db`), `data/`, `uploads/`, dữ liệu nghiên cứu (`sandi-*`, `research_data/`…), tệp âm thanh, `graphify-out/` và các tệp sinh ra khi chạy test;
3. chạy `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build --remove-orphans` trên máy chủ;
4. chờ `https://<AICEFR_DOMAIN>/healthz` trả lời (tối đa 5 phút, đổi bằng `WAIT_SECONDS=600`) rồi in địa chỉ.

Lần đầu dựng ảnh mất 5–15 phút. Nếu bật Whisper, lần chấm đầu tiên tải thêm khoảng 1,5 GB model vào volume `models`.

## 6. Tạo quản trị viên đầu tiên

Hệ thống không có đăng ký công khai: mọi tài khoản do quản trị viên tạo. Trên máy chủ:

```bash
ssh aicefr@<IP>
cd /srv/aicefr
docker compose exec core python -m aicefr.accounts_cli them --but-danh QT-01 --vai-tro admin
```

Mật khẩu nhập kín. Sau đó mở `https://<AICEFR_DOMAIN>` và đăng nhập.

## 7. Kiểm tra toàn hệ thống

Chạy trên máy chủ (lệnh cần `docker compose exec` để tạo tài khoản thử):

```bash
cd /srv/aicefr
python3 tools/compose_smoke.py --base-url https://<AICEFR_DOMAIN>
```

Kết quả mong đợi: `18 checks passed.` Lệnh tạo hai tài khoản thử `SV-xxxx`, `QT-xxxx` với mật khẩu ngẫu nhiên không lưu lại; học viên thử bị xoá dữ liệu ở cuối, còn tài khoản quản trị thử vẫn nằm trong danh sách (`accounts_cli liet-ke`). Nên chạy trước khi mời người dùng thật.

Kiểm tra thêm:

```bash
curl -sI https://<AICEFR_DOMAIN>/ | grep -i strict-transport   # có HSTS
curl -sI http://<AICEFR_DOMAIN>/                             # 308 chuyển sang https
```

Thử trên máy của bạn trước khi lên VPS: đặt `AICEFR_DOMAIN=localhost` (Caddy dùng CA nội bộ của nó), rồi `python tools/compose_smoke.py --base-url https://localhost --insecure`. Lưu ý trình duyệt sẽ nhớ HSTS cho `localhost`.

## 8. Sao lưu định kỳ

`deploy/vps/backup.sh` ghi vào `/srv/aicefr-backups/<thời điểm UTC>/`: `db.archive.gz` (mongodump database `aicefr`), `uploads.tar.gz` (volume bản ghi âm) và `SHA256SUMS`; xoá bản cũ hơn 14 ngày (`KEEP_DAYS`). Đặt lịch chạy mỗi đêm dưới người dùng `aicefr`:

```bash
crontab -e
# thêm dòng:
15 3 * * * /srv/aicefr/deploy/vps/backup.sh >>/srv/aicefr-backups/backup.log 2>&1
```

Bản sao lưu là **dữ liệu cá nhân** (giọng nói, bút danh, nhật ký kiểm toán): giữ thư mục ở quyền riêng, chép định kỳ sang một nơi khác có mã hoá. Một bản sao lưu nằm trên cùng ổ đĩa với máy chủ không bảo vệ được khi mất máy.

Phục hồi (dừng `core`, `web`, `speech`, thay cơ sở dữ liệu và toàn bộ bản ghi âm, rồi chạy lại):

```bash
/srv/aicefr/deploy/vps/restore.sh /srv/aicefr-backups/20261014T031500Z
# hỏi xác nhận; thêm --yes để bỏ qua
```

Phục hồi lên máy chủ mới: làm bước 3–5 với `.env` cũ, rồi chép thư mục sao lưu lên và chạy `restore.sh`.

## 9. Cập nhật phiên bản

1. Trên máy của bạn: cập nhật nhánh cần triển khai, chạy test.
2. Sao lưu trước khi cập nhật: `ssh aicefr@<IP> /srv/aicefr/deploy/vps/backup.sh`.
3. `deploy/vps/deploy.sh aicefr@<IP>`: chỉ container có thay đổi được dựng lại.
4. Chạy lại bước 7 nếu bản cập nhật chạm tới luồng chấm điểm, đăng nhập hoặc gateway.
5. Lược đồ cơ sở dữ liệu tự nâng khi `core` khởi động (D045). Xem phiên bản đang dùng: `docker compose exec core python -m aicefr.db_cli status`. Một kho dựng từ D043 (bốn schema cũ) không có vai trò `core`: xem `docs/plan/TRIEN_KHAI_DICH_VU.md` mục 4.

Nhật ký: `docker compose logs -f --tail=100 caddy core speech` (trên máy chủ, trong `/srv/aicefr`). Mỗi container giữ tối đa 3 tệp × 10 MB.

## 10. Quay lại bản trước

- **Chỉ mã thay đổi:** trên máy của bạn `git checkout <commit hoặc tag trước>`, chạy lại `deploy/vps/deploy.sh aicefr@<IP>`, rồi quay về nhánh làm việc.
- **Bản mới đã làm hỏng dữ liệu** (đổi bảng, xoá nhầm): triển khai lại bản cũ như trên, rồi `restore.sh` với bản sao lưu ở bước 9.2. Dữ liệu ghi sau thời điểm sao lưu sẽ mất.
- Không xoá volume `mongodata`, `uploads`, `caddy_data` khi quay lại: `docker compose down` giữ volume; **đừng** thêm `-v`.

## 11. Giới hạn

- **Chỉ dùng phi thương mại.** Mô hình chấm điểm được huấn luyện trên kho Speak & Improve theo giấy phép nghiên cứu: không bán quyền truy cập, không thu phí dịch vụ dựa trên điểm số này.
- **Giữ đăng ký đóng.** Tài khoản chỉ do quản trị viên tạo (`accounts_cli them`); không mở trang đăng ký công khai.
- **Không thu tiền thật.** Stripe chỉ ở chế độ thử (`sk_test_…`), MoMo và VNPay chỉ môi trường thử; để trống `AICEFR_PAYMENTS_LIVE`.
- Một máy chủ, không dự phòng: máy hỏng thì dịch vụ dừng cho tới khi dựng lại từ sao lưu (mục 8).
- Sau Caddy, gateway báo cho các dịch vụ rằng yêu cầu đến bằng http (`X-Forwarded-Proto`). Ứng dụng không dựng địa chỉ tuyệt đối từ đó; cookie và chuyển hướng dựa vào `AICEFR_HTTPS_ONLY` và `AICEFR_PUBLIC_URL`, nên không ảnh hưởng.
