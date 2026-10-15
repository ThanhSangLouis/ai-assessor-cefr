# Chạy W3 local

Ứng dụng WSGI chạy một process trên loopback với tài khoản fixture do người chạy tạo. SQLite, audio và model nằm ngoài repository. Cấu hình demo dành cho dữ liệu kiểm thử do nhóm tạo; chưa có nghiệm thu vận hành dữ liệu người học thật hay validation độ chính xác CEFR.

## Cài đặt và chạy demo

Từ thư mục repository, dùng Python >=3.11:

```bash
python3 -m venv /tmp/aicefr-local-venv
source /tmp/aicefr-local-venv/bin/activate
python -m pip install -e '.[dev]'
python -m aicefr.local init-demo --data-dir /tmp/aicefr-local-data --actor-id fixture-student --role student
python -m aicefr.local init-demo --data-dir /tmp/aicefr-local-data --actor-id fixture-teacher --role teacher
python -m aicefr.local serve --data-dir /tmp/aicefr-local-data --demo --port 8000
```

CLI hỏi mật khẩu bằng `getpass`; không có mật khẩu mặc định. ID phải bắt đầu `fixture-`. Có thể dùng `--password-stdin` trong automation local, không đặt mật khẩu trong command argument hay Git. Mở `http://127.0.0.1:8000/login`. Student đồng ý phiên bản `demo-v1`, rồi nộp bài `demo-speaking`, phiên bản `1`. Nếu không cấu hình ASR/model, report không đưa band AI. Teacher đăng nhập tài khoản riêng, mở hàng đợi, xem report/nghe audio và ghi quyết định; overall AI giữ nguyên.

Tạo một WAV kiểm thử 3 giây, có khoảng lặng để đi nhánh QC REVIEW mà không cần ASR:

```bash
python - <<'PY'
from pathlib import Path
import numpy as np
import soundfile as sf
path = Path('/tmp/aicefr-local-fixture.wav')
samples = np.zeros(48000, dtype=np.float32)
t = np.arange(14400) / 16000
samples[:14400] = 0.15 * np.sin(2 * np.pi * 220 * t)
sf.write(path, samples, 16000, subtype='PCM_16')
print(path)
PY
```

Đây là audio kiểm thử kỹ thuật, không có lời nói và không dùng để chứng minh chất lượng ASR/CEFR. Teacher override trên bài này chỉ chứng minh luồng lưu quyết định.

## Cấu hình model local

Whisper dùng đúng Systran/faster-whisper-small revision `536b0662742c02347bc0e980a01041f333bce120`, đã ghim tại [M03 model provenance](sdd/modules/m03-asr/evidence/evidence-manifest.md). Chuẩn bị model ngoài Git trước khi chạy; runtime chỉ đọc file local và kiểm checksum. Ridge dùng `ridge_resp_v2.json`, SHA256 `7cdeb2a04aa0db770d52d6ff20b49cc371b9cb690f0ace89e5233b5d65bb521a`; đặt `model_artifact` trong config hoặc `AICEFR_MODEL_DIR` trỏ thư mục chứa artifact. Không giảm pin hoặc thay band mapping để ép có điểm.

Cài optional extras cho ASR/VAD. Với máy CPU, cài torch và torchaudio **cùng phiên bản** từ CPU index trước để tránh tải dependencies GPU. Sau đó cài extras của repo:

```bash
python -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
python -m pip install -e '.[dev,asr,vad]'
```

W3 đã kiểm tra với faster-whisper1.2.1, CTranslate2 4.8.2, Silero6.2.1 và torch/torchaudio2.11.0+cpu. Nguồn cài CPU: [PyTorch](https://pytorch.org/get-started/locally/). Kiểm lại phiên bản torch/torchaudio nếu resolver chọn hai phiên bản khác nhau.

Tạo `/tmp/aicefr-local-config.json` theo mẫu dưới đây và thay hai đường dẫn model bằng đường dẫn thực. Đây vẫn là cấu hình demo, QC chưa được xem là ngưỡng vận hành đã nghiệm thu:

```json
{
  "demo": true,
  "consent_version": "demo-v1",
  "model_artifact": "/absolute/path/ridge_resp_v2.json",
  "asr_model_dir": "/absolute/path/faster-whisper-small",
  "asr_weight_name": "small",
  "asr_device": "cpu",
  "asr_compute_type": "int8",
  "vad_enabled": true,
  "vad_threshold": 0.5,
  "vad_min_silence_ms": 150,
  "allowed_media_types": ["audio/wav", "audio/flac", "audio/ogg", "audio/mpeg"],
  "tasks": [{"task_id": "demo-speaking", "task_version": "1"}],
  "qc": {
    "version": "demo-qc-v1",
    "accepted_formats": ["wav", "flac", "ogg", "mp3"],
    "max_input_bytes": 20000000,
    "min_duration_s": 1.0,
    "max_duration_s": 180.0,
    "max_input_sample_rate_hz": 48000,
    "silence_threshold": 0.01,
    "clipping_threshold": 0.99,
    "review_silence_ratio": 0.5,
    "reject_silence_ratio": 0.95,
    "review_clipping_ratio": 0.1,
    "reject_clipping_ratio": 0.5
  }
}
```

```bash
python -m aicefr.local serve --data-dir /tmp/aicefr-local-data --config /tmp/aicefr-local-config.json
```

ASR chạy English với word timestamps; Silero dùng model đi kèm package, không `torch.hub` tải mạng. Artifact chỉ cho inference trên một response. Provenance mismatch, VAD/ASR lỗi, OOD hoặc thiếu feature đều giữ reason và overall `null`; không thay bằng transcript/score kiểm thử.

## Kiểm thử và khởi động lại

```bash
python -m pytest -q -m 'not smoke'
ruff check src tests scripts
python scripts/ci/check_md_links.py
python scripts/ci/check_forbidden_files.py
```

Các tests cần Ridge thật chỉ chạy khi `AICEFR_MODEL_DIR` có artifact đúng pin; kết quả skip phải được ghi rõ. Browser QA có [evidence theo scope W3](sdd/features/w3-local-integration/evidence/evidence-manifest.md). Chạy server lại với cùng data-dir sẽ giữ accounts, consent, report và quyết định giảng viên. Logout thu hồi session phía server; rút consent chặn bài nộp mới. `Ctrl+C` dừng server và đóng SQLite. Không dùng nhiều workers/process cùng composition root local hiện tại.

## Các chức năng bổ sung PARITY-001

Nhánh `feat/PARITY-001-runtime-completeness` có lịch sử bài, tiến độ, profile/export
JSON, phát audio và nhận xét với timestamp có thể bấm để nghe đúng đoạn. Teacher
xem tất cả bài, thống kê riêng band AI/band cuối, lịch sử trước/sau, nhận/trả bài
và mở lại quyết định đã hoàn tất bằng revision và lý do. Claim hết hạn sau 15 phút.
Tài khoản admin vào `/admin`; tạo bằng lệnh `init-demo --role admin` giống ví dụ
student/teacher phía trên. Không có tài khoản hay mật khẩu quản trị mặc định.

Admin có tài khoản, mở khóa/disable, đề theo phiên bản, audit, trạng thái model,
kích hoạt artifact đúng pin, chỉnh QC bằng CAS, export nghiên cứu, xem trước/xác
nhận xóa tài khoản fixture, retention và orphan cleanup. API tương ứng dùng tiền
tố `/api`, ví dụ `/api/student/responses`, `/api/teacher/stats`, `/api/admin/accounts`.
Profile và export có hậu tố `.json`; các route này trả JSON khi mở trực tiếp.

Trong config, thêm `async_pipeline: true`, `queue_capacity: 8` để xử lý ở worker
nền có connection SQLite riêng. Status `QUEUED/RUNNING` tự tải lại mỗi 5 giây.
`serve` giữ khóa một instance/data-dir; khởi động lại chuyển bài `RUNNING` bị gián
đoạn sang `FAILED/PIPELINE_INTERRUPTED` cùng audit, rồi tiếp tục bài `QUEUED`.
Đăng nhập giới hạn 30 lần/phút/IP local; upload 10 lần/phút/tài khoản; sau 5 lần
sai mật khẩu tài khoản bị khóa 15 phút. Disable thu hồi session. Các giới hạn
process chỉ phù hợp server local một instance. Không phải số đo SLA vận hành.

Bật `long_response_windows: true` để dùng tổng hợp thử nghiệm cho bài vượt duration
training. Cửa sổ không chồng lấn, bao phủ cả phần cuối, theo giới hạn trong artifact;
median dùng band mapping hiện tại. Nếu một cửa sổ không được chấm, overall là null.
Mọi tổng hợp có `SCORE_AGGREGATED`, provenance từng cửa sổ và cần teacher review.
Ngưỡng QC mặc định trong ví dụ vẫn tối đa 180 giây; admin có thể cấu hình tối đa
300 giây. Tính năng này chưa phải validation CEFR.

Ghi âm micro cần `ffmpeg` và `ffprobe` trên PATH, ngoài dependencies Python. Thêm
`webm`, `mp4` vào `qc.accepted_formats` và `audio/webm`, `audio/mp4` vào
`allowed_media_types`, đồng thời dùng version QC mới khi thay danh sách định dạng.
Trình duyệt xin quyền micro khi người dùng bấm ghi âm; ghi âm không tự gửi tệp.
Có nghe lại, dừng, ghi lại và thanh tiến trình upload. Original blob không đổi;
chuyển mã qua pipe chỉ dùng cho giải mã, có timeout và giới hạn output. Khi thiếu
công cụ hệ thống, form vẫn cho chọn tệp WAV/FLAC/OGG/MP3.

Research opt-in là checkbox riêng, mặc định false. Withdraw chặn upload mới và
research export ngay; owner vẫn xem/export dữ liệu của mình. Erasure giữ audit
có ID fixture, và không xóa các bản backup đã tạo. Retention xóa audio, nhận xét
và refs; giữ score/provenance. Blob deletion intent được commit cùng metadata;
cleanup có thể retry sau lỗi hoặc crash. Orphan cleanup bỏ qua symlink và tệp
chưa đủ một giờ để tránh chạm tệp mới đang được lưu.

CLI bổ sung (mật khẩu qua getpass hoặc stdin, không dùng command argument):

```bash
python -m aicefr.local accounts list --data-dir /tmp/aicefr-local-data --config /tmp/aicefr-local-config.json --actor-id fixture-admin
python -m aicefr.local maintenance retention --data-dir /tmp/aicefr-local-data --config /tmp/aicefr-local-config.json --actor-id fixture-admin
python -m aicefr.local maintenance backup --data-dir /tmp/aicefr-local-data --config /tmp/aicefr-local-config.json --actor-id fixture-admin --destination /tmp/aicefr-backup-01
python -m aicefr.local score --data-dir /tmp/aicefr-local-data --config /tmp/aicefr-local-config.json --actor-id fixture-student --audio /tmp/aicefr-local-fixture.wav --task-id demo-speaking --task-version 1
```

Retention/orphans mặc định dry-run; `--apply` thực thi. Backup gồm SQLite snapshot
và blob đã kiểm checksum, không ghi đè destination. Các thao tác xóa/retention
được kiểm thử bằng fixture; policy cho dữ liệu người học thật chưa được nghiệm thu.

`/healthz` kiểm liveness, `/readyz` kiểm DB, model thật và worker. `/metrics` và
`/admin/health` chỉ admin; counters không có account/response/transcript trong
labels. Mỗi HTTP response có `X-Request-ID`. Model ASR/VAD đều dùng local adapter;
không fallback sang model/transcript giả khi thiếu model.

Browser QA mở rộng: `scripts/qa/parity_app_browser.py --config <config> --evidence-dir <dir>`.
Real-model smoke: `scripts/qa/parity_model_smoke.py --help`. Hai runner dùng data-dir
fixture riêng; các số đo kỹ thuật và giới hạn được ghi ở
[verification PARITY-001](evidence/parity-001-verification-2026-10-08.md).

## W5-T01 — Schema v9 và durable worker

Khi mở data-dir schema v4 bằng bản W5-T01, `SQLiteStore` tự tạo snapshot trong
`<data-dir>/backups/schema-v4-<timestamp>/`, sau đó áp dụng năm migration additive
identity → learning → research → billing → jobs/cleanup trong một transaction.
Snapshot có database, blobs và manifest SHA-256; file dữ liệu/backup giữ ngoài Git.
Dừng app/worker cũ và thử trên bản sao dữ liệu trước khi nâng data-dir cần giữ.
Schema mới hơn, partial hoặc ledger/schema shape sai bị từ chối khi startup.

`async_pipeline=true` dùng job bền vững trong cùng SQLite file, có lease,
heartbeat, bounded retry và idempotency. Restart phục hồi lease hết hạn;
lease còn hiệu lực không bị coi là interrupted. Request/worker/heartbeat dùng
connection riêng, không chia sẻ connection giữa thread. Lỗi hoặc thiếu model
không tạo score giả.

`GET /live` (cùng `/health`, `/healthz`) chỉ báo process alive. `GET /ready`
(cùng `/readyz`) kiểm config/schema/database/blob/worker/model và trả 503 khi
thiếu prerequisite; response chỉ có booleans, không đường dẫn/secret.

Rollback dùng code trước migration và data-dir restore mới. Với snapshot tự tạo:

```python
from pathlib import Path
from aicefr.storage.migrations import restore_backup

restore_backup(
    Path("/path/to/data/backups/schema-v4-TIMESTAMP"),
    Path("/path/to/restored-v4-data"),
)
```

Helper kiểm manifest/checksum, từ chối symlink/path traversal và không ghi đè
thư mục đang chứa dữ liệu. Sau restore, chạy **code trước migration** trên bản
v4 để kiểm report; mở bằng code W5 sẽ nâng lên v9 lại. Không xóa snapshot hoặc
bản database lỗi để ép rollback thành công.

Kiểm clean-wheel trên Linux bằng wheelhouse dependency đã chuẩn bị ngoài Git:

```bash
python -m build --wheel --no-isolation --outdir /tmp/aicefr-w5-wheels
python scripts/qa/w5_foundation_smoke.py \
  --wheel /tmp/aicefr-w5-wheels/aicefr-0.1.0-py3-none-any.whl \
  --python-dependency-cache /path/to/offline-wheelhouse \
  --evidence-dir /tmp/aicefr-w5-wheel-evidence
```

Script tạo venv sạch, cài wheel offline và kiểm CLI/HTTP thật, login, liveness,
readiness thiếu model, static assets và backup/restore report từ fixture QC REVIEW.
Không dùng kết quả này làm evidence ASR/VAD inference hoặc CEFR accuracy.
Evidence/review task: [SCRUM-65 review](sdd/modules/m16-monolith-runtime/evidence/scrum-65/review.md).
