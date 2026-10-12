# M01 — 05 Plan & Task Readiness (Kế hoạch)

> **BẢN NHÁP W2 (v0.1, 25/09/2026).** Chuẩn bị theo yêu cầu chủ dự án; Phase 01 của M01 vẫn `DRAFT/PENDING`. Nội dung dưới đây chưa là Specification/Plan được duyệt và không cấp quyền phát prompt triển khai.

> **Cập nhật direct implementation (28/09/2026):** chủ dự án yêu cầu triển khai trực tiếp; actual diff/evidence được ghi riêng, không thay Phase 05 hoặc user verdict.

**Owner đề xuất:** Nguyên. **Phạm vi source actual:** `src/aicefr/api/student.py`, `src/aicefr/api/templates.py`, `src/aicefr/api/wsgi.py`, contract/storage additions và tests M01. Evidence: `evidence/M01-EVID-DIRECT-20260928.md`.

## Kiến trúc và thứ tự triển khai

- Dựng schema request/response và API mỏng; dùng contract M08 cho session/consent/owner, không tự viết auth trong M01.
- Viết đường submit có validation, lưu blob/Response atomic hoặc rollback rõ; gọi pipeline qua port có kiểu.
- Viết status/report endpoint và giao diện tối thiểu; test quyền truy cập và trạng thái lỗi.

## Phụ thuộc và bàn giao

- M08 cung cấp auth, consent, BlobStore và ResponseRepository contract trước M01-TASK-001.
- M02–M06 trả artifact/status qua interface có kiểu; Thắng giữ orchestration, Nguyên giữ HTTP/UI M01.

## Required checks và review

- Trước task: đối chiếu `01` → `03` → `04`, chốt các quyết định `OPEN`, xác nhận đường dẫn được phép sửa và baseline/fingerprint của repo dự án. Git đã được khởi tạo trong repo dự án ngày 25/09/2026; dùng commit/diff và revision thực làm evidence sau khi có baseline commit.
- Khi triển khai: type hints cho contract public; validation tại boundary; hàm logic nhỏ và có test; không truyền trạng thái bằng dict vô kiểu giữa module. Mỗi dependency, model và download phải có lý do gắn với task cùng provenance rõ.
- Sau task: chạy các test ID của task, `ruff`/typecheck nếu được cấu hình, kiểm tra diff và privacy. Review code/test riêng tại Phase 07; chạy lại checks trên final revision tại Phase 08.
- Antigravity chỉ nhận prompt sau verdict `APPROVED` của Phase 01, 03, 04 và 05 đúng version. Prompt, raw report và review lưu trong scope root; `docs/evidence/` chỉ dẫn chiếu theo rubric.

## Rủi ro và phương án xử lý

- Nếu storage write thành công nhưng DB fail, blob rác phải được dọn có log; không coi response thành công.
- W2 thiếu local pipeline/model thì status/report được kiểm bằng integration contract, không báo E2E thực đạt.

## Definition of Ready (điều kiện phát prompt)

- M08 contract/consent decision được owner M01/M08 cùng review.
- Format/size và timeout policy có giá trị cấu hình được duyệt.
- AC và test plan Phase 01/03/04/05 được người dùng duyệt.

**CODEX CHECK RESULT:** DRAFT — ranh giới và phụ thuộc đã mô tả; các quyết định mở/approval khiến task chưa `READY`. **User verdict Phase 05:** PENDING.


## Actual implementation — W4-N4, 12/10/2026

Submit/status/report và template có code/test; auto-refresh 5 giây đã kiểm tra cả 6 trạng thái. Browser W3 có evidence lịch sử, current browser NOT_RUN. Source đã có trong Git tại base `3b2d2b7`; working fix binary read M08/regression test được Nguyên cho phép riêng ngày 12/10. [Evidence hiện hành](evidence/M01-W4-20261012.md) thay snapshot 28/09 làm nguồn current technical record; snapshot cũ giữ lịch sử. Chưa có Phase 05 approval hoặc prompt Antigravity mới từ lượt này.
