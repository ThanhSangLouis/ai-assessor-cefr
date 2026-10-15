# SCRUM-73 / W5-N01 — Kết quả nghiên cứu đọc-only của Codex

**Ngày:** 15/10/2026  
**Record type:** Đối chiếu hiện trạng phục vụ Phase 05; không phải Phase 05 verdict, không phải quyền implement.  
**Baseline:** HEAD `6baf720f173b440eb961676b09ea290058a39b35` cùng working-tree diff A2R1. Route/API được đọc từ mã nguồn hiện hành; diff `identity.py` chỉ đổi markup `_password_page` theo amendment F06.  
**Phạm vi:** `M15-TASK-001B`, `M15-TASK-002`, và trạng thái `M15-TASK-001A`. Không sửa source, không chạy test/browser QA, không phát prompt.

## Kết luận readiness

| Task | Readiness | Căn cứ |
| --- | --- | --- |
| `M15-TASK-001B` | `BLOCKED` | Route/method/role/consent contract chưa chốt đến từng page; M11/M09 contract và M16 asset/package boundary chưa được owner duyệt; thiếu font/art asset source, license, allowed-file list và owner locks. |
| `M15-TASK-002` | `BLOCKED` | M01/M02/M06/M08/M09/M13 consumer contracts chưa đủ revision/verdict; M02 cross-owner review còn pending; chưa có page-to-view-model/API map cuối và evidence matrix cho states. |
| `M15-TASK-001A` | `CHANGES_REQUIRED` | A2R1 còn review findings R01–R04. A2R2 đã chuẩn bị, nhưng chưa được gửi/chạy do model runner hiện không cung cấp Gemini 3.6 Flash (High) theo log hiện có. |

Scope W5-N01 được chủ dự án duyệt ngày 15/10/2026; điều đó không thay Phase 05 approval riêng của 001B/002. M15 `05-plan.md`, `06-tasks.md`, `07-status.md` và precheck hiện hành giữ nguyên ranh giới này.

## Route–method–role–consent matrix hiện tại

| Route/page hiện hành | Method / xử lý hiện tại | Actor / consent | Khoảng trống so với W5 |
| --- | --- | --- | --- |
| `/` | `GET` trả redirect `303` tới `/login` (`api/wsgi.py:220–223`). | Anonymous có thể vào login. | W5 đề xuất landing công khai tại `/`; chưa có canonical landing route. |
| `/login` | `GET` render login; `POST` gọi login (`api/wsgi.py:224–228`). | Public entry; role được xác lập sau đăng nhập. | Contract Google/disabled/lockout/recovery cần đối chiếu M11; trang hiện có không chứng minh account/band journey hoàn chỉnh. |
| `/bands` | Không có handler; fallback route là `404` (`api/wsgi.py:370`). | W5 dự kiến anonymous. | Chưa có page hoặc claim contract từ M05/M09. |
| `/student/consent` | `GET`; `/student/consent/accept` và `/student/consent/withdraw` là `POST` (`api/wsgi.py:260–316`). | `GET/POST` resolve Student; `POST` yêu cầu session và origin, nhận `research_allowed`; consent state/version được lưu. | W5 `/consent` chưa có route canonical/alias/method record. M08/M11 cần chốt version, required/optional purpose và hành vi sau withdrawal. |
| `/password-change` | `GET/POST` trong Identity API; form tạm đổi mật khẩu redirect theo role (`api/identity.py:220–272`). | Session bắt buộc, cho phép temporary session; M11 self-service. | M11 owner phải chốt one-time temp-password, purge/cache/no-log và hành vi sau đổi mật khẩu; markup `identity.py` hiện đang nằm trong source lock của amendment F06. |
| `/account` | Chưa có product page. Identity API có `/api/v1/me`, `/profile`, `/password`, `/sessions`, `/activity`, `/consent`, `/google` (`api/identity.py:32–44`). | API gắn với session của chính actor; `/api/v1/admin/accounts` có check Admin. | Chưa có view-model bốn tab, navigation hoặc method/permission matrix đã được M11 owner duyệt. |
| `/student/upload` | `GET` render form (`api/wsgi.py:317–344`); browser `POST /student/responses`; API `POST /api/student/responses` (`:345–348`). | GET yêu cầu Student (`:317–320`). Submit yêu cầu Student, giới hạn rate và consent active/version trùng (`:562–580`). | GET upload hiện resolve role nhưng không kiểm consent tại handler; cần owner chốt redirect/forbidden UX cho consent thiếu. API còn path cũ, không theo `/api/v1`; canonical/alias chưa khóa. |
| `/student/responses`, `/student/progress` | `GET` history và assessment statistics (`portal/router.py:179–188`). | Auth session; dữ liệu student được giới hạn theo owner trong service. | `/student/progress` là thống kê bài đánh giá, không phải learning progress. `/my-responses`/`/my-progress` và alias/back-refresh chưa được chốt. |
| `/student/responses/{id}`, `/report`, `/audio`, `/delete` | `GET` status/report/audio; delete page `GET`, xác nhận xóa `POST` (`api/wsgi.py:606–622`; `portal/router.py:199–256`). API status/report là `GET /api/student/responses/{id}/status|report` (`api/wsgi.py:590–604`). | Student service và portal response lookup kiểm owner; audio trả 404 nếu unavailable; delete là self-service. | M01/M06 chưa có formal acceptance hiện hành; thiếu M09 trust/refusal và M13 disclosure mapping. Route/payload versioning và foreign-ID evidence chưa gắn page contract mới. |

### Chi tiết API account hiện hành

Các route dưới đây dùng session của actor hiện tại; đây là quan sát từ adapter, không phải M11 owner approval. Writes có origin check ở những handler áp dụng.

| API | Method | Guard hiện tại / scope dữ liệu |
| --- | --- | --- |
| `/api/v1/me` | `GET` | Session self-service; handler cho phép temporary session (`identity.py:295–310`). |
| `/api/v1/me/profile` | `GET`, `PATCH` | Session actor hiện tại; chỉ field `goal`, `icon`, `color` được nhận khi update (`identity.py:312–326`). |
| `/api/v1/me/password` | `POST` | Session hiện tại; temporary session được resolve; cần origin check (`identity.py:328–346`). |
| `/api/v1/me/sessions` | `GET` | Liệt kê session của actor hiện tại (`identity.py:348–352`). |
| `/api/v1/me/sessions/{id}` | `DELETE` | Thu hồi session theo token actor hiện tại; origin check (`identity.py:354–375`). |
| `/api/v1/me/sessions/revoke-others` | `POST` | Thu hồi session khác của actor hiện tại; origin check (`identity.py:377–383`). |
| `/api/v1/me/activity` | `GET` | Session self-service, phân trang `limit/offset` (`identity.py:385–397`). |
| `/api/v1/me/consent` | `GET`, `POST` | Session self-service; body update giới hạn `version`, `research_allowed`, `active` (`identity.py:399–413`). |
| `/api/v1/me/google` | `GET`, `POST` | `GET` trả linked/enabled; `POST` unlink, có origin check. Link flow là route riêng; khi Google service thiếu, unlink/status phản hồi disabled (`identity.py:274–293`). |
| `/api/v1/admin/accounts` | `GET`, `POST` | `GET` resolve Admin; create đi qua account service sau origin check (`identity.py:415–445`). |
| `/api/v1/admin/accounts/{id}/{action}` | `POST` | Admin action qua account service, origin check (`identity.py:447–466`). |

Route target trong M15 Specification là đề xuất; chủ dự án đã chọn hướng giữ link hiện hành khi server authorization đúng, nhưng bảng canonical/alias/redirect theo method vẫn cần owner freeze (M15 Specification §§Page contracts; `04-test-plan.md:43–47`).

## Page-to-contract map và dependency owner

| Slice / trace | Implementation có thật | Contract cần chốt trước Phase 05 |
| --- | --- | --- |
| Landing/login/bands — `M15-FR-001/003`, `M15-AC-001/005`, `M15-TEST-001/002/012` | Login hiện có; landing/bands chưa có. | M11: auth/Google/password recovery và role; M05: approved public score/band explanation; M09: trust/refusal/claim guard. M05 đã được nghiệm thu; M09/M11 module approval còn pending. |
| Consent/account — `M15-FR-002`, `M15-AC-002`, `M15-TEST-002/008` | Consent page/form và M11 self-service API đã có; account UI chưa có. SCRUM-66 backend ở trạng thái `READY FOR REVIEW`, chưa phải M11 acceptance (`M11/07-status.md`, `evidence/scrum-66/review.md`). | M11 owner: policy temp password, Google disabled/configured, session UX, tab fields, consent event/version. M08 owner review vẫn pending cho shared Actor/Consent/API. |
| Upload/record/submit — `M15-FR-004`, `M15-AC-003/004`, `M15-TEST-003` | Upload form, recorder JS, file upload/submit, status page và consent submit check có sẵn (`api/templates.py`, `api/static/recorder.js`, `api/wsgi.py`). | M01 submit/status/retry/idempotency; M02 QC payload/reason/dispatch; M02 `QCMeasurement/QCResult` và PASS-only boundary còn Sang review (`m02-audio-qc/05-plan.md:16,38`); M08 owner/consent; M16 runtime/asset boundary. |
| Progress/history/report/audio/trust — `M15-FR-004/008`, `M15-AC-004/005`, `M15-TEST-004/012` | Assessment status, report, audio range, history/delete và assessment statistics có nền hiện hành. | M06 report/null/old-version contract; M09 refusal/trust payload; M13 metric source/n/disclosure; M01 owner/status. M01/M06 formal SDD còn `DRAFT/PENDING`, M09/M13 Phase 01 `PENDING`. |

**Error contract gap:** M15 Specification yêu cầu body `error.code`, `message`, `request_id`, redacted `details`; API handler hiện serialize lỗi thành `{"error": code}` (header request ID được thêm riêng ở `api/wsgi.py:182–187`). Cần chốt mapping 401/403/404/409/422/429/503 cho từng route trước khi UI retry hoặc giữ input.

## Asset/source ownership và candidate boundary

- Hiện có CSS inline ở `api/templates.py`, route `/local.css`, `api/static/recorder.js` và `report.js`. `pyproject.toml:35–36` chỉ khai báo package data cho `api/static/*.js` và migration SQL; không thấy font, SVG/art hoặc license manifest local trong vùng asset hiện tại.
- M15 Specification yêu cầu Roboto Vietnamese, local icon/art và package offline; `M15-TEST-009/010` cần reduced-motion, print, CSP và clean-wheel evidence. Cần Nguyên xác nhận nguồn/tác giả/license của font và art; Thắng/M16 xác nhận package path, license manifest và wheel/runtime boundary.
- Candidate files từ code hiện có: `src/aicefr/api/templates.py`, `src/aicefr/portal/templates.py`, `src/aicefr/api/static/*`, `src/aicefr/api/wsgi.py`, `src/aicefr/api/identity.py`, `pyproject.toml`. Đây **không phải allowed-file list**. `identity.py` hiện có diff riêng ở `_password_page` dưới amendment F06; route/handler/package file owner lock cần xác nhận trước khi chia task. Với `002`, `portal/router.py` và report/data path có thêm M01/M06/M08/M16 ownership.

## Evidence và candidate checks

- M15 Test Plan ghi candidate command `python -m pytest -q tests/api tests/local tests/web -m "not smoke"`, lint/format, coverage và Python Playwright; nhưng `tests/web/` và M15 browser script chưa tồn tại tại thời điểm Plan (`04-test-plan.md:33–39`). Chưa đủ để đóng exact task command/file list.
- `M15-TEST-002/003/004/008/009/010/012` cần direct route/API deny matrix; granted/denied consent; retry/double submit; status/report null/refusal/audio/delete/foreign ID; package font/license/CSP; DOM forbidden claim; viewport/focus/overflow. Browser evidence hiện cho 001A shell không thay integration QA N01.
- Không chạy test hoặc browser QA trong lượt đọc-only này. Không tạo evidence PASS mới.

## Tóm tắt `001A` A2R1/A2R2

- Phase 07 A2R1 review là `CHANGES_REQUIRED`: R01 required regression gate vẫn đỏ (33 fail IDs là tập con 35 fail IDs trên clean base; không có fail ID mới), coverage raw output/exit thiếu, browser evidence chưa gắn final fingerprint, clipping assertion chưa kiểm từng action, focus của main sau skip link mất visible outline. Xem `phase-07-review-a2-2026-10-15.md`.
- Correction A2R2 có file/fingerprint nhưng chưa được gửi/chạy; `agy-models.log` chỉ liệt kê Gemini 3.8 Flash (High), còn runner yêu cầu Gemini 3.6 Flash (High). Không có A2R2 report/evidence để review.

## Câu hỏi owner để mở gate

1. Nguyên/M11/M08: chốt route canonical/alias/redirect + method + actor/consent gate cho landing, bands, account, consent và password-change; chốt source lock quanh `identity.py`.
2. Sang/M05/M09: xác nhận copy/rubric scope public bands và schema/state cho trust/refusal; M05 đã accepted, M09 chưa có owner verdict.
3. Nguyên/Thắng/M16: xác nhận Roboto/art source, license và file packaging owner; wheel gate thuộc M16/W5-T04.
4. Nguyên/Thắng/Sang: cung cấp M01/M02/M06/M08/M09/M13 contract path/version/revision + owner verdict, gồm request/response/error, role/owner/consent và test evidence.
5. Nguyên: chốt page→view-model/API map, allowed files/owner locks, fixture states, test IDs/commands và evidence destination riêng cho 001B và 002.

**Codex readiness recommendation:** `BLOCKED` cho Phase 05 của `M15-TASK-001B` và `M15-TASK-002`. Chưa phát prompt.
