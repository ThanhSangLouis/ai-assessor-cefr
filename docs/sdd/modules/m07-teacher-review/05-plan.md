# M07 — 05 Plan & Task Readiness (Kế hoạch)

> **BẢN NHÁP W2 (v0.1, 25/09/2026).** Chuẩn bị theo yêu cầu chủ dự án; Phase 01 của M07 vẫn `DRAFT/PENDING`. Nội dung dưới đây chưa là Specification/Plan được duyệt và không cấp quyền phát prompt triển khai.

> **Cập nhật direct implementation (28/09/2026):** chủ dự án yêu cầu triển khai trực tiếp; actual diff/evidence được ghi riêng, không thay Phase 05 hoặc user verdict.

**Owner đề xuất:** Nguyên. **Phạm vi source actual:** `src/aicefr/review/`, `src/aicefr/api/review.py`, teacher queue/template/WSGI routes, contract/storage migration và tests M07. Evidence: `evidence/M07-EVID-DIRECT-20260928.md`.

## Kiến trúc và thứ tự triển khai

- W2 chỉ thiết kế ReviewCandidate/ReviewState/ReviewDecision và reason map; owner M05/M06/M08 review contract.
- W3 dựng repository transaction, queue/action API và UI; chặn stale revision/role.
- W3 nối M06 report, audit và browser QA trên dữ liệu được phép.

## Phụ thuộc và bàn giao

- M05/M02/M03 phát reason; M08 xác thực teacher, lưu audit/lock; M06 chỉ đọc state/final.
- W2 gate không phụ thuộc vào queue UI thật; W3 nghiệm thu M07 riêng.

## Required checks và review

- Trước task: đối chiếu `01` → `03` → `04`, chốt các quyết định `OPEN`, xác nhận đường dẫn được phép sửa và baseline/fingerprint của repo dự án. Git đã được khởi tạo trong repo dự án ngày 25/09/2026; dùng commit/diff và revision thực làm evidence sau khi có baseline commit.
- Khi triển khai: type hints cho contract public; validation tại boundary; hàm logic nhỏ và có test; không truyền trạng thái bằng dict vô kiểu giữa module. Mỗi dependency, model và download phải có lý do gắn với task cùng provenance rõ.
- Sau task: chạy các test ID của task, `ruff`/typecheck nếu được cấu hình, kiểm tra diff và privacy. Review code/test riêng tại Phase 07; chạy lại checks trên final revision tại Phase 08.
- Antigravity chỉ nhận prompt sau verdict `APPROVED` của Phase 01, 03, 04 và 05 đúng version. Prompt, raw report và review lưu trong scope root; `docs/evidence/` chỉ dẫn chiếu theo rubric.

## Rủi ro và phương án xử lý

- Nếu W2 lẫn thiết kế với implementation, có thể báo sai tiến độ; status W2 giữ `CONTRACT_DRAFT`.
- Nhiều teacher cùng sửa hoặc audit fail làm sai verified state; transaction/lock bắt buộc W3.

## Definition of Ready (điều kiện phát prompt)

- W2 reason/state/permission map được 3 owner review; user duyệt phạm vi W3 sau Phase 01.
- Data/role/audit retention policy M08 được chốt trước action thật.
- Phase 01/03/04/05 M07 được duyệt trước prompt W3.

**CODEX CHECK RESULT:** DRAFT — ranh giới và phụ thuộc đã mô tả; các quyết định mở/approval khiến task chưa `READY`. **User verdict Phase 05:** PENDING.


## Actual implementation — W4-N4, 12/10/2026

Contract/reason routing, queue/API/UI, decision/audit/CAS và portal claim/reopen có implementation/test. Cross-owner/user verdict PENDING; current browser NOT_RUN. Source đã có trong Git tại base `3b2d2b7`; working fix binary read M08/regression test được Nguyên cho phép riêng ngày 12/10. [Evidence hiện hành](evidence/M07-W4-20261012.md) thay snapshot 28/09 làm nguồn current technical record; snapshot cũ giữ lịch sử. Chưa có Phase 05 approval hoặc prompt Antigravity mới từ lượt này.
