# Triển khai lên AWS EC2, tự động từ GitHub Actions

Hướng dẫn này đưa hệ thống lên một máy EC2 chạy Ubuntu 24.04. Mỗi lần `main` có commit mới và CI xanh, hệ thống tự cập nhật. Máy EC2 được dùng như một VPS, nên phần lớn các bước dùng lại [TRIEN_KHAI_VPS.md](TRIEN_KHAI_VPS.md). Tài liệu này chỉ ghi phần riêng của AWS và phần tự động.

| Tệp | Việc |
| --- | --- |
| [`.github/workflows/deploy.yml`](../../.github/workflows/deploy.yml) | Workflow `Deploy EC2`: sau khi CI xanh trên `main`, runner của GitHub SSH vào EC2, sao lưu, rồi chạy `deploy/vps/deploy.sh` |
| `deploy/vps/*.sh`, `docker-compose.prod.yml`, `deploy/Caddyfile` | Giữ nguyên như trong hướng dẫn VPS |

```
push main ──▶ CI (5 job) ──xanh──▶ Deploy EC2 (ubuntu-latest)
                                        │ ssh + rsync, khoá deploy riêng
                                        ▼
                         EC2: backup.sh ─▶ docker compose up -d --build ─▶ /healthz
```

**Vì sao không dùng self-hosted runner:** repo nộp bài để public. Nếu gắn runner lên EC2, bất kỳ ai mở pull request từ fork cũng có thể chạy lệnh trên máy chủ, nơi đang giữ `.env`, mật khẩu cơ sở dữ liệu và bản ghi âm. Runner của GitHub chạy xong là bị huỷ, còn máy chủ chỉ nhận một khoá SSH dùng riêng cho việc deploy.

## 1. Tạo máy EC2

Dùng tài khoản AWS cá nhân hoặc của trường, không dùng tài khoản công ty. Trên AWS Console, vào **EC2 → Launch instance**:

- **Region:** `ap-southeast-1` (Singapore) là gần Việt Nam nhất.
- **AMI:** *Ubuntu Server 24.04 LTS*, kiến trúc **x86_64**. Ảnh `speech` chưa được thử trên ARM/Graviton.
- **Instance type:** chọn theo phần RAM ở [TRIEN_KHAI_VPS.md mục 1](TRIEN_KHAI_VPS.md#1-chọn-vps):

  | Loại | vCPU / RAM | Dùng cho | Giá tham khảo ở Singapore, chạy cả tháng |
  | --- | --- | --- | --- |
  | `t3.medium` | 2 / 4 GB | demo giao diện, để trống `AICEFR_ASR` | khoảng 40 USD |
  | `t3.large` | 2 / 8 GB | chấm thật bằng Whisper | khoảng 80 USD |
  | `t3.xlarge` | 4 / 16 GB | Whisper, chấm nhanh hơn | khoảng 155 USD |

  Giá chỉ để ước lượng. Xem số chính xác trên trang giá EC2 trước khi tạo máy. Bản free tier (`t3.micro`, 1 GB) không chạy được hệ thống này.

  **Tài khoản gói Free** (tài khoản mới, có credit 100 USD) chỉ cho tạo loại máy *free-tier eligible*, nên không chọn được `t3.large`. Khi đó dùng **`m7i-flex.large`** (2 vCPU, 8 GB, x86, đủ cho Whisper): ở Sydney khoảng 0,12 USD/giờ, tính cả ổ đĩa và IP là khoảng 95 USD/tháng nếu chạy liên tục, trừ vào credit. Xem các loại được phép:

  ```bash
  aws ec2 describe-instance-types --filters Name=free-tier-eligible,Values=true \
    --query 'InstanceTypes[].[InstanceType,MemoryInfo.SizeInMiB]' --output text
  ```

  Tài khoản gói Free cũng có thể chỉ cho dùng một region cố định (ví dụ `ap-southeast-2`, Sydney). `aws login` sẽ báo nếu chọn sai region.
- **Key pair:** tạo một cặp mới (ed25519). Đây là khoá để **bạn** đăng nhập, khác khoá deploy ở bước 5.
- **Network settings → Security group:** mở cho Inbound:
  - `22/tcp` từ `0.0.0.0/0`, vì runner của GitHub không có dải IP cố định. Máy chỉ nhận đăng nhập bằng khoá (xem bước 3).
  - `80/tcp` và `443/tcp` từ `0.0.0.0/0`, để Caddy xin chứng chỉ và phục vụ trang web.
- **Storage:** từ **40 GB gp3**.

Sau khi máy chạy: vào **Elastic IPs → Allocate**, rồi **Associate** địa chỉ đó với máy. Nếu không có Elastic IP, IP công khai sẽ đổi mỗi lần tắt/bật máy, làm hỏng DNS và secret `EC2_HOST`.

Nên đặt một ngưỡng cảnh báo ở **Billing → Budgets** (ví dụ 50 USD/tháng) để tránh bị trừ tiền bất ngờ.

## 2. Trỏ tên miền

Làm như [TRIEN_KHAI_VPS.md mục 2](TRIEN_KHAI_VPS.md#2-trỏ-tên-miền): tạo bản ghi **A** trỏ về Elastic IP. Caddy cần một tên miền thật để xin chứng chỉ Let's Encrypt; địa chỉ `ec2-…amazonaws.com` không dùng được.

Chưa có tên miền thì dùng `sslip.io`: IP `52.64.179.250` có sẵn tên `52-64-179-250.sslip.io`, tự trỏ về IP đó, không cần đăng ký, và Let's Encrypt vẫn cấp chứng chỉ được. Đủ cho demo; khi có tên miền riêng thì đổi `AICEFR_DOMAIN` trong `.env` rồi deploy lại.

## 3. Chuẩn bị máy chủ

Ubuntu trên EC2 **không cho đăng nhập `root`**. Phải vào bằng người dùng `ubuntu`, rồi chạy bootstrap qua `sudo`:

```bash
scp -i ~/.ssh/<khoá-ec2>.pem deploy/vps/bootstrap.sh ubuntu@<IP>:/tmp/
ssh -i ~/.ssh/<khoá-ec2>.pem ubuntu@<IP> sudo bash /tmp/bootstrap.sh
```

Script làm đúng những việc mô tả ở [mục 3 hướng dẫn VPS](TRIEN_KHAI_VPS.md#3-chuẩn-bị-máy-chủ). Có một chỗ khác trên EC2: script chép khoá trong `/root/.ssh/authorized_keys` sang người dùng `aicefr`, nhưng trên EC2 tệp đó chứa khoá kèm lệnh *"Please login as the user ubuntu"*. Vì vậy cần ghi đè bằng khoá của `ubuntu`:

```bash
ssh -i ~/.ssh/<khoá-ec2>.pem ubuntu@<IP> \
  sudo install -m 600 -o aicefr -g aicefr /home/ubuntu/.ssh/authorized_keys /home/aicefr/.ssh/authorized_keys
ssh -i ~/.ssh/<khoá-ec2>.pem aicefr@<IP> 'docker ps && echo OK'
```

Ảnh Ubuntu của AWS mặc định đã tắt đăng nhập bằng mật khẩu. Kiểm tra lại như sau, kết quả phải là `passwordauthentication no`:

```bash
ssh -i ~/.ssh/<khoá-ec2>.pem ubuntu@<IP> sudo sshd -T | grep -i passwordauthentication
```

## 4. Tạo `.env` trên máy chủ

Cho gọn các lệnh sau, thêm vào `~/.ssh/config` trên máy của bạn:

```
Host aicefr-ec2
  HostName <IP>
  User aicefr
  IdentityFile ~/.ssh/<khoá-ec2>.pem
```

Rồi làm như [TRIEN_KHAI_VPS.md mục 4](TRIEN_KHAI_VPS.md#4-tạo-env-trên-máy-chủ), thay `aicefr@<IP>` bằng `aicefr-ec2`. Chỉ đặt `AICEFR_ASR=whisper` khi máy có từ 8 GB RAM.

Bộ model của nhóm (thư mục `aicefr-models`) không có trong git, và workflow không chép nó lên. Compose đọc model từ `AICEFR_MODEL_HOST_DIR`, mặc định là `../aicefr-models`, tức `/srv/aicefr-models` trên máy chủ. Nếu bản triển khai cần model, chép tay một lần:

```bash
ssh -i ~/.ssh/<khoá-ec2>.pem ubuntu@<IP> sudo install -d -m 0750 -o aicefr -g aicefr /srv/aicefr-models
rsync -az ../aicefr-models/ aicefr-ec2:/srv/aicefr-models/
ssh aicefr-ec2 'cd /srv/aicefr-models && sha256sum -c --quiet SHA256SUMS && echo OK'
```

Người dùng `aicefr` không có quyền tạo thư mục trong `/srv`, nên lệnh đầu cần chạy bằng `ubuntu` với `sudo`.

## 5. Khoá deploy cho GitHub Actions

Tạo một cặp khoá **chỉ dùng cho việc deploy**, không đặt passphrase, trên máy của bạn và ngoài thư mục kho mã:

```bash
ssh-keygen -t ed25519 -N "" -C "github-actions-deploy" -f ~/aicefr-deploy
ssh aicefr-ec2 'cat >> ~/.ssh/authorized_keys' < ~/aicefr-deploy.pub
```

Lấy khoá nhận dạng của máy chủ, để runner nhận ra đúng máy chứ không tin bất kỳ máy nào trả lời ở IP đó:

```bash
ssh -i ~/.ssh/<khoá-ec2>.pem ubuntu@<IP> cat /etc/ssh/ssh_host_ed25519_key.pub \
  | awk -v h="<IP>" '{print h, $1, $2}'
```

Kết quả là một dòng dạng `<IP> ssh-ed25519 AAAA…`. Đây là giá trị của secret `EC2_KNOWN_HOSTS`.

## 6. Cấu hình repo trên GitHub

Bước này cần **quyền admin** của repo nộp bài. Nếu không có, nhờ chủ repo làm.

**Settings → Environments → New environment**, đặt tên `production`:

- **Deployment branches and tags:** chọn *Selected branches*, thêm `main`.
- Tuỳ chọn: **Required reviewers**, nếu muốn mỗi lần deploy phải có người bấm duyệt.
- **Environment secrets:**

  | Secret | Giá trị |
  | --- | --- |
  | `EC2_HOST` | Elastic IP, hoặc tên miền ở bước 2 |
  | `EC2_SSH_KEY` | toàn bộ nội dung `~/aicefr-deploy` (khoá **riêng**, kể cả dòng `-----BEGIN…` và `-----END…`) |
  | `EC2_KNOWN_HOSTS` | dòng lấy được ở bước 5. Nếu `EC2_HOST` là tên miền thì thay `<IP>` đầu dòng bằng tên miền đó |
  | `EC2_USER` | không bắt buộc; mặc định `aicefr` |

Sau khi dán xong, xoá `~/aicefr-deploy` khỏi máy, hoặc cất vào trình quản lý mật khẩu. Nếu khoá bị lộ: xoá dòng `github-actions-deploy` trong `/home/aicefr/.ssh/authorized_keys`, rồi làm lại bước 5 và 6.

**Settings → Actions → General → Fork pull request workflows:** bật *Require approval for all external contributors*. Workflow deploy vốn không chạy cho pull request, nhưng nên bật để chặn thêm một lớp.

Khi environment chưa có đủ secret, job `Deploy EC2` vẫn xanh và chỉ ghi một dòng *"Bỏ qua triển khai"*. Vì vậy có thể merge workflow trước khi có máy chủ.

## 7. Lần triển khai đầu

Lần đầu nên chạy tay, để xem trực tiếp quá trình dựng ảnh (5–15 phút). Chọn một trong hai cách:

- trên máy của bạn: `deploy/vps/deploy.sh aicefr-ec2` (dùng mục `aicefr-ec2` trong `~/.ssh/config` ở bước 4);
- trên GitHub: **Actions → Deploy EC2 → Run workflow**, chọn nhánh `main`.

Sau đó làm tiếp [mục 6](TRIEN_KHAI_VPS.md#6-tạo-quản-trị-viên-đầu-tiên) (tạo quản trị viên), [mục 7](TRIEN_KHAI_VPS.md#7-kiểm-tra-toàn-hệ-thống) (kiểm tra toàn hệ thống) và [mục 8](TRIEN_KHAI_VPS.md#8-sao-lưu-định-kỳ) (đặt lịch sao lưu) của hướng dẫn VPS.

## 8. Triển khai tự động

Từ đây, mỗi pull request được merge vào `main` sẽ đi qua các bước sau:

1. CI chạy trên commit mới của `main`.
2. CI xanh thì `Deploy EC2` bắt đầu. CI đỏ thì không có gì xảy ra.
3. Job bỏ qua nếu commit đó không còn là commit mới nhất của `main`. Nhờ vậy, khi hai lần CI xong không theo thứ tự, máy chủ không bị đưa về bản cũ.
4. Job chạy `backup.sh` trên máy chủ, như [mục 9.2](TRIEN_KHAI_VPS.md#9-cập-nhật-phiên-bản). Nếu sao lưu lỗi thì dừng, không deploy.
5. Job chạy `deploy/vps/deploy.sh`: rsync mã, `docker compose up -d --build`, rồi chờ `https://<AICEFR_DOMAIN>/healthz`.

Mỗi lúc chỉ có một lần deploy; lần sau xếp hàng chờ lần trước xong. Muốn deploy lại mà không cần commit mới: **Run workflow** như ở bước 7.

**Quay lại bản trước:** mở pull request `git revert` commit lỗi rồi merge; workflow sẽ deploy bản đã revert. Nếu dữ liệu đã hỏng, làm theo [mục 10](TRIEN_KHAI_VPS.md#10-quay-lại-bản-trước) với bản sao lưu mà job đã tạo ngay trước lần deploy lỗi.

## 9. Tắt máy khi không dùng

- **EC2 → Instance state → Stop**: không tính tiền máy, nhưng vẫn tính ổ EBS (khoảng 4 USD/tháng cho 40 GB) và Elastic IP. Khi **Start** lại, các container tự chạy (`restart: unless-stopped`) với cùng IP.
- Khi máy đang tắt, nếu `main` có commit mới thì job `Deploy EC2` sẽ đỏ vì không SSH được. Bật máy lên rồi bấm **Re-run** là xong.
- **Terminate** sẽ xoá máy cùng ổ đĩa. Trước khi terminate, chép thư mục sao lưu ra ngoài.

## 10. Giới hạn

Giữ nguyên [mục 11 của hướng dẫn VPS](TRIEN_KHAI_VPS.md#11-giới-hạn): chỉ dùng phi thương mại, giữ đăng ký đóng, không thu tiền thật. Ngoài ra:

- Cổng 22 mở cho toàn Internet vì runner của GitHub không có IP cố định. Lớp bảo vệ là đăng nhập chỉ bằng khoá và host key được ghim. Muốn đóng hẳn cổng 22 thì phải chuyển sang AWS SSM với OIDC; workflow này chưa làm phần đó.
- Ảnh Docker được dựng ngay trên máy chủ, không qua registry. Trong lúc dựng, máy chạy chậm hơn, và trên `t3.medium` có thể dùng tới swap.
