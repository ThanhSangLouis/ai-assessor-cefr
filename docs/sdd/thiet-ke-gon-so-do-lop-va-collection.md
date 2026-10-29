# Mô hình thực thể: 23 thực thể, 12 enum và 17 collection nghiệp vụ

**Trạng thái:** thiết kế theo chỉ dẫn của chủ dự án ngày 29/10/2026. Code đã chuyển theo ở D060 (gộp collection, migration 7); `tests/test_diagrams.py` và `tests/test_d060_collections.py` giữ hai bên khớp nhau.
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
5. **Quan hệ thể hiện qua thuộc tính** (29/10/2026, chỉnh lại bản trước).
   - Bản trước bỏ hết thuộc tính tham chiếu nên có đường không có trường nào giữ, ví dụ kim cương `RatingBatch` → `Rating` trong khi `RatingBatch` không có trường nào kiểu `Rating`.
   - Bản này mỗi đường có đúng một thuộc tính ở lớp giữ quan hệ.

## 2. Quy tắc vẽ

- **Thuộc tính không có định danh** thuộc về thực thể sở hữu nó, ví dụ:
  - từ có mốc thời gian, phép đo, nhận xét gắn bằng chứng;
  - nhiệm vụ của đề, nhãn nghe lại, các lần cộng lượt.
- **Miền giá trị** là một enum, và thuộc tính lấy enum làm kiểu, ví dụ `role: Role`, `band: Band [0..1]`.
  - Enum đặt trong khung của thực thể dùng nó. `Band`, `Criterion`, `TaskPurpose` dùng ở nhiều khung thì đặt trong khung Đánh giá.
  - Thực thể nối tới enum nó dùng bằng đường phụ thuộc UML: nét đứt, mũi tên mở ở phía enum. Có 22 đường như vậy, riêng `Band` có bảy lớp dùng.
  - Hai enum đặt tên khác code để khỏi nhầm: `ResponseStatus` (code: `Status`), `ServicePlan` (code: `Plan`, trùng nghĩa với `LearningPlan`).
- **Quan hệ qua thuộc tính.** Mỗi đường giữa hai thực thể có đúng một thuộc tính ở lớp giữ quan hệ, mang kiểu lớp kia.
  - Hợp thành (kim cương đặc ở lớp toàn thể): lớp toàn thể giữ danh sách phần và lưu chung một document, ví dụ `RatingBatch.ratings: Rating`, `Lesson.steps: Step`. Phần mất theo toàn thể.
  - Kết hợp (mũi tên mở về lớp được trỏ tới): lớp giữ lưu mã của bên kia, ví dụ `Response.speaker: Account`, `Rating.response: Response`.
  - Nhiều–nhiều (đường đậm, không mũi tên): `Classroom.members: Account`, không có lớp trung gian.
  - Bội số ở đầu xa của đường chính là bội số của thuộc tính. Trong hộp chỉ ghi tên và kiểu, bội số ghi trên đường.
  - Không vẽ quan hệ suy ra được qua lớp khác. Ví dụ đơn mua lượt cộng vào ví của chính `placedBy`, nên không có đường `Order` → `Wallet`.
  - `check_relations()` trong bộ sinh dừng lại nếu một đường thiếu thuộc tính, hoặc một thuộc tính kiểu thực thể thiếu đường.
- **Hợp thành không vượt database.** Code có ba database (D051): core, learning, metering.
  - `Wallet` ở metering nên là thực thể riêng trỏ tới `Account`, không nhúng vào tài khoản.
  - Thành tựu ở learning nên là thực thể `Achievement`, không là thuộc tính của `Account`.
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
| Tài khoản, điều khoản | `Account` | Danh tính đăng nhập ngoài và dấu đã xem là thuộc tính. `maySubmit()` khi đã đồng ý điều khoản |
| Truy vết quyết định | `AuditEntry` | Ai làm gì, với đối tượng nào |
| Đề và bài nói | `Task`, `Response` | Kết quả chấm (điểm, band, khoảng tin cậy, nhận xét, nhãn nghe lại) là thuộc tính của `Response` |
| Giảng viên duyệt | `Review` | Mỗi lần đổi điểm hoặc band, kèm lý do |
| Chấm mù hai người | `RatingBatch`, `Rating` | Phiếu và điểm của giám khảo là một `Rating`; đã thấy điểm máy hay chưa là thuộc tính |
| Thực nghiệm phản hồi | `Study`, `Participant` | Câu trả lời khảo sát là thuộc tính của người tham gia |
| Lớp học | `Classroom`, `Assignment` | Thành viên là quan hệ nhiều–nhiều với `Account` |
| Lộ trình, bài học | `LessonPath`, `Unit`, `Lesson`, `Step` | Phiên bản đã xuất bản và media là thuộc tính của `Lesson` |
| Luyện ở bước bài học | `StepAttempt` | Một lượt nói ở một bước, ghi phiên bản bài học |
| Ôn tập ngắt quãng | `ReviewItem` | Hộp Leitner, ngày đến hạn |
| Thành tựu | `Achievement` | Đạt lúc nào, đã xem chưa. Ở database learning |
| Lộ trình gợi ý | `LearningPlan` | Với giảng viên còn nối tới lộ trình nháp đã lưu |
| Gói dịch vụ | `Order`, `License` | Sự kiện cổng thanh toán nhúng vào đơn |
| Tính lượt | `Wallet`, `LedgerEntry` | Lượt miễn phí theo chu kỳ và các lần cộng lượt nhúng vào ví; mỗi bài một bút toán trỏ tới ví và bài nói |

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

## 4. Collection: 42 → 17 nghiệp vụ + 2 kỹ thuật

**Nguyên tắc:**
- Mỗi aggregate root là một collection.
- Phần hợp thành nằm trong document của gốc.
- Không gộp qua ranh giới database (D051) và không gộp thành mảng lớn mãi.

| Database | Collection | Gộp từ | Nhúng |
| --- | --- | --- | --- |
| core | `account` | `account`, `account_identity`, `seen_marker` | danh tính, dấu đã xem |
| | `audit_log` | `audit_log` | |
| | `task` | `task` | |
| | `response` | `response`, `replay_label`, `review_action`, `review_lock`, `review_session`, `machine_seen` | `Review`, nhãn nghe lại, khoá duyệt, lượt mở bài, người đã xem điểm máy |
| | `rating_batch` | `rating_batch`, `rating_assignment`, `research_rating` | `Rating` (phiếu và điểm là một) |
| | `study` | `study`, `study_participant`, `study_survey` | `Participant` |
| | `classroom` | `classroom`, `class_member`, `assignment` | thành viên, `Assignment` |
| | `order` | `billing_order`, `billing_event` | sự kiện cổng thanh toán |
| | `license` | `billing_license` | |
| learning | `path` | `lesson_path`, `lesson_unit` | `Unit` |
| | `lesson` | `lesson`, `lesson_version`, `lesson_media` | `Step`, các phiên bản, media |
| | `attempt` | `step_attempt` | |
| | `review_item` | `review_item` | |
| | `achievement` | `achievement` | |
| | `learning_plan` | `learning_plan` | |
| metering | `wallet` | `credit_wallet`, `free_quota`, `credit_grant` | lượt miễn phí theo chu kỳ, các lần cộng |
| | `ledger` | `usage_ledger` | |
| kỹ thuật, mỗi database | `session` (chỉ core) | `auth_sessions` | |
| | `system` | `server_secret`, `app_config`, `billing_setting`, `lesson_meta`, `schema_migrations`, `_counters` | |

`audit_log` có ở cả ba database vì mỗi phần ghi nhật ký vào database của mình. Đó vẫn là một collection, một thực thể.

**Không gộp thêm, kèm lý do:**

| Cặp | Vì sao không |
| --- | --- |
| `wallet`, `ledger` vào `account` | Khác database (metering), và mỗi bài nói thêm một bút toán. |
| `lesson` vào `path` | Mỗi bài giữ mọi phiên bản đã xuất bản nên lớn dần. Lượt luyện, ôn tập, lộ trình gợi ý đều tìm bài theo mã bài. |
| `attempt`, `review_item`, `achievement` vào một chỗ | Ba thực thể khác vòng đời và đều tăng theo từng lượt luyện. Không có document học viên nào ở database learning để nhúng vào. |
| `learning_plan` vào `account` | Khác database. Lộ trình gợi ý của giảng viên còn nối tới lộ trình nháp. |
| `license` vào `order` | License dùng thử hoặc từ mã kích hoạt không có đơn nào. |
| `session` vào `account` | Phiên cần chỉ mục TTL tự xoá khi hết hạn. TTL không áp được lên phần tử của mảng. |

`consent` đã bỏ ở D058 nên không có trong bảng.

Dữ liệu cũ chuyển bằng migration 7 trong `storage/migrations.py`:
- chạy lại được;
- chép xong một collection cũ thì mới xoá nó.

## 5. Khớp sơ đồ và code

Test đối chiếu sẽ đọc `02_class.drawio` và kiểm ba điều:

1. Mỗi thực thể có đúng một collection như mục 4; phần hợp thành không có collection riêng.
2. Mỗi đường giữa hai thực thể có thuộc tính ở lớp giữ (`check_relations()`).
3. Mỗi enum trên sơ đồ trùng tập giá trị với enum tương ứng trong code (không phân biệt hoa thường).

Phần kỹ thuật ở mục 4 nằm ngoài phép đối chiếu.
