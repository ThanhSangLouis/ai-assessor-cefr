# SCRUM-83 — Evidence nền tảng DoD W5

**Evidence ID:** `SCRUM-83-W5-DOD-BASELINE`  
**Ngày rà:** 25/10/2026  
**Owner theo nhánh:** Thắng  
**Integrated baseline:** `main` at `f540cb88643214cd1d4444f2dd0d81f4463119fa`
**SCRUM-83 code candidate:** `fa61076822787bf1e241345443e61860d8090a8c`
**Kết luận:** đã lập baseline evidence; W5 vẫn `PENDING`, chưa có verdict nghiệm thu của chủ dự án.

## Phạm vi và cách đọc

Ảnh Jira chỉ cung cấp tiêu đề SCRUM-83, không có mô tả/Acceptance Criteria đầy đủ. Bảng dưới dùng 12 điều kiện tại [Definition of Done W5](../plan/week-05.md#11-definition-of-done-w5) làm checklist evidence. Đây là inventory liên kết tới hồ sơ gốc, không phải lần chạy lại kiểm thử hay verdict Phase 09. Các kết quả cũ được gắn với revision/ngày chạy riêng; không ghép chúng thành một lần verification trên cùng SHA.

Baseline tích hợp hiện hành gồm PR #50–#52. SCRUM-83 candidate `fa61076` bổ sung dependency Windows timezone và sửa clean-wheel smoke theo consent-v2; log bên dưới chạy trên candidate này. Evidence lịch sử từ revision cũ vẫn được gắn rõ SHA/ngày chạy. Đây chưa phải final W5 DoD package hoặc owner acceptance.

## Đối chiếu 12 điều kiện DoD W5

| # | Điều kiện | Trạng thái evidence | Bằng chứng hiện có và phần còn thiếu |
| --- | --- | --- | --- |
| 1 | Feature matrix không còn hàng “Chưa có”; khác biệt còn lại được owner chấp nhận | `PARTIAL` | [Feature-gap matrix](../plan/week-05.md#3-hiện-trạng-và-khoảng-trống-phải-đóng) và [browser report M15](../sdd/modules/m15-product-web/evidence/scrum-74-76/integration-report.md) ghi các hành trình/API chưa hỗ trợ hoặc còn read-only. Chưa có record chấp nhận các gap còn lại. |
| 2 | Local mode khởi động sạch; ba role hoàn tất critical journey | `PARTIAL` | [M16 G0](../sdd/modules/m16-monolith-runtime/evidence/w5-g0-2026-10-15/W5-G0.md) có wheel boot và browser smoke ở baseline; [M15 integration](../sdd/modules/m15-product-web/evidence/scrum-74-76/integration-report.md) có role/route matrix. Chưa có lần chạy mọi critical journey trên một final SHA. |
| 3 | Wheel sạch; SQLite, blob store, worker và model readiness phản ánh đúng trạng thái | `PARTIAL — task-local PASS` | [Clean-wheel smoke](scrum-83/clean-wheel-smoke.log) trên `fa61076` cài wheel vào venv sạch, boot CLI/HTTP, kiểm tra login, liveness, missing-model readiness 503 và backup/restore report. [Coordinator/jobs tests](scrum-83/worker-jobs-tests.log) đạt 34 passed; [scoped regression](scrum-83/selected-tests.log) đạt 145 passed/4 skipped. Chưa kiểm tra worker restart và report dedup trên cùng wheel hoặc final W5 package. |
| 4 | Pipeline thật chạy ít nhất một audio có quyền, có model/version/provenance | `EVIDENCE_PRESENT — giới hạn rõ` | [W6-S03 / SCRUM-80](../sdd/modules/m09-trust-layer/evidence/w6-s03-real-pipeline.md) ghi một audio TTS do macOS tạo, hash và phiên bản model, chạy trên `cabcc44`. Đây là smoke kỹ thuật, không phải giọng người học hay đo độ chính xác CEFR; `NOT_MEASURED`/`NOT_EVALUATED` được giữ nguyên. |
| 5 | Migration/restore smoke PASS; report cũ đọc được | `PARTIAL` | [SCRUM-83 clean-wheel smoke](scrum-83/clean-wheel-smoke.log) tạo report không có model, backup vào snapshot và đọc lại report từ restore; migration/storage tests chạy trên `fa61076`. Chưa chứng minh toàn bộ report cũ trong final environment. |
| 6 | Full suite, format, lint, wheel, secret scan, coverage PASS trên final revision | `OPEN` | Scoped regression và worker/jobs PASS; changed-file Ruff PASS; wheel clean-install PASS. Chưa chạy full suite/coverage/global format/secret scan trên final W5 package. M16 G0 và SCRUM-67 ghi rõ các giới hạn global format cũ; cần W5-T01/final gate. |
| 7 | Browser desktop/mobile PASS cho public/student/teacher/admin | `PARTIAL` | [M15 integration report](../sdd/modules/m15-product-web/evidence/scrum-74-76/integration-report.md) có các route/viewport và screenshot trên revision `0827b37`; báo cáo cũng liệt kê interaction, accessibility và security cases chưa chạy. Chưa phải browser matrix trên `82fe708`/final candidate. |
| 8 | Không còn finding BLOCKER/MAJOR hoặc risk được owner chấp nhận | `OPEN` | Các report task-local có giới hạn và mục chờ reviewer/owner; chưa có một disposition tổng hợp và không có record accepted-risk cuối cho W5. |
| 9 | README/run guide/env/API inventory/evidence manifest khớp code | `PARTIAL` | `docs/local-run.md` và [.env.example](../../.env.example) khớp biến `AICEFR_MODEL_DIR`; ứng dụng không tự nạp dotenv, runtime config dùng JSON. API inventory và module statuses được xử lý riêng trong SCRUM-84; chưa audit toàn bộ manifest trên một final W5 package. |
| 10 | AI Prompt Log W05 của từng người đúng ngày/công việc | `PRESENT — completeness not rechecked` | Workbook W05 có trong repo; lượt rà SCRUM-83 này chưa kiểm tra từng sheet và từng dòng với lịch sử sử dụng AI. |
| 11 | SDD/status phản ánh thực tế, không tự ghi approval/acceptance | `PARTIAL` | [W6-S02 sync M09](../sdd/modules/m09-trust-layer/evidence/w6-s02-sync.md), M10/M12/M13 có cập nhật status; M11/M14/M16 và global phase vẫn còn `DRAFT`/`PENDING` hoặc task-local trạng thái khác nhau. Cần tiếp tục qua SCRUM-84, không đổi verdict thay owner. |
| 12 | Chủ dự án review package cuối và đưa verdict | `PENDING` | Chưa thấy verdict nghiệm thu W5. Theo DoD, trạng thái W5 vẫn `PENDING` trước verdict, kể cả khi từng kiểm tra kỹ thuật có kết quả tốt. |

## SCRUM-83 task-local verification

Jira SCRUM-83 được đọc trực tiếp ngày 25/10/2026: migration database v4/restore smoke, clean wheel, worker restart không tạo report trùng, run guide và `.env` mẫu; task kết thúc khi có log lệnh thật trong evidence W5. Scope này đã có evidence trong thư mục [scrum-83](scrum-83/):

- Scoped regression: **145 passed, 4 skipped, 2 warnings**; bốn skip do host Windows không cấp quyền tạo symlink. Hai warning là pytest temp cleanup không xóa được snapshot SQLite còn mở trong `test_report_migration.py` và `test_sqlite_memory_migration.py`; test vẫn pass.
- Coordinator/jobs: **34 passed**. Cụ thể gồm `tests/local/test_durable_worker.py::test_worker_recovers_lease_that_expires_after_startup` và `tests/storage/test_jobs.py::test_expired_job_after_terminal_commit_is_reconciled_without_new_audit`, kiểm tra recovery sau restart và không tạo audit trùng. Đây là test suite trên source branch, không claim chạy worker từ clean wheel. Ruff cho `scripts/qa/w5_foundation_smoke.py`: PASS.
- Wheel `aicefr-0.1.0-py3-none-any.whl`: SHA-256 `0cccde9db20b612f123f97b96a77f4f9cde6c0340b12531fc76ef763eecfa1d8`; clean venv smoke PASS (13 bước), có liveness/login, model-missing readiness 503, consent-v2 audio opt-in và backup/restore report. `Model inference NOT_RUN` vì không có model artifact.
- Windows clean wheel ban đầu thiếu `tzdata`, khiến `Asia/Ho_Chi_Minh` không khả dụng. Candidate thêm `tzdata>=2024.1`; helper đặt UTF-8 cho CLI trên Windows và chấp nhận consent hiện hành cùng audio-storage opt-in tường minh. Không nới mặc định consent.
- `.env.example` chỉ khai báo biến thực sự được code đọc (`AICEFR_MODEL_DIR`); tài liệu nói rõ file này không tự được nạp. Các thiết lập runtime còn lại ở JSON config.

Đây là evidence task-local cho SCRUM-83, không phải final gate hoặc owner verdict của W5. Mục #3/#5 vẫn partial vì chưa có một wheel chạy worker restart/dedup và mở mọi report cũ trong một lần final integrated run; mục #6 và #12 còn mở.

## Kết luận task-local

SCRUM-83 có log lệnh thật theo Definition of Done của ticket. Kết quả này **không** chứng minh W5 đạt DoD: điều kiện 6, 8, 12 còn mở; các mục 1–5, 7–11 vẫn có phần kiểm tra tích hợp/reviewer hoặc revision cần làm tiếp. Không đánh dấu W5 `DONE` trong report này.
