# M06 — 05 Plan & Task Readiness (Kế hoạch)

> **BẢN NHÁP W2 (v0.1, 25/09/2026).** Chuẩn bị theo yêu cầu chủ dự án; Phase 01 của M06 vẫn `DRAFT/PENDING`. Nội dung dưới đây chưa là Specification/Plan được duyệt và không cấp quyền phát prompt triển khai.

> **Cập nhật direct implementation (28/09/2026):** chủ dự án yêu cầu triển khai trực tiếp; actual diff/evidence được ghi riêng, không thay Phase 05 hoặc user verdict.

**Owner đề xuất:** Nguyên. **Phạm vi source actual:** `src/aicefr/report/`, M01 presentation adapter, M07 verification boundary và tests M06. Evidence: `evidence/M06-EVID-DIRECT-20260928.md`.

## Kiến trúc và thứ tự triển khai

- Thiết kế ReportInput/EvidenceRef/DiagnosticReport và validator cross-response/version.
- Tạo template comment giới hạn theo criterion/evidence; không có evidence thì report nêu thiếu.
- Kết xuất report qua M01 UI; contract M07 verification state chuẩn bị W2, integration W3.

## Phụ thuộc và bàn giao

- M03 timestamp, M04 feature ref, M05 estimated/refusal result; M01/M08 quyền xem; M07 review status.
- Template feedback cần giảng viên duyệt nếu phát biểu về năng lực/ưu tiên cải thiện.

## Required checks và review

- Trước task: đối chiếu `01` → `03` → `04`, chốt các quyết định `OPEN`, xác nhận đường dẫn được phép sửa và baseline/fingerprint của repo dự án. Git đã được khởi tạo trong repo dự án ngày 25/09/2026; dùng commit/diff và revision thực làm evidence sau khi có baseline commit.
- Khi triển khai: type hints cho contract public; validation tại boundary; hàm logic nhỏ và có test; không truyền trạng thái bằng dict vô kiểu giữa module. Mỗi dependency, model và download phải có lý do gắn với task cùng provenance rõ.
- Sau task: chạy các test ID của task, `ruff`/typecheck nếu được cấu hình, kiểm tra diff và privacy. Review code/test riêng tại Phase 07; chạy lại checks trên final revision tại Phase 08.
- Antigravity chỉ nhận prompt sau verdict `APPROVED` của Phase 01, 03, 04 và 05 đúng version. Prompt, raw report và review lưu trong scope root; `docs/evidence/` chỉ dẫn chiếu theo rubric.

## Rủi ro và phương án xử lý

- Comment template có thể suy quá mức từ proxy; giới hạn vào điều quan sát được và review ngôn ngữ.
- Dữ liệu version lệch tạo link sai; validator chặn trước render.

## Definition of Ready (điều kiện phát prompt)

- Schema EvidenceRef và trạng thái score/review thống nhất; comment templates được owner review.
- Quy tắc bản report `NOT_EVALUATED` được duyệt.
- Phase 01/03/04/05 đúng version được duyệt.

**CODEX CHECK RESULT:** DRAFT — ranh giới và phụ thuộc đã mô tả; các quyết định mở/approval khiến task chưa `READY`. **User verdict Phase 05:** PENDING.


## Actual implementation — W4-N4, 12/10/2026

Validator/builder, report SQLite và persisted M07 callback có implementation/test. Fixture không là validation CEFR. Source đã có trong Git tại base `3b2d2b7`; working fix binary read M08/regression test được Nguyên cho phép riêng ngày 12/10. [Evidence hiện hành](evidence/M06-W4-20261012.md) thay snapshot 28/09 làm nguồn current technical record; snapshot cũ giữ lịch sử. Chưa có Phase 05 approval hoặc prompt Antigravity mới từ lượt này.
