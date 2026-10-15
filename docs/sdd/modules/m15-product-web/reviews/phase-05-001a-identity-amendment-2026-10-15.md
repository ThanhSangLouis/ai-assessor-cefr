# M15 — Phase 05 amendment review — 001A / identity markup

**PHASE RECORD ID:** `M15-05-001A-F06-A1` · **SCOPE ID/ROOT:** M15 / `docs/sdd/modules/m15-product-web/`  
**SUBJECT:** [Plan & Task delta v0.2a](../05-001a-identity-amendment.md) cho `M15-TASK-001A`, chỉ `FINDING-M15-TASK-001A-06`.  
**BASE/HEAD:** review trên head `6baf720f173b440eb961676b09ea290058a39b35`; chưa có source diff F06.  
**PRIOR APPROVAL:** M15 Phase 01/03/04 APPROVED; Phase 05 v0.2 APPROVED chỉ cho 001A với file list không gồm `identity.py`. M11 Phase 01 vẫn PENDING, theo `m11-identity-account/07-status.md`.  
**USER DIRECTION:** cho phép bổ sung `identity.py` sau xác nhận source lock M11 và duyệt lại Phase 05. Chủ dự án đã xác nhận lock và trả lời riêng “APPROVED Phase 05 cho F06” ngày 15/10/2026 (Asia/Bangkok).

| DoR check | Codex assessment | Evidence / gate |
| --- | --- | --- |
| FR/AC/Test trace | PASS cho đề xuất | M15 Spec v0.3 có main/skip/one H1; Test Plan v0.2 TEST-001/008, TEST-002 chỉ regression auth; không đổi contract M11. |
| Actual problem | PASS | `identity.py:602-611` tạo `<main><h1>` trong body; `_document` ở `templates.py:383-384` tạo outer `main#main` và H1. F06 Review Record A1. |
| Boundary/smallest change | PASS cho kế hoạch | Chỉ markup `_password_page`; preserve route, auth, field/action, notice escaping, copy hữu ích; test semantic mới dưới `tests/local/`. |
| Ownership/source lock | PASS có preflight | Chủ dự án xác nhận ngày 15/10/2026 rằng Thắng đã khóa riêng `identity.py` và không có phiên AI khác đang sửa file. Đây là xác nhận qua chủ dự án; Antigravity phải kiểm lại trạng thái tại preflight. |
| Runtime/check/evidence | PASS cho kế hoạch | Targeted shell và `tests/api/test_identity_api.py`, browser semantic, lint/format, non-smoke/coverage theo 001A; failed checks phải hiện raw output. |
| Phase impact | PASS có điều kiện | Phase 03/04 không đổi vì requirement/test đã duyệt bao phủ semantic; nếu owner thấy contract/behavior M11 đổi, dừng và re-review phase sớm hơn. M11 module không được tự duyệt từ amendment M15. |

**OPEN FINDING:** nếu owner M11 báo contract impact mới thì quay lại phase sớm nhất bị ảnh hưởng; preflight phải xác nhận lock và baseline còn hiệu lực.  
**CODEX CHECK RESULT:** `PASS` cho readiness của delta F06, với preflight lock/baseline bắt buộc lúc handoff.  
**CODEX RECOMMENDATION:** `RECOMMEND APPROVAL` Phase 05 **chỉ cho delta F06**; không duyệt M11 module hoặc các task M15 khác.  
**USER VERDICT:** `APPROVED` **chỉ cho F06**. **VERIFIED/APPROVED BY:** chủ dự án, trả lời trực tiếp “APPROVED Phase 05 cho F06”. **USER VERDICT AT:** 15/10/2026 (Asia/Bangkok).  
**NEXT ACTION:** phát reissue prompt sửa gộp F01–F06 với base/fingerprint mới; Antigravity chỉ sửa `_password_page` trong `identity.py` theo amendment, rồi Codex review actual diff/evidence Phase 07 A2. Approval này không đổi verdict M11 module hoặc mở M15 task khác.
