# M15 — Phase 05 Readiness Precheck for W5-N01–N04

**Record ID:** `M15-05-PRECHECK-W5-N01-N04-2026-10-15`  
**Record type:** Codex readiness precheck; this is not a Phase 05 verdict record.  
**Scope:** M15 tasks mapped to SCRUM-73–76 in `docs/plan/week-05.md` §§9.3–9.5.  
**Baseline inspected:** HEAD `6baf720f173b440eb961676b09ea290058a39b35` plus current local SDD/evidence changes.  
**Owner scope decision:** W5-N01–N04 `APPROVED` by project owner on 15/10/2026; see [scope decision](w5-n01-n04-scope-approval-2026-10-15.md).

## Kết luận precheck

M15 Phase 01/03/04 có user verdict `APPROVED`. Phase 03 Codex check còn `BLOCKED` bởi P03-01–05; chủ dự án đã chọn hướng xử lý, nhưng các contract/version và route/security decisions cần owner approval vẫn chưa được cung cấp/freeze. Phase 05 chính thức chỉ được duyệt cho `M15-TASK-001A` và amendment F06. `M15-TASK-001A` hiện `CHANGES_REQUIRED` sau A2R1; correction A2R2 chưa chạy do Antigravity runner hiện không liệt kê Gemini 3.6 Flash (High).

**Codex check:** `BLOCKED` cho Phase 05 readiness của `M15-TASK-001B`, `002`, `003`, `004`, `005`, `006`.  
**Codex recommendation:** `BLOCKED`; chưa trình Phase 05 user verdict cho các task này.  
**Prompt issuance:** chưa đủ điều kiện phát prompt Antigravity. Scope approval không thay Definition of Ready.

## Precheck theo task

| W5 / M15 task | FR/AC/Test đã có | Readiness | Dependency cần chốt trước Phase 05 | File boundary và evidence còn phải chốt |
| --- | --- | --- | --- | --- |
| `W5-N01` / `001B`, `002` | FR-001–004/008; AC-001–005; TEST-001–004/008/009/012 | `BLOCKED`; riêng `001A` đang `CHANGES_REQUIRED` | Canonical route/method/auth/consent matrix; M11 account/temp-password policy; M01 submit/status; M02 upload/QC contract và Sang review; M06 report/audio/delete; M08 owner review; M09 trust/refusal; M13 disclosure; M16 asset/runtime impact; W5-S01/T02. M05 scoring semantics đã được nghiệm thu ở Phase 09. | Chốt page-to-view-model/API map và route/asset ownership trước khi đóng allowed files. M15-TEST-003/004/012 cần fixture cho granted/denied, retry, null/insufficient, foreign ID và forbidden claim; browser pack N01.7 chỉ sau khi N01 pages sẵn sàng. |
| `W5-N02` / `003` | FR-005; AC-004/005; TEST-005/008/012 | `BLOCKED` | M10 lesson/practice/review payload, enums, ordering, recommendation/error states; M13 pronunciation/metric source, n, thresholds and insufficient states; W5-S02/S03 và W5-T01 persistence contract. M10/M13 Status đang Phase 01 `DRAFT/PENDING`. | Chốt task-level allowed files sau endpoint/view-model freeze; tạo state matrix nối API→DOM cho lesson/review/result/achievement/pronunciation. Browser evidence cần lesson success/failure/retry, review schedule, no-band DOM assertion, mobile sticky/focus và delete permission. |
| `W5-N03` / `004` | FR-006; AC-002/004/006; TEST-006/008/012 | `BLOCKED` | M07 queue/claim/decision contract; M10 authoring/lesson contract; M12 blind route/payload deny matrix, admin-as-rater dual-role gate, draft lifetime/purge/one-time submit; M13 KPI/cohort disclosure; W5-S02/S04/T01. M07 Status PENDING; M10/M12/M13 Phase 01 `DRAFT/PENDING`. | Chốt allowlist/deny matrix trước route/template file list. Evidence cần claim contention/expiry, stale revision recovery, no leak trong DOM/JSON/URL/history/network, one-time submit, lesson publish và insight audit. |
| `W5-N04` / `005`, `006` | FR-007/009; AC-002/004–008; TEST-002/007–012 | `BLOCKED` | M11 temp-password exception/purge/no-log/CSV; M12 rating/adjudication/exports; M13 study/SEM/metrics; M14 order vs return/verify/receipt and sandbox labels; M16 data operations/assets/wheel/runtime. N01–N03 phải qua review trước integrated browser regression. M11/M14 technical handoff có sẵn nhưng owner/module acceptance còn `PENDING`; M12/M13/M16 còn DRAFT/PENDING. | Chốt admin route/view-model per owner và separate M15-TEST-007 vs M15-TEST-010/011 scope. Full role/direct-URL/forbidden-DOM scan chỉ chạy trên integrated revision; N04.7 không thể là prompt độc lập trước các page N01–N03. |

## Phase 05 Definition of Ready còn thiếu

1. Contract producer có version/revision, verdict của owner, schema/example, enum/error, role/authorization và contract tests; chỉ handoff kỹ thuật hoặc code đã merge chưa đủ thay verdict. Với N01, M02 Plan v0.2 nêu rõ QCResult/QCMeasurement và PASS-only dispatch còn cần Sang (M03/M04 owner) review; M05 scoring semantics đã accepted.
2. Route matrix cho canonical/alias/redirect và GET/POST/API, consent/auth server gate, old-link behavior và source owner.
3. Security decisions: M11 temporary-password exception và lifecycle; M12 blind forbidden-field matrix/dual-role/draft policy; M14 receipt/payment sandbox policy.
4. Metric/content disclosure từ M13, kể cả source, sample threshold, null/insufficient và những claim không được UI sinh.
5. M16 asset packaging/runtime boundary cho test cần wheel; phân biệt integration check của N04 với final W5-T04.
6. Per-task allowed file list, owner locks, rollback boundary, exact targeted commands, test fixtures và evidence destinations.

Khi inputs trên có mặt, Codex sẽ đối chiếu chúng với M15 Specification/Test Plan và implementation hiện hành. Nếu khác giả định Phase 03, quay lại phase sớm nhất bị ảnh hưởng; sau đó trình Phase 05 record riêng theo task/task batch đủ nhỏ. Chỉ sau user verdict Phase 05 `APPROVED` mới tạo prompt có base revision/fingerprint, file log và preflight lock.

## Owner input cần để mở gate

Vui lòng chuyển các contract đã duyệt hoặc nêu path/version/revision cùng verdict của owner cho M01, M02, M06–M14 và M16 theo task phụ thuộc ở bảng trên; M05 đang accepted và M08 có Phase 05 approval lịch sử nhưng owner review vẫn pending. Với contract chưa được duyệt, cần owner tương ứng chốt trực tiếp; Codex không ghi thay verdict của producer. Sau khi các đầu vào này được lưu trong repo, có thể chạy lại precheck mà không cần thay đổi scope W5 đã duyệt.
