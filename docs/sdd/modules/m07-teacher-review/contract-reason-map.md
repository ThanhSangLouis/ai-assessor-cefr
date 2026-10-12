# M07 — W2 Interface Pack: reason, state và audit contract

> **Trạng thái:** `CONTRACT_DRAFT` phục vụ review liên module ngày 28/09/2026.
> Artifact này được chuẩn bị theo yêu cầu trực tiếp của chủ dự án; không thay
> thế `03-specification.md`, không cấp verdict Phase 03/04/05, và không tự
> xác nhận M07 đã được nghiệm thu.

## Mục đích và boundary

M07 nhận một `ReviewCandidate` khi pipeline đã có một `Response` hợp lệ nhưng
kết quả cần người dạy xem xét. Candidate không mang audio, transcript, đường
dẫn blob hay PII. Quyết định cuối tạo `ReviewDecision` có audit record thật;
M06 chỉ được đặt `teacher_verified=true` khi xác minh được cặp decision/audit
đó qua repository M07.

`ResponseStatus` của M01/M08 là trạng thái kỹ thuật của bài nộp. `ReviewState`
là trạng thái nghiệp vụ của ca giảng viên; hai state machine không thay thế
nhau.

## Reason map

| Producer | Reason/status đầu vào | Route M07 | Kết quả mong đợi |
| --- | --- | --- | --- |
| M01 | `EMPTY_AUDIO`, `AUDIO_TOO_LARGE`, `UNSUPPORTED_AUDIO_FORMAT` | Không tạo candidate | Từ chối trước persistence; không có score/review. |
| M01/M08 | `PIPELINE_ENQUEUE_FAILED`, `REPORT_NOT_AVAILABLE` | Không tạo candidate tự động | M01 hiển thị failure/chờ report; operator xử lý pipeline. |
| M02 QC | `QC_SILENCE_REVIEW`, `QC_CLIPPING_REVIEW` | `PENDING` khi orchestrator phát hiện policy `REVIEW` | Giữ QC config/version trong provenance; không tự dispatch ASR khi policy M02 vẫn chờ review. |
| M02 QC | structural/policy `REJECT`, gồm `QC_EMPTY_AUDIO`, `QC_FORMAT_MISMATCH`, `QC_DECODE_FAILED`, `QC_SILENCE_REJECT`, `QC_CLIPPING_REJECT` | Không tạo candidate | Response `REJECTED`; không được biến lỗi input thành đánh giá giảng viên. |
| M03 | `ASR_FAILED`, `ASR_EMPTY_TRANSCRIPT`, `ASR_HALLUCINATION`, `ASR_VERSION_MISMATCH` | `PENDING` | Candidate lưu version ASR/decode và reason gốc. |
| M04 | `VAD_VERSION_MISMATCH`, `FEATURE_NOT_COMPUTABLE`, `TOO_FEW_WORDS`, `FEATURE_VERSION_MISMATCH` | `PENDING` | Candidate lưu feature/VAD version và không suy band mới. |
| M05 | `OUT_OF_DISTRIBUTION`, `SCORE_NEAR_BOUNDARY`, `MODEL_VERSION_MISSING`, `MODEL_ARTIFACT_INVALID` | `PENDING` | Candidate lưu model/band-map version và estimated band nullable. |
| M02 | `QC_MEASUREMENT_MISSING` | **Không route trong bản draft** | Cần owner M02/M03/M07 quyết định trước khi mở rộng `REVIEW_REASONS`; hiện không tự đoán policy. |

Code reference hiện hành: `src/aicefr/review/routing.py::REVIEW_REASONS`. Mọi
reason mới phải được đối chiếu với bảng này, Test ID M07-TEST-001 và owner của
producer trước khi đưa vào queue.

## Typed contract

```text
ReviewCandidate
  response_id: pseudonymous ID
  response_revision: revision của Response tại lúc route
  assessment_status: REVIEW_REQUIRED | NOT_EVALUATED
  proposed_band: A2 | B1 | B2 | null
  reasons: non-empty routed ReasonCode[]
  source_versions: non-empty map
  state: PENDING | IN_REVIEW | APPROVED | OVERRIDDEN | REJECTED
  revision: optimistic-lock token

ReviewDecision
  decision_id, audit_id: opaque 32-char IDs
  teacher_id: pseudonymous actor ID
  action: APPROVE | OVERRIDE | REJECT
  old_state, new_state, candidate_revision, recorded_at
  proposed_band, final_band, reason
```

`source_versions` tối thiểu nêu model, feature và band-map version khi candidate
đến từ M05. Dữ liệu version bị thiếu biểu diễn rõ là `unavailable`, không thay
bằng giá trị mặc định hoặc score giả.

## State và concurrency

| Current state | Action | Next state | Điều kiện |
| --- | --- | --- | --- |
| `PENDING` | claim | `IN_REVIEW` | teacher, đúng candidate revision và đúng response revision |
| `PENDING` / `IN_REVIEW` | `APPROVE` | `APPROVED` | proposed band tồn tại; client không gửi final band riêng |
| `PENDING` / `IN_REVIEW` | `OVERRIDE` | `OVERRIDDEN` | final band và reason không rỗng |
| `PENDING` / `IN_REVIEW` | `REJECT` | `REJECTED` | final band phải null |
| Final state | claim/decision | từ chối | Không mở lại hay ghi đè im lặng trong W3 scope |

Mọi mutation kiểm hai token: `ReviewCandidate.revision` và
`ResponseRecord.revision`. Nếu một teacher/pipeline đã đổi record trước đó,
request trả conflict, không ghi decision/audit mới. SQLite repository dùng
`BEGIN IMMEDIATE`, conditional update và audit append-only trong một
transaction.

## Authorization, audit và M06 integration

- M08 resolve session; chỉ `ActorRole.TEACHER` được list/claim/decide. Student
  nhận lỗi kiểm soát, không đổi candidate.
- Audit chỉ lưu actor pseudonym, action, response ID, timestamp và reason;
  không lưu audio, transcript, blob path hay token.
- M06 mặc định xuất `PROVISIONAL`, `teacher_verified=false`. `ReportService`
  yêu cầu `ReviewDecisionVerifier`; thiếu verifier hoặc decision không khớp
  persisted audit thì từ chối cập nhật report.
- Khi review action thành công, M06 lưu `TeacherFinalResult` riêng (final band,
  reason, audit ID). Overall AI vẫn là estimate tạm và không bị biến thành năm
  điểm tiêu chí.

## HTTP/UI surface W3

| Route | Quyền | Hành vi |
| --- | --- | --- |
| `GET /teacher/reviews` | teacher | Queue HTML tối thiểu, form claim/decision, chỉ pseudonymous ID/state/revision. |
| `GET /api/teacher/reviews` | teacher | Queue JSON. |
| `POST /api/teacher/reviews/{response_id}/claim` | teacher | Claim với `expected_revision`. |
| `POST /api/teacher/reviews/{response_id}/decision` | teacher | Approve/override/reject với contract ở trên. |
| `POST /teacher/reviews/{response_id}/{claim|decision}` | teacher | Form browser, redirect về queue. |

M01 surface tương ứng là `/student/upload`, `/api/student/responses`, status và
report owner-only. Adapter WSGI chấp nhận session M08 qua `Authorization:
Bearer` hoặc cookie `aicefr_session`; host/deployment phải bổ sung TLS,
cookie flags và session issuance theo owner M08.

## Impact và quyết định còn mở

1. Thay đổi hiện hành mở rộng M08 SQLite schema từ v1 lên v2: thêm
   `responses.status_reason`, `review_candidates` và `review_decisions`.
   **Thắng (M08 owner) cần review/đồng ý trước merge**; artifact này không tự
   thay verdict M08.
2. Chưa có rule gán teacher theo lớp/môn. Với phạm vi hiện có, role `teacher`
   là authorization boundary duy nhất; không được diễn giải thành phân quyền
   lớp học đã hoàn thành.
3. `ReportService` hiện có in-memory fixture repository. Khi đưa report vào
   persistent store, M06/M08 cần quyết định transaction chung hoặc
   outbox/reconciliation để xử lý trường hợp commit metadata và lưu report ở
   hai kho khác nhau.
4. Orchestrator M02→M05 phải gọi `ReviewService.add_candidate` sau khi tạo
   artifact/revision phù hợp; contract này không tự sinh candidate từ polling.

## Review requested

| Owner | Nội dung cần phản hồi | Trạng thái |
| --- | --- | --- |
| Thắng / M08 | schema v2, audit event, response revision, session/cookie host boundary | PENDING |
| Sang / M03–M05 | reason map, source version và semantic `NOT_EVALUATED` | PENDING |
| Nguyên / M01–M06–M07 | UI wording, report verification boundary, fixture/browser evidence | SELF-REVIEW PENDING Phase 07 |

## Actual boundary update — W4-N4, 12/10/2026

Các mô tả W2/W3 ở trên giữ vai trò snapshot contract DRAFT. Implementation tại base `3b2d2b7` đã có `report/sqlite.py`; report, decision/audit và candidate dùng cùng M08 transaction/connection. Coordinator gọi `build_and_store` và `add_candidate`; runtime không phụ thuộc polling để tạo candidate. Portal đã có claim/release/expiry và reopen kèm revision/lý do, nên câu “không mở lại trong W3 scope” không mô tả đầy đủ actual PARITY-001. Đây là đối chiếu hiện trạng, không tự duyệt contract mở rộng.

[M07-W4-20261012](evidence/M07-W4-20261012.md) đối chiếu Actor/Consent/Response/Blob/Audit và kiểm tra role, CAS, transaction rollback, lưu lịch sử trước/sau. Source M08 sửa binary read Windows theo quyền riêng Nguyên ngày 12/10; không claim Thắng/Sang đã approve. Review liên owner và formal phase vẫn `PENDING`.

D030/chấm mù kép chưa có implementation được duyệt; [W4-N6](evidence/W4-N6-giam-khao-va-phan-xu.md) chỉ chuẩn bị protocol. Không dùng màn hình teacher hiện tại để suy ra giám khảo được che điểm AI.
