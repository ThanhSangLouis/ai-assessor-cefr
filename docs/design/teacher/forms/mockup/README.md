# Mockup form staff

Sáu màn HTML tĩnh dựa trên markup/CSS hiện hành tại `FE-Teacher`, HEAD `04375678`.
Chỉ tạo tệp trong thư mục này. Dữ liệu là demo, email `@demo.speakup.fit`.

| Trang | Nội dung |
|---|---|
| [classes-list.html](classes-list.html) | Tạo lớp một ô, bảng 3 lớp; chưa thêm tìm/lọc lớp |
| [classes-detail.html](classes-detail.html) | Thêm sinh viên, bảng 3 sinh viên, giảng viên và nhóm band |
| [tasks.html](tasks.html) | Tab band, thanh công cụ một hàng, bảng đề; Tắt là nút phụ |
| [tasks-dialog.html](tasks-dialog.html) | Cùng trang Đề, hộp thoại Thêm đề đang mở |
| [path-dialog.html](path-dialog.html) | Trang Lộ trình, hộp thoại Lộ trình mới đang mở |
| [admin-accounts.html](admin-accounts.html) | Quản trị › Tài khoản, giữ cấu trúc form nhiều ô của Admin |

## Xem và đo lại

Chạy từ gốc repo, không cài thêm gói:

```powershell
.venv/Scripts/python.exe docs/design/teacher/forms/mockup/verify_mockups.py --serve
```

Mở <http://127.0.0.1:8765/docs/design/teacher/forms/mockup/classes-list.html>.
Thêm `?theme=dark` vào từng trang để xem tối. Script chỉ phục vụ tệp tĩnh cục bộ;
ánh xạ `/static/` để font Poppins trong CSS gốc tải đúng. Mở bằng `file://` có thể
không tải được font/biểu tượng do URL tuyệt đối và hạn chế của trình duyệt.

```powershell
.venv/Scripts/python.exe docs/design/teacher/forms/mockup/verify_mockups.py --static-only
.venv/Scripts/python.exe docs/design/teacher/forms/mockup/verify_mockups.py
```

Lệnh cuối dùng Python Playwright, `channel="chrome"`, đo `getBoundingClientRect`,
thử Tab, thu lỗi console, chụp 24 ảnh: 6 trang × 2 kích thước × sáng/tối.
Ảnh khung nhìn và số đo được ghi trong `evidence/`. Các nút/menu chỉ minh hoạ;
mockup không gọi API, không làm nghiệp vụ hoặc triển khai quản lý focus bằng JS.

## Lớp mới

- `.inline-form.one-line`: form tạo nhanh, desktop căn ô/nút cùng hàng, điện thoại xếp dọc.
- `.field-name`: ô tên lớp rộng 360px desktop.
- `.field-list`: ô email rộng 360–640px desktop, 100% điện thoại; dùng lại cho nhánh Admin.
- `.classes-table`, `.members-table`: bảng tối thiểu 640px, cuộn trong `.table-scroll`.
- `.mockup-backdrop`, `.mockup-dialog`: riêng minh hoạ `<dialog open>`; thay cho backdrop native.

`.field`, `.field-row`, `.field-hint`, `.list-toolbar`, `.toolbar-controls`, `.row-actions`
là lớp đã có, được tái sử dụng. Dropdown giữ đúng thứ tự của `enhanceSelect`:
trigger (label + arrow), menu, rồi select gốc ẩn; bổ sung `aria-label` cho trigger tĩnh.
Các `id`/`name` của form/ô hiện diện được giữ nguyên. Trong teacher view, thẻ giảng viên
chỉ đọc, đúng nhánh `!isAdmin`; không hiển thị quyền phân công của Admin.

## Ánh xạ và kết quả S1–S16

Kết quả dưới đây đã đo bằng Chrome tại 1440 × 900 và 390 × 844, cả sáng/tối.
“Đạt” chỉ nói về phép kiểm tra mockup, không thay thế nghiệm thu nghiệp vụ.

| Mã | Selector / luật trong forms-staff.css | Đích desktop / điện thoại | Kiểm chứng hiện tại |
|---|---|---|---|
| S1 | `input:not(...)`, `.c-dropdown button.c-dropdown-trigger`, nút trong `.inline-form`, `.toolbar-controls`, `dialog.sheet` | 40 / 44px; nút theo hàng thuộc S14/V3 | Đạt |
| S2 | `.field` gap `--sp-2`; `.field > label` bỏ margin, giữ weight 650 | Nhãn → ô 8px cả hai | Đạt |
| S3 | `dialog.sheet form` và `.field-row` gap `--sp-4` | Cụm → cụm 16px cả hai | Đạt |
| S4 | `.field > .field-hint` margin 0, hưởng gap của `.field` | Ô → gợi ý 8px | Đạt |
| S5 | `.inline-form.one-line`, `.button-row` không chiếm hàng riêng; media đổi sang cột; margin-bottom 0 | Cùng mép trên/dưới; điện thoại 100%, cách 12px | Đạt |
| S6 | `.inline-form.one-line .field-name` | 360px / 100% vùng trong thẻ (324px ở 390) | Đạt |
| S7 | `.inline-form.one-line .field-list` | Co giãn 360–640px / 100% | Đạt với thêm sinh viên; nhánh email giảng viên Admin NOT_EVALUATED |
| S8 | `.field-name`, `.field-list` và placeholder demo tương ứng | Gợi ý trọn ở desktop | Đạt ở 1440; 390 được phép cắt |
| S9 | `.task-bank .toolbar-controls` và các con trực tiếp | Hàng 40px, dropdown 160px, tìm ≤420px, nút sát phải; điện thoại 100%, gap 8px | Đạt |
| S10 | `#task-form .field-row` chứa một `.field`; grid 2 cột, gap 16px | (Rộng form −16)/2 / 100% | Đạt |
| S11 | Cả `#task-form`, `#path-form` cùng `.field`/`.field-row`, không `.stack` | Cùng nhịp S2/S3 | Đạt cùng S2/S3 |
| S12 | `dialog.sheet .button-row`: gap form 16 + margin-top 8; gap nút `--sp-3` | Sau cụm cuối 24px; Lưu → Huỷ cách 12px; điện thoại 2 nút 100% | Đạt |
| S13 | `body.staff .card` padding `--sp-5`; media dùng `--sp-4` | 24 / 16px cả bốn cạnh | Đạt; khoảng dư ngoài padding kiểm thêm V4 |
| S14 | `.row-actions button.danger.small`, `aria-label` có tên từng sinh viên | Viền đỏ, cao 32px cả hai | Hình thức đạt; `confirm()` NOT_EVALUATED |
| S15 | `.list-toolbar` + `.table-scroll > .classes-table`; `min-width:640px`; lưu trữ dùng `.badge` không có lớp trạng thái | 4 cột Lớp · Sinh viên · Giảng viên · Trạng thái, 3 lớp và badge | Đạt cấu trúc; bảng cuộn trong khung ở 390, trang không tràn |
| S16 | `.table-scroll` overflow-x, `main` min-width 0, `:focus-visible` dùng `--brand` | Không tràn trang, console sạch, Tab thấy focus | Đạt |

Lưu ý token: `--sp-5` của CSS gốc giảm còn 16px ở màn nhỏ. Chiều cao điện thoại
dùng `--sp-6 + --sp-3` (=44); khoảng cuối hộp thoại dùng 16+8 (=24), giữ đúng brief.

## Kiểm tra hồi quy V1–V7

Các phép đo được thêm trước khi sửa và đã bắt đủ bảy lỗi trên bản cũ.
Kết quả trước sửa: [regression-before.json](evidence/regression-before.json);
sau sửa: [measurements.json](evidence/measurements.json). Số phép kiểm bên dưới
đếm các phần tử áp dụng trong tổng cộng 24 lượt, không đòi mã xuất hiện trên trang không có phần tử đó.

| Mã | Thay đổi / phép đo trong verify_mockups.py | Kết quả sau sửa |
|---|---|---|
| V1 | Tiêu đề dialog giữ font-family/font-size gốc của hộp thoại khi chỉ nạp style.css + staff.css; màu `--heading` và weight theo `.card h2`. Không ép Poppins hoặc đổi token toàn staff. Trang Đề chưa có h2 thẻ thì tạo h2 tham chiếu ẩn tạm trong thẻ rồi xoá. | 8/8 đạt, sáng/tối cùng màu và weight với thẻ |
| V2 | Tách padding nút khỏi padding ô nhập: nút form/thanh công cụ/dialog và trigger dropdown dùng `--sp-4`; đo padding trái/phải 16px, trừ `.icon-only`. Ô nhập vẫn 12px. | 76/76 đạt |
| V3 | `.row-actions button` cao 32px; `.icon-only` rộng 32px, padding 0. Đo mọi nút trong hàng, không chỉ `.small`. | 60/60 đạt; bút chì 32 × 32px |
| V4 | Bỏ margin-bottom của `.inline-form.one-line`; đặt khoảng form → bảng bằng margin-top 16px ở `.table-scroll` kế tiếp; bỏ margin-bottom của bảng cuối trong thẻ, kể cả bảng lồng. Đo mép trong đáy thẻ trừ đáy con trực tiếp cuối còn nhìn thấy, bằng padding-bottom. | 40/40 đạt: 24px desktop, 16px điện thoại; không tính 1px border |
| V5 | Badge Lưu trữ chỉ dùng `.badge`; kiểm `.classes-table` không có `.badge.FAILED`; màu trung tính được kiểm thêm ở W2. | 4/4 đạt |
| V6 | Bỏ override bo góc dialog, kế thừa 14px từ style.css. Kiểm cả bốn góc bằng 14px. | 8/8 đạt |
| V7 | `.field > label` giữ weight 650, không ghi đè cỡ chữ. Đo mọi label nhìn thấy (bỏ `.visually-hidden`) có weight 650 và cỡ bằng `--t-sm`. | 44/44 đạt: 650, 13px |

## Kiểm tra hồi quy W1–W2

| Mã | Thay đổi / phép đo | Kết quả |
|---|---|---|
| W1 | Bỏ override `body.staff --font-display`. Chụp computed font-family của từng `main h1` và `.card h2`, tạm tắt riêng forms-staff.css để đo đối chứng, rồi khôi phục stylesheet bằng `finally`. Hai giá trị phải giống hệt. V1 đồng thời so font-family/font-size của dialog với bản chỉ nạp hai CSS gốc. | 56/56 đạt; font gốc Roboto được giữ nguyên; dialog giữ cỡ 22px |
| W2 | Đổi Lưu trữ thành `<span class="badge">`, không dùng QUEUED hay FAILED. Đo computed color của badge, so với màu `var(--fg-muted)` đã resolve ở cùng theme. | 4/4 đạt, cả hai khung sáng/tối |

Đối chứng W1 chạy **sau** mọi phép đo hình học để việc tắt CSS không tác động số đo
S1–S16/V2–V7. Giữ nguyên đoạn chờ `document.getAnimations()` và 400ms do chủ dự án
thêm trước `MEASURE`, tránh đo hộp thoại giữa hiệu ứng `scale(0.96)`.

## Antigravity chuyển vào code thật

1. **`src/aicefr/api/static/staff.css`**: dán khối [forms-staff.css](forms-staff.css) vào cuối.
   Hai luật `.mockup-backdrop`/`.mockup-dialog` chỉ cần trong mockup; có thể bỏ khi tích hợp
   vì app đã dùng `showModal()` và `::backdrop`. Tất cả selector đều dưới `body.staff`.
2. **`static/classes.js`**: trong `listView()`, đổi form thành `div.field > label + input`,
   thêm `.one-line/.field-name/.button-row`, `novalidate`, và thay danh sách bằng bảng S15.
   Trong `detailView()`, dùng `.one-line/.field-list` cho `members-form`, `teachers-form`,
   giữ `name="list"`/`name="email"`; dùng `row-actions`, `.danger.small`, aria-label có tên.
   Thêm `window.confirm()` nêu người bị tác động trước `apiJson(..., {method:"DELETE"})`
   trong listener `[data-remove]` và `[data-unteach]`. Giữ nhánh `isAdmin`,
   `new-class`/`name="name"`/`name="teachers"`; email Admin dùng lại `.field-list`.
   Thêm kiểm tra dữ liệu/toast/focus khi dùng `novalidate`, giữ payload hiện hành.
   `bandGroups()`/`wireGroups()` giữ quyền và hợp đồng; không đổi chức năng giao nhóm.
3. **`templates/classes.html`**: giữ `classes-root`, `page-title`, `page-lede` và script hiện có;
   các lớp/thẻ chủ yếu được tạo bởi JS. Dùng icon từ sprite như các mockup.
4. **`templates/teach_tasks.html`**: thay `.bank-toolbar` bằng `.list-toolbar/.toolbar-controls`,
   bỏ `.stack` của `task-form`, nhóm các ô thành `.field`, Band vào `.field-row`,
   đưa `.field-hint` vào cụm từ khóa. Giữ nguyên toàn bộ id/name.
   **`static/teach_tasks.js::paint()`**: bọc thao tác theo hàng bằng `.row-actions`,
   Tắt/Bật giữ `.secondary.small`; giữ `open()`, listener, lọc, API và cách đọc form.
   Dropdown thực tế tiếp tục do `common.js::enhanceSelect()` dựng, không chép dropdown tĩnh.
5. **`templates/teach_paths.html`**: chuyển `path-form` sang cấu trúc mockup, áp cùng khuôn cho
   `unit-form`, `lesson-form`, `compose-form`, `compose-save`; thêm `novalidate`, giữ id/name,
   phần nhãn không bắt buộc dùng `span.muted`. Không thêm `.stack`.
   `teach_paths.js` chỉ cần sửa nếu markup làm thay đổi cách JS tìm ô; kiểm tra validation sẵn có.
6. **`templates/admin.html`**: không cần đổi form tạo tài khoản; CSS S1 tự áp.
   Chụp lại Admin sáng/tối, desktop/điện thoại. Chỉ xoá luật `.bank-toolbar` trong `style.css`
   nếu tìm toàn repo xác nhận không còn nơi dùng; không chuyển CSS mockup vào `style.css`.

## Nhật ký kiểm tra thực tế

- Ngày 16/11/2026, nhánh `FE-Teacher`, HEAD `04375678`.
- `verify_mockups.py --static-only`: **172/172 kiểm tra cấu trúc đạt**, exit 0;
  [chi tiết](static-checks.json). Kiểm tra doctype/lang/body, thứ tự CSS, id duy nhất,
  nhãn, select ẩn, icon/tài nguyên tồn tại, email demo, token có sẵn và scope CSS.
- Bước trình duyệt ở lượt đầu từng bị `WinError 5` trong sandbox. Lượt sửa V1–V7 này
  chạy Chrome **157.0.8103.51**, `channel="chrome"`, ngoài giới hạn cũ.
- Trước sửa: phép đo mới phát hiện đủ **V1–V7**, exit 1; giữ
  [log](evidence/regression-before.log) và [số đo](evidence/regression-before.json).
- Sau sửa: `verify_mockups.py` **24/24 lượt OK**, exit 0, cả S1–S16 đang áp dụng
  và V1–V7/W1–W2; **240/240 phép kiểm V, 60/60 phép kiểm W đạt**. [Log](evidence/verification.log),
  [số đo](evidence/measurements.json) và 12 ảnh `evidence/*-{1440,390}-light.png` (ảnh tối đã bỏ để repo gọn; số đo tối vẫn trong `measurements.json`)
  đã cập nhật. Đã xem trực tiếp ảnh Thêm đề desktop sáng, Lớp desktop/điện thoại sáng
  và Admin desktop tối để rà bố cục.
- Lượt W1–W2: đã thêm phép đo trước khi sửa, xác nhận bắt được cả W1/W2
  (V1 đã chỉnh theo yêu cầu cũng bắt sai font gốc); giữ
  [log trước sửa](evidence/w-regression-before.log) và [số đo trước sửa](evidence/w-regression-before.json).
  Sau sửa đã xem lại ảnh Lớp desktop sáng và Thêm đề desktop tối; đoạn chờ hiệu ứng
  hộp thoại giữ nguyên. 24 ảnh và bản ghi cuối ở trên phản ánh bản sau sửa W1–W2.
- Kiểm thử API/backend, `ruff` toàn repo và E2E nghiệp vụ: **NOT_RUN**, ngoài phạm vi mockup tĩnh.
  Hành vi xác nhận xoá và thao tác Admin: **NOT_EVALUATED**, cần kiểm khi tích hợp.
- Không sửa tệp ngoài `mockup/`, không commit, không push, không cài gói.
