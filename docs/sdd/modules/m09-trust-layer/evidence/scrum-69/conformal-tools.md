# SCRUM-69 — Bằng chứng conformal và tools

## Baseline và quyền sở hữu

- Historical target: `3b2d2b78ba5bb35bd162b8f3e5de21ade946d237`.
- Sang reference, chỉ đọc: `40907cc35b3d04408f9a8713f16d9be99f4cd6c7`.
- Actual branch base: `9748814cd783656c2a2f0780549349b2d1032707`.
- Source base: `d60e8a4` (T01–T03 merged).
- Reference CV+ JSON SHA-256 pin: `3c09d2583a26e8cc057c0cf36dfb7637d15dfdc901cf00c4e25faef9ce6ef885`.
- Scorer SHA-256 pin trong reference: `7cdeb2a04aa0db770d52d6ff20b49cc371b9cb690f0ace89e5233b5d65bb521a`.

Lane conformal sở hữu `src/aicefr/scoring/conformal.py`, `tools/`, `tests/scoring/test_conformal.py` và `tests/tools/test_trust_tools.py`. Không có calibration artifact, residual, audio, transcript hay dữ liệu cá nhân trong Git.

## Kiểm tra tổng hợp

Lệnh chạy trên worktree SCRUM-69, với `HEAD` vẫn ở actual branch base nêu trên:

```bash
COVERAGE_FILE=/tmp/.coverage-conformal69 PYTHONPATH=src /home/thanglvc/Documents/HCMUTE/TLCN/ai-assessor-cefr/.venv/bin/coverage run --branch --source=aicefr.scoring.conformal,tools.calibrate_conformal,tools.refusal_benchmark,tools._trust_cli -m pytest -q tests/scoring/test_conformal.py tests/tools/test_trust_tools.py
COVERAGE_FILE=/tmp/.coverage-conformal69 /home/thanglvc/Documents/HCMUTE/TLCN/ai-assessor-cefr/.venv/bin/coverage report -m --include=src/aicefr/scoring/conformal.py,tools/calibrate_conformal.py,tools/refusal_benchmark.py,tools/_trust_cli.py
```

Kết quả test sau bổ sung kiểm soát nesting JSON: **142 passed**. Coverage line/branch theo từng file:

| File | Line | Branch |
| --- | ---: | ---: |
| `src/aicefr/scoring/conformal.py` | 95.38% | 93.10% |
| `tools/calibrate_conformal.py` | 93.95% | 90.48% |
| `tools/refusal_benchmark.py` | 97.08% | 94.44% |
| `tools/_trust_cli.py` | 95.00% | 93.18% |
| **Tổng các file trên** | **95.21%** | **92.60%** |

Fixtures là dữ liệu tổng hợp nhỏ. Test bao phủ rank hữu hạn `floor(alpha(n+1))`/`ceil((1-alpha)(n+1))`, endpoint và biên band, nhiều band, checksum/model SHA/feature order/threshold identity, lỗi JSON/NaN/kích thước/nesting/fold/provenance, deterministic CLI hashes, split/group leakage và refusal benchmark gọi cùng typed `TrustPolicy` như runtime. JSON có nesting vượt 64 cấp bị từ chối trước khi dựng object; hai CLI trả `NOT_RUN` không traceback/path, giữ nguyên hash input và bytes output đã tồn tại. CLI không ghi đè input; output artifact/report bị chặn trong repository và được ghi atomic.

Nhánh legacy chỉ nhận JSON có đúng SHA-256 nguồn pinned cùng model SHA đã ghim. Adapter giữ `conformal_version`, `method`, `fold_of`, `n`, `folds`, `feature_order` và `residuals`; source không có sample/speaker identity nên hai giá trị đó vẫn `None`. Band thresholds lấy từ scorer đã nạp. Các curve/statistic gốc của reference không được chép vào artifact/report mới. Calibration fixture không chứng minh retraining hay empirical coverage; `empirical_coverage=NOT_EVALUATED`.

Smoke test với reference artifact thật nằm ngoài Git và full/runtime integration do root thực hiện; chưa tính vào kết quả lane này. Coverage data chỉ nằm tại `/tmp/.coverage-conformal69`.

## Kiểm tra lint

```bash
/home/thanglvc/Documents/HCMUTE/TLCN/ai-assessor-cefr/.venv/bin/ruff check src/aicefr/scoring/conformal.py tools tests/scoring/test_conformal.py tests/tools/test_trust_tools.py
```

Kết quả trên toàn bộ file thuộc lane: **All checks passed**. `ruff format` cũng chạy trên sáu file Python thuộc lane. Không chạy lại test trong bước chỉnh lint này vì root đang chạy bộ xác minh toàn scope.
