# Báo cáo thực hiện M15-TASK-001A (Attempt A1)

PROMPT ID: `M15-W5-N01-001A-A1`
TASK ID(S): `M15-TASK-001A` (W5-N01.1 một phần)
ATTEMPT: `A1`
SCOPE ID/TYPE/ROOT: `M15` / module / `docs/sdd/modules/m15-product-web/`
STATUS: `COMPLETED`
OPERATING MODE: `Standard`
HANDOFF MODE: `Shared workspace`
INBOUND BASELINE USED: checkout hiện tại của repo dự án
BASE REVISION: `61455024f1544a92e4313030067f72c29cf80d49`
STARTING FINGERPRINT: `870b7db74c8d49ae96415af179ae009dfd14f49d6b10fb449239f1e59fbac0a4`
FINGERPRINT ALGORITHM: `sdd-workspace-v2`
FINGERPRINT METADATA FILES: `docs/sdd/modules/m15-product-web/07-status.md`; `docs/sdd/modules/m15-product-web/prompts/M15-W5-N01-001A-A1.md`; `docs/sdd/modules/m15-product-web/prompts/prompt-log.md`
FINGERPRINT EXCLUSIONS: KHÔNG CÓ
ARTIFACT VERSIONS USED: M15 Requirement v0.2; Research v0.3 (`RUN`); Specification v0.3; Test Plan v0.2; Plan v0.2 và Tasks v0.2 chỉ cho 001A
APPROVED PHASE RECORDS USED: 01 / 03 / 04 / 05 (`reviews/phase-01-review-2026-10-15.md`, `phase-03-review-2026-10-15.md`, `phase-04-review-2026-10-15.md`, `phase-05-review-2026-10-15.md`)
DIRECT DEPENDENCY/IMPACT SCOPES USED: M01/M06/M07/M08/M11 và portal page hiện hữu dùng shared renderer

## 1. Tóm tắt kết quả

Đã triển khai hoàn chỉnh nền giao diện semantic shell, CSS tokens, landmark và các state style trên renderer chung `src/aicefr/api/templates.py`:
- Thêm accessible skip link `<a href="#main" class="skip-link">Chuyển đến nội dung chính</a>` và gán landmark `<main id="main">` trong `_document`.
- Định nghĩa đầy đủ hệ thống CSS semantic tokens cho surface, text, action/brand, focus-ring, border, error, disabled, spacing và radii trên `:root`.
- Hỗ trợ dark mode qua `@media (prefers-color-scheme: dark)` bảo đảm tương phản AA (>4.5:1).
- Hỗ trợ `prefers-reduced-motion: reduce` triệt tiêu animation không thiết yếu.
- Hỗ trợ `@media print` ẩn các phần tử tương tác (skip link, nav, form, button, audio, alert).
- Tương thích responsive mobile 390×844 và 360×640 (touch target min-height >= 2.75rem / 44px, không tràn ngang `overflow-wrap: anywhere`).
- Giữ nguyên toàn bộ route, quyền, payload, form action, copy nghiệp vụ và thứ tự journey hiện hành.
- Viết mới test suite `tests/local/test_templates_m15_shell.py`, cập nhật `tests/local/test_templates_mobile.py`, và xây dựng script QA browser Playwright `scripts/qa/m15_shell_browser.py`.

## 2. File đã đổi

- `src/aicefr/api/templates.py`: cập nhật `LOCAL_CSS` và `_document` (skip link `#main`, landmark `main#main`, CSS tokens, responsive, dark mode, reduced motion, print).
- `tests/local/test_templates_mobile.py`: thêm kiểm tra skip link và main landmark trên mọi document.
- `tests/local/test_templates_m15_shell.py`: test mới kiểm tra chuyên sâu tokens, landmarks, dark mode, print, reduced motion và các branch renderer.
- `scripts/qa/m15_shell_browser.py`: script Playwright thực thi QA trên loopback server local cho desktop và mobile viewports.
- `docs/sdd/modules/m15-product-web/evidence/m15-task-001a/`: chứa `browser-qa-results.json`, `coverage.json`, `report.md` và 13 screenshots kiểm thử.

## 3. Mapping Yêu cầu & Kiểm thử (Traceability)

- `M15-FR-001 / M15-AC-001` (Semantic shell, tokens, accessible landmarks): kiểm thử qua `tests/local/test_templates_m15_shell.py` và `scripts/qa/m15_shell_browser.py` (`M15-TEST-001`).
- `M15-FR-008 / M15-AC-001` (Reduced motion, print, light/dark): kiểm thử qua `scripts/qa/m15_shell_browser.py` (`M15-TEST-009`).
- `M15-TEST-008` (Responsive viewports 1280×800, 390×844, 360×640): kiểm thử qua `scripts/qa/m15_shell_browser.py`.
- `M15-TEST-012` (Không có claim cấm, không lộ secret/path): kiểm tra static diff và DOM rendering.

## 4. Kết quả kiểm tra bắt buộc

1. **Targeted unit & template tests:**
   - Lệnh: `.venv\Scripts\python.exe -m pytest -q tests/local/test_templates_mobile.py tests/local/test_templates_m15_shell.py`
   - Exit code: `0`
   - Kết quả: `8 passed in 0.35s` (100% pass)

2. **Lint & Format (Changed files):**
   - Lệnh: `.venv\Scripts\ruff.exe check src/aicefr/api/templates.py tests/local/test_templates_mobile.py tests/local/test_templates_m15_shell.py scripts/qa/m15_shell_browser.py`
   - Exit code: `0` (`All checks passed!`)
   - Lệnh: `.venv\Scripts\ruff.exe format --check src/aicefr/api/templates.py tests/local/test_templates_mobile.py tests/local/test_templates_m15_shell.py scripts/qa/m15_shell_browser.py`
   - Exit code: `0` (`4 files already formatted`)

3. **Format & Lint Gate Repo:**
   - Lệnh: `.venv\Scripts\ruff.exe check src tests scripts`
   - Exit code: `0` (`All checks passed!`)
   - Lệnh: `.venv\Scripts\ruff.exe format --check src tests scripts`
   - Exit code: `1` (Legacy baseline: 22 files unformatted trong tests/audio, tests/qc, tests/report từ các tuần trước).

4. **Coverage:**
   - Lệnh: `.venv\Scripts\python.exe -m pytest -q tests/local/test_templates_mobile.py tests/local/test_templates_m15_shell.py tests/api/test_student.py --cov=aicefr.api.templates --cov-branch --cov-report=term-missing --cov-report=json:docs/sdd/modules/m15-product-web/evidence/m15-task-001a/coverage.json`
   - Exit code: `0`
   - Độ bao phủ trên `src/aicefr/api/templates.py`:
     - Statements: 115/115 (100%, 0 miss)
     - Branches: 20, BrPart: 3 (98% branch coverage)
     - Nhánh chưa phủ hoàn toàn: 3 partial branches trong các nhánh điều kiện fallback phụ của review action và evidence seek button.

5. **Shared Regression Repo:**
   - Lệnh: `.venv\Scripts\python.exe -m pytest -q -m "not smoke"`
   - Exit code: `1`
   - Ghi nhận: 508 passed, 15 skipped, 2 deselected.
   - Lỗi tồn đọng cũ (legacy baseline platform): 31 failures và 53 errors xuất phát từ các test storage/privacy/billing/symlink được viết giả định môi trường Linux POSIX (`os.getuid`, symlink permissions, và monkeypatch Windows `KeyError: 'AICEFR_STORAGE_DIR'`). Toàn bộ các test liên quan trực tiếp đến template/student/mobile đều PASS 100%.

6. **Browser QA (Playwright):**
   - Lệnh: `.venv\Scripts\python.exe scripts/qa/m15_shell_browser.py`
   - Exit code: `0`
   - Kết quả: 14/14 assertions passed.
   - Console errors: 0
   - Failed requests: 0
   - External requests blocked: 0
   - Screenshots tạo lập (kèm SHA-256 lưu tại `browser-qa-results.json`):
     - `student_upload_desktop_light.png` (`674cf8dd...`)
     - `student_upload_desktop_dark.png` (`6fe322f2...`)
     - `student_upload_mobile_light.png` (`38fa5a18...`)
     - `student_upload_mobile-narrow_light.png` (`9d9b7f0b...`)
     - `student_report_desktop_light.png` (`38e96b98...`)
     - `student_report_desktop_dark.png` (`f3fba941...`)
     - `student_report_mobile_light.png` (`6218d844...`)
     - `student_report_mobile-narrow_light.png` (`1ec03f56...`)
     - `login_desktop_light.png` (`bece51d9...`)
     - `login_desktop_dark.png` (`8e7ebcf0...`)
     - `login_mobile_light.png` (`5eef7b5a...`)
     - `login_mobile-narrow_light.png` (`b40445d4...`)
     - `report_desktop_print.png` (`d60d3d4b...`)

## 5. Clean Code Self-Review

- **Đơn giản & Bền vững:** Không thêm JavaScript framework, CDN hay thư viện bên ngoài; giữ nguyên kiến trúc server-side rendering gốc của dự án.
- **Tính đóng gói:** Toàn bộ CSS tokens và utility states nằm tập trung trong `LOCAL_CSS`, dễ mở rộng và tái sử dụng cho các task 001B tiếp theo.
- **Khả năng tiếp cận (A11y):** Skip link đáp ứng chuẩn WCAG 2.1 (nhảy thẳng vào `#main`), text contrast đạt chuẩn AA cả 2 theme light/dark, touch target đảm bảo kích thước tối thiểu 44px (2.75rem).
- **An toàn:** Tiêu đề và nội dung được escape bằng `html.escape()`.

## 6. Giả định và Vấn đề còn lại

- Task `M15-TASK-001A` hoàn thành trong phạm vi semantic shell cho các trang hiện hữu.
- Các hạng mục typography tùy biến (Roboto font local, WOFF2/subset), icon/art local package, navigation mở rộng theo vai trò W5, và các journey đầy đủ (N01.2–N04.7) thuộc về các task tiếp theo (`001B` và `002`–`006`) sau khi có phê duyệt contract tương ứng.
