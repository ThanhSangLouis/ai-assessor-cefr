# M15 — Tasks

**Version:** v0.2 · **STATUS:** Phase 05 user verdict `APPROVED` cho `M15-TASK-001A`; project owner confirmed separate `APPROVED` verdicts for SCRUM-74/75/76 (`M15-TASK-003`–`006`) on 16/10/2026. See each task's boundary/evidence addendum; producer-module approval and acceptance remain separately owned.
**Owner triển khai UI:** Hoàng Nguyên; Codex lead/review; Antigravity implementer sau prompt hợp lệ. Mỗi task chỉ có một owner, một vùng file và dependency riêng. Các mã `W5-N01.1`… trong `docs/plan/week-05.md` vẫn là work package bắt buộc của task tuần.

| Task | W5 | Deliverable / trace | Readiness |
| --- | --- | --- | --- |
| `M15-TASK-001A` | W5-N01.1 một phần | semantic shell/tokens/states cho page hiện có; FR-001/008, AC-001/004 phần shell; TEST-001/008/009/012 | `IN_PROGRESS` — chuẩn bị prompt, chưa có implementation report |
| `M15-TASK-001B` | W5-N01.1–N01.3 | assets/font/package, nav, landing/login/bands/consent/account; TEST-001/002/008–012 | `BLOCKED` — route/asset owner và M11 contract |
| `M15-TASK-002` | W5-N01.4–N01.7 | record/upload/preparation/progress/report/history; TEST-002–004/008/012 | `BLOCKED` — M01/M06/M09/M13 contract |
| `M15-TASK-003` | W5-N02.1–N02.6 | practice/lesson/review/result/progress; TEST-005/008/012 | `IN_PROGRESS` — user Phase 05 verdict `APPROVED`; transferring/adapting UI only; preserve producer APIs; acceptance `NOT_RUN`; see [task-specific verdict](reviews/phase-05-implementation-authorization-scrum-74-2026-10-16.md) |
| `M15-TASK-004` | W5-N03.1–N03.6 | review/stats/blind/teach/insights; TEST-006/008/012 | `IN_PROGRESS` — current M07/M12 and M10 APIs integrated; no path-list/cohort-insights API; E2E `NOT_RUN` |
| `M15-TASK-005` | W5-N04.1–N04.5 | admin account/data/rating/study/billing; TEST-007/008/012 | `IN_PROGRESS` — current admin/rating/study/read-only billing UI adapted; unsupported policy mutations remain gated |
| `M15-TASK-006` | W5-N04.6–N04.7 | full cross-role browser/a11y/motion/evidence; TEST-001–012 | `IN_PROGRESS` — final integrated browser/E2E remains `NOT_RUN` pending all task branches |
| `M15-TASK-007` | W5-T04 | final package/clean-wheel/integrated browser gate; TEST-010/011 + full | `BLOCKED`; owner Thắng, không nằm trong prompt Nguyên |

## `M15-TASK-001A` — Phase 05 readiness candidate

- **Objective:** semantic shell/tokens/state styling cho các page hiện hữu, không đổi URL, auth, payload hoặc business copy. Kết quả xem được trên local HTML tại 1280×800 và 390×844; skip link/main landmark/focus/contrast/light-dark/reduced motion/print có assertion.
- **One owner:** Hoàng Nguyên. **Implementer:** Antigravity sau Phase 05 user verdict. **Review:** Codex actual diff/tests; Thắng kiểm impact auth/runtime, Sang kiểm claim/wording nếu có thay đổi text. Trước khi sửa shared renderer, thông báo owner liên quan và xác nhận source lock.
- **Allowed files:** `src/aicefr/api/templates.py`, `tests/local/test_templates_mobile.py`, test mới dưới `tests/local/` và một script QA M15 riêng dưới `scripts/qa/` nếu cần. Không sửa `src/aicefr/api/wsgi.py`, `src/aicefr/portal/templates.py`, `pyproject.toml`, API/service/storage/SDD khác; nếu cần thì báo `BLOCKED` với diff đề xuất.
- **Input:** Specification v0.3 §§Design tokens/components, Layout/navigation, Assets/motion; Test Plan v0.2 M15-TEST-001/008/009/012; hiện trạng `_document`/`LOCAL_CSS` ở `api/templates.py`. Không phụ thuộc producer contract mới vì không đổi route/role/nav.
- **Expected output:** diff nhỏ có Task ID; targeted/related pytest + lint/format + non-smoke regression; coverage line/branch và critical uncovered branches; browser result JSON ở desktop/mobile với focus/overflow/theme/reduced-motion/print, screenshot SHA-256, console/network/external summary; raw report đúng prompt. Checks chưa chạy phải là `NOT_RUN`/`VERIFICATION_FAILED`, không suy từ code.
- **Done boundary:** chỉ `M15-TASK-001A` có thể qua review/verification. Parent W5-N01.1/W5-N01/M15 chưa `DONE`: Roboto/assets/nav/API/journey và full browser matrix còn trong 001B/002–006. Không dùng prompt 001A để sửa các task khác.
