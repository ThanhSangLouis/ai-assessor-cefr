# Xây dựng hệ thống AI hỗ trợ đánh giá năng lực nói tiếng Anh theo CEFR cho sinh viên đại học Việt Nam ở trình độ A2-B2

## 12. Câu hỏi nghiên cứu và kế hoạch trả lời

| Thuộc tính | Giá trị |
| --- | --- |
| Tuần | W1 - Nền tảng đo lường, phạm vi và điều kiện nghiên cứu |
| Trạng thái | DRAFT - cần thực hiện và xác nhận |
| Người phụ trách | SV2 |
| Người duyệt | GVHD |
| Phiên bản | 1.1 |
| Ngày cập nhật | 02/09/2026 |

Các RQ dưới đây là `PROPOSED`. RQ1 chỉ được gọi là confirmatory sau khi hypothesis/estimand, fold manifest, analysis code và quy tắc loại dữ liệu được preregister trước khi xem prediction; nếu không, phải báo exploratory.

## RQ1 - Agreement

**Câu hỏi:** Điểm từng tiêu chí và overall của hệ thống đồng thuận với giảng viên ở mức nào, so với human-human ceiling và với khoảng tin cậy nào?

- Dữ liệu: double-rated responses, adjudicated labels, model predictions.
- Phân tích: agreement ratio, QWK + speaker-cluster CI, macro-F1, Gross Error Rate, confusion matrix.
- Báo cáo: human-human trước AI-human; theo criterion/task/band.
- Rủi ro: gold label vẫn có uncertainty; imbalance.
- Vị thế dự kiến: confirmatory có điều kiện; chưa đủ điều kiện tại W1.

## RQ2 - Fusion

**Câu hỏi:** Fusion có cải thiện so với baseline trên cùng tập response/fold hay không?

- So sánh chính trên Task A/B: B1 audio, B2 transcript, B3 local LLM và M1-AB audio+text, cùng response/fold.
- So sánh Interaction riêng: M1-ABC với M1-AB trên đúng subset có Task C và đủ evidence; không so metric từ hai tập speaker khác nhau như thể là paired.
- Thiết kế: cùng repeated GroupKFold; preprocessing trong fold.
- Kiểm định: paired cluster bootstrap theo speaker.
- Diễn giải: chênh lệch nhỏ hơn độ nhạy dự kiến được báo “không kết luận được”.
- Vị thế: exploratory.

## RQ3 - Quality and ASR

**Câu hỏi:** WER, noise, duration, device và prompt ảnh hưởng sai số chấm thế nào?

- Dữ liệu: QC flags, device/prompt metadata, manual transcript subset.
- Phân tích: error stratification, regression/exploratory plots, case analysis.
- Không suy luận nhân quả nếu thiết kế quan sát.

## RQ4 - Confidence and review

**Câu hỏi:** Calibration và confidence threshold có phát hiện được ca cần giảng viên duyệt không?

- Phân tích: reliability diagram, ECE/Brier nếu phù hợp, error/coverage curve.
- Outcome: review rate, captured gross errors, missed errors.
- Ngưỡng phải chọn trong CV/training process, không chọn trên confirmation set.

## RQ5 - Grounded feedback

**Câu hỏi:** Phản hồi gắn timestamp/transcript có rõ ràng và hành động được hơn phản hồi chung không?

- Thiết kế: usability nhỏ; nhiệm vụ đọc report và nêu hành động tiếp theo.
- Người tham gia: 6-8 sinh viên + 2 giảng viên dự kiến.
- Outcome: hiểu đúng criterion, tìm được evidence, hành động đề xuất, trust/clarity.
- Không tuyên bố learning gain dài hạn.

## RQ6 - Reliability

**Câu hỏi:** Điểm có ổn định giữa prompt tương đương, lần chạy và trước nhiễu âm thanh không?

- Prompt reliability: cần cùng speaker thực hiện hai form tương đương hoặc một thiết kế reliability có thể biện minh; phương án “mỗi speaker luân phiên một prompt” hiện không tạo cặp trong-person và là blocker Q25/D014.
- Run reliability: cùng input/config cho kết quả xác định hoặc sai khác được log.
- Noise robustness: perturbation có kiểm soát; không dùng để thay thế dữ liệu thật.
- Báo cáo per criterion, không chỉ overall.

## Ma trận khả năng trả lời

| RQ | Biến đầu vào | Outcome | Tuần chính | Điều kiện dữ liệu |
| --- | --- | --- | --- | --- |
| RQ1 | Human labels, AI predictions | Agreement/error | W6-W9 | Double-rating đủ |
| RQ2 | Baseline/fusion predictions | Delta QWK | W7-W8 | Same folds |
| RQ3 | WER/QC/device/prompt | Error pattern | W6-W9 | Metadata đầy đủ |
| RQ4 | Probabilities/errors | Calibration/review trade-off | W8-W9 | Calibrated outputs |
| RQ5 | Report variants/usability | Clarity/actionability | W9 | Working report |
| RQ6 | Prompt/run/noise variants | Reliability | W8-W9 | Frozen protocol |

## Phụ thuộc quyết định

| RQ | Quyết định/blocker |
| --- | --- |
| RQ1 | D007, D008, D009, D015; tỷ lệ double-rating và reference-label protocol |
| RQ2 | D004, D011; định nghĩa common evaluation set và Task C subset |
| RQ3 | D010; manual transcript sampling và metadata completeness |
| RQ4 | Calibration/review threshold phải chọn hoàn toàn trong training/CV |
| RQ5 | Report variants, consent và protocol usability chưa duyệt |
| RQ6 | D014: paired/equivalent-form design chưa giải quyết |

## Checklist

- [ ] Mỗi RQ có dữ liệu tạo được trong 10 tuần.
- [ ] Confirmatory/exploratory được ghi trước collection.
- [ ] Không dùng confirmation set để chọn mô hình/ngưỡng.
- [ ] Cách diễn giải null/inconclusive được chốt.
- [ ] Mọi model comparison dùng cùng fold manifest, preprocessing và seed; không chọn run tốt nhất để báo cáo.
