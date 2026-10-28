# Thiết kế gọn: sơ đồ lớp 24 hộp và 18 collection

**Trạng thái:** thiết kế đã được chủ dự án chốt ngày 28/10/2026; code đang được chuyển theo (PR riêng, xếp sau PR làm xanh `main`).
**Người soạn:** Sang. **Sơ đồ:** [`diagrams/02_class.drawio`](diagrams/02_class.drawio) (sinh bằng `tools/gen_class_diagram.py`), bản trên Drive trang "So do lop".

## 1. Quyết định của chủ dự án (28/10/2026)

1. Giảm số lớp và số collection xuống mức tối thiểu. Lớp dùng chung được thì gộp theo OOP. Sau đó code phải khớp đúng sơ đồ.
2. Gộp luôn các collection MongoDB, kèm migration dữ liệu.
3. Phần mở rộng không thuộc cam kết **bỏ khỏi sơ đồ nhưng giữ code**: gói dịch vụ và kênh NetID (`PriceList`, `TokenUsage`, `Action`), nghe lại D056 (`Moment`), nhắc việc D055 (`Nudge`).
4. **Bỏ đồng thuận nghiên cứu.** Đợt xin giọng nói để huấn luyện đã qua, nên bỏ collection `consent`, hộp `Consent` và trang đồng thuận nhiều phiên bản. Chỉ giữ mốc `Account.termsAcceptedAt`: người học đồng ý điều khoản trước lần nộp đầu tiên, vì hệ thống vẫn lưu giọng nói, là dữ liệu cá nhân.

## 2. Sơ đồ lớp: 37 → 24 hộp

| Trước | Sau | Lý do |
| --- | --- | --- |
| `Consent` («entity») | `Account.termsAcceptedAt`, `Account.maySubmit()` | quyết định 4 |
| `Feature`, `CriterionIndicator` | **`Measure`**, dùng chung cho `FeatureSet.items` và `CriterionResult.measures` | cùng là một phép đo có tên, giá trị, lý do thiếu, vị trí trong phân bố |
| `CriterionCoverage` | **`CriterionResult`** (độ phủ, lý do, các `Measure`) | một kết quả cho mỗi tiêu chí thay vì hai danh sách song song |
| `Evidence`, `Comment`, `Priority`, `EvidenceKind` | **`Feedback`** + **`FeedbackKind`** (`PAUSE`, `FILLER`, `LOW_CONFIDENCE_WORD`, `LEXICAL`, `COMMENT`, `PRIORITY`) | cùng là phản hồi gắn bằng chứng trên báo cáo |
| `ScoreInterval` | `Assessment.intervalLow`, `intervalHigh`, `intervalBands`, `intervalCoverage`, `isSingleBand()` | không có định danh, chỉ thuộc một `Assessment` |
| `Assessment` («entity») | «value object» trong `Response` | không có định danh riêng; sửa điểm được ghi bằng `Review` |
| `Review` («entity») | «value object» trong `Response.reviews` | mỗi lần sửa là một bản ghi bất biến |
| `PracticeResult`, `MissionCheck`, `MissionHit` | **`MissionResult`** trong `Response.missionResults`; chỗ máy nghe được là `Word` | dùng lại `Word` thay vì một lớp hai trường |
| `TaskPart` | `Task.part: str` | chỉ một lớp dùng, không có luật riêng |
| `PriceList`, `TokenUsage`, `Action`, `Moment`, `Nudge` | bỏ khỏi sơ đồ, code giữ | quyết định 3 |

Kết quả: 3 thực thể (`Account`, `Task`, `Response`), 12 đối tượng giá trị, 9 kiểu liệt kê, 29 quan hệ.

## 3. Collection: 42 → 18

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

Test đối chiếu sẽ đọc `02_class.drawio` và kiểm mỗi hộp có một lớp cùng tên, cùng thuộc tính và thao tác trong code. Phần mở rộng ở quyết định 3 nằm ngoài phép đối chiếu.
