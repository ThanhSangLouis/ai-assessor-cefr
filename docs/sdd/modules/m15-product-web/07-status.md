# M15 — Status

| Mục | Trạng thái |
| --- | --- |
| Lifecycle | proposed |
| Phase | 07 — Implementation Review `M15-TASK-001A` A1, A2R1 và A2R2; Codex recommendation mới nhất `CHANGES_REQUIRED`, user verdict `PENDING`; correction budget đã dùng, chờ quyết định chủ dự án sau khi R02 tái diễn; Phase 08 `NOT_STARTED` |
| Requirement | v0.2 · chủ dự án APPROVED ngày 15/10/2026; [Phase 01 record](reviews/phase-01-review-2026-10-15.md) |
| Research mode | RUN · chủ dự án chọn cùng Phase 01 verdict |
| Research | v0.3 DRAFT; hai read-only lane W5-N01/N02 và W5-N03/N04; source `40907cc` static, browser `NOT_RUN` |
| Specification | v0.3; Phase 03 user verdict APPROVED ngày 15/10/2026; Codex check khi review vẫn BLOCKED |
| Artifacts 04–06 | Test Plan v0.2 APPROVED, [Phase 04 review](reviews/phase-04-review-2026-10-15.md); Plan/Tasks v0.2 APPROVED chỉ cho 001A, [Phase 05 review](reviews/phase-05-review-2026-10-15.md); amendment v0.2a APPROVED chỉ cho F06 `identity.py`; W5-N01–N04 scope approved, readiness `BLOCKED` theo [Phase 05 precheck](reviews/phase-05-readiness-precheck-w5-n01-n04-2026-10-15.md) và [scope decision](reviews/w5-n01-n04-scope-approval-2026-10-15.md) |
| Implementation | A2R1 đã bàn giao diff/evidence tại `evidence/m15-task-001a-a2/`; A2R2 handoff/evidence được chủ dự án báo đã hoàn thành. Review A2R2: targeted Codex rerun 32 PASS; browser evidence 18 assertions/17 screenshot hashes hợp lệ; non-smoke 36 failures và coverage command exit 1; R01–R03 còn mở, không Verified. Correction bundle đã dùng; do R02 traceability lặp lại, bước sửa tiếp theo cần chủ dự án quyết định sau khi đánh giá lại task/Plan. Xem [Phase 07 A2R2 review](reviews/phase-07-review-a2r2-2026-10-15.md). |
| Prompt | A1 đã bàn giao; A2 cũ `SUPERSEDED_BEFORE_EXECUTION`; [A2R1](prompts/M15-W5-N01-001A-A2R1.md) và [A2R2 correction](prompts/M15-W5-N01-001A-A2R2.md) đã được thực thi. Chưa tạo prompt correction mới: correction budget mặc định đã dùng, R02 tái diễn, và `agy models` hiện chỉ liệt kê Gemini 3.8 Flash (High), không có Gemini 3.6 Flash (High) bắt buộc theo runner skill. Xem [prompt log](prompts/prompt-log.md), [Review Record A2R2](reviews/phase-07-review-a2r2-2026-10-15.md) và phần tái đánh giá bên dưới. |

UI work bắt đầu sau khi backend payload/error/authorization contract tương ứng freeze; mock có thể dùng cho component test nhưng không đủ để đánh dấu task DONE.

Sau pull `d60e8a4` ngày 15/10/2026, backend SCRUM-65/66/67 đã merge. M11/M14 có handoff API/UI và technical task `READY FOR REVIEW`, nhưng approval module/reviewer vẫn PENDING; M10/M12/M13/M16 cũng chưa cấp contract được duyệt cho M15. Không suy backend browser smoke thành QA N01–N04.

Chủ dự án chọn hướng giải quyết M15-P03-01–05, duyệt Phase 03/04 và Phase 05 riêng cho 001A ngày 15/10/2026. Cùng ngày, chủ dự án duyệt phạm vi W5-N01–N04; xem [scope decision](reviews/w5-n01-n04-scope-approval-2026-10-15.md). Quyết định scope không thay contract producer đã duyệt hoặc Phase 05 readiness review riêng cho 001B/002–006; các prompt đó chưa được phát. [Phase 03 review](reviews/phase-03-review-2026-10-15.md) vẫn ghi Codex check `BLOCKED` và finding cần kiểm lại trước task integration. Subagent Codex chỉ nghiên cứu/review đọc-only; Antigravity implementer.

Phase 07 [Review Record A1](reviews/phase-07-review-2026-10-15.md): skip link che H1, hover light thiếu contrast, browser QA ghi 8 console errors/8 failed requests dù report claim 0, assertion thiếu và coverage branch thực tế 85%. `/password-change` có main/H1 lồng, liên quan M11. Chủ dự án xác nhận Thắng đã khóa `identity.py`, sau đó `APPROVED` [amendment v0.2a](05-001a-identity-amendment.md) tại [Phase 05 F06 record](reviews/phase-05-001a-identity-amendment-2026-10-15.md) ngày 15/10/2026. Approval chỉ cho markup `_password_page`; M11 module vẫn PENDING. User verdict Phase 07: `PENDING`; Phase 08: `NOT_STARTED`.

Phase 07 [Review Record A2R1](reviews/phase-07-review-a2-2026-10-15.md): Base `6baf720` có 35 failures/557 passes; Codex khi đó đo current 33 failures/560 passes, tất cả IDs thuộc baseline. Sau đó chủ dự án báo A2R2 đã chạy. [Review Record A2R2](reviews/phase-07-review-a2r2-2026-10-15.md) ghi targeted rerun 32 PASS, nhưng non-smoke có 36 failures/558 passes/15 skipped/2 deselected; hai fail IDs không có trong baseline. Fingerprint prompt/report/current workspace không thống nhất; R03 cũng chưa assert primary action bắt buộc. Codex Recommendation `CHANGES_REQUIRED`; user verdict `PENDING`; Phase 08 `NOT_STARTED`. Không nâng W5-N01.1/W5-N01 lên DONE.

Phase 05 readiness precheck của W5-N01–N04: `BLOCKED` cho `001B`/`002`–`006` bởi contract/route/security approvals và các task phụ thuộc còn mở; xem [precheck matrix](reviews/phase-05-readiness-precheck-w5-n01-n04-2026-10-15.md). Không có prompt mới được phát.

Bốn báo cáo hiện trạng/brief đọc-only để giao SCRUM-73–76: [W5-N01](reviews/subagent-briefs/scrum-73-w5-n01-2026-10-15.md), [W5-N02](reviews/subagent-briefs/scrum-74-w5-n02-2026-10-15.md), [W5-N03](reviews/subagent-briefs/scrum-75-w5-n03-2026-10-15.md), [W5-N04](reviews/subagent-briefs/scrum-76-w5-n04-2026-10-15.md). Đây là gói giao đọc-only, không phải Phase 05 verdict hay quyền sửa source.

## SCRUM-73/SCRUM-74 — Codex read-only follow-up

- [SCRUM-73 / W5-N01](reviews/scrum-73-w5-n01-readonly-research-2026-10-15.md): route/method/role/consent và page-to-contract map được đối chiếu với source. `M15-TASK-001B`/`002` tiếp tục `BLOCKED`; tại thời điểm brief, `001A` A2R1 còn `CHANGES_REQUIRED` và A2R2 chưa chạy; handoff A2R2 sau đó được ghi ở Review Record riêng.
- [SCRUM-74 / W5-N02](reviews/scrum-74-w5-n02-readonly-research-2026-10-15.md): xác nhận persistence learning có nền kỹ thuật nhưng chưa có learning API/service/UI; M10/M13 chưa duyệt và T01 chưa được dùng làm contract freeze. `M15-TASK-003` tiếp tục `BLOCKED`.
- Hai brief follow-up trên chỉ đọc source/SDD; không sửa code, không chạy test/browser QA, không phát prompt và không ghi user approval. Review A2R2 là lượt riêng bên dưới.

A2R2 PROMPT STARTING WORKSPACE FINGERPRINT (as recorded): `1ae115f3a33d0d76baa28de634654eec31311d60ebaeb8392748478011e56b37`
WORKSPACE FINGERPRINT: b7214b57d426435c5ce7ce02f2e9255cfdbdbd8c2fdecd0e6a2d3d6929a4c545
FINGERPRINT CONTEXT: Footer fingerprint is the Codex review workspace after Review Record/W05 updates. At review entry, Codex computed `1ae115f3…`, matching the A2R2 prompt start but not Antigravity report's final fingerprint.
FINGERPRINT ALGORITHM: `sdd-workspace-v2`
FINGERPRINT METADATA FILES: `docs/sdd/modules/m15-product-web/07-status.md`; `docs/sdd/modules/m15-product-web/prompts/M15-W5-N01-001A-A2R2.md`; `docs/sdd/modules/m15-product-web/prompts/prompt-log.md`
FINGERPRINT EXCLUSIONS: `EDUZ/**`; `docs/sdd/modules/m15-product-web/evidence/m15-task-001a-a2r2/**` (A2R2 preflight options)
NEXT ACTION: Không tự phát correction prompt khác. Chờ chủ dự án quyết định đánh giá lại task/Plan và cách xử lý blocker runner/model; sau quyết định, Codex cập nhật readiness rồi mới tiếp tục đúng gate. User verdict Phase 07 vẫn `PENDING`; Phase 08 `NOT_STARTED`. W5-N01.1/W5-N01 chưa DONE. W5-N01–N04 còn lại tiếp tục chờ contract/version/verdict và Phase 05 readiness riêng theo [precheck matrix](reviews/phase-05-readiness-precheck-w5-n01-n04-2026-10-15.md); không phát prompt cho task còn `BLOCKED`.

## Tái đánh giá correction budget sau Review A2R2 — 15/10/2026

A2R2 là bundled correction xử lý các finding từ review A2R1. Review hiện tại còn `M15-A2R2-R01` (MAJOR), `R02` (BLOCKER) và `R03` (MAJOR) mở. R02 tiếp tục là lỗi traceability/fingerprint qua các attempt; theo quy tắc ngân sách vòng lặp của skill SDD, mặc định chỉ có một bundled correction và khi cùng root cause tái diễn phải dừng để đánh giá lại task/Plan hoặc xin quyết định chủ dự án. Vì vậy chưa tạo hoặc gửi prompt A2R3.

Kiểm tra `agy models` ngày 15/10/2026 chỉ trả về Gemini 3.8 Flash (High/Medium/Low), không có Gemini 3.6 Flash (High); raw output lưu tại `evidence/m15-task-001a-a2/codex-review/agy-models-recheck-2026-10-15.log`. Skill `antigravity-task-runner` yêu cầu đúng Gemini 3.6 Flash (High), dừng nếu model không có và cấm fallback. Không gọi Antigravity implementer trong lượt này. Codex giữ nguyên recommendation `CHANGES_REQUIRED`, user verdict `PENDING`, Phase 08 `NOT_STARTED`; quyết định tiếp tục correction hay quay lại đánh giá Plan thuộc chủ dự án.
