# Báo cáo tiến độ tuần 7 — Võ Thanh Sang

**Tuần:** W7, 26/10–01/11/2026 (số liệu chốt ngày 29/10/2026). **Phụ trách:** M03, M04, M05, M09, M10, M12, M13 theo bảng phân vùng của kế hoạch W7.
**Kế hoạch đối chiếu:** [kế hoạch W7](../../plan/week-07.md), phần "3.1. Sang" (W7-S01 đến W7-S05).
**Trạng thái nộp:** bản để nộp lên projects-fit; chưa có xác nhận GVHD.

## 1. Việc đã làm

### 1.1. Việc trong kế hoạch W7

| ID | Việc | Kết quả | Minh chứng |
| --- | --- | --- | --- |
| W7-S01 | Gỡ artifact S&I, nạp model từ ngoài, ghim SHA | Repo nộp bài không chứa artifact nào của Speak & Improve: model nạp từ thư mục ngoài Git (`AICEFR_MODEL_DIR`) và chỉ dùng khi SHA-256 khớp giá trị ghim trong `scoring/artifacts.py`; test dùng artifact tổng hợp. Số đo S&I còn sót trong tài liệu và chữ giao diện đã gỡ | PR #59, [#73](https://github.com/thanglb2005/ai-assessor-cefr/pull/73) |
| W7-S02 | Chuyển M03, M04, M05, M09 | Lõi chấm và Trust Layer đã vào nhánh tích hợp, merge 27/10 | PR #59 |
| W7-S03 | Chuyển M10, M12, M13 | Học tập, chấm mù, bằng chứng nghiên cứu đã vào nhánh tích hợp, merge 27/10 | PR #60 |
| W7-S04 | Sửa và ký Bản cam kết (SCRUM-61) | **Chưa ký.** Bản thảo W6 phải sửa thêm theo D058–D060 (mục 1.2) trước khi ký | — |
| W7-S05 | Chạy thật trên nhánh tích hợp | Chạy đủ ở local và trên CI của `main` (mục 1.3) | [#78](https://github.com/thanglb2005/ai-assessor-cefr/pull/78) |

### 1.2. Làm lại sau W7, đã vào `main`

Kế hoạch W7 cũ nhóm đã làm xong và vẫn nằm nguyên trong lịch sử `main`. Phần dưới đây xếp chồng lên trên, vào `main` bằng một commit squash ([#78](https://github.com/thanglb2005/ai-assessor-cefr/pull/78), `130ffea`). Từ nay repo nhóm là repo nộp bài; repo gốc `ThanhSangLouis/ai-assessor-cefr` không dùng nữa.

| Việc | Kết quả | Minh chứng |
| --- | --- | --- |
| `main` xanh trở lại | Code khớp bản nguồn đã chuyển; trước đó CI của `main` đỏ ba lần liên tiếp | #71 (trong #78) |
| Bỏ thuộc tính không ai đọc | `Transcript.has_word_timestamps` và các chỗ dùng | #74 (trong #78) |
| **D058** bỏ đồng thuận nghiên cứu | Giai đoạn thu giọng đã xong; thay bằng một lần đồng ý điều khoản sử dụng, migration 6 chuyển dữ liệu cũ | #75 (trong #78) |
| **D059** band đủ A1–C2 | Ánh xạ điểm sang band ở `scoring/band_map.py`; ngân hàng luyện tập 30 nhiệm vụ; lộ trình mẫu A1 → C2 có 24 chặng, 46 bài | #76 (trong #78) |
| Sơ đồ lớp chỉ gồm thực thể và enum | 23 thực thể, 12 enum, 6 khung theo phần nghiệp vụ. Mỗi quan hệ có thuộc tính ở lớp giữ nó; bội số chỉ ghi trên đường. Bản trên Drive (trang "So do lop") đã cập nhật | #69, #70, [#77](https://github.com/thanglb2005/ai-assessor-cefr/pull/77); [thiết kế](../../sdd/thiet-ke-gon-so-do-lop-va-collection.md) |
| **D060** collection theo sơ đồ lớp | 42 collection còn 17 nghiệp vụ + 2 kỹ thuật (`session`, `system`). Lớp miền trong code khớp sơ đồ; migration 7 chuyển dữ liệu cũ; `tests/test_diagrams.py` đối chiếu sơ đồ với code | [#77](https://github.com/thanglb2005/ai-assessor-cefr/pull/77); [từ điển dữ liệu](../../db/TU_DIEN_DU_LIEU.md) |
| Tài liệu | SDD bản 1.7 (hình 5, 5c, 5d vẽ lại theo MongoDB), từ điển dữ liệu, ERD, snapshot schema; D058–D060 ghi PROPOSED trong nhật ký quyết định | #77, #78 |
| Tài liệu vận hành | Chạy trên localhost, setup cho teammate, triển khai, cấu hình khoá ngoài đã chuyển sang repo nhóm | [#73](https://github.com/thanglb2005/ai-assessor-cefr/pull/73) |
| AI Prompt Log tuần 7 | 10 dòng trong sheet Sang, mỗi dòng có PR hoặc tệp làm minh chứng | [AI Prompt Log W07](../../evidence/tc2-3-ai-usage/README.md#ai-prompt-log-theo-tuan) |

### 1.3. Kiểm thử

Trên nhánh đã gộp, trước khi vào `main`:
- Toàn bộ test đơn vị (mongomock): 1488 qua, 0 lỗi, 27 bỏ qua.
- 15 tệp test lưu trữ trên MongoDB 7 thật: 265 qua. Tám bước migration D060 chạy hai lần trên MongoDB 7: đều đạt.
- E2E Playwright với MongoDB 7: 79/79 qua.
- CI của PR vào `main`: đủ 5 check xanh (định dạng/lint/kiểm thử, kiểm thử trên MongoDB và Redis, dựng ảnh Docker, tài liệu và tệp cấm, quét lộ khoá).

## 2. Vướng mắc

1. **Bản cam kết sản phẩm và bộ metric chưa ký** (W7-S04). Hạn chặn G1 là trước tuần 11 (23/11/2026). Bản thảo phải ghi theo hệ thống hiện tại: band A1–C2, không còn đồng thuận nghiên cứu, thanh toán chỉ chạy chế độ thử.
2. **Ba ngưỡng band ngoài chưa hiệu chuẩn** (A1/A2, B2/C1, C1/C2; D059). Mỗi band giờ chỉ rộng 1 điểm trong khi khoảng tin cậy 90% rộng gần 2 điểm, nên gần như mọi bài chạm hai band trở lên và chuyển giảng viên duyệt. Cần nhóm và GVHD chấp nhận giới hạn này hoặc có dữ liệu để hiệu chuẩn.
3. **D058, D059, D060 đang PROPOSED.** Cần cả nhóm xác nhận. D060 có migration biến đổi và xoá collection cũ; dữ liệu trên máy của từng người sẽ được chuyển khi khởi động lần đầu.
4. **Tài liệu SDD module** (M03–M05, M09, M10, M12, M13) và vài mục lịch sử trong SDD còn nhắc tên bảng cũ. Ghi chú bản 1.7 của SDD đã trỏ sang nguồn chuẩn mới, nhưng các tệp module chưa cập nhật.
5. **AI Prompt Log tuần 6 của Sang còn trống** (0 dòng), dù tuần 6 có việc (kế hoạch W7, chuẩn bị chuyển module). Cần bổ sung, chỉ những dòng có PR làm minh chứng.

## 3. Kế hoạch tuần 8

1. Sửa Bản cam kết theo D058–D060, gửi GVHD và ký trước tuần 11.
2. Thống nhất với nhóm D058–D060 (PROPOSED → quyết định của nhóm).
3. Cập nhật SDD module M03–M05, M09, M10, M12, M13 theo collection và lớp miền của D060.
4. Phương án cho ba ngưỡng band chưa hiệu chuẩn: hiệu chuẩn nếu có dữ liệu, nếu không thì ghi rõ giới hạn trong Bản cam kết và trang `/bands`.
5. Bổ sung AI Prompt Log tuần 6 của Sang.
