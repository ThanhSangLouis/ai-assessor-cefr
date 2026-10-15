# M15 — Test Plan

**Version:** v0.2 · **STATUS:** Phase 04 user verdict `APPROVED` ngày 15/10/2026; contract-dependent tests chờ owner freeze.
**Input:** Requirement v0.2 `APPROVED`; Research v0.3 `RUN`; Specification v0.3 Phase 03 user verdict `APPROVED` ngày 15/10/2026. Approval M15 không duyệt thay contract của M10–M14/M16.

## Chiến lược và dữ liệu kiểm thử

- `pytest` kiểm view-model, template, route/auth/consent và các chuyển trạng thái deterministic; fixture chỉ dùng tài khoản/audio/dữ liệu do nhóm tạo, không dùng secret hoặc thông tin cá nhân thật.
- Python Playwright theo convention `scripts/qa/w5_identity_browser.py` và `scripts/qa/w5_billing_browser.py` thực hiện browser assertions trên server local loopback. Script M15 sẽ được tạo trong Phase 06 theo Task đã duyệt; vì chưa có script hoặc UI mới, toàn bộ M15 browser QA hiện `NOT_RUN`.
- Mỗi journey kiểm desktop 1280×800 và mobile 390×844; responsive risk kiểm thêm 360/768 px, zoom 200%, long Vietnamese text. Xác minh keyboard/focus, accessible name, semantic state, contrast light/dark, reduced motion và print khi áp dụng.
- Request ra host ngoài phải bị chặn và ghi; console error, failed critical request và external request phải bằng 0, trừ mock fixture được khai báo trong result JSON. Screenshot có hash và assertion DOM/API tương ứng; ảnh riêng lẻ không đạt `PASS`.
- Contract-dependent test phải dùng version/revision đã owner duyệt. Nếu contract thiếu hoặc khác Specification, ghi `BLOCKED`/`NOT_RUN`, cập nhật Phase 03/05 đúng impact; không dùng mock để tuyên bố integration `PASS`.

## Trace FR/AC → Test → expected result

| Test ID | FR / AC | Case chính, lỗi và ranh giới | Expected / level |
| --- | --- | --- | --- |
| M15-TEST-001 | FR-001; AC-001 | Button/field/dialog/table/audio ở idle, focus, disabled, loading, invalid, error; keyboard Tab/Enter/Escape; light/dark và contrast | Component/template + browser: accessible name, focus visible, no trap, dialog trả focus, text/control đạt AA; không có state chỉ truyền bằng màu |
| M15-TEST-002 | FR-002; AC-002 | Anonymous/student/teacher/admin, actor đa role; menu và direct GET/API; 401/403/404; consent thiếu, password-change gate | API + browser: server deny đúng contract, foreign resource không bị xác nhận; menu không lộ quyền/count; browser ẩn action không thay server gate |
| M15-TEST-003 | FR-004; AC-003/004 | Recorder permission granted/denied, upload file hợp lệ/sai định dạng/quá cỡ, preparation 30 giây/skip, preview, rerecord, submit double-click, network failure | Browser: chỉ submit sau preview, audio nghe lại được, retry/fallback rõ, không tạo hai submission; countdown thông báo được bằng chữ và assistive tech |
| M15-TEST-004 | FR-004; AC-004/005 | `QUEUED/RUNNING/REVIEW_REQUIRED/FAILED/COMPLETED`, report cũ/null/insufficient/refusal, audio unavailable, delete confirm/foreign ID | Template + browser/API: poll/backoff/stop đúng trạng thái; overall chỉ khi đủ evidence, 5 tiêu chí chỉ coverage; `Interaction=null` kèm `insufficient_evidence` cho độc thoại; null không thành 0; 401/403/404 không leak |
| M15-TEST-005 | FR-005; AC-004/005 | Roadmap/lesson/review/result/achievement/streak/pronunciation đủ-thiếu data; 409/422/retry/continue; mobile sticky action | Browser/API: next/review state đúng contract M10/M13, practice không hiện CEFR band; insufficient có source/n/status; action không che nội dung |
| M15-TEST-006 | FR-006; AC-002/004/006 | Review claim contention/TTL/stale revision; blind list/sheet/draft/submit timeout/one-time; authoring save/preview/publish conflict; insight override | Browser/API/security: giữ input và recovery, không duplicate mutation; blind allowlist áp dụng ở DOM, JSON, URL, history và network; không lộ identity/machine/other-rater |
| M15-TEST-007 | FR-007; AC-002/004/005/006 | Admin account create/reset/CSV, config/data preview-confirm, rating/study, billing quote/order/return/receipt/refresh; 401/403/404/409/422/429/503 | Browser/API: role gate server, one-time temp-password chỉ theo M11 policy đã duyệt, CSV thường không chứa password, sandbox label, order state tách verify, receipt chỉ PAID/đúng quyền |
| M15-TEST-008 | FR-001/002/004–007; AC-001/004 | 360/390/768/1280 px, zoom 200%, long label/table/card, keyboard order, direct route refresh/back | Browser: không horizontal overflow/trap/covered primary action; heading/current nav/focus đồng bộ URL và role |
| M15-TEST-009 | FR-008; AC-001 | Reduced motion, decorative art, print, screen-reader tree, pointer events | Browser/static: art không chặn thao tác/đọc; thông tin vẫn còn khi tắt animation; asset ẩn trong print khi decorative |
| M15-TEST-010 | FR-001; AC-007 | Build wheel, cài sạch offline và mở page ở target runtime; CSS/JS/SVG/WOFF2/license/CSP | Package/runtime: asset đủ trong wheel, không request CDN, font/license đúng manifest; final clean-wheel gate phối hợp owner M16/W5-T04 |
| M15-TEST-011 | FR-009; AC-008 | QA result JSON đầy đủ revision/route/role/viewport/steps/assertions/console/network/external/screenshot SHA-256; file thiếu hoặc hash sai | Tooling: reject evidence không trace được; `PASS` chỉ khi assertions và artifact thực tồn tại trên cùng revision |
| M15-TEST-012 | FR-003/005/006/007; AC-005/006 | Scan template, rendered DOM, response và network cho claim chứng chỉ/đậu-rớt, 5 điểm tiêu chí, practice band, secret/token/path, blind forbidden fields | Static + browser: không có claim/field cấm; label lộ trình A2/B1/B2 không ngụ ý practice CEFR band; exception một lần của M11 chỉ theo policy owner duyệt |

## Lệnh và áp dụng

| Gate | Lệnh hoặc cách chạy | Trạng thái hiện tại |
| --- | --- | --- |
| Targeted Python tests | `python -m pytest -q tests/api tests/local tests/web -m "not smoke"` sau khi Task tạo `tests/web/`; kiểm file thay đổi và direct dependency | `NOT_RUN` cho M15 mới; `tests/web/` chưa tồn tại |
| Format/lint | `ruff format --check src tests scripts` và `ruff check src tests scripts` | `NOT_RUN` cho M15 mới |
| Coverage | `python -m pytest -q -m "not smoke" --cov=aicefr --cov-branch --cov-report=term-missing --cov-report=json:coverage.json` | `NOT_RUN` cho M15 mới; ghi line/branch, delta và nhánh critical chưa phủ |
| Browser QA | Python Playwright script M15 trong `scripts/qa/`, chỉ `localhost/127.0.0.1`, output result JSON/screenshots/hash/console/network vào evidence của Task | `NOT_RUN`; script M15 chưa được tạo |
| Packaging | `python -m build --wheel --no-isolation`, rồi clean-wheel boot theo `docs/local-run.md` khi M16 readiness có | `NOT_RUN` cho M15; final gate thuộc W5-T04 |

**UT/coverage policy đề xuất:** unit/template/API tests là `REQUIRED` cho logic view-model, authorization integration và trạng thái JS có thể tách test; browser E2E là `REQUIRED` cho journey, accessibility và responsive. Coverage được đo trên revision final; chưa đặt một tỷ lệ toàn cục. Phase 05 sẽ chốt cách ghi delta, critical uncovered branch và quyền chấp nhận rủi ro. Browser assertions là evidence bổ sung, không thay UT nơi có logic testable.

## Dependency và điều kiện dừng

- M10/M12/M13, M11/M14/M16 cần owner cung cấp payload/error/role/enum/forbidden-field/metric/order contract đã duyệt, kèm version/revision. M11 temporary-password ngoại lệ và M12 blind dual-role là security gate; không đánh dấu Test 006/007/012 `PASS` bằng contract kỹ thuật `READY FOR REVIEW`.
- Canonical route/alias/server gate phải được owner chốt trước khi xây browser route matrix. Link hiện hành chỉ được giữ khi server kiểm quyền/consent đúng.
- `M15-TEST-010` và full integrated matrix cần W5-T04/M16 readiness; component mock test có thể chạy trước nhưng task W5-N01–N04 không `DONE` vì mock.
- Mọi fail/skip/missing fixture/không chạy phải hiện trong evidence và Phase 07/08. Test Plan này là thiết kế kiểm tra, chưa phải kết quả kiểm thử.
