# W4-N6 — Hồ sơ giám khảo và người phân xử

**Owner:** Nguyên. **Ngày chuẩn bị:** 12/10/2026, W05 xử lý chuyển tiếp W4. **Version:** v1.0. **Trạng thái:** `PREPARED`; cam kết thực tế `NOT_VERIFIED`.

Nguyên chỉ dẫn “cứ cho là có rồi đi” trong chat ngày 12/10. Tài liệu dùng ba vị trí nhân sự làm **giả định kế hoạch**; chỉ dẫn này không cung cấp danh tính, ngày đồng ý hay nguồn xác nhận. Không có chữ ký hoặc cam kết được xác minh từ lượt này.

Nguồn scope: [plan W4](../../../../plan/week-04.md), W4-N6 và D030; [Requirement M07](../01-requirement.md), [contract/reason map](../contract-reason-map.md). Luồng chấm mù kép là đề xuất cho nghiên cứu W6–W7, không phải chức năng đã có của M07 hiện tại.

## Roster giả danh

| Mã | Vai trò dự kiến | Năng lực/điều kiện cần xác nhận | Ngày đồng ý / nguồn | Trạng thái |
| --- | --- | --- | --- | --- |
| R1 | Giám khảo 1 | Kinh nghiệm đánh giá bài nói; hiểu rubric được chọn; thời gian và không xung đột lợi ích | Chưa có | `NOT_VERIFIED` |
| R2 | Giám khảo 2 | Cùng điều kiện; chấm độc lập với R1 và không xem điểm AI | Chưa có | `NOT_VERIFIED` |
| A1 | Người phân xử | Có năng lực giải quyết bất đồng; độc lập với hai lượt chấm ban đầu | Chưa có | `NOT_VERIFIED` |

Mã trên là vị trí cần tuyển, không phải ba người đã tham gia. Danh tính thật, liên hệ, chữ ký và mapping mã ↔ người giữ ngoài Git do Nguyên quản lý; manifest chỉ có reference phù hợp quyền truy cập.

## Mẫu lời mời để Nguyên gửi

> Nhóm AI Assessor CEFR kính mời thầy/cô tham gia đánh giá bài nói tiếng Anh độc thoại cho nghiên cứu của đồ án. Vai trò dự kiến là [giám khảo độc lập/người phân xử]. Bộ audio sẽ có nguồn sử dụng và đồng ý phù hợp; rubric, khối lượng bài, lịch, cách truy cập và cách xử lý dữ liệu sẽ được thống nhất trước khi chấm. Với giám khảo độc lập, thầy/cô chấm mà không xem band AI hoặc kết quả người chấm khác. Thầy/cô có thể xác nhận khả năng tham gia, điều kiện chuyên môn, thời gian phù hợp và các giới hạn cần nhóm đáp ứng không?

Đây là bản soạn, chưa được gửi. Không tự đặt danh tính, thời gian hoặc số bài thay người tham gia.

## Mẫu cam kết cho từng người

Sao chép mẫu này cho R1, R2 và A1; điền thông tin thật trong hồ sơ hạn chế truy cập.

| Trường | Nội dung cần điền khi có xác nhận |
| --- | --- |
| Mã người tham gia / vai trò | R1, R2 hoặc A1; kiểm tra đủ ba người riêng biệt |
| Danh tính và năng lực | Bản hạn chế truy cập; bản public chỉ lưu mô tả ẩn danh được cho phép |
| Rubric và phạm vi band | Tên/version/nguồn rubric được GVHD chốt; không coi rubric bản nháp là đã phê duyệt học thuật |
| Khối lượng, thời gian, phương thức | Số bài tối đa, lịch, nền tảng có quyền truy cập; thống nhất với người tham gia |
| Độc lập / xung đột lợi ích | Giám khảo không xem điểm AI/điểm người khác; ghi mọi quan hệ có thể ảnh hưởng đánh giá |
| Dữ liệu và đồng ý | Audio có quyền sử dụng, quyền truy cập, không chuyển tiếp ngoài phạm vi được phép; cách rút tham gia |
| Xác nhận | Nội dung đồng ý, ngày thực tế, chữ ký hoặc thư xác nhận, reference và SHA-256 |
| Nguyên kiểm tra | Ngày kiểm tra, đủ thông tin/chưa đủ, vấn đề còn mở |

Mẫu chưa điền không là cam kết. Không đánh dấu “đã ký” hoặc điền ngày quá khứ nếu chưa có bằng chứng.

## Protocol chấm độc lập đề xuất

1. Sang và Nguyên thống nhất cùng GVHD rubric/version, đơn vị overall, bộ dữ liệu được phép dùng, tiêu chí loại bài và rule phân xử **trước** khi phát bài. Các quyết định này hiện `PENDING`.
2. Nguyên phân phối audio bằng ID giả danh và thứ tự đã ghi; xác nhận quyền/consent và kênh hạn chế truy cập. Không gửi score AI, report AI hoặc tên người nói cho R1/R2. Không dùng trang M07 hiện tại để claim blind rating vì trang này có thể hiện kết quả AI.
3. R1 và R2 chấm cùng tập bài độc lập, dùng cùng version rubric; giữ raw ratings riêng và ghi thời điểm. Mỗi người chỉ xem lượt của mình trong giai đoạn này.
4. Lưu hai kết quả gốc bất biến. Tính bất đồng từ hai lượt **trước phân xử**. Đề xuất gửi mọi bài khác overall band hoặc có cờ “không đủ bằng chứng” cho A1; rule cuối do Sang/Nguyên/GVHD chốt.
5. A1 nghe audio, xem hai đánh giá sau khi hoàn tất chấm độc lập và ghi quyết định kèm lý do. Không thay raw R1/R2 bằng điểm phân xử.
6. Sang phân tích độ đồng thuận; Nguyên cung cấp manifest ghép đúng `response_id`, rater ID, rubric và dataset version. Tách agreement người–người, kết quả phân xử và so sánh AI; chưa có ratings thì mọi metric `NOT_EVALUATED`.

Không bổ sung chức năng chấm mù kép vào source trong W4-N6. Nếu nhóm duyệt tích hợp D030, tạo/bổ sung SDD đúng module và thống nhất contract với Sang, Thắng trước triển khai.

## Bằng chứng và điều kiện khép task

| Evidence ID | Nội dung | Nguồn / checksum / người giữ | Trạng thái |
| --- | --- | --- | --- |
| W4-N6-PREP-001 | Roster, mẫu lời mời, mẫu cam kết và protocol | Tài liệu này, v1.0 | `PREPARED` |
| W4-N6-R1 | Xác nhận giám khảo 1 | Chưa cung cấp | `NOT_VERIFIED` |
| W4-N6-R2 | Xác nhận giám khảo 2 | Chưa cung cấp | `NOT_VERIFIED` |
| W4-N6-A1 | Xác nhận người phân xử | Chưa cung cấp | `NOT_VERIFIED` |

W4-N6 chỉ khép khi đủ xác nhận của ba người riêng biệt, vai trò và năng lực phù hợp, ngày thực tế và bằng chứng truy cập được. Đánh giá CEFR, agreement, người tham gia thật và nghiệm thu scope vẫn chưa được thực hiện từ bộ mẫu này.
