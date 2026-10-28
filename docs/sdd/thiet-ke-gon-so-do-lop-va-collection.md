# Mô hình thực thể: 22 thực thể, 27 enum và 20 collection

**Trạng thái:** thiết kế theo chỉ dẫn của chủ dự án ngày 29/10/2026. Code chưa chuyển theo: migration gộp collection và lớp miền khớp sơ đồ là việc tiếp theo, làm ở PR riêng.
**Người soạn:** Sang.
**Sơ đồ:** [`diagrams/02_class.drawio`](diagrams/02_class.drawio), sinh bằng `tools/gen_class_diagram.py`. Bản trên Drive ở trang "So do lop".

## 1. Quyết định của chủ dự án

1. **Sơ đồ lớp chỉ chứa thực thể và enum** (29/10/2026).
   - Thực thể là lớp có định danh và vòng đời riêng, lưu thành một document.
   - Enum là tập giá trị đóng mà thuộc tính của thực thể lấy làm kiểu. Bổ sung theo chỉ dẫn cùng ngày.
   - Không có lớp trừu tượng hay đối tượng giá trị.
2. **Phủ hết nghiệp vụ của bài toán; số collection được linh hoạt** (29/10/2026). Thay cho quyết định ngày 28/10 "chỉ vẽ phần cốt lõi, khoảng 20 hộp". Bản 20 hộp trước đã bỏ sót gói dịch vụ, ví lượt, chấm mù, thực nghiệm, nhật ký kiểm toán và lượt luyện ở bước bài học.
3. **Bỏ đồng thuận nghiên cứu** (D058). Chỉ giữ `Account.termsAcceptedAt`.
4. **Band đủ sáu bậc A1 đến C2** (D059).

## 2. Quy tắc vẽ

- **Thuộc tính không có định danh** thuộc về thực thể sở hữu nó, ví dụ:
  - từ có mốc thời gian, phép đo, nhận xét gắn bằng chứng;
  - nhiệm vụ của đề, nhãn nghe lại, các lần cộng lượt.
- **Miền giá trị** là một enum, và thuộc tính lấy enum làm kiểu, ví dụ `role: Role`, `band: Band [0..1]`.
  - Enum đặt dưới cột của thực thể dùng nó. `Band`, `Criterion` dùng ở nhiều cột thì đặt dưới cột đề và bài nói.
  - Không vẽ đường phụ thuộc tới enum: tên kiểu trên thuộc tính đã nói quan hệ, và riêng `Band` có bảy lớp dùng.
  - Ba enum đặt tên khác code để khỏi nhầm: `ResponseStatus` (code: `Status`), `ServicePlan` (code: `Plan`, trùng nghĩa với `LearningPlan`), `MeteredAction` (code: `Action`).
- **Khoá ngoài** không ghi thành thuộc tính.
  - Quan hệ là đường nối, bội số ghi ở hai đầu đường.
  - Kim cương đặc là hợp thành: phần mất theo toàn thể.
  - Đường đậm không mũi tên là quan hệ nhiều–nhiều.
- **Chung trường giữa `Task` và `Step` thì chấp nhận lặp**, vì không có lớp cha. Hai lớp khác vòng đời:
  - đề có phiên bản lời đề;
  - bước nằm trong một phiên bản bài học.

## 3. Thực thể theo nghiệp vụ

| Nghiệp vụ | Thực thể | Ghi chú |
| --- | --- | --- |
| Tài khoản, điều khoản | `Account` | Thành tựu là thuộc tính. `maySubmit()` khi đã đồng ý điều khoản |
| Truy vết quyết định | `AuditEntry` | Ai làm gì, với đối tượng nào |
| Đề và bài nói | `Task`, `Response` | Kết quả chấm (điểm, band, khoảng tin cậy, nhận xét, nhãn nghe lại) là thuộc tính của `Response` |
| Giảng viên duyệt | `Review` | Mỗi lần đổi điểm hoặc band, kèm lý do |
| Chấm mù hai người | `RatingBatch`, `Rating` | Phiếu và điểm của giám khảo là một `Rating`; đã thấy điểm máy hay chưa là thuộc tính |
| Thực nghiệm phản hồi | `Study`, `Participant` | Câu trả lời khảo sát là thuộc tính của người tham gia |
| Lớp học | `Classroom`, `Assignment` | Thành viên là quan hệ nhiều–nhiều với `Account` |
| Lộ trình, bài học | `LessonPath`, `Unit`, `Lesson`, `Step` | Phiên bản đã xuất bản và media là thuộc tính của `Lesson` |
| Luyện ở bước bài học | `StepAttempt` | Một lượt nói ở một bước, ghi phiên bản bài học |
| Ôn tập ngắt quãng | `ReviewItem` | Hộp Leitner, ngày đến hạn |
| Lộ trình gợi ý | `LearningPlan` | Với giảng viên còn nối tới lộ trình nháp đã lưu |
| Gói dịch vụ | `Order`, `License` | Sự kiện cổng thanh toán nhúng vào đơn |
| Tính lượt | `Wallet`, `LedgerEntry` | Lượt miễn phí theo chu kỳ và các lần cộng lượt nhúng vào ví; mỗi bài một bút toán |

### Enum

| Nhóm | Enum |
| --- | --- |
| Tài khoản | `Role` |
| Đề và bài nói | `Band` (A1–C2), `Criterion`, `TaskPurpose`, `TaskPart`, `MissionKind`, `ResponseStatus`, `ReasonCode` |
| Chấm mù, thực nghiệm | `BatchStatus`, `UnscorableReason`, `StudyStatus` |
| Bài học, ôn tập, lộ trình gợi ý | `PathStatus`, `Topic`, `StepKind`, `Stage`, `Strictness`, `ReviewKind`, `Audience` |
| Gói dịch vụ | `OrderKind`, `OrderStatus`, `Gateway`, `ServicePlan`, `PlanFeature`, `LicenseSource`, `LicenseState` |
| Tính lượt | `MeteredAction`, `LedgerState` |

Không vẽ các enum chỉ dùng **bên trong** bước tính, không là kiểu của thuộc tính nào được lưu:

- `QcStatus` (kết quả kiểm chất lượng âm thanh, đã thể hiện qua `ResponseStatus` và `ReasonCode`);
- `EvidenceKind`, `Pattern` (chi tiết trong từng dòng nhận xét);
- `WordStatus`, `GapStatus`, `Op` (chi tiết trong kết quả một lượt luyện);
- `Provenance`, `RecommendationBasis` (nhãn hiển thị trên báo cáo và gợi ý).

### Rà lại khi thêm enum

Đối chiếu tập giá trị với code đã lộ ra chỗ sơ đồ trước thiếu hoặc lệch, nay đã sửa:

- thiếu `RatingBatch.status`, `Task.part`, `Response.reasonCodes`, `LedgerEntry.action`, `Order.events`, `Step.strictness`, `Step.stage()`;
- lệch giá trị: `Study.status` là RUNNING/SURVEY/CLOSED (không phải OPEN/CLOSED), `ReviewItem.kind` là WORD/TALK, `LearningPlan.audience` là STUDENT/TEACHER, `License.source` là TRIAL/ORDER/KEY;
- `License.isActive()` đổi thành `state(today): LicenseState` (có hạn gia hạn GRACE), thêm `allows(feature)`.

## 4. Collection: 42 → 20

Mỗi thực thể gốc là một collection. Phần có định danh nhưng sống trong thực thể gốc được nhúng vào document của gốc: `Unit` trong lộ trình, `Step` trong bài học, `Rating` trong đợt chấm, `Participant` trong thực nghiệm, `Assignment` trong lớp.

| Phần | Collection sau | Gộp từ |
| --- | --- | --- |
| identity | `account` | `account`, `account_identity`, `seen_marker`, `achievement` |
| | `audit_log` | `audit_log` |
| assessment | `task` | `task` |
| | `response` | `response`, `replay_label` |
| | `review` | `review_action`, `review_lock`, `review_session` |
| | `rating_batch` | `rating_batch`, `rating_assignment`, `research_rating`, `machine_seen` |
| | `study` | `study`, `study_participant`, `study_survey` |
| | `classroom` | `classroom`, `class_member`, `assignment` |
| learning | `path` | `lesson_path`, `lesson_unit` |
| | `lesson` | `lesson`, `lesson_version`, `lesson_media` |
| | `attempt` | `step_attempt` |
| | `review_item` | `review_item` |
| | `learning_plan` | `learning_plan` |
| billing | `order` | `billing_order`, `billing_event` |
| | `license` | `billing_license` |
| metering | `wallet` | `credit_wallet`, `free_quota`, `credit_grant` |
| | `ledger` | `usage_ledger` |
| kỹ thuật, không vẽ | `session` | `auth_sessions` |
| | `setting` | `server_secret`, `app_config`, `billing_setting`, `lesson_meta` |
| | `schema_migrations` | `schema_migrations` |

`consent` đã bỏ ở D058 nên không có trong bảng.

Dữ liệu cũ chuyển bằng migration đánh số trong `storage/migrations.py`. Migration chạy lại được, và không xoá collection cũ cho tới khi chuyển xong.

## 5. Khớp sơ đồ và code

Test đối chiếu sẽ đọc `02_class.drawio` và kiểm ba điều:

1. Mỗi hộp có một lớp miền cùng tên trong code, cùng thuộc tính và thao tác.
2. Mỗi thực thể gốc có đúng một collection.
3. Mỗi enum trùng tập giá trị với enum tương ứng trong code (không phân biệt hoa thường).

Phần kỹ thuật ở mục 4 nằm ngoài phép đối chiếu.
