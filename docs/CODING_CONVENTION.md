# Quy tắc viết mã của nhóm

Tài liệu gom các quy tắc nhóm đã thống nhất và **đang áp dụng thật**. Mỗi quy tắc có cột "Kiểm ở đâu": một công cụ, một test hoặc một bước CI chặn khi vi phạm. Quy tắc nào chưa có máy kiểm thì ghi "review PR".

Áp dụng cho toàn repo từ 13/09/2026. Cập nhật lần cuối 28/11/2026.

## 1. Ngôn ngữ

Nguyên tắc: **ai đọc thì viết bằng ngôn ngữ của người đó.** Máy và lập trình viên đọc thì viết tiếng Anh; người học, giảng viên và hội đồng đọc thì viết tiếng Việt. Nguồn: [SPEC_WEB.md mục 10b](web/SPEC_WEB.md#10b-quy-ước-ngôn-ngữ-trong-mã-nguồn).

| Thành phần | Ngôn ngữ | Kiểm ở đâu |
| --- | --- | --- |
| Tên hàm, biến, lớp, tệp, lớp CSS, id phần tử | Tiếng Anh | review PR |
| Comment, docstring, tên test | Tiếng Anh | review PR |
| Đường dẫn URL (`/login`, `/report/{id}`) | Tiếng Anh | review PR |
| Chuỗi hiển thị cho người dùng | Tiếng Việt có dấu | review PR; E2E trình duyệt (`tests/e2e/`) đọc đúng chữ tiếng Việt trên trang |
| Tài liệu trong `docs/` | Tiếng Việt | review PR |
| Thực thể trong sơ đồ lớp, ERD | Tiếng Anh, đúng tên trong mã | `tests/test_class_diagram_in_code.py` |

Giao diện cho người học không hiện tên mô hình hay chi tiết kỹ thuật ("Whisper", "Ridge", "DeBERTa").

## 2. Python

| Quy tắc | Giá trị | Kiểm ở đâu |
| --- | --- | --- |
| Phiên bản tối thiểu | Python 3.10 (`target-version = "py310"`), CI chạy 3.12 | `pyproject.toml`, CI |
| Định dạng | `ruff format`, dòng tối đa 100 ký tự | CI: `ruff format --check src tests tools` |
| Lint | `ruff check`, nhóm luật E, F, I (isort), UP, B (bugbear) | CI: `ruff check src tests tools scripts` |
| Thứ tự import | isort qua ruff, `aicefr` là first-party | `[tool.ruff.lint.isort]` |
| `Depends`, `Form`, `File` trong tham số mặc định | Cho phép (cách dùng đúng của FastAPI), khai một lần ở cấu hình, không rải `noqa` | `[tool.ruff.lint.flake8-bugbear]` |
| Kiểu dữ liệu | Có type hint cho hàm công khai; hợp đồng giữa module dùng Pydantic trong `src/aicefr/contracts.py` | review PR |
| Phụ thuộc giữa lõi và hạ tầng | Lõi gọi qua port (`ports.py`), không nhắc tên adapter | `tests/test_ports.py` |

## 3. JavaScript (giao diện)

Mã giao diện là các tệp `<script>` thường trong `src/aicefr/api/static/`, không có bundler.

| Quy tắc | Giá trị | Kiểm ở đâu |
| --- | --- | --- |
| Lint | ESLint 9, `js.configs.recommended`, `sourceType: "script"` | CI job `Lint JavaScript (ESLint)`, `eslint.config.mjs` |
| Biến toàn cục | Không đặt tên trùng biến có sẵn của trình duyệt (`open`, `name`, `status`…), vì tệp nào nạp sau cũng thấy | ESLint `no-redeclare`, `no-global-assign` |
| Hàm dùng chung | Đặt trong `common.js`, nạp trước các tệp trang | review PR |
| Chèn dữ liệu vào HTML | Luôn qua `escapeHtml(...)` | review PR, CodeQL |

## 4. Nhánh, commit và pull request

Áp dụng từ W12 (30/11/2026). Chi tiết luồng nhánh: [QUY_TRINH_NHANH.md](plan/QUY_TRINH_NHANH.md).

| Quy tắc | Kiểm ở đâu |
| --- | --- |
| Không đẩy thẳng lên `dev` hay `production`; mọi thay đổi qua pull request | Branch protection của `dev`, `production` |
| Tên nhánh `loai/nguoi/SCRUM-<số>-mo-ta`, ví dụ `feat/nguyen/SCRUM-130-sus-survey`; `loai` ∈ `feat`, `fix`, `docs`, `test`, `refactor`, `ci`, `ui`, `hotfix` | Job CI `Ma Jira trong PR`, review PR |
| Nhánh mới tạo từ `origin/dev` mới nhất; cập nhật bằng cách merge `origin/dev` vào, trước khi code và trước khi push | review PR |
| Commit: `SCRUM-<số>: <việc đã làm>`; việc theo quyết định thêm mã quyết định (`SCRUM-130: D113 …`) | review PR |
| Tiêu đề PR `[SCRUM-<số>] <tóm tắt>` | Job CI `Ma Jira trong PR` |
| Ít nhất **một thành viên khác** duyệt PR trước khi merge | Branch protection của `dev` (1 lượt duyệt bắt buộc) |
| PR chỉ merge khi CI xanh; vào `dev` bằng squash | Branch protection, `.github/workflows/ci.yml` |
| PR vào `production` chỉ từ `dev` (phát hành, merge commit) hoặc `hotfix/*` | Job CI `Nhanh nguon cua PR vao production` |
| Một PR một việc; không trộn tái cấu trúc với tính năng | review PR |
| Không force push, không merge nhánh của người khác vào nhánh mình | Branch protection, review PR |
| Merge vào `production` là tự deploy lên EC2 | `.github/workflows/deploy.yml` |

## 5. Tệp không được commit

| Loại | Kiểm ở đâu |
| --- | --- |
| `.env`, khoá, token, mật khẩu thật | `.gitignore`, CI job `Quet lo khoa bi mat` (gitleaks), `.gitleaksignore` chỉ ghi báo nhầm đã xác minh |
| Bản ghi âm, trọng số mô hình, cơ sở dữ liệu | CI bước `Chặn audio, model, DB, bí mật` (`scripts/ci/check_forbidden_files.py`) |
| Số đo trên Speak & Improve (dữ liệu phi thương mại) | review PR; số đo giữ ở hồ sơ nội bộ ngoài repo |

## 6. Dữ liệu và lược đồ

| Quy tắc | Kiểm ở đâu |
| --- | --- |
| Đổi cấu trúc kho (collection, index) phải qua một migration có số thứ tự trong `src/aicefr/storage/migrations.py`, không sửa lặng lẽ `INDEXES` | `tests/test_schema.py` so với `docs/db/schema_core.json` |
| Migration phải chạy lại được nhiều lần (idempotent) | `tests/test_schema.py`, review PR |
| Số migration không trùng giữa các nhánh: trước khi merge, đánh lại số theo `main` | review PR |

## 7. Kiểm thử

| Quy tắc | Kiểm ở đâu |
| --- | --- |
| Sửa lỗi: viết test tái hiện lỗi trước, thấy đỏ, sửa rồi thấy xanh | review PR |
| Tên test là một câu tiếng Anh mô tả hành vi (`test_a_short_password_opens_no_account`) | review PR |
| Độ phủ không dưới 70 % | CI: `pytest --cov-fail-under=70` |
| Thay đổi API: cập nhật `docs/sdd/api/` bằng `python tools/export_openapi.py` | `tests/test_openapi_export.py` |
| Tính năng có kế hoạch kiểm thử riêng `docs/test/TEST_PLAN_D*.md` | review PR, [kế hoạch tổng](test/TEST_PLAN.md) |

## 8. Tài liệu đi cùng mã

| Quy tắc | Kiểm ở đâu |
| --- | --- |
| Quyết định mới ghi vào lịch sử phiên bản SRS và mục tương ứng của SDD | review PR |
| Link Markdown trong repo không được hỏng | CI: `scripts/ci/check_md_links.py` |
| Sơ đồ lớp khớp mã | `tests/test_class_diagram_in_code.py` |
| Dùng AI thì ghi nhật ký vào workbook tuần ở `docs/evidence/tc2-3-ai-usage/` | review PR |
