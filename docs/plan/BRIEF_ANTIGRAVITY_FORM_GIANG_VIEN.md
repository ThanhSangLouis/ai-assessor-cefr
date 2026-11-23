# Brief cho Antigravity: form quản lý của giảng viên, chuẩn từng pixel

Soạn 15/11/2026 trên `main` 04375678. Kế hoạch đầy đủ và bảng lỗi đo được: [KE_HOACH_FORM_GIANG_VIEN.md](KE_HOACH_FORM_GIANG_VIEN.md) (mục 2 và 6). Ảnh "trước" và số đo: [docs/design/teacher/forms/before/](../design/teacher/forms/before/).

## Mục tiêu

Form quản lý của giảng viên (Lớp học, Đề đánh giá, Lộ trình luyện) theo đúng một khuôn với Admin › Tạo tài khoản, trong thế giới "Thời khoá biểu khoa" ([docs/design/teacher/README.md](../design/teacher/README.md)): ô, nhãn, nút thẳng hàng tới từng pixel, không ô nào phình rộng hay cao hơn nội dung cần, không khoảng trống thừa.

## Phạm vi được sửa

- `src/aicefr/api/static/staff.css` — thêm một khối "Form" (chỉ dưới `body.staff`).
- `src/aicefr/api/static/classes.js`, `src/aicefr/api/templates/classes.html`
- `src/aicefr/api/static/teach_tasks.js`, `src/aicefr/api/templates/teach_tasks.html`
- `src/aicefr/api/templates/teach_paths.html` (và `static/teach_paths.js` chỉ khi đổi markup buộc phải đổi JS)
- `src/aicefr/api/static/style.css` — chỉ được **xoá** luật `.bank-toolbar` khi không còn ai dùng. Không sửa luật chung khác: trang sinh viên dùng chung tệp này.

## Ràng buộc

- Không đổi API, payload, quyền, route. Không đổi `id`/`name` của form và ô: `new-class`, `members-form`, `teachers-form`, `name`, `teachers`, `list`, `email`, `task-form`, `task-band`, `task-text`, `task-keywords`, `bank-search`, `bank-state`, `bank-add`, `path-form`, `unit-form`, `lesson-form`, `compose-form`, `compose-save` và các ô bên trong (test và e2e bám vào chúng).
- Giữ nhánh `isAdmin` trong `classes.js` (ô email giảng viên, phân công/bỏ phân công).
- Chỉ dùng token có sẵn (`--sp-*`, `--t-*`, `--border*`, `--bg-*`, `--brand*`, `--danger`); không số màu mới. Sáng, tối đều phải đúng.
- `common.js` thay mọi `<select>` bằng `.c-dropdown` > `button.c-dropdown-trigger`: CSS phải nhắm `.c-dropdown`/`.c-dropdown-trigger`, không nhắm `select`.
- Không đặt biểu tượng cạnh tiêu đề trang, không sọc màu bên trái, không nền cam cho thẻ (README teacher, mục "Không làm").
- **Không commit, không push.** Xong thì để nguyên working tree cho chủ dự án duyệt.

## Thông số đích (nghiệm thu bằng số đo, sai số ghi rõ)

Đo bằng `getBoundingClientRect` tại 1440 × 900 và 390 × 844, giao diện sáng, rồi chụp lại tối.

| Mã | Thông số | 1440 | 390 | Sai số |
|---|---|---|---|---|
| S1 | Chiều cao ô một dòng (`input`), `.c-dropdown-trigger`, nút trong form và thanh công cụ | 40px cả ba | 44px cả ba | 0 |
| S2 | Khoảng nhãn → ô của nó (đáy nhãn tới đỉnh ô) | 8px | 8px | 0 |
| S3 | Khoảng giữa hai cụm nhãn+ô liên tiếp (đáy ô trên tới đỉnh nhãn dưới) | 16px | 16px | 0 |
| S4 | Gợi ý `.field-hint` dưới ô | cách đáy ô 8px | 8px | 0 |
| S5 | Form một ô (Tạo lớp, Thêm sinh viên, Phân công GV): ô và nút **cùng hàng**, mép trên và mép dưới nút trùng mép ô | Δy = 0 | ô trên, nút dưới, cả hai rộng 100% thẻ, cách nhau 12px | 0 |
| S6 | Bề rộng ô "Tên lớp" | 360px | 100% thẻ (324px) | ±1 |
| S7 | Bề rộng ô danh sách email (Thêm sinh viên, Email giảng viên) | co giãn, tối thiểu 360px, tối đa 640px | 100% | ±1 |
| S8 | Chữ gợi ý (placeholder) hiện trọn trong ô ở 1440 | không bị cắt | được phép cắt ở 390 | — |
| S9 | Thanh công cụ Đề (`.bank-toolbar` → `.list-toolbar`/`.toolbar-controls`): ô tìm, dropdown trạng thái, nút "Thêm đề" trên **một hàng** | cao 40px; dropdown 160px; ô tìm co giãn tối đa 420px; nút sát phải | xếp dọc, mỗi điều khiển 100%, cách 8px | 0 |
| S10 | Dropdown Band trong hộp thoại Thêm đề | đặt trong `.field-row`, rộng bằng 1 cột (như Lộ trình, ~ (rộng form − 16)/2) | 100% | ±1 |
| S11 | Hộp thoại: nhãn→ô và nhịp giữa cụm của Thêm đề **giống hệt** Lộ trình mới (bỏ `.stack` ở `#task-form`, không thêm `.stack` vào form Lộ trình) | S2, S3 | S2, S3 | 0 |
| S12 | Hàng nút cuối hộp thoại: cách đáy ô/gợi ý cuối 24px; Lưu (cam) rồi Huỷ (viền), cách 12px | như mô tả | hai nút 100%, cách 12px | 0 |
| S13 | Padding thẻ (`.card`) | 24px mọi cạnh, gồm thẻ ngân hàng Đề (đang 8px trên) | 16px | 0 |
| S14 | Nút phá huỷ theo hàng ("Xoá khỏi lớp", "Bỏ phân công"): `row-actions` + `button.danger` viền đỏ, cao 32px (`.small`), có `aria-label` nêu tên người, `confirm()` trước khi gọi API | | | — |
| S15 | Danh sách lớp: `.list-toolbar` (h2 trái) + bảng `table-scroll`: Lớp · Sinh viên · Giảng viên · Trạng thái (`badge`) | | bảng cuộn ngang trong khung, trang không tràn | — |
| S16 | Không tràn ngang trang (`scrollWidth == clientWidth`), không lỗi console, focus thấy rõ khi Tab | ✔ | ✔ | — |

S1 áp cho cả Admin vì cùng `staff.css`: chụp lại Admin › Tạo tài khoản và xác nhận chỉ đổi chiều cao điều khiển, không vỡ bố cục.

## Cách chạy và đo

App cần MongoDB. Trên máy Windows của nhóm không có Docker thì dùng MongoDB cục bộ:

```bash
"/c/Program Files/MongoDB/Server/8.3/bin/mongod.exe" --dbpath <thư-mục-tạm> --port 27019 --bind_ip 127.0.0.1
```

```bash
export AICEFR_DB="mongodb://localhost:27019/aicefr" AICEFR_MODEL_DIR="$PWD/tests/fixtures/models" PYTHONIOENCODING=utf-8
export AICEFR_MODEL_PINS="$(awk '{sub(/\.json$/, "", $2); printf "%s%s=%s", sep, $2, $1; sep=","}' "$AICEFR_MODEL_DIR/SHA256SUMS")"
```

```bash
.venv/Scripts/python.exe -m aicefr.accounts_cli them --email gv-01@demo.speakup.fit --vai-tro teacher --mat-khau matkhau123
```

(Làm tương tự cho `qt-01` vai trò `admin`, `sv-001`, `sv-002` vai trò `student`; hoặc `./demo.sh` nếu có Docker.)

```bash
.venv/Scripts/python.exe -m uvicorn aicefr.api.main:app --port 8000
```

```bash
.venv/Scripts/python.exe docs/design/teacher/forms/measure_forms.py docs/design/teacher/forms/after
```

So `after/measure.json` với bảng S1–S16; đặt ảnh `after/*.png` cạnh `before/*.png` cùng tên. Script dùng Chrome đã cài (`channel="chrome"`).

## Lệnh kiểm tra bắt buộc

```bash
ruff check src tests tools scripts
```

```bash
.venv/Scripts/python.exe -m pytest --no-cov -q tests/test_classes.py tests/test_d071_accounts_and_classes.py tests/test_d076_prompt_bank.py tests/test_d068_navigation.py
```

```bash
python scripts/ci/check_md_links.py
```

E2E (`tests/e2e/test_ui_e2e.py`, `test_lessons_e2e.py`) cần `AICEFR_TEST_MONGO` + Playwright: chạy nếu được, không thì ghi `NOT_RUN`.

## Bàn giao lại

1. Danh sách tệp đã đổi.
2. Bảng S1–S16: giá trị đo được sau khi sửa, đạt/không đạt.
3. Ảnh `after/` 1440 sáng, 1440 tối, 390 cho: Lớp (danh sách, chi tiết), Đề (trang, hộp thoại), Lộ trình (hộp thoại Lộ trình mới), Admin › Tài khoản.
4. Kết quả thật của các lệnh kiểm tra; mục nào chưa chạy ghi `NOT_RUN`.
5. Không commit.

## Quyết định đã chốt (chủ dự án, 15/11/2026)

- Chiều cao điều khiển 40px desktop / 44px điện thoại, áp cho cả Admin (S1).
- Nút "Tắt" đề là nút phụ (viền trắng), không viền đỏ: tắt đề bật lại được, không mất dữ liệu.
- Chưa làm tìm/lọc danh sách lớp; S15 chỉ đổi danh sách thành bảng.
