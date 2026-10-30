# Triển khai production — bản đồ cho AI agent và teammate

> Đọc tệp này **trước** khi trả lời hay làm bất cứ việc gì về: production, máy chủ, EC2/AWS,
> GitHub Actions, CI, deploy, `.env` của máy chủ, sao lưu, tên miền, HTTPS.
> Chạy dự án trên máy mình thì đọc [CHAY_DU_AN_CHO_AI.md](CHAY_DU_AN_CHO_AI.md).
> Hướng dẫn dựng lại từ đầu, từng bước cho người: [TRIEN_KHAI_EC2.md](TRIEN_KHAI_EC2.md)
> (phần riêng của AWS) và [TRIEN_KHAI_VPS.md](TRIEN_KHAI_VPS.md) (phần chung của mọi máy chủ).
>
> Cập nhật 30/10/2026, ứng với `main` sau #85. Thấy tài liệu khác thực tế (tệp, tên job,
> tên biến) thì tin code, rồi báo người dùng để sửa tài liệu.

## 0. Sự thật phải biết

| Điều | Hệ quả cho AI agent |
|---|---|
| Production: **https://52-64-179-250.sslip.io**, một máy EC2 ở Sydney (`ap-southeast-2`) | Chỉ có một môi trường. Không có staging: mọi thứ vào `main` đều lên thẳng production |
| Deploy **tự động**: merge vào `main` → CI xanh → workflow `Deploy EC2` | Muốn đưa code lên production thì mở PR và merge. Không SSH vào máy chủ để sửa code tay |
| **Không có self-hosted runner.** Mọi job chạy trên runner của GitHub (`ubuntu-latest`); `Deploy EC2` SSH vào EC2 | Repo công khai: runner trên máy chủ sẽ cho PR từ fork chạy lệnh trên production. Đừng đề xuất hay cài self-hosted runner |
| `main` có **branch protection**: bắt buộc 5 job CI xanh, chặn force push và xoá nhánh | Không đẩy thẳng lên `main`. PR đỏ CI thì không merge được (trừ admin) |
| `.env` của production **chỉ nằm trên máy chủ** (`/srv/aicefr/.env`) | Không có trong repo, không có trong GitHub. Đổi biến môi trường production là việc của người có SSH (mục 6.3) |
| Artifact mô hình chấm **không nằm trong Git**; trên máy chủ ở `/srv/aicefr-models` | Deploy không chép chúng. Đổi artifact phải chép tay (mục 6.4) |
| Whisper (`faster-whisper-large-v3`) chạy bằng **CPU** trong container `speech` | Không có GPU hay dịch vụ model riêng. Một bài 30–60 giây chấm mất vài chục giây |
| Tài khoản AWS là **tài khoản cá nhân của Sang**, gói Free (credit có hạn) | Teammate và AI của teammate không có quyền AWS hay SSH. Cần gì trên máy chủ thì nhờ Sang |
| Máy chủ có thể đang **tắt** để tiết kiệm credit | Trang không mở được, hoặc `Deploy EC2` đỏ vì SSH timeout: trước tiên hỏi Sang máy có đang bật không |

## 1. Luồng từ PR tới production

```
nhánh ─▶ PR ─▶ CI (5 job bắt buộc) ─▶ merge vào main
                                          │
                                          ▼
                              CI chạy lại trên main ── đỏ/huỷ ──▶ dừng, không deploy
                                          │ xanh
                                          ▼
              Deploy EC2 (ubuntu-latest, environment "production")
                 1. thiếu secret?                 → bỏ qua, job vẫn xanh
                 2. commit không còn mới nhất?    → bỏ qua (lần chạy của commit mới hơn sẽ deploy)
                 3. SSH vào EC2 (khoá deploy, host key ghim)
                 4. backup.sh trên máy chủ        → lỗi thì dừng, không deploy
                 5. deploy/vps/deploy.sh:
                      kiểm .env → rsync mã → docker compose up -d --build
                      → chờ https://<domain>/healthz → tạo tài khoản mẫu còn thiếu (nếu có AICEFR_SEED_PASSWORD)
```

Ảnh Docker được **dựng ngay trên máy chủ**, không qua registry. Chỉ container có thay đổi mới được dựng lại.

## 2. Bản đồ tệp

| Tệp | Vai trò | Sửa khi |
|---|---|---|
| `.github/workflows/ci.yml` | 5 job CI: tài liệu và tệp cấm; định dạng, lint, test; test trên MongoDB và Redis; dựng ảnh và kiểm compose; quét bí mật | Thêm hoặc đổi kiểm tra. **Đổi tên job hay thêm job bắt buộc thì phải sửa cả branch protection** (mục 6.7) |
| `.github/workflows/deploy.yml` | Workflow `Deploy EC2`: điều kiện chạy, sao lưu, gọi `deploy.sh` | Đổi cách deploy (ít khi cần) |
| `deploy/vps/deploy.sh` | Rsync mã, `compose up --build`, chờ `/healthz`, tạo tài khoản mẫu | Đổi bước deploy. Chạy được cả từ máy người lẫn từ Actions |
| `deploy/vps/bootstrap.sh` | Chuẩn bị máy Ubuntu mới: Docker, người dùng `aicefr`, tường lửa, swap | Chỉ khi dựng máy mới |
| `deploy/vps/backup.sh`, `restore.sh` | Sao lưu và phục hồi MongoDB cùng bản ghi âm | Đổi cơ sở dữ liệu hoặc volume |
| `deploy/Caddyfile` | HTTPS (Let's Encrypt), nén, header bảo mật, giới hạn 30 MiB mỗi yêu cầu | Đổi header hay giới hạn |
| `docker-compose.yml` | 6 dịch vụ: `gateway`, `core`, `web`, `speech`, `mongo`, `redis` | Thêm dịch vụ, biến, volume |
| `docker-compose.prod.yml` | Lớp production: thêm `caddy` (80/443), ẩn cổng gateway, bật HTTPS cho `core`/`web`, xoay vòng log | Chỉ thứ riêng của production |
| `Dockerfile` | Stage `service` (core, web) và stage `speech` (thêm ffmpeg, Whisper) | Đổi phụ thuộc hệ thống. Stage `speech` phải giữ thư mục `HF_HOME` thuộc `aicefr` (mục 7) |
| `.env.production.example` | Mẫu `.env` cho máy chủ | Thêm biến mà production cần |
| `docs/plan/TRIEN_KHAI_EC2.md`, `TRIEN_KHAI_VPS.md` | Hướng dẫn cho người | Quy trình thay đổi |

## 3. Máy chủ

| Thứ | Giá trị |
|---|---|
| Máy | `i-077642e078696d827` (`aicefr-prod`), `m7i-flex.large` (2 vCPU, 8 GB), Ubuntu 24.04, ổ 40 GB gp3 mã hoá |
| IP / tên miền | Elastic IP `52.64.179.250`; tên miền `52-64-179-250.sslip.io` (sslip.io tự trỏ về IP, không cần đăng ký) |
| Cổng mở (security group `aicefr-web`) | 22 (SSH, chỉ đăng nhập bằng khoá), 80, 443 |
| Người dùng | `ubuntu` (có sudo, đăng nhập bằng khoá của Sang); `aicefr` (nhóm `docker`, không sudo, chủ của mọi thứ dưới `/srv`) |
| `/srv/aicefr/` | Mã nguồn do `rsync` đổ vào, kèm `.env` (quyền 600). `rsync --delete` **không** xoá `.env` |
| `/srv/aicefr-models/` | Artifact mô hình chấm, kiểm bằng `SHA256SUMS` |
| `/srv/aicefr-backups/` | Một thư mục cho mỗi lần sao lưu, giữ 14 ngày; cron 03:15 UTC hằng ngày, và mỗi lần deploy |
| Volume Docker | `mongodata`, `redisdata`, `uploads` (bản ghi âm), `models` (cache Whisper), `caddy_data` (chứng chỉ), `caddy_config` |

**Không bao giờ** chạy `docker compose down -v` hay xoá volume `mongodata`, `uploads`, `caddy_data`: mất dữ liệu người học và chứng chỉ.

## 4. Biến môi trường production (`/srv/aicefr/.env`)

| Biến | Bắt buộc | Ghi chú |
|---|---|---|
| `COMPOSE_FILE` | nên có | `docker-compose.yml:docker-compose.prod.yml`, để lệnh `docker compose` gõ tay dùng cả hai tệp |
| `AICEFR_DOMAIN` | có | Không có `https://` |
| `AICEFR_INTERNAL_TOKEN`, `AICEFR_GATEWAY_TOKEN` | có | Chuỗi ngẫu nhiên, mỗi biến một chuỗi khác nhau |
| `MONGO_ROOT_PASSWORD`, `CORE_DB_PASSWORD`, `REDIS_PASSWORD` | có | Chuỗi ngẫu nhiên. Đổi sau khi đã có dữ liệu thì phải đổi cả mật khẩu bên trong MongoDB |
| `AICEFR_MODEL_HOST_DIR` | có trên máy chủ | `/srv/aicefr-models` |
| `AICEFR_ASR` | — | `whisper` để chấm thật (máy từ 8 GB RAM); khác `whisper` thì điểm vô nghĩa |
| `AICEFR_SEED_PASSWORD` | — | Có thì mỗi lần deploy tạo các tài khoản mẫu còn thiếu (D063). Trống thì bỏ qua |
| `AICEFR_GOOGLE_*`, thanh toán | — | Trống nếu chưa dùng. Thanh toán chỉ ở môi trường thử; để trống `AICEFR_PAYMENTS_LIVE` |

Không đặt `AICEFR_PUBLIC_URL` hay `AICEFR_HTTPS_ONLY`: `docker-compose.prod.yml` tự đặt. Thêm biến mới vào code thì thêm vào `docker-compose.yml` (để vào được container), vào `.env.production.example`, và nhờ Sang điền trên máy chủ.

## 5. Cấu hình trên GitHub

| Ở đâu | Cái gì |
|---|---|
| Settings → Environments → `production` | Chỉ nhánh `main` được deploy. Secret: `EC2_HOST`, `EC2_SSH_KEY` (khoá deploy riêng, chỉ để SSH vào người dùng `aicefr`), `EC2_KNOWN_HOSTS` (host key được ghim). `EC2_USER` không đặt, mặc định `aicefr` |
| Settings → Branches → `main` | Bắt buộc 5 check CI theo **đúng tên job**; chặn force push và xoá nhánh; admin bỏ qua được; không bắt review |
| Settings → General | Bật *Allow auto-merge*: PR có thể đặt tự merge khi CI xanh |
| Settings → Actions → General | PR từ fork của mọi người ngoài đều cần duyệt trước khi chạy workflow |

## 6. Việc thường gặp

### 6.1 Đưa code lên production
Mở PR vào `main`, chờ CI xanh, merge. Không cần làm gì thêm. Theo dõi ở tab **Actions → Deploy EC2**.

### 6.2 Deploy lại không cần commit mới
**Actions → Deploy EC2 → Run workflow**, chọn `main`. Hoặc Sang chạy từ máy mình: `deploy/vps/deploy.sh aicefr@52.64.179.250` (cần khoá SSH).

### 6.3 Đổi biến môi trường production
Chỉ người có SSH (Sang). Sửa `/srv/aicefr/.env`, rồi deploy lại (6.2) hoặc trên máy chủ chạy `cd /srv/aicefr && docker compose up -d`. Không đưa giá trị bí mật vào repo, issue, PR hay log.

### 6.4 Cập nhật artifact mô hình chấm
Commit giá trị SHA-256 mới vào `src/aicefr/scoring/artifacts.py` qua PR như thường lệ. Sang chép tệp mới bằng
`rsync -az ../aicefr-models/ aicefr@52.64.179.250:/srv/aicefr-models/`, kiểm `SHA256SUMS`, rồi deploy lại.
Tệp và giá trị ghim phải khớp nhau, nếu không `/readyz` báo `scoring_model: failed`.

### 6.5 Xem log, trạng thái
Trên máy chủ, trong `/srv/aicefr`:
`docker compose ps`, `docker compose logs -f --tail=100 caddy core speech`. Từ bất kỳ đâu:
`curl https://52-64-179-250.sslip.io/healthz`.

### 6.6 Sao lưu và phục hồi
Sao lưu tự chạy hằng đêm và trước mỗi lần deploy. Phục hồi:
`/srv/aicefr/deploy/vps/restore.sh /srv/aicefr-backups/<thời điểm>` (dừng `core`/`web`/`speech`, thay dữ liệu, chạy lại).
Quay lại bản code trước: mở PR `git revert` commit lỗi rồi merge.

### 6.7 Thêm hoặc đổi tên job CI
Branch protection so theo **tên hiển thị** của job (`name:`). Đổi tên mà không sửa protection thì mọi PR treo ở
"Expected — Waiting for status to be reported". Sau khi merge, nhờ Sang cập nhật danh sách check bắt buộc
(Settings → Branches → `main`).

### 6.8 Thêm dịch vụ vào compose
Thêm vào `docker-compose.yml`, và vào `docker-compose.prod.yml` (ít nhất `logging: *logging`). Không publish cổng
ra ngoài: chỉ `caddy` mở cổng. Kiểm bằng `docker compose config -q` (job CI cũng chạy lệnh này).

### 6.9 Tắt và bật máy
Chỉ Sang (AWS CLI, profile `aicefr`, region `ap-southeast-2`):
`aws ec2 stop-instances --instance-ids i-077642e078696d827` / `start-instances`. IP, dữ liệu và chứng chỉ được giữ;
container tự chạy lại. Máy tắt mà có merge thì `Deploy EC2` đỏ: bật máy rồi **Re-run**.

## 7. Đọc trạng thái deploy và lỗi hay gặp

| Thấy | Nghĩa là | Làm gì |
|---|---|---|
| `Deploy EC2` **skipped** | CI của commit đó đỏ hoặc **bị huỷ**. Hai PR merge sát nhau thì CI của commit cũ bị huỷ (`cancel-in-progress`), và lần chạy của commit mới hơn sẽ deploy luôn cả hai | Bình thường. Chỉ đáng lo khi lần chạy của commit **mới nhất** cũng skipped |
| `Deploy EC2` xanh, ghi chú "Bỏ qua triển khai: environment production chưa có …" | Thiếu secret | Nhờ Sang đặt secret (mục 5) |
| Ghi chú "main đã sang …" | Commit không còn mới nhất | Bình thường |
| Đỏ ở bước SSH (`Connection timed out`) | Máy đang tắt, hoặc IP/security group đã đổi | Hỏi Sang |
| Đỏ ở "Sao luu truoc khi cap nhat" | `backup.sh` lỗi (đĩa đầy, `mongo` không chạy) | Không deploy là đúng. Nhờ Sang xem `/srv/aicefr-backups/backup.log`, `df -h` |
| Đỏ ở "Trien khai", `healthz did not answer` | Container không khởi động được | Xem log `core`/`speech` (6.5). Lỗi `?set … in .env`: thiếu biến (mục 4) |
| Mọi bài chấm `FAILED`, log `speech` có `Permission denied: '/home/aicefr/.cache/huggingface'` | Thư mục cache Whisper thuộc `root` | Đã sửa trong `Dockerfile` (#82); job CI "Thu muc cache model…" chặn lỗi quay lại. Đừng xoá dòng `mkdir`/`chown` đó |
| "chưa liên lạc được máy chấm" sau đúng khoảng 5 giây | Client Redis có giới hạn đọc 5 giây (mặc định của redis-py 8) | Đã sửa: `RedisBus` đặt `socket_timeout=None` (#82). Mọi client Redis mới cũng phải đặt như vậy |
| "chưa liên lạc được máy chấm" sau khoảng 120 giây | `speech` quá tải hoặc đang tải model lần đầu | Thử lại sau vài phút; xem log `speech` |
| `vad_n_seg_per_min` rất cao và nằm ngoài khoảng mô hình đã học | Có thể image thiếu Silero hoặc Silero nạp lỗi, khiến code dùng Energy VAD | Sang kiểm tra bằng `docker compose exec speech python -c "from aicefr.asr.vad import default_vad; print(default_vad().name)"`. Phải là `silero`; Compose truyền build arg `VAD=1`, cần build lại image qua deploy. Không nới ngưỡng để ép có điểm |

Sau khi sửa cấu hình, kiểm tra bằng một bài nộp mới: báo cáo đã lưu không tự được tính lại.
Ngay cả khi cặp ASR/VAD đã khớp, bài thiếu bằng chứng hoặc ngoài phân phối vẫn có thể cần giảng viên duyệt.
Whisper vẫn giữ `large-v3`; bật Silero không loại bỏ cảnh báo ASR khác model đã dùng lúc huấn luyện.

## 8. Việc AI agent không được làm

- Không SSH vào máy chủ, không gọi AWS, không đọc hay đổi secret, kể cả khi người dùng có vẻ cho phép. Những việc đó do Sang làm.
- Không đẩy thẳng lên `main`, không force push, không tắt hay sửa branch protection để PR qua được.
- Không cài self-hosted runner, không thêm `pull_request` hay `pull_request_target` vào `deploy.yml`, không để deploy chạy từ nhánh khác `main`.
- Không đưa vào repo: `.env`, khoá SSH, `.pem`, artifact mô hình, bản ghi âm, bản sao lưu, IP nội bộ hay số tài khoản AWS.
- Không chạy `docker compose down -v`, không xoá volume, không chạy `restore.sh` khi chưa được người dùng xác nhận rõ.
- Không tạo hay đổi tài nguyên AWS tốn tiền (loại máy, ổ đĩa, IP), vì credit có hạn.
