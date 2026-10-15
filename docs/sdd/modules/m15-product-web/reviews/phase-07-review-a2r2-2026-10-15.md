# M15 — Phase 07 Implementation Review — M15-TASK-001A / A2R2

**PHASE RECORD ID / REVIEW ID:** `M15-07-A2R2` / `07-M15-TASK-001A-A2R2`  
**PHASE:** 07 — Implementation Review; **SCOPE ID/TYPE/ROOT:** `M15` / module / `docs/sdd/modules/m15-product-web/`  
**TASK / PROMPT:** `M15-TASK-001A` / `M15-W5-N01-001A-A2R2` (W5-N01.1 một phần).  
**BASE REVISION:** `6baf720f173b440eb961676b09ea290058a39b35`. **HEAD:** `null` — working-tree diff chưa commit.  
**REVIEW BASIS:** actual working-tree diff, A2R2 prompt, raw logs, browser JSON/screenshots và coverage JSON; không có commit/patchediff riêng cho A2R2 nên diff hiện tại gồm cả thay đổi A2R1 đã có.  
**EVIDENCE:** `evidence/m15-task-001a-a2r2/`.  
**USER VERDICT:** `PENDING`. **CODEX CHECK RESULT:** `FAIL`. **CODEX RECOMMENDATION:** `CHANGES REQUIRED`.

## Kết luận

Chưa thể khép Phase 07. R04 đã được sửa và browser QA có assertion computed focus style. Tuy nhiên, R03 vẫn thiếu kiểm tra primary action bắt buộc theo route và có thể cho PASS khi action chính bị ẩn. Bằng chứng R01 không khớp tuyên bố baseline trong report: hai failed test ID không có trong clean-base log; non-smoke và coverage gate đều exit 1. R02 còn mâu thuẫn giữa fingerprint của prompt, report và trạng thái workspace; do đó không chứng minh được các log/browser artifacts thuộc cùng source snapshot. Không đánh dấu Task Verified/DONE và chưa bắt đầu Phase 08.

## Scope và actual diff

Actual working-tree diff so với `HEAD` gồm `src/aicefr/api/templates.py`, `scripts/qa/m15_shell_browser.py`, `tests/local/test_templates_m15_shell.py`, `tests/local/test_templates_mobile.py` và `src/aicefr/api/identity.py`. Diff `identity.py` chỉ bỏ `<main>` bọc ngoài và đổi heading trong `_password_page`; đây là F06 đã được cho phép qua Phase 05 amendment v0.2a/A2R1. Không thấy thay đổi route/auth/form action mới trong diff đó. Không có immutable A2R2 head để tách chính xác delta A2R2 khỏi phần A2R1.

`git status` hiển thị `EDUZ/` là thư mục untracked. Theo giới hạn của prompt, Codex không đọc nội dung thư mục này; vì vậy review không thể xác nhận độc lập rằng nội dung EDUZ giống snapshot trước handoff. Fingerprint A2R2 cũng loại trừ `EDUZ/**`. Không ghi nhận việc Codex sửa source hoặc nội dung ngoài scope trong lượt review này.

## Đối chiếu R01–R04

| Finding | Kết quả | Căn cứ |
| --- | --- | --- |
| **R01 — raw verification/baseline/coverage** | **OPEN — MAJOR.** Raw logs có đủ để đọc kết quả, nhưng report kết luận sai về tập lỗi và ghi sai whole-project branch totals. | `non-smoke-regression.log` có 36 failed / 558 passed / 15 skipped / 2 deselected, exit 1. So với clean-base `evidence/m15-task-001a-a2/codex-review/pytest-baseline-nonsmoke.log`: 34 failed IDs trùng, hai ID mới là `tests/billing/test_billing_repository.py::test_distinct_connections_settle_one_event_once` và `tests/storage/test_jobs.py::test_two_connections_cannot_claim_same_job`; một baseline-only ID là `tests/storage/test_w5_storage_foundation.py::test_w5_restore_rejects_incomplete_or_escaping_manifests`. Hai traceback mới có `BrokenBarrierError`/timeout nhưng không chứng minh được nguyên nhân là baseline. `coverage.log` cũng exit 1 do suite đỏ. `coverage.json` xác nhận `templates.py` 115/115 statements, 20/20 branches; toàn repo là 7,815/8,917 statements (87.64%) và 2,173/2,880 branches (75.45%). Trong report, 455 bị ghi thành missing branches nhưng JSON xác định đó là `num_partial_branches`; 85% là combined coverage. |
| **R02 — fingerprint/traceability** | **OPEN — BLOCKER.** Các giá trị không nhất quán, final state không tái lập được từ evidence hiện có. | Prompt A2R2 và prompt-log ghi starting fingerprint `1ae115f3…`; `report.md` ghi `3a4bd112…`. `final-source-fingerprint.log` ghi final `6687a1a1…`, nhưng không có preflight log với `--expect`; `browser-qa-results.json` chỉ lưu giá trị truyền bằng CLI. Codex chạy lại helper với đúng exclude/metadata options: workspace fingerprint `1ae115f3…` (file_count 693 trước khi tạo record này), trùng prompt start nhưng khác report final. `07-status.md`/prompt-log tại lúc handoff còn ghi A2R2 chưa gửi/chạy do model unavailable, trái với user handoff và report đã chạy. HEAD null là phù hợp với diff chưa commit; các mâu thuẫn còn lại khiến không thể ràng buộc raw logs/ảnh với một final source snapshot xác minh được. |
| **R03 — clipping và primary actions** | **OPEN — MAJOR.** Assertion mới kiểm được bounds một số phần tử nhìn thấy, nhưng không bảo đảm primary action của từng route đang hiện diện và dùng được. | Trong `scripts/qa/m15_shell_browser.py`, `visibleActions` loại `display:none`, `visibility:hidden` và `offsetParent === null` trước khi review; sau đó chỉ đặt `num_actions = len(...)`, không có `assert num_actions > 0` hoặc expected primary selector/count theo route. Navigation links có thể làm danh sách còn phần tử khi nút submit chính bị ẩn. `interactable` chỉ kiểm `pointerEvents !== 'none'`; forms không được kiểm ancestor clipping. Vì vậy report §1.2/§2 nói có assert số action dương và toàn bộ primary actions được kiểm là vượt quá những gì code thực thi. |
| **R04 — focus indicator của main** | **RESOLVED.** | `templates.py` có `main:focus, main:focus-visible` với outline 3px. Unit test `test_main_landmark_focus_indicator_defined` xác minh CSS; browser script sau Enter kiểm `activeElement`, style/độ rộng/màu outline và kích thước/vị trí main. JSON ghi 18 PASS assertions. |

## Evidence và checks Codex

| Check | Kết quả | Evidence |
| --- | --- | --- |
| Diff/scope review | **FAIL** do R02/R03 còn mở; không thấy route/auth change ngoài scope. `identity.py` là F06 carry-over đã duyệt. | `git diff HEAD`; `src/aicefr/api/identity.py` `_password_page`; prompt A2R2. |
| Targeted tests — Codex rerun | **PASS — 32 passed in 4.62s.** Lượt chạy đầu với pytest temp mặc định lỗi tạo temp directory trong sandbox (26 passed, 6 fixture setup errors); chạy lại với `--basetemp` trong writable visualization folder cho kết quả nêu trên. | Command: `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --basetemp <writable-temp> tests/local/test_templates_mobile.py tests/local/test_templates_m15_shell.py tests/api/test_identity_api.py tests/api/test_student.py`. |
| Non-smoke regression | **FAIL — 36 failed, 558 passed, 15 skipped, 2 deselected; exit 1.** Có 2 ID không nằm trong clean-base failure set. Không kết luận chúng do code M15 gây ra; evidence chưa chứng minh đó là baseline. | `non-smoke-regression.log`; clean-base `pytest-baseline-nonsmoke.log`; so sánh ID set độc lập của Codex. |
| Coverage | **FAIL — command exit 1** vì test suite đỏ. Target `templates.py` 100% statements/branches; repo report có số branch sai như R01. | `coverage.log`, `coverage.json`, `report.md` §3. |
| Lint/format | Changed-file log báo PASS; repo `ruff check` PASS, repo `ruff format --check` exit 1 với 22 file. | `lint-format-changed.log`, `lint-format-repo.log`. |
| Browser QA | JSON có 18 PASS strings, 0 console errors, 0 failed requests, fixture-server mode; 17/17 screenshot tồn tại và SHA-256 khớp JSON. Đây không khắc phục lỗ hổng assertion R03. | `browser-qa-results.json`, `screenshots/`, `browser-qa.log`. |
| Fingerprint | **FAIL — không khớp.** Tính lại theo đúng options của prompt cho ra `1ae115f3…`, không phải final `6687a1a1…` trong report/log. | `final-source-fingerprint.log`; lệnh `workspace_fingerprint.py` do Codex chạy lại trong review. |

## Findings

### `M15-A2R2-R01` — MAJOR · Verification evidence

**STATUS:** `OPEN`  
**OBSERVED EVIDENCE:** non-smoke/coverage exit 1; two A2R2 failed IDs vắng trong baseline log; report ghi `100%` lỗi trùng baseline. Coverage report gán nhầm 455 partial branches thành missing và ghi 2,425 covered thay vì JSON 2,173.  
**RISK / FAILED AC:** Không chứng minh được regression gate không phát sinh failure mới; người đọc có thể hiểu sai baseline và coverage.  
**REQUIRED CHANGE:** Cập nhật report theo raw logs/JSON. Chạy so sánh clean-base tương đương cho hai test concurrency mới hoặc ghi rõ chúng chưa được xác nhận là baseline; giữ `VERIFICATION_FAILED` khi required gate còn exit 1. Không mô tả toàn bộ failures là lỗi Windows baseline nếu test-ID/traceback evidence không chứng minh điều đó.

### `M15-A2R2-R02` — BLOCKER · Evidence traceability

**STATUS:** `OPEN`  
**OBSERVED EVIDENCE:** starting fingerprint `1ae115f3…` trong prompt khác `3a4bd112…` trong report; final report/log `6687a1a1…` khác kết quả Codex tính lại `1ae115f3…`; không có preflight `--expect` output; status/prompt-log chưa ghi nhận handoff đã chạy. QA script nhận fingerprint do CLI truyền vào và không xác minh snapshot.  
**RISK / FAILED AC:** Không thể gắn test/browser/coverage output với một source snapshot xác định; actual diff chưa có immutable head SHA.  
**REQUIRED CHANGE:** Cung cấp preflight command/output `--expect` và final fingerprint được tính lại trên working tree đúng lúc chạy gate; đồng bộ report, prompt/log, browser JSON và Status. Nếu attempt đã thay đổi sau gate, tạo evidence mới trên final fingerprint. Không thay các giá trị lịch sử bằng số mới mà không ghi nguồn/thời điểm.

### `M15-A2R2-R03` — MAJOR · Browser QA/test quality

**STATUS:** `OPEN`  
**OBSERVED EVIDENCE:** QA lọc bỏ action bị ẩn trước khi đếm; không assert action bắt buộc nào tồn tại theo từng route; test tương tác chỉ xét `pointerEvents`; form không có kiểm tra ancestor clipping.  
**RISK / FAILED AC:** Primary submit có thể bị ẩn/mất mà browser QA vẫn PASS do còn link điều hướng; element bị che bởi overlay có thể bị tính là interactable.  
**REQUIRED CHANGE:** Khai báo selector/expected primary actions theo route; assert mỗi action bắt buộc có bounds dương, visible, trong viewport, không ancestor-clipped và hit-test/interact được. Kiểm tra form clipping phù hợp với report, rồi cập nhật claim trong report khớp assertion thực tế.

### `M15-A2R2-R04` — MAJOR · Accessibility

**STATUS:** `RESOLVED`  
**RESOLUTION EVIDENCE:** CSS focus indicator, unit assertion và browser computed-style assertion sau khi kích hoạt skip link bằng Enter; R04 không còn blocker trong diff/evidence được inspect.

## Review package

**CHECKLIST RESULT:** Scope/traceability — FAIL (R02); behavior/test — FAIL (R03); raw verification/baseline — FAIL (R01); accessibility focus — PASS (R04); screenshot integrity — PASS.  
**RESULT:** `CHANGES_REQUIRED`.  
**CODEX RECOMMENDATION:** `CHANGES REQUIRED`; không approve Phase 07.  
**USER VERDICT:** `PENDING` — chủ dự án quyết định verdict cuối.  
**NEXT ACTION:** Khắc phục R01–R03 trong phạm vi/quyền còn hiệu lực và trả evidence nhất quán; sau đó Codex re-review finding còn mở. Không đánh Task Verified/DONE và không vào Phase 08 trước user verdict Phase 07 `APPROVED`.
