# Phục hồi AI Prompt Log W05 của Nguyên sau pull — 15/10/2026

Chủ dự án chọn **khôi phục toàn bộ dòng Nguyên từ bản trước pull**. Workbook sau pull có 3 dòng Nguyên ở hàng 6–8; ba dòng này trùng chính xác với hàng 13–15 của bản trước pull. Bản trước pull có 34 dòng ở hàng 6–39. Đã ghép 34 dòng đó vào workbook sau pull và thêm 7 lượt M15 phát sinh sau bản sao lưu ở hàng 40–46. Không thay giá trị/công thức hai sheet `Thắng`, `Sang` hoặc công thức `Tổng hợp`.

| Đối tượng | SHA-256 / kết quả |
| --- | --- |
| Workbook sau pull trước khi ghép | `5e24dbbb79fc092681fab44b95c3f943d0dd57d124f83a3af75e2a725f67818e` |
| Bản sao lưu trước pull (local, không commit riêng) | `edb5cfb4d6b820e7338e8cb365b4d98e4643bca2d9b5427425712539e7672e9c` |
| Workbook W05 ngay sau phục hồi (snapshot checksum, trước khi ghi tiếp Phase 03–05) | `f2d57959308e5668dbaf919cc9b4d0e101950d17b0691ea415dcc0fb4d6b478b` |
| Kiểm tra sau xuất và đọc lại | 41 dòng Nguyên khớp giá trị đã ghép; Thắng 28, Sang 0; Tổng hợp 69; các công thức Tổng hợp và dữ liệu/công thức hai sheet còn lại giữ nguyên; render hàng 38–46 đã xem |

Việc phục hồi dòng **không phục hồi tệp minh chứng gốc**. Những tệp dưới đây được nêu ở cột F của các dòng lịch sử nhưng không tồn tại tại revision kiểm tra `abd20255b4d4e21a22317ea96b6c909e80b73baa`. Trạng thái của từng dẫn chiếu là `HISTORICAL_EVIDENCE_MISSING`, không suy từ prompt rằng công việc hoặc kết quả đã được nghiệm thu:

- `docs/reports/week-04/Nhom03_DT_Baocaotuan04.docx`
- `docs/evidence/tc2-3-ai-usage/nguyen/prompt-log-bao-cao-w4-20261012.md`
- `docs/evidence/tc2-3-ai-usage/nguyen/dinh-huong-de-tai-20261012.md`
- `docs/evidence/tc2-3-ai-usage/nguyen/dinh-huong-zoom-revision-20261012.md`
- `docs/evidence/tc2-3-ai-usage/nguyen/ke-hoach-15-tuan-20261012.md`
- `docs/evidence/tc2-3-ai-usage/nguyen/ke-hoach-15-tuan-excel-20261012.md`
- `docs/evidence/tc2-3-ai-usage/nguyen/khoi-phuc-stash-20261012.md`
- `docs/evidence/tc2-3-ai-usage/nguyen/khoi-phuc-stash-lan2-20261012.md`
- `docs/evidence/tc2-3-ai-usage/nguyen/tao-thu-muc-eduz-20261013.md`
- `docs/evidence/tc2-3-ai-usage/nguyen/tach-ho-so-eduz-20261013.md`
- `docs/evidence/tc2-3-ai-usage/nguyen/chuyen-dinh-huong-sang-word-20261013.md`
- `docs/evidence/tc2-3-ai-usage/nguyen/dinh-huong-tuong-lai-20261013.md`
- `docs/evidence/tc2-3-ai-usage/nguyen/dac-ta-hien-tai-20261013.md`
- `docs/evidence/tc2-3-ai-usage/nguyen/mongodb-20261013.md`

Các dẫn chiếu đường dẫn đầu tiên ở cột F còn lại đã được kiểm tồn tại trong repo sau khi tạo [record M15](m15-w5-20261015.md). Bản sao lưu trước pull được giữ ngoài repo để đối chiếu nếu cần truy lại giá trị ô; không dùng nó làm minh chứng nội dung các tệp đã mất.

Sau snapshot phục hồi, ba lượt AI mới được ghi ở hàng 47–49. [Workbook W05 hiện tại](../AI%20Prompt%20Log%20-%20W05%20-%202026-10-12_2026-10-18.xlsx) có SHA-256 `ed5c90cbf2e0185896a01b0980516d351c368bab4e3ea0a062aaf6fdf869d2fa`, Nguyên 44 dòng và Tổng hợp 72; các sheet/công thức khác vẫn được đối chiếu khi xuất/đọc lại.
