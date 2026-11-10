# Mô hình thực thể: 24 thực thể, 9 enum và 19 collection nghiệp vụ

**Trạng thái:**
- Thiết kế theo chỉ dẫn của chủ dự án ngày 29/10/2026; code chuyển theo ở D060 (gộp collection, migration 7).
- Ngày 03/11/2026 cập nhật theo các thay đổi đến D090: gỡ chấm mù và thực nghiệm (D078), gỡ gói dịch vụ (D075), tách `ReviewSession` (D082), tách `Payment` (D084), thêm `WordDrill` (D089) và `DrillPassage` (D090).
- Hai bên được giữ khớp bằng `tests/test_diagrams.py` và `tests/test_class_diagram_in_code.py` (mục 5).

**Người soạn:** Sang.
**Sơ đồ:** [`diagrams/02_class.drawio`](diagrams/02_class.drawio), sinh bằng `tools/gen_class_diagram.py`. Bản trên Drive ở trang "So do lop".

## 1. Quyết định của chủ dự án

1. **Sơ đồ lớp chỉ chứa thực thể và enum** (29/10/2026).
   - Thực thể là lớp có định danh và vòng đời riêng, lưu thành một document.
   - Enum là tập giá trị đóng mà thuộc tính của thực thể lấy làm kiểu.
   - Không có lớp trừu tượng hay đối tượng giá trị.
2. **Phủ hết nghiệp vụ của bài toán; số collection được linh hoạt** (29/10/2026). Quyết định này thay cho quyết định ngày 28/10 "chỉ vẽ phần cốt lõi, khoảng 20 hộp".
3. **Band đủ sáu bậc A1 đến C2** (D059).
4. **Quan hệ thể hiện qua thuộc tính** (29/10/2026). Mỗi đường có đúng một thuộc tính ở lớp giữ quan hệ.
5. **Các thay đổi sau đó:**
   - D058, D064: bỏ đồng thuận nghiên cứu, rồi bỏ hẳn bước đồng ý điều khoản; `Account` không còn `termsAcceptedAt`.
   - D075: gỡ gói dịch vụ của trường. Bỏ `License`, `ServicePlan`, `OrderKind`, `Assignment`; `Order` chỉ còn là đơn nạp lượt.
   - D078: gỡ chấm mù kép và thực nghiệm phản hồi. Bỏ `RatingBatch`, `Rating`, `Study`, `Participant`, `StudyStatus`.
   - D082: việc duyệt bài tách khỏi bài nộp thành `ReviewSession`.
   - D084: đơn nạp lượt tách thành `Order` (phần mua) và `Payment` (phần cổng thanh toán).
   - D089: `WordDrill`, từ máy nghe chưa rõ được nói lại. `ReviewItem` thêm `drill`; `ReviewItem.lesson` thành 0..1.
   - D090: `DrillPassage`, đoạn đọc viết quanh 3–5 từ đang luyện dở. `PriceList` thêm `passageRuns`; `MeteredAction` thêm `DRILL_PASSAGE`.
   - D094: tính lượt cho bản ghi trong lộ trình học. `PriceList` thêm `lessonMinuteRuns`, `lessonFreePerDay`, `lessonDailyCap`; `Wallet` thêm `lessonDay`, `lessonUsed`, `lessonFreeUsed`; `LedgerEntry` thêm `day`, `freeSlot`; `MeteredAction` thêm `LESSON`.

## 2. Quy tắc vẽ

- **Thuộc tính không có định danh** thuộc về thực thể sở hữu nó, ví dụ:
  - kết quả chấm, nhãn nghe lại;
  - các lượt nói lại của một từ, các lần đọc một đoạn;
  - các lần cộng lượt vào ví.
- **Miền giá trị** là một enum, và thuộc tính lấy enum làm kiểu, ví dụ `role: Role`, `overallBand: Band`.
  - Enum đặt trong khung của thực thể dùng nó. `Band`, `Criterion`, `ResponseStatus` đặt trong khung Đánh giá.
  - Thực thể nối tới enum nó dùng bằng đường phụ thuộc UML: nét đứt, mũi tên mở ở phía enum.
- **Quan hệ qua thuộc tính.** Mỗi đường giữa hai thực thể có đúng một thuộc tính ở lớp giữ quan hệ, mang kiểu lớp kia.
  - **Hợp thành** (kim cương đặc ở lớp toàn thể): lớp toàn thể giữ danh sách phần và lưu chung một document. Phần mất theo toàn thể. Ví dụ `Lesson.steps: List<Step>`, `Response.reviews: List<Review>`.
  - **Kết hợp** (mũi tên mở về lớp được trỏ tới): lớp giữ lưu mã của bên kia. Ví dụ:
    - `Response.speaker: Account`;
    - `WordDrill.response: Response`;
    - `DrillPassage.words: List<WordDrill>`.
  - **Nhiều–nhiều** (đường đậm, không mũi tên): `Classroom.members: List<Account>`, không có lớp trung gian.
  - **Bội số** ở đầu xa của đường chính là bội số của thuộc tính. Trong hộp chỉ ghi tên và kiểu (`List<X>` khi đầu xa nhiều hơn một), bội số ghi trên đường.
  - **Không vẽ quan hệ suy ra được qua lớp khác.** Ví dụ đơn nạp lượt cộng vào ví của chính `createdBy`, nên không có đường `Order` → `Wallet`.
  - `check_relations()` trong bộ sinh dừng lại nếu một đường thiếu thuộc tính, hoặc một thuộc tính kiểu thực thể thiếu đường.
- **Hợp thành không vượt database.** Code có ba database (D051): core, learning, metering.
  - `Wallet` ở metering nên là thực thể riêng trỏ tới `Account`, không nhúng vào tài khoản.
  - `WordDrill` ở learning nên trỏ tới `Response` (core) bằng mã, không nhúng vào bài nói.
- **Khung theo phần nghiệp vụ.** Năm khung:
  - hàng trên: Định danh, Thương mại;
  - hàng dưới: Lớp học, Đánh giá, Học tập.
  - Đường đi vuông góc, do `tools/zone_layout.py` tìm: không đi xuyên hộp, không chồng lên đường khác, đi giữa hai khung thì theo hành lang.
- **Chung trường giữa `Task` và `Step` thì chấp nhận lặp**, vì không có lớp cha. Hai lớp khác vòng đời: đề có phiên bản lời đề, bước nằm trong một phiên bản bài học.

## 3. Thực thể theo nghiệp vụ

| Nghiệp vụ | Thực thể | Ghi chú |
| --- | --- | --- |
| Tài khoản | `Account` | Danh tính đăng nhập ngoài, dấu đã xem, mã email và nhắc học là thuộc tính |
| Truy vết quyết định | `AuditEntry` | Ai làm gì, với đối tượng nào; mỗi database một nhật ký |
| Đề và bài nói | `Task`, `Response` | Kết quả chấm (điểm, band, khoảng tin cậy, nhận xét, lý do) và nhãn nghe lại là thuộc tính của `Response` |
| Giảng viên duyệt | `Review`, `ReviewSession` | `Review`: mỗi lần đổi điểm hoặc band, kèm lý do, nằm trong bài nói. `ReviewSession` (D082): ai đang giữ quyền duyệt, tới lúc nào, các lần mở bài |
| Bản nâng cấp và sổ cụm từ | `CoachUpgrade`, `PhraseCard` | Bài nói viết lại một band cao hơn (D069), các cụm từ của nó ôn theo hộp (D070) |
| Lớp học | `Classroom` | Giảng viên và thành viên là quan hệ nhiều–nhiều với `Account` |
| Lộ trình, bài học | `LessonPath`, `Unit`, `Lesson`, `Step` | Phiên bản đã xuất bản và media là thuộc tính của `Lesson` |
| Luyện ở bước bài học | `StepAttempt` | Một lượt nói ở một bước, ghi phiên bản bài học |
| Ôn tập ngắt quãng | `ReviewItem` | Hộp Leitner, ngày đến hạn; từ của một bước bài học hoặc (D089) của một `WordDrill` |
| Luyện lại từ máy nghe chưa rõ | `WordDrill`, `DrillPassage` | `WordDrill` (D089): một từ của một bài nói và các lượt nói lại. `DrillPassage` (D090): một đoạn đọc viết quanh 3–5 `WordDrill`, kèm các lần đọc |
| Thành tựu | `Achievement` | Đạt lúc nào, đã xem chưa |
| Lộ trình gợi ý | `LearningPlan` | Với giảng viên còn nối tới lộ trình nháp đã lưu |
| Nạp lượt | `Order`, `Payment` | `Order` (D084): phần mua. `Payment`: phần cổng thanh toán, kèm sự kiện của cổng |
| Tính lượt | `Wallet`, `LedgerEntry`, `PriceList` | Lượt miễn phí theo chu kỳ và các lần cộng lượt nằm trong ví. Mỗi lần chấm hay mỗi lần AI viết là một bút toán. Bảng giá có phiên bản (D078) |

### Enum: chỉ giữ cái điều khiển nghiệp vụ

Một tập giá trị được vẽ thành enum khi code **rẽ nhánh theo nó**: phân quyền, chấm điểm, chuyển trạng thái, tính tiền.

| Nhóm | Enum (9) |
| --- | --- |
| Tài khoản | `Role` |
| Chấm điểm | `Band` (A1–C2), `Criterion`, `ResponseStatus` |
| Bài học | `PathStatus`, `StepKind` (quyết định cách chấm một bước) |
| Nạp lượt, tính lượt | `OrderStatus`, `LedgerState`, `MeteredAction` (chấm, luyện, bản nâng cấp, bản soạn bài, đoạn đọc) |

Bỏ khỏi sơ đồ, kèm cách ghi thay:

| Bỏ | Ghi thay | Lý do |
| --- | --- | --- |
| `ReasonCode`, `QcStatus`, `EvidenceKind`, `Provenance` | `Response.reasonCodes: List<str>`; phần còn lại nằm trong báo cáo chấm | Chi tiết của kiểm tra âm thanh và bằng chứng, không đổi luồng nghiệp vụ |
| `Topic`, `MissionKind`, `Pattern` | `str` | Dữ liệu tham chiếu: chủ đề, kiểu nhiệm vụ luyện, mẫu lỗi phát âm của người Việt (D039) |
| `Strictness` | `Step.strictness: str` | Mức chặt của một bước, chỉ đổi ngưỡng đo |
| `WordStatus`, `GapStatus`, `Op` | không thành thuộc tính | Kết quả đo của một lượt, nằm trong `StepAttempt.result` |
| `Stage` | bỏ | Suy ra từ `StepKind` |

Code vẫn dùng các enum này; sơ đồ chỉ không vẽ chúng.

## 4. Collection: 19 nghiệp vụ + 3 kỹ thuật

**Nguyên tắc:**
- Mỗi aggregate root là một collection.
- Phần hợp thành nằm trong document của gốc.
- Không gộp qua ranh giới database (D051), và không gộp thành mảng lớn mãi.

| Database | Collection | Thực thể | Nhúng | Từ đâu |
| --- | --- | --- | --- | --- |
| core | `account` | `Account` | danh tính, dấu đã xem, mã email | D060 gộp `account`, `account_identity`, `seen_marker` |
| | `audit_log` | `AuditEntry` | | |
| | `task` | `Task` | | |
| | `response` | `Response` | `Review`, `CoachUpgrade` (kèm `PhraseCard`), nhãn nghe lại, báo cáo chấm | D060 gộp `response`, `replay_label`, `review_action` |
| | `review_session` | `ReviewSession` | các lần mở bài | D082 tách từ `response` |
| | `classroom` | `Classroom` | giảng viên, thành viên | D060; `Assignment` gỡ ở D075 |
| | `order` | `Order` | | D060 gộp `billing_order` |
| | `payment` | `Payment` | sự kiện cổng thanh toán | D084 tách từ `order` |
| learning | `path` | `LessonPath` | `Unit` | D060 gộp `lesson_path`, `lesson_unit` |
| | `lesson` | `Lesson` | `Step`, các phiên bản, media | D060 gộp `lesson`, `lesson_version`, `lesson_media` |
| | `attempt` | `StepAttempt` | | |
| | `review_item` | `ReviewItem` | | |
| | `achievement` | `Achievement` | | |
| | `learning_plan` | `LearningPlan` | | |
| | `word_drill` | `WordDrill` | các lượt nói lại (tối đa 20) | D089, migration 18 |
| | `drill_passage` | `DrillPassage` | các lần đọc (tối đa 20) | D090, migration 19 |
| metering | `wallet` | `Wallet` | lượt miễn phí theo chu kỳ, các lần cộng | D060 gộp `credit_wallet`, `free_quota`, `credit_grant` |
| | `ledger` | `LedgerEntry` | | |
| | `price_list` | `PriceList` | các phiên bản trước | D078 |
| kỹ thuật | `session` (chỉ core) | | | Phiên đăng nhập |
| | `system` (mỗi database) | | | Cấu hình, bộ đếm, migration |
| | `push_subscription` (chỉ core) | | | Đăng ký nhận thông báo của trình duyệt; D088 để ở ERD, không ở sơ đồ lớp |

Mỗi database có `audit_log` riêng vì mỗi phần ghi nhật ký vào database của mình. Đó vẫn là một collection, một thực thể.

**Không gộp thêm, kèm lý do:**

| Cặp | Vì sao không |
| --- | --- |
| `wallet`, `ledger` vào `account` | Khác database (metering), và mỗi lần chấm thêm một bút toán. |
| `review_session` vào `response` | Chủ dự án chọn tách việc duyệt thành lớp riêng (D082). `Response` còn bài nộp, kết quả chấm và các lần duyệt; mỗi bài nhiều nhất một phiên (duy nhất `response_id`), nên giành quyền duyệt vẫn nguyên tử. |
| `payment` vào `order` | Chủ dự án chọn tách (D084): `Order` giữ phần mua, `Payment` giữ phần cổng thanh toán, mỗi đơn một thanh toán. |
| `lesson` vào `path` | Mỗi bài giữ mọi phiên bản đã xuất bản nên lớn dần. Lượt luyện, ôn tập, lộ trình gợi ý đều tìm bài theo mã bài. |
| `attempt`, `review_item`, `achievement` vào một chỗ | Ba thực thể khác vòng đời và đều tăng theo từng lượt luyện. Không có document học viên nào ở database learning để nhúng vào. |
| `word_drill` vào `response` | Khác database: bài nói ở core, việc luyện ở learning. |
| `drill_passage` vào `word_drill` | Một đoạn đọc viết cho 3–5 từ, có thể của nhiều bài nói khác nhau. |
| `learning_plan` vào `account` | Khác database. Lộ trình gợi ý của giảng viên còn nối tới lộ trình nháp. |
| `session` vào `account` | Phiên cần chỉ mục TTL tự xoá khi hết hạn. TTL không áp được lên phần tử của mảng. |

## 5. Khớp sơ đồ và code

Sơ đồ là thiết kế mà code theo. Các kiểm tra sau chạy trong CI:

1. **`check_relations()`** trong bộ sinh: mỗi đường giữa hai thực thể có thuộc tính ở lớp giữ, và mỗi thuộc tính kiểu thực thể có đường.
2. **`tests/test_diagrams.py`:**
   - lớp nào vẽ cũng có trong code;
   - thuộc tính nào cũng có kiểu;
   - enum nào cũng đủ giá trị;
   - hợp thành nào cũng có trường chứa thật và chỉ một chủ;
   - bội số khớp giới hạn code ép.
3. **`tests/test_class_diagram_in_code.py`** đối chiếu tới từng thuộc tính. Mỗi thuộc tính và thao tác vẽ trên một thực thể phải tìm được trong code theo một trong ba cách:
   - **cùng tên**, viết kiểu snake case, trên lớp của thực thể (`wordIndex` → `WordDrill.word_index`);
   - **tham chiếu lưu bằng mã**: sơ đồ vẽ `learner: Account`, code giữ `account_id`; `wallet: Wallet` là `user_ref`;
   - **trường của document hay của báo cáo** mà lớp không khai:
     - `Account.emailVerified` là khoá `email_verified` kho tài khoản ghi;
     - `Response.transcript` là `Transcript.text` trong báo cáo chấm;
     - `PriceList.history` là các phiên bản trước trong `price_list`.

   Hai cách sau được liệt kê trong bảng `ELSEWHERE` của test, và bảng được kiểm cả hai chiều: dòng cho thuộc tính đã không còn trên sơ đồ, hay trỏ tới chỗ không có, cũng làm test đỏ. Test còn kiểm mọi collection nghiệp vụ trong `docs/db/schema_core.json` thuộc một thực thể trên sơ đồ; chỉ ba collection kỹ thuật ở mục 4 được ngoại lệ.
