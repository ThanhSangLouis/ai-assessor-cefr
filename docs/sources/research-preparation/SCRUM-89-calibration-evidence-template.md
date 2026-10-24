# SCRUM-89 — Mẫu ghi bằng chứng tập huấn và calibration

**Trạng thái mặc định:** `NOT_RUN` · **Đây là mẫu trống, không phải kết quả.**  
Không ghi tên, email, mã sinh viên, audio, transcript có PII, chữ ký hoặc raw restricted ratings vào bản Git. Khi thực hiện, đặt hồ sơ chi tiết ở vị trí được duyệt và chỉ ghi role ID/pseudonymous IDs cùng `approval_ref` tại đây.

## A. Thông tin phiên

| Trường | Giá trị điền sau khi được chốt/thực hiện |
|---|---|
| Activity ID | `[TBD]` |
| Loại phiên | `[DRY_RUN_4_6 / CALIBRATION_10]` |
| Ngày thực tế | `[NOT_RUN]` |
| Facilitator role ID | `[NOT_VERIFIED]` |
| Rater role IDs | `RATER-01: [NOT_VERIFIED]` · `RATER-02: [NOT_VERIFIED]` |
| Approved rubric/version | `[PENDING]` |
| Scoring-sheet/version | `[PENDING]` |
| Prompt/task version | `[PENDING]` |
| Sample-set version / pseudonymous manifest ref | `[PENDING]` |
| Sample audio rights/consent approval ref | `[PENDING]` |
| Blind-workflow verification ref | `[PENDING]` |
| Approval/GVHD reference | `[PENDING]` |
| Restricted evidence location/owner | `[PENDING — do not put personal path or identity here]` |

## B. Preflight checklist

| Check | State | Evidence reference / open item |
|---|---|---|
| Rubric and scoring rules frozen before the session | `NOT_VERIFIED` | `[TBD]` |
| Sample use rights and consent confirmed | `NOT_VERIFIED` | `[TBD]` |
| Answer key/consensus reviewed by authorized human | `NOT_VERIFIED` | `[TBD]` |
| Rater qualification, conflict and schedule checked | `NOT_VERIFIED` | `[TBD]` |
| AI output, identity and other rater scores hidden | `NOT_VERIFIED` | `[TBD]` |
| Restricted storage/access and retention confirmed | `NOT_VERIFIED` | `[TBD]` |
| Metric, threshold, missing-data rule and remediation approved | `NOT_VERIFIED` | `[TBD]` |

## C. Operational dry run — proposed 4–6 samples

Purpose: test rubric clarity, time, disagreement topics and workload. Do not use these rows as the 10-item calibration outcome unless the owner explicitly approves a documented design. Do not fill without an actual session.

| Pseudonymous sample ID | R1 completion/time | R2 completion/time | Clarity question or workload issue | Debrief action ID | Notes/ref (no PII) |
|---|---|---|---|---|---|
| DRY-01 | | | | | |
| DRY-02 | | | | | |
| DRY-03 | | | | | |
| DRY-04 | | | | | |
| DRY-05 | | | | | |
| DRY-06 | | | | | |

Dry-run summary after execution only: `NOT_RUN` · sample count: `[ ]` · median/summary time: `[ ]` · rubric issues: `[ ]` · fatigue/workload notes: `[ ]` · approved changes/action IDs: `[ ]`.

## D. Calibration — proposed 10 samples

Proposed source gate: weighted kappa ≥ 0.70. The metric definition, weighting, score/band unit and threshold require approval before data are opened. Store per-rater raw score sheets in restricted storage; enter approved aggregate result and evidence reference only after actual calculation.

| Pseudonymous calibration ID | R1 complete? | R2 complete? | Unrateable flag/reason code | Locked raw-sheet reference | Disagreement handled? |
|---|---|---|---|---|---|
| CAL-01 | | | | | |
| CAL-02 | | | | | |
| CAL-03 | | | | | |
| CAL-04 | | | | | |
| CAL-05 | | | | | |
| CAL-06 | | | | | |
| CAL-07 | | | | | |
| CAL-08 | | | | | |
| CAL-09 | | | | | |
| CAL-10 | | | | | |

### Chỉ số sau khi đã chạy

| Chỉ số | Quy tắc đã được duyệt trước phiên | Actual | Evidence ref |
|---|---|---|---|
| Weighted kappa (metric/weighting/unit ghi rõ) | `[PENDING APPROVAL]` | `NOT_EVALUATED` | `[NONE]` |
| ICC hoặc chỉ số khác nếu được duyệt | `[PENDING APPROVAL / N/A]` | `NOT_EVALUATED` | `[NONE]` |
| Số sample usable / excluded | `[PENDING RULE]` | `NOT_RUN` | `[NONE]` |
| Outcome theo threshold đã duyệt | `[PENDING APPROVAL]` | `NOT_EVALUATED` | `[NONE]` |
| Remediation / next activity | `[PENDING RULE]` | `NOT_RUN` | `[NONE]` |

## E. Kết luận và sign-off

| Vai trò | Kết luận sau khi xem evidence | Approval ref | Ngày thực tế |
|---|---|---|---|
| Facilitator | `NOT_RUN` | `[NONE]` | `[NONE]` |
| RATER-01 | `NOT_RUN` | `[NONE]` | `[NONE]` |
| RATER-02 | `NOT_RUN` | `[NONE]` | `[NONE]` |
| Owner/GVHD | `PENDING` | `[NONE]` | `[NONE]` |

Không đổi `NOT_RUN`, `NOT_VERIFIED` hoặc `NOT_EVALUATED` thành `PASS`/`READY` khi thiếu raw evidence và approval tương ứng. Không điền hồi tố.

