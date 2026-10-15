# M15 — Tasks

**Version:** v0.2 · **STATUS:** Chủ dự án duyệt phạm vi W5-N01–N04 ngày 15/10/2026; Phase 05 user verdict `APPROVED` vẫn chỉ áp dụng cho `M15-TASK-001A` và amendment F06. Task phụ thuộc contract chưa sẵn sàng implement.
**Owner triển khai UI:** Nguyên; Codex lead/review; Antigravity implementer sau prompt hợp lệ. Mỗi task chỉ có một owner, một vùng file và dependency riêng. Các mã `W5-N01.1`… trong `docs/plan/week-05.md` vẫn là work package bắt buộc của task tuần.

| Task | W5 | Deliverable / trace | Readiness |
| --- | --- | --- | --- |
| `M15-TASK-001A` | W5-N01.1 một phần | semantic shell/tokens/states cho page hiện có; FR-001/008, AC-001/004 phần shell; TEST-001/008/009/012 | `CHANGES_REQUIRED` — Phase 07 A2R2 còn R01–R03 mở; correction bundle đã dùng, cùng vấn đề traceability R02 tái diễn nên cần chủ dự án quyết định hướng tiếp theo. Runner hiện không liệt kê Gemini 3.6 Flash (High); Phase 08 chưa bắt đầu; 001A chưa verified |
| `M15-TASK-001B` | W5-N01.1–N01.3 | assets/font/package, nav, landing/login/bands/consent/account; TEST-001/002/008–012 | `BLOCKED` — scope W5-N01 được duyệt; route/asset owner, M11/M09 contracts, M16 asset/runtime impact còn thiếu; M05 đã accepted, M08 review còn pending |
| `M15-TASK-002` | W5-N01.4–N01.7 | record/upload/preparation/progress/report/history; TEST-002–004/008/012 | `BLOCKED` — scope W5-N01 được duyệt; M01/M02/M06/M08/M09/M13 consumer contracts, M02 owner review và Phase 05 readiness còn thiếu; M05 semantics đã accepted |
| `M15-TASK-003` | W5-N02.1–N02.6 | practice/lesson/review/result/progress; TEST-005/008/012 | `BLOCKED` — scope W5-N02 được duyệt; M10/M13 payload, enum, disclosure và W5-T01 persistence chưa được freeze/duyệt |
| `M15-TASK-004` | W5-N03.1–N03.6 | review/stats/blind/teach/insights; TEST-006/008/012 | `BLOCKED` — scope W5-N03 được duyệt; M07/M10/M12/M13 contract, blind allowlist, dual-role gate và Phase 05 readiness còn thiếu |
| `M15-TASK-005` | W5-N04.1–N04.5 | admin account/data/rating/study/billing; TEST-007/008/012 | `BLOCKED` — scope W5-N04 được duyệt; M11–M14/M16 policy/consumer approval và Phase 05 readiness còn thiếu |
| `M15-TASK-006` | W5-N04.6–N04.7 | full cross-role browser/a11y/motion/evidence; TEST-001–012 | `BLOCKED` — scope W5-N04 được duyệt; 001A–005 phải qua review và cần integrated revision |
| `M15-TASK-007` | W5-T04 | final package/clean-wheel/integrated browser gate; TEST-010/011 + full | `BLOCKED`; owner Thắng, không nằm trong prompt Nguyên |

## `M15-TASK-001A` — Phase 05 readiness candidate

- **Objective:** semantic shell/tokens/state styling cho các page hiện hữu, không đổi URL, auth, payload hoặc business copy. Kết quả xem được trên local HTML tại 1280×800 và 390×844; skip link/main landmark/focus/contrast/light-dark/reduced motion/print có assertion.
- **One owner:** Nguyên. **Implementer:** Antigravity sau Phase 05 user verdict. **Review:** Codex actual diff/tests; Thắng kiểm impact auth/runtime, Sang kiểm claim/wording nếu có thay đổi text. Trước khi sửa shared renderer, thông báo owner liên quan và xác nhận source lock.
- **Allowed files:** `src/aicefr/api/templates.py`, `tests/local/test_templates_mobile.py`, test mới dưới `tests/local/` và một script QA M15 riêng dưới `scripts/qa/` nếu cần. Không sửa `src/aicefr/api/wsgi.py`, `src/aicefr/portal/templates.py`, `pyproject.toml`, API/service/storage/SDD khác; nếu cần thì báo `BLOCKED` với diff đề xuất.
- **Input:** Specification v0.3 §§Design tokens/components, Layout/navigation, Assets/motion; Test Plan v0.2 M15-TEST-001/008/009/012; hiện trạng `_document`/`LOCAL_CSS` ở `api/templates.py`. Không phụ thuộc producer contract mới vì không đổi route/role/nav.
- **Expected output:** diff nhỏ có Task ID; targeted/related pytest + lint/format + non-smoke regression; coverage line/branch và critical uncovered branches; browser result JSON ở desktop/mobile với focus/overflow/theme/reduced-motion/print, screenshot SHA-256, console/network/external summary; raw report đúng prompt. Checks chưa chạy phải là `NOT_RUN`/`VERIFICATION_FAILED`, không suy từ code.
- **Done boundary:** chỉ `M15-TASK-001A` có thể qua review/verification. Parent W5-N01.1/W5-N01/M15 chưa `DONE`: Roboto/assets/nav/API/journey và full browser matrix còn trong 001B/002–006. Không dùng prompt 001A để sửa các task khác.
