# SCRUM-69 — Final verification và bàn giao

Historical target `3b2d2b78ba5bb35bd162b8f3e5de21ade946d237`; Sang reference `40907cc35b3d04408f9a8713f16d9be99f4cd6c7`. Source base `d60e8a4`, G1 parent `9748814`. **Code revision `34da102`**; commit tài liệu/log phía sau không đổi source. Ngày 15/10/2026, root review; Luna implementation.

## Kết quả đã chạy

| Kiểm tra | Kết quả |
| --- | --- |
| Full pytest không smoke, branch coverage trên source freeze | PASS: 780 passed, 0 failed/skipped, 2 smoke deselected, 140.50s |
| Coverage toàn repo | Statement 90.8241%, branch 80.1893%, combined 88.1899%; 127 excluded lines |
| Baseline T03 để so sánh | Statement 90.5237%, branch 79.3403%, combined 87.7935% |
| Trust contracts/policy/service và LID/guards | Pure/new critical logic đạt ≥90% line, ≥85% branch; service 100%/100% |
| CV+ | 96.5318% statement, 93.1034% branch trong full suite |
| Ruff src/tests/scripts/tools | PASS |
| Format Python thay đổi và git diff check | PASS; không tuyên bố toàn bộ legacy formatter đã sạch |
| Markdown links | PASS, 17 link ngoài repo được checker bỏ qua |
| Forbidden-file | PASS, 646 tracked files tại bước code staged |
| Credential-pattern scan trên 42 file code/test/tool thay đổi | PASS với bốn pattern families; không phải scan PII/secret toàn diện |
| CV+ oracle độc lập trên pinned artifact | PASS: sáu vector, interval khớp tới tolerance 1e-10 |
| Calibration/refusal CLI chạy lặp | PASS: bytes và hash giống nhau trên synthetic fixtures |
| Real audio model smoke | PASS: hai audio ngắn/dài; Whisper/VAD thật đã nạp; report/session đọc lại sau restart; 64.048s |
| Wheel sạch offline | PASS: 104/104 code/sql/js byte-equal, package assets đầy đủ, cài venv mới thành công |

Lệnh chính, chạy từ worktree task:

```bash
PYTHONPATH=src AICEFR_MODEL_DIR=<runtime>/models COVERAGE_FILE=/tmp/.coverage-root69-final3 \
  <venv>/bin/pytest -q -m 'not smoke' --cov=aicefr --cov-branch \
  --cov-report=json:<evidence>/frozen-coverage.json --cov-report=term
<venv>/bin/ruff check src tests scripts tools
<venv>/bin/python scripts/ci/check_md_links.py
<venv>/bin/python scripts/ci/check_forbidden_files.py
PYTHONPATH=src HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  <venv>/bin/python scripts/qa/parity_model_smoke.py --config <evidence>/real-config.json \
  --data-dir <evidence>/real-data --audio-short <runtime>/fixtures/physicsworks-40s.wav \
  --audio-long <runtime>/fixtures/physicsworks-70s.wav --evidence-dir <evidence>/real-model
```

`<runtime>` là thư mục runtime ngoài repo; `<venv>` là môi trường đã có dependencies; `<evidence>` là `ai-assessor-cefr-runtime/evidence/scrum-69-2026-10-15`. Raw audio/transcript/model/calibration/residual/DB và screenshot giữ ngoài Git. Audio-rights record: `docs/sdd/features/w3-local-integration/prompts/W3-USER-002-audio-rights.md`. Đây là smoke kỹ thuật, **CEFR accuracy NOT_MEASURED**, empirical conformal coverage **NOT_EVALUATED**.

## Hash và provenance

- Wheel: `e7965e8148b41a52afb2d403b71f02e8d4f853ea458efca5091a67c83ae5b739`.
- Reference calibration: `3c09d2583a26e8cc057c0cf36dfb7637d15dfdc901cf00c4e25faef9ce6ef885`.
- Scorer: `7cdeb2a04aa0db770d52d6ff20b49cc371b9cb690f0ace89e5233b5d65bb521a`.
- Synthetic assembled artifact: `e768a740e25a836a547ae80979c95dac04d6924ab210af21cb29f00a7cbb95da`.
- Synthetic calibration result: `2473f585ee7482a4101272a2e1cc70fbd5ad65d2e326b8202ff697d889849580`.
- Synthetic refusal result: `00dfb651d1a08a873fa7cb8c92d41a4eff0f87f3f1e963f853d21c94912bbf7d`.

Raw logs: `frozen-tests.log`, `frozen-coverage.json`, `root-conformal-oracle.json`, `root-cli/root-result.json`, `real-model/result.json`, `wheel-qa/wheel-integrity.json`, `wheel-qa/installed-smoke.json`, `secret-scan.json` dưới evidence ngoài Git. Các run trước formatting không dùng làm final coverage.

## Checklist W5-S01

- S01.1 immutable models/reason enum: domain contract/tests.
- S01.2 independent LID/confidence boundary: ASR/language tests và real adapter smoke.
- S01.3 guards/evidence/no penalty: domain guards và unchanged score regression.
- S01.4 CV+/hash/model binding: strict loader, exact-pinned legacy adapter, oracle và failure tests.
- S01.5 pipeline/report/review/retry/old report: integration report và full suite.
- S01.6 reproducible CLI/split guard/handoff: conformal-tools report, double-run output hashes; không tuyên bố tự retrain hay empirical refusal quality.

Runtime yêu cầu `trust.calibration_artifact`, `trust.expected_sha256`, tùy chọn alpha mặc định .10, cùng `model_artifact`/ASR dependencies. Artifact thiếu hoặc pin sai: `/readyz` 503, không band từ fallback. Không có D043 dependency hoặc schema migration mới.

API payload/authorization và giới hạn lexical guard xem `integration-report.md`; reviewer findings xem `../../reviews/SCRUM-69-review.md`. UI hoàn chỉnh W5-N01/N03 vẫn là task riêng. **Reviewer/user acceptance PENDING; chưa tự đánh dấu Jira Done.**

## Browser từ wheel sạch

Final escalated loopback run: **PASS 65 checks, 0 failed**, 12 screenshot desktop/mobile cho CONTINUE, REVIEW_REQUIRED, REJECTED, NOT_EVALUATED và report legacy, cùng teacher review. Root đã xem screenshot mobile review và kiểm raw JSON/harness; import package từ clean wheel venv. Student khác nhận 404; teacher đọc completed report không cần candidate; thiếu calibration readiness 503; student không thấy nội bộ LID/calibration/provenance; teacher DOM không chứa path; rejected/not-evaluated không estimate.

Không page exception, failed request hoặc external request; ba resource-console error được ghép đúng URL/status với hai foreign-report 404 và một readiness 503 có chủ đích, không xóa âm thầm lỗi khác. Các run QA trước thất bại do harness thread SQLite/serialization/expected-error classification; chỉ run cuối `wheel-qa/browser-qa.json` status PASS được nghiệm thu kỹ thuật. Harness và screenshots giữ ngoài Git; không dùng browser fixture để claim pipeline accuracy. N01/N03 UX toàn phần chưa nằm trong verdict này.
