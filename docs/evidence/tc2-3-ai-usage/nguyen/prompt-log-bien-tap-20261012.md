# AI Prompt Log của Nguyên — Biên tập lời văn

**Ngày biên tập:** 12/10/2026. **Scope ban đầu:** W05, sheet Nguyên, hàng 6–12. **Người dùng yêu cầu:** lời văn như một người sử dụng prompt chuyên nghiệp. **Vị trí lưu hiện tại:** W04, sheet Nguyên, hàng 6–12 theo [yêu cầu chuyển file](chuyen-log-sang-W04-20261012.md); ID đối chiếu bên dưới giữ nguyên.

Cột E là phiên bản biên tập từ yêu cầu/xác nhận trong chat. Các đoạn biên tập giữ mục tiêu và ý nghĩa, diễn đạt rõ ngữ cảnh, phạm vi và đầu ra; không phải bản chép nguyên văn prompt đã gửi. Bản gốc được giữ dưới đây để đối chiếu. Ngày, người dùng và công cụ của năm bản ghi cũ giữ nguyên; hai yêu cầu chỉnh log mới ghi ngày 12/10/2026, tool Codex.

Các dòng Nguyên W03 đã có cấu trúc prompt đầy đủ nên được giữ nguyên. Lượt biên tập không bổ sung lịch sử 05–11/10, không thay đổi sheet Thắng/Sang hay công thức Tổng hợp. Tổng W05 sau lượt biên tập, trước chuyển file: Nguyên 7, toàn workbook 7.

## Đối chiếu từng bản ghi

### W05-R06

**Nội dung gốc:**

> đọc plan week 4 và với task của tôi (Nguyên)

**Prompt biên tập:**

Hãy đọc kế hoạch tuần 4 và xác định các task thuộc trách nhiệm của Nguyên (M01, M06, M07). Đối chiếu từng task với mã nguồn, trạng thái SDD và minh chứng hiện có; tổng hợp kết quả, phần còn thiếu và thứ tự ưu tiên thực hiện.

**Công việc:** Đối chiếu kế hoạch W4 với các task và minh chứng của Nguyên.

### W05-R07

**Nội dung gốc:**

> Hãy hoàn thiện toàn bộ các task week4 của tôi

**Prompt biên tập:**

Hãy hoàn thiện các task W4-N1–W4-N6 của Nguyên trong phạm vi đã được phân công. Kiểm tra phần triển khai hiện có, xử lý vấn đề kỹ thuật, đồng bộ tài liệu SDD và chuẩn bị hồ sơ cần thiết. Lưu minh chứng kiểm tra và báo cáo rõ kết quả cùng các mục còn phụ thuộc dữ liệu hoặc xác nhận thực tế.

**Công việc:** Hoàn thiện phần kỹ thuật, tài liệu SDD và hồ sơ W4-N1–N6.

### W05-R08

**Nội dung gốc:**

> Chưa có 1 và 3

**Prompt biên tập:**

Tôi xác nhận hiện chưa có kết quả khảo sát/phỏng vấn TC1 và lịch sử prompt AI trong tuần 04. Hãy dùng thông tin này khi hoàn thiện hồ sơ W4-N5 và đối chiếu AI log, giữ rõ những nội dung chưa có nguồn minh chứng.

**Công việc:** Xác nhận phần thiếu trong khảo sát TC1 và lịch sử AI W04.

### W05-R09

**Nội dung gốc:**

> cứ cho là có rồi đi

**Prompt biên tập:**

Với W4-N6, hãy sử dụng giả định đã có hai giám khảo độc lập và một người phân xử để hoàn thiện hồ sơ và quy trình dự kiến. Ghi rõ đây là giả định lập kế hoạch; thông tin nhân sự và nguồn cam kết cần được xác nhận riêng.

**Công việc:** Chuẩn bị hồ sơ N6 theo giả định về ba vị trí nhân sự.

### W05-R10

**Nội dung gốc:**

> Cho phép sửa; tôi thông báo Thắng

**Prompt biên tập:**

Tôi cho phép áp dụng patch W4-N2-M08 đã trình bày: bổ sung O_BINARY trong src/aicefr/storage/blob.py và regression test bảo toàn byte CRLF/0x1A. Hãy kiểm tra lại phần tích hợp sau thay đổi và lưu kết quả. Tôi chịu trách nhiệm thông báo Thắng về thay đổi thuộc M08.

**Công việc:** Cho phép fix binary read M08 và kiểm tra lại phần tích hợp.

### W05-R11

**Nội dung gốc:**

> hãy sửa lại promt log của tôi (nguyên)

**Prompt biên tập:**

Hãy rà soát và chỉnh sửa AI Prompt Log trong sheet Nguyên, bảo đảm nội dung công việc, prompt và minh chứng được trình bày rõ ràng, thống nhất.

**Công việc:** Rà soát và chỉnh sửa AI Prompt Log của Nguyên.

### W05-R12

**Nội dung gốc:**

> sửa lại sao cho lời văn như 1 bạn đang sử dụng promt 1 cách chuyên nghiệp

**Prompt biên tập:**

Hãy biên tập lời văn của các prompt theo phong cách chuyên nghiệp: nêu rõ mục tiêu, phạm vi xử lý và đầu ra phù hợp với từng yêu cầu. Giữ nguyên ý nghĩa của nội dung gốc.

**Công việc:** Biên tập lời văn prompt theo phong cách chuyên nghiệp.

## Kiểm tra và nguồn

[Workbook W04 — vị trí hiện tại](../AI%20Prompt%20Log%20-%20W04%20-%202026-10-05_2026-10-11.xlsx), [báo cáo W4](../../../reports/week-04/bao-cao-tuan-04-nguyen.md), [audit W04](W04-audit.md). Cột Minh chứng của từng hàng dẫn tới hồ sơ tương ứng và ID đối chiếu trong tài liệu này. Các hash/fingerprint của lượt biên tập bên dưới mô tả snapshot trước chuyển file; [record chuyển](chuyen-log-sang-W04-20261012.md) dẫn tới kiểm tra hiện hành.

Kiểm tra bảo toàn XML xác nhận chỉ thay các ô công việc/prompt/minh chứng được yêu cầu, tiêu đề cột E, chiều cao hàng 6–12 và hai dòng mới; Tổng hợp cập nhật giá trị đếm với công thức nguyên vẹn. Các phần khác trong workbook giữ nguyên. [Kết quả kiểm tra](prompt-log-bien-tap-20261012-checks.json) giữ hash trước/sau và scope thay đổi.

Fingerprint W4 trong báo cáo/module thuộc snapshot trước lượt biên tập log này. Phép đo kỹ thuật ở snapshot đó giữ nguyên; không chạy lại test source cho thay đổi lời văn. Fingerprint dưới đây dùng helper sdd-workspace-v2, normalize duy nhất trường WORKSPACE FINGERPRINT trong tài liệu này; manifest giữ local ngoài Git.

WORKSPACE FINGERPRINT: ddeac3792181714d9cad96e58092b902216526e0c9d27d0c5d1c8b9187b6079e
