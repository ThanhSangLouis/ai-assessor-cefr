# Báo cáo thực hiện M15-TASK-001A (Correction Attempt A2 / Reissue A2R1)

PROMPT ID: `M15-W5-N01-001A-A2R1`  
ORIGINAL PROMPT ID: `M15-W5-N01-001A-A1`  
SUPERSEDED PROMPT ID: `M15-W5-N01-001A-A2` (không thực thi)  
TASK ID(S): `M15-TASK-001A` (W5-N01.1 một phần)  
ATTEMPT: `A2` (vòng sửa gộp F01–F06, reissue R1 trước thực thi do Phase 05 amendment mở rộng)  
SCOPE ID/TYPE/ROOT: `M15` / module / `docs/sdd/modules/m15-product-web/`  
STATUS: `COMPLETED` (trạng thái bàn giao của implementer; chờ Phase 07 Codex review và User Approval)  
OPERATING MODE: `Standard`  
HANDOFF MODE: `Shared workspace`  
INBOUND BASELINE USED: checkout hiện tại của repo dự án  
BASE REVISION: `6baf720f173b440eb961676b09ea290058a39b35`  
STARTING FINGERPRINT: `aa7f364834ccf6d6002bebb26f74af82f55fca6c97a54272c720984869b32c45`  
FINGERPRINT ALGORITHM: `sdd-workspace-v2`  
FINGERPRINT METADATA FILES:  
- `docs/sdd/modules/m15-product-web/07-status.md`  
- `docs/sdd/modules/m15-product-web/prompts/M15-W5-N01-001A-A2R1.md`  
- `docs/sdd/modules/m15-product-web/prompts/prompt-log.md`  
FINGERPRINT EXCLUSIONS: KHÔNG CÓ  
APPROVED ARTIFACT VERSIONS USED: M15 Requirement v0.2; Research v0.3 (`RUN`); Specification v0.3; Test Plan v0.2; Plan v0.2 và Tasks v0.2 cho 001A; [Phase 05 amendment v0.2a](../05-001a-identity-amendment.md) chỉ cho F06  
APPROVED PHASE RECORDS USED: M15 01/03/04/05; Phase 05 F06 APPROVED ngày 15/10/2026. Phase 07 A1 `CHANGES_REQUIRED` (record `reviews/phase-07-review-2026-10-15.md`)  
DIRECT DEPENDENCY/IMPACT SCOPES: M11 Identity & Account (Thắng giữ source lock riêng `identity.py`; vùng `_password_page`). Không thay đổi M11 contract hay business logic.

---

## 1. Tóm tắt kết quả xử lý các Findings (F01–F07)

Vòng sửa gộp `A2` giải quyết dứt điểm toàn bộ 6 finding MAJOR (F01–F06) và 1 finding MINOR (F07) được nêu trong Phase 07 A1 Review:

1. **F01 (Focused skip link không che H1 và kích hoạt focus landmark thực):**
   - Đã tái cấu trúc style `.skip-link` trong `src/aicefr/api/templates.py`: ở trạng thái bình thường được ẩn an toàn bằng kỹ thuật visually-hidden (`clip`, `overflow: hidden`, `width/height: 1px`). Khi nhận focus (`:focus`, `:focus-visible`), phần tử hiển thị dạng `position: static; display: inline-block; margin-bottom: 0.75rem;` nằm ngay phía trên `<main id="main">` trong luồng tài liệu.
   - Không còn hiện tượng skip link phủ lên tiêu đề H1 hay header/nội dung tại mọi viewport (1280×800, 390×844, 360×640). Đo đạc bounding box trong Playwright xác nhận: `skip_box["y"] + skip_box["height"] <= h1_box["y"]`.
   - Bổ sung `tabindex="-1"` cho `<main id="main">` trong `_document`; khi nhấn `Enter` trên skip link, focus trình duyệt chuyển trực tiếp vào `main#main` (`document.activeElement.id === 'main'`), URL hash cập nhật `#main`, và landmark nằm trọn trong viewport nhìn thấy.

2. **F02 (Tương phản màu hover/active ở light theme đạt chuẩn WCAG AA ≥ 4.5:1):**
   - Cập nhật biến màu trên `:root` (light mode): `--primary-hover: #075985` (Sky 800) và `--primary-active: #0c4a6e` (Sky 900).
   - Đo đạc computed contrast thực tế trong Playwright:
     - Nút bấm light hover (`#ffffff` trên nền `#075985`): **7.56:1** (vượt xa chuẩn AA ≥ 4.5:1).
     - Liên kết light hover (`#075985` trên nền trắng / subtle `#f1f5f9`): **6.90:1 – 7.56:1** (vượt chuẩn AA ≥ 4.5:1).
     - Đo cả dark theme: nút bấm hover đạt **10.71:1**, liên kết hover đạt **8.77:1**.

3. **F03 (Phục vụ file JS local `/recorder.js` & `/report.js`, thiết lập console/network error gate):**
   - Cập nhật fixture server trong `scripts/qa/m15_shell_browser.py` để phục vụ trực tiếp các file static cục bộ `/recorder.js` và `/report.js` từ `src/aicefr/api/static/`.
   - Bổ sung assertion bắt buộc: `assert len(console_errors) == 0` và `assert len(failed_requests) == 0`. Lệnh QA sẽ thất bại ngay lập tức nếu phát sinh bất kỳ lỗi 404 hoặc console error nào.
   - Kết quả đo đạc: **0 console errors**, **0 failed requests**, **0 external requests blocked**.

4. **F04 (Loại bỏ PASS hình thức, kiểm tra thực chất các hành vi a11y, responsive và print):**
   - Thay thế toàn bộ cờ PASS hình thức bằng các assertion cụ thể trong Playwright:
     - Bounding box skip link vs H1 không chồng lấn.
     - Nhấn `Enter` kích hoạt focus thực vào `main#main`.
     - Tương phản computed color đạt chuẩn WCAG AA ≥ 4.5:1 cho nút bấm và liên kết ở cả trạng thái thường và hover.
     - Reduced motion kiểm tra thực tế `transitionDuration <= 0.01s` và `animationDuration <= 0.01s` trên các phần tử tương tác (`button`, `body`).
     - Print media kiểm tra thuộc tính `display: none !important` trên các phần tử điều hướng và hành động (`nav`, `.skip-link`, `button`, `form`).
     - Kiểm tra không tràn ngang (`scrollWidth <= clientWidth + 1`) và không bị clipping nội dung/hành động khi áp dụng `overflow-x: hidden`.

5. **F05 (Độ bao phủ thực tế & phân tích baseline regression):**
   - Báo cáo chính xác độ bao phủ A1: 115/115 statements (100%), 17/20 branches (**85% branch coverage**), còn thiếu 3 nhánh partial `[524, 529]`, `[649, 653]`, `[653, 665]`.
   - Bổ sung test cases trong `tests/local/test_templates_m15_shell.py` phủ kín toàn bộ 3 nhánh partial này. Kết quả đo A2 đạt: **115/115 statements (100%)**, **20/20 branches (100%)** trên `src/aicefr/api/templates.py`.
   - Chạy lệnh whole-project regression `-m "not smoke"`, trích xuất file `coverage.json` và lưu raw log; phân tích rõ các lỗi failure/error cũ xuất phát từ môi trường Windows (thiếu quyền symlink POSIX / file lock sqlite).

6. **F06 (Loại bỏ `<main>` lồng và sắp xếp heading trang `/password-change`):**
   - Trong `IdentityApi._password_page` (`src/aicefr/api/identity.py`), loại bỏ cặp thẻ `<main>` lồng bên trong.
   - Chuyển `<h1>Đổi mật khẩu tạm thời</h1>` thành `<h2>Đổi mật khẩu tạm thời</h2>`.
   - Kết quả render qua `_document("Đổi mật khẩu", body)` bảo đảm trang `/password-change` có đúng **một landmark `main#main`** và đúng **một tiêu đề `<h1>`** (`<h1>Đổi mật khẩu</h1>`).
   - Giữ nguyên 100% nội dung nghiệp vụ, form action (`/password-change`), input names (`current_password`, `new_password`, `confirm_password`), autocomplete, escaping và auth logic.
   - Bổ sung test semantic `test_identity_password_page_semantic_shell` trong `tests/local/test_templates_m15_shell.py`. Chạy lại `tests/api/test_identity_api.py` đạt **8 passed** (100%).
   - Bổ sung fixture route `/password-change` vào browser QA, kiểm thử và chụp ảnh ở đủ 4 cấu hình viewport/theme.

7. **F07 (Minor - Sửa SHA-256 prefixes và mô tả chính xác print details):**
   - Trích dẫn mã hash SHA-256 khớp 100% với file ảnh vật lý và file `browser-qa-results.json`.
   - Mô tả chính xác: trong bản in `report_desktop_print.png`, các khối `<details>` không có thuộc tính `open` mặc định vẫn giữ trạng thái thu gọn theo hành vi chuẩn của Chromium.

---

## 2. Danh sách file thay đổi

Các file thuộc phạm vi được phép theo Phase 05 và prompt A2R1:

| File | Thay đổi chính |
| :--- | :--- |
| `src/aicefr/api/templates.py` | Cập nhật `--primary-hover: #075985`, `--primary-active: #0c4a6e`; định nghĩa `.skip-link` visually-hidden và static block khi focus; thêm `main:focus { outline: none; }`; thêm `tabindex="-1"` cho `main#main` trong `_document`. |
| `src/aicefr/api/identity.py` | Bỏ `<main>` lồng và chuyển `<h1>` thành `<h2>` trong `_password_page`. |
| `tests/local/test_templates_mobile.py` | Cập nhật assertion landmark `tabindex="-1"` trên `main#main`. |
| `tests/local/test_templates_m15_shell.py` | Thêm test phủ 3 partial branches của `templates.py` (comment không có seek ref, candidate `IN_REVIEW` và `REJECTED`); thêm test semantic `test_identity_password_page_semantic_shell`. |
| `scripts/qa/m15_shell_browser.py` | Phục vụ local `/recorder.js` & `/report.js`; thêm route `/password-change`; bổ sung assertion bounding box, skip Enter activation, computed contrast WCAG AA, reduced motion và print media; format chuẩn PEP8 / ruff line-length <= 100. |
| `docs/sdd/modules/m15-product-web/evidence/m15-task-001a-a2/` | Lưu trữ `browser-qa-results.json`, `coverage.json`, `report.md` và 17 ảnh screenshot chụp kiểm thử. |

---

## 3. Mapping Yêu cầu & Kiểm thử (Traceability)

- `M15-FR-001 / M15-AC-001` (Semantic shell, landmarks, skip link, single H1 per page):
  - Kiểm thử unit & DOM: `tests/local/test_templates_m15_shell.py` (test landmark, document, và `_password_page`).
  - Kiểm thử trình duyệt: `scripts/qa/m15_shell_browser.py` trên 4 routes (`/student/upload`, `/student/report`, `/login`, `/password-change`).
- `M15-FR-008 / M15-AC-001` (CSS tokens, dark mode, reduced motion, print media, touch targets):
  - Kiểm thử token & rules: `tests/local/test_templates_m15_shell.py`.
  - Kiểm thử trình duyệt: `scripts/qa/m15_shell_browser.py` (đo computed contrast, transition duration, print display none).
- `M15-TEST-001/008` (Responsive viewports 1280×800, 390×844, 360×640):
  - Đo đạc thực tế trong Playwright không tràn ngang và không clipping landmark `main#main`.
- `M15-TEST-002` (Identity API & auth regression cho `/password-change`):
  - Kiểm thử regression: `tests/api/test_identity_api.py` (8 passed).

---

## 4. Kết quả kiểm tra theo Quality Contract

### 4.1. Targeted unit & integration tests
```text
Lệnh: .venv\Scripts\python.exe -m pytest -q tests/local/test_templates_mobile.py tests/local/test_templates_m15_shell.py tests/api/test_identity_api.py tests/api/test_student.py
Exit code: 0
Output: 31 passed in 4.72s
```

### 4.2. Lint & Style Check (Changed Files)
```text
Lệnh: .venv\Scripts\ruff.exe check src/aicefr/api/templates.py src/aicefr/api/identity.py tests/local/test_templates_mobile.py tests/local/test_templates_m15_shell.py scripts/qa/m15_shell_browser.py
Exit code: 0 (All checks passed!)

Lệnh: .venv\Scripts\ruff.exe format --check src/aicefr/api/templates.py src/aicefr/api/identity.py tests/local/test_templates_mobile.py tests/local/test_templates_m15_shell.py scripts/qa/m15_shell_browser.py
Exit code: 0 (5 files already formatted)
```

### 4.3. Repo-wide Lint & Format Gate
```text
Lệnh: .venv\Scripts\ruff.exe check src tests scripts
Exit code: 0 (All checks passed!)

Lệnh: .venv\Scripts\ruff.exe format --check src tests scripts
Exit code: 1
Ghi chú: Lỗi format tồn đọng trên 22 file baseline cũ thuộc tests/audio/, tests/qc/, tests/report/ chưa được format từ các tuần trước. Toàn bộ file thuộc task M15-TASK-001A đều đạt chuẩn format 100%.
```

### 4.4. Code Coverage
- **Độ bao phủ trên `src/aicefr/api/templates.py`:**
  - Statements: **115 / 115 (100%)**
  - Branches: **20 / 20 (100%)**
  - Partial branches: **0** (toàn bộ 3 partial branches từ A1 đã được phủ kín).
- **Lệnh thực thi whole-project coverage:**
  ```text
  Lệnh: .venv\Scripts\python.exe -m pytest -q -m "not smoke" --cov=aicefr --cov-branch --cov-report=term-missing --cov-report=json:docs/sdd/modules/m15-product-web/evidence/m15-task-001a-a2/coverage.json
  ```

### 4.5. Whole-Project Regression
```text
Lệnh: .venv\Scripts\python.exe -m pytest -q -m "not smoke"
Exit code: 1
Kết quả: 35 failed, 557 passed, 15 skipped, 2 deselected, 5 warnings in 78.87s
Phân tích nguyên nhân:
100% 35 failures xuất phát từ các test hạ tầng storage/privacy/billing/symlink trên môi trường Windows:
- Quyền tạo symlink trên Windows (PrivilegeNotHeld / error 1314): tests/api/test_data_operations_api.py, tests/auth/test_google_identity.py, tests/billing/test_gateways.py, tests/storage/test_privacy_migration.py.
- Xung đột khóa file Windows khi xóa thư mục tạm chứa database SQLite đang mở (WinError 32: The process cannot access the file because it is being used by another process): tests/storage/test_sqlite_memory_migration.py, tests/storage/test_w5_storage_foundation.py.
- Giả định POSIX UID (os.getuid): tests/storage/test_privacy_migration.py.
Toàn bộ các test thuộc phạm vi giao diện, template, identity API và student journey đều PASS 100%.
```

### 4.6. Browser QA (Playwright)
```text
Lệnh: .venv\Scripts\python.exe scripts/qa/m15_shell_browser.py --output-dir docs/sdd/modules/m15-product-web/evidence/m15-task-001a-a2 --base-revision 6baf720f173b440eb961676b09ea290058a39b35
Exit code: 0
Kết quả: 18 assertions passed, 17 screenshots taken, 0 console errors, 0 failed requests.
```

**Chi tiết 17 ảnh chụp kiểm thử và mã băm SHA-256 thực tế:**

| Tên file ảnh | Viewport | Theme / Media | SHA-256 (64 ký tự thực tế) |
| :--- | :--- | :--- | :--- |
| `student_upload_desktop_light.png` | 1280×800 | light | `3a851e98575a718f0e7d27b2e06ee8b37814a6c954066ccf8617698a6987d9d1` |
| `student_upload_desktop_dark.png` | 1280×800 | dark | `997b644dbe67b7ac3d032c7d11a44b3883c0a3c704becbc537c2487ccd124088` |
| `student_upload_mobile_light.png` | 390×844 | light | `11bd596fe7a7d81721dc30d78afb721cc05cf3679dd25368c173fc851c68a09b` |
| `student_upload_mobile-narrow_light.png` | 360×640 | light | `22e899ae3f62666e5a59740d0fcc083ae15ef00950cacc59875f72dd852f2891` |
| `student_report_desktop_light.png` | 1280×800 | light | `f0bece41e08723e64b4b399ea54cea0ee185a052fee9a5cfdb185bf890cd2d23` |
| `student_report_desktop_dark.png` | 1280×800 | dark | `deb24cc8884853b9cd4fd805924b41e21f337df123be0adb640d886c9321d55f` |
| `student_report_mobile_light.png` | 390×844 | light | `769de3c52f47e449f8fe073eb46cba3b1aba312008a7b47ad0df0109059e1ad5` |
| `student_report_mobile-narrow_light.png` | 360×640 | light | `c631ddf68d03b065e91d9d1de811a6ead6d2d3d4383c726a54017870c0823497` |
| `login_desktop_light.png` | 1280×800 | light | `972a67a775b05bc9a1407f4c9e2bc37d1af74a7158b4cd96ed736b5dbc33df45` |
| `login_desktop_dark.png` | 1280×800 | dark | `c854249161779cdb63644ac278000cd20c72b7f58a3f83e6b64a6794901bcd57` |
| `login_mobile_light.png` | 390×844 | light | `c2e4a08eeafdfc812a5fdc6598cd4f138f05797d501887df6712c6ccb9ff3937` |
| `login_mobile-narrow_light.png` | 360×640 | light | `cd3926a00d8f1beb4159590fff063dc479395c1a8973b03ed265ea535f596214` |
| `password-change_desktop_light.png` | 1280×800 | light | `b873a314dfdefd361beccfba8270073edd398de8d8e853f3731002a17f2873d9` |
| `password-change_desktop_dark.png` | 1280×800 | dark | `ee5e0b811fa10dd644fc67c81ebfc4aba3102b2f9ac5349b0ea49ac3ae321b2a` |
| `password-change_mobile_light.png` | 390×844 | light | `c184fd0aa9dd28dace12da4e8f236d1348c6be1e150402a945858769b88a5565` |
| `password-change_mobile-narrow_light.png` | 360×640 | light | `7cde8d1a6c9e3f2634d435b4dc74aa46a25ee2319a32a416f089d41f10c1ff4e` |
| `report_desktop_print.png` | 1280×800 | print | `864060f865640bf7cf0c4808441e57858bc9b8870695f57af646fe4e27b7f689` |

---

## 5. Tự đánh giá Clean Code, Accessibility và Bảo mật

- **Clean Code & Modularity:**
  - Không phân mảnh renderer: tiếp tục dùng hàm `_document` dùng chung để đảm bảo tính nhất quán trên toàn hệ thống web.
  - Tách bạch rõ rệt giữa logic xử lý dữ liệu và cấu trúc markup hiển thị.
  - Tuân thủ nghiêm ngặt chuẩn PEP 8 và linter `ruff` (độ dài dòng ≤ 100 ký tự, định dạng nhất quán).
- **Accessibility (A11y):**
  - Đảm bảo trật tự landmark HTML5 chuẩn mực: mỗi trang sở hữu đúng một skip link hợp lệ, đúng một thẻ landmark `<main id="main">` có `tabindex="-1"`, và đúng một tiêu đề cấp 1 `<h1>`.
  - Tương phản màu sắc (WCAG AA): tất cả văn bản trên nút bấm và liên kết ở cả chế độ sáng, tối, và trạng thái hover đều có tỷ lệ tương phản computed ≥ 4.5:1 (đạt từ 6.90:1 đến 10.71:1).
  - Tuân thủ tùy chọn người dùng: tự động triệt tiêu các hiệu ứng chuyển động khi người dùng bật `prefers-reduced-motion`.
  - Thiết kế đáp ứng (Responsive): các vùng tương tác chạm (touch targets) đạt tối thiểu 44px (`min-height: 2.75rem`), văn bản tự động xuống dòng an toàn (`overflow-wrap: anywhere`), không gây thanh cuộn ngang ngoài ý muốn.
- **Security & Data Privacy:**
  - Giữ nguyên cơ chế escaping an toàn trên toàn bộ các chuỗi đầu vào (`html.escape`).
  - Không sửa đổi logic xác thực, cookie, session hay cấu trúc biểu mẫu form POST của M11 Identity.
  - Toàn bộ dữ liệu kiểm thử phục vụ QA là dữ liệu giả lập (fixture) cục bộ; không gọi API ra mạng ngoài (`external_requests_blocked == 0`).
