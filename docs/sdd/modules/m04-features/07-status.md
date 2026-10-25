# M04 — Status

| Mục | Trạng thái |
| --- | --- |
| Lifecycle | proposed |
| Phase hiện tại | 09 — Acceptance APPROVED cho phần đã làm; M04-TASK-003 xong Phase 06, chờ Phase 07 |
| Requirement | [01-requirement.md](01-requirement.md) · v0.2 · **APPROVED** 26/09/2026 |
| Research mode | **`SKIPPED`** (chọn tại Phase 01) — skip record: M04-D-003 trong [01-requirement.md](01-requirement.md) |
| Specification | [03-specification.md](03-specification.md) · v0.2 · **APPROVED** 26/09/2026 |
| Test Plan | [04-test-plan.md](04-test-plan.md) · v0.2 · **APPROVED** 26/09/2026 |
| Plan & Tasks | [05-plan.md](05-plan.md), [06-tasks.md](06-tasks.md) · v0.2 · **APPROVED** 26/09/2026; task READY/BLOCKED theo dependency — xem 06-tasks.md |
| Implementation | M04-TASK-001, 002 đã implement (Claude, theo yêu cầu chủ dự án); evidence [M04-EV-001](evidence/evidence-manifest.md). TASK-003: adapter `features/local.py` có từ W3; thêm TEST-016 và smoke `tests/smoke/test_vad_smoke.py` 11/10/2026, PASS ([M04-EV-002](evidence/evidence-manifest.md)) — chờ Phase 07 |
| Review | Phase 07 A1 **APPROVED** 26/09/2026, [review-log](reviews/review-log.md); A2 (M04-TASK-003) PASS 11/10/2026, **chờ verdict** |
| Final Verification | Phase 08 evidence [M04-EV-P08](evidence/evidence-manifest.md) trên main 74afca9 — **APPROVED** 27/09/2026 |
| Acceptance | Phase 09 **APPROVED** 27/09/2026 — nghiệm thu phần đã làm (AC-001–004 mức unit); M04-TASK-003 để mở |
| Prompt hiện hành | NONE ISSUED; base revision/fingerprint NOT_SET |

## Phase 01 record

```text
PHASE RECORD ID: M04-01-A1
PHASE: 01 — Requirement
SUBJECT: 01-requirement.md v0.2
CODEX CHECK RESULT: PASS — FR/AC có ID và trace; xung đột liên module đã nêu impact
CODEX RECOMMENDATION: RECOMMEND APPROVAL
USER VERDICT: APPROVED
VERIFIED/APPROVED BY: User (Sang)
USER VERDICT AT: 26/09/2026
RESEARCH MODE: SKIP — theo đề xuất, người dùng không đổi khi duyệt
NEXT ACTION: Phase 03 — Specification với skip record
```

## Phase 03 record

```text
PHASE RECORD ID: M04-03-A1
PHASE: 03 — Specification
SUBJECT: 03-specification.md v0.2 (Research SKIPPED)
CHECKS: FR/AC trace; success/invalid/boundary/failure/recovery; security/privacy;
  accessibility N/A có lý do; fact/inference/option tách riêng; không tự quyết sản phẩm
OPEN: Không có OPEN riêng; phụ thuộc M03-O-002 và mã `FEATURE_VERSION_MISMATCH` (Thắng duyệt)
CODEX CHECK RESULT: PASS về cấu trúc; không có OPEN riêng
CODEX RECOMMENDATION: RECOMMEND APPROVAL sau khi user chốt OPEN
USER VERDICT: APPROVED — chốt các OPEN theo khuyến nghị
VERIFIED/APPROVED BY: User (Sang)
USER VERDICT AT: 26/09/2026
NEXT ACTION: Phase 04 — Test Plan
```

## Phase 04 record

```text
PHASE RECORD ID: M04-04-A1
PHASE: 04 — Test Plan
SUBJECT: 04-test-plan.md v0.2 — 18 unit + 1 smoke; giá trị kỳ vọng số cho 18 đặc trưng
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
PHASE RECORD ID: M04-05-A2
PHASE: 05 — Plan & Task Readiness
SUBJECT: 05-plan.md v0.2 + 06-tasks.md v0.2 — 3 task (001–003)
CHECKS: trace FR/AC → Test → Task PASS; boundary/data flow PASS; rủi ro/rollback/Clean Code PASS;
  task nhỏ, vùng file rõ PASS; runtime/convention PASS (pyproject + CI trên main a92fafe);
  dependency sẵn sàng PASS cho task READY (kiểm lại 26/09/2026)
TASKS: TASK-001, 002 đề xuất READY; TASK-003 BLOCKED (DEP-03 16 kHz, DEP-06 audio)
CODEX CHECK RESULT: PASS cho task đề xuất READY
CODEX RECOMMENDATION: RECOMMEND APPROVAL — chỉ phát prompt Antigravity cho task READY
USER VERDICT: APPROVED — cho các task READY; task BLOCKED chờ đủ dependency
VERIFIED/APPROVED BY: User (Sang)
USER VERDICT AT: 26/09/2026
NEXT ACTION: Phase 06 — M05-TASK-002 (Claude implement theo yêu cầu của chủ dự án)
```

## Phase 07 record

```text
PHASE RECORD ID: M04-07-A1
PHASE: 07 — Implementation Review
SUBJECT: M04-TASK-001, 002 (SCRUM-24, 25)
CHECKS: verify evidence (base/diff/test/coverage) PASS; checklist code + test PASS sau correction
FINDINGS: 07-A1-01 MAJOR, 07-A1-04 MINOR, 07-A1-05 MINOR — MAJOR/NIT đã sửa; MINOR còn mở là follow-up
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
PHASE RECORD ID: M04-08-A1
PHASE: 08 — Final Verification
SUBJECT: M04-TASK-001, 002 trên main 74afca9, fingerprint 7bc236e3a3df1890…
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

**SCOPE ID/ROOT:** M04 / `docs/sdd/modules/m04-features/` — chỉ kết luận cho module này.

| Phase | Record | Verdict |
| --- | --- | --- |
| 01 Requirement | M04-01-A1 | APPROVED 26/09/2026 |
| 03 Specification | M04-03-A1 | APPROVED 26/09/2026 |
| 04 Test Plan | M04-04-A1 | APPROVED 26/09/2026 |
| 05 Plan & Tasks | M04-05-A2 | APPROVED 26/09/2026 |
| 07 Review | 07-M04-A1 (reviews/review-log.md) | APPROVED 26/09/2026 |
| 08 Final Verification | M04-08-A1 (M04-EV-P08) | APPROVED 27/09/2026 |

| AC | Nội dung | Evidence cuối | Kết quả |
| --- | --- | --- | --- |
| M04-AC-001 | Feature tất định; thiếu timing → null + reason | M04-TEST-001–009 (M04-EV-001, EV-P08) | ĐẠT |
| M04-AC-002 | Không PII; chỉ số không đo được không bị báo là đã đo | M04-TEST-007, 017 | ĐẠT |
| M04-AC-003 | Đủ 18 tên đúng feature_order; thiếu vẫn giữ tên | M04-TEST-010, 011, 012 | ĐẠT |
| M04-AC-004 | vad_name khớp trained_with; VAD khác → reason lệch | M04-TEST-014, 015 (VAD giả); Silero thật chưa có — M04-TASK-003 BLOCKED | ĐẠT ở mức unit |

**Regression / chất lượng trên main 74afca9:** 133 passed (có artifact), 123 passed + 10 skipped (CI), 0 failed; coverage branch 99 %; TP-D-001 không bị hạ, không thêm exclusion.

4/4 AC có evidence unit. Adapter Silero thật (M04-TASK-003, M04-TEST-016, S1) chưa làm vì bị chặn như M03-TASK-002; follow-up 07-A1-04 (kiểm segment VAD) gắn vào task này.

```text
PHASE RECORD ID: M04-09-A1
PHASE: 09 — Acceptance
CODEX CHECK RESULT: PASS cho phần đã làm; module còn task BLOCKED
CODEX RECOMMENDATION: RECOMMEND APPROVAL cho phần đã làm (AC-001–004 ở mức unit); M04-TASK-003 để mở — chưa nghiệm thu trọn module
USER VERDICT: APPROVED — nghiệm thu phần đã làm (AC-001–004 mức unit); M04-TASK-003 để mở
VERIFIED/APPROVED BY: User (Sang)
USER VERDICT AT: 27/09/2026
```

**Lý do trạng thái:** chủ dự án yêu cầu chuẩn bị đầy đủ tài liệu W2 để review một lượt. Việc có file nháp không vượt checkpoint tuần tự của skill SDD; các phase vẫn phải được duyệt theo thứ tự trước implementation/handoff.


- [Prompt Log](prompts/prompt-log.md): chưa phát prompt.
- [Evidence Manifest](evidence/evidence-manifest.md): chưa có implementation/test evidence của repo dự án.
- [Review Records](reviews/review-log.md): chưa có Phase 07 review.
- [Kế hoạch W2](../../../plan/week-02.md); [nguồn tài liệu](../../../sources/README.md).

## Phase 06 record — M04-TASK-003 (11/10/2026)

```text
PHASE RECORD ID: M04-06-A2
PHASE: 06 — Implementation & Test
SUBJECT: M04-TASK-003 (DEP-06, Jira SCRUM-22); Claude làm theo yêu cầu chủ dự án, không qua prompt Antigravity
BASE: main c427983
CHANGES: tests/features/test_local.py (M04-TEST-016 với Silero thật không nạp được); tests/smoke/test_vad_smoke.py (M04-TEST-S1);
  adapter features/local.py có sẵn từ W3-TASK-005, không sửa
CHECKS: TEST-016 PASS — 10 đặc trưng vad_* None + FEATURE_NOT_COMPUTABLE, không VAD dự phòng, đặc trưng transcript vẫn có;
  smoke S1 chạy thật, chặn socket: PASS, 0 lần thử kết nối; Silero 6.2.1 (MIT), 9 đoạn, đủ 10 giá trị vad_*;
  CI-mode 308 passed, 13 skipped; có artifact Ridge 321 passed; ruff sạch
USER VERDICT: PENDING
NEXT ACTION: Phase 07 — Implementation Review
```

## Phase 08–09 chuẩn bị — M04-TASK-003 (11/10/2026)

```text
PHASE RECORD ID: M04-08-W4
PHASE: 08 — Final Verification
SUBJECT: M04-TASK-003 trên main 35d3514cf3279f2cd6d87ce2db2f1d0d23de725b (merge PR #32)
CHECKS: xem M04-EV-P08-W4 — CI run 38150517851 PASS; 0 failed trên máy và CI; độ phủ 96 %
CODEX CHECK RESULT: PASS
CODEX RECOMMENDATION: RECOMMEND APPROVAL
USER VERDICT: PENDING
NEXT ACTION: chủ module ghi verdict Phase 07 (review-log), 08 và 09
```

| AC | Evidence | Đề xuất |
| --- | --- | --- |
| M04-AC-001..003 | Không đổi (M04-EV-001, P08) | ĐẠT (đã nghiệm thu) |
| M04-AC-004 | TEST-016 và smoke S1 với Silero thật (M04-EV-002, M04-EV-P08-W4) | Đề xuất ĐẠT |

```text
PHASE RECORD ID: M04-09-W4
PHASE: 09 — Acceptance
CODEX CHECK RESULT: PASS — đủ evidence cho mọi AC; không còn task BLOCKED
CODEX RECOMMENDATION: RECOMMEND APPROVAL
USER VERDICT: PENDING
```

## W7-S02 — Chuyển M04 sang kiến trúc ba dịch vụ (25/10/2026)

- PR `port/m03-m05-m09-cham` vào nhánh tích hợp `migrate/w7-repo-goc`, xếp trên PR nền `port/m16-nen-w7` (W7-T01). Người làm: Sang. Chưa có verdict.
- Kết quả test ghi trong mô tả PR. Lý do: trên riêng nhánh tích hợp, test chưa chạy được cho tới khi mọi module đã chuyển, nên kết quả được đo bằng cách phủ tạm phần của người khác từ repo gốc.
- Không có số đo Speak & Improve trong code, test hay tài liệu của PR.
