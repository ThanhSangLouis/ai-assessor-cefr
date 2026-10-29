# Xây dựng hệ thống AI hỗ trợ đánh giá năng lực nói tiếng Anh theo CEFR cho sinh viên đại học Việt Nam ở trình độ A2-B2

## 15. Bản đồ lập luận validation

| Thuộc tính | Giá trị |
| --- | --- |
| Tuần | W1 - Nền tảng đo lường, phạm vi và điều kiện nghiên cứu |
| Trạng thái | DRAFT - cần thực hiện và xác nhận |
| Người phụ trách | SV2 |
| Người duyệt | GVHD |
| Phiên bản | 1.1 |
| Ngày cập nhật | 02/09/2026 |

## 1. Claim trung tâm

Trong phạm vi sinh viên đại học Việt Nam A2-B2 và các task đã đặc tả, hệ thống có thể hỗ trợ tạo đánh giá sơ bộ CEFR-aligned với mức đồng thuận, độ tin cậy và giới hạn được báo cáo; giảng viên giữ quyết định cuối cùng.

## 2. Chuỗi bằng chứng

| Giai đoạn | Claim phụ | Bằng chứng | Tuần | Owner |
| --- | --- | --- | --- | --- |
| Familiarisation | Nhóm/rater hiểu CEFR levels và construct | Sorting, quiz, workshop notes | W1, lặp W4 | SV2 |
| Specification | Task/rubric bao phủ construct dự kiến | Construct map, ALTE Grid, task blueprint | W1-W2 | Pedagogy + SV2 |
| Response process | Người học hiểu instruction và thực hiện đúng | Pilot completion, interviews, logs | W4 | SV3 |
| Human rating | Rater dùng rubric nhất quán | Double-rating, agreement, calibration notes | W4-W6 | SV2 |
| Internal structure | Criteria/model behave coherently | Confusion, reliability, ablation | W7-W9 | SV2 |
| Relations to criterion | AI-human so với human-human | QWK+CI, macro-F1, GER | W7-W10 | SV2 |
| Consequences/use | Feedback/review phù hợp low-stakes | Usability, review queue, error capture | W9 | SV3 |
| Generalisability limits | Claim chỉ đúng population/task | Datasheet, subgroup/error analysis | W6-W10 | Cả nhóm |

## 3. Năm bước từ Manual và cách điều chỉnh

1. **Familiarisation:** bắt buộc W1 và trước rater calibration.
2. **Specification:** mô tả coverage, task, construct, rating và intended use.
3. **Standardisation/benchmarking:** dùng anchor, practice, discussion và agreement.
4. **Standard setting:** dự án không tuyên bố cut-score chứng chỉ; cách map band phải được mô tả và giới hạn.
5. **Validation:** chạy liên tục, không chờ W10.

Manual 2009 nói về lập luận liên kết kết quả với CEFR. [Manual for Language Test Development and Examining sửa đổi 2026](https://rm.coe.int/new-revised-manual-for-language-test-development-and-examining-joint-p/48802cc30d) bổ sung test development cycle, fairness/data protection, documentation và automated rating. Hai tài liệu được dùng bổ trợ: không lấy Manual phát triển test để thay thế bằng chứng alignment, và không lấy quy trình alignment để thay thế quality assurance của sản phẩm AI.

## 3.1. Evidence riêng cho automated rating

- Accuracy/agreement so với reference labels và human-human trước adjudication.
- Reliability theo prompt/run và robustness trước điều kiện âm thanh; protocol phải đóng trước khi đo.
- Explainability theo evidence trace: mọi feedback/score truy tới artifact hợp lệ.
- Fairness/error analysis trong giới hạn cỡ mẫu; không tuyên bố “không bias” từ non-significant result.
- Monitoring drift theo model/prompt/rubric version; `teacher_verified` không tự bật.
- Privacy/data protection, prohibited use và human-review consequence evidence.

## 4. Threats-to-validity register

| Threat | Loại | Bằng chứng/kiểm soát |
| --- | --- | --- |
| Prompt quá khó/dễ | Content/method | Prompt equivalence + pilot floor/ceiling |
| ASR sai accent Việt | Scoring | Manual transcript, confidence masking, WER-error |
| Halo giữa criteria | Rating | Two-pass rating, one-criterion practice, agreement per criterion |
| Speaker leakage | Evaluation | GroupKFold + locked fold manifest |
| Model selection bias | Statistical | Nested CV, frozen confirmation set |
| Confidence quá tự tin | Decision | Calibration + review threshold |
| Sample không đại diện | Generalisation | Recruitment log, data card, limited claims |
| Feedback bịa evidence | Consequence | Evidence refs only + teacher review |
| Task C chỉ giả lập interaction | Construct representation | Pedagogy review, pilot response-process evidence, thu hẹp/không chấm Interaction nếu không đủ |
| RQ6 không có paired forms | Reliability | Chốt D014 trước collection; không tính correlation trên dữ liệu không ghép cặp |
| Precision claim không tái lập | Statistical | Cung cấp script/config/output hoặc hạ claim sample-size xuống planning assumption |

## 5. Hồ sơ bằng chứng cần lưu

- Rubric/task/prompt versions.
- Rater training attendance và anchor decisions.
- Raw independent ratings trước adjudication.
- Dataset/fold manifest.
- Model config, seed, code commit.
- Metric scripts và CI method.
- Error casebook và usability notes.
- Deviation log so với pre-registration.

## 6. Điều kiện G1

- [ ] Claim trung tâm không vượt intended use.
- [ ] Mỗi claim phụ có evidence và owner.
- [ ] Validation không phụ thuộc một metric.
- [ ] Standard setting được giới hạn đúng quy mô khóa luận.
