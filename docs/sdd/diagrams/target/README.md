# Sơ đồ lớp thiết kế đích v3

Tệp: `02_class_v3.drawio`. Sinh bằng:

```bash
.venv/bin/python tools/gen_class_diagram.py --spec v3
```

Đặc tả nằm ở `tools/class_spec_v3.py`. Muốn sửa hình thì sửa đặc tả rồi sinh lại, đừng kéo thả trên app.diagrams.net rồi lưu đè: `tests/test_target_design.py` sẽ báo tệp lệch đầu ra của bộ sinh.

## Hiện trạng và thiết kế đích

| Tệp | Vai trò | Kiểm bằng |
| --- | --- | --- |
| `../02_class.drawio` | **Hiện trạng**: mô tả đúng mã đang chạy trong repo này | `tests/test_diagrams.py`: lớp vẽ ra phải có trong mã, giá trị enum và bội số phải khớp mã |
| `target/02_class_v3.drawio` | **Thiết kế đích**: mã phải chuyển theo | `tests/test_target_design.py`: đúng cú pháp UML, kiểu nào được nhắc tên thì phải được vẽ, mỗi bộ phận của hợp thành chỉ có một thể sở hữu, tệp đúng là đầu ra của bộ sinh |

Thiết kế là nguồn chuẩn, mã đi theo. Khi mã đã chuyển xong sang v3 thì v3 thay `02_class.drawio`, đặc tả v3 thành đặc tả mặc định của bộ sinh, và thư mục này được xóa.

Trên Google Drive, v3 nằm ở tệp `AI.drawio`, trang **"So do lop v3"**. Hai trang "So do lop" và "So do lop (hoan thien)" được giữ làm lịch sử.

## Chín quyết định (chủ dự án duyệt ngày 02/10/2026)

Nguồn: đối chiếu sơ đồ "So do lop (hoan thien)" với mã repo nộp bài `thanglb2005/ai-assessor-cefr` @ `2b428ce`. Đợt đối chiếu tìm 130 chỗ lệch; agent kiểm chứng phản biện không bác bỏ chỗ nào. Nguyên tắc chung: quyết định nào đã duyệt qua SDD của module và có lý do kỹ thuật thì đưa vào thiết kế, không bắt mã quay lại cách cũ.

| # | Quyết định | Lý do |
| --- | --- | --- |
| D1 | Đổi tên theo spec đã duyệt: `Account` → `Actor`; `Consent` → `ConsentRecord`; `Response` → `ResponseRecord`; `QcResult`/`QcStatus` → `QCResult`/`QCStatus`; `Feature` → `FeatureValue`; `items` → `values`; `reason` → `missingReason`; `accountId` → `actorId`/`participantId`; `overall06` → `overallScore` | SDD M02/M04/M05/M08 đã APPROVED và test plan đã dùng các tên này. Đổi hình rẻ hơn đổi spec + test plan, mà hình vẫn khớp mã khi hội đồng đối chiếu |
| D2 | `QCResult` chứa `measurements: List<QCMeasurement>`, mỗi phép đo có giá trị hoặc `missingReason`. Bỏ `snrDb` và mã `LOW_SNR`. Tần số lấy mẫu và số kênh không lưu trên `QCResult`: bộ giải mã kiểm (`QC_SAMPLE_RATE_LIMIT`, `QC_TOO_MANY_CHANNELS`) rồi chuẩn hóa về 16 kHz mono | M02 APPROVED chỉ đo thời lượng, tỉ lệ im lặng, tỉ lệ vỡ tiếng; phép đo thiếu là rỗng kèm lý do, không bao giờ là 0 |
| D3 | Giữ hợp thành: `ResponseRecord` chứa `QCResult`, `Transcript`, `FeatureSet`, `Assessment`, `DiagnosticReport` (mỗi cái 0..1) | Vòng đời của mọi kết quả xử lý gắn với bài nộp. Mã được phép lưu từng phần theo `response_id`; đó là cách cài đặt, không đổi quan hệ |
| D4 | Value object `Provenance` (model, SHA-256 artifact, feature, band map, calibration, `trainedWith`, `unitOfInference`, `scoredAt`) thay các trường phẳng trên `Assessment` | M05 APPROVED. Gom nguồn gốc điểm về một chỗ, có hash artifact |
| D5 | Thêm `Interaction` (`level` luôn rỗng, `scoreStatus = "insufficient_evidence"`) | M05-AC-001 APPROVED. Nói rõ vì sao chỉ chấm 5/6 tiêu chí CEFR với bài độc thoại |
| D6 | Bỏ `AnalysisWindow`, `windowSpread`, `SCORE_AGGREGATED` | M05-O-002 APPROVED: không chia cửa sổ. Kế hoạch nâng cấp không làm chấm theo cửa sổ (chấm theo phiên là mục kéo dãn, chưa cam kết nên chưa vẽ) |
| D7 | Thêm aggregate `DiagnosticReport` sở hữu `Evidence`, `Comment`, `Priority`, `EvidenceIssue`, `TeacherFinalResult`; báo cáo **tham chiếu** `Assessment` (0..1 : 1) thay vì chép lại điểm | Tách "chấm" (M05) khỏi "giải thích" (M06). `teacherVerified` chỉ nằm ở `Assessment`, một nguồn duy nhất |
| D8 | Một bảng `ReasonCode` duy nhất (27 mã). Mức độ (REVIEW/REJECT) nằm ở `status`, không nằm trong tên mã | Bỏ các cặp `QC_SILENCE_REVIEW`/`_REJECT`; đổi `QC_DURATION_LIMIT`/`QC_TOO_SHORT` thành `AUDIO_TOO_LONG`/`AUDIO_TOO_SHORT`; `PIPELINE_ENQUEUE_FAILED` thành `PROCESSING_INTERRUPTED`; thêm `CONSENT_MISSING`; bỏ các mã không còn ai phát (`LOW_SNR`, `WRONG_SAMPLE_RATE`, `ASR_LOW_CONFIDENCE`, `SCORE_AGGREGATED`) |
| D9 | `Transcript` theo M03: `status: AsrStatus`, `reasons`, `asrModel: str [0..1]` (weight lạ thì rỗng kèm `ASR_VERSION_MISMATCH`) và các trường nguồn gốc. Bỏ `hasWordTimestamps` (timestamp luôn bắt buộc) và `isVerbatim` (văn bản luôn giữ nguyên lời nói) | M03 APPROVED |

Các bổ sung đi kèm, cùng một nguồn: `CriterionCoverage.features`, `FeatureValue.unit`, nguồn gốc VAD/ASR trên `FeatureSet`, `AssessmentStatus`, `OutOfRangeFeature`, `ReviewCandidate`, `ReviewState`, `ReviewAction`, `EvidenceSource`, `CommentTemplate` (nhận xét chỉ sinh từ mẫu cố định).

## Bổ sung D022 (chủ dự án duyệt ngày 03/10/2026): Trust Layer và lá chắn hợp lệ

| Phần tử | Nội dung | Lý do |
| --- | --- | --- |
| `ScoreInterval` (VO, `Assessment.interval [0..1]`) | Khoảng điểm `[low, high]`, tập band giao với khoảng, mức phủ danh nghĩa `1 − α`, phương pháp (`cv+`), phiên bản hiệu chỉnh | Thay ngưỡng "gần ranh giới ±0,5" đặt tay bằng khoảng có bảo đảm thống kê (CV+, Barber và cs. 2021). Tập ≥2 band thì gắn `SCORE_NEAR_BOUNDARY` (giữ mã cũ, đổi nghĩa thành "khoảng tin cậy chạm hơn một band"). α mặc định 0,10 |
| `CriterionIndicator` (VO, `Assessment.indicators`), `Assessment.weakestCriteria` | Vị trí (phân vị) của từng phép đo trong phân bố huấn luyện, gắn với tiêu chí; tiêu chí có chỉ báo thấp nhất | Đáp ứng "5 tiêu chí khả dụng" của đề cương mà **không** bịa điểm tiêu chí: mô hình chỉ học nhãn overall |
| `Transcript.language`, `languageProbability` | Ngôn ngữ do bộ nhận dạng phát hiện | Whisper ép tiếng Anh có thể "dịch" lời tiếng Việt thành chữ tiếng Anh rồi được chấm |
| `Task.topicKeywords` | Từ khóa chủ đề tiếng Anh của từng đề; rỗng với đề mở (P5) | Đề bài trong hệ thống viết bằng tiếng Việt, sinh viên nói tiếng Anh: không so lời nói với đề được, phải so với từ khóa. Kiểm tra đọc lại đề chỉ chạy với đề tiếng Anh |
| `ReasonCode` + `LANGUAGE_NOT_ENGLISH`, `OFF_TOPIC_SUSPECTED`, `PROMPT_COPY_SUSPECTED` (30 mã) | Ba cờ chuyển giảng viên | Ngôn ngữ khác thì không chấm; lạc đề / đọc lại đề thì giữ điểm, không trừ, chỉ chuyển giảng viên |

## Bổ sung D023 (chủ dự án duyệt ngày 06/10/2026): chế độ Luyện tập

Hiện thực vòng phản hồi ở mục 2.5 đề cương: sau khi biết mình đang ở đâu, người học có một nhiệm vụ ngắn để luyện đúng chỗ yếu, và biết ngay mình đã làm được gì. Cách tổ chức tham khảo các ứng dụng học hiện nay (bài học ngắn theo lộ trình, mục tiêu ngày, chuỗi ngày có ngày dự phòng, ôn lại bài chưa xong), nhưng bỏ những gì nghiên cứu cho thấy có hại (bảng xếp hạng, trừ điểm theo lỗi, chuỗi ngày cứng).

| Phần tử | Nội dung | Lý do |
| --- | --- | --- |
| `Task.purpose: TaskPurpose` (`ASSESSMENT`, `PRACTICE`) | Đề luyện tập là một `Task`, không phải lớp riêng: cùng bảng, cùng `promptVersion`, cùng đường nộp bài | Một bài luyện vẫn là một bản ghi giọng nói có đồng thuận, vẫn qua QC, VAD, nhận dạng; tách lớp thì phải nhân đôi cả đường nộp bài |
| `Task.criterion`, `Task.band`, `Task.tips`, `Task.referenceText` | Mỗi đề luyện một tiêu chí ở một band; đề phát âm có đoạn văn mẫu để đọc to | Mô hình chỉ học nhãn overall, nên không có điểm tiêu chí để hứa; thứ luyện được là hành vi đo được |
| `Mission` (VO, `Task.missions`) | Một mục tiêu đọc được trước khi nói: loại, ngưỡng, câu mô tả, danh sách từ (chỉ với `USE_WORDS`) | Luật đo và lời hứa phải là một; người học biết chính xác máy sẽ đếm gì |
| `MissionKind` (7 giá trị) | Thời lượng nói, khoảng lặng dài nhất, dùng từ trong danh sách, số từ khác nhau, động từ quá khứ, câu điều kiện, đọc to khớp đoạn mẫu | Mỗi loại là một phép đếm người học tự kiểm lại được khi nghe bản ghi |
| `PracticeResult` (VO, `ResponseRecord.practice [0..1]`) | Kết quả một lần luyện; `completed` suy ra từ các mục tiêu | Bài luyện **không** có `Assessment`: nhiệm vụ luyện nằm ngoài phân bố bài thi mô hình đã học, và sai số mô hình lớn hơn mức tiến bộ thật giữa hai lần luyện |
| `MissionCheck`, `MissionHit` | Đo được thì có số và chỗ trong bản ghi (từ đã dùng kèm giây, khoảng lặng kèm giây, từ chưa nghe ra); không đo được thì rỗng kèm `ReasonCode` | Cùng nguyên tắc với `FeatureValue`: "chưa đo được" không bao giờ thành "chưa hoàn thành" |

Không vẽ: mục tiêu ngày, chuỗi ngày và gợi ý nhiệm vụ tiếp theo là **giá trị suy ra** từ các lần luyện (`practice/streak.py`, `practice/recommend.py`), không lưu thành đối tượng.

## Bổ sung D025–D036 (vẽ lại ngày 08/10/2026)

Các tính năng làm sau D023 đã có trong mã nhưng chưa có trên sơ đồ. Bản này thêm phần miền của chúng; thiết kế vẫn là nguồn chuẩn, nên tên thuộc tính theo quy ước của sơ đồ (camelCase, `[0..1]`), không theo tên cột.

| Nhóm | Phần tử | Ghi chú |
| --- | --- | --- |
| Tài khoản, đăng nhập Google (D028, D029, D036) | `Actor` thêm `pseudonym`, `disabled`, `identities`; `Student.dailyGoalSeconds`; `LinkedIdentity` (VO) | Chỉ giữ mã băm của định danh Google. Cookie luồng và khoá ký là hạ tầng, không vẽ |
| Lộ trình bài học (D025, D027) | `LessonPath` ◆ `LessonUnit` ◆ `Lesson` ◆ `Step`; `PathStatus`, `Topic`, `StepKind`, `Strictness` | `Step.missions` dùng lại `Mission` của D023 bằng liên kết, không hợp thành, vì `Mission` đã thuộc `Task` |
| Lần luyện và ôn tập (D025, D027) | `StepAttempt` ◆ `StepResult` ◆ `WordMark`, `GapMark`; `ReviewItem`; `WordStatus`, `GapStatus` | Lần luyện ghi phiên bản bài học đã xuất bản. `MISSED` nghĩa là máy chưa nghe ra, không phải nói sai |
| Thành tựu (D032) | `Achievement` (VO, danh mục), `UnlockedAchievement` | Chuỗi ngày, kỷ lục là giá trị suy ra, không lưu thành đối tượng |
| Chấm mù kép (D030) | `RatingBatch` ◆ `RatingAssignment` ◆ `ResearchRating`; `BatchStatus` | Mỗi bài có hai lượt chấm độc lập (`slot`), không thấy điểm máy |
| Gói dịch vụ, thanh toán (D034, D035) | `Order`, `License`; `Plan`, `OrderStatus`, `OrderKind`, `LicenseSource` | Cổng thanh toán là cổng (port) ở hình 2b, không phải lớp miền. Nhật ký thông điệp của cổng và cấu hình là hạ tầng |

## Bản gọn hướng đối tượng (08/10/2026)

Chủ dự án nhận xét bản đầy đủ "phức tạp như tơ nhện", yêu cầu vẽ lại gọn như trang "So do lop", chỉ các phần chính, "theo hướng OOP gọn vì đây sẽ là bản thiết kế sẽ được rã lại xuống code". Vì vậy có hai tệp:

| Tệp | Dùng để |
| --- | --- |
| `02_class_v3_overview.drawio` (`tools/class_spec_overview.py`) | Đọc và rã xuống mã. Mỗi lớp có trạng thái chính và vài thao tác là trách nhiệm của nó. Đây là trang "So do lop v3" trên Drive |
| `02_class_v3.drawio` (`tools/class_spec_v3.py`) | Tra chi tiết từng thuộc tính: reason code, nguồn gốc kết quả, phép đo QC, kiểm nhiệm vụ… |

Hai thay đổi theo hướng đối tượng, áp dụng cho cả hai bản:
- **Vai trò là lớp con.** `Actor` thành lớp trừu tượng; `Student`, `Teacher`, `Admin` kế thừa nó, và việc mỗi vai trò được làm là thao tác của lớp con đó: nộp bài, luyện; duyệt, chấm, xuất bản bài học; tạo tài khoản, mua gói. Kiểu liệt kê `Role` bỏ đi. Khi rã xuống mã, cột `role` của bảng `account` là cột phân biệt lớp con (single-table inheritance), nên không phải đổi lược đồ.
- **Cổng thanh toán là một interface.** `PaymentGateway` có `checkout` và `verify`; Stripe, MoMo, VNPay và cổng thử là các lớp hiện thực, vẽ ở hình 2b.

`tests/test_target_design.py` kiểm cả hai tệp theo cùng luật UML, và kiểm rằng mọi lớp của bản gọn đều có trong bản đầy đủ.

## Ký hiệu

- Thuộc tính `- tên: Kiểu`; tập hợp `List<X>`; ánh xạ `Map<K, V>`.
- Thuộc tính **có thể rỗng** ghi bội số `[0..1]` sau kiểu. UML 2.5 cho phép bội số trên mọi property. Nguyên tắc "thiếu dữ liệu thì rỗng kèm reason code" chỉ đọc được trên hình nhờ dòng này. (Trang "So do lop (hoan thien)" trên Drive dùng `| None`; v3 đổi sang ký hiệu UML.)
- Hình thoi đặc là hợp thành, mũi tên mở là liên kết, nét đứt là phụ thuộc tới kiểu liệt kê.

## Cố ý không vẽ

Sơ đồ lớp là mô hình miền (SDD mục 3.2). Các thứ sau là hạ tầng, có trong mã nhưng vẽ ở ERD:
- phiên đăng nhập (`SessionRecord`);
- khoá ký của máy chủ (`server_secret`), cookie luồng đăng nhập Google;
- nhật ký thông điệp và cấu hình của cổng thanh toán (`billing_event`, `billing_setting`);
- nhật ký kiểm toán (`AuditEvent`, `auditId`);
- băm mật khẩu;
- khóa tranh ghi đè (`revision`, `responseRevision`, `candidateRevision`);
- tham chiếu blob (`BlobRef`);
- mảng PCM đã giải mã (`DecodedAudio`);
- khóa liên kết ngược `responseId` trên các bộ phận của hợp thành.

## Việc mã phải đổi để khớp v3

**Repo này (`ThanhSangLouis/ai-assessor-cefr`)** chưa có 22 lớp/enum: `Actor`, `AsrStatus`, `AssessmentStatus`, `CommentTemplate`, `ConsentRecord`, `ConsentState`, `DiagnosticReport`, `EvidenceIssue`, `EvidenceSource`, `FeatureValue`, `Interaction`, `OutOfRangeFeature`, `Provenance`, `QCMeasurement`, `QCResult`, `QCStatus`, `ReportStatus`, `ResponseRecord`, `ReviewAction`, `ReviewCandidate`, `ReviewState`, `TeacherFinalResult`. `ReasonCode` cần thêm 9 mã và bỏ 4 mã.

**Repo nộp bài (`thanglb2005/ai-assessor-cefr` @ `2b428ce`)** gần v3 hơn nhiều; còn thiếu:
- **Tên lớp:** `Role` (đang là `ActorRole`), `Status` (`ResponseStatus`), `Review` (`ReviewDecision`), `Evidence` (`EvidenceRef`), `Comment` (`DiagnosticComment`).
- **Lớp chưa có:** `Task` và `TaskPart`, `EvidenceKind`, `Priority`.
- **`ReasonCode`:** gộp và đổi tên theo D8.
- **Chỗ lệch nội dung** (lịch sử consent, `reasons` dạng danh sách, `configVersion`, điểm cũ/mới trên `Review`, báo cáo tham chiếu `Assessment` thay vì chép lại): xem báo cáo đối chiếu ngày 02/10/2026 của chủ dự án (lưu ngoài repo vì có chi tiết repo nhóm), mục 1.

Danh sách trên tính tự động bằng cách so tên lớp/enum trên hình với `ast` của `src/`, ngày 02/10/2026.
