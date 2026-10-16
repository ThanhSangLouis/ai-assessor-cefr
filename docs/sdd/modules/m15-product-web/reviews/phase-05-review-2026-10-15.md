# M15 — Phase 05 Plan & Task Readiness review — 15/10/2026

**PHASE RECORD ID:** M15-05-A1 · **SCOPE ID/ROOT:** M15 · `docs/sdd/modules/m15-product-web/`
**SUBJECT:** [Plan v0.2](../05-plan.md) + [Tasks v0.2](../06-tasks.md); recommendation chỉ cho `M15-TASK-001A` thuộc W5-N01.1.
**BASE REVISION:** `ced32e90509eee439c1660507d31b18c2854829a` cộng local M15 documentation diff ngày 15/10/2026.
**SHA-256 tại review:** Plan `d31843efdb6ffb9f86da59ea9ab8be03ffe5a383495bb9bd5683f511c78a7322`; Tasks `cc7ea61fbc1bc2dc3bdd121ae4eff07de0994b95f6af61b0ba85011fd3712f66`. Sau khi ghi user verdict/task metadata, SHA-256 hiện tại: Plan `8c014f4f21af43f49b2737ee388ed213994ce059dbdb8ebf30640609c3bd088e`; Tasks `5171684c75461fcc187f5b59c6b864148a96ac7ed021e45c40d45a053ff06ebb`; không đổi scope/DoR của 001A.
**USER VERDICT:** `APPROVED` ngày 15/10/2026 (Asia/Bangkok), trả lời trực tiếp “APPROVED Phase 05 cho 001A”. **APPLICABILITY:** chỉ `M15-TASK-001A`; 001B/002–006 và W5-N01–N04 toàn phần không nằm trong approval này.

| DoR check | Result | Evidence / limitation |
| --- | --- | --- |
| FR/AC → TEST → Task | PASS cho 001A | FR-001/008, AC-001/004 phần shell → TEST-001/008/009/012 → W5-N01.1; parent AC chưa PASS |
| Boundary/data flow/contract | PASS cho 001A | Chỉ `_document`/`LOCAL_CSS` và page hiện có; không đổi route/auth/payload; không cần producer contract mới |
| Runtime và file ownership | PASS có preflight | Python WSGI renderers hiện ở `src/aicefr/api/templates.py`; source lock và thông báo Thắng/Sang trước khi Antigravity sửa file chung |
| Testability/commands/evidence | PASS cho kế hoạch | Pytest/lint/format/non-smoke/coverage/browser fixture được quy định; actual tests/browser vẫn `NOT_RUN` trước Phase 06 |
| Scope/recovery | PASS | Allowed files rõ; out of scope và `BLOCKED` nếu impact sang `wsgi.py`, portal, package/backend; một diff/Task ID và review/fix/verification |
| Producer-dependent tasks | `BLOCKED` | M10–M14/M16 approved contract, canonical route, M11/M12 security policy, M13 disclosure và M14 receipt chưa đủ; không đề xuất prompt cho 001B/002–006 |

**OPEN RISK:** 001A sửa shared HTML/CSS ảnh hưởng mọi role; cần preflight lock và regression trên page hiện hữu. Roboto/package/nav và toàn bộ user journey không nằm trong 001A; không đánh W5-N01.1 hay W5-N01 `DONE` từ output này. Thư mục `EDUZ/` là untracked data của user, phải bảo toàn, không đưa vào fingerprint exclusion tùy tiện.

**CODEX CHECK RESULT:** `PASS` cho readiness của 001A, `BLOCKED` cho các task producer-dependent. **CODEX RECOMMENDATION tại review:** `RECOMMEND APPROVAL` Phase 05 **chỉ cho M15-TASK-001A**. Chủ dự án đã duyệt phạm vi hẹp này. Nếu muốn approve toàn W5-N01–N04, còn cần contract/version và Phase 05 review mới cho phần đó. **NEXT ACTION:** tạo prompt/file/log với Prompt ID, base revision và `sdd-workspace-v2` fingerprint, rồi giao Antigravity.
