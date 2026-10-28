# Mô hình thực thể: 22 thực thể, 12 enum và 17 collection

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
  - Enum đặt trong khung của thực thể dùng nó. `Band`, `Criterion`, `TaskPurpose` dùng ở nhiều khung thì đặt trong khung Đánh giá.
  - Thực thể nối tới enum nó dùng bằng đường phụ thuộc UML: nét đứt, mũi tên mở ở phía enum. Có 22 đường như vậy, riêng `Band` có bảy lớp dùng.
  - Hai enum đặt tên khác code để khỏi nhầm: `ResponseStatus` (code: `Status`), `ServicePlan` (code: `Plan`, trùng nghĩa với `LearningPlan`).
- **Khoá ngoài** không ghi thành thuộc tính.
  - Quan hệ là đường nối, bội số ghi ở hai đầu đường.
  - Kim cương đặc là hợp thành: phần mất theo toàn thể.
  - Đường đậm không mũi tên là quan hệ nhiều–nhiều.
- **Khung theo phần nghiệp vụ.** Sáu khung, mỗi khung một nhóm thực thể:
  - hàng trên: Nghiên cứu, Định danh, Thương mại;
  - hàng dưới: Lớp học, Đánh giá, Học tập.
  - Định danh ở giữa hàng trên vì `Account` nối tới mọi khung. Đánh giá ở giữa hàng dưới vì bốn khung còn lại đều nối vào bài nói hoặc `Band`.
  - Đường đi vuông góc, do `tools/zone_layout.py` tìm:
    - không đi xuyên hộp;
    - không chồng lên đường khác hay chạy sát viền khung;
    - đi giữa hai khung thì theo hành lang, không cắt ngang khung thứ ba.
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

### Enum: chỉ giữ cái điều khiển nghiệp vụ

Một tập giá trị được vẽ thành enum khi code **rẽ nhánh theo nó**: phân quyền, chấm điểm, chuyển trạng thái, tính tiền.

| Nhóm | Enum giữ lại (12) |
| --- | --- |
| Tài khoản | `Role` |
| Chấm điểm | `Band` (A1–C2), `Criterion`, `TaskPurpose`, `ResponseStatus` |
| Thực nghiệm | `StudyStatus` |
| Bài học | `PathStatus`, `StepKind` (quyết định cách chấm một bước) |
| Gói dịch vụ, tính lượt | `OrderKind`, `OrderStatus`, `ServicePlan`, `LedgerState` |

Bỏ khỏi sơ đồ, kèm cách ghi thay:

| Bỏ | Ghi thay | Lý do |
| --- | --- | --- |
| `ReasonCode` (25 mã), `MissionKind`, `TaskPart`, `Topic` | `str` | Chi tiết hoặc dữ liệu tham chiếu, không đổi luồng nghiệp vụ |
| `UnscorableReason`, `Gateway`, `LicenseSource`, `Strictness`, `ReviewKind` | `str` | Như trên |
| `BatchStatus` (mở/đóng) | `closed: bool` | Hai trạng thái là một cờ |
| `MeteredAction` | `TaskPurpose` | Trùng nghĩa: chấm hay luyện |
| `Audience` | `Role` | Trùng giá trị STUDENT/TEACHER |
| `Stage` | bỏ | Suy ra từ `StepKind` |
| `PlanFeature`, `LicenseState` | `License.isActive()` | Suy ra từ gói và ngày, không lưu |

Code vẫn giữ các enum này để kiểm đầu vào. Sơ đồ chỉ không vẽ chúng.

### Rà lại khi thêm enum

Đối chiếu tập giá trị với code đã lộ ra chỗ sơ đồ trước thiếu hoặc lệch, nay đã sửa:

- thiếu `RatingBatch.closed`, `Task.part`, `Response.reasonCodes`, `LedgerEntry.action`, `Order.events`, `Step.strictness`;
- lệch giá trị: `Study.status` là RUNNING/SURVEY/CLOSED (không phải OPEN/CLOSED), `ReviewItem.kind` là WORD/TALK, `LearningPlan.audience` là STUDENT/TEACHER, `License.source` là TRIAL/ORDER/KEY;
- thuộc tính `Step.strictness` ghi `str`.

## 4. Collection: 42 → 17

**Nguyên tắc:** mỗi aggregate root là một collection. Phần hợp thành (kim cương đặc) nằm trong document của gốc, trừ khi số phần tăng không giới hạn.

- Nhúng vào gốc:
  - `Unit` trong lộ trình, `Step` trong bài học;
  - `Rating` trong đợt chấm, `Participant` trong thực nghiệm, `Assignment` trong lớp;
  - `Review` trong bài nói;
  - `Wallet` trong tài khoản.
- Giữ collection riêng dù là phần hợp thành hoặc chỉ là tham chiếu:
  - `ledger`: mỗi bài nói thêm một bút toán, mảng nhúng sẽ lớn mãi.
  - `lesson`: giảng viên sửa và xuất bản từng bài độc lập; nhúng vào lộ trình thì hai người sửa hai bài sẽ ghi đè cùng một document.
  - `attempt`, `review_item`: tăng theo mỗi lượt luyện.

| Phần | Collection | Gộp từ |
| --- | --- | --- |
| identity | `account` | `account`, `account_identity`, `seen_marker`, `achievement`, `credit_wallet`, `free_quota`, `credit_grant` |
| | `audit_log` | `audit_log` |
| assessment | `task` | `task` |
| | `response` | `response`, `replay_label`, `review_action`, `review_lock`, `review_session` |
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
| metering | `ledger` | `usage_ledger` |
| kỹ thuật, không vẽ | `session` | `auth_sessions` (giữ riêng vì có chỉ mục TTL tự xoá phiên hết hạn) |
| | `system` | `server_secret`, `app_config`, `billing_setting`, `lesson_meta`, `schema_migrations` |

Không gộp thêm:

- `license` vào `order`: license dùng thử hoặc từ mã kích hoạt không có đơn nào.
- `learning_plan` vào `account`: lộ trình gợi ý của giảng viên còn nối tới lộ trình nháp, không thuộc riêng một tài khoản học.

`consent` đã bỏ ở D058 nên không có trong bảng.

Dữ liệu cũ chuyển bằng migration đánh số trong `storage/migrations.py`. Migration chạy lại được, và không xoá collection cũ cho tới khi chuyển xong.

## 5. Khớp sơ đồ và code

Test đối chiếu sẽ đọc `02_class.drawio` và kiểm ba điều:

1. Mỗi hộp có một lớp miền cùng tên trong code, cùng thuộc tính và thao tác.
2. Mỗi aggregate root có đúng một collection, phần nhúng thì không có collection riêng.
3. Mỗi enum trên sơ đồ trùng tập giá trị với enum tương ứng trong code (không phân biệt hoa thường).

Phần kỹ thuật ở mục 4 nằm ngoài phép đối chiếu.
