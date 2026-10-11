# M03 — Status

| Mục | Trạng thái |
| --- | --- |
| Lifecycle | proposed |
| Phase hiện tại | 09 — Acceptance APPROVED cho phần đã làm; M03-TASK-002 xong Phase 06, chờ Phase 07 |
| Requirement | [01-requirement.md](01-requirement.md) · v0.2 · **APPROVED** 26/09/2026 |
| Research mode | **`RUN`** (chọn tại Phase 01); [02-research.md](02-research.md) review cùng Phase 03 |
| Specification | [03-specification.md](03-specification.md) · v0.2 · **APPROVED** 26/09/2026 |
| Test Plan | [04-test-plan.md](04-test-plan.md) · v0.2 · **APPROVED** 26/09/2026 |
| Plan & Tasks | [05-plan.md](05-plan.md), [06-tasks.md](06-tasks.md) · v0.2 · **APPROVED** 26/09/2026; task READY/BLOCKED theo dependency — xem 06-tasks.md |
| Implementation | M03-TASK-003, 004, 001 đã implement (Claude, theo yêu cầu chủ dự án); evidence [M03-EV-002](evidence/evidence-manifest.md). TASK-002: adapter `asr/local.py` có từ W3, smoke `tests/smoke/test_asr_smoke.py` thêm 11/10/2026; S1/S2 PASS trên audio của DEP-06 ([M03-EV-004](evidence/evidence-manifest.md)) — chờ Phase 07 |
| Review | Phase 07 A1 **APPROVED** 26/09/2026; A2 (follow-up 07-A1-03) **APPROVED** 03/10/2026, [review-log](reviews/review-log.md) |
| Final Verification | Phase 08 [M03-EV-P08](evidence/evidence-manifest.md) trên main 74afca9 — **APPROVED** 27/09/2026; [M03-EV-P08-A2](evidence/evidence-manifest.md) trên main ae72d57 — **APPROVED** 03/10/2026 |
| Acceptance | Phase 09 **APPROVED** 27/09/2026 và 03/10/2026 (follow-up 07-A1-03) — nghiệm thu phần đã làm (AC-001, AC-003); AC-002 và M03-TASK-002 để mở |
| Prompt hiện hành | NONE ISSUED; base revision/fingerprint NOT_SET |

## Phase 01 record

```text
PHASE RECORD ID: M03-01-A1
PHASE: 01 — Requirement
SUBJECT: 01-requirement.md v0.2
CODEX CHECK RESULT: PASS — FR/AC có ID và trace; xung đột liên module đã nêu impact
CODEX RECOMMENDATION: RECOMMEND APPROVAL
USER VERDICT: APPROVED
VERIFIED/APPROVED BY: User (Sang)
USER VERDICT AT: 26/09/2026
RESEARCH MODE: RUN — theo đề xuất, người dùng không đổi khi duyệt
NEXT ACTION: Phase 03 — Specification cùng Research
```

## Phase 03 record

```text
PHASE RECORD ID: M03-03-A1
PHASE: 03 — Specification
SUBJECT: 02-research.md v0.2 + 03-specification.md v0.2
CHECKS: FR/AC trace; success/invalid/boundary/failure/recovery; security/privacy;
  accessibility N/A có lý do; fact/inference/option tách riêng; không tự quyết sản phẩm
OPEN: M03-O-001 engine (khuyến nghị faster-whisper `small` cho mọi môi trường); M03-O-002 DecodedAudio 16 kHz mono (Thắng chốt)
CODEX CHECK RESULT: PASS về cấu trúc; còn OPEN nêu trên
CODEX RECOMMENDATION: RECOMMEND APPROVAL sau khi user chốt OPEN
USER VERDICT: APPROVED — chốt các OPEN theo khuyến nghị
VERIFIED/APPROVED BY: User (Sang)
USER VERDICT AT: 26/09/2026
NEXT ACTION: Phase 04 — Test Plan
```

## Phase 04 record

```text
PHASE RECORD ID: M03-04-A1
PHASE: 04 — Test Plan
SUBJECT: 04-test-plan.md v0.2 — 16 unit + 2 smoke (S2 chỉ quan sát)
CHECKS: FR/AC → Test ID; success/invalid/boundary/failure/regression; level/command;
  UT applicability + alternative evidence; browser N/A có lý do; không thêm requirement
OPEN: TP-D-001 coverage policy (khuyến nghị line ≥ 90 %, branch ≥ 85 %, loại trừ adapter nặng)
DEPENDENCY: pyproject/tests skeleton của Thắng; reason code mới trong contract chung
CODEX CHECK RESULT: PASS về cấu trúc; chờ TP-D-001
CODEX RECOMMENDATION: RECOMMEND APPROVAL sau khi user chốt TP-D-001
USER VERDICT: APPROVED — TP-D-001 theo khuyến nghị
VERIFIED/APPROVED BY: User (Sang)
USER VERDICT AT: 26/09/2026
NEXT ACTION: Phase 05 — Plan & Task Readiness
```

## Phase 05 record

```text
PHASE RECORD ID: M03-05-A2
PHASE: 05 — Plan & Task Readiness
SUBJECT: 05-plan.md v0.2 + 06-tasks.md v0.2 — 4 task (001–004)
CHECKS: trace FR/AC → Test → Task PASS; boundary/data flow PASS; rủi ro/rollback/Clean Code PASS;
  task nhỏ, vùng file rõ PASS; runtime/convention PASS (pyproject + CI trên main a92fafe);
  dependency sẵn sàng PASS cho task READY (kiểm lại 26/09/2026)
TASKS: TASK-001, 003, 004 đề xuất READY; TASK-002 BLOCKED (DEP-03 16 kHz, DEP-06 audio)
CODEX CHECK RESULT: PASS cho task đề xuất READY
CODEX RECOMMENDATION: RECOMMEND APPROVAL — chỉ phát prompt Antigravity cho task READY
USER VERDICT: APPROVED — cho các task READY; task BLOCKED chờ đủ dependency
VERIFIED/APPROVED BY: User (Sang)
USER VERDICT AT: 26/09/2026
NEXT ACTION: Phase 06 — M05-TASK-002 (Claude implement theo yêu cầu của chủ dự án)
```

## Phase 07 record

```text
PHASE RECORD ID: M03-07-A1
PHASE: 07 — Implementation Review
SUBJECT: M03-TASK-003, 004, 001 (SCRUM-18, 19, 20)
CHECKS: verify evidence (base/diff/test/coverage) PASS; checklist code + test PASS sau correction
FINDINGS: 07-A1-01 MAJOR, 07-A1-02 MINOR, 07-A1-03 MINOR, 07-A1-07 NIT — MAJOR/NIT đã sửa; MINOR còn mở là follow-up
DEVIATIONS: xem reviews/review-log.md (cần user chấp nhận)
CODEX CHECK RESULT: PASS
CODEX RECOMMENDATION: RECOMMEND APPROVAL — kèm chấp nhận các khác biệt Test Plan và follow-up MINOR
USER VERDICT: APPROVED — chấp nhận các khác biệt Test Plan và các follow-up MINOR đã ghi
VERIFIED/APPROVED BY: User (Sang)
USER VERDICT AT: 26/09/2026
NEXT ACTION: Phase 08 — Final Verification trên main sau khi merge PR Phase 07
```

## Phase 08 record

```text
PHASE RECORD ID: M03-08-A1
PHASE: 08 — Final Verification
SUBJECT: M03-TASK-003, 004, 001 trên main 74afca9, fingerprint 7bc236e3a3df1890…
CHECKS: test pass trên final head (0 failed); skipped có lý do (cần artifact thật, P05-D-001) và
  đã chạy PASS trên máy có artifact; coverage đạt TP-D-001; Test ID khớp code cuối; CI main xanh
CODEX CHECK RESULT: PASS
CODEX RECOMMENDATION: RECOMMEND APPROVAL
USER VERDICT: APPROVED — task đã làm chuyển Verified
VERIFIED/APPROVED BY: User (Sang)
USER VERDICT AT: 27/09/2026
NEXT ACTION: Phase 09 — Acceptance
```

## Phase 09 record

**SCOPE ID/ROOT:** M03 / `docs/sdd/modules/m03-asr/` — chỉ kết luận cho module này.

| Phase | Record | Verdict |
| --- | --- | --- |
| 01 Requirement | M03-01-A1 | APPROVED 26/09/2026 |
| 03 Specification | M03-03-A1 | APPROVED 26/09/2026 |
| 04 Test Plan | M03-04-A1 | APPROVED 26/09/2026 |
| 05 Plan & Tasks | M03-05-A2 | APPROVED 26/09/2026 |
| 07 Review | 07-M03-A1 (reviews/review-log.md) | APPROVED 26/09/2026 |
| 08 Final Verification | M03-08-A1 (M03-EV-P08) | APPROVED 27/09/2026 |

| AC | Nội dung | Evidence cuối | Kết quả |
| --- | --- | --- | --- |
| M03-AC-001 | Test double tất định, đánh dấu test_only; lỗi engine → ASR_FAILED | M03-TEST-001, 003 (M03-EV-002, EV-P08) | ĐẠT |
| M03-AC-002 | Smoke local thật có model/version, không mạng; chưa có evidence thì pending | Weight đã tải + SHA-256 (M03-EV-001); smoke S1/S2 NOT_RUN — M03-TASK-002 BLOCKED | PENDING (AC cho phép trạng thái chờ) |
| M03-AC-003 | ASR khớp/lệch trained_with.asr_model | M03-TEST-013–015 (M03-EV-002) | ĐẠT |

**Regression / chất lượng trên main 74afca9:** 133 passed (có artifact), 123 passed + 10 skipped (CI), 0 failed; coverage branch 99 %; TP-D-001 không bị hạ, không thêm exclusion.

Phần W2 đã làm (TASK-003, 004, 001) đạt AC-001, AC-003. AC-002 còn PENDING vì TASK-002 bị chặn (16 kHz từ M02 — SCRUM-16, audio có quyền dùng — SCRUM-22).

```text
PHASE RECORD ID: M03-09-A1
PHASE: 09 — Acceptance
CODEX CHECK RESULT: PASS cho phần đã làm; module còn task BLOCKED
CODEX RECOMMENDATION: RECOMMEND APPROVAL cho phần đã làm (AC-001, AC-003); AC-002 và TASK-002 để mở — chưa nghiệm thu trọn module
USER VERDICT: APPROVED — nghiệm thu phần đã làm (AC-001, AC-003); AC-002 và M03-TASK-002 để mở
VERIFIED/APPROVED BY: User (Sang)
USER VERDICT AT: 27/09/2026
```

## Đợt A2 — follow-up 07-A1-03 (W3, 03/10/2026)

```text
PHASE RECORD ID: M03-07-A2
PHASE: 07 — Implementation Review
SUBJECT: Follow-up 07-A1-03 (SCRUM-50), review record 07-M03-A2
CHECKS: verify evidence M03-EV-003 PASS; checklist code + test PASS
FINDINGS: 07-A2-01 NIT, 07-A2-02 MINOR liên module
DEVIATIONS: Spec v0.2.1, Test Plan v0.2.1 — cần user chấp nhận
CODEX CHECK RESULT: PASS
CODEX RECOMMENDATION: RECOMMEND APPROVAL — kèm chấp nhận v0.2.1, NIT, và follow-up MINOR cho coordinator
USER VERDICT: APPROVED — chấp nhận v0.2.1, NIT 07-A2-01 và follow-up 07-A2-02
VERIFIED/APPROVED BY: User (Sang)
USER VERDICT AT: 03/10/2026
NEXT ACTION: Phase 08 trên main ae72d57 (ae72d57b03de0ae9333e8b549484d026feb3177c)
```

```text
PHASE RECORD ID: M03-08-A2
PHASE: 08 — Final Verification
SUBJECT: Follow-up 07-A1-03 trên main ae72d57 (ae72d57b03de0ae9333e8b549484d026feb3177c), fingerprint 8835acf872d8c0ab…
CHECKS: 0 failed trên final head; `asr/service.py` 100 % line/branch; M03-TEST-005 ↔ tests/asr/test_service.py;
  CI run 37113044170 trên ae72d57, Python 3.11: 192 passed, 11 skipped
CODEX CHECK RESULT: PASS
CODEX RECOMMENDATION: RECOMMEND APPROVAL
USER VERDICT: APPROVED
VERIFIED/APPROVED BY: User (Sang)
USER VERDICT AT: 03/10/2026
NEXT ACTION: Phase 09 — Acceptance
```

| AC | Evidence bổ sung đợt A2 | Kết quả |
| --- | --- | --- |
| M03-AC-001 | M03-TEST-005 mở rộng: QC REJECT → NOT_RUN kèm lý do QC, engine không được gọi (M03-EV-003, EV-P08-A2) | ĐẠT |
| M03-AC-002 | Không đổi — M03-TASK-002 chỉ còn chờ DEP-06 (audio có quyền dùng) | PENDING (AC cho phép trạng thái chờ) |
| M03-AC-003 | Không đổi | ĐẠT |

```text
PHASE RECORD ID: M03-09-A2
PHASE: 09 — Acceptance
CODEX CHECK RESULT: PASS cho phần đã làm; FINDING-07-A1-03 RESOLVED; M03-TASK-002 vẫn BLOCKED
CODEX RECOMMENDATION: RECOMMEND APPROVAL cho follow-up 07-A1-03; AC-002 và TASK-002 để mở
USER VERDICT: APPROVED — nghiệm thu follow-up 07-A1-03; AC-002 và M03-TASK-002 để mở
VERIFIED/APPROVED BY: User (Sang)
USER VERDICT AT: 03/10/2026
```

**Lý do trạng thái:** chủ dự án yêu cầu chuẩn bị đầy đủ tài liệu W2 để review một lượt. Việc có file nháp không vượt checkpoint tuần tự của skill SDD; các phase vẫn phải được duyệt theo thứ tự trước implementation/handoff.


- [Prompt Log](prompts/prompt-log.md): chưa phát prompt Antigravity; mọi implementation do Claude làm theo yêu cầu chủ dự án, ghi trong Evidence Manifest.
- [Evidence Manifest](evidence/evidence-manifest.md): evidence Phase 06 và Phase 08 của từng đợt.
- [Review Records](reviews/review-log.md): Phase 07 A1 (26/09/2026), A2 (03/10/2026).
- [Kế hoạch W2](../../../plan/week-02.md); [nguồn tài liệu](../../../sources/README.md).

## Phase 06 record — M03-TASK-002 (11/10/2026)

```text
PHASE RECORD ID: M03-06-A3
PHASE: 06 — Implementation & Test
SUBJECT: M03-TASK-002 (Jira SCRUM-22 cho DEP-06); Claude làm theo yêu cầu chủ dự án, không qua prompt Antigravity
BASE: main c427983
CHANGES: tests/smoke/test_asr_smoke.py (M03-TEST-S1, S2); adapter asr/local.py có sẵn từ W3-TASK-005, không sửa
CHECKS: smoke S1/S2 chạy thật, tắt mạng bằng cách chặn socket: PASS, 0 lần thử kết nối;
  SHA-256 bốn tệp weight khớp M03-EV-001; status OK, asr_model whisper-small, 136 từ, 9,5–9,9 s;
  S2 asr_conf_mean 0,990 — ngoài khoảng huấn luyện [0,691 ; 0,950] nhưng trong khoảng M05 chấp nhận
  [0,561 ; 1,079] (ood_tolerance 0,5), nên không phải báo owner M05 theo Test Plan;
  CI-mode 308 passed, 13 skipped; có artifact Ridge 321 passed; ruff sạch
RESULT: M03-AC-002 có smoke evidence — đề xuất chuyển ĐẠT ở Phase 09
USER VERDICT: PENDING
NEXT ACTION: Phase 07 — Implementation Review
```
