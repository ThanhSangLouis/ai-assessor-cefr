# Chạy dự án — hướng dẫn cho AI agent

> Viết cho AI agent (Claude Code, Codex, Cursor...) mà một thành viên nhóm nhờ
> "chạy project lên". Làm đúng thứ tự, mỗi bước có lệnh kiểm tra và kết quả
> mong đợi. Chưa thấy đúng kết quả thì **dừng, báo người dùng**, đừng đoán sang
> bước sau. Hướng dẫn dài cho người đọc: [CHAY_TREN_LOCALHOST.md](CHAY_TREN_LOCALHOST.md).
>
> Cập nhật 29/10/2026, ứng với `main` sau #81. Mọi lệnh chạy từ thư mục gốc repo.

## 0. Sự thật phải biết trước khi gõ lệnh

| Điều | Hệ quả |
|---|---|
| Dữ liệu nằm trong **MongoDB** (D048). Không còn tệp `aicefr.db` | Không đặt `AICEFR_DB` thì mỗi tiến trình có một kho **trong bộ nhớ riêng**: tài khoản tạo bằng CLI sẽ mất trước khi server mở lên, đăng nhập luôn báo sai mật khẩu. Luôn có MongoDB thật (`demo.sh` tự dựng bằng Docker) |
| Artifact mô hình chấm (`ridge_*.json`, `conformal_*.json`) **không nằm trong repo** (W7-S01, giấy phép Speak & Improve) | Đọc ở `AICEFR_MODEL_DIR`, mặc định `../aicefr-models` (thư mục anh em của repo). Code chỉ nạp tệp có SHA-256 khớp giá trị ghim trong `src/aicefr/scoring/artifacts.py` |
| Máy không có `../aicefr-models` | `demo.sh` tự dùng artifact **giả lập** trong `tests/fixtures/models` và in `CANH BAO`. Web chạy trọn vòng nhưng điểm và band **vô nghĩa**. Muốn điểm thật: xin thư mục `aicefr-models` từ Sang qua kênh riêng |
| Mặc định chép lời bằng engine **giả lập** (`AICEFR_ASR=fake`) | Bản chép lời không phải lời người nói, điểm vô nghĩa. Chấm thật: `AICEFR_ASR=whisper` (mục 4) |
| Repo nộp bài là **công khai** | Không bao giờ commit `aicefr-models/`, `.env`, `uploads/`, tệp ghi âm, số đo suy từ Speak & Improve |

## 1. Kiểm tra máy

```bash
python3 --version        # >= 3.10 (nhóm dùng 3.12)
ffmpeg -version          # phải có; thiếu thì bài ghi âm trên web bị AUDIO_UNSUPPORTED
docker info >/dev/null && echo docker_ok   # Docker phải đang chạy (MongoDB)
git log --oneline -1     # đang ở main mới nhất? nếu không: git checkout main && git pull
ls ../aicefr-models/ridge_resp_v2.json     # có = điểm thật; không có = artifact giả lập
```

Thiếu thứ gì thì báo người dùng cài (macOS: `brew install python@3.12 ffmpeg`,
Docker Desktop; Windows: `winget install Python.Python.3.12 Gyan.FFmpeg`, Docker
Desktop, chạy lệnh trong Git Bash hoặc WSL vì `demo.sh` là bash).

## 2. Cài môi trường Python

```bash
python3.12 -m venv .venv                       # hoặc python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev,vad]"
```

Luôn gọi thẳng `.venv/bin/python` (Windows: `.venv\Scripts\python.exe`), không
dựa vào `activate`. Kiểm tra:

```bash
.venv/bin/python -m pytest -q --no-cov --ignore=tests/e2e -p no:randomly 2>&1 | tail -3
```

Mong đợi: khoảng **1495 passed, 27 skipped, 0 failed**. Test đơn vị chạy trên
kho bộ nhớ và artifact giả lập, không cần MongoDB, mạng hay model. Có `FAILED`
thì dừng và báo, đừng sửa test cho xanh.

## 3. Chạy web (cách chính)

```bash
./demo.sh
```

Script tự làm, theo thứ tự:

1. nạp `.env` nếu có;
2. chưa đặt `AICEFR_DB` thì chạy MongoDB 7 trong Docker: container
   `aicefr-demo-mongo`, cổng `27019`, volume `aicefr-demo-mongo`; đặt
   `AICEFR_DB=mongodb://localhost:27019/aicefr`;
3. tìm artifact ở `AICEFR_MODEL_DIR` (mặc định `../aicefr-models`); không có thì
   chuyển sang `tests/fixtures/models` kèm `AICEFR_MODEL_PINS` và in `CANH BAO`;
4. tạo 4 tài khoản demo, mật khẩu `matkhau123` (đã có thì bỏ qua):
   `SV-001`, `SV-002` (student), `GV-01` (teacher), `QT-01` (admin);
5. chạy `uvicorn aicefr.api.main:app --reload --port 8000`.

Kiểm tra (terminal khác):

```bash
curl -s localhost:8000/readyz
# {"status":"ready","checks":{"database":"ok","scoring_model":"ridge_resp_v2","asr_engine":"fake",...}}
curl -s -o /dev/null -w "%{http_code}\n" -H 'content-type: application/json' \
  -d '{"pseudonym":"SV-001","password":"matkhau123"}' localhost:8000/api/v1/auth/login   # 200
```

Mở http://localhost:8000. Sinh viên phải **đồng ý điều khoản** (`/terms`) trước
khi nộp bài lần đầu; chưa đồng ý thì API trả `TERMS_NOT_ACCEPTED` — đó là hành vi
đúng (D058), không phải lỗi.

## 4. Chấm thật bằng Whisper

```bash
.venv/bin/python -m pip install -e ".[dev,asr,vad]"   # Mac: mlx-whisper; nơi khác: faster-whisper
AICEFR_ASR=whisper ./demo.sh
```

Lần đầu tải model khoảng 1,5 GB (Mac) hoặc 3 GB (Windows/Linux) vào
`~/.cache/huggingface`. Kiểm tra `/readyz` có `"asr_is_real":true`. Điểm chỉ có
nghĩa khi **cả hai**: Whisper thật và artifact thật ở `../aicefr-models`.

Bài phải dài **40–60 giây** (đề P3, P4); dưới 20 giây bị từ chối
(`AUDIO_TOO_SHORT`). Bài chạm hai band trở lên được chuyển giảng viên duyệt
(`REVIEW_REQUIRED`) — với ba ngưỡng band ngoài chưa hiệu chuẩn (D059), đây là
trường hợp thường gặp, không phải lỗi.

Thử nhanh không qua web:

```bash
.venv/bin/python -m aicefr.cli duong/dan/bai.wav --engine whisper --task P3
```

## 5. Ba dịch vụ bằng Docker Compose

Dùng khi cần chạy giống triển khai (gateway, core, web, speech, MongoDB, Redis).

```bash
cp .env.example .env
# Điền 5 biến bắt buộc, mỗi biến một chuỗi ngẫu nhiên:
#   AICEFR_INTERNAL_TOKEN AICEFR_GATEWAY_TOKEN MONGO_ROOT_PASSWORD CORE_DB_PASSWORD REDIS_PASSWORD
python3 -c "import secrets; print(secrets.token_hex(32))"
# Không có ../aicefr-models: bỏ dấu # ở hai dòng AICEFR_MODEL_HOST_DIR / AICEFR_MODEL_PINS giả lập trong .env
docker compose up -d --build
docker compose ps                       # mọi dịch vụ healthy
curl -s localhost:8000/readyz
docker compose exec core python -m aicefr.accounts_cli them --but-danh SV-001 --vai-tro student --mat-khau matkhau123
```

Thiếu biến nào `docker compose` từ chối chạy và nói tên biến đó. Chấm thật:
`AICEFR_ASR=whisper` trong `.env`.

## 6. Kiểm thử đầy đủ như CI

```bash
.venv/bin/ruff format --check src tests tools && .venv/bin/ruff check src tests tools scripts
.venv/bin/python -m pytest -q --ignore=tests/e2e
.venv/bin/python scripts/ci/check_md_links.py && .venv/bin/python scripts/ci/check_forbidden_files.py
```

Test trên MongoDB và Redis thật, và E2E bằng Playwright:

```bash
docker run -d --rm --name aicefr-test-mongo -p 27018:27017 mongo:7
docker run -d --rm --name aicefr-test-redis -p 6380:6379 redis:7-alpine
AICEFR_TEST_MONGO=mongodb://localhost:27018 AICEFR_TEST_REDIS=redis://localhost:6380/0 \
  .venv/bin/python -m pytest --no-cov -m "not e2e and not slow"
.venv/bin/python -m pip install -e ".[dev,e2e]" && .venv/bin/playwright install chromium
AICEFR_TEST_MONGO=mongodb://localhost:27018 .venv/bin/python -m pytest --no-cov tests/e2e
docker stop aicefr-test-mongo aicefr-test-redis     # luôn tắt container thử
```

## 7. Lỗi hay gặp

| Triệu chứng | Nguyên nhân | Cách xử lý |
|---|---|---|
| Đăng nhập báo "bút danh hoặc mật khẩu không đúng" với tài khoản demo | Chạy server không có `AICEFR_DB` (kho bộ nhớ) | Dùng `./demo.sh`, hoặc đặt `AICEFR_DB=mongodb://...` cho **cả** lệnh tạo tài khoản lẫn server |
| `Can Docker dang chay de dung MongoDB` | Docker chưa chạy | Mở Docker Desktop, chạy lại |
| `CANH BAO: khong thay artifact that` | Không có `../aicefr-models` | Bình thường trên máy teammate; xin thư mục từ Sang nếu cần điểm thật. **Không** chép artifact vào repo |
| `/readyz` 503, `scoring_model: failed: SHA-256 ...` | Artifact bị sửa hoặc sai phiên bản | Lấy lại bản gốc; không sửa giá trị ghim trong `artifacts.py` |
| Bài nộp không có điểm, `MODEL_VERSION_MISSING` | Thiếu artifact (chạy uvicorn tay, không qua `demo.sh`) | Đặt `AICEFR_MODEL_DIR`, hoặc dùng `demo.sh` |
| `TERMS_NOT_ACCEPTED` | Chưa đồng ý điều khoản | Vào `/terms` bấm đồng ý |
| `AUDIO_UNSUPPORTED` | Thiếu `ffmpeg` | Cài ffmpeg, mở lại terminal |
| Cổng 8000 hoặc 27019 đã bị chiếm | Server cũ còn chạy | `lsof -iTCP:8000 -sTCP:LISTEN`; đổi cổng Mongo bằng `AICEFR_DEMO_MONGO_PORT` |
| Muốn làm sạch dữ liệu thử | — | `docker rm -f aicefr-demo-mongo && docker volume rm aicefr-demo-mongo && rm -rf uploads/` |

## 8. Việc AI agent không được làm

- Không đẩy thẳng lên `main`: làm trên nhánh, mở PR, chờ CI xanh, người dùng merge.
- Không commit artifact mô hình, `.env`, dữ liệu ghi âm, cơ sở dữ liệu.
- Không đưa lại `src/aicefr/scoring/models/*.json` hay bất kỳ số đo suy từ Speak & Improve vào repo.
- Không "sửa" bằng cách quay về bản cũ của cây mã (như `ff683cc`); nếu `main` không chạy, báo người dùng kèm lỗi.
- Không sửa test hay giá trị ghim SHA cho xanh; báo lỗi thật.
