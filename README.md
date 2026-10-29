# AI Assessor CEFR

Hệ thống AI hỗ trợ đánh giá năng lực nói tiếng Anh theo khung CEFR (A1–C2, D059) cho sinh viên đại học Việt Nam, phục vụ học tập và hỗ trợ giảng viên duyệt bài.

> **Lưu ý:** Đây là công cụ hỗ trợ học tập, không phải công cụ cấp chứng chỉ tự động. Giảng viên là người quyết định cuối cùng.

---

## Kiến trúc hệ thống (Tuần 7)

Từ Tuần 7 (D043, D044, D048, D050, D051), hệ thống được cấu trúc thành ba dịch vụ chính sau Nginx Gateway:

1. **`core`**: Quản lý định danh (tài khoản, phiên, Google OAuth PKCE, đồng thuận), bài nộp và đánh giá, duyệt bài, chấm mù kép, lộ trình học tập, tính lượt (NetID IDPoint) và thanh toán gói dịch vụ. Kho dữ liệu MongoDB (`aicefr`, `aicefr_learning`, `aicefr_metering`).
2. **`speech`**: Xử lý âm thanh độc lập (QC, VAD Silero/Energy, Whisper ASR, trích xuất đặc trưng, Ridge Scorer, Trust Layer conformal). Nhận việc qua Redis BullMQ và phát kết quả qua Redis Streams. Không giữ khoá hay lưu trữ người dùng.
3. **`web`**: Giao diện người dùng Jinja2, tệp tĩnh, BFF (Backend-for-Frontend) kết nối tới `core` qua HTTP nội bộ.

---

## Bắt đầu nhanh

### Yêu cầu môi trường
- Python 3.11+
- MongoDB 7.0+ (hoặc chạy qua Docker Compose)
- Redis 7+ (hoặc chạy qua Docker Compose)
- Docker & Docker Compose (cho triển khai ba dịch vụ)

### Cài đặt thư viện

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev,services]'
```

### Chạy bằng Docker Compose (Khuyến nghị)

Khởi động toàn bộ stack ba dịch vụ (`gateway`, `core`, `speech`, `web`, `mongodb`, `redis`):

```bash
docker compose up -d
```

Mở trình duyệt: `http://localhost:8000/login`

### Chạy cục bộ (Development)

Chạy kịch bản khởi tạo và máy chủ cục bộ:

```bash
./demo.sh
```

Hoặc chạy lệnh trực tiếp:

```bash
# 1. Chạy di trú dữ liệu
python -m aicefr.cli db migrate

# 2. Tạo tài khoản thử nghiệm
python -m aicefr.accounts_cli them --but-danh SV-001 --vai-tro student --mat-khau matkhau123
python -m aicefr.accounts_cli them --but-danh GV-01  --vai-tro teacher --mat-khau matkhau123
python -m aicefr.accounts_cli them --but-danh QT-01  --vai-tro admin   --mat-khau matkhau123

# 3. Khởi động ứng dụng
python -m aicefr.cli serve --port 8000
```

---

## Quản lý tài khoản (CLI)

Hệ thống **không cho phép tự đăng ký tự do**: mỗi tài khoản được cấp bởi quản trị viên hoặc tích hợp qua mã lớp/NetID để bảo đảm phân quyền chặt chẽ.

```bash
# Xem danh sách tài khoản
python -m aicefr.accounts_cli liet-ke

# Đổi mật khẩu
python -m aicefr.accounts_cli doi-mat-khau --but-danh SV-001 --mat-khau-moi MatKhauMoi456

# Khoá / Mở khoá tài khoản
python -m aicefr.accounts_cli khoa --but-danh SV-001
python -m aicefr.accounts_cli mo-khoa --but-danh SV-001
```

---

## Kiểm tra chất lượng & CI

Trước khi push hoặc tạo PR, chạy các kiểm tra tuân thủ:

```bash
# 1. Kiểm tra file bị cấm (audio *.wav, model weights *.json, .env, *.db)
python3 scripts/ci/check_forbidden_files.py

# 2. Kiểm tra liên kết Markdown
python3 scripts/ci/check_md_links.py

# 3. Chạy kiểm thử tự động
pytest -m "not e2e" -q
```

---

## Tài liệu tham chiếu

- [Kế hoạch Tuần 7](docs/plan/week-07.md)
- [Đặc tả yêu cầu phần mềm (SRS v1.11, FR-01..FR-90)](docs/srs/SRS.md)
- [Thiết kế kiến trúc hệ thống (SDD tổng)](docs/sdd/SDD.md)
- [Nhật ký quyết định kiến trúc (D001–D057)](docs/sources/research-preparation/21_week1_decision_log.md)
- [Kiểm kê tài sản W7](docs/evidence/w7-migration/kiem-ke.md)
- [Quy tắc bảo mật và quản lý agent](AGENTS.md)
