# Kế hoạch phát triển AI Assessor CEFR trong 3 tuần

**Trạng thái:** W1 (14–18/09/2026) HOÀN THÀNH theo xác nhận của người dùng. W2 (21–25/09/2026) và W3 (28/09–02/10/2026) là lịch dự kiến; kết quả W2 chưa được xác minh trong repo dự án. Việc hoàn thành W1 không tự phê duyệt Requirement/Specification SDD của repo dự án.

## 1. Đích bàn giao và nguyên tắc cắt phạm vi

Đề xuất bàn giao một **MVP local-first**: sinh viên có tài khoản và consent, nộp một bài nói độc thoại, hệ thống xử lý QC → ASR → features → báo cáo chẩn đoán có provenance; chỉ ước lượng điểm/band khi rubric, model và bằng chứng đủ điều kiện; trường hợp không chắc chắn vào hàng đợi để giảng viên nghe, duyệt hoặc sửa có audit. Quản trị viên quản lý tài khoản và dữ liệu ở mức thiết yếu. Unit test dùng fixture do nhóm tạo; smoke/demo chỉ dùng audio có quyền sử dụng. Không dùng fixture kiểm thử để tuyên bố hiệu năng hay độ chính xác CEFR.

Bản nháp W2 dùng 5 tiêu chí theo lựa chọn của chủ dự án từ báo cáo tuần 1: Range, Accuracy, Fluency, Coherence, Phonology. `Interaction` giữ field `null` cùng reason `insufficient_evidence`; báo cáo chỉ hiển thị overall score/band và coverage/evidence của năm tiêu chí, không lặp overall thành năm điểm, theo quyết định của chủ dự án ngày 25/09/2026. Mô hình baseline là **ước lượng thử nghiệm** cho đến khi có dữ liệu và validation phù hợp. Metric báo cáo phải gắn với dataset, protocol và revision hiện hành. Task C, fine-tune mô hình nền, nghiên cứu người học thật, tuyên bố độ chính xác chuẩn hóa, sản phẩm mobile và production nằm ngoài mốc này. Những nội dung đó cần một đợt riêng nếu chủ dự án lựa chọn.

M01–M08 là kiến trúc module của dự án; [đề cương gốc và báo cáo W1](../sources/README.md) cung cấp bối cảnh và yêu cầu đầu vào. SDD xác lập contract, test plan và phạm vi triển khai của từng module. Mọi path `src/aicefr/` dưới đây là **đề xuất**, chưa phải code đã tạo.

## 2. Module, chủ sở hữu và đường phụ thuộc

Phân công W2–W3 dưới đây là **đề xuất dựa trên chuyên môn W1**, chưa phải xác nhận phân công của từng thành viên.

| ID / SDD | Trách nhiệm trong MVP | Owner đề xuất | Path dự kiến | Phụ thuộc chính |
| --- | --- | --- | --- | --- |
| [M01 — Intake & Student Flow](../sdd/modules/m01-intake-student/01-requirement.md) | Nộp bài, trạng thái, trang sinh viên | Nguyên | api/student, templates | M08, M02–M06 |
| [M02 — Audio QC](../sdd/modules/m02-audio-qc/01-requirement.md) | Giải mã, kiểm tra audio, reason code | Thắng | audio, qc | contract dùng chung |
| [M03 — ASR](../sdd/modules/m03-asr/01-requirement.md) | Adapter local, transcript và timestamp; test double chỉ dùng trong test | Sang | asr | M02 |
| [M04 — Features](../sdd/modules/m04-features/01-requirement.md) | Đặc trưng có version, missing value có lý do | Sang | features | M02, M03 |
| [M05 — Scoring](../sdd/modules/m05-scoring/01-requirement.md) | Baseline, band, ngưỡng từ chối, model provenance | Sang | scoring | M04, rubric chuyên môn |
| [M06 — Diagnostic Report](../sdd/modules/m06-diagnostic-report/01-requirement.md) | Tạo báo cáo chẩn đoán có dẫn chứng từ bài nói | Nguyên | report | M03–M05 |
| [M07 — Teacher Review](../sdd/modules/m07-teacher-review/01-requirement.md) | Định tuyến review, hàng đợi, duyệt/sửa và audit | Nguyên | review, api/review | M05, M06, M08 |
| [M08 — Identity, Storage & Admin](../sdd/modules/m08-identity-storage-admin/01-requirement.md) | Tài khoản/role, consent, SQLite, lưu trữ, xuất/xóa tối thiểu | Thắng | auth, storage, infra | contract dùng chung |

Thắng giữ hợp đồng dùng chung, pipeline coordinator, entrypoint API, migration và CI. Nguyên giữ route/trang sinh viên và giảng viên trong file riêng; Sang giữ các package AI. Mỗi người chỉ sửa file thuộc phần mình; thay đổi schema/enum phải được cả ba review trước khi Thắng cập nhật.

## 3. Kế hoạch theo tuần

| Tuần | File chi tiết | Trạng thái | Kết quả chính |
| --- | --- | --- | --- |
| W1 — 14–18/09 | [week-01.md](week-01.md) | DONE theo người dùng | Repo, module, SDD process, rubric/Jira/AI rules, use case, báo cáo |
| W2 — 21–25/09 | [week-02.md](week-02.md) | SDD nháp; implementation chưa xác minh | Contract, test/plan/task và local smoke có điều kiện |
| W3 — 28/09–02/10 | [week-03.md](week-03.md) | DRAFT | Tích hợp, teacher review, QA, evidence và nghiệm thu |
| W4 — 05–11/10 | [week-04.md](week-04.md) | v2, đối chiếu 11/10/2026 | Nối đầu-cuối (đã đạt), chuẩn hoá repo nộp bài (còn mở), phân loại tính năng của repo gốc |

Phân công Thắng/Sang/Nguyên và gate từng tuần nằm trong ba file trên. W1 đã đóng; ngày 25/09 repo dự án vẫn chưa có source code, nên lịch W3 phụ thuộc vào việc đồng bộ hoặc hoàn thành W2.

## 4. Definition of Done (Điều kiện hoàn thành)

1. Mỗi module có Requirement, Specification, Test Plan, Plan/Tasks và record review/verification/acceptance theo đúng phase SDD; không đánh dấu APPROVED thay người dùng.
2. Luồng demo dùng audio có quyền sử dụng và ASR local thật, có command/model/version/output smoke. Test double chỉ chứng minh logic điều phối; nếu model hoặc audio hợp lệ chưa sẵn, local smoke giữ `NOT_RUN` và gate chưa đạt.
3. Không bịa điểm khi audio/ASR/feature lỗi, thiếu rubric/model được duyệt hoặc input ngoài phân phối. Nếu chưa đủ điều kiện, báo cáo hiển thị `NOT_EVALUATED`; score/band thực nếu có phải mang version và evidence ref. `Interaction` của độc thoại là `null/insufficient_evidence`.
4. Phân quyền sinh viên/giảng viên/quản trị và consent được kiểm thử; `teacher_verified` chỉ bật sau thao tác giảng viên có audit. Log không chứa PII/audio/transcript.
5. Test unit/integration bắt buộc cho happy path, QC/ASR failure, score refusal, evidence linkage, access control, review update và xóa/retention; CI chạy được trên môi trường sạch. Mỗi kết quả kiểm thử ghi revision, lệnh chạy và evidence của dự án.
6. Báo cáo nêu rõ phần đã làm, phần thử nghiệm, giới hạn khoa học và nguồn hình. Bộ tài liệu nộp đối chiếu rubric nhưng không ghi nhận sign-off hay metric chưa có evidence.

## 5. Rủi ro và quyết định đang mở

| ID | Vấn đề | Đề xuất xử lý |
| --- | --- | --- |
| O-01 | Báo cáo W1 mô tả độc thoại 5 tiêu chí; đề cương dài hạn định hướng 6 tiêu chí/Task C. | Chủ dự án đã chọn 5 tiêu chí cho **bản nháp W2** ngày 25/09; cần review học thuật/Phase 01 trước khi khóa rubric. |
| O-02 | Hồ sơ kỹ thuật nội bộ có phạm vi dài hơn kế hoạch ba tuần và metric theo dataset riêng. | Lưu đề cương, model provenance và [khảo sát kỹ thuật](../sources/code-survey.md) tại `docs/sources/`; SDD W2 xác lập phạm vi hiện hành theo module. |
| O-03 | Chưa có dữ liệu/rater validation cho population mục tiêu trong repo dự án. | Không tuyên bố đã đánh giá chính xác CEFR; baseline/demonstrator ở trạng thái thử nghiệm. |
| O-04 | ASR local cần model, máy đủ tài nguyên và audio có quyền. | Ghi smoke thực hoặc `NOT_RUN`; test double không là đầu ra sản phẩm. |
| O-05 | W2 kết thúc ngày 25/09 nhưng repo dự án chưa có source code; W3 chỉ còn 5 ngày làm việc theo lịch. | Đối chiếu [kế hoạch W2](week-02.md); nếu chưa có vertical slice, giảm scope hoặc điều chỉnh hạn 02/10. |
| O-06 | Hai ảnh sơ đồ lớp bổ sung khác hình nhúng trong Word. | Giữ riêng hai nguồn; đầu W2 rà class/quan hệ và ghi rõ bản dùng cho implementation. |

## 6. Quy trình SDD

Mỗi module đi theo `01 Requirement → [02 Research] → 03 Specification → 04 Test Plan → 05 Plan & Task Readiness → 06 Implementation & Test → 07 Implementation Review → 08 Final Verification → 09 Acceptance`. Phase 02 được đề xuất `RUN` cho M03/M05 và `SKIP` cho scope còn lại, nhưng **người dùng quyết định tại Phase 01**. Hiện có Requirement cùng Research đề xuất và Specification/Test Plan/Plan/Tasks **bản nháp W2** theo yêu cầu chuẩn bị của chủ dự án; mọi module vẫn ở Phase 01 PENDING. Chưa có prompt triển khai hoặc approval Phase 05. [Prompt Log](../sdd/prompt-log.md) dẫn tới prompts/, evidence/ và reviews/ riêng của từng module; prompt không tự được lưu chỉ vì xuất hiện trong chat. Báo cáo tuần 1/sơ đồ là tài liệu đầu vào, không thay checkpoint.

## 7. Minh chứng để đối chiếu rubric

Bộ hồ sơ nộp được tập hợp tại [docs/evidence/](../evidence/README.md), phân theo TC và 12 mục bắt buộc của rubric. Evidence kỹ thuật gốc vẫn nằm trong module SDD.

| Minh chứng | Owner chính | Hạn trong lịch | Nơi dự kiến |
| --- | --- | --- | --- |
| Báo cáo, sơ đồ lớp và use case tuần 1 | Thắng, Sang, Nguyên theo phân công được cung cấp | DONE — 14–18/09 | docs/design/week-01/, docs/reports/week-01/ |
| Bảng phân công ba người cho phần còn lại | Thắng tổng hợp; Sang/Nguyên xác nhận | Đề xuất W2–W3 | [week-02.md](week-02.md) và [week-03.md](week-03.md) |
| SRS/SDD cấp module, ma trận FR → AC → test | Owner từng module | Chốt trước khi code module ở W2 | docs/sdd/modules/ |
| Nhật ký prompt AI và sổ/báo cáo tiến độ repo dự án | Cả ba ghi sheet riêng; Thắng tổng hợp | Cập nhật khi có hoạt động thật | [AI Prompt Log theo tuần](../evidence/tc2-3-ai-usage/README.md#ai-prompt-log-theo-tuan) và docs/reports/ |
| Test plan, test case, test result, coverage và defect log | Owner từng module; Thắng tổng hợp CI | W2–W3 | evidence/ của từng module và test code |
| CI chạy được, build/run guide, demo | Thắng CI; Sang/Nguyên xác minh chuyên môn | W3 | Repo dự án và evidence tương ứng |

Rubric có yêu cầu minh chứng thực nghiệm người dùng thật. Ba tuần và dữ liệu hiện có chưa đủ để tự coi mục đó là hoàn thành; nếu chưa có consent/protocol/approval, báo cáo rõ NOT EVALUATED thay vì trình bày fixture kiểm thử như thực nghiệm người dùng.
