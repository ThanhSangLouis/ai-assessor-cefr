# Kế hoạch 1 ngày: chuẩn hoá form quản lý của giảng viên

Ngày soạn: 15/11/2026. Phạm vi: các form quản lý mà vai trò `teacher` dùng — Lớp học (`/teach/classes`, `/teach/classes/{id}`), Đề đánh giá (`/teach/tasks`), Lộ trình luyện (`/teach`, các hộp thoại tạo lộ trình/chặng/bài học/ghép lộ trình). Mục tiêu: các form này theo đúng một khuôn với form quản trị (`/admin`, tab Tài khoản) và trang Tài khoản (`/account`), trong thế giới "Thời khoá biểu khoa" ([docs/design/teacher/README.md](../design/teacher/README.md)).

Không đổi API, contract, quyền hay rubric. Chỉ đổi template, JS dựng giao diện và CSS.

## 1. Mẫu thiết kế form đang có (nguồn chuẩn)

Rút từ `admin.html` (Tạo tài khoản, Danh sách tài khoản), `account.html`, `teach_tasks.html` (hộp thoại đề) và `style.css`/`staff.css`.

| Khối | Cấu trúc chuẩn | Nơi đang dùng đúng |
|---|---|---|
| Thẻ form tạo nhanh | `section.card` → `h2` (biểu tượng + tên việc) → `p.muted` giải thích 1 câu → `form.inline-form` | Admin › Tạo tài khoản |
| Ô nhập trong form ngang | `div.field` → `label for` + `input/select/textarea`; ô dài dùng `.field.field-wide`; gợi ý dùng `p.field-hint` | Admin › Tạo tài khoản |
| Hàng nút | `div.button-row` (chiếm hết hàng trong `.inline-form`): **một** nút cam cho việc chính, các nút khác `.secondary`; vùng `aria-live` báo trước kết quả | Admin, Account |
| Thẻ danh sách | `section.card` → `div.list-toolbar` (`h2` trái, `div.toolbar-controls` phải: CSV, tìm kiếm, lọc) → `div.table-scroll` → `table` | Admin › Danh sách tài khoản |
| Bảng | `th` nền lõm, kẻ mảnh giữa hàng và cột, số dùng `tabular-nums`, dòng phụ `span.cell-sub` | Admin, Lớp (chi tiết) |
| Thao tác theo hàng | `div.row-actions`: nút phụ viền trắng; thao tác phá huỷ `button.danger` chỉ viền đỏ, đứng tách bên phải, có `aria-label` nêu rõ đối tượng | Admin |
| Trạng thái | `span.badge` (`COMPLETED` đang dùng, `FAILED` đã tắt, `REVIEW_REQUIRED` chờ…); band dùng `.band-chip[data-band]` | Admin, Lộ trình |
| Hộp thoại sửa/tạo | `dialog.sheet` (`.wide` khi nhiều ô) → `form.stack` `novalidate` → `h2` → các cặp `label`/ô → `.field-row` cho 2 ô ngắn cạnh nhau → `.field-hint` → `.button-row` (Lưu cam + Huỷ `.secondary`) | Đề đánh giá |
| Phản hồi | `window.toast(msg, "ok"/"error")`; xác nhận phá huỷ bằng `window.confirm` nêu số lượng/đối tượng | Toàn bộ |

Quy tắc chung (README teacher/admin): không ô biểu tượng cạnh tiêu đề trang; tiêu đề Poppins cam; không tô nền cam cho thẻ; nhãn "không bắt buộc" viết bằng `span.muted` trong label.

## 2. Chỗ lệch ở form giảng viên

| # | Trang / tệp | Lệch so với mẫu | Sửa thành |
|---|---|---|---|
| L1 | Lớp học — `static/classes.js` (`listView`, `detailView`) | Dùng `<label class="field"><span>…</span><input></label>` thay vì `div.field > label + input`; nút submit nằm trơ, không trong `.button-row`; ô email không có `.field-wide` | Khuôn ô nhập và hàng nút như Admin › Tạo tài khoản |
| L2 | Lớp học — danh sách lớp | `ul.plain-list` + `assign-row`, không thanh công cụ, không tìm/lọc | `.list-toolbar` (tìm theo tên lớp, lọc Đang dùng/Lưu trữ) + bảng: Lớp · Sinh viên · Giảng viên · Trạng thái (`badge`) |
| L3 | Lớp học — chi tiết | "Xoá khỏi lớp", "Bỏ phân công" là nút `.secondary` thường, không xác nhận, không `row-actions` | `row-actions` + `button.danger` viền đỏ, `aria-label` có tên sinh viên, `confirm()` trước khi xoá |
| L4 | Lớp học — thẻ | `card-head > h2` không biểu tượng, trong khi Admin/Account có biểu tượng ở `h2` của thẻ | Thêm biểu tượng `users-plus`/`users`/`layers` cho `h2` thẻ, giữ tiêu đề trang không biểu tượng |
| L5 | Đề đánh giá — `teach_tasks.html` | Thanh công cụ riêng `.bank-toolbar` thay vì `.list-toolbar/.toolbar-controls`; nút "Tắt" đề là `.secondary`, không phải phá huỷ viền đỏ như "Tắt" tài khoản | Dùng `.toolbar-controls`; nút Tắt/Bật đặt trong `row-actions` (nút phụ, đã chốt 15/11) |
| L6 | Lộ trình — `teach_paths.html` | 4 hộp thoại thiếu `novalidate`; nhãn "(không bắt buộc)" viết thẳng trong chữ thay vì `span.muted` | Thêm `novalidate`, `span.muted` cho phần phụ. **Không** thêm `.stack` (đo 15/11: `.stack` đẩy khoảng nhãn→ô lên 24px, xem mục 6, P5) |
| L7 | `static/staff.css` | Không có luật nào cho `.inline-form`, `dialog.sheet`, `label`, `.field-hint` trong thế giới staff → form giảng viên lấy kiểu chung của trang sinh viên (nhãn, bo góc, khoảng cách khác nhau) | Thêm một khối "Form" ngắn, phạm vi `body.staff`: nhãn chữ mực 600, bo 8px, khoảng cách ô đều, `dialog.sheet` nền trắng viền mảnh, tiêu đề hộp thoại Poppins |
| L8 | Kiểm tra dữ liệu | Lớp học dựa vào `required` của trình duyệt; Admin và Đề dùng `novalidate` + toast lỗi tiếng Việt | Thống nhất `novalidate` + kiểm tra trong JS + `window.toast(…, "error")`, focus về ô sai |

## 3. Kế hoạch trong 1 ngày (≈ 8 giờ)

| Khung giờ | Việc | Tệp | Xong khi |
|---|---|---|---|
| 08:00–08:45 | Chạy app với dữ liệu demo theo [CHAY_DU_AN_CHO_AI.md](CHAY_DU_AN_CHO_AI.md); chụp ảnh **trước** 1440 px sáng/tối và 390 px cho 4 màn: Lớp (danh sách, chi tiết), Đề, Lộ trình (mở từng hộp thoại) | `docs/design/teacher/evidence/before/` | Có 8–10 ảnh "trước" |
| 08:45–09:30 | L7: thêm khối "Form" vào `staff.css` (label, input/select/textarea, `.inline-form`, `.field-hint`, `dialog.sheet`, `.list-toolbar`) — chỉ trong `body.staff`, không đụng `style.css` của sinh viên | `static/staff.css` | Form Admin › Tạo tài khoản trông như cũ; hộp thoại Đề/Lộ trình đổi theo |
| 09:30–11:30 | L1–L4, L8: viết lại phần dựng HTML của `classes.js` — form tạo lớp, form thêm sinh viên, form phân công giảng viên theo khuôn `div.field`/`.button-row`; danh sách lớp thành `.list-toolbar` + bảng (tìm, lọc lưu trữ ở phía client, không đổi API); thao tác xoá thành `row-actions` + `button.danger` + `confirm()` | `static/classes.js`, `templates/classes.html` | Các id/name ô form giữ nguyên (`new-class`, `members-form`, `teachers-form`, `name`, `list`, `email`) để test và e2e không gãy |
| 11:30–12:00 | Kiểm tra nhanh trên trình duyệt: tạo lớp, thêm/xoá sinh viên, admin phân công giảng viên | — | Không lỗi console, toast đúng |
| 13:00–14:15 | L5: đổi `.bank-toolbar` sang `.list-toolbar/.toolbar-controls`, nút Tắt/Bật theo `row-actions`; xoá CSS `.bank-toolbar` thừa trong `style.css` nếu không còn ai dùng | `templates/teach_tasks.html`, `static/teach_tasks.js`, `static/style.css` | Tìm, lọc, thêm, sửa, tắt/bật đề vẫn chạy |
| 14:15–15:15 | L6: 4 hộp thoại Lộ trình — `novalidate`, `span.muted`, `.field-row` đồng nhất; kiểm tra JS submit của `teach_paths.js` vẫn đọc đúng ô | `templates/teach_paths.html`, `static/teach_paths.js` | Tạo lộ trình, chặng, bài học, ghép lộ trình vẫn chạy |
| 15:15–16:15 | Kiểm thử tự động (mục 4) và sửa lỗi phát sinh | `tests/test_classes.py` và test liên quan | Lint + test tập trung xanh |
| 16:15–17:00 | Chụp ảnh **sau** cùng khung, cập nhật `docs/design/teacher/README.md` (thêm hàng "Form quản lý" vào bảng Thành phần chính), rà `git diff`, ghi nhật ký AI vào sheet tuần | `docs/design/teacher/` , `docs/evidence/tc2-3-ai-usage/` | Bàn giao cho chủ dự án duyệt; **không tự commit** |

Đệm rủi ro: nếu trễ, cắt L2 (tìm/lọc danh sách lớp) sang ngày sau — đây là phần thêm chức năng, các phần còn lại chỉ là đồng bộ giao diện.

## 4. Kiểm tra

```bash
ruff check src tests tools scripts
pytest --no-cov tests/test_classes.py tests/test_d071_accounts_and_classes.py tests/test_d076_prompt_bank.py tests/test_d068_navigation.py -q
python scripts/ci/check_md_links.py
```

- Mở rộng `tests/test_classes.py::test_the_pages_render` nếu đổi template `classes.html`.
- E2E (`tests/e2e/test_ui_e2e.py`, `test_lessons_e2e.py`) chạm các id form trên: chạy nếu máy có Mongo + Playwright, không thì ghi `NOT_RUN`.
- Kiểm tra tay: bàn phím (Tab qua form, Esc đóng hộp thoại), giao diện tối, 390 px (ô xếp một cột, nút đủ rộng).

## 5. Rủi ro và điểm cần chủ dự án chốt

- **Tìm/lọc danh sách lớp (L2)**: đã chốt 15/11 — chưa làm; danh sách lớp chỉ đổi thành bảng.
- **"Tắt" đề (L5)**: đã chốt 15/11 — nút phụ, không viền đỏ. Chiều cao điều khiển 40px desktop / 44px điện thoại áp cho cả Admin: đã chốt 15/11.
- Lớp học được admin dùng chung: mọi thay đổi ở `classes.js` phải giữ nhánh `isAdmin` (ô email giảng viên, phân công/bỏ phân công).
- `staff.css` cũng áp cho trang Admin: sau L7 phải chụp lại tab Tài khoản để chắc không lệch.
- Ảnh trong `evidence/` là dữ liệu demo, không dùng dữ liệu người học thật.

## 6. Đo thực tế ngày 15/11/2026 (bản `main` 04375678)

Chạy app trên máy (MongoDB 8.3 cục bộ, artifact giả lập, 4 tài khoản demo), chụp bằng Chrome qua Playwright ở 1440 × 900 và 390 × 844, giao diện sáng. Ảnh và số đo: [docs/design/teacher/forms/before/](../design/teacher/forms/before/), script: [measure_forms.py](../design/teacher/forms/measure_forms.py). Số dưới đây là `getBoundingClientRect` (x, y, rộng, cao, px).

| # | Màn | Đo được | Lỗi | Mức |
|---|---|---|---|---|
| P1 | Lớp › Tạo lớp mới, 1440 | ô `name` y 189–232 (cao 43); nút "Tạo lớp" y 202–240 (cao 38, `margin-top` 16) | Nút thấp hơn ô **8px** ở mép dưới, 13px ở mép trên; không thẳng hàng | Cao |
| P2 | Lớp › Tạo lớp mới, 1440 | ô `name` rộng **179px** | Chữ gợi ý bị cắt ("…nhóm 03" → "nhón") | Cao |
| P3 | Lớp › Thêm sinh viên, 1440 | ô `list` rộng 308px, nút "Thêm" lệch 8px như P1 | Gợi ý bị cắt, nút lệch | Cao |
| P4 | Lớp › cả hai form, 390 | ô rộng 179px / 308px trong thẻ 324px, nút rộng 324px; ô→nút cách 36px | Ô hẹp hơn nút, khoảng trống phình | Cao |
| P5 | Đề › hộp thoại Thêm đề, 1440 | nhãn→ô: **24px** (nhãn "Band" đáy 280, dropdown đỉnh 304; "Đề bài" đáy 377, textarea 400) do `form.stack` cộng 16px | Nhãn trôi giữa hai ô; Lộ trình chỉ 8px → hai hộp thoại khác nhau | Cao |
| P6 | Đề › hộp thoại, 1440 | dropdown Band rộng **734px** cho giá trị 2 ký tự | Phình | Trung |
| P7 | Đề › thanh công cụ, 1440 | ô tìm 1038 × 43, dropdown trạng thái 1038 × 36, nút "Thêm đề" xuống hàng 3; cả thanh cao **133px** | Phình: 3 hàng cho 3 điều khiển (luật `.bank-toolbar select` không áp được vì `common.js` thay `select` bằng `.c-dropdown`) | Cao |
| P8 | Đề › thẻ ngân hàng | `padding-top` thẻ 8px, các thẻ khác 24px | Lệch nhịp | Thấp |
| P9 | Mọi form staff | ô một dòng cao **43px**, dropdown `.c-dropdown-trigger` **36px**, nút **38px** | Ba chiều cao khác nhau cạnh nhau (cả Admin) | Trung |
| P10 | Admin › Tạo tài khoản (mẫu) | nhãn "Vai trò" y 327, nhãn "Email" y 269 (hàng căn đáy) | Chấp nhận được ở mẫu; không nhân bản sang form giảng viên | Thấp |

Không có tràn ngang ở cả hai khung. Hộp thoại Lộ trình (P-ok): nhãn→ô 8px, hai band cạnh nhau 239px mỗi ô, nút Lưu/Huỷ thẳng hàng — giữ làm mẫu cho hộp thoại.

Thông số đích và tiêu chí nghiệm thu: [BRIEF_ANTIGRAVITY_FORM_GIANG_VIEN.md](BRIEF_ANTIGRAVITY_FORM_GIANG_VIEN.md).
