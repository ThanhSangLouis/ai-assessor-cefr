# SCRUM-65 — Codex implementation review

Historical target: `3b2d2b7` · reference: `40907cc` · actual branch base: `9968abc`.
Implementation: `514fb02` · reviewed code/tests: `61a5353`.
Ngày 15/10/2026 · Owner Thắng · Executor ba Luna theo chỉ dẫn trực tiếp · Codex lead/review.

## Kết luận

**Technical review: PASS / RECOMMEND REVIEW BY SANG.** Không còn finding BLOCKER/MAJOR trong implementation đã kiểm tra. Sang/user verdict **PENDING**, Jira SCRUM-65 chưa được đổi Done; G1/SCRUM-63 vẫn To Do tại lần đọc cuối. Không tự merge hoặc nghiệm thu thay reviewer.

Scope review gồm mọi source/test/SQL thay đổi của T01, composition root, pipeline commit fencing, package metadata, QA harness và các dependency trực tiếp. Root chỉ soạn prompt/docs, review actual diff và chạy độc lập; code do Luna thực hiện. Không implement account/OAuth/payment/learning UI hoặc task của Sang/Nguyên.

## Work package → evidence

| WP | Kết quả kỹ thuật | Evidence |
| --- | --- | --- |
| T01.1 | baseline actual branch 323 passed; backup v4/11 bảng/4 blob, restore báo cáo cũ | [baseline](baseline-pytest.log), [matrix](final-migration-matrix.json), [old app](rollback-old-app.json) |
| T01.2 | version registry, OS lock, preflight/backup, shape/checksum verification; v4→v9 atomic rollback/rerun | [pytest](reviewed-pytest.log), tests/storage/test_w5_storage_foundation.py |
| T01.3 | 5 nhóm schema additive, tổng 48 bảng; legacy 11 bảng và blobs giữ nguyên; FK/unique/immutable guards | [matrix](final-migration-matrix.json), [migration lane](migrations-report.md) |
| T01.4 | typed providers inject cùng một store; không DB thứ hai/global singleton | [integration](integration-report.md), tests/local/test_foundation_runtime.py |
| T01.5 | lease/CAS/heartbeat/retry/recovery/idempotency; stale caller không ghi report/terminal audit | [jobs](jobs-report.md), tests/storage/test_jobs.py, tests/local/test_durable_worker.py, tests/pipeline/test_coordinator.py |
| T01.6 | readiness/liveness aliases, safe probes, wheel SQL/static; clean venv+CLI/HTTP thật offline | [clean wheel](clean-wheel.json), [static](reviewed-static.json), [browser](final-browser.log) |

## Kiểm tra độc lập

- **358 passed, 0 failed/skip, 2 smoke deselected**, full non-smoke suite trên reviewed revision; [JUnit](reviewed-pytest.xml).
- Combined coverage **85.69865% → 86.15023%**, line **88.91223% → 89.46736%**, branch **74.20701% → 74.28367%**; không hạ threshold hoặc thêm exclusion để ép pass. [Coverage/risk summary](coverage-summary.json) ghi missing lines/branches của critical modules.
- Full lint PASS; format tất cả file Python đã đổi PASS. Global formatter còn 23 file legacy ngoài scope (baseline G0 28 file); không format sweep source không liên quan.
- Final wheel build PASS; cài từ wheel vào **venv sạch**, không editable/source import, dependencies cài offline từ wheelhouse; 10 HTTP/CLI/restore checks PASS. Missing model readiness 503, report `NOT_EVALUATED`/overall null, không fake score.
- Browser regression **11 viewport checks PASS**, desktop/mobile student/teacher, 0 console error, 0 failed/external requests. Screenshot hashes ở manifest/browser log.
- Migration thử trên bản sao demo: cả 11 bảng legacy/count/content digest giữ nguyên, blob hashes giữ nguyên, v9/FK/integrity/ledger/rerun PASS; restore v4 và app code cũ đọc được **4/4 report**.
- D043 path/dependency/import scan và high-confidence key/private-key pattern scan PASS; giới hạn scanner ghi rõ trong static record. Database/blob/models/private backups không đưa vào Git.

## Findings đã sửa trong review cycle

| ID | Mức | Finding và resolution |
| --- | --- | --- |
| F01 | MAJOR | Profile có display_name/free-text goal ngoài allowlist → bỏ PII field, constrain goal/icon/color; regression FK/allowlist |
| F02 | MAJOR | Lock import fcntl làm hỏng Windows, fresh initialization race → OS-conditional lock + bounded wait + single outer lock, concurrent initializer test |
| F03 | MAJOR | Schema version/ledger có thể bỏ sót index/trigger/column hoặc literal tamper → derived expected SQL signatures, literal-preserving normalization, tamper matrix |
| F04 | MAJOR | Backup/restore symlink/path traversal/incomplete manifest → confined paths, reject symlinks, required DB/inventory/checksum/private modes tests |
| F05 | MAJOR | Worker chỉ recover tại startup và mất crash gap trước claim response → periodic recovery/discovery, QUEUED/RUNNING retry/max-attempts tests |
| F06 | MAJOR | Pipeline stale fallback có thể làm fail successor → job+response fencing trong transaction, actual two-connection takeover success/error, một report/terminal audit |
| F07 | MAJOR | Readiness rollback có thể hủy transaction caller → savepoint và regression transaction preservation/query-only/schema/blob/model failures |
| F08 | MAJOR | Wheel smoke dùng fixture không tạo report/redirect login hoặc source contamination → QC REVIEW fixture, no-redirect login, sanitized env/import path, actual CLI+HTTP in clean venv |
| F09 | MAJOR | Heartbeat/retry critical branches thiếu evidence và coverage regression → behavioral tests bổ sung; full final coverage no regression |

## Giới hạn và dependency

- Windows path được review và có nhánh msvcrt; **chưa chạy trên Windows thật**.
- ASR/VAD inference bằng audio thật **NOT_RUN** trong T01 minimal smoke. Adapter readiness thật được kiểm riêng nếu local artifacts có sẵn; không claim CEFR accuracy/WER hoặc pipeline score thật từ browser QC REVIEW.
- Real local model adapter readiness PASS (scoring/ASR/VAD), chỉ load/verify artifact, không inference; [result](real-model-readiness.json).
- G1 To Do và Sang review chưa có verdict; PR sẵn sàng technical review, chưa phải Jira Done.
- M16 global phase/draft records và module khác không được tự đổi thành APPROVED. [Authority](authority.md) giữ đúng user request cho task này.
- Sự kiện feedback Luna được trao đổi trực tiếp qua collaboration trong review; bảng findings là tổng hợp sau review, không giả lập issuance timestamp trước khi gửi. Ba prompt gốc đã lưu trước dispatch.

**Next:** Sang review PR và G1 được chốt; xử lý finding mới nếu có. Không merge/chuyển Jira Done trong lượt này.
