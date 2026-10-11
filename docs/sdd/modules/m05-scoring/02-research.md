# M05 — 02 Research (khảo sát scorer và band mapping)

> **v0.2 · 26/09/2026 · APPROVED cùng Phase 03 ngày 26/09/2026.** `RESEARCH MODE: RUN` đã được chọn tại Phase 01 (v0.2 APPROVED). Tách **fact / inference / option / quyết định cần user**; không thêm requirement ngoài M05-FR-001..003. Kết quả kiểm tra hash và `trained_with` đã ghi ở Requirement (M05-R-001..003), không lặp lại.

## Câu hỏi nghiên cứu

1. Đường chấm overall của Ridge v2 hoạt động chính xác thế nào (chuẩn hóa, clip, OOD, near-boundary)?
2. Output năm tiêu chí dạng coverage-only (M05-R-003) tính từ đâu, có lỗi gì khi áp vào Ridge v2?
3. Ngưỡng near-boundary (M05-O-001) nên đặt thế nào?
4. Bài dài hơn khoảng huấn luyện xử lý ra sao?

## Reference contract

```text
TARGET REPO: thanglb2005/ai-assessor-cefr
REFERENCE SOURCE(S): hồ sơ kỹ thuật nội bộ do nhóm tạo (bản local mới nhất trên máy Sang) —
  src/aicefr/scoring/scorer.py, scoring/windows.py, scoring/models/ridge_resp_v2.json,
  pipeline.py (_version_mismatches, _score_windows), contracts.py
REFERENCE SCOPE: predict overall, OOD, near-boundary, coverage năm tiêu chí, guard đơn vị suy luận,
  kiểm lệch phiên bản, chấm theo cửa sổ
MỨC TÁI SỬ DỤNG: ADAPT — code dự án viết theo Spec này; artifact JSON dùng nguyên (hash đã khớp)
PHẦN KHÔNG MANG SANG: năm CriterionScore lặp overall (bản cũ); filler_ratio trong bản đồ tiêu chí;
  so khớp ASR bằng chuỗi con
SOURCE ACCESS: đọc local; không chạy model, không dùng dữ liệu corpus
HANDOFF MODE: tài liệu SDD; Antigravity chỉ nhận prompt sau Phase 05
```

## Fact đã kiểm (26/09/2026)

| ID | Fact | Nguồn |
| --- | --- | --- |
| M05-F-01 | `predict_overall`: thiếu bất kỳ đặc trưng nào trong `feature_order` → `null` + `FEATURE_NOT_COMPUTABLE`; OOD → `null` + `OUT_OF_DISTRIBUTION`; ngược lại `z = (x − mean)/scale` (scale 0 → 1), `raw = Σ coef·z + intercept`, clip vào **[1,0 ; 6,0]**. | `scorer.py` |
| M05-F-02 | OOD: với mỗi đặc trưng có `span = hi − lo > 0`, ngoài `[lo − 0,5·span ; hi + 0,5·span]` là OOD (`ood_tolerance=0.5` trong artifact). Chi tiết trả `value`, `accepted_low/high`, `too`. | `scorer.py`, artifact |
| M05-F-03 | `to_band`: `< 2,75` → A2; `< 3,75` → B1; còn lại B2. `near_boundary`: `|score − t| ≤ boundary_margin` với một ngưỡng `t` bất kỳ. | `scorer.py`, artifact |
| M05-F-04 | Guard đơn vị suy luận: artifact phải khai `unit_of_inference` chứa "một bài nói"; không thì từ chối khi khởi tạo (chống lặp lại lỗi model cấp cả bài thi cho 1,00 với bài thực tế 4,00). | `scorer.py` `IncompatibleModelError` |
| M05-F-05 | `CRITERION_FEATURES` gán Fluency 6 đặc trưng, **trong đó có `filler_ratio`** — không có trong `feature_order` của Ridge v2. Coverage Fluency vì vậy tối đa 5/6 = 0,83 và luôn mang `FEATURE_NOT_COMPUTABLE`, kể cả khi mọi đặc trưng tính được. | `scorer.py`, artifact |
| M05-F-06 | `SCORE_NEAR_BOUNDARY` được gắn ở cấp Assessment (bản cũ gắn vào danh sách bị bỏ, router không bao giờ thấy). | `scorer.py` comment |
| M05-F-07 | Khoảng chấp nhận theo OOD: `total_dur` ≤ **77,8 s** (≥ 9,6 s), `vad_speech_sec` ≤ 76,7 s, `n_words` ≤ 208,75. Hồ sơ tham chiếu chia cửa sổ khi bài `> 60 s` (mục tiêu 45 s, 30–60 s, tối đa 10 cửa sổ), lấy **trung vị** và gắn `SCORE_AGGREGATED` → review. | artifact; `windows.py`, `pipeline.py` |
| M05-F-08 | Metric artifact: `cv_pcc`, `cv_rmse` và `train_n` ghi trong artifact (không chép số vào repo public vì là thống kê suy ra từ S&I, chờ CUP&A — SCRUM-52), GroupKFold 5 theo người nói, `calibration_version="chua-hieu-chuan"`. Tập huấn luyện: S&I 2025 dev P3/P4, chỉ lưu hệ số. | artifact |
| M05-F-09 | Kiểm lệch tham chiếu so `vad_name` bằng `==` nhưng `asr_model` bằng chuỗi con (xem M03 Research F-04). | `pipeline.py` |

## Inference cho M05-O-001 (chưa hiệu chỉnh — chỉ để cân nhắc)

Giả định sai số của model xấp xỉ phân phối chuẩn với độ lệch bằng `cv_rmse` của artifact (giả định này **chưa được kiểm**; `calibration_version` ghi chưa hiệu chỉnh). Khi đó xác suất band thật khác band ước lượng lớn nhất ở sát ngưỡng band, và vẫn đáng kể ngay ở tâm bậc B1, vì sai số CV xấp xỉ một nửa độ rộng bậc B1. Bảng xác suất theo từng mức điểm tính từ `cv_rmse` nên chỉ lưu ở tài liệu nội bộ của chủ module cho tới khi CUP&A trả lời (W4-S4).

## Option cho M05-O-001 (near-boundary)

| Option | Vùng review | Hệ quả |
| --- | --- | --- |
| A. Giữ `boundary_margin = 0,5` của artifact | [2,25 ; 4,25] | Mọi bài ước lượng B1 đều sang giảng viên; band tự động chỉ phát cho A2 thấp (< 2,25) và B2 cao (> 4,25). P(sai) ở biên vùng tự động ≈ 0,17 |
| B. `0,25` (config dự án, có version) | [2,5 ; 3,0] ∪ [3,5 ; 4,0] | Tâm B1 [3,0 ; 3,5] phát tự động với P(sai) ≈ 0,34–0,39 |
| C. Bỏ near-boundary, phát band mọi bài | — | Trái M05-FR-002 |

**Khuyến nghị (Codex role):** Option A. Theo bảng inference, thu hẹp vùng review chỉ đổi lấy band tự động sai khoảng một phần ba số lần; A khớp trạng thái "chưa hiệu chỉnh" của artifact. Hệ quả cần nói rõ trong report M06: "bậc B1 luôn cần giảng viên xác nhận". Đây là quyết định sản phẩm → **user chốt**.

## Option cho M05-O-002 (bài dài hơn khoảng huấn luyện)

| Option | Hành vi | Hệ quả |
| --- | --- | --- |
| A. Không chia cửa sổ ở W2 | Bài vượt khoảng chấp nhận (≈ 77,8 s) → `null` + `OUT_OF_DISTRIBUTION` kèm chi tiết (giá trị, `accepted_high`) để báo người học giữ bài dưới giới hạn | Đơn giản; bài 60–77,8 s vẫn chấm trực tiếp |
| B. Chia cửa sổ như tham chiếu | Bài > 60 s chia cửa sổ, trung vị, `SCORE_AGGREGATED` → review | Thêm module con và test; mọi bài dài vẫn sang review |

**Khuyến nghị:** Option A cho W2, B để W3 nếu dữ liệu thật cho thấy nhiều bài dài. M01/M02 nên hiển thị giới hạn độ dài cho người học — phối hợp với Nguyên/Thắng.

## Adaptation Map

| REF-ID | Nguồn | Evidence | Giá trị | Cách áp dụng | Thay đổi bắt buộc | Quyết định |
| --- | --- | --- | --- | --- | --- | --- |
| M05-REF-01 | `predict_overall` | F-01 | Công thức tuyến tính đúng artifact | Scorer đọc mean/scale/coef/intercept từ JSON | — | **ADOPT** |
| M05-REF-02 | `out_of_distribution_detail` | F-02 | Từ chối có lý do, kèm con số | OOD với `ood_tolerance` từ artifact | — | **ADOPT** |
| M05-REF-03 | `to_band` | F-03 | Band từ `band_thresholds` của artifact | — | — | **ADOPT** |
| M05-REF-04 | `near_boundary` | F-03, F-06 | Cờ review ở cấp Assessment | — | Margin 0,5 của artifact (M05-O-001) | **ADOPT** |
| M05-REF-05 | `IncompatibleModelError` | F-04 | Chặn model sai đơn vị | Kiểm `unit_of_inference` khi nạp | — | **ADOPT** |
| M05-REF-06 | `CRITERION_FEATURES` | F-05 | Bản đồ tiêu chí → đặc trưng cho coverage | Coverage chỉ tính trên đặc trưng có trong `feature_order` | Bỏ `filler_ratio` | **ADAPT** |
| M05-REF-07 | `_version_mismatches` | F-09 | Kiểm lệch ASR/VAD | So bằng `==` cả hai, thêm `feature_order`, `feature_version` | Bỏ chuỗi con | **ADAPT** |
| M05-REF-08 | `windows.py` | F-07 | Chấm bài dài | Không chia cửa sổ ở W2 (M05-O-002) | — | **REJECT** cho W2, xem lại W3 |
| M05-REF-09 | `CriterionScore` lặp overall (bản cũ) | M05-R-003 | — | — | Đã thay bằng coverage-only | **REJECT** |
| M05-REF-10 | Nhánh DeBERTa | scoring-audit | — | Nhánh nghiên cứu riêng, ngoài W2 | — | **REJECT** cho W2 |

**CODEX CHECK RESULT:** fact/inference/option tách riêng. **User decision (26/09/2026):** M05-O-001 → Option A (giữ 0,5); M05-O-002 → Option A (không chia cửa sổ W2).

## Error analysis W3 (SCRUM-53, 03/10/2026)

**Cách làm.**
- Dự đoán out-of-fold, GroupKFold 5 theo người nói, trên phần P3/P4 của tập dev S&I.
- Mô hình dựng lại khớp tuyệt đối artifact `ridge_resp_v2` đang dùng.
- Phân tích lỗi theo nhãn, band, phần thi, thời lượng, độ tin cậy ASR và tỉ lệ im lặng.
- Đo hành vi của luật từ chối ngoài phân bố và luật biên band.
- Thử giãn điểm hậu kỳ bằng CV lồng nhau.

**Số liệu ở đâu.** Số liệu chi tiết là thống kê suy ra từ corpus. Theo license S&I, số liệu này chỉ lưu nội bộ cho tới khi CUP&A cho phép công bố, và người giữ là Sang. Mục này chỉ ghi kết luận định tính.

| ID | Kết luận (định tính) | Hệ quả cho M05 |
| --- | --- | --- |
| EA-01 | Điểm bị co về giữa thang: bài yếu bị chấm cao, bài giỏi bị chấm thấp. Band thấp nhất hiếm khi được nhận ra; một phần đáng kể bài B1 bị đẩy lên B2 | Rủi ro lớn nhất với nhóm đích: người yếu nhận band cao hơn thực tế. Báo cáo người học phải nêu điểm là ước lượng thử nghiệm |
| EA-02 | Lỗi nặng tập trung ở bài nói trôi chảy nhưng nhãn thấp, và bài ngắn nhưng nhãn cao | 18 đặc trưng đo lượng và độ trôi, không đo độ chính xác ngữ pháp, từ vựng, nội dung. Đây là giới hạn của tập đặc trưng, không sửa được bằng tinh chỉnh tham số |
| EA-03 | Lỗi không phụ thuộc rõ vào thời lượng, độ tin cậy ASR hay tỉ lệ im lặng; P4 kém hơn P3 một chút | Lỗi mang tính hệ thống của mô hình, không do bài ghi xấu |
| EA-04 | Bài bị luật ngoài phân bố từ chối đúng là bài mà mô hình chấm kém hơn. Phần bài được tự cho band (ngoài vùng biên ±`boundary_margin`) có độ chính xác band cao | Giữ luật OOD và luật biên (M05-O-001 Option A). Đổi lại, phần lớn bài phải qua giảng viên duyệt |
| EA-05 | Giãn điểm hậu kỳ (khớp phương sai) giúp nhận ra band thấp tốt hơn nhưng tăng sai số trung bình và tăng số bài sai hai band. Hồi quy tuyến tính nhãn theo dự đoán gần như không đổi gì | Đánh đổi thiết kế, xem M05-O-004 |

### Option cho M05-O-004 (bù co điểm về giữa thang)

| Option | Mô tả | Ưu | Nhược |
| --- | --- | --- | --- |
| A | Giữ nguyên `ridge_resp_v2` và luật biên; ghi rõ EA-01, EA-02 là giới hạn | Không đổi code; phần tự cho band vẫn chính xác | Người yếu vẫn dễ được chấm cao khi bài ngoài vùng biên |
| B | Mô hình mới có version riêng, kèm bước giãn điểm (khớp phương sai hoặc isotonic) học bằng CV lồng nhau | Nhận ra band thấp tốt hơn | Sai số trung bình tăng; phải hiệu chỉnh lại khoảng tin cậy, cập nhật Spec/Test Plan M05 |
| C | Thêm đặc trưng độ chính xác (ngữ pháp, từ vựng theo CEFR) | Sửa đúng gốc EA-02 | Khối lượng lớn; phụ thuộc nhãn và license |

**Đề xuất:**
- **Option A** cho demo W4.
- Chốt giữa B và C cùng lúc chốt metric cho Bản cam kết (W5–W6).
- Kiểm lại EA-01 đến EA-05 trên bài sinh viên thật khi có nhãn giảng viên.

**User decision (03/10/2026, Sang):** Option A cho W4; chốt B hay C ở W5–W6 cùng metric Bản cam kết.
