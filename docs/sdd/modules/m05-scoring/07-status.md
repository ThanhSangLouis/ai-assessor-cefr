# M05 — Status

| Mục | Trạng thái |
| --- | --- |
| Lifecycle | proposed |
| Phase hiện tại | 09 — Acceptance APPROVED: W2 (27/09/2026) và M05-TASK-004 (03/10/2026) |
| Requirement | [01-requirement.md](01-requirement.md) · v0.2 · **APPROVED** 26/09/2026 |
| Research mode | **`RUN`** (chọn tại Phase 01); [02-research.md](02-research.md) review cùng Phase 03 |
| Specification | [03-specification.md](03-specification.md) · v0.2 · **APPROVED** 26/09/2026 |
| Test Plan | [04-test-plan.md](04-test-plan.md) · v0.2 · **APPROVED** 26/09/2026 |
| Plan & Tasks | [05-plan.md](05-plan.md), [06-tasks.md](06-tasks.md) · v0.2 · **APPROVED** 26/09/2026; task READY/BLOCKED theo dependency — xem 06-tasks.md |
| Implementation | M05-TASK-002, M05-TASK-001 đã implement (Claude, theo yêu cầu chủ dự án); evidence [M05-EV-001, M05-EV-002](evidence/evidence-manifest.md). M05-TASK-004 implement 03/10/2026, evidence [M05-EV-003](evidence/evidence-manifest.md) |
| Review | Phase 07 A1 **APPROVED** 26/09/2026; A2 (M05-TASK-004) **APPROVED** 03/10/2026, [review-log](reviews/review-log.md) |
| Final Verification | Phase 08 [M05-EV-P08](evidence/evidence-manifest.md) trên main 74afca9 — **APPROVED** 27/09/2026; [M05-EV-P08-A2](evidence/evidence-manifest.md) trên main ae72d57 — **APPROVED** 03/10/2026 |
| Acceptance | Phase 09 **APPROVED** 27/09/2026 (W2) và 03/10/2026 (M05-TASK-004) — xong scope M05 của W3 |
| Prompt hiện hành | NONE ISSUED; base revision/fingerprint NOT_SET |

## Phase 01 record

```text
PHASE RECORD ID: M05-01-A1
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
PHASE RECORD ID: M05-03-A1
PHASE: 03 — Specification
SUBJECT: 02-research.md v0.2 + 03-specification.md v0.2
CHECKS: FR/AC trace; success/invalid/boundary/failure/recovery; security/privacy;
  accessibility N/A có lý do; fact/inference/option tách riêng; không tự quyết sản phẩm
OPEN: M05-O-001 boundary_margin (khuyến nghị 0,5); M05-O-002 bài dài (khuyến nghị không chia cửa sổ W2); M05-O-003 provenance lệch (khuyến nghị NOT_EVALUATED)
CODEX CHECK RESULT: PASS về cấu trúc; còn OPEN nêu trên
CODEX RECOMMENDATION: RECOMMEND APPROVAL sau khi user chốt OPEN
USER VERDICT: APPROVED — chốt các OPEN theo khuyến nghị
VERIFIED/APPROVED BY: User (Sang)
USER VERDICT AT: 26/09/2026
NEXT ACTION: Phase 04 — Test Plan
```

## Phase 04 record

```text
PHASE RECORD ID: M05-04-A1
PHASE: 04 — Test Plan
SUBJECT: 04-test-plan.md v0.2 — 21 unit + 1 integration; giá trị vàng trên artifact thật
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
PHASE RECORD ID: M05-05-A2
PHASE: 05 — Plan & Task Readiness
SUBJECT: 05-plan.md v0.2 + 06-tasks.md v0.2 — task 001, 002, 004; TASK-003 rút lại
CHECKS: trace FR/AC → Test → Task PASS; boundary/data flow PASS; rủi ro/rollback/Clean Code PASS;
  task nhỏ, vùng file rõ PASS; runtime/convention PASS (pyproject + CI trên main a92fafe);
  dependency sẵn sàng PASS cho task READY (kiểm lại 26/09/2026)
TASKS: TASK-002, 001, 004 đề xuất READY
DECISION: P05-D-001 = artifact ngoài repo (AICEFR_MODEL_DIR, hash ghim) — user chốt 26/09/2026
CODEX CHECK RESULT: PASS cho task đề xuất READY
CODEX RECOMMENDATION: RECOMMEND APPROVAL — chỉ phát prompt Antigravity cho task READY
USER VERDICT: APPROVED — cho các task READY; task BLOCKED chờ đủ dependency
VERIFIED/APPROVED BY: User (Sang)
USER VERDICT AT: 26/09/2026
NEXT ACTION: Phase 06 — M05-TASK-002 (Claude implement theo yêu cầu của chủ dự án)
```

## Phase 07 record

```text
PHASE RECORD ID: M05-07-A1
PHASE: 07 — Implementation Review
SUBJECT: M05-TASK-002, 001 (SCRUM-27, 28)
CHECKS: verify evidence (base/diff/test/coverage) PASS; checklist code + test PASS sau correction
FINDINGS: 07-A1-01 MAJOR, 07-A1-03 MINOR, 07-A1-06 NIT — MAJOR/NIT đã sửa; MINOR còn mở là follow-up
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
PHASE RECORD ID: M05-08-A1
PHASE: 08 — Final Verification
SUBJECT: M05-TASK-002, 001 trên main 74afca9, fingerprint 7bc236e3a3df1890…
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

**SCOPE ID/ROOT:** M05 / `docs/sdd/modules/m05-scoring/` — chỉ kết luận cho module này.

| Phase | Record | Verdict |
| --- | --- | --- |
| 01 Requirement | M05-01-A1 | APPROVED 26/09/2026 |
| 03 Specification | M05-03-A1 | APPROVED 26/09/2026 |
| 04 Test Plan | M05-04-A1 | APPROVED 26/09/2026 |
| 05 Plan & Tasks | M05-05-A2 | APPROVED 26/09/2026 |
| 07 Review | 07-M05-A1 (reviews/review-log.md) | APPROVED 26/09/2026 |
| 08 Final Verification | M05-08-A1 (M05-EV-P08) | APPROVED 27/09/2026 |

| AC | Nội dung | Evidence cuối | Kết quả |
| --- | --- | --- | --- |
| M05-AC-001 | Thiếu evidence không có score; Interaction luôn insufficient_evidence | M05-TEST-004, 005–008, 014 (M05-EV-001/002, EV-P08) | ĐẠT |
| M05-AC-002 | Artifact hợp lệ → overall tái lập + 5 coverage, không score riêng tiêu chí | M05-TEST-001–003, 015–020 (giá trị vàng tính lại từ artifact theo công thức Spec) | ĐẠT |
| M05-AC-003 | Ba test lệch riêng asr_model, vad_name, feature_order | M05-TEST-009–013 | ĐẠT |

**Regression / chất lượng trên main 74afca9:** 133 passed (có artifact), 123 passed + 10 skipped (CI), 0 failed; coverage branch 99 %; TP-D-001 không bị hạ, không thêm exclusion.

3/3 AC đạt. M05-TASK-004 (integration M04→M05, M05-TEST-022) còn READY, thuộc W3, không chặn AC nào. Follow-up 07-A1-03 (reason QC) là SCRUM-45 của M02.

```text
PHASE RECORD ID: M05-09-A1
PHASE: 09 — Acceptance
CODEX CHECK RESULT: PASS
CODEX RECOMMENDATION: RECOMMEND APPROVAL — nghiệm thu scope M05 cho W2
USER VERDICT: APPROVED — nghiệm thu scope M05 cho W2
VERIFIED/APPROVED BY: User (Sang)
USER VERDICT AT: 27/09/2026
```

## Đợt A2 — M05-TASK-004 (W3, 03/10/2026)

```text
PHASE RECORD ID: M05-07-A2
PHASE: 07 — Implementation Review
SUBJECT: M05-TASK-004 (SCRUM-29), review record 07-M05-A2
CHECKS: verify evidence M05-EV-003 PASS; checklist code + test PASS
FINDINGS: không có
DEVIATIONS: Test Plan v0.2.1 (dòng 022) — cần user chấp nhận
CODEX CHECK RESULT: PASS
CODEX RECOMMENDATION: RECOMMEND APPROVAL — kèm chấp nhận Test Plan v0.2.1
USER VERDICT: APPROVED — chấp nhận Test Plan v0.2.1
VERIFIED/APPROVED BY: User (Sang)
USER VERDICT AT: 03/10/2026
NEXT ACTION: Phase 08 trên main ae72d57 (ae72d57b03de0ae9333e8b549484d026feb3177c)
```

```text
PHASE RECORD ID: M05-08-A2
PHASE: 08 — Final Verification
SUBJECT: M05-TASK-004 trên main ae72d57 (ae72d57b03de0ae9333e8b549484d026feb3177c), fingerprint 8835acf872d8c0ab…
CHECKS: 0 failed trên final head; 11 skipped đều cần artifact thật (P05-D-001) và PASS khi có artifact
  (203 passed); `aicefr.scoring` 100 % line/branch; M05-TEST-022 ↔ tests/scoring/test_integration_features.py;
  CI run 37113044170 trên ae72d57, Python 3.11: 192 passed, 11 skipped
CODEX CHECK RESULT: PASS
CODEX RECOMMENDATION: RECOMMEND APPROVAL
USER VERDICT: APPROVED — M05-TASK-004 chuyển Verified
VERIFIED/APPROVED BY: User (Sang)
USER VERDICT AT: 03/10/2026
NEXT ACTION: Phase 09 — Acceptance
```

| AC | Evidence bổ sung đợt A2 | Kết quả |
| --- | --- | --- |
| M05-AC-001 | Không đổi | ĐẠT |
| M05-AC-002 | M05-TEST-022: FeatureSet thật từ M04 đi qua scorer, ngoài phân bố thì không có điểm (M05-EV-003, EV-P08-A2) | ĐẠT |
| M05-AC-003 | M05-TEST-022 (b): VAD lệch đi từ M04 sang M05 vẫn không cho band | ĐẠT |

**Error analysis W3 (SCRUM-53):** mục "Error analysis W3" trong [02-research.md](02-research.md); quyết định M05-O-004 = Option A cho W4, chốt B hay C ở W5–W6 cùng metric Bản cam kết.

```text
PHASE RECORD ID: M05-09-A2
PHASE: 09 — Acceptance
CODEX CHECK RESULT: PASS — 3/3 AC đạt; M05-TASK-001, 002, 004 Verified; TASK-003 WITHDRAWN
CODEX RECOMMENDATION: RECOMMEND APPROVAL — nghiệm thu M05-TASK-004, đóng scope M05 của W3
USER VERDICT: APPROVED — nghiệm thu M05-TASK-004; đóng scope M05 của W3
VERIFIED/APPROVED BY: User (Sang)
USER VERDICT AT: 03/10/2026
```

**Lý do trạng thái:** chủ dự án yêu cầu chuẩn bị đầy đủ tài liệu W2 để review một lượt. Việc có file nháp không vượt checkpoint tuần tự của skill SDD; các phase vẫn phải được duyệt theo thứ tự trước implementation/handoff.


- [Prompt Log](prompts/prompt-log.md): chưa phát prompt Antigravity; mọi implementation do Claude làm theo yêu cầu chủ dự án, ghi trong Evidence Manifest.
- [Evidence Manifest](evidence/evidence-manifest.md): evidence Phase 06 và Phase 08 của từng đợt.
- [Review Records](reviews/review-log.md): Phase 07 A1 (26/09/2026), A2 (03/10/2026).
- [Kế hoạch W2](../../../plan/week-02.md); [nguồn tài liệu](../../../sources/README.md).

## Ghi chú W4-S4 (SCRUM-51) — 11/10/2026

Repo nộp bài đang public, còn license S&I không cho công bố thống kê suy ra từ dữ liệu khi chưa được CUP&A duyệt. Đã gỡ khỏi tài liệu và test của M03/M05:
- hệ số và khoảng huấn luyện của `asr_conf_mean`;
- metric CV (PCC, RMSE, `train_n`) và bảng xác suất sai band tính từ chúng;
- ba giá trị vàng của M05-TEST-001.

Test giờ tính kỳ vọng từ chính artifact (ngoài repo) theo công thức Spec, nên vẫn kiểm đúng như cũ: `tests/scoring/test_scorer.py` có artifact thì 3/3 PASS. Các số đã gỡ lưu ở tài liệu nội bộ của chủ module.

Lịch sử Git còn các số này; theo kế hoạch W4, không viết lại lịch sử khi chưa có quyết định của nhóm và GVHD. Cách giảm rủi ro chính vẫn là chuyển repo sang private (W4-T1, Thắng).

## W7-S02 — Chuyển M05 sang kiến trúc ba dịch vụ (25/10/2026)

- PR `port/m03-m05-m09-cham` vào nhánh tích hợp `migrate/w7-repo-goc`, xếp trên PR nền `port/m16-nen-w7` (W7-T01). Người làm: Sang. Chưa có verdict.
- Kết quả test ghi trong mô tả PR. Lý do: trên riêng nhánh tích hợp, test chưa chạy được cho tới khi mọi module đã chuyển, nên kết quả được đo bằng cách phủ tạm phần của người khác từ repo gốc.
- Không có số đo Speak & Improve trong code, test hay tài liệu của PR.
