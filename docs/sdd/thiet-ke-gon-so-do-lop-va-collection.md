# Thiết kế gọn: mô hình nghiệp vụ 20 hộp và 18 collection

**Trạng thái:** thiết kế đã được chủ dự án chốt ngày 28/10/2026; code đang được chuyển theo (PR riêng, xếp sau PR làm xanh `main`).
**Người soạn:** Sang. **Sơ đồ:** [`diagrams/02_class.drawio`](diagrams/02_class.drawio) (sinh bằng `tools/gen_class_diagram.py`), bản trên Drive trang "So do lop".

## 1. Quyết định của chủ dự án (28/10/2026)

1. **Sơ đồ lớp chỉ giữ nghiệp vụ của bài toán:**
   - đánh giá kỹ năng nói theo CEFR có bằng chứng;
   - giảng viên duyệt;
   - vòng "đánh giá để học" (nhiệm vụ, bài học, ôn tập, lộ trình);
   - giao bài cho lớp.
2. **Thiết kế phải đúng chuẩn OOP và rã xuống code được.** Khoảng 20 hộp là mục tiêu, được chênh lệch, không ép số làm sai thiết kế.
3. **Không vẽ phần ngoài nghiệp vụ, nhưng vẫn giữ code của chúng:**
   - gói dịch vụ, giấy phép, đơn và lượt NetID;
   - công cụ nghiên cứu (chấm mù hai người, thực nghiệm phản hồi, nghe lại có đối chứng);
   - thuộc tính kỹ thuật (đăng nhập Google, đổi mật khẩu, hình đại diện, khoá bản ghi âm, tên mô hình ASR).
4. **Bỏ đồng thuận nghiên cứu.** Đợt xin giọng nói để huấn luyện đã qua, nên bỏ collection `consent`, lớp `Consent` và trang đồng thuận nhiều phiên bản. Chỉ giữ mốc `Account.termsAcceptedAt`, vì hệ thống vẫn lưu giọng nói, là dữ liệu cá nhân.
5. **Gộp collection MongoDB** theo mục 3, kèm migration dữ liệu.

## 2. Sơ đồ lớp: 37 → 20 hộp

**Bảy thực thể:** `Account`, `Task`, `Response`, `Lesson`, `LessonPath`, `ReviewItem`, `Classroom`. Mỗi thực thể là một tập dữ liệu có định danh.

**Chín lớp còn lại:**
- `Prompt`: lớp trừu tượng, cha của `Task` và `Step`;
- đối tượng giá trị: `Step`, `Mission`, `Assessment`, `Measure`, `Feedback`, `Word`, `Rating`, `Assignment`.

**Bốn kiểu liệt kê:** `Role`, `Status`, `Band`, `Criterion`.

| Trước | Sau | Lý do (OOP) |
| --- | --- | --- |
| `Task` và bước bài học (`Step` trong code) có chung lời đề, thời lượng, từ gợi ý, văn bản mẫu, giọng mẫu, ảnh, nhiệm vụ | lớp cha trừu tượng **`Prompt`**, hai lớp con `Task`, `Step` | kế thừa thay cho hai lớp lặp trường |
| `Consent` | `Account.termsAcceptedAt`, `Account.maySubmit()` | quyết định 4 |
| `Feature`, `CriterionCoverage`, `CriterionIndicator` | **`Measure`** (tên, giá trị, vị trí trong phân bố, lý do thiếu): dùng cho `Response.features` và `Assessment.criteria` | cùng là một phép đo có tên |
| `QcResult`, `Transcript`, `FeatureSet` | thuộc tính của `Response` (`durationMs`, `qcStatus`, `transcript`, `words`, `features`) | chỉ thuộc một bài nộp, không có hành vi riêng ngoài `valueOf()` |
| `Evidence`, `Comment`, `Priority` | **`Feedback`** (loại, tiêu chí, lời, đoạn thời gian) | cùng là nhận xét gắn bằng chứng |
| `ScoreInterval`, `AnalysisWindow` | `Assessment.intervalLow`, `intervalHigh`, `windowScores`, `isSingleBand()` | không có định danh, chỉ thuộc một `Assessment` |
| `Review` (giảng viên sửa điểm) | **`Rating`** trong `Response.ratings` | một lần người chấm một bài, bất biến |
| `PracticeResult`, `MissionCheck`, `MissionHit` | **`Mission`**: phần kết quả (`measured`, `met`, `hits: Word`) để tuỳ chọn | cùng một nhiệm vụ trước và sau khi đo |
| `WordMark` (đánh dấu từ trong bài học) | **`Word`** thêm `status`, `said`, `pattern` | cùng là một từ có mốc thời gian |
| lượt nói ở một bước bài học (`step_attempt`) | **`Response`** với `purpose`, `passed` | cùng là một lượt nói được thu âm và đo |
| lộ trình gợi ý (`learning_plan`) | `LessonPath.ownerId`, `goal` | lộ trình gợi ý là một lộ trình có chủ và mục tiêu |
| thành tựu, chuỗi ngày, nhắc việc | `Account.achievements`, `streakDays()`, `nudges()` | trạng thái và phép tính của người học |
| `EvidenceKind`, `QcStatus`, `TaskPart`, `TaskPurpose`, `MissionKind`, `ReasonCode` | ghi `str`, danh sách giá trị ở SRS | chỉ giữ bốn kiểu liệt kê cốt lõi |

## 3. Collection: 42 → 18

Collection gộp theo kho, độc lập với việc lớp nào được vẽ: các kho ngoài nghiệp vụ (gói dịch vụ, lượt, nghiên cứu) vẫn gộp như bảng dưới.


| Phần (database) | Trước | Sau | Cách gộp |
| --- | --- | --- | --- |
| identity (`aicefr`) | `account`, `account_identity`, `seen_marker`, `consent` | `account` | liên kết Google và dấu đã xem nhúng vào tài khoản; `consent` bỏ (quyết định 4) |
| | `auth_sessions` | `session` | giữ riêng: ghi nhiều, có hạn |
| | `audit_log` | `audit_log` | giữ: chỉ ghi thêm |
| dùng chung | `server_secret`, `app_config`, `billing_setting`, `lesson_meta` | `setting` | một lớp `SettingStore` (khoá, giá trị, phạm vi), một collection mỗi database |
| assessment (`aicefr`) | `task` | `task` | — |
| | `response`, `replay_label` | `response` | nhãn nghe lại nhúng vào bài |
| | `review_action`, `review_lock`, `review_session`, `machine_seen` | `review` | một document mỗi bài: khoá, các lần sửa, phiên duyệt, ai đã thấy điểm máy |
| | `rating_batch`, `rating_assignment`, `research_rating` | `rating_batch` | phiếu và điểm nhúng trong đợt |
| | `study`, `study_participant`, `study_survey` | `study` | người tham gia kèm khảo sát nhúng vào |
| | `classroom`, `class_member`, `assignment` | `classroom` | thành viên và bài giao nhúng vào |
| learning (`aicefr_learning`) | `lesson_path`, `lesson_unit` | `path` | chặng nhúng vào lộ trình |
| | `lesson`, `lesson_version`, `lesson_media` | `lesson` | phiên bản bất biến và media nhúng vào bài |
| | `step_attempt` | `attempt` | giữ riêng: số lượng lớn |
| | `review_item`, `achievement`, `learning_plan` | `learner` | một document mỗi người học |
| billing (`aicefr`) | `billing_order`, `billing_event` | `order` | sự kiện cổng nhúng vào đơn, chống trùng bằng chỉ mục duy nhất trên `events.event_id` |
| | `billing_license` | `license` | — |
| metering (`aicefr_metering`) | `usage_ledger` | `ledger` | giữ: sổ bút toán |
| | `credit_wallet`, `free_quota`, `credit_grant` | `wallet` | lượt miễn phí theo chu kỳ và các lần cộng lượt nhúng vào ví, chống cộng trùng bằng chỉ mục duy nhất trên `grants.source` + `grants.ref` |
| hệ thống | `schema_migrations` | `schema_migrations` | — |

Mọi kho kế thừa một lớp cha `MongoStore`. Lớp cha có sẵn thao tác cho document nhúng (thêm, sửa, xoá phần tử con theo khoá) để các kho không tự viết lại. Dữ liệu cũ được chuyển bằng một migration đánh số trong `storage/migrations.py`. Migration chạy lại được và không xoá collection cũ cho tới khi chuyển xong.

## 4. Khớp sơ đồ và code

Test đối chiếu sẽ đọc `02_class.drawio` và kiểm: mỗi hộp có một lớp cùng tên trong code, cùng thuộc tính và thao tác; `Task` và `Step` kế thừa `Prompt`. Phần ở quyết định 3 nằm ngoài phép đối chiếu.
