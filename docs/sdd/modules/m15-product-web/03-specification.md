# M15 — Specification

**Version:** v0.3 · **STATUS:** DRAFT, Phase 03 user verdict `PENDING`.
**Inputs:** Requirement v0.2 `APPROVED`; Research v0.3 `RUN`; `docs/plan/week-05.md` §6/9.3; backend handoff M11 SCRUM-66 và M14 SCRUM-67 tại target `d60e8a4`. M10/M12/M13/M16 và global M11/M14 contract vẫn chưa có approval module; phần consumer dưới đây chưa được freeze.

## Mục tiêu và ranh giới

M15 đặc tả tầng trình bày cho khách, sinh viên, giảng viên và quản trị viên. Page parse/trình bày view-model từ service/API theo quyền server; không tự tính điểm, cấp quyền, tạo rule học tập, suy ra số liệu nghiên cứu hoặc settle payment trong JavaScript. Nguyên sở hữu page/template/static/browser QA; thay đổi contract nghiệp vụ quay về owner module.

## Design tokens/components

Tokens: màu semantic theo role/light-dark, typography scale, spacing, radius, border, elevation, motion duration/easing, breakpoint và z-index. Roboto tiếng Việt được phục vụ local kèm license; icon/art là asset local. Components: button/icon button, field/select, tabs, badge/status, card/table, dialog/toast, skeleton/empty/error, pagination/disclosure/audio/recorder. Mỗi component hỗ trợ disabled/loading/error/focus-visible và accessible name; không dùng màu/motion làm kênh thông tin duy nhất.

## Layout/navigation

- ≥1024: persistent left sidebar; 600–1023 compact rail/drawer; 360–599 top bar + bottom nav.
- Main landmark, skip link, one H1, logical heading, visible focus; icon-only needs accessible name.
- Server supplies role/navigation model; client does not invent entitlement/role. Một mục current trong mỗi context; badge/count chỉ xuất hiện khi server cho phép. Mobile 390 px cần chốt slot/thứ tự bottom nav và vị trí Account; keyboard order và `aria-current` phải khớp URL thật.
- Theme và reduced motion giữ thông tin. Dialog đưa focus vào vùng tương tác rồi trả lại trigger khi đóng. Table nhiều cột chuyển card/scroll có nhãn ở mobile, không che primary action.

## Page contracts

URL dưới đây là sản phẩm W5 đề xuất, không tự thay route hiện hành. M15 cùng owner chốt canonical/alias/redirect, method, quyền/consent và back/refresh trước Phase 05. Mỗi page contract/task phải ghi API/view-model, primary action, initial/loading/empty/success/error/conflict/forbidden state, recovery, keyboard order, mobile transformation và forbidden claims.

| Journey | Route hiện hành sau pull | Route W5 đề xuất | Owner route/contract |
| --- | --- | --- | --- |
| Landing | `/` chuyển `/login` | `/` landing | M15/M11 |
| Consent/account | `/student/consent`; `/password-change` đã có, `/account` chưa có | `/consent`, `/account` | M08/M11/M15 |
| Status/report | `/student/responses/{id}`, `/student/responses/{id}/report` | `/progress/{id}`, `/report/{id}` | M01/M06/M15 |
| Teacher review | `/teacher/reviews`, `/teacher/reviews/{id}` | `/review`, `/review/{id}` | M07/M15 |
| Learning/blind | chưa có route UI tương ứng | `/practice/*`, `/rate/*`, `/teach/*` | M10/M12/M15 |
| Admin/billing | `/admin/*`, API `/api/v1/admin/billing/*`; chưa có product billing result/receipt page | `/admin` tab có URL state, result/receipt | M11–M14/M16/M15 |

Nguồn tham chiếu dùng `/admin#billing`, còn target có subroute `/admin/accounts`, `/admin/models`, `/admin/config`, `/admin/erase`. Fragment không thay server authorization. User đã chọn hướng giữ link hiện hành có kiểm quyền trong migration; owner route vẫn cần duyệt bảng GET/POST/API cụ thể và ảnh hưởng link cũ.

| Route/page | View-model owner và hành động chính | State/recovery bắt buộc |
| --- | --- | --- |
| `/`, `/login`, `/bands` | M15/M11/M05/M09; giới thiệu, login, giải thích overall/coverage | Public copy không claim chứng chỉ/độ chính xác chưa đo; invalid/lockout/Google disabled/429/503 có recovery |
| `/consent`, `/account` | M08/M11; consent, bốn tab profile/security/activity/data | Version/required/optional, invalid/conflict, revoke session/Google disabled; temporary-password gate dẫn `/password-change` theo handoff M11 |
| `/student/upload` | M01/M02; chọn task, record/file → nghe lại → ghi lại/đổi file hoặc submit | Preparation 30 giây có skip/countdown/focus/live announcement; lỗi thiết bị/transcode/upload có file fallback; không submit trước preview |
| `/progress/{id}` | M01; response status | `QUEUED/RUNNING` poll có backoff; `REVIEW_REQUIRED` nêu chờ duyệt; `FAILED` giải thích retry hợp lệ; chỉ `COMPLETED` có report mới chuyển/link |
| `/report/{id}`, `/my-responses` | M06/M09/M01; overall/evidence/audio, history/delete | Null/old version/refusal/evidence thiếu không thành 0; seek chỉ khi audio khả dụng, play lỗi có chữ; foreign response không tiết lộ, delete confirm |
| `/my-progress`, `/practice/*` | M10/M13; trend/roadmap/lesson/review/result | Insufficient n/source/config, lesson measured/unmeasured, review due/empty/retry; practice result không band, next/previous an toàn |
| `/review`, `/review/{id}`, `/review/stats` | M07/M13; queue/claim/detail/decision/KPI | TTL contention/expiry, stale revision giữ input, reload/resolve/release/close; AI vs teacher-final tách; sample insufficient không thành 0 |
| `/rate`, `/rate/{id}` | M12; blind list/sheet/local draft/one-time submit | Opaque assignment, expired/conflict/confirm/focus, unrateable; draft key/lifetime/purge theo M12, timeout retry không double-submit; forbidden fields không vào DOM/network |
| `/teach/*` | M10/M13; path/lesson builder/lint/preview/publish/insight override | Dirty/saving/saved/error, preview/publish sau save thành công, 409/422 giữ input; audit confirm, role/entitlement server-side |
| `/admin` và tab có URL state | M11–M14/M16; account/task/model/config/audit/data/rating/study/billing | Mutation confirm/loading/success/error/conflict; export/erase preview; temp-password one-time policy M11; secret/path không lộ |
| Payment result/receipt | M14; order/result/receipt | Tách order `PENDING/PAID/FAILED/CANCELLED/EXPIRED` với return/verify transient; sandbox label; receipt chỉ PAID/đúng quyền; refresh không settle lặp |

M15 dùng error envelope an toàn theo W5 §7: `error.code`, `message`, `request_id`, `details` đã redact. `401` login, `403` thiếu quyền/consent hoặc `PASSWORD_CHANGE_REQUIRED`, `404` không xác nhận foreign resource, `409` giữ input/draft và reload/resolve, `422` chỉ field/rule an toàn, `429` chờ theo server, `503` giải thích dependency chưa sẵn. Mọi mutation khóa duplicate submit, không tự retry request có side effect hoặc hiển thị raw exception.

## Nội dung, quyền và privacy

- Assessment chỉ hiện một overall estimate/band khi đủ evidence; năm tiêu chí chỉ coverage/evidence. `Interaction=null` cùng `insufficient_evidence` cho độc thoại. Teacher-final tách AI estimate và chỉ verified sau audit action.
- Practice/lesson không sinh hoặc hiển thị CEFR band cho lượt luyện theo M15-AC-005. Nguồn dùng A2/B1/B2 đặt tên cấp lộ trình; M10/M15 cần chốt cách nhãn cấp học không bị hiểu là band đánh giá. Trust/lạc đề/LID chỉ giải thích review/refusal theo M09. Research/pronunciation/teacher-time/reliable-change dùng status, n, source và disclosure do M13 cung cấp; thiếu dữ liệu hiển thị `insufficient`/`NOT_EVALUATED`.
- Blind view không render alias, internal response ID, report, machine score/band/reason/provenance hoặc other-rater value. M12 cung cấp allowlist và deny matrix cho queue, assignment, audio, report, history, admin agreement/export, kể cả admin kiêm rater. Local draft không chứa trường cấm và bị xóa khi assignment hết hiệu lực.
- Page GET nhạy cảm, direct URL và API đều qua server gate. Anonymous chỉ public/login/bands; student chỉ tài nguyên mình; teacher chỉ review/authoring/blind assignment của mình; admin theo quyền thực. Actor có hai role/admin kiêm rater cần M11/M12 quyết định explicit. `401/403/404` không xác nhận foreign resource; matrix method/route final do owner freeze, không suy từ menu.
- M11 backend SCRUM-66 trả temporary password một lần khi admin create/reset; W5 yêu cầu phiếu in, nhưng M11-AC-006 DRAFT cấm password API/DOM/export. User chọn hướng phát một lần cho admin và CSV account thường không mang password. M11 owner phải chốt ngoại lệ, purge/cache/download/no-log test trước khi M15 render phiếu.
- M14 backend SCRUM-67 chỉ sandbox/test W5. UI không hiển thị live payment khi chưa có quyền/cấu hình; không suy đoán đã trừ tiền từ browser return, không lộ provider payload/secret.

## Assets/motion

All local, hashed/packageable, CSP-compatible. Decorative SVG has `aria-hidden`, `pointer-events:none`, hidden in print and no horizontal overflow. `prefers-reduced-motion` disables page/art/progress animation, never removes information. Asset URL/CSP/cache, Roboto subset/license và wheel manifest phải chốt theo WSGI target; không request CDN. Source FastAPI/Jinja không được mang nguyên sang target.

## Browser evidence contract

Machine-readable result has revision, route, role, viewport, steps/assertions, console/network/external requests, screenshot path/hash and result. Screenshots supplement assertions, never replace them.

## Traceability và dependency

| FR | AC | Test draft | W5 task |
| --- | --- | --- | --- |
| M15-FR-001/008 | M15-AC-001/007 | M15-TEST-001/008/009/010 | W5-N01, W5-N04 |
| M15-FR-002 | M15-AC-002/004 | M15-TEST-002/008 | W5-N01–N04 |
| M15-FR-003 | M15-AC-005 | M15-TEST-012 | W5-N01 |
| M15-FR-004 | M15-AC-003/004/005 | M15-TEST-003/004/008 | W5-N01 |
| M15-FR-005 | M15-AC-004/005 | M15-TEST-005/008/012 | W5-N02 |
| M15-FR-006 | M15-AC-002/004/006 | M15-TEST-006/008/012 | W5-N03 |
| M15-FR-007 | M15-AC-002/004/005/006 | M15-TEST-007/008/012 | W5-N04 |
| M15-FR-009 | M15-AC-008 | M15-TEST-011 | W5-N04 |

**Open dependency:** backend M11 SCRUM-66 và M14 SCRUM-67 có code/handoff ở revision `d60e8a4`, nhưng reviewer/user verdict toàn module vẫn `PENDING`. M10/M12/M13 còn Phase 01 `PENDING`; M16 integration gate cũng chưa được chấp nhận. Route canonical/alias, normalized payload/error/reason enum, M12 forbidden-field matrix, M13 metric disclosure, M11 one-time password policy và M14 order/receipt view-model chưa freeze. User đã chọn các đề xuất Codex làm hướng xử lý M15-P03-01–05, sẽ cung cấp contract đã duyệt; nếu contract khác, cập nhật M15 và re-review Phase 03 đúng impact trước Phase 04/05/prompt. Research static và backend browser smoke không thay browser QA M15.
