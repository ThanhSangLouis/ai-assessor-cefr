# TC2.4 — Chất lượng mã nguồn

**Nguồn tiêu chí:** rubric PDF tại docs/rubric/.
**Trạng thái:** cập nhật 28/11/2026 trên `main` `2dfa4fc`. Có đủ phân tích tĩnh cho Python và JavaScript, quét secret toàn lịch sử, tài liệu convention. Chờ GVHD xác nhận.

## Hồ sơ cần có

Git history, coding convention, static analysis, lint/typecheck, secret scan và review record.

## Minh chứng hiện có

| Mã | Minh chứng | Kết quả | Ngày, revision |
| --- | --- | --- | --- |
| CQ-01 | **Ruff (Python):** `ruff check src tests tools scripts`, `ruff format --check src tests tools`; luật E, F, I, UP, B ở `pyproject.toml` | 0 lỗi; 345 tệp đúng định dạng. CI chặn ở job `Dinh dang, lint, kiem thu` ([run 45749465088](https://github.com/ThanhSangLouis/ai-assessor-cefr/actions/runs/45749465088)) | 26/11, `2dfa4fc` |
| CQ-02 | **ESLint (JavaScript):** `npx eslint src/aicefr/api/static`, cấu hình `eslint.config.mjs`, phiên bản ghim ở `package.json` | Lần đầu: 5 lỗi, 3 cảnh báo ([báo cáo nguyên văn](reports/eslint-before-2026-11-28.txt)). Sau khi sửa: 0 ([báo cáo](reports/eslint-after-2026-11-28.txt)). Lỗi thật đã sửa ghi ở [DEFECTS.md](../../test/DEFECTS.md) DF-25. CI thêm job `Lint JavaScript (ESLint)` | 28/11, nhánh `docs/sang/submission-evidence` |
| CQ-03 | **gitleaks toàn lịch sử:** `gitleaks git --redact --log-opts=origin/main .` trên 353 commit | Lần đầu 2 phát hiện, đều là báo nhầm: mã SHA-256 của tệp (`src/aicefr/asr/local.py:15` ghim checksum `tokenizer.json`; `checks.json:118` ghi checksum `test_auth.py`). Đã ghi dấu vân tay vào `.gitleaksignore` kèm lý do. Quét lại: **0** ([báo cáo JSON](reports/gitleaks-full-history.json)) | 28/11, `origin/main` |
| CQ-04 | **gitleaks trong CI:** job `Quet lo khoa bi mat` chạy mỗi PR và mỗi lần đẩy lên `main` (quét các commit mới của lần đó) | Xanh ở mọi lần chạy gần nhất | 26/11, `2dfa4fc` |
| CQ-05 | **CodeQL** (`.github/workflows/codeql.yml`), **Trivy** quét ảnh Docker (chặn lỗ hổng CRITICAL), **Dependabot** | Xanh | 26/11, `2dfa4fc` |
| CQ-06 | **Chặn tệp cấm:** `scripts/ci/check_forbidden_files.py` (audio, model, DB, khoá) | 1.617 tệp, không có tệp cấm | 28/11 |
| CQ-07 | **Quy tắc viết mã:** [CODING_CONVENTION.md](../../CODING_CONVENTION.md). Mỗi quy tắc dẫn tới công cụ hoặc test đang chặn nó | Áp dụng từ 13/09/2026 | 28/11 |
| CQ-08 | **Review qua PR:** mọi thay đổi vào `main` đi qua PR có CI xanh (branch protection); 73 PR đã merge | – | đến 26/11 |
| CQ-09 | **Lịch sử Git gom theo người:** `.mailmap`; `git shortlog -sne` ra 3 thành viên (Sang 163, Nguyên 140, Thắng 123 commit). Ba cặp tên/email lẫn của hai người được để riêng, chờ thành viên xác nhận | – | 28/11 |

## Còn thiếu / giới hạn

- Không có trình kiểm kiểu tĩnh riêng (mypy). Type hint được review, hợp đồng giữa module dùng Pydantic.
- `gitleaks dir` trên thư mục làm việc còn báo mật khẩu **thử** trong 2 tệp test E2E (`tests/e2e/test_signup_e2e.py:30`, `tests/test_d071_accounts_and_classes.py:25`) và tệp `.env` cục bộ (không commit, nằm trong `.gitignore`). Lịch sử commit đã quét sạch ở CQ-03.

## Lịch sử (W3, 10/2026)

| Evidence | Phạm vi | Revision/owner |
| --- | --- | --- |
| [W3 Review](../../sdd/features/w3-local-integration/reviews/review-01.md) | Actual diff/tests, transaction/refusal/provenance/auth/privacy và bundled corrections | Codex, 02/10/2026; commits trong record |
| [Speech correction](../../sdd/features/w3-local-integration/evidence/raw-speech-fix-01.md) | Offline pin, deterministic optional-package mocks, safe logs | af5dc8a, gpt-6-luna |
| [Pipeline correction](../../sdd/features/w3-local-integration/evidence/raw-pipeline-fix-01.md) | SQLite atomicity, CAS/recovery, grounded evidence | 5056d05, gpt-6-luna |
| [W3 Evidence Manifest](../../sdd/features/w3-local-integration/evidence/evidence-manifest.md) | Lint/guards và final verification thực tế | Codex final rerun; không là remote CI |
