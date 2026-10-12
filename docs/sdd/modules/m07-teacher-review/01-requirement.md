# M07 — Teacher Review

| Metadata | Giá trị |
| --- | --- |
| SCOPE ID / TYPE | M07 / module |
| SCOPE ROOT | `docs/sdd/modules/m07-teacher-review/` |
| OWNER | Nguyên (đề xuất W2–W3) |
| LIFECYCLE | proposed |
| PHASE 01 | DRAFT — chờ người dùng duyệt |
| RESEARCH MODE | Đề xuất `SKIP`; người dùng quyết định trong Phase 01 |
| TARGET | W2 chuẩn bị contract; W3 triển khai |
| RELATED SCOPES | M05 score/reason, M06 diagnostic report, M08 account/DB |
| SOURCE BASIS | [Tài liệu nguồn do nhóm tạo](../../../sources/README.md), [báo cáo W1](../../../reports/week-01/bao-cao-tuan-01.docx); SDD hiện hành quyết định phạm vi, contract và approval của module |
| CODE TARGET | `src/aicefr/review/`, `src/aicefr/api/review.py` — actual hiện có |

## Requirement (Yêu cầu)

**Mục tiêu:** Đưa ca không chắc chắn cho giảng viên, ghi nhận quyết định sửa/duyệt có audit.

**Trong phạm vi:** Review reason routing, hàng đợi, nghe audio, duyệt/sửa kèm lý do, khóa/chống đè nếu nhiều người.

**Ngoài phạm vi W2–W3:** Tự động phê duyệt thay giảng viên; tính lại score khi chỉ sửa nhãn thủ công.

| ID | Functional Requirement (Yêu cầu chức năng) |
| --- | --- |
| M07-FR-001 | Bài lỗi/near boundary/OOD được định tuyến theo reason code, trạng thái review được lưu nhất quán. |
| M07-FR-002 | Chỉ role teacher được duyệt/sửa; `teacher_verified=true` chỉ sau action thật với reviewer/time/old/new/reason. |

## Acceptance Criteria (Tiêu chí chấp nhận)

| ID | Bằng chứng phải kiểm tra |
| --- | --- |
| M07-AC-001 | Bài cần review hiện trong hàng đợi; hai thao tác đồng thời không làm mất lịch sử hoặc ghi đè im lặng. |
| M07-AC-002 | Sinh viên không thể sửa/duyệt; hành động giảng viên cập nhật báo cáo và audit record. |

## W2 scope note (Ranh giới tuần 2)

W2 chỉ chuẩn bị contract trạng thái/reason/audit và giao diện nháp cho W3; không tự đánh dấu đã duyệt hoặc có thao tác giảng viên thật.

## Điều kiện chung và câu hỏi mở

- Unit test dùng fixture tạo bởi nhóm; smoke/integration chỉ dùng audio có quyền sử dụng. Fixture kiểm thử không là số liệu thực nghiệm; không log audio, transcript hoặc PII.
- ID, enum, schema/API xuyên module phải được cả owner liên quan review; mọi feature code chỉ bắt đầu sau khi Phase 01, 03, 04 và 05 của **module này** được người dùng duyệt theo thứ tự.
- Chủ dự án đã chọn 5 tiêu chí độc thoại làm bản nháp W2; rubric học thuật vẫn cần xác minh. Giữ field `Interaction=null` cùng lý do `insufficient_evidence` cho độc thoại. Dữ liệu/model và lịch 3 tuần xem [roadmap](../../../plan/three-week-roadmap.md).

