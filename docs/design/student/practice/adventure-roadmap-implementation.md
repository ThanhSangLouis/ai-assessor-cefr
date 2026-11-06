# Roadmap phong cảnh 2.5D

Triển khai trên `/practice`, theo mockup đã được chủ dự án chọn. Không đổi điều kiện mở bài, cách chấm điểm hay dữ liệu lộ trình.

## Cảnh và khả năng mở rộng

| Cấp độ | Cảnh | Bảng màu |
| --- | --- | --- |
| A1 | Rừng xanh | Xanh lá |
| A2 | Miền núi lửa | Đỏ cam |
| B1 | Xứ tuyết | Trắng xanh |
| B2 | Dòng sông ngọc | Xanh ngọc |
| C1 | Sa mạc vàng | Vàng cát |
| C2 | Đồng hoa | Hồng tím |

- Tọa độ đường tính từ số bài thực tế, không kéo giãn ảnh nền. Đường kết thúc tại node cuối.
- Mỗi 12 bài tạo mốc chặng tiếp theo. Nền lặp theo chiều dọc, giữ tỉ lệ ảnh khi chiều dài phần học tăng; không thêm giới hạn số bài vào dữ liệu giáo viên.
- Sáu phông cảnh vẽ liền khối thay cho các hình trang trí rời. Địa hình và cây nằm hai bên, trung tâm dành cho đường học.
- Mascot giữ giữa chiều dài từng phần. Card bài học nổi phía trên đường nên mở card không đổi chiều dài đường.
- Phông cảnh là CSS background, không có nội dung ngữ nghĩa hay tương tác. Ảnh WebP được xuất ở nhiều cỡ từ PNG gốc, không upscale; mobile dùng hình học node riêng.
- Chưa dùng virtualization: vẫn render toàn bộ node của lộ trình. Đã kiểm tra đến 100 bài/cấp độ; đây là phạm vi kiểm tra, không phải cam kết hiệu năng cho số bài không giới hạn.

## Asset và bảo trì

Bản hiện tại dùng 24 tranh ngày/đêm v3 cho sáu vùng, xuất thành 120 file WebP. Sáu companion dùng bộ mascot v3 theo vùng; mascot cô bé ở header giữ nguyên. Các ảnh v2 và SVG/PNG trang trí cũ được giữ để truy vết, không render trên roadmap hiện tại.

- [Xem sáu vùng ngày/đêm hiện tại](adventure-worlds-day-night.html)
- [Prompt và export bộ v3](adventure-worlds-v3-prompts.json)
- [Thư viện cảnh cũ](adventure-assets.html)
- [Prompt sáu vùng và dải dài](adventure-worlds-v2-prompts.json)
- [Prompt phông cảnh 2.5D trước đó](adventure-landscapes-prompts.json)
- [Prompt asset cũ](adventure-assets-prompts.json)
- Danh sách export v3, dung lượng và SHA-256: hai manifest prompt v3. `static/art/adventure/manifest.json` là thư viện phiên bản cũ.
- Theme, nhịp đường, chặng và vị trí cảnh: `src/aicefr/api/static/practice_adventure.js`.
- Màu, kích thước responsive: `src/aicefr/api/static/practice_adventure.css`.
- Tạo lại SVG: `python3 tools/build_adventure_vectors.py`. PNG giữ nguyên đầu ra công cụ tạo ảnh.

## Kiểm tra có thể chạy lại

```sh
node --test tests/js/practice_adventure.test.cjs
.venv/bin/python -m pytest tests/test_practice_ui.py -q
.venv/bin/python tools/check_adventure_browser.py
```

Browser dùng tài khoản demo, thay GET bằng fixture; không ghi tiến độ người học. Ma trận gồm 0, 1, 2, 5, 12, 13, 30, 100 bài mỗi cấp độ tại chiều rộng 1440, 1024, 700, 390, 320px. Kiểm tra số node/chặng, tràn ngang, vị trí node và mascot, mở/đóng card, chiều dài đường và lỗi JavaScript. Screenshot ghi vào `/tmp/adventure-checks/`.

Kiểm tra tự động không thay cho nghiệm thu thẩm mỹ của chủ dự án. Chưa đo hiệu năng trên thiết bị di động thật.

Phông 2.5D thể hiện độ cao bằng phối cảnh nghiêng, vách đá, ánh sáng từ trên trái, bóng tiếp xúc và sắc độ xa/gần. Các cây và địa hình được vẽ chung trong phông để thống nhất chất liệu. Không dùng WebGL hoặc hiệu ứng cuộn. Các generator SVG trước đây được giữ làm nguồn của phiên bản cũ.

## Cắt cảnh theo chiều dài phần học

Mỗi phông v2 là một dải dọc tỉ lệ 1:3, dài gấp đôi tỉ lệ 2:3 của phông v1. CSS dùng `background-size: 100% auto`: chiều cao ảnh do tỉ lệ gốc quyết định, không phụ thuộc chiều cao section. Với ít bài, section cắt một phần phía trên ảnh; thêm bài sẽ lộ dần phần cảnh phía dưới. Khi số bài vượt chiều dài một phông, ảnh lặp dọc có mép chuyển nhẹ để vẫn hỗ trợ lộ trình dài. Đây là dải cảnh có thể lặp, không phải cảnh độc nhất vô hạn.

`--scene-ratio` phải khớp tỉ lệ chiều cao/chiều rộng của ảnh để mặt nạ nối cảnh đúng vị trí. Bộ kiểm tra browser giải mã cả sáu ảnh và đối chiếu tỉ lệ này, sau đó kiểm tra 0–100 bài mỗi cấp độ. Badge và thanh tiến độ cấp độ sử dụng màu tương ứng từng vùng; màu trạng thái bài học và điều kiện mở bài giữ nguyên.

## Mascot theo vùng v3 — 06/11/2026

Thay toàn bộ sáu companion trên đường học bằng bộ 2.5D cùng chất liệu, nền trong suốt: A1 cú lá, A2 rồng con, B1 cáo tuyết, B2 rái cá, C1 cáo cát, C2 thỏ hoa. Màu lần lượt xanh lá, đỏ cam, trắng xanh, xanh ngọc, vàng cát, hồng tím. Ảnh WebP có kích thước khai báo để tránh dịch bố cục khi tải; lazy loading. Vị trí giữa section, lời nhắn và tương tác giữ theo cơ chế hiện hành. Cô bé trang trí header nằm ngoài bộ companion theo vùng. Prompt và gallery nằm tại `adventure-mascots-v3-prompts.json`, `adventure-mascots.html`.

Kiểm chứng bộ mascot v3: Node 19/19, pytest UI 16/16; browser 0–100 bài mỗi phần; audit 135 trường hợp sáng/tối/system, 320–2560px không còn finding hoặc lỗi JavaScript. Audit chờ 250ms khi đổi breakpoint để qua resize debounce 150ms. Evidence: `adventure-mascots-verification.json`. Chưa kiểm trên thiết bị thật hoặc Safari/Firefox.

## Sửa responsive theo ảnh thực tế — 06/11/2026

Flex column trên mobile kế thừa `align-items: start` từ grid desktop làm roadmap co ngang; đổi thành stretch và khai báo width 100%. Chuyển nav mobile sang block `app_navigation` trực tiếp dưới main trong base để neo theo viewport, không nằm trong khối nội dung. Xóa markup footer ứng dụng trong base và CSS liên quan; footer khách trên landing vẫn dùng riêng. Header mobile dùng title 19px, subtitle 13px, mascot top 20px để cân phần dưới.

Kiểm chứng: pytest practice UI 16/16, test_web 71/71; browser fixture 0–100 bài tại 1440/1024/700/390/320px qua kiểm tra chiều rộng đầy đủ và nav đúng đáy. Screenshot đầu/cuối ở `/tmp/fixed-mobile-{top,bottom}.png`.

## Mở khóa bài theo từng phần — 06/11/2026

Mỗi band A1–C2 là một phần, kể cả khi giáo viên chia thành nhiều unit. Bài đầu mỗi phần mở độc lập; sau đó chỉ bài đầu chưa hoàn thành của phần được học. Các bài phía sau mang status `locked`, bài `completed` vẫn được học lại. Bắt đầu hoặc thử bài chưa đủ để mở bài sau: giữ nguyên điều kiện hoàn thành đã có (`is_complete`), không đổi ngưỡng chấm điểm.

API `/api/v1/learn` và plan/bands trả status đã áp dụng chung `gate_units`. Khuyến nghị không chọn bài khóa. `GET /api/v1/learn/lessons/{id}` và `POST /api/v1/learn/lessons/{id}/steps/{step}/attempts` kiểm tra điều kiện từ dữ liệu backend, trả 403 trước khi đọc/chấm/lưu audio nếu chưa mở. Với bài nằm trong plan đang hoạt động, dùng thứ tự của plan; các bài ngoài plan dùng thứ tự published path. Teacher preview giữ luồng riêng. FE hiển thị bài mở tiếp theo bằng nút cam và nhãn Bắt đầu/Học tiếp ở từng phần, bài khóa hiện ổ khóa và giải thích, không xuất link học. Trang bài học vào thẳng URL có thông báo chưa mở khóa khi API trả 403.

Kiểm chứng: test_lessons_unit, test_learning_plans, test_lessons_integration và test_practice_ui chạy qua. Test mới bao phủ 6 bài đầu mở độc lập, gọi API trực tiếp bị chặn, không ghi attempt bị từ chối, hoàn thành mở bài kế tiếp, bài cũ được học lại, cùng band qua nhiều unit, active plan và không sửa dữ liệu plan gốc. Kiểm tra Chromium trên dữ liệu demo 46 bài: 6 mở/40 khóa; popup bài khóa không có link, popup bài mở có link tại 390 và 1440px. Screenshot `/tmp/roadmap-lesson-gates.png`. Không ghi tiến độ demo trong kiểm tra browser.

### Mascot đứng trong khoảng trống cạnh bài học (06/11/2026)

- Tính vị trí theo kích thước section và vị trí nút học thực tế, ưu tiên khoảng trống gần đường quanh giữa section thay vì bám mép ngoài.
- Chừa khoảng cho lời nhắn, ưu tiên tránh che nút học khi section rất ngắn; ResizeObserver tính lại khi đổi chiều rộng.
- Kiểm tra trình duyệt bằng `tools/check_adventure_browser.py` và `tools/audit_adventure_display.py`; ảnh kiểm tra tại `/tmp/adventure-display-audit/` (artifact cục bộ).

### Rừng ngày/đêm v3 — bản thử nghiệm (06/11/2026)

- A1 dùng hai đoạn địa hình A/B khác nhau, mỗi đoạn có bản ngày và bản đêm riêng. Bản đêm giữ vị trí địa hình, đổi sang ánh trăng xanh và đom đóm; không áp dụng bộ lọc giảm sáng 52% lên ảnh đêm. Năm vùng còn lại vẫn dùng ảnh v2 và cách xử lý theme cũ trong giai đoạn thử nghiệm này.
- Ảnh nguồn tạo bằng built-in imagegen có kích thước thực tế 1536×1024 (yêu cầu 1920×1280 nhưng công cụ trả về kích thước nhỏ hơn). Xuất WebP 480/768/960/1280/1536px bằng downsampling; không upscale giả làm nguồn nét cao. Prompt và SHA-256 từng export: `adventure-forest-v3-prompts.json`.
- Renderer dùng các đoạn cảnh đúng tỉ lệ nguồn, kích thước chỉ phụ thuộc chiều rộng. Section ngắn cắt cảnh qua overflow; section dài bổ sung đoạn A/B luân phiên. Đầu section hoàn toàn không có fade; chỉ mask đầu các đoạn tiếp nối trong phần chồng 4.5% chiều rộng. Năm vùng v2 cũng dùng renderer nối đoạn mới để bỏ fade ở đầu.
- CSS image-set chọn tài nguyên theo viewport và DPR, hỗ trợ explicit light/dark và system dark. Chỉ tải bộ ảnh của theme đang dùng. Đổi theme không dựng lại đường hoặc đổi vị trí bài.
- Bản xem độc lập: `adventure-forest-day-night.html`, có nút đổi 1/3/5/15/50 bài. Tích hợp thực tế tại `/practice`.
- Kiểm tra: `tools/check_forest_day_night.py` đạt 60 trường hợp (3 viewport 390/1440/1920 × 5 số bài × DPR 1/2 × light/dark), kiểm tra cả system dark và explicit light override. Không hở đoạn, không fade đầu, không lỗi JS; kích thước đoạn không đổi theo số bài. `tools/check_adventure_browser.py` đạt 0/1/2/5/12/13/30/100 bài trên 5 viewport, kiểm tra card và va chạm mascot. 16 kiểm tra template/UI và 25 kiểm tra JS đạt.
- Giới hạn: nguồn 1536px phủ đủ 2× khi bản đồ rộng tối đa 768 CSS px. Tại viewport 1920, bản đồ rộng 1241 CSS px, nguồn đạt 0.619 pixel nguồn/device pixel ở DPR 2. Độ nét được cải thiện so với v2 nhưng chưa thể khẳng định native 2× cho desktop rộng; cần nguồn rộng hơn hoặc bổ sung các mảnh ảnh chi tiết trước khi mở rộng cả bộ. Các đoạn A/B có lặp lại trên section dài, không phải vô hạn cảnh độc nhất. Đánh giá thẩm mỹ chỗ nối và mức sáng đêm vẫn cần người dùng xem bản thử.

### Cúp ở cuối lộ trình

Thay dòng chữ “Đích đến · band” bằng ảnh cúp vàng 2.5D nền trong suốt, đặt giữa phía dưới section cuối, có bóng và quầng sáng nhẹ. Giữ tên đích đến/hoàn thành dưới dạng accessible label; không còn dòng chữ dài trên giao diện. Nhãn hoàn thành chỉ áp dụng khi toàn bộ bài của lộ trình đã hoàn thành. Prompt: `adventure-trophy-v1-prompt.json`.

### Hoàn thiện sáu vùng ngày/đêm v3 — 06/11/2026

Bản rừng thử nghiệm đã được chủ dự án duyệt. Cả sáu vùng trên `/practice` hiện dùng bộ v3: rừng xanh, núi lửa đỏ cam, tuyết trắng xanh, sông xanh ngọc, sa mạc vàng cát và đồng hoa hồng tím. Mỗi vùng có hai đoạn A/B và hai thời điểm ngày/đêm, tổng cộng 24 tranh địa hình. Các bản đêm được tạo từ đúng tranh ngày tương ứng để giữ bố cục; ánh trăng, dung nham, phản chiếu nước và đom đóm theo từng vùng. Đã bỏ hoàn toàn cơ chế giảm sáng ảnh ngày trong roadmap.

Giữ cơ chế cắt và nối theo chiều rộng đã kiểm chứng ở rừng; tỉ lệ chiều cao/chiều rộng mỗi đoạn là 2/3. Số bài chỉ thay đổi chiều cao section và số đoạn A/B luân phiên, không kéo giãn hoặc phóng cảnh theo số bài. Đầu section không fade; mask chỉ nằm tại chỗ chồng giữa các đoạn. Hai đoạn được lặp khi lộ trình rất dài, không phải địa hình độc nhất vô hạn.

Có 120 ảnh WebP ở năm cỡ 480/768/960/1280/1536px. CSS chọn theo viewport và DPR; desktop từ 2000px dùng bản native 1536px ở cả DPR 1/2. Tổng dung lượng toàn bộ 24 ảnh ở cỡ 480px là khoảng 1.24 MiB; chỉ bộ ngày khoảng 0.63 MiB. Các số này là dung lượng file, không phải số đo tải trang trên thiết bị thật. Không upscale: nguồn thực tế vẫn là 1536×1024, có giới hạn native density trên desktop rất rộng/DPR 2.

Đã sửa R01 của lượt review: reset `width:auto; min-width:0` riêng các nút `.bp-dialog-actions`, tránh quy tắc button 100% trên mobile đẩy nút xác nhận ra ngoài. Audit đo cả scrollWidth và từng nút, gồm font lớn, không chỉ kiểm khung popup. Không thay đổi điều kiện mở bài hoặc ghi tiến độ học.

- Bộ prompt và provenance: `adventure-worlds-v3-prompts.json`, liên kết nguồn rừng trong `adventure-forest-v3-prompts.json`.
- Gallery độc lập: `adventure-worlds-day-night.html`, chọn đủ sáu vùng và 1/3/5/15/50 bài.
- Công cụ xuất WebP: `tools/export_adventure_worlds.py`; chỉ resize xuống, xác minh kích thước và lưu SHA-256.
- Kiểm tra cảnh: `tools/check_adventure_worlds.py`; kiểm tra bố cục và popup: `tools/audit_adventure_display.py`; kiểm tra thêm/xóa bài và card: `tools/check_adventure_browser.py`.
- Bằng chứng và giới hạn cuối: `adventure-worlds-v3-verification.md`.
