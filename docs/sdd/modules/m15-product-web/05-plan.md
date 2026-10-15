# M15 — Plan & Task Readiness

**Version:** v0.2 · **STATUS:** Phase 05 user verdict `APPROVED` ngày 15/10/2026 chỉ cho `M15-TASK-001A`; task khác vẫn `BLOCKED`.
**Inputs:** Requirement v0.2, Research v0.3, Specification v0.3, Test Plan v0.2 và `docs/plan/week-05.md` W5-N01–N04. Phase 01/03/04 có user verdict `APPROVED`; Phase 03 Codex finding P03-01–05 vẫn cần xử lý theo phạm vi task.

## Implementation slices và dependency

| Thứ tự | Task / W5 | Kết quả và vùng sở hữu | Gate trước khi giao |
| --- | --- | --- | --- |
| 1 | `M15-TASK-001A` / W5-N01.1 | Semantic shell và CSS token/state cho page hiện có; không đổi route, auth, payload hoặc asset packaging | Có thể giao riêng sau Phase 05 approval cho 001A; base/fingerprint và source lock phải đúng |
| 2 | `M15-TASK-001B`, `002` / W5-N01 | Local font/assets/package, public/auth, account/consent/record/progress/report | M11/M09 và M01/M06/M08/M13 contract theo page; route/asset ownership với Thắng |
| 3 | `M15-TASK-003` / W5-N02 | Practice/lesson/review/progress/achievement/pronunciation | M10/M13 payload, enum và metric disclosure đã duyệt; W5-T01 persistence |
| 4 | `M15-TASK-004` / W5-N03 | Teacher review/blind/authoring/insights | M07/M10/M12/M13 contract, blind allowlist và dual-role gate đã duyệt |
| 5 | `M15-TASK-005`, `006` / W5-N04 | Admin/account/data/rating/study/billing, full cross-role browser QA | M11–M14/M16 approved handoff, temp-password/receipt policy, các page N01–N03 đã review |
| 6 | `M15-TASK-007` / W5-T04 của Thắng | Final package/clean-wheel/integrated browser gate | Thắng sở hữu; không giao trong prompt của Nguyên |

`M15-TASK-001A` chỉ là phần đầu của W5-N01.1, không chứng minh W5-N01 hoặc M15 hoàn thành. Các slice còn lại cần Phase 05 readiness bổ sung theo contract/revision mới; không dùng approval hẹp này làm quyền implement toàn M15.

## Task 001A — ranh giới sẵn sàng xem xét

**Mục tiêu quan sát được:** các page HTML hiện có dùng semantic skip link/main landmark, token CSS cho surface/text/action/focus, trạng thái input/button/nav, light/dark và reduced-motion/print cơ bản; không che nội dung ở 390×844 và 1280×800. Giữ route và business behavior nguyên trạng. Chỉ dùng CSS/HTML local, không cần API producer mới.

**Vùng file đề xuất:** `src/aicefr/api/templates.py` (shared `_document`, `LOCAL_CSS` và markup component hiện có); `tests/local/test_templates_mobile.py` và test mới cùng `tests/local/` cho shell/state; một QA script riêng dưới `scripts/qa/` nếu cần browser assertions. Không sửa `src/aicefr/api/wsgi.py`, `src/aicefr/portal/templates.py`, `pyproject.toml`, route registry, backend nghiệp vụ hoặc module SDD khác trong 001A. Nếu không thể đạt mục tiêu mà phải chạm file ngoài vùng, Antigravity trả `BLOCKED` và nêu impact; Codex/owner duyệt lại scope.

**Source lock:** `api/templates.py` là file chung của student/teacher/account. Nguyên là owner task; trước khi giao/triển khai cần báo Thắng (auth/runtime) và Sang (wording/evidence) vùng file, bảo đảm không có phiên AI khác sửa đồng thời. Prompt sẽ ghi base SHA/fingerprint và yêu cầu dừng nếu không khớp.

**In scope:** token CSS có tên semantic; markup shell accessible cho page hiện có; style focus/disabled/error/loading khi state hiện hữu; keyboard/contrast/responsive/reduced-motion/print assertions; test cho escaped title/text và không regress route hiện hành. **Out of scope:** Roboto/icon/art packaging, route mới, đổi IA/role nav, API integration, password slip, blind payload, billing, full student/teacher/admin journey. Các phần này thuộc 001B/002–006.

**Trace:** FR-001/008 và AC-001/004 phần shell ↔ M15-TEST-001/008/009; FR-003/005 và AC-005/006 forbidden-claim regression ↔ M15-TEST-012. AC-007/008 chỉ kiểm ở later slice/final gate. Không ghi parent AC `PASS` từ Task 001A đơn lẻ.

**Required checks cho 001A:** targeted `python -m pytest -q tests/local/test_templates_mobile.py` cùng test shell mới; `ruff format --check` và `ruff check` trên changed Python/test files; non-smoke suite để phát hiện regression shared renderer; `pytest-cov` line/branch trên final task revision, báo critical uncovered branch; browser fixture hoặc local loopback assertions ở hai viewport cho skip/focus/overflow/light-dark/reduced-motion/print. Script browser QA mới phải ghi result JSON, console/network summary, screenshot/hash, revision. Nếu Playwright/fixture không chạy được, ghi `VERIFICATION_FAILED`/`NOT_RUN`, không đánh `PASS`.

**Rollback/recovery:** một task một commit/diff có Task ID; không commit dữ liệu thật/asset ngoài quyền. Nếu shell làm hỏng trang cũ hoặc test fail, Antigravity sửa trong task hoặc trả report `VERIFICATION_FAILED`; không tự mở rộng route/backend. Codex review actual diff/evidence Phase 07, yêu cầu fix trong cycle; Phase 08 chạy lại trên final fingerprint.

## Contract gate cho các task còn lại

Trước prompt 001B/002–006, owner liên quan cung cấp version/revision + verdict, schema/example, error/enum/role, authorization và contract test. Đặc biệt: route canonical/alias theo method; M11 one-time temp-password/purge/no-log policy; M12 blind allowlist/dual-role/draft; M13 disclosure/source/n; M14 persisted order vs return/verify/receipt; M16 asset/wheel/runtime. Nếu khác Specification/Test Plan đã duyệt, re-review phase bị ảnh hưởng trước Phase 05 mới. UI component fixture không chứng minh integration.
