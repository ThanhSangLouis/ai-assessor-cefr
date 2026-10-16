# M15 — Research: UI, Route, State và Accessibility/Responsive

- **SCOPE ID / TYPE:** M15 / module
- **SCOPE ROOT:** `docs/sdd/modules/m15-product-web/`
- **PHASE RECORD ID:** `M15-02-W5-N01-R1`
- **TASK:** W5-N01
- **VERSION / STATUS:** v0.2 / REVIEWED WITH PHASE 03 — APPROVED, 2026-10-16
- **BASE REVISION:** `d60e8a4b9f63a0b0259ada8971e23bafdb1df041` (`main`)
- **RESEARCH DATE:** 2026-10-16
- **RESEARCH MODE:** `RUN`, do chủ dự án chọn 2026-10-16
- **ACCESSIBILITY TARGET:** tiêu chí hành vi, không claim mức conformance, do chủ dự án chọn 2026-10-16.

## 1. Mục tiêu và giới hạn

Đối chiếu hành trình W5-N01 với page/route/state đang có trong revision hiện hành; ghi nhận ranh giới kỹ thuật, dependency và hướng thiết kế để chuẩn bị Specification. Nguồn repo được đọc ở chế độ chỉ đọc; tài liệu M15 được cập nhật sau khi kiểm tra.

Research này không tạo requirement mới, không xác nhận approval của module producer, không kết luận WCAG conformance, không chạy test/browser QA và không sửa product source. W3C được dùng làm tài liệu tham khảo hành vi, không phải tuyên bố đạt chuẩn.

## 2. Nguồn đã xem

| ID | Nguồn | Dùng để | Giới hạn |
| --- | --- | --- | --- |
| R-01 | [`01-requirement.md`](01-requirement.md) v0.2, Phase 01 APPROVED | Phạm vi N01, FR/AC và quyết định người dùng | Nguồn requirement quyết định phạm vi; không tự giải quyết contract producer. |
| R-02 | [`week-05.md`](../../../plan/week-05.md) §9.3, W5-N01.1–N01.7 | Work packages, vùng code, dependency và Done Gate | Kế hoạch tuần cho biết đầu việc; không thay verdict SDD/module owner. |
| R-03 | [`src/aicefr/api/wsgi.py`](../../../../src/aicefr/api/wsgi.py#L220) và [`identity.py`](../../../../src/aicefr/api/identity.py#L34) | Route và hành vi server đang có | Quan sát implementation ở base revision, không chứng minh mọi route đã được formal approve. |
| R-04 | [`src/aicefr/portal/router.py`](../../../../src/aicefr/portal/router.py#L176) và [`portal/templates.py`](../../../../src/aicefr/portal/templates.py#L16) | Student history/progress navigation và renderer hiện hành | Chỉ phản ánh route được đăng ký trong source hiện tại. |
| R-05 | [`src/aicefr/api/templates.py`](../../../../src/aicefr/api/templates.py#L17), [`pyproject.toml`](../../../../pyproject.toml#L35) | Style/accessibility markup và packaged static assets | Đọc source; không chạy template hoặc browser. |
| R-06 | [`M11 Status`](../m11-identity-account/07-status.md), [`SCRUM-66 UI handoff`](../m11-identity-account/evidence/scrum-66/ui-handoff.md) | Account/session/consent/Google API observations | M11 module Requirement/Research còn DRAFT/PENDING; handoff là technical evidence, chưa là module approval. |
| R-07 | [`M01 Status`](../m01-intake-student/07-status.md), [`M01 W4 evidence`](../m01-intake-student/evidence/M01-W4-20261012.md), [`M02 Status`](../m02-audio-qc/07-status.md) | Student submit/status, QC boundary và trạng thái duyệt hiện có | M01 SDD còn PENDING; M02 shared contract còn owner review. |
| R-08 | [`M06 Status`](../m06-diagnostic-report/07-status.md), [`M09 Status`](../m09-trust-layer/07-status.md), [`M13 Status`](../m13-learning-evidence/07-status.md) | Report, trust và learning evidence dependencies | Các module tương ứng đang DRAFT/PENDING; không dùng làm API contract đã freeze. |
| R-09 | [`M16 G0`](../m16-monolith-runtime/evidence/w5-g0-2026-10-15/W5-G0.md) | Runtime/package/browser baseline context | Evidence dùng target `3b2d2b7`, khác base M15 hiện hành `d60e8a4`; không dùng như kiểm chứng N01 trên revision này. |
| R-10 | [`docs/sources/README.md`](../../../sources/README.md) | Provenance và quy tắc dùng tài liệu nguồn | Không phải design specification cho M15. |
| R-11 | [Understanding Focus Visible — W3C WAI](https://www.w3.org/WAI/WCAG22/Understanding/focus-visible.html), [Labels or Instructions — W3C WAI](https://www.w3.org/WAI/WCAG22/Understanding/labels-or-instructions), [Use of Color — W3C WAI](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html) | Hành vi focus, form label và thông tin không phụ thuộc màu | Tài liệu hướng dẫn không được dùng để claim conformance. Truy cập 2026-10-16. |
| R-12 | [Reflow — W3C WAI](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html) | Tham khảo ảnh hưởng của phóng to/thu hẹp viewport | Tài liệu nêu benchmark 320 CSS px của criterion; requirement hiện được duyệt dùng viewport tối thiểu 360 CSS px và không claim chuẩn. Không tự đổi AC. Truy cập 2026-10-16. |
| R-13 | [Media Queries Level 5 — W3C](https://www.w3.org/TR/mediaqueries-5/#prefers-reduced-motion), [Technique C39 — W3C WAI](https://www.w3.org/WAI/WCAG22/Techniques/css/C39) | Ý nghĩa user preference `prefers-reduced-motion` và cách cung cấp trạng thái ít chuyển động | Media Queries Level 5 là Working Draft; technique là ví dụ, không phải điều kiện approval của dự án. Truy cập 2026-10-16. |

### Nguồn không tìm thấy hoặc không được dùng làm bằng chứng

M15 draft Research v0.1 trên base này trỏ tới `docs/web/SPEC_WEB.md`; đường dẫn đó không tồn tại trong worktree sạch (`Test-Path` trả `False`). Vì vậy các `M15-REF-01–06` cũ chưa được tái xác minh và không được dùng để kết luận về thiết kế hoặc route hiện hành. Không có design file/screenshot tham chiếu do người dùng cung cấp trong scope này. Research v0.2 thay bộ tham chiếu không kiểm tra được bằng inventory code/docs của revision sạch và hướng dẫn W3C chính thức.

## 3. Quan sát implementation hiện hành — FACT

### 3.1 Route/page inventory

| Journey/page | Route quan sát được tại base | Hành vi/state hiện có | Khoảng trống so với W5-N01 |
| --- | --- | --- | --- |
| Root/login | `GET /` redirect `303` tới `/login`; `/login` GET/POST | Form đăng nhập, rate limit và lỗi đăng nhập | Chưa có landing page công khai hoặc link giải thích band. |
| Public assets | `GET /local.css`, `/recorder.js`, `/report.js` | Phục vụ local CSS/JS | Chưa có full asset system Roboto/icon/art theo package requirement. |
| Consent | `GET /student/consent`; POST `/student/consent/accept` và `/withdraw` | Active/version, optional research consent, withdraw và session check | Cần map thêm trạng thái consent từ M11 contract; không tự đặt consent state ở client. |
| Upload/record | `GET /student/upload`; POST `/student/responses`; API POST `/api/student/responses` | Chọn task/audio; recorder chỉ bật khi config/format/runtime cho phép; upload browser redirect hoặc JSON status | Chưa có 30-second preparation state; không có guarantee UI-only về duplicate-safe retry. |
| Status/report | `/student/responses/{id}`; `/student/responses/{id}/report`; API GET `/api/student/responses/{id}/status|report` | Owner-scoped server service; queued/running/completed/review/rejected/failed; report chưa sẵn sàng giữ `202`/not-ready state, không bịa score | Cần nêu retry/recovery, audio seek và trust/student evidence theo contract đã duyệt. |
| History/progress | `/student/responses`, `/student/progress`, `/student/tasks` | Student list, pagination, aggregate summary và task list | Renderer hiện còn đơn giản; không phải UX specification hoàn chỉnh cho history/progress. |
| Account API | `/api/v1/me`, `/profile`, `/password`, `/sessions`, `/activity`, `/consent`, `/google` | Identity routes có server-side session/role gate | Không thấy student HTML account page hoặc bốn tab; formal M11 contract/Phase 01 còn pending. |
| Bands/reliable change/pronunciation/study | Chưa thấy route/page tương ứng trong current source | M13/M09 artifact DRAFT/PENDING | Chỉ render block khi producer contract và evidence state được duyệt; thiếu dữ liệu giữ null/insufficient, không render số 0. |

Nguồn route: `src/aicefr/api/wsgi.py:220–368`, `src/aicefr/api/identity.py:34–82`, `src/aicefr/portal/router.py:176–238`.

### 3.2 Navigation, style và asset/package

- Student nav hiện là một `<nav>` ngang có wrap, chứa Nộp bài/Đề bài/Bài đã nộp/Tiến độ/Đồng ý dữ liệu. Template hiện chưa tạo desktop sidebar, compact tablet rail hoặc mobile bottom navigation (`src/aicefr/portal/templates.py:16–45`).
- Global CSS hiện đặt `color-scheme: light`, `system-ui`, một main max-width, control min-height và `:focus-visible` outline 3px. Trong file CSS hiện xem không có media query, dark theme hoặc `prefers-reduced-motion` (`src/aicefr/api/templates.py:17–37`). Đây là quan sát source, chưa phải accessibility assessment.
- Form hiện có label, `role=alert` cho lỗi và `role=status` cho recorder notice. Consent checkbox có visible text; report có các nút seek theo evidence refs. Chưa kiểm tra với screen reader/browser.
- `pyproject.toml:35–36` package-data hiện gồm `api/static/*.js` và migration SQL. CSS còn là hằng số Python; font, icons và art local chưa có trong package-data hiện tại.
- `docs/sources/README.md` xác định dự án là sản phẩm nhóm phát triển theo SDD và quy tắc provenance. Không chuyển source/code ngoài vào dự án để lấp chỗ trống UI design.

## 4. Cross-module constraints — FACT và OPEN

| Owner/module | Input liên quan N01 | Trạng thái được kiểm tra | Kết luận dùng cho Specification |
| --- | --- | --- | --- |
| M11 — identity/account | Session, consent, account, password, activity, Google | Module `07-status.md` Phase 01 DRAFT/PENDING; SCRUM-66 có technical UI handoff | Dùng route/payload trong handoff làm observed technical input, không tuyên bố module contract đã được approve. Phase 05 cần owner review/freeze version. |
| M01 — student intake | Task list, submit, status, owner boundary | Có source/evidence thực tế; module Phase 01/03/04/05 còn PENDING | Nối hành trình với endpoint/state đã quan sát; idempotency/retry behavior phải có contract owner trước khi pass AC duplicate-submit. |
| M02 — audio/QC | Allowed media, reject/review reasons, limits | Phase 01/03/04 approved; Plan/Tasks có Sang review PENDING | Hiển thị reason safe theo producer; không tự quy đổi reason hoặc threshold. |
| M06 — report | Overall estimate, evidence refs, audio seek/history | `07-status.md` DRAFT/PENDING | AC về overall/evidence đã có trong M15 Requirement; cần consumer contract cụ thể trước Phase 05. |
| M09 — trust | Refusal/uncertainty reason và provenance | Requirement v0.1 DRAFT/PENDING | Không invent trust badge/text/state. |
| M13 — learning evidence | Reliable change, pronunciation, student study | Requirement v0.1 DRAFT/PENDING | Chỉ thiết kế empty/insufficient/available component contract; không tự tạo metric, threshold hay sample. |
| M16 — runtime/package | Local font/art/template assets, clean wheel/browser | Module approval pending; G0 evidence có base khác | Phải ghi owner review/packaging dependency. G0 screenshots không thay browser QA final N01. |

## 5. Accessibility và responsive — nguồn tham khảo và giới hạn

Các tài liệu W3C WAI được dùng làm behavioral guidance: trạng thái focus cần nhìn thấy khi keyboard operation; input có label/instruction; màu không phải phương tiện duy nhất để truyền trạng thái; user preference `prefers-reduced-motion` có thể giảm/chuyển non-essential motion. Đây không phải checklist conformance cho W5-N01.

W3C Reflow mô tả một benchmark 320 CSS px cho criterion 1.4.10. Requirement v0.2 đã được owner duyệt ở 360/390/768/1280 CSS px, zoom 200%, print và reduced motion, theo tiêu chí hành vi. Giữ nguyên AC đó; không claim rằng các viewport này chứng minh WCAG Reflow.

Source hiện có visible focus style và semantic labels nhưng CSS chỉ hỗ trợ light theme và không có responsive breakpoints/reduced-motion rule. Đây là gap implementation cần giải quyết trong Phase 06 sau Phase 05; source review không thay browser/screen-reader QA.

## 6. Inference, options và recommendation

### Inference

1. Có thể dùng các route student history/progress hiện hành, nhưng public landing/bands và account UI cần bổ sung page/view; request scope không đòi thay backend domain logic.
2. Tích hợp N01 phụ thuộc nhiều owner: M11 cho account/consent, M01/M02 cho upload/status/recovery, M06 cho report/audio, M09/M13 cho evidence disclosure và M16 cho package assets.
3. UI-only disable/lock không đủ để cam kết retry không tạo duplicate nếu submit API không có idempotency contract. N01 không tự sở hữu mutation backend; cần producer xác nhận server behavior trước Phase 05.

### Options

| Option | Lợi ích | Chi phí/rủi ro | Trạng thái |
| --- | --- | --- | --- |
| A. Native server-rendered HTML + CSS + JS nhỏ, package qua setuptools hiện có | Phù hợp WSGI/router/templates hiện hữu, asset local/offline, không phát sinh build runtime mới | Shared template/static files cần file ownership; UI state phải giữ rõ boundary giữa browser và service | Codex đề xuất để user duyệt trong Phase 03. |
| B. Thêm frontend framework/build pipeline | Có component tooling và client-side routing sẵn | Thêm dependency/build/package/runtime scope, không có nguồn hoặc quyết định trong Requirement hiện duyệt | Không đề xuất trong W5-N01 hiện tại. |

## 7. Recommendation cho Specification

1. Giữ server là nguồn role/owner/consent/score/report status; view layer chỉ trình bày DTO và state contract.
2. Bảo toàn `/login`, consent, upload/status/report/history/progress routes quan sát được; đề xuất `/` landing, `/bands` public explanation và `/student/account` bốn tab để owner review trong Phase 03.
3. Ghi rõ page state: loading, empty, disabled/not-configured, error, retry, queued/running, report unavailable, completed/review-required/rejected/failed. Không chuyển thiếu dữ liệu thành 0.
4. Dùng design tokens có nghĩa, shared components, Roboto/icon/art local, light/dark, responsive navigation theo requirement; mọi art/motion decorative.
5. Giữ cross-module route/payload tables là `PROVISIONAL` tới khi producer owner review. Nếu route, error, idempotency hoặc evidence state chưa freeze, Phase 05 readiness là `BLOCKED`.
6. Lưu browser evidence trên final integrated revision ở Phase 06; M16 G0 historical screenshots không được tính là evidence N01.

## 8. Research self-check

| Kiểm tra | Kết quả | Evidence |
| --- | --- | --- |
| Scope/decision source | PASS | Requirement v0.2 owner-approved; research mode/accessibility decision recorded. |
| Source provenance | PASS | Source table distinguishes current repo implementation, DRAFT contracts and official W3C guidance; missing prior UI doc is explicitly called out. |
| Fact vs inference vs option | PASS | Sections 3–7 label observations, cross-module status, inference and options separately. |
| No new requirement or conformance claim | PASS | Acceptance scope is not changed; WCAG pages are behavior guidance only. |
| Current-code test/browser validation | NOT_RUN | Phase 02 read-only; no test or browser run. |

**Phase 02 outcome:** Research v0.2 was reviewed with M15 Specification v0.2. The project owner approved Phase 03 on 2026-10-16; the approved implementation boundary and route proposals are recorded in `03-specification.md`. Research observations remain evidence from the stated base revision, not producer-contract approval.
