# Báo cáo tiến độ tuần 7 — Võ Thanh Sang

**Tuần:** W7, 26/10–01/11/2026 (số liệu chốt ngày 30/10/2026; bản 29/10 bổ sung mục 1.3). **Phụ trách:** M03, M04, M05, M09, M10, M12, M13 theo bảng phân vùng của kế hoạch W7.
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

### 1.3. Làm thêm ngày 29–30/10

Repo nộp bài đã chuyển sang tài khoản `ThanhSangLouis/ai-assessor-cefr` (đường cũ `thanglb2005/...` tự chuyển hướng) và tự deploy lên EC2 `https://52-64-179-250.sslip.io` sau khi CI xanh trên `main`.

| Việc | Kết quả | Minh chứng |
| --- | --- | --- |
| Khôi phục `main` | Commit `ff683cc` đẩy thẳng lên `main` đưa lại bản cũ (mất D058–D060, đưa lại artifact S&I vào repo công khai). Cây mã về đúng bản #79 | [#80](https://github.com/ThanhSangLouis/ai-assessor-cefr/pull/80) |
| **D061** Mạch lạc đo bằng từ nối | Báo cáo liệt kê các kiểu từ nối trong bài làm bằng chứng cho Mạch lạc; `demo.sh` dùng MongoDB trong Docker, tự dùng artifact giả lập khi thiếu model thật | [#81](https://github.com/ThanhSangLouis/ai-assessor-cefr/pull/81) |
| Hướng dẫn chạy cho AI agent | `docs/plan/CHAY_DU_AN_CHO_AI.md`; `CLAUDE.md` trỏ tới `AGENTS.md`; sửa lệnh sai trong README | [#83](https://github.com/ThanhSangLouis/ai-assessor-cefr/pull/83) |
| **D062** Chỉ còn năm tiêu chí | Bỏ khía cạnh Tương tác khỏi báo cáo và trang `/bands` | [#84](https://github.com/ThanhSangLouis/ai-assessor-cefr/pull/84) |
| Deploy EC2 tự động | GitHub Actions SSH vào EC2 sau CI xanh; CI kiểm thư mục cache Whisper; bản đồ triển khai cho AI agent | [#82](https://github.com/ThanhSangLouis/ai-assessor-cefr/pull/82), [#86](https://github.com/ThanhSangLouis/ai-assessor-cefr/pull/86) |
| **D063** Đăng ký bằng Google, seed tài khoản | Sinh viên đăng ký bằng Google (bút danh ngẫu nhiên, chỉ lưu băm định danh). Deploy tự seed QT-01, GV-01..03, SV-001..010; trên máy chủ đã tắt 10 tài khoản thử thừa | [#85](https://github.com/ThanhSangLouis/ai-assessor-cefr/pull/85) |
| **D064** Bỏ bước đồng ý điều khoản | Thay D058; migration 8; logo Google trên nút đăng nhập; sơ đồ lớp và ERD cập nhật | [#87](https://github.com/ThanhSangLouis/ai-assessor-cefr/pull/87) |
| Kiểm chấm điểm toàn bộ | Whisper và model thật chấm đủ dạng P3, P4, P5; bài quá ngắn bị từ chối đúng; mọi bài vẫn chuyển giảng viên duyệt vì khoảng tin cậy rộng và bản Whisper khác lúc huấn luyện (thiết kế, không phải lỗi) | [#87](https://github.com/ThanhSangLouis/ai-assessor-cefr/pull/87) |
| Lỗi teammate không chạy được | Tái hiện trên bản clone mới: bật Whisper khi chưa cài nhóm `[asr]` làm mọi bài `FAILED` mà log không nói lý do; Mac Intel cài nhầm backend; nút Google không hiện khi thiếu khoá (khoá chỉ có trên EC2). `demo.sh` và trang đăng nhập giờ báo rõ | [#89](https://github.com/ThanhSangLouis/ai-assessor-cefr/pull/89) |
| Rà phân quyền vai trò admin | 184 route API: mọi route `/api/v1/admin/*` chỉ cho admin, mọi route khác có lớp chặn trừ bốn route phải công khai. Trang `/admin` trước đây ai cũng xem được khung trang, nay chuyển hướng. Test ma trận quyền tự phủ route mới | [#90](https://github.com/ThanhSangLouis/ai-assessor-cefr/pull/90) |
| **D065** Đăng ký và quên mật khẩu | `/signup` chỉ cần mật khẩu, bút danh ngẫu nhiên; `/forgot` dùng mã khôi phục dùng một lần (hệ thống không lưu email nên không gửi được thư) | [#91](https://github.com/ThanhSangLouis/ai-assessor-cefr/pull/91) |
| AI Prompt Log tuần 7 | Sheet Sang thêm 11 dòng (hàng 16–26), tổng 21 dòng | [AI Prompt Log W07](../../evidence/tc2-3-ai-usage/README.md#ai-prompt-log-theo-tuan) |

### 1.4. Kiểm thử

Bản 30/10 (sau D064, trước #89–#91):
- Kiểm thử trên MongoDB và Redis thật: 1492/1492 qua. E2E Playwright với ba vai trò: 75/75 qua (bỏ 4 test điều khoản theo D064).
- Bản clone sạch của `main` (`bbaa713`), cài như máy teammate: 1493 test qua, 0 lỗi; đăng nhập ba vai trò, 178 trang không lỗi.
- #89, #90: CI đủ 5 check xanh. #91: toàn bộ test đơn vị 1525 qua, 24 test tích hợp và 2 test E2E mới của D065 qua.

### 1.5. Kiểm thử trước khi vào `main` (bản 29/10)

Trên nhánh đã gộp, trước khi vào `main`:
- Toàn bộ test đơn vị (mongomock): 1488 qua, 0 lỗi, 27 bỏ qua.
- 15 tệp test lưu trữ trên MongoDB 7 thật: 265 qua. Tám bước migration D060 chạy hai lần trên MongoDB 7: đều đạt.
- E2E Playwright với MongoDB 7: 79/79 qua.
- CI của PR vào `main`: đủ 5 check xanh (định dạng/lint/kiểm thử, kiểm thử trên MongoDB và Redis, dựng ảnh Docker, tài liệu và tệp cấm, quét lộ khoá).

## 2. Vướng mắc

1. **Bản cam kết sản phẩm và bộ metric chưa ký** (W7-S04). Hạn chặn G1 là trước tuần 11 (23/11/2026). Bản thảo phải ghi theo hệ thống hiện tại: band A1–C2, năm tiêu chí (D062), không còn bước đồng ý điều khoản (D064), đăng ký bằng Google và mật khẩu (D063, D065), thanh toán chỉ chạy chế độ thử.
2. **Ba ngưỡng band ngoài chưa hiệu chuẩn** (A1/A2, B2/C1, C1/C2; D059). Gần như mọi bài chạm hai band trở lên và chuyển giảng viên duyệt. Cần nhóm và GVHD chấp nhận giới hạn này hoặc có dữ liệu để hiệu chuẩn.
3. **D059–D065 đang PROPOSED** (D058 đã được D064 thay). Cần cả nhóm xác nhận.
4. **Production bật cổng thanh toán thử (sandbox).** `.env` trên EC2 để trống `AICEFR_PAYMENT_GATEWAYS` nên dùng mặc định `sandbox`: ai đặt mua lượt chấm cũng tự "thanh toán" được mà không mất tiền. Cần chủ dự án quyết: giữ (đồ án, không thu tiền thật) hay tắt (sinh viên chỉ còn lượt miễn phí mỗi kỳ).
5. **Rủi ro dữ liệu cá nhân sau D064.** Giọng nói là dữ liệu cá nhân (Nghị định 13/2023); không còn mốc đồng ý trong hệ thống thì cơ sở pháp lý phải nằm ở hợp đồng với trường hoặc thông báo ngoài hệ thống.
6. **#89, #90, #91 chờ merge.** CI xanh nhưng công cụ AI không được tự merge; #91 cần cập nhật sau khi #90 vào `main` (thêm hai route công khai mới vào test ma trận quyền).
7. **Tài liệu SDD module** (M03–M05, M09, M10, M12, M13) còn nhắc tên bảng cũ.
8. **AI Prompt Log tuần 6 của Sang còn trống** (0 dòng).

## 3. Kế hoạch tuần 8

1. Sửa Bản cam kết theo D059–D065, gửi GVHD và ký trước tuần 11.
2. Thống nhất với nhóm D059–D065 (PROPOSED → quyết định của nhóm); chốt cổng thanh toán thử trên production.
3. Merge #89–#91; teammate chạy lại theo `docs/plan/CHAY_DU_AN_CHO_AI.md` để xác nhận đã chạy được.
4. Cập nhật SDD module M03–M05, M09, M10, M12, M13 theo collection và lớp miền của D060.
5. Phương án cho ba ngưỡng band chưa hiệu chuẩn; cân nhắc huấn luyện lại model trên bản chép lời của Whisper đang chạy để bớt bài phải duyệt.
6. Bổ sung AI Prompt Log tuần 6 của Sang.
