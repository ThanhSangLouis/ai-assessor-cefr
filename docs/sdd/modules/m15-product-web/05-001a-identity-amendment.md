# M15 — Proposed Phase 05 amendment for M15-TASK-001A / F06

**Version:** v0.2a · **STATUS:** Phase 05 `APPROVED` ngày 15/10/2026 chỉ cho F06 · **SCOPE ID/ROOT:** M15 / `docs/sdd/modules/m15-product-web/`  
**Related scope:** M11 Identity & Account (`docs/sdd/modules/m11-identity-account/`), owner Thắng.  
**Decision source:** Chủ dự án chọn ngày 15/10/2026: cho phép bổ sung sửa `identity.py` **sau khi** owner M11 xác nhận source lock và Phase 05 được duyệt lại cho thay đổi này. Chủ dự án sau đó xác nhận Thắng đã khóa sửa riêng `identity.py` và không có phiên AI khác đang sửa file; đây là xác nhận qua chủ dự án, không phải biên bản riêng do Thắng gửi. Chủ dự án tiếp tục trả lời trực tiếp “APPROVED Phase 05 cho F06”.  
**Base:** M15 Plan/Tasks v0.2 đã APPROVED chỉ cho 001A; Phase 07 A1 `CHANGES_REQUIRED`, finding `FINDING-M15-TASK-001A-06`.

## Plan delta

| Mục | Bổ sung đề xuất cho riêng F06 |
| --- | --- |
| Mục tiêu | Trang `/password-change` render đúng một `main#main`, một H1 và skip link đến main; giữ nguyên nội dung hữu ích và chức năng đổi mật khẩu. |
| Source | Chỉ `src/aicefr/api/identity.py`, hàm `_password_page` (hiện quanh dòng 597–613). Loại bỏ `<main>` lồng; chuyển heading nội bộ thành cấp hợp lý hoặc sắp xếp lại heading để giữ một H1 mà không bỏ business copy. `_document` tiếp tục sở hữu shell/landmark. |
| Test/evidence | Test semantic ở `tests/local/test_templates_m15_shell.py` hoặc test mới dưới `tests/local/`, kiểm HTML thực từ `_password_page`; chạy thêm `tests/api/test_identity_api.py` để bảo đảm auth gate, form fields/action và response không regress. Browser QA kiểm route/fixture thích hợp với một main/H1, skip target và focus. |
| Frozen | Không đổi route/method, cookie/session, temporary-password gate, form `action`, field names, security policy, response DTO/status, notice escaping hoặc business logic. Không sửa `wsgi.py`, M11 service/repository, portal, package/config hay API test thuộc M11 trong amendment này. |
| Owner và lock | Nguyên vẫn là owner của `M15-TASK-001A`, Antigravity implementer. Thắng phải xác nhận khóa độc quyền tạm thời cho vùng `_password_page` trong `identity.py` và không có phiên AI khác sửa cùng vùng; Thắng review impact M11 trước khi gộp. Codex review actual diff và evidence. |
| Recovery | Nếu cần sửa logic M11, contract, text nghiệp vụ hoặc file ngoài bảng này, Antigravity trả `BLOCKED`; Codex quay lại phase sớm nhất bị ảnh hưởng và xin quyết định scope mới. Diff F06 tách rõ khỏi F01–F05 để review. |

**Trace:** M15 Specification v0.3 §Layout/navigation (main landmark, skip link, one H1) và route hiện hành `/password-change`; M15-FR-001 / M15-AC-001 phần shell; M15-TEST-001/008 (semantic/keyboard/responsive), M15-TEST-002 chỉ regression auth gate. Không thêm requirement hoặc test strategy mới, nên đề xuất re-review **Phase 05** cho allowed file/ownership/DoR; Phase 03/04 giữ verdict đã có nếu owner M11 xác nhận không đổi contract. Việc này không duyệt M11 Phase 01–05, không mở M15-001B/002–006 và không nghiệm thu toàn W5-N01.

## Definition of Ready và Quality Contract delta

1. **Gate 1 — M11 lock:** chủ dự án đã xác nhận Thắng khóa sửa riêng `identity.py` cho phần mở rộng này và không có phiên AI khác đang sửa file (trả lời trực tiếp ngày 15/10/2026). Antigravity vẫn phải kiểm preflight base revision/fingerprint và không có concurrent edit lúc bắt đầu; nếu trạng thái đổi thì trả `BLOCKED`.
2. **Gate 2 — Phase 05 user verdict:** chủ dự án đã trả lời “APPROVED Phase 05 cho F06” ngày 15/10/2026; [record](reviews/phase-05-001a-identity-amendment-2026-10-15.md) giới hạn approval vào đúng delta này.
3. Codex phát bản reissue của prompt sửa gộp, có Prompt ID, Task ID, base revision/fingerprint theo helper `sdd-workspace-v2`. Prompt A2 cũ chỉ có F01–F05 đã `SUPERSEDED`, không dùng để sửa `identity.py`.
4. Antigravity thêm test regression có assertion một main/H1 và preserve form/gate; chạy targeted template + identity API, lint/format, non-smoke/coverage và browser QA theo Quality Contract 001A. Report phải phân biệt failure do môi trường với regression bằng raw output. Phase 07 review lại F06 từ actual diff/evidence; Phase 08 chỉ sau user Phase 07 verdict.
