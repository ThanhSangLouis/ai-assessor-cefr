# Chạy hệ thống trên máy mình — hướng dẫn từ số không

> Viết cho người vừa clone repo về, **chưa cài gì, chưa tải model nào**.
> Làm theo đúng thứ tự. Mỗi bước có một lệnh kiểm tra: chưa thấy đúng kết quả
> mong đợi thì đừng sang bước sau, vì lỗi ở bước sau sẽ khó đoán hơn nhiều.
>
> Nếu bạn chỉ cần xem giao diện và không cần chấm điểm thật, bạn **không phải
> tải model nào cả** — nhảy thẳng tới [Chặng A](#chặng-a--chạy-được-web-trong-10-phút-không-cần-model).
> Model chỉ cần cho [Chặng B](#chặng-b--chấm-điểm-thật-bằng-whisper).

---

## 0. Mất bao lâu, tốn bao nhiêu dung lượng

| Chặng | Làm được gì | Thời gian | Dung lượng |
|---|---|---|---|
| A | Web chạy, đăng nhập, nộp bài, xem báo cáo — nhưng bản chép lời là **giả lập** | ~10 phút | ~600 MB (thư viện Python) |
| B | Chấm điểm thật bằng Whisper trên giọng nói thật | thêm ~20 phút | thêm ~1,5 GB (Mac) hoặc ~3 GB (Windows/Linux) |
| C | Chạy bằng Docker, không đụng gì tới máy | ~15 phút | ~2 GB ảnh |

Chặng A đủ để làm phần lớn việc: sửa giao diện, sửa API, chạy test, xem luồng
duyệt bài của giảng viên. Chỉ khi nào bạn cần nghe máy chấm **giọng thật** thì
mới cần chặng B.

---

## 1. Cài sẵn trên máy (trước mọi thứ khác)

Cần bốn thứ: **Python 3.10 trở lên** (nhóm đang dùng 3.12), **git**,
**ffmpeg** và **Docker** (Docker Desktop trên macOS/Windows). Docker dùng để chạy
MongoDB: từ D048 hệ thống lưu dữ liệu trong MongoDB, không còn tệp `aicefr.db`.

`ffmpeg` không phải thư viện Python, phải cài ở mức hệ điều hành. Nó là bắt
buộc chứ không phải tùy chọn: trình duyệt ghi âm ra định dạng WebM/Opus, mà
`soundfile` không đọc được WebM. Thiếu `ffmpeg` thì mọi bài ghi âm trực tiếp
trên web đều bị trả về `AUDIO_UNSUPPORTED` (quyết định QD-06).

### macOS

```bash
# Nếu chưa có Homebrew, cài trước:
# /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install python@3.12 ffmpeg
```

### Windows

Dùng PowerShell:

```powershell
winget install Python.Python.3.12
winget install Gyan.FFmpeg
```

Sau khi cài xong **phải mở lại cửa sổ terminal**, nếu không `PATH` chưa cập
nhật và `ffmpeg` vẫn báo không tìm thấy.

### Ubuntu / Debian

```bash
sudo apt update && sudo apt install -y python3.12 python3.12-venv ffmpeg git
```

### Kiểm tra — bắt buộc thấy cả hai dòng

```bash
python3 --version     # Python 3.12.x (hoặc >= 3.10)
ffmpeg -version       # ffmpeg version ...
```

Nếu `ffmpeg` báo *command not found*, dừng ở đây và xử lý xong hẵng đi tiếp.
Trên Windows lỗi này gần như luôn là do chưa mở lại terminal.

---

## 2. Lấy mã nguồn

```bash
git clone git@github.com:thanglb2005/ai-assessor-cefr.git
cd ai-assessor-cefr
```

Nếu chưa cài khóa SSH cho GitHub thì dùng HTTPS:

```bash
git clone https://github.com/thanglb2005/ai-assessor-cefr.git
```

Kho là **riêng tư**, nên GitHub sẽ hỏi tài khoản. Bạn phải được thêm vào kho
trước đó; nếu bị từ chối quyền, nhắn Sang thêm tài khoản bạn vào.

---

## Chặng A — chạy được web trong 10 phút, không cần model

### A.1. Tạo môi trường ảo riêng cho dự án

Đừng cài thẳng vào Python hệ thống. Môi trường ảo là một thư mục `.venv` nằm
trong dự án, xoá đi làm lại được, và không ảnh hưởng tới máy.

```bash
python3.12 -m venv .venv
```

Từ giờ trở đi hướng dẫn này **luôn gọi thẳng** `.venv/bin/python` thay vì
`activate`. Lý do rất thực tế: quên `activate` là nguồn gốc của khoảng một nửa
số lỗi kiểu "máy tôi chạy được mà máy bạn không chạy". Gọi thẳng thì không bao
giờ nhầm.

Trên Windows đường dẫn là `.venv\Scripts\python.exe` (dấu `\`, có `.exe`,
thư mục là `Scripts` chứ không phải `bin`). Mọi lệnh bên dưới cứ đổi tương ứng.

### A.2. Cài thư viện

```bash
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev,vad]"
```

Giải thích mấy thứ dễ gây thắc mắc:

- `-e` là **editable**: gói trỏ thẳng vào thư mục `src/`, nên bạn sửa mã là có
  hiệu lực ngay, không phải cài lại.
- `[dev]` kéo theo pytest, ruff, httpx2 — cần để chạy test.
- `[vad]` kéo theo `silero-vad` và `torch`. Đây là phần **nặng nhất** của bước
  này (torch khoảng 300–800 MB tùy nền tảng), và nó là bắt buộc: các đặc trưng
  ngừng nghỉ — thứ quan trọng nhất của tiêu chí Fluency — được tính bằng VAD
  Silero. Tin tốt là **trọng số Silero nằm sẵn trong gói pip (~11 MB), không
  phải tải model gì thêm.**
- Chưa cần `[asr]` ở chặng này.

Bước này mất 3–8 phút tùy mạng. Nhìn thấy `Successfully installed ...` là xong.

### A.3. Chạy kiểm thử — đây mới là bằng chứng cài đúng

```bash
.venv/bin/python -m pytest -q
```

Phải thấy khoảng **1500 passed** (ngày 29/10/2026). Nếu số test khác đi mà vẫn
xanh hết thì cũng không sao — nghĩa là mã đã đi tiếp từ lúc tài liệu này viết. Điều quan trọng là
**không có dòng FAILED nào**.

Bộ test này chạy hoàn toàn bằng ASR giả lập và artifact mô hình giả lập
(`tests/fixtures/models`), không cần mạng, không cần MongoDB, không cần model.
Nó xanh tức là môi trường Python của bạn đã đúng.

### A.4. Chạy web

```bash
./demo.sh
```

Script tự làm ba việc rồi mới mở máy chủ:

1. **MongoDB:** nếu bạn chưa đặt `AICEFR_DB`, script chạy MongoDB 7 trong Docker
   (container `aicefr-demo-mongo`, cổng 27019, dữ liệu giữ trong volume
   `aicefr-demo-mongo`). Docker chưa chạy thì script dừng và báo.
2. **Artifact mô hình chấm:** đọc ở thư mục `../aicefr-models` (cạnh thư mục
   repo). Chưa có thư mục này thì script **dùng artifact giả lập** của bộ test và
   in cảnh báo: web chạy trọn vòng nhưng điểm và band **vô nghĩa**. Xem mục
   [Lấy artifact mô hình thật](#lấy-artifact-mô-hình-thật).
3. **Tài khoản demo:** tạo bốn tài khoản (mật khẩu đều là `matkhau123`); chạy lại
   script thì tài khoản đã có được giữ nguyên:

| Bút danh | Vai trò | Dùng để xem |
|---|---|---|
| `SV-001` | student | màn nộp bài, báo cáo của chính mình |
| `SV-002` | student | kiểm tra sinh viên A **không** xem được bài sinh viên B |
| `GV-01` | teacher | hàng đợi duyệt bài, khóa bài, sửa điểm |
| `QT-01` | admin | trang quản trị, thống kê, nhật ký kiểm toán |

Mở http://localhost:8000, đăng nhập `SV-001` / `matkhau123`.

Nếu bạn muốn chạy tay thay vì qua script:

```bash
.venv/bin/uvicorn aicefr.api.main:app --reload --port 8000
```

### Lấy artifact mô hình thật

Mô hình chấm là thống kê suy ra từ Speak & Improve Corpus 2025. Giấy phép cấm
công bố, nên artifact **không nằm trong repo nào** (W7-S01) — repo nộp bài là
công khai. Xin Sang thư mục `aicefr-models` qua kênh riêng của nhóm, đặt cạnh
thư mục repo:

```
Project/
├── ai-assessor-cefr/      ← repo
└── aicefr-models/         ← ridge_resp_v2.json, conformal_resp_v2.json, ...
```

Code chỉ nạp tệp có SHA-256 khớp giá trị ghim trong
`src/aicefr/scoring/artifacts.py`. **Không** commit thư mục này, không chép các
tệp `*.json` của nó vào repo.

### A.5. Kiểm tra hệ thống tự báo là sẵn sàng

Mở một terminal thứ hai, để nguyên terminal đang chạy server:

```bash
curl -s localhost:8000/readyz | python3 -m json.tool
```

`/readyz` kiểm tra ba thứ âm thầm làm hệ thống vô dụng: cơ sở dữ liệu ghi được,
nạp được tệp mô hình chấm điểm, và bộ nhận dạng gọi được. Trả về `503` nghĩa là
có ít nhất một thứ hỏng — đọc trường nào ghi `failed:` để biết thứ nào.

### A.6. Thử một vòng đầy đủ

1. Đăng nhập `SV-001`, chọn một đề, bấm ghi âm (trình duyệt sẽ xin quyền
   micro — phải cho phép), nói **40–60 giây** rồi nộp.
   Đừng nói ngắn hơn 20 giây: hệ thống sẽ từ chối thẳng với mã
   `AUDIO_TOO_SHORT`, đó là hành vi đúng theo SRS chứ không phải lỗi.
2. Trang tiến trình sẽ tự nhảy sang báo cáo.
3. Đăng xuất, đăng nhập `GV-01`, vào `/review` để xem bài vừa nộp nếu nó bị
   đẩy sang hàng đợi duyệt.

**Ở chặng A bản chép lời là giả lập, nên điểm số vô nghĩa.** Đừng hoảng khi
thấy bản chép lời không giống lời bạn nói — đó là engine `fake`, cố tình như
vậy để chạy nhanh và không cần mạng.

---

## Chặng B — chấm điểm thật bằng Whisper

Đây là phần cần tải model. Đọc hết mục này trước khi gõ lệnh, vì lựa chọn
backend phụ thuộc vào máy bạn.

### B.1. Máy nào dùng backend nào

Mã tự chọn backend theo nền tảng, bạn không phải khai báo gì:

| Máy | Backend | Model mặc định | Dung lượng tải |
|---|---|---|---|
| Mac Apple Silicon (M1–M4) | `mlx-whisper`, chạy trên Metal | `mlx-community/whisper-small-mlx` | ~0,5 GB |
| Windows / Linux / Mac Intel | `faster-whisper` (CTranslate2) | `small` | ~0,5 GB |

Model mặc định là **Whisper small**: đúng bộ nhận dạng mô hình chấm đã học (D066). Model lớn hơn không chấm đúng hơn mà làm lệch đặc trưng `asr_conf_mean` và chậm hơn khoảng 5 lần.

### B.2. Cài thêm gói ASR

```bash
.venv/bin/python -m pip install -e ".[dev,asr,vad]"
```

Khai báo trong `pyproject.toml` đã tự phân nhánh theo hệ điều hành, nên cùng
một lệnh này cài `mlx-whisper` trên Mac và `faster-whisper` ở nơi khác.

### B.3. Tải model **trước**, đừng để lần nộp bài đầu tiên tải

Nếu không tải trước, lần nộp bài đầu tiên sẽ đứng im vài phút trong lúc tải
khoảng 0,5 GB, và rất dễ bị hiểu nhầm thành treo máy.

**Trên Mac (Apple Silicon):**

```bash
.venv/bin/python -c "
from huggingface_hub import snapshot_download
p = snapshot_download('mlx-community/whisper-small-mlx')
print('Da tai xong ve:', p)
"
```

**Trên Windows / Linux:**

```bash
.venv/bin/python -c "
from faster_whisper import WhisperModel
WhisperModel('small', device='cpu', compute_type='int8')
print('Da tai xong')
"
```

Model nằm trong `~/.cache/huggingface/hub/` (Windows:
`C:\Users\<tên>\.cache\huggingface\hub\`). Nó **nằm ngoài dự án**, nên xoá
`.venv` hay clone lại repo không làm mất model — tải một lần dùng mãi.

Kiểm tra đã có model:

```bash
du -sh ~/.cache/huggingface/hub/*whisper*
```

### B.4. Chạy ở chế độ thật

```bash
AICEFR_ASR=whisper ./demo.sh
```

Trên Windows PowerShell:

```powershell
$env:AICEFR_ASR="whisper"; .\.venv\Scripts\uvicorn aicefr.api.main:app --port 8000
```

Bài đầu tiên sau khi khởi động sẽ chậm hơn hẳn (nạp model vào bộ nhớ, khoảng
10–30 giây). Các bài sau nhanh hơn nhiều vì model được nạp một lần và dùng lại.

Thời gian chấm tham khảo cho một bài 60 giây: khoảng 15–40 giây trên Mac M-series,
lâu hơn đáng kể nếu chạy CPU thuần.

### B.5. Điều bắt buộc phải biết trước khi nhìn điểm

Mô hình hồi quy được huấn luyện trên đặc trưng trích từ Whisper **small**, và
hệ thống mặc định chạy đúng model đó (D066). Đổi `AICEFR_WHISPER_MODEL` sang
model khác (large-v3, large-v3-turbo…) thì báo cáo có mã `ASR_VERSION_MISMATCH`
và bị đẩy sang giảng viên: model khác làm lệch `asr_conf_mean`, đặc trưng có hệ
số lớn nhất, nên điểm đổi vì lý do không liên quan tới người nói. Đó là hành vi
cố ý, không phải lỗi cài đặt.

Muốn so một model khác với small (chỉ để so sánh, không chạy production):

```bash
.venv/bin/python tools/compare_asr.py bai1.wav bai2.webm --models small large-v3 --labels diem_gv.csv
```

Công cụ chạy đủ pipeline với từng model, in thời gian, điểm, band, lý do chuyển
giảng viên, `asr_conf_mean`, độ lệch bản chép và (khi có `--labels` gồm cột
`file,score` là điểm giảng viên) sai số tuyệt đối trung bình so với giảng viên.
Chỉ dùng bản ghi không có dữ liệu cá nhân hoặc đã được đồng ý; không commit bản ghi.

---

## Chặng C — cách khác: chạy bằng Docker

Dùng khi bạn không muốn cài Python và ffmpeg lên máy, hoặc khi cài mãi không
được.

Trước tiên chép `.env.example` thành `.env` và điền năm biến bắt buộc của phần
dịch vụ (`AICEFR_INTERNAL_TOKEN`, `AICEFR_GATEWAY_TOKEN`, `MONGO_ROOT_PASSWORD`,
`CORE_DB_PASSWORD`, `REDIS_PASSWORD`; mỗi biến một chuỗi ngẫu nhiên, ví dụ
`python3 -c "import secrets; print(secrets.token_hex(32))"`). Thiếu biến nào
`docker compose` từ chối chạy và nói tên biến đó. Chưa có `../aicefr-models` thì
bỏ dấu `#` ở hai dòng artifact giả lập trong `.env`.

```bash
docker compose up --build
```

Mở http://localhost:8000. Container chạy bằng người dùng không phải root và có
sẵn `HEALTHCHECK` trỏ vào `/readyz`.

Đổi lại: **model không nằm trong ảnh**. Lần chạy thật đầu tiên container sẽ tải
model, và nếu bạn không gắn volume cho thư mục cache thì xoá container là mất,
lần sau tải lại từ đầu.

Tạo tài khoản bên trong container:

```bash
docker compose exec app python -m aicefr.accounts_cli them \
  --but-danh SV-001 --vai-tro student
```

---

## 3. Việc hay phải làm

### Tạo thêm tài khoản

```bash
.venv/bin/python -m aicefr.accounts_cli them --but-danh SV-003 --vai-tro student
```

Bỏ `--mat-khau` thì CLI hỏi kín, mật khẩu không lọt vào lịch sử lệnh. Vai trò
hợp lệ: `student`, `teacher`, `admin`.

Quy tắc bắt buộc: bút danh **không được** là họ tên thật hay MSSV. Đây là yêu
cầu bảo vệ dữ liệu cá nhân (FR-33), không phải quy ước đặt tên cho đẹp.

`validate_pseudonym` chặn được: ký tự ngoài `A-Z a-z 0-9 - _`, độ dài ngoài
khoảng 2–32, các chuỗi `mssv` `cmnd` `cccd` `sdt` `phone`, và dãy thuần số dài
7–12 chữ số. Nó **không** đoán được `vothanhsang` là tên người — phần đó là
trách nhiệm của bạn khi đặt bút danh. Cứ theo mẫu `SV-001`, `GV-01` cho chắc.

```bash
.venv/bin/python -m aicefr.accounts_cli liet-ke              # xem có những ai
.venv/bin/python -m aicefr.accounts_cli mo-khoa --but-danh SV-001   # gỡ khóa khi nhập sai nhiều lần
```

### Làm lại từ đầu khi dữ liệu thử rối

```bash
docker rm -f aicefr-demo-mongo && docker volume rm aicefr-demo-mongo && rm -rf uploads/
./demo.sh
```

An toàn: dữ liệu MongoDB nằm trong volume Docker, còn `uploads/` đã nằm trong
`.gitignore`; cả hai **không bao giờ** được đẩy lên git — chúng chứa file ghi âm giọng nói, là dữ liệu cá nhân theo
Luật 91/2025/QH15.

### Trước mỗi lần push

```bash
.venv/bin/ruff format --check src tests tools && .venv/bin/ruff check src tests tools
.venv/bin/python -m pytest -q --ignore=tests/e2e
```

Định dạng, lint và toàn bộ test đơn vị — đúng những gì CI chạy trên mỗi PR.
Đẩy thẳng lên `main` thì CI chỉ báo đỏ sau khi đã muộn: luôn đi qua PR.

### Các biến môi trường hay dùng

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `AICEFR_ASR` | `fake` | `whisper` để chấm thật |
| `AICEFR_WHISPER_MODEL` | theo nền tảng | đổi sang model nhỏ hơn cho nhanh |
| `AICEFR_DB` | `demo.sh` tự đặt `mongodb://localhost:27019/aicefr` | địa chỉ MongoDB; một đường dẫn tệp nghĩa là kho trong bộ nhớ, mất khi tắt tiến trình |
| `AICEFR_MODEL_DIR` | `../aicefr-models` | thư mục artifact mô hình chấm (ngoài Git) |
| `AICEFR_UPLOADS` | `uploads` | thư mục chứa file ghi âm |
| `AICEFR_MAX_UPLOAD` | 25 MiB | giới hạn kích thước tệp |
| `AICEFR_JOB_MODE` | `threadpool` | `inline` để chấm đồng bộ, tiện gỡ lỗi |
| `AICEFR_MAX_JOBS` | 2 | số bài chấm song song |

Muốn gỡ lỗi một bài cụ thể, `AICEFR_JOB_MODE=inline` là thứ đáng dùng nhất:
bài được chấm ngay trong request, nên lỗi hiện thẳng ra thay vì chìm trong
luồng nền.

---

## 4. Lỗi thường gặp

**`ffmpeg: command not found` / mọi bài ghi âm đều `AUDIO_UNSUPPORTED`**
Chưa cài ffmpeg, hoặc trên Windows là chưa mở lại terminal sau khi cài.
Quay lại mục 1.

**`ModuleNotFoundError: No module named 'aicefr'`**
Bạn đang chạy bằng Python hệ thống chứ không phải `.venv`. Gọi thẳng
`.venv/bin/python ...` như trong hướng dẫn.

**`ModuleNotFoundError: No module named 'silero_vad'`**
Cài thiếu nhóm phụ thuộc. Chạy lại `pip install -e ".[dev,vad]"` — chú ý phải
có dấu nháy quanh `".[dev,vad]"`, nếu không `zsh` sẽ hiểu `[` là ký tự đại diện
và báo `no matches found`.

**Trình duyệt không cho ghi âm**
Micro chỉ được cấp quyền trên ngữ cảnh bảo mật. `http://localhost` được tính là
an toàn, nhưng `http://192.168.x.x` thì **không** — mở bằng `localhost`.

**Nộp bài xong đứng mãi ở trang tiến trình (lần đầu, chế độ whisper)**
Model đang được tải hoặc nạp. Xem terminal chạy server; nếu có thanh tiến trình
tải thì cứ đợi. Tránh bằng cách tải trước ở bước B.3.

**Điểm ra nhưng báo cáo ghi `REVIEW_REQUIRED`**
Thường là bình thường, không phải hỏng. Đọc mã lý do trong báo cáo. Ba mã hay
gặp nhất: `ASR_VERSION_MISMATCH` (giải thích ở B.5), `SCORE_NEAR_BOUNDARY`
(điểm sát ranh giới hai band nên hệ thống không dám tự quyết),
`ASR_LOW_CONFIDENCE` (bộ nhận dạng không chắc về lời nói).

**Bản chép lời lặp một từ hàng trăm lần**
Đó là hiện tượng ảo giác của Whisper trên đoạn im lặng dài. Hệ thống đã có bộ
phát hiện và sẽ gắn cờ `ASR_HALLUCINATION`. Nếu gặp thường xuyên, kiểm tra micro
— thường là do thu được quá nhiều im lặng hoặc mức thu quá nhỏ.

**Test hỏng ở `test_diagrams.py`**
Bạn vừa đổi tên một lớp mà chưa cập nhật sơ đồ trong `docs/sdd/diagrams/`, hoặc
ngược lại. Test này cố ý bắt lỗi lệch giữa tài liệu và mã.

---

## 5. Đọc gì tiếp

| File | Khi nào cần |
|---|---|
| `docs/srs/SRS.md` | hệ thống *phải* làm gì — khi SRS mâu thuẫn SDD thì SRS thắng |
| `docs/sdd/SDD.md` | thiết kế, các sơ đồ lớp/tuần tự/hoạt động |
| `docs/plan/QUYET_DINH.md` | tám quyết định đã chốt và lý do |
| `docs/web/SCALING.md` | vì sao tầng nghiệp vụ không biết gì về SQLite hay đĩa cứng |
| `docs/ai-usage-log.md` | nhật ký dùng AI và các lỗi đã mắc — rubric yêu cầu |

Hai quy ước của nhóm, vi phạm là phải sửa lại:

1. **Mã nguồn viết bằng tiếng Anh** — tên biến, tên hàm, chú thích, tên tệp,
   lớp CSS, tên test, đường dẫn URL. Tài liệu thì viết tiếng Việt.
2. **Không bao giờ đẩy lên git**: file ghi âm, bản chép lời, model đã tải,
   `aicefr.db`, thư mục `uploads/`, hay bất kỳ dữ liệu cá nhân nào. Kho dữ liệu
   Speak & Improve có giấy phép phi thương mại, không được phát tán lại — mỗi
   người tự đăng ký tài khoản riêng để tải.
