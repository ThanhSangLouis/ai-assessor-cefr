# SCRUM-67 — Verification độc lập

Historical target `3b2d2b7`; Sang `40907cc`; actual base `bab5f25` (T01 + T02 `754ee9a`). Final reviewed code/test/QA revision `5c6397ffaf804a3cb08c17aef1017fa3884737ca`. Full non-smoke: **600 PASS, 0 FAIL, 0 SKIP, 2 smoke deselected**, 131,99 giây; baseline 425 PASS. [Coverage summary](coverage-summary.json), [full log](final-pytest.log), [baseline log](baseline-pytest.log). Raw logs/coverage/junit/wheel nằm ngoài repo: `ai-assessor-cefr-runtime/evidence/scrum-67-2026-10-15/`; không commit binary wheel, database, blob hoặc key.

## Evidence đã kiểm tra

| Work package / gate | Evidence | Kết quả |
| --- | --- | --- |
| T03.1 / M14-TEST-001/002 plan/entitlement/usage/proration/grace | tests/billing/test_plans.py, test_quotes.py, test_billing_service.py | PASS (final full suite) |
| T03.2 / M14-TEST-004/010 repository/state machine/rollback/race | tests/billing/test_billing_repository.py | PASS (final full suite) |
| T03.3 / M14-TEST-003–005 signature/tampering/replay | tests/billing/test_gateways.py, test_payment_tampering.py; tests/api/test_billing_webhook_contract.py | PASS (final full suite) |
| T03.4 / M14-TEST-006/008 test adapters/live guard/setup status/no outbound | billing autouse outbound-deny fixture; injected fake transport; gateway tests | offline PASS; merchant sandbox thật NOT_RUN |
| T03.5 / M14-TEST-007 signed license/key version/audit | tests/billing/test_licenses.py | PASS (final full suite) |
| T03.6 / M16-TEST-006/007 export/erase/retention/restore | tests/api/test_data_operations_api.py; tests/portal/test_portal.py | PASS (final full suite) |
| Migration v4/v9→v10, failure rollback, preserve/reopen | tests/storage/test_privacy_migration.py; test_w5_storage_foundation.py | PASS (final full suite) |
| W5 populated data roundtrip | [Count/hash matrix](root-w5-roundtrip.json) | PASS |
| Wheel clean boot/static/readiness/CLI | [Foundation](wheel-foundation.json) | PASS |
| Chromium trên wheel sạch | [Browser](wheel-browser.json) | PASS |
| Sang signature/statistical boundary review | handoff; chưa có verdict người review | PENDING |
| Nguyên admin flow review | handoff; chưa có verdict người review | PENDING |

## Populated W5 fixture

Harness độc lập ngoài source nạp profile/session/consent, lesson/media, practice/step attempt, review item, achievement/streak, study/enrollment/survey, assignment/research rating/adjudication, machine seen/review session/SEM, durable job/cleanup intent, quote/order/receipt/entitlement và signed license. So sánh row count và SHA256 full rows của **mọi bảng** giữa snapshot database và bản restore; FK sạch, cả response audio và lesson media còn nguyên, license xác minh được bằng key đã restore. Blob bị sửa bị từ chối. Erasure gỡ dữ liệu cá nhân và giữ media bài học dùng chung; export không có credential/session hash/provider secret/license artifact. Chỉ dùng fixture tổng hợp, không đụng database demo hiện có.

## Wheel và browser

Wheel được cài bằng `pip --no-index --find-links .../wheelhouse/scrum-65` trong venv mới, cwd ngoài repo và bỏ PYTHONPATH/PYTHONHOME. Server import `aicefr` từ site-packages; wheel chứa migration010/template JS. Root so sánh byte mọi Python/SQL/JS với source candidate. Browser client dùng Playwright Chromium; adapter nguồn chỉ dùng ký fixture callback, server chạy code trong wheel.

Journey thực: login admin/student có HTTP200→303; admin đọc overview, quote/order, gửi signed sandbox webhook hai lần, đọc receipt; retention GET dry-run, backup, restore vào thư mục mới và erasure preview; student export own dữ liệu và bị từ chối billing/backup admin; request sai Origin bị403. Zero page/console errors. Đây là browser integration API qua session thật, chưa phải nghiệm thu full UI N04.

## Lệnh tái lập

```text
PYTHONPATH=src AICEFR_MODEL_DIR=<runtime/models> COVERAGE_FILE=<evidence/.coverage-final> python -m pytest -m 'not smoke' --cov=aicefr --cov-report=json:<evidence/final-coverage.json> --junitxml=<evidence/final-junit.xml>
ruff check src tests scripts
ruff format --check <changed Python files>
python scripts/ci/check_md_links.py
python scripts/ci/check_forbidden_files.py
python -m pip wheel --no-deps --no-build-isolation . -w <evidence/dist>
python scripts/qa/w5_foundation_smoke.py --wheel <wheel> --evidence-dir <evidence/wheel-foundation> --python-dependency-cache <runtime/wheelhouse/scrum-65>
python scripts/qa/w5_billing_browser.py --base-url <loopback> --data-dir <disposable data-dir> --admin-id <fixture-admin> --student-id <fixture-student>
```

Root harness orchestration và populated fixture script: `/tmp/scrum67_wheel_journey.py`, `/tmp/scrum67_w5_roundtrip.py`; đường dẫn là evidence local của phiên, không là dependency của sản phẩm/CI. Tests tương ứng trong repo giữ regression có thể chạy lại.

## Giới hạn

Linux/Python3.12 local; CI Python3.11 được kiểm riêng trên PR. Windows runtime chưa chạy; portability getuid có regression mô phỏng. Model inference, provider merchant sandbox thật và live payment NOT_RUN. Không có production deployment hoặc network call thật tới payment provider. Global format có 22 file legacy ngoài diff không đạt ở cả baseline và candidate; changed-file format phải PASS, không trình bày global format là PASS. Strong-secret pattern scan và review DTO chỉ là kiểm tra trong phạm vi thay đổi, không tuyên bố audit bí mật toàn tổ chức.

User verdict và Sang/Nguyên acceptance: PENDING; tạo PR không tự đổi Jira DONE.

## Final coverage và quality checks

Whole project: statement **90,524%** (baseline 89,011%), branch **79,340%** (baseline 74,974%), combined **87,794%** (baseline 85,817%). Excluded lines vẫn 122 như baseline, không thêm pragma/exclusion hoặc hạ threshold. Policy no-regression PASS. Các implementation critical đạt ≥90% statement và ≥85% branch:

| Module | Statement | Branch |
| --- | --- | --- |
| billing/gateways | 94,06% | 89,44% |
| billing/licenses | 92,61% | 87,25% |
| billing/secrets | 92,79% | 85,71% |
| billing/service | 95,96% | 88,60% |
| billing/plans, quotes | 100% | 100% |
| storage/billing | 97,29% | 95,24% |
| api/billing | 92,68% | 88,46% |
| api/data_operations | 94,26% | 86,96% |
| portal/data | 95,97% | 85,37% |

Facade `billing/__init__.py` còn nhánh AttributeError cho import tên không tồn tại (statement85,71%/branch50%); không phải authorization/settlement/privacy branch. PortalService legacy được giữ trong global coverage, không mở scope sửa toàn bộ legacy. Các nhánh hiếm filesystem/platform vẫn chưa cover hoàn toàn; policy critical đã đạt, các đường quyền/secret/replay/rollback chính có regression và code inspection.

Ruff toàn `src tests scripts`: PASS; 39 changed Python format: PASS; diff whitespace: PASS; Markdown links: PASS; forbidden tracked files và strong-secret pattern scan trong changed text: PASS. Global format: FAIL từ 22 file legacy ngoài diff, cùng số lượng ở baseline; không sửa hàng loạt file ngoài task. Migration005–009 không đổi byte/checksum. Model inference và merchant/live payment NOT_RUN.

Codex recommendation: **RECOMMEND APPROVAL về kỹ thuật / READY FOR REVIEW**. Sang/Nguyên/user verdict PENDING; CI sẽ được theo dõi trên PR, không tự nghiệm thu hoặc đổi Jira DONE.
