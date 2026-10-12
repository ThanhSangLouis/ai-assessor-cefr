# M01 — Intake & Student Flow

| Metadata | Giá trị |
| --- | --- |
| SCOPE ID / TYPE | M01 / module |
| SCOPE ROOT | `docs/sdd/modules/m01-intake-student/` |
| OWNER | Nguyên (đề xuất W2–W3) |
| LIFECYCLE | proposed |
| PHASE 01 | DRAFT — chờ người dùng duyệt |
| RESEARCH MODE | Đề xuất `SKIP`; người dùng quyết định trong Phase 01 |
| TARGET | W2 |
| RELATED SCOPES | M08 (auth/consent/storage), M02–M06 (pipeline và report) |
| SOURCE BASIS | [Tài liệu nguồn do nhóm tạo](../../../sources/README.md), [báo cáo W1](../../../reports/week-01/bao-cao-tuan-01.docx); SDD hiện hành quyết định phạm vi, contract và approval của module |
| CODE TARGET | `src/aicefr/api/student.py`, `src/aicefr/api/templates.py`, `src/aicefr/api/wsgi.py` — actual hiện có |

## Requirement (Yêu cầu)

**Mục tiêu:** Sinh viên có quyền nộp một bài nói độc thoại và theo dõi trạng thái tới báo cáo, qua HTTP/UI mỏng và contract xử lý có kiểu.

**Trong phạm vi:** Upload trong W2; ghi âm trình duyệt nếu được duyệt cho W3; kiểm tra quyền/consent trước khi nhận; gắn `task_id`, `response_id`, version; xem trạng thái/báo cáo của chính mình.

**Ngoài phạm vi W2–W3:** Nghiệp vụ QC/ASR/scoring; tự tạo tài khoản; dashboard tiến độ nâng cao.

| ID | Functional Requirement (Yêu cầu chức năng) |
| --- | --- |
| M01-FR-001 | Chỉ tài khoản sinh viên có consent hợp lệ được tạo `Response`; bài nộp phải có ID giả danh, task/version và audio ref. |
| M01-FR-002 | Giao diện/API cho upload, trạng thái và báo cáo chỉ trả dữ liệu của chủ sở hữu; lỗi transport/status có reason code. |

## Acceptance Criteria (Tiêu chí chấp nhận)

| ID | Bằng chứng phải kiểm tra |
| --- | --- |
| M01-AC-001 | Không consent hoặc sai role: không tạo bài; người khác truy cập response bị chặn mà không lộ nội dung. |
| M01-AC-002 | Bài kiểm tra có nguồn sử dụng hợp lệ đi qua lời gọi pipeline; trạng thái `QUEUED/RUNNING/COMPLETED/REVIEW_REQUIRED/REJECTED/FAILED` được hiển thị đúng, không hiển thị score nếu chưa có. |

## W2 scope note (Ranh giới tuần 2)

W2 ưu tiên upload file có quyền sử dụng, consent và xem trạng thái của chính người nộp. Ghi âm trên trình duyệt là phần mở rộng W3 nếu đường upload và quyền truy cập đã được kiểm tra.

## Điều kiện chung và câu hỏi mở

- Unit test dùng fixture tạo bởi nhóm; smoke/integration chỉ dùng audio có quyền sử dụng. Fixture kiểm thử không là số liệu thực nghiệm; không log audio, transcript hoặc PII.
- ID, enum, schema/API xuyên module phải được cả owner liên quan review; mọi feature code chỉ bắt đầu sau khi Phase 01, 03, 04 và 05 của **module này** được người dùng duyệt theo thứ tự.
- Chủ dự án đã chọn 5 tiêu chí độc thoại làm bản nháp W2; rubric học thuật vẫn cần xác minh. Giữ field `Interaction=null` cùng lý do `insufficient_evidence` cho độc thoại. Dữ liệu/model và lịch 3 tuần xem [roadmap](../../../plan/three-week-roadmap.md).

