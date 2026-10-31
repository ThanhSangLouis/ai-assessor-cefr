# ĐẶC TẢ YÊU CẦU PHẦN MỀM (SRS)

## Hệ thống AI hỗ trợ đánh giá năng lực nói tiếng Anh theo CEFR (A1–C2) cho sinh viên đại học Việt Nam

| Thuộc tính | Giá trị |
| --- | --- |
| Mã tài liệu | SRS-AICEFR-001 |
| Phiên bản | 1.11 |
| Ngày ban hành | 14/10/2026 (bản 1.0 ngày 12/09/2026, bản 1.2 ngày 14/09/2026) |
| Môn học | Công nghệ phần mềm — đồ án môn học |
| Nhóm thực hiện | 3 sinh viên: SV1 (Speech pipeline), SV2 (Scoring/ML & đo lường), SV3 (Hệ thống & tích hợp) |
| Người duyệt | GVHD [tên], GV Ngoại ngữ [tên] |
| Thời lượng còn lại | 12 tuần (W4–W15) |
| Trạng thái | BASELINE cho giai đoạn xây dựng |
| Phạm vi tiêu chí | **Một điểm tổng thể** mỗi bài nói (QĐ-09). Năm mặt CEFR — Range, Accuracy, Fluency, Coherence, Phonology — được mô tả bằng phép đo liên quan và độ đầy đủ dữ liệu, **không** có điểm riêng; Phonology chỉ qua độ dễ hiểu, không chấm giọng (§9.3). Đã loại Interaction (QĐ-04) |
| Đơn vị suy luận | Một bài nói, tức một file audio |
| Kho mã nguồn | `github.com/ThanhSangLouis/ai-assessor-cefr` |

**Tóm tắt cho người đọc nhanh.** Tài liệu này đặc tả **82 yêu cầu chức năng**, **18 yêu cầu phi chức năng**, **39 quy tắc nghiệp vụ** (mục 2.6) và **23 use case**, mỗi yêu cầu đều có tiêu chí chấp nhận dạng Given/When/Then có thể kiểm chứng bằng kiểm thử tự động. Hệ thống nhận một file audio do sinh viên thu, chạy kiểm tra chất lượng, nhận dạng tiếng nói, trích đặc trưng, chấm sơ bộ theo CEFR kèm bằng chứng truy vết được, và chuyển những bài không chắc chắn cho giảng viên duyệt. Hệ thống **không cấp chứng chỉ** và **không thay thế quyết định của giảng viên**.

## Lịch sử phiên bản

| Phiên bản | Ngày | Nội dung thay đổi | Quyết định |
| --- | --- | --- | --- |
| 1.0 | 12/09/2026 | Baseline: FR-01..FR-39, 18 NFR, UC-01..UC-12 | — |
| 1.2 | 14/09/2026 | FR-21a (bài dài cắt cửa sổ), FR-27a (tiến độ người học); mở rộng FR-29, FR-35; màn hình S3b, S5b; UC-13..UC-17 | — |
| 1.3 | 07/10/2026 | **+25 FR và 5 use case.** FR-40..FR-44, UC-18: luyện tập theo nhiệm vụ. FR-45..FR-50, UC-19, UC-20: lộ trình bài học do giáo viên soạn, giao diện mới. FR-51..FR-55: tài khoản, mật khẩu tạm, việc đang chờ, trang band, chuẩn bị 30 giây. FR-56..FR-60: hồ sơ cá nhân, phiên đăng nhập, lịch sử, đăng nhập Google, quản trị tài khoản đầy đủ. FR-61..FR-64, UC-21, UC-22: chấm mù kép và báo cáo đồng thuận. Thêm **mục 2.6 quy tắc nghiệp vụ** BR-01..BR-27 và đặc tả chi tiết UC-10, UC-17, UC-21, UC-22 | D023, D025, D026, D027, D028, D029, D030 |
| 1.4 | 07/10/2026 | Dòng "Phạm vi tiêu chí" của bảng đầu khớp với QĐ-09 và §9.3: một điểm tổng thể, năm mặt chỉ được mô tả, không có điểm riêng. AC-62.10: quản trị viên giao lại phiếu không còn mù cho giám khảo khác (FR-62) | QĐ-09, D030 |
| 1.5 | 07/10/2026 | **+2 FR, +1 quy tắc.** FR-65: thành tựu ghi công sức luyện tập; FR-66: kỷ lục chuỗi, ngày nghỉ được tính và so với tuần trước (mục 3.9f). BR-28: thành tựu không dựa vào điểm, band hay so với người khác, không bị lấy lại. FR-W6 (không bảng xếp hạng, không XP). US-29, US-30; UC-15 và UC-19 thêm FR-65, FR-66; màn hình S3b có mục Thành tựu; mục 7.4 thêm dòng lưu giữ thành tựu | D032 |
| 1.6 | 07/10/2026 | **+4 FR, +5 quy tắc, +1 use case.** Gói dịch vụ của trường và thanh toán (mục 3.9g): FR-67 thang gói Miễn phí, Dùng thử, Chuẩn, Nâng cao; FR-68 giới hạn số sinh viên và số bài đánh giá dự kiến; FR-69 mua, nâng cấp, gia hạn qua cổng thanh toán; FR-70 mã giấy phép theo hợp đồng, quyền và nhật ký. BR-29..BR-33. UC-23 có tác nhân ngoài là cổng thanh toán. US-31, US-32; mục 7.4 thêm dòng lưu giữ đơn hàng | D033 (đề xuất), D034 |
| 1.7 | 07/10/2026 | **+4 FR, +3 quy tắc.** Nhiều cổng thanh toán (mục 3.9h): FR-71 chọn cổng cho từng đơn, cổng thiếu khoá được nói rõ, tiền thật phải bật riêng; FR-72 Stripe Checkout ở chế độ thử — phiên mở bằng API, trang trả về đọc lại phiên, webhook có chữ ký; FR-73 ví MoMo với IPN có chữ ký. Đăng nhập Google (mục 3.9i): FR-74 cookie của luồng có chữ ký, cookie `__Host-` sau TLS, khung cấu hình cho quản trị viên. BR-34..BR-36. AC-69.9 sửa theo nghĩa mới của môi trường thử: địa chỉ thử của VNPay là môi trường thử. UC-23 thêm bước chọn cổng và ba luồng thay thế; US-33, US-34; mục 7.4 và 8.8 thêm dòng | D035, D036 |
| 1.8 | 11/10/2026 | **+6 FR, +3 quy tắc.** Bằng chứng học tập (mục 3.9j): FR-75 chẩn đoán phát âm theo năm lỗi đặc trưng của người Việt trên trang Tiến độ; FR-76 bản gộp của cả lớp cho giảng viên, không chỉ ra ai; FR-77 thực nghiệm phản hồi — chia nhóm ngẫu nhiên, nhóm "Chỉ điểm" do máy chủ giữ lại phản hồi, rời được bất cứ lúc nào; FR-78 khảo sát, phân tích có khoảng tin cậy bootstrap, xuất CSV theo mã; FR-79 đo thời gian giảng viên và phần máy tự xử lý; FR-80 tiến bộ đáng tin theo sai số đo. BR-37..BR-39 | D039, D040, D041, D042 |
| 1.9 | 11/10/2026 | **Không thêm FR.** Kiến trúc (mục 2.1): sáu dịch vụ sau một gateway, PostgreSQL mỗi dịch vụ một schema, RabbitMQ cho việc chấm, đo bước bài học và sự kiện đồng thuận. Mọi FR, NFR và quy tắc nghiệp vụ giữ nguyên hành vi; kiểm thử chạy trên cả dạng một tiến trình lẫn dạng tách dịch vụ | D043 |
| 1.10 | 13/10/2026 | **Không thêm FR.** Kiến trúc (mục 2.1): gộp còn ba dịch vụ — `core`, `speech`, `web` — `core` một schema PostgreSQL. Mọi FR, NFR và quy tắc nghiệp vụ giữ nguyên hành vi | D044 |
| 1.11 | 14/10/2026 | +4 FR, +1 quy tắc (đề xuất). Mục 3.9k: FR-81 lộ trình riêng của người học và FR-82 giảng viên ghép lộ trình từ bài có sẵn (model chọn và xếp thứ tự bài đã xuất bản, học thứ tự từ các lộ trình hiện có); FR-83 lược đồ cơ sở dữ liệu có phiên bản; FR-84 triển khai lên máy chủ có HTTPS. BR-40 | D045, D046, D047 (PROPOSED) |
| **1.12** | **21/10/2026** | **+1 FR (đề xuất).** FR-85 tính lượt trên bản triển khai thương mại cho kênh NetID: giữ chỗ khi nộp, chỉ thu khi có kết quả, 3 lượt miễn phí mỗi chu kỳ; bản của trường và nghiên cứu không đổi (BR-29, BR-30, FR-W7 giữ nguyên). Kho dữ liệu chuyển sang MongoDB (D048) | D048, D049 (PROPOSED) |
| **1.13** | **24/10/2026** | **+5 FR (đề xuất).** FR-86 hiệu chuẩn band tuỳ chọn, FR-87 gói lượt mua qua cổng thanh toán, FR-88 lớp học và giao bài, FR-89 nhắc việc trong ứng dụng, FR-90 tự nghe lại có mốc đối chứng | D052–D056 (PROPOSED) |
| **1.14** | **24/10/2026** | FR-85 theo bảng giá team chốt: bán theo bài và phút (2.000 IDPoint bài đầu, 1.400 mỗi phút thêm), đo kèm token Whisper để tính giá vốn (D057); AC-85.1 và AC-85.5 viết lại | D057 (PROPOSED) |

> **Bản 1.3 (07/10/2026).** FR-40..FR-50 đã được ghi vào tài liệu từ ngày 06/10 (D023, D025) nhưng số phiên bản khi đó chưa được nâng; bản 1.3 gom mọi thay đổi kể từ bản 1.2 vào một phiên bản và ghi rõ quyết định đứng sau từng nhóm yêu cầu. Từ bản này, mỗi đợt thêm yêu cầu nâng số phiên bản cùng lúc với nhật ký quyết định.
>
> **Bản 1.2 (14/09/2026).** Thêm **FR-21a** (chấm bài dài bằng cách cắt cửa sổ) và **FR-27a** (người học xem tiến độ của mình theo thời gian); mở rộng FR-29 với thống kê cấp lớp và FR-35 với đường người học **tự** xoá một bài của mình; thêm hai màn hình S3b và S5b; sửa lại mục 8.2 vì nay có **hai loại đề bài** với hai dải thời lượng khác nhau chứ không phải một.
>
> FR-21a sinh ra từ một sự cố đo được chứ không phải từ một mong muốn: một bản ghi 94 giây qua được toàn bộ kiểm tra chất lượng rồi nhận một báo cáo đầy đủ mà nội dung duy nhất là "không chấm được vì bài dài 94 giây".

---

# 1. GIỚI THIỆU

## 1.1. Mục đích tài liệu

Tài liệu này đặc tả đầy đủ yêu cầu chức năng và phi chức năng của phần mềm **AI Assessor CEFR Speaking (viết tắt: AICEFR)** — một hệ thống web hỗ trợ giảng viên đánh giá năng lực nói tiếng Anh của sinh viên đại học Việt Nam trong dải A1–C2 (D059).

Đối tượng đọc:

| Đối tượng | Dùng tài liệu để |
| --- | --- |
| Nhóm phát triển (SV1, SV2, SV3) | Làm nguồn duy nhất xác định phạm vi code phải viết trong 12 tuần |
| GVHD và hội đồng chấm đồ án | Đối chiếu tài liệu ↔ sơ đồ ↔ mã nguồn, kiểm tra tiêu chí nghiệm thu |
| GV Ngoại ngữ / giảng viên đánh giá | Xác nhận hệ thống không vượt quá tuyên bố đo lường được phép |
| Người phụ trách đạo đức/dữ liệu | Kiểm tra tuân thủ Luật 91/2025/QH15 và Nghị định 356/2025/NĐ-CP |

Tài liệu là **baseline**: mọi thay đổi yêu cầu phải đi qua decision log và được GVHD duyệt trước khi code thay đổi theo.

## 1.2. Phạm vi sản phẩm

AICEFR nhận file audio bài nói tiếng Anh (độc thoại, Task A và Task B), kiểm tra chất lượng thu âm, chuyển thành văn bản bằng ASR, trích đặc trưng định lượng, chấm điểm bằng mô hình học máy huấn luyện trên corpus công khai, quy về band A2/B1/B2 và sinh báo cáo **có bằng chứng truy vết được**. Mọi kết quả đều là **ước lượng hỗ trợ (estimated)**; giảng viên là người ra quyết định cuối cùng.

**Trong phạm vi (sẽ code):**

- Upload/quản lý phiên đánh giá, lưu audio ở kho có kiểm soát.
- Quality Control audio: duration, sample rate, clipping, silence ratio, SNR proxy.
- ASR local (faster-whisper) với word-level timestamp, ưu tiên bản verbatim giữ filler `um/uh`.
- Trích 14 đặc trưng định lượng (fluency + lexical + chất lượng transcript).
- Mô hình chấm: ridge regression trên đặc trưng + BERT text grader, late fusion, đầu ra thang 0–6.
- Quy band A2/B1/B2 từ thang 0–6 theo bảng ngưỡng có version.
- Báo cáo bằng chứng: trích đoạn transcript, mốc thời gian pause/filler, từ có ASR confidence thấp.
- Cờ chuyển giảng viên (low confidence / audio kém / điểm gần ranh giới).
- Màn hình giảng viên duyệt và sửa điểm, lưu audit record.
- Quản trị người dùng, xuất/xóa dữ liệu theo yêu cầu, log không chứa PII.

**Ngoài phạm vi (KHÔNG code trong 12 tuần):**

- Chấm tiêu chí **Interaction** từ hội thoại (không có Task C trong bản này).
- Cấp chứng chỉ CEFR; quyết định đậu/rớt/xếp lớp tự động.
- A1, C1, C2; người dưới 18 tuổi; ngôn ngữ khác tiếng Anh.
- Fine-tune mô hình nền lớn, huấn luyện ASR từ đầu.
- Mobile app native, chatbot hội thoại, LMS đầy đủ, proctoring, thanh toán.
- Speaker identification, suy diễn cảm xúc/tính cách/giới tính/dân tộc.

## 1.3. Định nghĩa và từ viết tắt

| Thuật ngữ | Giải thích |
| --- | --- |
| CEFR | Common European Framework of Reference for Languages — khung tham chiếu năng lực ngôn ngữ châu Âu |
| A2 / B1 / B2 | Ba mức năng lực trong phạm vi đề tài (sơ cấp cao → trung cấp cao) |
| ASR | Automatic Speech Recognition — nhận dạng tiếng nói tự động |
| QC | Quality Control — kiểm tra chất lượng audio trước khi xử lý |
| SNR | Signal-to-Noise Ratio — tỷ lệ tín hiệu/nhiễu, đo bằng dB |
| Clipping | Hiện tượng biên độ audio bị cắt ngọn do thu quá lớn |
| Silence ratio | Tỷ lệ thời lượng im lặng trên tổng thời lượng |
| Filler | Từ đệm khi ngập ngừng: `um`, `uh`, `er`, `ah` |
| Run length | Độ dài một đoạn nói liên tục giữa hai pause ≥ 0,25 s |
| TTR | Type-Token Ratio — tỷ lệ số từ khác nhau / tổng số từ |
| MTLD | Measure of Textual Lexical Diversity — chỉ số đa dạng từ vựng ổn định theo độ dài văn bản |
| Ridge regression | Hồi quy tuyến tính có phạt L2, chống overfit khi dữ liệu nhỏ |
| BERT text grader | Mô hình transformer đã pretrain, fine-tune nhẹ phần head để dự đoán điểm từ transcript |
| Late fusion | Kết hợp đầu ra hai mô hình ở bước cuối bằng trọng số học được |
| Band | Nhãn mức CEFR cuối cùng (A2/B1/B2) |
| Score 0–6 | Thang điểm liên tục của corpus Speak & Improve, ánh xạ sang band |
| Evidence | Mảnh bằng chứng có `evidence_id`, trỏ tới vị trí cụ thể trong audio/transcript |
| Reason code | Mã lý do chuẩn hóa khi hệ thống từ chối hoặc chuyển review |
| Teacher review | Quy trình giảng viên xem, duyệt hoặc sửa kết quả AI |
| `teacher_verified` | Cờ boolean, mặc định `false`, chỉ `true` sau hành động duyệt thực tế |
| PII | Personally Identifiable Information — thông tin định danh cá nhân |
| S&I 2025 | Speak & Improve Corpus 2025 — corpus huấn luyện đã tải về |
| MoSCoW | Phân loại ưu tiên: Must / Should / Could / Won't |
| FR / NFR | Functional Requirement / Non-Functional Requirement |
| DoD | Definition of Done — tiêu chí hoàn thành |

## 1.4. Tài liệu tham khảo

| Mã | Tài liệu |
| --- | --- |
| R1 | `markdown/week_01/05_construct_definition.md` — định nghĩa construct Speaking và năm tiêu chí |
| R2 | `markdown/week_01/06_cefr_A2_B1_B2_descriptor_map.md` — bản đồ descriptor A2/B1/B2 |
| R3 | `markdown/week_01/07_construct_evidence_matrix.md` — ma trận tiêu chí ↔ bằng chứng ↔ reason code |
| R4 | `markdown/week_01/09_scope_and_intended_use.md` — phạm vi và mục đích sử dụng |
| R5 | `markdown/week_01/10_target_population.md` — đối tượng và kế hoạch lấy mẫu |
| R6 | `markdown/week_01/11_claims_and_nonclaims.md` — ma trận tuyên bố và giới hạn tuyên bố |
| R7 | `markdown/week_01/16_data_management_plan.md` — kế hoạch quản lý dữ liệu |
| R8 | `markdown/week_01/17_consent_requirements.md` — yêu cầu phiếu đồng thuận |
| R9 | `markdown/week_03/01_vertical_slice_draft_spec.md` — đặc tả vertical slice `ResponseProcessor` |
| R10 | `markdown/De_cuong_AI_Assessor_CEFR_v3.1_ALDM-L.md` — đề cương nghiên cứu v3.1 (kiến trúc, feature lanes, metric, rủi ro) |
| R11 | CEFR Companion Volume 2020, Council of Europe, Appendix 3 |
| R12 | Luật Bảo vệ dữ liệu cá nhân số 91/2025/QH15, hiệu lực 01/01/2026 |
| R13 | Nghị định 356/2025/NĐ-CP quy định chi tiết thi hành Luật 91/2025/QH15, hiệu lực 01/01/2026 |
| R14 | Speak & Improve Corpus 2025 — 5.616 file tập dev, có nhãn điểm CEFR 0–6 |
| R15 | IEEE Std 830-1998 / ISO/IEC/IEEE 29148:2018 — cấu trúc SRS |

---

# 2. MÔ TẢ TỔNG QUAN

## 2.1. Bối cảnh sản phẩm

Giảng viên tiếng Anh ở đại học Việt Nam phải chấm bài nói cho lớp 60–90 sinh viên (sàn 60). Một bài nói 2 phút cần khoảng 5–8 phút để nghe, ghi chú và chấm theo rubric, tức khoảng 4–6 giờ cho một lớp mỗi vòng đánh giá. Hệ quả thực tế là số vòng đánh giá quá trình bị giảm, phản hồi trả về chậm và thiếu bằng chứng cụ thể.

AICEFR **không thay thế giảng viên**. Nó rút ngắn bước chuẩn bị: tự động nghe, đo, đề xuất mức và — quan trọng nhất — **trình bày bằng chứng có mốc thời gian** để giảng viên xác nhận nhanh hoặc chỉnh sửa.

Hệ thống viết bằng Python, chạy local-first, đóng gói bằng Docker. Từ bản 1.10 (D044) hệ thống gồm **ba dịch vụ** sau một gateway — `core` (tài khoản, đánh giá, bài học, gói dịch vụ; PostgreSQL một schema), `speech` (nhận dạng và chấm), `web` (trang) — giao tiếp qua HTTP nội bộ và RabbitMQ; bản 1.9 (D043) từng tách sáu dịch vụ; cùng mã vẫn chạy được trong một tiến trình trên một máy. Không phụ thuộc dịch vụ cloud để xử lý audio: mọi thành phần, kể cả cơ sở dữ liệu và hàng đợi, chạy trên máy của trường.

**Sơ đồ luồng xử lý chính:**

```text
[Sinh viên] --upload audio--> [API /responses]
                                     |
                                     v
                            [M2: QC audio]  --fail--> REJECTED + reason_code
                                     | pass / review
                                     v
                            [M3: ASR whisper]  --fail--> FAILED + ASR_FAILED
                                     | transcript + word timestamps
                                     v
                            [M4: Feature extractor] (14 đặc trưng)
                                     |
                     +---------------+---------------+
                     v                               v
        [M5a: Ridge trên đặc trưng]      [M5b: BERT text grader]
                     |                               |
                     +------------> late fusion <----+
                                     |
                            score 0-6 + confidence
                                     v
                            [M5c: Band mapper] -> A2 / B1 / B2
                                     v
                            [M6: Evidence & Report builder]
                                     v
                            [M7: Flag engine] --flag--> [Teacher queue]
                                     |                          |
                                     v                          v
                            [Report cho sinh viên] <--- [M7: Giảng viên duyệt/sửa]
                                     |
                                     v
                            [M8: Lưu hồ sơ speaking_profile]
```

## 2.2. Chức năng chính

| Nhóm | Mô tả ngắn |
| --- | --- |
| F1. Quản lý phiên và nộp bài | Tạo phiên đánh giá, upload audio hoặc ghi âm trực tiếp trên trình duyệt, gắn `task_id`/`prompt_version`/`consent_version` |
| F2. Kiểm tra chất lượng audio | Đo 5 chỉ số kỹ thuật, chặn bài không đủ chất lượng bằng reason code |
| F3. Nhận dạng tiếng nói | Sinh transcript verbatim + word timestamp + confidence từng từ |
| F4. Trích đặc trưng | 14 đặc trưng fluency/lexical/chất lượng, có `feature_version` |
| F5. Chấm điểm | Ridge + BERT grader → điểm 0–6 → band A2/B1/B2 + độ tin cậy |
| F6. Báo cáo bằng chứng | Ghép điểm với đoạn transcript, mốc pause/filler, từ confidence thấp |
| F7. Chuyển giảng viên | Sinh cờ review theo 4 quy tắc, quản lý hàng đợi, ghi audit khi duyệt/sửa |
| F8. Quản trị và dữ liệu | Tài khoản/phân quyền, xuất dữ liệu cá nhân, xóa theo yêu cầu rút consent |

## 2.3. Đặc điểm người dùng

| Actor | Mô tả | Trình độ CNTT | Tần suất dùng | Quyền chính |
| --- | --- | --- | --- | --- |
| **Sinh viên** (Student) | Người học 18+, A1–C2 (phần lớn A2–B2), nộp bài nói và xem phản hồi | Dùng web cơ bản | 1–3 lần/tuần | Upload bài của mình; xem báo cáo đã phát hành; yêu cầu xuất/xóa dữ liệu của mình. **Không** sửa được transcript/audio/điểm sau khi nộp |
| **Giảng viên đánh giá** (Teacher/Rater) | GV tiếng Anh, chịu trách nhiệm chuyên môn cuối cùng | Dùng web cơ bản, hiểu rubric CEFR | Theo đợt, 20–60 bài/đợt | Xem hàng đợi review, nghe audio, xem bằng chứng, duyệt hoặc sửa band và điểm tiêu chí, ghi lý do; phát hành báo cáo |
| **Quản trị viên** (Admin) | Thành viên nhóm nghiên cứu (SV3) vận hành hệ thống | Kỹ thuật | Hằng ngày trong đợt thu | Quản lý tài khoản/vai trò, cấu hình ngưỡng QC, kích hoạt `model_version`, xem log vận hành, xử lý yêu cầu xóa dữ liệu, xuất dataset đã giả danh |

Ba actor này là **toàn bộ** vai trò được cài đặt. Không có vai trò adjudicator riêng trong phần mềm; việc phân xử bất đồng giữa hai giảng viên được thực hiện ngoài hệ thống theo protocol nghiên cứu.

## 2.4. Ràng buộc

| Mã | Ràng buộc |
| --- | --- |
| C-01 | Ngôn ngữ cài đặt: Python 3.11+. Backend FastAPI + Pydantic v2. |
| C-02 | Cơ sở dữ liệu: SQLite ở môi trường dev/demo; PostgreSQL ở môi trường có nhiều người dùng đồng thời. **Hiện thực hiện tại khác ràng buộc gốc và cố ý như vậy:** truy cập qua cổng `ResponseStore` với adapter `Repository` dùng thẳng `sqlite3`, không dùng SQLAlchemy. Mục tiêu "đổi backend không sửa nghiệp vụ" được giữ nguyên, chỉ đổi cách đạt: viết adapter thứ hai thay vì đổi ORM. |
| C-03 | Giao diện web: FastAPI + Jinja2, render HTML phía máy chủ (1 ứng dụng, các trang điều hướng theo vai trò). Không viết mobile native, không SPA phức tạp. Lý do chọn nền tảng này thay cho Streamlit: hệ thống đã có sẵn 11 endpoint FastAPI đang chạy và bộ test bám trực tiếp vào các endpoint đó, trong khi Streamlit không tách được tầng API khỏi tầng hiển thị nên sẽ phải dựng song song hai tầng hoặc bỏ phần đã làm. |
| C-04 | Xử lý audio/ASR chạy **local**. Không gửi audio ra bất kỳ dịch vụ ngoài nào. |
| C-05 | Máy tham chiếu: CPU 8 nhân, 16 GB RAM, không GPU. Mọi NFR hiệu năng đo trên cấu hình này. |
| C-06 | Đóng gói bằng Docker Compose; CI chạy trên GitHub Actions. |
| C-07 | Nguồn lực: 3 sinh viên × 12 tuần. Mọi FR ưu tiên `Must` phải hoàn thành trước W9. |
| C-08 | Không có GPU dành riêng → dùng `faster-whisper small` int8 và BERT `base` size, chỉ fine-tune classification head, không fine-tune toàn bộ backbone. |
| C-09 | Hệ thống không được có bất kỳ hành động tự động nào tạo ra quyết định pass/fail, cấp chứng chỉ hoặc xếp lớp (ràng buộc từ R4 mục 6.1). |
| C-10 | Repository không được chứa audio thật, transcript thật, PII hoặc secret. CI có bước kiểm tra tự động. |

## 2.5. Giả định và phụ thuộc

| Mã | Nội dung | Ảnh hưởng nếu sai |
| --- | --- | --- |
| A-01 | Corpus Speak & Improve 2025 (5.616 file dev, nhãn 0–6) dùng được cho huấn luyện theo license đã kiểm tra | Không có dữ liệu huấn luyện → phải chuyển sang mô hình rule-based, giảm claim |
| A-02 | Dữ liệu sinh viên Việt Nam **chỉ dùng để kiểm định**, không dùng huấn luyện, và chỉ thu khi có phiếu đồng thuận đã ký | Không có consent → chỉ báo cáo kết quả trên corpus công khai |
| A-03 | Ánh xạ thang 0–6 của S&I sang A2/B1/B2 được GV Ngoại ngữ xác nhận trước W6 | Band mapper không có cơ sở → chỉ trả điểm 0–6, không trả band |
| A-04 | FFmpeg/ffprobe, librosa, faster-whisper, transformers cài được offline từ cache đã chuẩn bị | Không chạy được demo offline |
| A-05 | Giảng viên đánh giá có ít nhất 2 người và cam kết review tối thiểu 60 bài trong W8–W9 | Không đủ dữ liệu human reference để báo cáo độ đồng thuận |
| A-06 | Tiêu chí **Interaction** không được chấm trong bản này; API luôn trả `null` + `insufficient_evidence` | Nếu cố chấm từ độc thoại → vi phạm R1/R3, mất hiệu lực đo lường |

## 2.6. Quy tắc nghiệp vụ (Business Rules)

Quy tắc nghiệp vụ là những điều hệ thống **phải luôn đúng**, bất kể màn hình hay API nào chạm tới. Mỗi yêu cầu chức năng ở mục 3 là một cách hiện thực các quy tắc này; khi hai thứ mâu thuẫn, quy tắc thắng và yêu cầu phải sửa. Cột "Từ bản" ghi phiên bản SRS và quyết định đưa quy tắc vào; cột "Giữ bằng" ghi nơi trong mã chặn vi phạm và test chứng minh.

| Mã | Quy tắc | Yêu cầu liên quan | Từ bản | Giữ bằng |
| --- | --- | --- | --- | --- |
| BR-01 | Hệ thống **không cấp chứng chỉ** và không quyết định đậu/rớt. Mọi điểm và band là ước lượng; giảng viên quyết định cuối cùng | FR-21, FR-30, C-09 | 1.0 | Tuyên bố bắt buộc ở mọi trang; `tests/test_web.py` (`test_every_page_carries_required_disclaimer`, chuỗi cấm) |
| BR-02 | Hệ thống chỉ biết **bút danh**: không lưu họ tên, mã số sinh viên, email hay số điện thoại. Mối nối bút danh – người thật nằm trên giấy | FR-33, FR-52, FR-59 | 1.0 | `auth/pseudonyms.py` (`validate_pseudonym`); bảng `account` không có cột liên lạc; Google chỉ để lại mã băm (BR-15) |
| BR-03 | **Chỉ sinh viên tự đăng ký (D063, D065).** Giảng viên và quản trị viên do quản trị viên cấp, kèm một vai trò; sinh viên tự đăng ký bằng Google hoặc bằng mật khẩu ở `/signup`, nhận bút danh ngẫu nhiên và (với mật khẩu) một mã khôi phục dùng một lần; tắt bằng `AICEFR_GOOGLE_SIGNUP=0`, `AICEFR_SELF_SIGNUP=0` | FR-32, FR-52, FR-59 | 1.0 | `accounts_api.py`; `tests/test_profile.py` (`test_with_sign_up_off_an_unlinked_google_account_cannot_sign_in_or_create_one`) |
| BR-04 | Chưa đồng ý điều khoản sử dụng thì hệ thống **không nhận** bài nói hay lượt luyện nào | FR-01 | 1.0, đổi ở D058 | `TERMS_NOT_ACCEPTED` ở `POST /api/v1/responses` và API lượt luyện; `tests/test_terms.py` |
| BR-05 | Chỉ dữ liệu của người **đã đồng ý điều khoản sử dụng** mới vào bản xuất nghiên cứu, đợt chấm mù, báo cáo đồng thuận và bản xuất phiếu chấm; xoá dữ liệu là rút khỏi tất cả | FR-34, FR-35, FR-61, FR-64 | 1.0, mở rộng 1.3 (D030), đổi ở D058 | `AuthRepository.accounts_with_terms`; `tests/test_terms.py` (`test_research_use_covers_the_accounts_that_accepted`) |
| BR-06 | Bài luyện **không** qua mô hình chấm, không có band, không vào hàng đợi duyệt, thống kê chấm hay bản xuất nghiên cứu | FR-44, FR-49 | 1.3 (D023, D025) | cột `purpose`; `tests/test_lessons_integration.py` (`test_lesson_attempts_stay_out_of_queue_and_research_export`) |
| BR-07 | `teacher_verified` chỉ bật khi một giảng viên lưu quyết định **có lý do** | FR-30, FR-31 | 1.0 | `Repository.apply_review`; `tests/test_auth.py` |
| BR-08 | Năm lần đăng nhập sai liên tiếp thì khoá 15 phút; nhập sai mật khẩu hiện tại khi đổi mật khẩu cũng tính là một lần sai | NFR-07, FR-51 | 1.0, mở rộng 1.3 (D028) | `AuthRepository._record_failure`; `tests/test_accounts.py` (`test_a_wrong_current_password_is_refused_and_counts_towards_the_lockout`) |
| BR-09 | Một phiên đăng nhập sống tối đa 8 giờ; đăng xuất, đổi mật khẩu hay bị tắt tài khoản là thu hồi phiên ngay | NFR-07, FR-32, FR-51, FR-52 | 1.0, mở rộng 1.3 | `auth/sessions.py` (`LIFETIME_HOURS`), `AuthRepository.revoke_sessions` |
| BR-10 | Mật khẩu từ 8 ký tự, không quá 72 byte, không trùng bút danh, khác mật khẩu đang dùng | FR-51 | 1.3 (D028) | `auth/passwords.py` (`check_new_password`); `test_the_password_policy_says_what_is_wrong` |
| BR-11 | Mật khẩu quản trị viên nhìn thấy là **mật khẩu tạm**: hiện một lần, không lưu bản rõ, và tài khoản giữ mật khẩu tạm không dùng được gì ngoài việc đổi mật khẩu | FR-52 | 1.3 (D028) | `deps.PASSWORD_CHANGE_PATHS`; `test_a_temporary_password_opens_nothing_but_the_password_change` |
| BR-12 | Tạo tài khoản theo dãy là **tất cả hoặc không**; số bút danh nối tiếp số lớn nhất đang có, không tái dùng số của tài khoản đã xoá dữ liệu | FR-52 | 1.3 (D028) | `AuthRepository.create_with_temporary_passwords`, `next_pseudonyms` |
| BR-13 | Quản trị viên **không thao tác lên chính mình**: không tự tắt, tự cấp lại mật khẩu, tự đổi vai trò hay tự đăng xuất mọi thiết bị | FR-52, FR-60 | 1.3 (D028, D029) | `accounts_api.py` trả 409; `test_an_administrator_changes_a_role_but_not_their_own` |
| BR-14 | Hồ sơ chỉ nhận giá trị trong danh sách (biểu tượng, màu, mục tiêu ngày); không có trường văn bản tự do nào mời người dùng nhập tên thật | FR-56 | 1.3 (D029) | `AuthRepository.update_profile`; `test_a_profile_takes_only_listed_avatars_and_goals` |
| BR-15 | Google chỉ đăng nhập cho tài khoản **đã tự liên kết**; Google không tạo tài khoản, không cấp vai trò; hệ thống chỉ giữ **mã băm một chiều** của định danh Google | FR-59 | 1.3 (D029) | `auth/google.py` (`subject_hash`), `google_api.py`; `test_linking_then_signing_in_with_google` |
| BR-16 | Một tài khoản Google chỉ liên kết với **một** bút danh | FR-59 | 1.3 (D029) | `account_identity` khoá chính (provider, subject_hash); `test_one_google_account_links_to_one_pseudonym` |
| BR-17 | Nhật ký chỉ ghi lần đăng nhập sai với bút danh **có thật**; chuỗi gõ vào không khớp tài khoản nào không vào nhật ký | FR-58 | 1.3 (D029) | `main.py` (`login`); `test_an_unknown_pseudonym_leaves_nothing_in_the_audit_log` |
| BR-18 | Mỗi bài trong một đợt chấm mù có **đúng hai** giám khảo khác nhau; thứ tự bài xáo riêng cho từng giám khảo; mẫu bài và thứ tự sinh từ **một hạt giống được ghi lại** | FR-61 | 1.3 (D030) | `research/assign.py`; `tests/test_assign_unit.py` |
| BR-19 | Trong lúc còn phải chấm mù một bài, giám khảo **không thấy** bút danh, mã bài, điểm của máy hay điểm của giám khảo khác — trên phiếu chấm cũng như qua đường vòng (báo cáo, lịch sử, hàng đợi) | FR-62 | 1.3 (D030) | `rating_api.py` (`_sheet`), `main.py` (`_blind`); `test_the_rating_sheet_carries_no_pseudonym_response_id_or_machine_score`, `test_the_machine_result_stays_closed_to_a_rater_until_they_have_rated` |
| BR-20 | Phiếu chấm: năm tiêu chí và điểm tổng trên thang 0–6 bước 0,5, band A2/B1/B2, một dòng lý do; hoặc "không chấm được" kèm lý do. Nộp **một lần**, không sửa | FR-62 | 1.3 (D030) | `rating_api.py` (`_to_rating`), khoá chính `research_rating`; `test_a_rating_follows_the_rating_sheet_rules` |
| BR-21 | Chuyển người thứ ba phân xử khi hai điểm tổng lệch **từ 1,0** trở lên, lệch band, hoặc chỉ một bên thấy không chấm được; người phân xử **không** là người đã chấm bài đó | FR-63 | 1.3 (D030) | `research/agreement.py` (`needs_adjudication`), `RatingRepository.add_adjudication` |
| BR-22 | Điểm đối chiếu với máy: trung bình hai giám khảo; bài có phân xử thì trung vị ba | FR-64 | 1.3 (D030) | `research/agreement.py` (`reference`) |
| BR-23 | Đồng thuận giữa hai giám khảo được báo **trước** đồng thuận máy–người; khoảng tin cậy lấy mẫu lại theo **người nói**, không theo bài | FR-64 | 1.3 (D030) | `agreement_report`; `test_the_report_puts_humans_first_and_compares_the_machine_before_any_review` |
| BR-24 | Điểm máy dùng để so là kết quả của máy **trước** mọi quyết định của giảng viên | FR-64 | 1.3 (D030) | `rating_repository.py` (`_MACHINE`) |
| BR-25 | Xoá dữ liệu của một người học là xoá luôn các phiếu chấm về bài của người đó | FR-35, FR-64 | 1.3 (D030) | khoá ngoại `ON DELETE CASCADE`; `test_erasing_a_participant_erases_what_raters_said_about_them` |
| BR-26 | Mỗi lần nghe một bản ghi, mỗi thao tác trên tài khoản và mỗi phiếu nộp đều có một dòng nhật ký kiểm toán, không chứa mật khẩu, điểm hay nội dung bài nói | FR-31, FR-37, FR-51..FR-64 | 1.0, mở rộng 1.3 | `Repository.write_audit`; các test `audit` trong `tests/test_accounts.py`, `tests/test_ratings.py` |
| BR-27 | Ai đã **xem kết quả của máy** cho một bài — mở báo cáo, lịch sử hay màn duyệt bài đó, hoặc đã ra quyết định duyệt — thì **không còn mù** với bài đó: không được giao chấm mù hay phân xử bài đó, và phiếu đang nợ của họ về bài đó không nhận điểm nữa, kể cả khi đợt đóng rồi mở lại. Quản trị viên làm giám khảo được che trên màn quản trị (danh sách bài, bản xuất nghiên cứu, báo cáo và CSV của đợt) như giảng viên trên hàng đợi | FR-61, FR-62, FR-63 | 1.3 (D030) | bảng `machine_seen`, `rating_repository.py` (`_SEEN`), `main.py` (`_saw`), `rating_api.py` (`_not_while_owed`); `test_a_teacher_who_opened_the_machine_result_is_not_drawn_to_rate_that_response`, `test_a_sheet_goes_void_once_its_rater_has_seen_the_machine_result`, `test_an_administrator_who_rates_stays_blind_on_the_administration_screens` |
| BR-28 | Thành tựu và nhịp luyện chỉ ghi **công sức** của chính người học — thời gian nói, số ngày luyện, bài và chặng đã xong, lần thử lại, lượt ôn, số bài đánh giá có kết quả — **không bao giờ** dựa vào điểm, band, tỷ lệ đạt hay so với người khác: không bảng xếp hạng, không lời đe doạ mất chuỗi, không đếm ngược. Đã đạt thì **không bị lấy lại**, kể cả khi lượt luyện bị xoá hay giảng viên sửa nhận định; chỉ người học xem được; xoá dữ liệu người học là xoá theo | FR-65, FR-66 | 1.5 (D032) | `practice/achievements.py` (`Facts` không có trường điểm hay band), bảng `achievement`; `test_no_achievement_reads_a_score_a_band_or_anyone_else`, `test_an_achievement_is_never_taken_back`, `test_the_personal_export_and_erasure_cover_achievements` |
| BR-29 | Gói dịch vụ là của **trường**, không bao giờ của từng sinh viên, và **không bao giờ khoá việc học**: bài đánh giá có bằng chứng, lộ trình, ôn tập, thành tựu, tiến độ và quyền với dữ liệu của mình như nhau ở mọi gói. Gói chỉ mở công cụ cho giảng viên (soạn lộ trình riêng, thống kê lớp, chấm mù kép) và số sinh viên dùng được | FR-67, FR-68 | 1.6 (D034) | `billing/plans.py` (`PLAN_FEATURES` chỉ chứa công cụ của giảng viên); `test_each_step_up_adds_something_and_none_locks_learning`, `test_after_the_trial_the_free_plan_closes_staff_tools_but_never_learning` |
| BR-30 | Số bài đánh giá dự kiến của gói chỉ để **cảnh báo** quản trị viên ở 80% và 100%, không bao giờ từ chối bài của sinh viên; bài của người đang đồng thuận nghiên cứu không tính vào con số đó. Bản triển khai chạy khảo sát của đồ án để thu phí tắt (`AICEFR_BILLING`) | FR-68 | 1.6 (D034) | `BillingService.usage`; `test_assessments_over_the_monthly_figure_only_warn`, `test_with_billing_off_nothing_changes` |
| BR-31 | Hết hạn hay hạ gói **không xoá, không đóng** gì đã có: tài khoản đang có vẫn học, lộ trình đã xuất bản vẫn mở, đợt chấm đã tạo vẫn chấm nốt, xem báo cáo và tải được. Chỉ việc mới vượt gói phải chờ nâng cấp: tạo hay mở lại tài khoản sinh viên quá số cho phép, soạn lộ trình, xem thống kê lớp, tạo đợt chấm mù mới. Gói trả tiền có 14 ngày ân hạn, rồi trường về gói Miễn phí | FR-67, FR-68 | 1.6 (D034) | `billing/plans.py` (`standing`, `GRACE_DAYS`); `test_a_paid_plan_keeps_its_tools_through_grace_then_falls_back_to_free`, `test_the_plan_limits_new_student_accounts_only` |
| BR-32 | Hệ thống **không nhận, không lưu** số thẻ, tài khoản ngân hàng hay tên người trả: người trả nhập trên trang của cổng thanh toán; hệ thống chỉ giữ mã giao dịch, mã kết quả, mã ngân hàng và thời điểm | FR-69 | 1.6 (D034) | `billing/payments.py` (`PaymentResult.details`), bảng `billing_order`, `billing_event`; `test_vnpay_results_map_to_outcomes_and_a_changed_byte_is_refused` |
| BR-33 | Kết quả thanh toán chỉ được tin khi **chữ ký đúng** và **số tiền khớp đơn**; mỗi đơn được ghi nhận **một lần** dù trình duyệt và máy chủ của cổng cùng báo; mọi thông điệp của cổng về một đơn được lưu để đối soát (từ bản 1.7, thông điệp lặp y hệt được đếm trên dòng đã lưu thay vì thêm dòng); thanh toán đến muộn cho đơn đã hết hạn chờ vẫn được ghi nhận. Cổng thanh toán thử không bao giờ dùng cho bản triển khai bán thật | FR-69 | 1.6 (D034) | `BillingService.settle`, `BillingRepository.settle`; `test_a_forged_or_altered_result_is_refused`, `test_buying_through_the_sandbox_installs_the_plan_once`, `test_pending_orders_expire_and_a_late_payment_still_counts` |
| BR-34 | Cổng **thu tiền thật** — khoá Stripe `sk_live_`, địa chỉ thật của VNPay hay MoMo — chỉ chạy khi bản triển khai bật riêng `AICEFR_PAYMENTS_LIVE`; mặc định mọi cổng ở môi trường thử của chính nó. Không cổng nào ở môi trường thử — cổng thử trong ứng dụng, Stripe với khoá thử, sandbox của VNPay hay MoMo — chạy cạnh một cổng thu tiền thật: thẻ thử không bao giờ mua được gói thật | FR-71 | 1.7 (D035) | `billing/registry.py` (`build_gateways`); `test_real_money_is_never_a_default`, `test_real_money_needs_to_be_switched_on` |
| BR-35 | Kết quả của một cổng chỉ ghi nhận đơn **đặt qua chính cổng đó**, ở đúng chế độ tiền lúc đặt và về đúng phiên thanh toán đơn đã mở; khi phải hỏi lại cổng (Stripe), hệ thống chỉ hỏi về phiên do chính nó mở và chưa xong | FR-71, FR-72 | 1.7 (D035) | `BillingService.settle` (so `gateway` của đơn), `billing_api.billing_return` (`order_by_checkout`); `test_one_gateway_cannot_settle_another_gateways_order`, `test_stripe_is_asked_only_about_checkouts_this_system_opened` |
| BR-36 | Luồng đăng nhập Google chỉ đi tiếp khi cookie mang `state`, `nonce` và verifier PKCE có **chữ ký của bản triển khai**; cookie không do máy chủ ký bị bỏ trước khi hỏi Google. Sau TLS, cookie là cookie `__Host-` mà tên miền con không đặt được; địa chỉ chuyển hướng là `https` mà chưa bật `AICEFR_HTTPS_ONLY` thì luồng không bắt đầu | FR-59, FR-74 | 1.7 (D036) | `auth/google.py` (`encode_flow`, `decode_flow`), `google_api.py` (`_cookie`); `test_a_flow_cookie_this_server_did_not_sign_is_ignored`, `test_behind_tls_the_flow_cookie_is_a_host_cookie` |
| BR-37 | Trong thực nghiệm phản hồi, phản hồi của nhóm "Chỉ điểm" được **máy chủ** giữ lại, không phải trang ẩn đi; chỉ áp cho báo cáo bài đánh giá của chính người học, không bao giờ cho giảng viên, quản trị viên, bài học hay luyện tập. Chỉ sinh viên **đang cho phép dùng dữ liệu nghiên cứu** được chia nhóm; người học rời được bất cứ lúc nào và nhận lại phản hồi đầy đủ ngay; rút đồng ý nghiên cứu hay bị xoá dữ liệu cũng là rời | FR-77, FR-78 | 1.8 (D040) | `api/study_api.py` (`gate_report`); `test_score_only_arm_gets_the_score_and_nothing_more`, `test_leaving_the_study_or_closing_it_brings_feedback_back` |
| BR-38 | Trang Tiến độ chỉ gọi là **tiến bộ** khi chênh lệch vượt 1,96 lần sai số của chênh lệch tính từ **sai số đo (SEM)** đo bằng cặp bài thử lại hoặc nhập tay **kèm nguồn**; chưa có SEM thì nói là chưa đo được sai số. RMSE của mô hình không được dùng thay SEM | FR-80 | 1.8 (D042) | `research/reliable_change.py`; `test_reliable_change_verdicts`, `test_progress_says_no_error_measured_until_an_admin_sets_one` |
| BR-39 | Chẩn đoán phát âm **không phải điểm phát âm** và không vào điểm tổng: nó đếm chỗ chữ máy nghe được lệch khỏi chữ viết theo năm lỗi đặc trưng, chỉ nêu tỉ lệ khi đủ 8 lần gặp, và từ giảng viên đã sửa thành "nghe được" không tính là lỗi. Bản của cả lớp không chỉ ra ai | FR-75, FR-76 | 1.8 (D039) | `pronunciation/vietnamese.py`; `test_profile_reports_a_rate_only_from_enough_opportunities`, `test_class_profile_is_for_staff_and_names_nobody` |
| BR-40 | Model lộ trình (D046) chỉ **chọn và xếp thứ tự** bài giảng viên đã xuất bản; không viết câu chữ, không sửa bài. Mỗi bài được chọn kèm lý do. Lộ trình của sinh viên chỉ gồm bài đã xuất bản trong lộ trình đã xuất bản; lộ trình giảng viên lưu ra luôn là bản nháp | FR-81, FR-82 | 1.11 (D046, đề xuất) | `lessons/composer.py`; `test_a_draft_path_never_reaches_a_learners_plan`, `test_a_teacher_saves_the_kept_lessons_as_a_draft_path_of_copies` |

---

# 3. YÊU CẦU CHỨC NĂNG

Ký hiệu ưu tiên MoSCoW: **M** = Must (bắt buộc, W4–W8), **S** = Should (nên có, W8–W9), **C** = Could (làm nếu còn thời gian, W10), **W** = Won't (xác nhận không làm).

## 3.1. Module M1 — Quản lý phiên và nộp bài (`src/aicefr/ingest/`)

### FR-01 — Tạo phiên đánh giá

**Mô tả:** Hệ thống cho phép tạo một phiên đánh giá gắn với `speaker_id` giả danh, `task_id`, `prompt_version`, `consent_version` và `pipeline_config_version`. Thiếu bất kỳ trường version nào thì request bị từ chối.
**Ưu tiên:** M

| Acceptance Criteria |
| --- |
| **AC-01.1** — *Given* người dùng đã đăng nhập vai trò Sinh viên hoặc Giảng viên, *When* gửi `POST /api/v1/sessions` với đủ `speaker_id`, `task_id`, `prompt_version`, `consent_version`, *Then* hệ thống trả HTTP 201 kèm `session_id` dạng UUID v4 và `created_at` theo ISO-8601. |
| **AC-01.2** — *Given* request thiếu `consent_version`, *When* gọi `POST /api/v1/sessions`, *Then* hệ thống trả HTTP 422 với `reason_code = "MISSING_VERSION_FIELD"` và **không** tạo bản ghi nào trong bảng `sessions`. |
| **AC-01.3** — *Given* `speaker_id` chứa chuỗi khớp biểu thức mã số sinh viên `^[0-9]{7,10}$` hoặc chứa ký tự `@`, *When* tạo phiên, *Then* hệ thống trả HTTP 422 với `reason_code = "IDENTIFIER_LOOKS_LIKE_PII"`. |

### FR-02 — Upload file audio

**Mô tả:** Sinh viên tải lên một file audio cho một phiên. Hệ thống chấp nhận `.wav`, `.mp3`, `.m4a`, `.webm`; dung lượng ≤ 25 MB; thời lượng 20–300 giây.
**Ưu tiên:** M

| Acceptance Criteria |
| --- |
| **AC-02.1** — *Given* một `session_id` hợp lệ và file `.wav` 3 MB dài 95 giây, *When* gửi `POST /api/v1/responses` dạng multipart, *Then* hệ thống trả HTTP 202 kèm `response_id`, `qc_status = "PENDING"` và lưu file gốc vào `research_root/raw_audio/` với tên là `response_id`, không phải tên file gốc. |
| **AC-02.2** — *Given* file có phần mở rộng `.txt` hoặc nội dung không giải mã được bằng ffprobe, *When* upload, *Then* trả HTTP 415 với `reason_code = "AUDIO_UNSUPPORTED"` và **không** gọi ASR. |
| **AC-02.3** — *Given* file dung lượng 30 MB, *When* upload, *Then* trả HTTP 413 với `reason_code = "FILE_TOO_LARGE"` kèm thông điệp nêu giới hạn 25 MB. |
| **AC-02.4** — *Given* upload thành công, *When* kiểm tra bản ghi trong DB, *Then* trường `original_filename` **không** được lưu và log ứng dụng không chứa tên file gốc. |

### FR-03 — Chuẩn hóa audio

**Mô tả:** Hệ thống tạo bản làm việc mono, 16 kHz, PCM 16-bit từ file gốc bằng FFmpeg; file gốc không bị sửa đổi.
**Ưu tiên:** M

| Acceptance Criteria |
| --- |
| **AC-03.1** — *Given* file `.m4a` stereo 44,1 kHz, *When* pipeline chạy bước chuẩn hóa, *Then* sinh ra file `.wav` mono 16.000 Hz và ghi `normalized_audio_hash` (SHA-256) vào bản ghi response. |
| **AC-03.2** — *Given* pipeline đã chạy xong, *When* so sánh SHA-256 của file gốc trước và sau khi chạy, *Then* hai giá trị bằng nhau. |
| **AC-03.3** — *Given* pipeline kết thúc (thành công hoặc lỗi), *When* kiểm tra thư mục tạm, *Then* mọi file trung gian của `response_id` đó đã bị xóa. |

### FR-04 — Xem danh sách bài đã nộp

**Mô tả:** Sinh viên xem danh sách bài của chính mình kèm trạng thái; giảng viên xem danh sách bài trong lớp/đợt được phân công.
**Ưu tiên:** M

| Acceptance Criteria |
| --- |
| **AC-04.1** — *Given* sinh viên A đã nộp 3 bài, *When* gọi `GET /api/v1/responses`, *Then* trả đúng 3 bản ghi với các trường `response_id`, `task_id`, `submitted_at`, `status`, `band` (hoặc `null` nếu chưa chấm). |
| **AC-04.2** — *Given* sinh viên A gọi `GET /api/v1/responses/{id}` với `id` thuộc sinh viên B, *When* xử lý request, *Then* trả HTTP 404 (không phải 403, để không tiết lộ sự tồn tại của tài nguyên). |

### FR-05 — Kích hoạt chấm điểm bất đồng bộ

**Mô tả:** Sau khi QC đạt, hệ thống đưa response vào hàng đợi xử lý nền và cung cấp endpoint tra trạng thái.
**Ưu tiên:** M

| Acceptance Criteria |
| --- |
| **AC-05.1** — *Given* response có `qc_status = "PASS"`, *When* gọi `POST /api/v1/score` với `response_id`, *Then* trả HTTP 202 kèm `job_id` và `status = "QUEUED"` trong dưới 300 ms. |
| **AC-05.2** — *Given* một `job_id` đang chạy, *When* gọi `GET /api/v1/jobs/{job_id}`, *Then* trả một trong các giá trị `QUEUED`, `RUNNING`, `COMPLETED`, `REVIEW_REQUIRED`, `REJECTED`, `FAILED`. |
| **AC-05.3** — *Given* cùng một `response_id` được gửi chấm hai lần liên tiếp, *When* job thứ nhất chưa xong, *Then* hệ thống trả lại đúng `job_id` cũ, không tạo job trùng. |

### FR-39 — Ghi âm trực tiếp trên trình duyệt

**Mô tả:** Ngoài đường tải file lên, màn hình nộp bài cho phép sinh viên ghi âm ngay trên trình duyệt bằng `MediaRecorder`. Bản ghi sinh ra là WebM/Opus trên Chrome và Firefox, MP4/AAC trên Safari; `soundfile` không đọc được hai định dạng này nên máy chủ phải chuyển mã bằng `ffmpeg` về WAV mono 16 kHz trước khi đưa vào pipeline. Khi máy chủ không có `ffmpeg`, hoặc khi trình duyệt không hỗ trợ `MediaRecorder`, hoặc khi người dùng từ chối quyền micro, giao diện phải ẩn hoặc vô hiệu hóa lối ghi âm ngay từ đầu và luôn giữ nguyên đường tải file lên. Bản ghi từ micro đi qua **đúng** bộ QC như file tải lên, không có ngoại lệ nào.
**Ưu tiên:** S

| Acceptance Criteria |
| --- |
| **AC-39.1** — *Given* máy chủ có `ffmpeg` và trình duyệt hỗ trợ `MediaRecorder`, *When* sinh viên mở màn hình nộp bài, *Then* màn hình hiển thị đồng thời nút "Ghi âm" và vùng kéo-thả file. |
| **AC-39.2** — *Given* sinh viên ghi một đoạn 45 giây trên Chrome, *When* bấm "Dừng và nộp", *Then* trình duyệt gửi lên một blob WebM/Opus và máy chủ trả về `response_id` như luồng tải file, không có thông báo lỗi định dạng. |
| **AC-39.3** — *Given* máy chủ nhận một blob WebM/Opus hoặc MP4/AAC, *When* xử lý trước khi vào QC, *Then* máy chủ gọi `ffmpeg` chuyển mã về WAV **mono, 16 kHz, PCM 16-bit** và ghi phiên bản `ffmpeg` vào `provenance`; file gốc do trình duyệt gửi lên được giữ nguyên, không bị ghi đè (đối chiếu FR-03). |
| **AC-39.4** — *Given* chuyển mã `ffmpeg` thất bại hoặc quá 30 giây, *When* xử lý bản ghi, *Then* hệ thống trả HTTP 422 với `reason_code = "TRANSCODE_FAILED"`, hiển thị câu tiếng Việt "Không xử lý được bản ghi, vui lòng tải file lên thay thế", và **không** trả band nào. |
| **AC-39.5** — *Given* máy chủ **không** có `ffmpeg` trên `PATH`, *When* sinh viên mở màn hình nộp bài, *Then* nút "Ghi âm" không xuất hiện, chỉ còn vùng tải file, kèm dòng giải thích "Máy chủ chưa cài ffmpeg nên tạm thời chưa ghi âm trực tiếp được"; hệ thống **không** để người dùng ghi âm xong rồi mới báo lỗi (kiểm chứng bằng `GET /api/v1/health` trả `recording_enabled = false` và trang nộp bài render theo cờ này). |
| **AC-39.6** — *Given* trình duyệt không hỗ trợ `MediaRecorder`, *When* trang nộp bài tải xong, *Then* nút "Ghi âm" bị ẩn, hiện hướng dẫn "Trình duyệt này chưa hỗ trợ ghi âm, vui lòng dùng Chrome ≥ 120 / Edge ≥ 120 / Firefox ≥ 121 hoặc tải file lên", và vùng tải file vẫn dùng được bình thường. |
| **AC-39.7** — *Given* người dùng từ chối quyền truy cập micro, *When* trình duyệt trả lỗi `NotAllowedError`, *Then* nút "Ghi âm" chuyển sang trạng thái vô hiệu kèm hướng dẫn cấp lại quyền bằng tiếng Việt, không có bản ghi rỗng nào được gửi lên máy chủ, và đường tải file vẫn dùng được. |
| **AC-39.8** — *Given* đang ghi âm, *When* đồng hồ chạy, *Then* giao diện hiện thời lượng dạng `mm:ss`; dưới 20 giây nút "Dừng và nộp" bị vô hiệu kèm dòng "Cần ít nhất 20 giây"; tới 300 giây hệ thống tự dừng ghi và cảnh báo "Đã đạt mức tối đa 300 giây". |
| **AC-39.9** — *Given* một bản ghi từ micro có SNR 3 dB, *When* QC chạy, *Then* bản ghi bị từ chối với đúng reason code như file tải lên (FR-07) và người dùng thấy chẩn đoán của FR-09; không có nhánh nào miễn trừ QC cho nguồn micro. |

## 3.2. Module M2 — Kiểm tra chất lượng audio (`src/aicefr/qc/audio_qc.py`)

### FR-06 — Đo các chỉ số chất lượng audio

**Mô tả:** Hệ thống đo 5 chỉ số bằng ffprobe và librosa: `duration_sec`, `sample_rate_hz`, `clipping_ratio`, `silence_ratio`, `snr_db`.
**Ưu tiên:** M

| Acceptance Criteria |
| --- |
| **AC-06.1** — *Given* một file audio hợp lệ, *When* chạy QC, *Then* bản ghi `qc_metrics` chứa đủ 5 trường số thực nêu trên cùng `qc_config_version`. |
| **AC-06.2** — *Given* file fixture đã biết trước có 12% mẫu đạt biên độ ≥ 0,99, *When* chạy QC, *Then* `clipping_ratio` trả về trong khoảng 0,11–0,13. |
| **AC-06.3** — *Given* chạy QC hai lần trên cùng file với cùng `qc_config_version`, *When* so sánh kết quả, *Then* 5 chỉ số giống nhau tới 4 chữ số thập phân. |

### FR-07 — Áp ngưỡng QC và sinh reason code

**Mô tả:** Hệ thống so sánh chỉ số với ngưỡng cấu hình và gán `qc_status` thuộc {`PASS`, `REVIEW`, `REJECT`} kèm danh sách reason code.

Ngưỡng mặc định (`qc_config_version = "qc-v1"`, là ngưỡng candidate, chưa phải ngưỡng đã validation):

| Chỉ số | REJECT khi | REVIEW khi | PASS khi |
| --- | --- | --- | --- |
| `duration_sec` | < 20 hoặc > 300 | 20–29 | 30–300 |
| `clipping_ratio` | > 0,05 | 0,01–0,05 | < 0,01 |
| `silence_ratio` | > 0,70 | 0,50–0,70 | < 0,50 |
| `snr_db` | < 5 | 5–12 | > 12 |

**Ưu tiên:** M

| Acceptance Criteria |
| --- |
| **AC-07.1** — *Given* audio dài 14 giây, *When* chạy QC, *Then* `qc_status = "REJECT"`, `reason_codes` chứa `AUDIO_TOO_SHORT`, và bước ASR **không** được gọi. |
| **AC-07.2** — *Given* audio có `silence_ratio = 0,62` và các chỉ số khác đạt, *When* chạy QC, *Then* `qc_status = "REVIEW"`, `reason_codes` chứa `HIGH_SILENCE`, pipeline vẫn chạy tiếp nhưng response được gắn cờ chuyển giảng viên. |
| **AC-07.3** — *Given* audio vi phạm cả clipping và SNR, *When* chạy QC, *Then* `reason_codes` chứa **cả** `CLIPPING` và `NOISE_HIGH`, không chỉ mã đầu tiên. |
| **AC-07.4** — *Given* `qc_status = "REJECT"`, *When* truy vấn báo cáo, *Then* trường `band` là `null`, **không** có band mặc định nào được tạo. |

### FR-08 — Cấu hình ngưỡng QC có version

**Mô tả:** Quản trị viên thay đổi ngưỡng QC qua file cấu hình YAML có version; mỗi kết quả QC ghi lại version đã dùng.
**Ưu tiên:** S

| Acceptance Criteria |
| --- |
| **AC-08.1** — *Given* admin sửa `snr_db.reject` từ 5 sang 8 và tăng version lên `qc-v2`, *When* chấm bài mới, *Then* bản ghi QC ghi `qc_config_version = "qc-v2"`; các bản ghi cũ vẫn giữ `qc-v1`. |
| **AC-08.2** — *Given* file cấu hình thiếu trường `version`, *When* ứng dụng khởi động, *Then* ứng dụng dừng với lỗi rõ ràng, không chạy với giá trị mặc định ngầm. |

### FR-09 — Hiển thị chẩn đoán QC cho người dùng

**Mô tả:** Khi bài bị REJECT/REVIEW, giao diện hiển thị lý do bằng tiếng Việt dễ hiểu và hướng dẫn khắc phục.
**Ưu tiên:** S

| Acceptance Criteria |
| --- |
| **AC-09.1** — *Given* bài bị `REJECT` vì `NOISE_HIGH`, *When* sinh viên mở trang kết quả, *Then* giao diện hiện câu "Bản ghi có nhiều tiếng ồn nền (SNR 3,4 dB, cần trên 5 dB). Hãy thu lại ở nơi yên tĩnh hơn." và nút "Nộp lại". |
| **AC-09.2** — *Given* bài bị từ chối, *When* xem giao diện, *Then* **không** hiển thị bất kỳ band hay điểm số nào. |

## 3.3. Module M3 — Nhận dạng tiếng nói (`src/aicefr/asr/whisper_adapter.py`)

### FR-10 — Sinh transcript với word-level timestamp

**Mô tả:** Hệ thống gọi faster-whisper (model `small`, `word_timestamps=True`, `language="en"`) để sinh transcript, mốc thời gian từng từ và confidence từng từ.
**Ưu tiên:** M

| Acceptance Criteria |
| --- |
| **AC-10.1** — *Given* audio hợp lệ 90 giây, *When* ASR chạy xong, *Then* artifact ASR chứa mảng `words`, mỗi phần tử có `text`, `start_ms`, `end_ms`, `confidence` ∈ [0, 1]. |
| **AC-10.2** — *Given* artifact ASR đã sinh, *When* kiểm tra tính nhất quán, *Then* với mọi `i`, `words[i].end_ms >= words[i].start_ms` và `words[i+1].start_ms >= words[i].start_ms`. |
| **AC-10.3** — *Given* artifact ASR đã sinh, *When* đọc metadata, *Then* có đủ `asr_engine`, `asr_model`, `asr_config_version`, `transcript_version`. |

### FR-11 — Giữ nguyên filler trong transcript verbatim

**Mô tả:** Cấu hình ASR được đặt để **không** loại bỏ từ đệm; hệ thống lưu hai trường: `transcript_verbatim` (giữ `um/uh/er/ah`) và `transcript_clean` (đã lọc filler) để phục vụ hai mục đích khác nhau.
**Ưu tiên:** M

| Acceptance Criteria |
| --- |
| **AC-11.1** — *Given* fixture audio có 6 lần nói `um`/`uh` được xác nhận bằng chép tay, *When* ASR chạy, *Then* `transcript_verbatim` chứa ít nhất 4 trong 6 filler đó (≥ 66% recall). |
| **AC-11.2** — *Given* `transcript_verbatim` chứa filler, *When* sinh `transcript_clean`, *Then* mọi token thuộc tập `{um, uh, er, ah, mm, hmm}` bị loại và số từ của `transcript_clean` nhỏ hơn hoặc bằng `transcript_verbatim`. |
| **AC-11.3** — *Given* đặc trưng `filler_per_minute` được tính, *When* kiểm tra nguồn dữ liệu, *Then* nó được tính từ `transcript_verbatim`, còn đặc trưng từ vựng (TTR, MTLD) tính từ `transcript_clean`. |

### FR-12 — Xử lý lỗi ASR

**Mô tả:** Khi ASR ném ngoại lệ, timeout hoặc trả transcript rỗng, hệ thống không được tiếp tục như thành công.
**Ưu tiên:** M

| Acceptance Criteria |
| --- |
| **AC-12.1** — *Given* adapter ASR ném ngoại lệ, *When* pipeline xử lý, *Then* trạng thái response là `FAILED`, `reason_codes` chứa `ASR_FAILED`, và **không** có bản ghi feature hay score nào được tạo. |
| **AC-12.2** — *Given* ASR trả transcript có 0 từ trên audio dài 60 giây, *When* pipeline xử lý, *Then* trạng thái là `REVIEW_REQUIRED` với `reason_code = "TRANSCRIPT_INCOMPLETE"`. |
| **AC-12.3** — *Given* ASR vượt quá 180 giây xử lý, *When* timeout xảy ra, *Then* job dừng, ghi `ASR_TIMEOUT` và giải phóng tài nguyên worker. |

### FR-13 — Không ghi transcript vào log

**Mô tả:** Log vận hành chỉ chứa `response_id`, version, trạng thái, thời gian và reason code.
**Ưu tiên:** M

| Acceptance Criteria |
| --- |
| **AC-13.1** — *Given* một pipeline chạy đầy đủ trên fixture có transcript đã biết, *When* grep toàn bộ file log, *Then* không tìm thấy bất kỳ chuỗi 5 từ liên tiếp nào của transcript đó. |
| **AC-13.2** — *Given* pipeline gặp lỗi nội bộ, *When* xem thông điệp lỗi trả về API, *Then* thông điệp chứa `run_id` và `reason_code` nhưng không chứa đường dẫn hệ thống tệp tuyệt đối. |

## 3.4. Module M4 — Trích đặc trưng (`src/aicefr/features/`)

### FR-14 — Trích đặc trưng độ trôi chảy

**Mô tả:** Từ word timestamp, hệ thống tính: `speech_rate_wpm` (từ/phút tính trên tổng thời lượng), `articulation_rate_wps` (từ/giây trên thời gian có tiếng nói), `pause_ratio` (tổng thời gian pause ≥ 0,25 s / tổng thời lượng), `pause_count_per_min`, `mean_run_length_words`, `filler_per_minute`, `long_pause_count` (pause ≥ 1,0 s).
**Ưu tiên:** M

| Acceptance Criteria |
| --- |
| **AC-14.1** — *Given* transcript có 150 từ trên 100 giây, *When* trích đặc trưng, *Then* `speech_rate_wpm` = 90,0 ± 0,1. |
| **AC-14.2** — *Given* chuỗi word timestamp có 3 khoảng trống lần lượt 0,20 s, 0,40 s, 1,50 s, *When* trích đặc trưng, *Then* `pause_count_per_min` tính trên 2 pause (bỏ qua 0,20 s) và `long_pause_count` = 1. |
| **AC-14.3** — *Given* audio chỉ có 1 từ được nhận dạng, *When* trích đặc trưng, *Then* `mean_run_length_words` trả `null` kèm `reason_code = "INSUFFICIENT_TOKENS"`, **không** trả 0. |

### FR-15 — Trích đặc trưng từ vựng và độ dài

**Mô tả:** Từ `transcript_clean`, hệ thống tính: `word_count`, `mean_word_length_chars`, `ttr`, `mtld`.
**Ưu tiên:** M

| Acceptance Criteria |
| --- |
| **AC-15.1** — *Given* transcript "the cat sat on the mat", *When* tính TTR, *Then* `ttr` = 5/6 ≈ 0,8333 ± 0,0001. |
| **AC-15.2** — *Given* transcript có dưới 50 token, *When* tính MTLD, *Then* `mtld` trả `null` kèm `reason_code = "TEXT_TOO_SHORT_FOR_MTLD"` (MTLD không ổn định dưới 50 token). |
| **AC-15.3** — *Given* transcript rỗng, *When* trích đặc trưng, *Then* toàn bộ đặc trưng từ vựng là `null` và trạng thái response chuyển `REVIEW_REQUIRED`. |

### FR-16 — Trích đặc trưng chất lượng transcript

**Mô tả:** Hệ thống tính `mean_asr_confidence` (trung bình confidence của các từ), `low_conf_word_ratio` (tỷ lệ từ có confidence < 0,50) và `low_conf_words` (danh sách tối đa 20 từ có confidence thấp nhất kèm timestamp).
**Ưu tiên:** M

| Acceptance Criteria |
| --- |
| **AC-16.1** — *Given* transcript 100 từ trong đó 18 từ có confidence < 0,50, *When* trích đặc trưng, *Then* `low_conf_word_ratio` = 0,18 ± 0,001. |
| **AC-16.2** — *Given* `mean_asr_confidence` < 0,60, *When* pipeline tiếp tục, *Then* `reason_codes` chứa `ASR_LOW_CONFIDENCE` và cờ chuyển giảng viên được bật. |
| **AC-16.3** — *Given* có hơn 20 từ confidence thấp, *When* xây `low_conf_words`, *Then* danh sách chứa đúng 20 phần tử, sắp xếp tăng dần theo confidence. |

### FR-17 — Đóng gói vector đặc trưng có version

**Mô tả:** 14 đặc trưng được đóng gói thành `feature_vector` kèm `feature_version`, hash của artifact đầu vào và trạng thái hợp lệ từng đặc trưng.
**Ưu tiên:** M

| Acceptance Criteria |
| --- |
| **AC-17.1** — *Given* pipeline chạy xong, *When* đọc artifact feature, *Then* có đủ 14 khóa đặc trưng, `feature_version`, `asr_artifact_hash`, `extractor_config_version`. |
| **AC-17.2** — *Given* 3 trong 14 đặc trưng là `null`, *When* mô hình chấm nhận vector, *Then* mô hình dùng chiến lược impute đã khai báo trong `model_card.md` và ghi `imputed_features` vào kết quả, **không** thay `null` bằng 0 âm thầm. |
| **AC-17.3** — *Given* nhiều hơn 5 trong 14 đặc trưng là `null`, *When* chấm điểm, *Then* hệ thống trả `REVIEW_REQUIRED` với `reason_code = "TOO_MANY_MISSING_FEATURES"` và không trả band. |

## 3.5. Module M5 — Chấm điểm và quy band (`src/aicefr/scoring/`)

### FR-18 — Mô hình chấm trên đặc trưng

**Mô tả:** Ridge regression (scikit-learn) huấn luyện trên đặc trưng của Speak & Improve 2025, dự đoán điểm liên tục 0–6.
**Ưu tiên:** M

| Acceptance Criteria |
| --- |
| **AC-18.1** — *Given* một `feature_vector` hợp lệ, *When* gọi `FeatureScorer.predict()`, *Then* trả `score_feature` ∈ [0, 6] dạng float làm tròn 2 chữ số. |
| **AC-18.2** — *Given* cùng một `feature_vector` và cùng `model_version`, *When* dự đoán 10 lần, *Then* 10 kết quả giống hệt nhau tới 6 chữ số thập phân. |
| **AC-18.3** — *Given* mô hình được huấn luyện, *When* kiểm tra artifact, *Then* tồn tại `models/feature_ridge_{version}.joblib` kèm `metrics.json` có `rmse_dev`, `qwk_dev`, `n_train`, `seed`. |

### FR-19 — Mô hình chấm trên văn bản

**Mô tả:** BERT text grader (backbone đóng băng, chỉ huấn luyện regression head) nhận `transcript_clean`, dự đoán điểm 0–6.
**Ưu tiên:** M

| Acceptance Criteria |
| --- |
| **AC-19.1** — *Given* `transcript_clean` có ít nhất 20 token, *When* gọi `TextGrader.predict()`, *Then* trả `score_text` ∈ [0, 6]. |
| **AC-19.2** — *Given* transcript dài hơn 512 token, *When* mã hóa, *Then* hệ thống cắt còn 512 token đầu và ghi `truncated = true` vào kết quả. |
| **AC-19.3** — *Given* backbone BERT, *When* kiểm tra script huấn luyện, *Then* số tham số có `requires_grad = True` nhỏ hơn 2% tổng tham số (xác nhận không fine-tune toàn bộ). |

### FR-20 — Kết hợp hai mô hình (late fusion)

**Mô tả:** Điểm cuối là tổ hợp tuyến tính `score_final = w1 × score_feature + w2 × score_text + b`, trọng số học trên tập dev và đóng băng trong `fusion_{version}.json`.
**Ưu tiên:** M

| Acceptance Criteria |
| --- |
| **AC-20.1** — *Given* `score_feature = 3,0` và `score_text = 4,0` với `w1 = 0,4`, `w2 = 0,6`, `b = 0`, *When* fusion chạy, *Then* `score_final` = 3,60 ± 0,01. |
| **AC-20.2** — *Given* `score_text` không tính được (transcript quá ngắn), *When* fusion chạy, *Then* hệ thống dùng riêng `score_feature` và ghi `fusion_mode = "feature_only"` vào kết quả. |
| **AC-20.3** — *Given* file `fusion_{version}.json` bị thiếu, *When* ứng dụng khởi động, *Then* ứng dụng dừng với lỗi cấu hình, không rơi về trọng số mặc định 0,5/0,5. |

### FR-21 — Quy điểm 0–6 về band A2/B1/B2

**Mô tả:** Hệ thống ánh xạ điểm liên tục sang band theo bảng ngưỡng có version (`band_map_v1`), đồng thời trả khoảng cách tới ranh giới gần nhất.

| Điểm 0–6 | Band |
| --- | --- |
| < 2,50 | A2 |
| 2,50 – 4,19 | B1 |
| ≥ 4,20 | B2 |

**Ưu tiên:** M

| Acceptance Criteria |
| --- |
| **AC-21.1** — *Given* `score_final = 3,10`, *When* quy band, *Then* `band = "B1"` và `boundary_distance` = min(\|3,10 − 2,50\|, \|3,10 − 4,20\|) = 0,60. |
| **AC-21.2** — *Given* `score_final = 2,45`, *When* quy band, *Then* `band = "A2"` và `boundary_distance` = 0,05. |
| **AC-21.3** — *Given* kết quả bất kỳ, *When* đọc payload, *Then* có `band_map_version` và trường `band_status = "estimated"`; không tồn tại trường nào mang nghĩa "certified" hoặc "final". |

### FR-21a — Chấm bài dài bằng cách cắt cửa sổ

**Mô tả:** Bản ghi dài hơn mức mô hình chấm được trong một lần (hiện là khoảng 77,8 giây, suy ra từ dải huấn luyện 26,7–60,7 giây cộng dung sai) **không bị từ chối chấm**. Hệ thống cắt bản ghi thành các cửa sổ 30–60 giây, chấm riêng từng cửa sổ — mỗi cửa sổ khi đó nằm trong dải mô hình biết — rồi lấy **trung vị** làm điểm của cả bài.

Yêu cầu này sinh ra từ một sự cố đo được, không phải từ một mong muốn: một bản ghi 94 giây qua được toàn bộ kiểm tra chất lượng rồi nhận một báo cáo đầy đủ mà nội dung duy nhất là "không chấm được vì bài dài 94 giây". Nói lâu hơn lại nhận được ít hơn nói ngắn.

Ba ràng buộc lên phép cắt, mỗi ràng buộc chặn một cách ra số sai:

1. Điểm cắt phải rơi vào **khoảng lặng** do bộ tách tiếng tìm được, không rơi vào giữa từ. Một biên cắt giữa từ sẽ cắt cụt từ đó ở cửa sổ này và bỏ rơi nó ở cửa sổ kia, làm lệch mọi đặc trưng đếm.
2. **Mọi** cửa sổ phải nằm trong dải mô hình chấm được. Một cửa sổ 12 giây không phải cửa sổ ngắn mà là cửa sổ ngoài kinh nghiệm của mô hình — đúng cái lỗi mà cơ chế này sinh ra để tránh. Đuôi ngắn hơn 20 giây được gộp ngược vào cửa sổ trước.
3. Các cửa sổ **phủ kín** bản ghi, không chồng nhau và không bỏ sót, để người nói không mất một câu ở chỗ giáp ranh hay bị đếm hai lần.

**Điều bắt buộc phải nói ra.** Phép gộp này là một quy tắc **có lý lẽ nhưng chưa được kiểm định**: không có nghiên cứu nào nói trung vị điểm các cửa sổ dự đoán được đánh giá của người chấm cho cả bài. Vì vậy kết quả mang `SCORE_AGGREGATED`, hiển thị như **điểm tạm ghi rõ chưa kiểm định**, và **luôn** đi qua giảng viên. Khảo sát ở tuần 10–11 (`docs/plan/KE_HOACH_KHAO_SAT.md`) là thứ trả lời được câu này.

**Ưu tiên:** M

| Acceptance Criteria |
| --- |
| **AC-21a.1** — *Given* bản ghi dài 95 giây đạt QC, *When* pipeline chấm, *Then* báo cáo có điểm tổng khác `null`, có ít nhất 2 phần tử trong `windows`, và `reasons` chứa `SCORE_AGGREGATED`. |
| **AC-21a.2** — *Given* bản ghi bất kỳ dài tới 300 giây, *When* hệ thống lập kế hoạch cắt, *Then* mọi cửa sổ dài 30–60 giây (riêng cửa sổ cuối được phép tới 20 giây), tổng thời lượng các cửa sổ bằng đúng thời lượng bản ghi, và không có hai cửa sổ nào chồng lên nhau. |
| **AC-21a.3** — *Given* một bài được chấm theo cửa sổ, *When* router quyết định trạng thái, *Then* trạng thái là `REVIEW_REQUIRED` kể cả khi không cửa sổ nào gắn cờ gì khác. |
| **AC-21a.4** — *Given* một bài được chấm theo cửa sổ, *When* người học mở báo cáo, *Then* báo cáo **không** chứa `OUT_OF_DISTRIBUTION` ở bất kỳ đâu — một con số điểm nằm cạnh dòng chữ "bài dài quá nên không chấm được" là báo cáo tự mâu thuẫn. |
| **AC-21a.5** — *Given* một bài được chấm theo cửa sổ, *When* giảng viên mở màn duyệt, *Then* màn hình hiện từng cửa sổ kèm điểm riêng và khoảng cách giữa cửa sổ cao nhất với thấp nhất, vẽ theo đúng tỷ lệ thời gian. |

### FR-22 — Tính độ tin cậy

**Mô tả:** Hệ thống tính `confidence` ∈ [0, 1] từ ba yếu tố: `boundary_distance`, `mean_asr_confidence`, tỷ lệ đặc trưng hợp lệ; công thức và trọng số khai báo trong `calibration_{version}.json`.
**Ưu tiên:** M

| Acceptance Criteria |
| --- |
| **AC-22.1** — *Given* `boundary_distance = 0,05`, *When* tính confidence, *Then* `confidence` < 0,50. |
| **AC-22.2** — *Given* `boundary_distance ≥ 0,80`, `mean_asr_confidence ≥ 0,85` và 14/14 đặc trưng hợp lệ, *When* tính confidence, *Then* `confidence` ≥ 0,75. |
| **AC-22.3** — *Given* bất kỳ kết quả nào, *When* đọc payload, *Then* `calibration_version` có mặt và `confidence` được làm tròn 2 chữ số. |

### FR-23 — Không chấm tiêu chí Interaction

**Mô tả:** Trong bản này hệ thống chỉ trả điểm tổng thể; tiêu chí Interaction luôn là `null` với `score_status = "insufficient_evidence"`.
**Ưu tiên:** M

| Acceptance Criteria |
| --- |
| **AC-23.1** — *Given* bất kỳ response Task A hoặc Task B nào, *When* đọc payload kết quả, *Then* `criteria.interaction.level = null`, `criteria.interaction.score_status = "insufficient_evidence"`, `criteria.interaction.review_reason = "INTERACTION_MISSING"`. |
| **AC-23.2** — *Given* payload kết quả, *When* kiểm tra cách tính điểm tổng, *Then* giá trị `interaction` không tham gia vào bất kỳ phép trung bình nào (kiểm chứng bằng unit test so sánh điểm tổng khi có/không có trường interaction). |

## 3.6. Module M6 — Báo cáo có bằng chứng (`src/aicefr/report/`)

### FR-24 — Sinh bằng chứng có mốc thời gian

**Mô tả:** Hệ thống tạo tối đa 6 evidence cho mỗi báo cáo, mỗi evidence có `evidence_id`, `type`, `start_ms`, `end_ms`, `excerpt`, `metric_value`.
Các loại evidence: `LONG_PAUSE`, `FILLER_CLUSTER`, `LOW_CONFIDENCE_WORD`, `TRANSCRIPT_EXCERPT`, `SPEECH_RATE`, `LEXICAL_DIVERSITY`.
**Ưu tiên:** M

| Acceptance Criteria |
| --- |
| **AC-24.1** — *Given* transcript có 3 pause ≥ 1,0 s, *When* sinh evidence, *Then* có ít nhất 1 evidence loại `LONG_PAUSE` với `start_ms`/`end_ms` khớp pause dài nhất (sai số ≤ 50 ms). |
| **AC-24.2** — *Given* bất kỳ evidence nào, *When* truy ngược `evidence_id`, *Then* tìm được artifact ASR/feature tương ứng và `start_ms < end_ms ≤ duration_ms`. |
| **AC-24.3** — *Given* một đặc trưng có trạng thái `null`, *When* sinh evidence, *Then* **không** evidence nào được tạo từ đặc trưng đó. |
| **AC-24.4** — *Given* báo cáo đã sinh, *When* đếm evidence, *Then* số lượng ≤ 6 và không có hai evidence nào trùng khoảng thời gian quá 80%. |

### FR-25 — Sinh nhận xét theo mẫu có bằng chứng

**Mô tả:** Nhận xét được sinh từ **template cố định** (không dùng LLM sinh tự do), mỗi câu nhận xét bắt buộc tham chiếu ít nhất một `evidence_id`.
**Ưu tiên:** M

| Acceptance Criteria |
| --- |
| **AC-25.1** — *Given* báo cáo có 4 câu nhận xét, *When* kiểm tra cấu trúc, *Then* mỗi câu có mảng `evidence_refs` không rỗng và mọi `evidence_id` trong đó tồn tại trong danh sách evidence của báo cáo. |
| **AC-25.2** — *Given* không có evidence hợp lệ nào, *When* sinh nhận xét, *Then* hệ thống trả nhận xét rỗng kèm thông báo "Chưa đủ bằng chứng để đưa nhận xét", **không** sinh câu chung chung. |
| **AC-25.3** — *Given* cùng một bộ evidence, *When* sinh nhận xét 5 lần, *Then* văn bản đầu ra giống hệt nhau (tính xác định). |

### FR-26 — Đề xuất tối đa hai ưu tiên cải thiện

**Mô tả:** Hệ thống chọn tối đa 2 ưu tiên cải thiện từ tập gợi ý đã được GV Ngoại ngữ duyệt, dựa trên đặc trưng lệch xa nhất so với chuẩn của band cao hơn liền kề.
**Ưu tiên:** S

| Acceptance Criteria |
| --- |
| **AC-26.1** — *Given* `pause_ratio` cao hơn mức trung vị của band trên 1,5 độ lệch chuẩn, *When* chọn ưu tiên, *Then* ưu tiên "giảm ngập ngừng" xuất hiện trong danh sách. |
| **AC-26.2** — *Given* bất kỳ báo cáo nào, *When* đếm ưu tiên, *Then* số ưu tiên ≤ 2. |
| **AC-26.3** — *Given* `confidence` < 0,50, *When* sinh báo cáo, *Then* danh sách ưu tiên rỗng và hiển thị "Kết quả cần giảng viên xác nhận trước khi đưa gợi ý luyện tập". |

### FR-27 — Hiển thị version trên báo cáo

**Mô tả:** Mọi báo cáo hiển thị `model_version`, `feature_version`, `asr_model`, `band_map_version`, `calibration_version`, `qc_config_version`, `scored_at`.
**Ưu tiên:** M

| Acceptance Criteria |
| --- |
| **AC-27.1** — *Given* mở một báo cáo bất kỳ, *When* xem phần chân trang, *Then* đủ 7 trường version/thời gian nêu trên đều có giá trị khác rỗng. |
| **AC-27.2** — *Given* báo cáo xuất ra JSON, *When* kiểm tra schema, *Then* các trường version nằm trong object `provenance` và JSON hợp lệ theo `schemas/report_v1.json`. |

## 3.7. Module M7 — Cờ chuyển giảng viên và duyệt (`src/aicefr/review/`)

### FR-27a — Người học xem tiến độ của mình theo thời gian

**Mô tả:** Người học xem lại kết quả các bài nói của chính mình xếp theo thời gian, để trả lời câu hỏi "mình có tiến bộ không" — khác với màn danh sách bài nộp vốn trả lời "bài vừa nộp ra sao".

Yêu cầu khó của màn hình này không phải vẽ biểu đồ mà là **không nói quá**. Mô hình đang dùng có sai số cỡ nửa điểm trên chính tập kiểm định của nó, nên chênh lệch 0,2 điểm giữa hai bài nằm gọn trong sai số của dụng cụ đo.

**Ưu tiên:** S

| Acceptance Criteria |
| --- |
| **AC-27a.1** — *Given* người học có dưới 5 bài đã có điểm, *When* mở màn tiến độ, *Then* hệ thống ghi "chưa đủ dữ liệu" và **không** đưa ra nhận định tăng hay giảm. |
| **AC-27a.2** — *Given* chênh lệch giữa nhóm bài đầu và nhóm bài cuối nhỏ hơn RMSE của mô hình đang dùng, *When* hệ thống tính xu hướng, *Then* kết quả là "chưa kết luận được" kèm con số RMSE làm lý do, **không** phải một mũi tên đi lên. |
| **AC-27a.3** — *Given* biểu đồ có cả bài đã được giảng viên xác nhận và bài mới chỉ có điểm máy, *When* vẽ, *Then* hai loại được vẽ khác nhau và có chú giải — gộp chung sẽ khiến một con số chưa ai kiểm tra trông như một kết luận. |
| **AC-27a.4** — *Given* người học A mở màn tiến độ, *When* hệ thống trả dữ liệu, *Then* dữ liệu chỉ chứa bài của A. |

### FR-28 — Quy tắc sinh cờ chuyển giảng viên

**Mô tả:** Response được đưa vào hàng đợi review khi thỏa **bất kỳ** điều kiện nào trong 4 quy tắc:

| Mã quy tắc | Điều kiện | Reason code |
| --- | --- | --- |
| RV-1 | `confidence` < 0,60 | `LOW_CONFIDENCE` |
| RV-2 | `qc_status = "REVIEW"` hoặc có bất kỳ reason code QC nào | `AUDIO_QUALITY_RISK` |
| RV-3 | `mean_asr_confidence` < 0,60 hoặc `low_conf_word_ratio` > 0,20 | `ASR_LOW_CONFIDENCE` |
| RV-4 | `boundary_distance` < 0,25 | `NEAR_BAND_BOUNDARY` |

**Ưu tiên:** M

| Acceptance Criteria |
| --- |
| **AC-28.1** — *Given* `confidence = 0,55`, *When* pipeline hoàn tất, *Then* `teacher_review_required = true` và `review_reasons` chứa `LOW_CONFIDENCE`. |
| **AC-28.2** — *Given* response thỏa cả RV-2 và RV-4, *When* sinh cờ, *Then* `review_reasons` chứa đúng 2 mã, không trùng lặp. |
| **AC-28.3** — *Given* response không thỏa quy tắc nào, *When* pipeline hoàn tất, *Then* `teacher_review_required = false` nhưng `teacher_verified` vẫn là `false`. |
| **AC-28.4** — *Given* một tập 100 response có nhãn tham chiếu, *When* chạy đánh giá quy tắc cờ, *Then* script `evaluate_flags.py` sinh được bảng yield–flag rate (tỷ lệ lỗi nghiêm trọng bắt được theo tỷ lệ gắn cờ). |

### FR-29 — Hàng đợi review cho giảng viên

**Mô tả:** Giảng viên xem danh sách bài cần duyệt, sắp xếp theo mức ưu tiên (confidence thấp nhất trước), lọc theo reason code và trạng thái.
**Ưu tiên:** M

| Acceptance Criteria |
| --- |
| **AC-29.1** — *Given* 10 bài đang chờ với confidence khác nhau, *When* mở hàng đợi mặc định, *Then* bài có confidence thấp nhất nằm ở vị trí đầu tiên. |
| **AC-29.2** — *Given* giảng viên chọn lọc `reason_code = "NEAR_BAND_BOUNDARY"`, *When* áp bộ lọc, *Then* mọi bài hiển thị đều chứa mã đó trong `review_reasons`. |
| **AC-29.3** — *Given* giảng viên A đang mở bài X để duyệt, *When* giảng viên B mở cùng bài X, *Then* B thấy nhãn "Đang được [A] xem" và nút lưu bị vô hiệu hóa cho tới khi A kết thúc hoặc quá 15 phút. |
| **AC-29.4** — *Given* lớp đã có bài được chấm, *When* giảng viên mở màn thống kê lớp, *Then* màn hình hiện số bài đã nộp và số bài máy chấm được **như hai con số tách biệt** — bài máy từ chối chấm vẫn là bài đã nộp, và là loại cần người nhất. |
| **AC-29.5** — *Given* đã có ít nhất một lượt duyệt trên bài mà máy **có** đề xuất band, *When* giảng viên mở màn thống kê, *Then* màn hình hiện số lần giữ nguyên band, số lần đổi band và tỷ lệ đồng ý. Lượt duyệt trên bài máy không chấm được **không** được tính, vì đó không phải đồng ý hay không đồng ý với ai cả. |
| **AC-29.6** — *Given* chưa có lượt duyệt nào, *When* đọc tỷ lệ đồng ý, *Then* giá trị là `null` kèm câu giải thích, **không** phải `0` — trả về 0 sẽ đọc thành "giảng viên không bao giờ đồng ý với máy". |

### FR-30 — Giảng viên duyệt hoặc sửa kết quả

**Mô tả:** Giảng viên chọn "Đồng ý với AI" hoặc nhập band khác kèm lý do bắt buộc; hệ thống ghi audit record.
**Ưu tiên:** M

| Acceptance Criteria |
| --- |
| **AC-30.1** — *Given* giảng viên bấm "Đồng ý", *When* lưu, *Then* tạo bản ghi `reviews` với `action = "APPROVE"`, `final_band = ai_band`, `reviewer_id`, `reviewed_at`, và `teacher_verified` của response chuyển thành `true`. |
| **AC-30.2** — *Given* giảng viên đổi band từ B1 sang B2 nhưng để trống ô lý do, *When* bấm lưu, *Then* hệ thống từ chối với thông báo "Bắt buộc nhập lý do khi sửa kết quả AI" và không tạo bản ghi. |
| **AC-30.3** — *Given* giảng viên đã sửa band, *When* xem lại báo cáo, *Then* hiển thị đồng thời `ai_band` và `final_band`, ghi rõ "Kết quả đã được giảng viên điều chỉnh". |
| **AC-30.4** — *Given* một response đã có `teacher_verified = true`, *When* chạy lại pipeline chấm, *Then* kết quả AI mới được lưu thành version mới nhưng **không** ghi đè `final_band` đã duyệt. |

### FR-31 — Audit trail cho mọi thay đổi kết quả

**Mô tả:** Mọi hành động duyệt/sửa/thu hồi được ghi bất biến (append-only) với ai, khi nào, giá trị trước và sau.
**Ưu tiên:** M

| Acceptance Criteria |
| --- |
| **AC-31.1** — *Given* giảng viên sửa band 2 lần, *When* truy vấn `GET /api/v1/responses/{id}/audit`, *Then* trả 2 bản ghi theo thứ tự thời gian, mỗi bản có `before_value`, `after_value`, `reviewer_id` (giả danh), `reason`. |
| **AC-31.2** — *Given* một bản ghi audit đã tạo, *When* thử gọi bất kỳ endpoint nào để sửa/xóa nó, *Then* API trả HTTP 405; không có route `PUT`/`DELETE` nào cho tài nguyên audit. |

## 3.8. Module M8 — Quản trị, dữ liệu và quyền riêng tư (`src/aicefr/admin/`, `src/aicefr/storage/`)

### FR-32 — Xác thực và phân quyền theo vai trò

**Mô tả:** Hệ thống dùng đăng nhập bằng email nội bộ + mật khẩu băm (bcrypt, cost ≥ 12) và **cookie phiên có chữ ký** (`HttpOnly`, `SameSite=Lax`) tra ngược về bảng `auth_sessions` phía máy chủ; ba vai trò `student`, `teacher`, `admin`. Cơ chế phiên phía máy chủ được chọn thay cho JWT vì JWT không thu hồi được trước hạn — đăng xuất chỉ xoá bản sao phía trình duyệt còn token vẫn hợp lệ tới lúc hết hạn; với vai trò giảng viên sửa được điểm thì không thu hồi được phiên là điểm yếu thật, trong khi xoá một dòng trong bảng `auth_sessions` làm phiên mất hiệu lực ngay.
**Ưu tiên:** M

| Acceptance Criteria |
| --- |
| **AC-32.1** — *Given* tài khoản vai trò `student`, *When* gọi `GET /api/v1/review/queue`, *Then* trả HTTP 403 với `reason_code = "FORBIDDEN_ROLE"`. |
| **AC-32.2** — *Given* mật khẩu được lưu, *When* đọc bảng `users`, *Then* trường `password_hash` bắt đầu bằng `$2b$12$` và không tồn tại cột lưu mật khẩu dạng rõ. |
| **AC-32.3** — *Given* cookie phiên đã quá 8 giờ kể từ khi phát hành, *When* gọi API bất kỳ, *Then* trả HTTP 401 và yêu cầu đăng nhập lại. |
| **AC-32.4** — *Given* người dùng đang có phiên hợp lệ, *When* người dùng bấm "Đăng xuất", *Then* dòng tương ứng trong bảng `auth_sessions` bị xoá và mọi request mang lại đúng cookie đó trả HTTP 401 ngay ở lần gọi kế tiếp. |

### FR-33 — Tách bảng danh tính khỏi dữ liệu nghiên cứu

**Mô tả:** Bảng ánh xạ `identity_map` (họ tên, email, `participant_id`) nằm ở kho riêng, không nằm trong DB nghiên cứu; dữ liệu nghiên cứu chỉ dùng `speaker_id` giả danh.
**Ưu tiên:** M

| Acceptance Criteria |
| --- |
| **AC-33.1** — *Given* truy cập DB nghiên cứu, *When* liệt kê tất cả bảng và cột, *Then* không tồn tại cột nào tên `email`, `full_name`, `student_code` hoặc `phone`. |
| **AC-33.2** — *Given* một `speaker_id`, *When* thử suy ra danh tính chỉ từ DB nghiên cứu, *Then* không có đường truy vấn nào dẫn tới thông tin định danh (kiểm chứng bằng test `test_identity_separation.py`). |

### FR-34 — Xuất dữ liệu cá nhân theo yêu cầu

**Mô tả:** Sinh viên yêu cầu xuất toàn bộ dữ liệu của mình; quản trị viên tạo gói JSON gồm metadata, transcript, điểm, báo cáo.
**Ưu tiên:** S

| Acceptance Criteria |
| --- |
| **AC-34.1** — *Given* sinh viên gửi yêu cầu xuất, *When* admin chạy `POST /api/v1/admin/export/{participant_id}`, *Then* sinh file JSON chứa đủ các response của người đó và danh sách các trường dữ liệu kèm mục đích sử dụng. |
| **AC-34.2** — *Given* gói xuất đã sinh, *When* kiểm tra nội dung, *Then* không chứa dữ liệu của bất kỳ `participant_id` nào khác. |

### FR-35 — Xóa dữ liệu khi rút đồng thuận

**Mô tả:** Quản trị viên thực hiện quy trình xóa: xác minh `participant_id` → liệt kê artifact liên quan → xóa audio gốc, audio chuẩn hóa, transcript, feature, báo cáo → ghi deletion log không chứa PII.
**Ưu tiên:** M

| Acceptance Criteria |
| --- |
| **AC-35.1** — *Given* một `participant_id` có 4 response, *When* chạy `POST /api/v1/admin/withdraw/{participant_id}` ở chế độ `dry_run = true`, *Then* trả danh sách đúng 4 response và các đường dẫn artifact sẽ bị xóa, chưa xóa gì. |
| **AC-35.2** — *Given* xác nhận xóa thật, *When* lệnh hoàn tất, *Then* không còn file audio nào của `participant_id` đó trên đĩa và các bản ghi DB bị xóa hoặc đánh dấu `withdrawn = true` theo chính sách retention đã duyệt. |
| **AC-35.3** — *Given* xóa đã hoàn tất, *When* đọc deletion log, *Then* log chứa `participant_id` giả danh, số artifact đã xử lý, thời điểm, người thực hiện — và **không** chứa họ tên, email hoặc nội dung transcript. |
| **AC-35.4** — *Given* mô hình đã huấn luyện trước thời điểm rút, *When* sinh thông báo cho người dùng, *Then* thông báo nêu rõ mốc cutoff và không hứa xóa dữ liệu khỏi mô hình đã phát hành. |
| **AC-35.5** — *Given* người học có một bài chưa được giảng viên xác nhận, *When* họ tự xoá bài đó, *Then* dòng dữ liệu **và tệp ghi âm** đều biến mất, và nhật ký kiểm toán ghi lại rằng đã có một lần xoá cùng người yêu cầu — nhưng **không** giữ lại nội dung đã xoá. |
| **AC-35.6** — *Given* một bài thuộc về người học khác, *When* ai đó gọi lệnh xoá bài đó, *Then* hệ thống trả **404 chứ không phải 403** — 403 tự nó xác nhận mã bài đó có thật. |
| **AC-35.7** — *Given* một bài đã được giảng viên xác nhận, *When* người học tự xoá, *Then* hệ thống từ chối kèm lý do: kết quả đã xác nhận là bản ghi của một quyết định, và nhật ký kiểm toán đứng sau nó phải còn trỏ tới một thứ có thật. |

> **Ghi chú phạm vi.** FR-35 nay có **hai đường**, phục vụ hai tình huống khác nhau. Quản trị viên xoá theo người tham gia khi có người rút đồng thuận (các AC 35.1–35.4). Người học tự xoá **một** bài của mình cho trường hợp thường ngày — một bản ghi nói vấp muốn bỏ đi (AC 35.5–35.7). Bắt tình huống thứ hai phải nhờ người khác sẽ biến quyền xoá thành một hàng đợi.

### FR-36 — Quản lý phiên bản mô hình

**Mô tả:** Quản trị viên xem danh sách `model_version` và chọn version đang hoạt động; đổi version không ảnh hưởng kết quả đã lưu.
**Ưu tiên:** S

| Acceptance Criteria |
| --- |
| **AC-36.1** — *Given* có 2 model version, *When* admin kích hoạt version mới, *Then* các response chấm sau đó ghi version mới; các báo cáo cũ vẫn giữ version cũ. |
| **AC-36.2** — *Given* thư mục model thiếu file trọng số của version được kích hoạt, *When* admin bấm kích hoạt, *Then* hệ thống từ chối và giữ nguyên version đang chạy. |

### FR-37 — Kiểm soát nội dung log

**Mô tả:** Toàn bộ log ứng dụng dùng structured logging (JSON) với whitelist trường được phép.
**Ưu tiên:** M

| Acceptance Criteria |
| --- |
| **AC-37.1** — *Given* một bản ghi log bất kỳ, *When* kiểm tra khóa, *Then* tất cả khóa nằm trong tập cho phép {`ts`, `level`, `run_id`, `response_id`, `stage`, `status`, `reason_code`, `duration_ms`, `version`}. |
| **AC-37.2** — *Given* CI chạy, *When* thực thi `tests/test_log_privacy.py`, *Then* test quét toàn bộ log của một lần chạy pipeline đầy đủ và fail nếu phát hiện email, chuỗi số 7–10 chữ số, hoặc đoạn transcript. |

### FR-38 — Xuất hồ sơ năng lực nói

**Mô tả:** Hệ thống xuất `speaking_profile.json` cho một người học, chỉ gồm các kết quả đã có `teacher_verified = true`.
**Ưu tiên:** S

| Acceptance Criteria |
| --- |
| **AC-38.1** — *Given* người học có 3 kết quả, trong đó 2 đã được giảng viên duyệt, *When* gọi `GET /api/v1/profiles/{speaker_id}`, *Then* hồ sơ chứa đúng 2 kết quả đã duyệt. |
| **AC-38.2** — *Given* hồ sơ xuất ra, *When* validate theo `schemas/speaking_profile_v1.json`, *Then* validate pass và trường `band_status` của mọi mục là `"estimated"`. |
| **AC-38.3** — *Given* người học chưa có kết quả nào được duyệt, *When* gọi endpoint, *Then* trả HTTP 200 với mảng rỗng, **không** trả band suy đoán. |

## 3.9. Module M9 — Luyện tập theo nhiệm vụ (`src/aicefr/practice/`) — D023

Hiện thực vòng phản hồi ở mục 2.5 của đề cương: sau một bài đánh giá, người học có nhiệm vụ ngắn để luyện đúng tiêu chí yếu và biết ngay mình đã làm được gì. Bài luyện tập là bản ghi giọng nói có đồng thuận, đi qua QC, VAD và nhận dạng như bài đánh giá, nhưng **không** qua mô hình chấm và **không** vào hàng đợi giảng viên.

### FR-40 — Ngân hàng nhiệm vụ luyện tập

**Mô tả:** Hệ thống có 30 nhiệm vụ luyện tập, mỗi nhiệm vụ một tiêu chí đang chấm (Range, Accuracy, Fluency, Coherence, Phonology) ở một band (A1 đến C2, D059). Mỗi nhiệm vụ có đề bài, mục tiêu đo được bằng luật cố định (`MissionKind`), mẹo, và với tiêu chí phát âm là một đoạn văn mẫu để đọc to. Mục tiêu hiện cho người học **trước** khi ghi âm. Nhiệm vụ luyện tập không xuất hiện trong danh sách đề đánh giá.
**Ưu tiên:** S

| Acceptance Criteria |
| --- |
| **AC-40.1** — *Given* ngân hàng nhiệm vụ, *When* đếm theo tiêu chí và band, *Then* mỗi ô trong 5 × 3 có đúng một nhiệm vụ và mọi nhiệm vụ có ít nhất một mục tiêu (`test_bank_has_one_task_per_criterion_and_band`). |
| **AC-40.2** — *Given* sinh viên mở trang nộp bài đánh giá, *When* tải `/api/v1/tasks`, *Then* không có nhiệm vụ luyện tập nào trong danh sách (`test_practice_tasks_never_appear_in_the_assessment_task_list`). |
| **AC-40.3** — *Given* một đoạn văn đọc to, *When* kiểm tra nội dung, *Then* đoạn văn không chứa chữ số hay từ có hai cách viết Anh/Mỹ (`test_read_aloud_passages_have_no_digits_or_dual_spellings`). |
| **AC-40.4** — *Given* ngân hàng tăng `prompt_version` của một nhiệm vụ, *When* khởi động lại, *Then* dòng trong CSDL được cập nhật; cùng phiên bản thì không bị đụng tới (`test_bank_version_bump_updates_the_row_and_same_version_leaves_it`). |

### FR-41 — Đo mục tiêu luyện tập bằng luật, có căn cứ

**Mô tả:** Sau khi nhận dạng, mỗi mục tiêu của nhiệm vụ được đo bằng một luật cố định trên bản chép và các đoạn nói của VAD. Mục tiêu đo được thì có số đo, kết luận hoàn thành hay chưa, và chỗ trong bản ghi làm căn cứ (từ đã dùng kèm giây, khoảng lặng dài nhất kèm giây, từ trong đoạn mẫu máy chưa nghe ra). Mục tiêu không đo được thì rỗng kèm reason code, không bao giờ thành "chưa hoàn thành". Bài luyện tập không có band và không có điểm.
**Ưu tiên:** S

| Acceptance Criteria |
| --- |
| **AC-41.1** — *Given* một bài luyện hợp lệ, *When* pipeline xử lý xong, *Then* `status = COMPLETED`, `assessment` rỗng và `practice` có kết quả từng mục tiêu (`test_practice_attempt_is_measured_not_scored_and_not_routed`). |
| **AC-41.2** — *Given* VAD không trả đoạn nói nào, *When* đo khoảng lặng dài nhất, *Then* mục tiêu rỗng kèm `FEATURE_NOT_COMPUTABLE` (`test_pause_is_unmeasured_without_segments_rather_than_zero`). |
| **AC-41.3** — *Given* câu "If so, fine." đứng sau một câu có "would", *When* đếm câu điều kiện, *Then* câu đó không được tính vì không có động từ khuyết thiếu trong cùng câu (`test_conditionals_need_if_and_a_modal_in_the_same_sentence`). |
| **AC-41.4** — *Given* bài luyện không phải tiếng Anh hoặc không có lời, *When* pipeline xử lý, *Then* bài bị `REJECTED` kèm lý do thay vì chờ giảng viên (`test_non_english_practice_is_rejected_not_sent_to_a_teacher`). |

### FR-42 — Gợi ý nhiệm vụ tiếp theo bằng luật minh bạch

**Mô tả:** Hệ thống gợi ý một nhiệm vụ luyện tiếp, kèm câu giải thích vì sao. Tiêu chí ưu tiên là tiêu chí yếu nhất của bài đánh giá gần nhất (khi bài đó có chỉ báo theo tiêu chí); mức bắt đầu là band của bài đó (band giảng viên đã sửa nếu có), chưa có bài nào thì từ A2. Trong một tiêu chí, nhiệm vụ chưa hoàn thành ở band thấp nhất từ mức bắt đầu trở lên được chọn trước, rồi tới band thấp hơn, rồi tiêu chí kế tiếp; xong cả lộ trình thì gợi ý ôn lại nhiệm vụ lâu nhất chưa luyện. Hồ sơ `speaking_profile.json` thêm `next_task_id` (mã nhiệm vụ của tiêu chí yếu nhất ở band đã xác nhận); `next_task_hint` giữ nguyên nghĩa.
**Ưu tiên:** S

| Acceptance Criteria |
| --- |
| **AC-42.1** — *Given* sinh viên chưa có bài đánh giá nào, *When* mở trang luyện tập, *Then* gợi ý là nhiệm vụ độ trôi chảy A2 với căn cứ `no_assessment` (`test_new_learner_gets_an_a2_suggestion_and_the_full_path`). |
| **AC-42.2** — *Given* bài đánh giá gần nhất band B1, tiêu chí yếu nhất là Range, *When* mở trang luyện tập, *Then* gợi ý là `PR-RAN-B1` với căn cứ `weakest_criterion` (`test_suggestion_follows_the_weakest_criterion_of_the_latest_assessment`). |
| **AC-42.3** — *Given* một kết quả giảng viên đã xác nhận có tiêu chí yếu nhất Fluency, band B1, *When* xuất hồ sơ, *Then* dòng đó có `next_task_id = "PR-FLU-B1"` (`test_speaking_profile_carries_the_practice_task_for_the_weakest_criterion`). |

### FR-43 — Phản hồi sau mỗi lần luyện và thói quen luyện tập

**Mô tả:** Trang kết quả cho một lời khuyên chính (từ mục tiêu chưa hoàn thành đầu tiên), số đo của lần trước cùng nhiệm vụ để tự so, mục tiêu ngày (mặc định 2 lần luyện đã xử lý xong) và chuỗi ngày (được nghỉ một ngày mỗi tuần mà không mất chuỗi; ngày tính theo giờ Việt Nam). Không có bảng xếp hạng.
**Ưu tiên:** C

| Acceptance Criteria |
| --- |
| **AC-43.1** — *Given* hai lần luyện cùng nhiệm vụ, *When* xem kết quả lần sau, *Then* mỗi mục tiêu có số đo lần trước, kể cả khi hai lần nộp trong cùng một giây (`test_second_attempt_compares_with_the_previous_one_on_the_same_task`). |
| **AC-43.2** — *Given* có luyện ngày 1, 2, 4, 5, *When* tính chuỗi ngày 5, *Then* chuỗi là 4; nghỉ hai ngày liền thì chuỗi đứt (`test_one_rest_day_per_week_keeps_streak_but_does_not_count`). |
| **AC-43.3** — *Given* lần luyện lúc 18:30 UTC ngày 05/10, *When* xếp vào ngày, *Then* đó là ngày 06/10 theo giờ Việt Nam (`test_days_follow_vietnam_time`). |

### FR-44 — Tách bài luyện tập khỏi dữ liệu đánh giá

**Mô tả:** Bài luyện tập mang `purpose = practice`. Bài này không vào hàng đợi giảng viên, không vào bản xuất nghiên cứu, không làm lệch các con số về máy chấm trong thống kê lớp (có khối thống kê luyện tập riêng, không theo từng sinh viên), và chỉ chủ bài xem được trang kết quả luyện. Sinh viên vẫn tự xoá được bài luyện như mọi bản ghi khác (FR-35).
**Ưu tiên:** M

| Acceptance Criteria |
| --- |
| **AC-44.1** — *Given* một bài luyện đã xử lý, *When* giảng viên mở hàng đợi duyệt, *Then* bài đó không có trong hàng đợi (`test_practice_submission_gets_a_result_without_band_and_skips_the_queue`). |
| **AC-44.2** — *Given* một sinh viên có một bài đánh giá và một bài luyện, *When* quản trị viên xuất dữ liệu nghiên cứu, *Then* chỉ có bài đánh giá (`test_admin_research_export_excludes_practice`). |
| **AC-44.3** — *Given* sinh viên khác hoặc giảng viên, *When* mở kết quả luyện của người khác, *Then* nhận 404 (`test_only_the_owner_can_open_a_practice_result`). |
| AC-44.4 (đã bỏ) — Theo D048: kho MongoDB được dựng mới, không có dữ liệu nào tạo trước D023 để nâng cấp. |

## 3.9b. Module M10 — Lộ trình bài học do giáo viên soạn (`src/aicefr/lessons/`) — D025

Thay lộ trình 15 nhiệm vụ của M9 bằng các bài học có thứ tự. Mỗi bài học đi thang bốn bậc Mẫu → Có kiểm soát → Có hướng dẫn → Tự do và luôn kết thúc bằng một lượt nói tự do. Giáo viên soạn, sinh viên học. Mỗi lượt ghi âm của một bước đi qua kiểm tra chất lượng (mức riêng cho bài luyện), VAD và nhận dạng, rồi được đo bằng luật cố định. Không qua mô hình chấm, không có band, không vào hàng đợi duyệt. FR-40..FR-44 vẫn giữ cho các lượt luyện D023 đã có; trang luyện tập nay hiện lộ trình bài học.

### FR-45 — Lộ trình, chặng, bài học, bước và phiên bản

**Mô tả:** Một lộ trình gồm các chặng; mỗi chặng là một chức năng giao tiếp ở một band (A1 đến C2), có thể gắn một tiêu chí; mỗi chặng gồm các bài học; mỗi bài học gồm các bước. Giáo viên sửa bản nháp; **xuất bản** tạo một phiên bản bất biến của bài học, sinh viên chỉ thấy phiên bản đã xuất bản mới nhất. Mỗi lượt luyện ghi phiên bản bài học và phiên bản luật đo. Bài học hoàn thành khi số bước đạt ≥ tỷ lệ của bài (mặc định 80%) **và** bước nói tự do đã được làm. Lộ trình đi sáu phần theo trình độ (A1 đến C2, D059); mỗi phần gồm các chặng theo chủ đề (D027: đời sống, giáo dục, du lịch, nghề nghiệp, ẩm thực, sức khoẻ, công nghệ, môi trường, con người, xã hội). Bản cài mới có sẵn một lộ trình mẫu 24 chặng, 46 bài: 16 bài soạn đủ và 30 bài dựng từ 30 nhiệm vụ luyện tập, ghi rõ là nội dung mẫu chờ giảng viên duyệt.
**Ưu tiên:** S

| Acceptance Criteria |
| --- |
| **AC-45.1** — *Given* một bài học đã xuất bản phiên bản 1, *When* giáo viên sửa và lưu nháp mà chưa xuất bản, *Then* sinh viên vẫn nhận phiên bản 1 (`test_students_see_the_published_version_until_republished`). |
| **AC-45.2** — *Given* một lượt luyện được xử lý, *When* lưu, *Then* lượt đó ghi phiên bản bài học và phiên bản luật đo (`test_attempt_records_lesson_version_and_rules_version`). |
| **AC-45.3** — *Given* bản cài mới, *When* khởi động, *Then* có lộ trình mẫu đã xuất bản gồm sáu phần A1 đến C2, mỗi phần các chặng theo chủ đề khác nhau (A2, B1, B2 sáu chặng; A1, C1, C2 hai chặng), tổng 46 bài học, mọi bài có bước cuối là nói tự do (`test_fresh_install_seeds_the_sample_path`). |
| **AC-45.4** — *Given* một bài 5 bước, *When* sinh viên đạt 4 bước nhưng chưa làm bước tự do, *Then* bài chưa hoàn thành; làm thêm bước tự do thì hoàn thành (`test_lesson_completes_only_with_enough_passed_steps_and_the_free_step`). |

### FR-46 — Chín dạng bước và bộ đo bằng luật

**Mô tả:** Chín dạng bước: đọc to có từ gợi ý, nghe và nhắc lại, đọc rồi nói lại, đọc đoạn có chỗ trống, ghép câu từ từ khóa, trả lời có khung câu, mô tả tranh có ngân hàng từ, nói theo dàn ý, nói tự do nhiều lượt. Bộ đo dùng bản chép **không** gợi văn bản cho máy nhận dạng, căn chỉnh Levenshtein với văn bản (đã chuẩn hoá chữ, số, viết tắt, cách viết Anh/Mỹ), nhận mọi dạng của từ khóa, và chỉ đếm từ nằm trong đoạn có tiếng nói theo VAD. Từ máy không nghe ra hiện là "máy chưa nghe ra", không bao giờ là "sai"; từ nghe ra nhưng độ tin cậy thấp hiện là "chưa chắc". Ngưỡng đạt có ba mức Dễ / Vừa / Chặt do giáo viên chọn. Lượt luyện dùng mức kiểm tra chất lượng riêng: tối thiểu 1 giây thay vì 20 giây.
**Ưu tiên:** S

| Acceptance Criteria |
| --- |
| **AC-46.1** — *Given* văn bản "the people are friendly" và bản chép "the people friendly", *When* đo bước đọc to, *Then* "are" là máy chưa nghe ra, ba từ còn lại là nghe ra (`test_read_aloud_marks_each_reference_word_heard_missed_or_unsure`). |
| **AC-46.2** — *Given* từ khóa "go" và bản chép "I went to school", *When* đo bước ghép câu, *Then* từ khóa được tính (`test_keyword_counts_any_form_of_the_word`). |
| **AC-46.3** — *Given* một đoạn có hai chỗ trống, *When* sinh viên điền một từ đúng và một từ gây nhiễu, *Then* mỗi chỗ trống được xếp đúng loại (`test_gap_classifies_each_blank`). |
| **AC-46.4** — *Given* bản chép có từ nằm ngoài mọi đoạn có tiếng nói, *When* đo, *Then* từ đó không được đếm (`test_words_outside_speech_are_not_counted`). |
| **AC-46.5** — *Given* bước nói tự do ba lượt, *When* lượt 3 có quãng ngừng dài nhất ngắn hơn lượt 1, *Then* kết quả nêu thay đổi đó (`test_free_step_compares_rounds`). |
| **AC-46.6** — *Given* bản ghi 3 giây, *When* kiểm tra chất lượng, *Then* lượt luyện được nhận còn bài đánh giá bị từ chối vì quá ngắn (`test_practice_clip_qc_accepts_short_recordings_assessment_does_not`). |

### FR-47 — Giáo viên soạn bài học

**Mô tả:** Giáo viên tạo và sắp xếp lộ trình, chặng, bài học. Từ một đoạn văn mẫu, các từ khóa và một đề tự do, hệ thống dựng bài học bảy bước theo luật cố định (không dùng mô hình sinh nội dung); giáo viên sửa mọi bước. Bộ soát lỗi khi soạn cảnh báo: chữ số, cách viết Anh/Mỹ, câu quá dài so với band, văn bản quá dài so với thời gian, từ khóa không có trong văn bản, chỗ trống mà đáp án và từ gây nhiễu chỉ khác đuôi từ. Giáo viên tự ghi giọng mẫu; hệ thống chép lại giọng mẫu và cảnh báo khi nó lệch văn bản. Lộ trình xuất và nhập được dạng JSON. Chỉ giảng viên và quản trị viên được soạn.
**Ưu tiên:** S

| Acceptance Criteria |
| --- |
| **AC-47.1** — *Given* một đoạn văn mẫu và sáu từ khóa, *When* dựng bài, *Then* bài có đủ bốn bậc theo thứ tự và bước cuối là nói tự do ba lượt (`test_generator_builds_the_four_stage_ladder_from_one_text`). |
| **AC-47.2** — *Given* văn bản có chữ số và từ "colour", *When* soát lỗi, *Then* có một mục soát lỗi cho từng chỗ: chữ số ở mức cảnh báo vì máy chép lúc ra số lúc ra chữ, cách viết Anh ở mức lưu ý vì bộ đo đã coi hai cách viết là một (`test_linter_warns_about_asr_traps`). |
| **AC-47.3** — *Given* tài khoản sinh viên, *When* gọi API soạn bài, *Then* nhận HTTP 403 (`test_students_cannot_edit_paths`). |
| **AC-47.4** — *Given* giọng mẫu mà máy chép ra lệch văn bản, *When* tải lên, *Then* có cảnh báo kèm tỷ lệ từ nghe ra (`test_model_audio_that_does_not_match_its_text_is_flagged`). |
| **AC-47.5** — *Given* một lộ trình, *When* xuất rồi nhập lại, *Then* lộ trình mới có cùng chặng, bài và bước, ở trạng thái nháp (`test_path_export_import_roundtrip`). |

### FR-48 — Ôn tập giãn cách

**Mô tả:** Từ khóa, từ gợi ý, đáp án chỗ trống mà máy chưa nghe ra và bước nói tự do đã làm được đưa vào hàng ôn của sinh viên theo hộp Leitner: hẹn sau 1 ngày, đúng thì sang 3 rồi 7 ngày rồi xong, sai thì về 1 ngày. Bài ôn gợi bằng từ khóa, không cho đọc lại nguyên văn.
**Ưu tiên:** C

| Acceptance Criteria |
| --- |
| **AC-48.1** — *Given* một từ khóa máy chưa nghe ra, *When* lượt luyện được lưu, *Then* có một mục ôn hẹn ngày hôm sau theo giờ Việt Nam (`test_missed_words_are_scheduled_for_tomorrow`). |
| **AC-48.2** — *Given* một mục ôn ở hộp 1, *When* ôn đạt, *Then* hẹn sau 3 ngày; ôn không đạt thì về hộp 1 (`test_review_boxes_follow_leitner_intervals`). |

### FR-49 — Giáo viên theo dõi và sửa nhận định của máy

**Mô tả:** Giáo viên xem tỷ lệ hoàn thành theo bài, bước sinh viên hay dừng, từ cả lớp hay bị bỏ, và danh sách lượt luyện. Giáo viên nghe lại lượt luyện (sinh viên đã đồng thuận) và sửa nhận định từng từ hay kết luận đạt/chưa đạt; sửa đổi được ghi nhật ký kiểm toán và hiện cho sinh viên là "giáo viên đã xem lại". Việc này **không chặn** sinh viên và không tạo điểm. Không có bảng xếp hạng. Lượt luyện không vào hàng đợi duyệt và không vào bản xuất nghiên cứu.
**Ưu tiên:** C

| Acceptance Criteria |
| --- |
| **AC-49.1** — *Given* giáo viên sửa một từ từ "máy chưa nghe ra" thành "nghe ra", *When* sinh viên mở lại kết quả, *Then* thấy nhận định mới kèm dấu giáo viên đã xem, và nhật ký có dòng tương ứng (`test_teacher_override_updates_the_result_and_is_audited`). |
| **AC-49.2** — *Given* sinh viên có lượt luyện theo bài học, *When* giảng viên mở hàng đợi và quản trị viên xuất dữ liệu nghiên cứu, *Then* không có lượt luyện nào (`test_lesson_attempts_stay_out_of_queue_and_research_export`). |

### FR-50 — Tiến độ hằng ngày và bài học nên học tiếp

**Mô tả:** Mục tiêu ngày đo bằng **số phút thực nói** trong các lượt luyện (mặc định 3 phút), chuỗi ngày giữ luật D023 (nghỉ một ngày mỗi tuần không mất chuỗi, giờ Việt Nam). Bài nên học tiếp là bài chưa hoàn thành đầu tiên của chặng gắn tiêu chí yếu nhất của bài đánh giá gần nhất ở đúng band; không có thì là bài chưa hoàn thành đầu tiên theo thứ tự lộ trình. Luôn kèm câu giải thích.
**Ưu tiên:** C

| Acceptance Criteria |
| --- |
| **AC-50.1** — *Given* hôm nay có hai lượt nói tổng 95 giây, *When* mở trang lộ trình, *Then* mục tiêu ngày hiện 95 trên 180 giây (`test_daily_goal_counts_seconds_spoken`). |
| **AC-50.2** — *Given* bài đánh giá gần nhất band B1 có tiêu chí yếu nhất Range và lộ trình có chặng Range B1, *When* tính bài nên học, *Then* là bài chưa hoàn thành đầu tiên của chặng đó (`test_next_lesson_follows_the_weakest_criterion`). |

## 3.9c. Hoàn thiện sản phẩm — tài khoản, việc đang chờ, thang band, chuẩn bị — D028

Năm yêu cầu cho ba vai trò dùng hệ thống hằng ngày mà không cần người vận hành gõ lệnh trên máy chủ. Không đổi luồng chấm, không đổi dữ liệu nghiên cứu. Ràng buộc FR-33 giữ nguyên: hệ thống chỉ biết bút danh, mối nối bút danh – người thật nằm trên giấy.

### FR-51 — Đổi mật khẩu và quản lý phiên của chính mình

**Mô tả:** Người đã đăng nhập đổi mật khẩu ở trang `/account` khi nhập đúng mật khẩu hiện tại. Mật khẩu mới từ 8 ký tự, không quá 72 byte (giới hạn của bcrypt), không trùng bút danh, khác mật khẩu đang dùng. Đổi xong, mọi phiên khác của tài khoản kết thúc, phiên đang dùng giữ nguyên. Nhập sai mật khẩu hiện tại tính như một lần đăng nhập sai (NFR-07), nên một phiên bị lấy cắp không thành đường đoán mật khẩu không giới hạn. Người dùng tự đăng xuất được mọi thiết bị khác. Mỗi lần đổi ghi nhật ký kiểm toán, không ghi mật khẩu.
**Ưu tiên:** S

| Acceptance Criteria |
| --- |
| **AC-51.1** — *Given* hai phiên của cùng một tài khoản, *When* đổi mật khẩu ở phiên thứ nhất, *Then* phiên thứ hai nhận 401, phiên thứ nhất vẫn dùng được, mật khẩu cũ không đăng nhập được nữa, và nhật ký có dòng `account.password_change` không chứa mật khẩu (`test_password_change_needs_the_current_password_and_ends_other_sessions`). |
| **AC-51.2** — *Given* năm lần nhập sai mật khẩu hiện tại, *When* đổi lần thứ sáu dù nhập đúng, *Then* nhận 429 và tài khoản tạm khoá như khi đăng nhập sai (`test_a_wrong_current_password_is_refused_and_counts_towards_the_lockout`). |
| **AC-51.3** — *Given* mật khẩu mới ngắn hơn 8 ký tự, trùng bút danh, trùng mật khẩu đang dùng hoặc dài hơn 72 byte, *When* đổi, *Then* nhận 422 kèm lý do cụ thể (`test_the_password_policy_says_what_is_wrong`). |
| **AC-51.4** — *Given* ba phiên đang mở, *When* chọn đăng xuất khỏi các thiết bị khác, *Then* hai phiên kia kết thúc còn phiên này dùng tiếp (`test_signing_out_other_devices_keeps_this_one`). |
| **AC-51.5** — *Given* khách chưa đăng nhập, *When* mở `/account`, *Then* được đưa về trang đăng nhập; người đã đăng nhập thấy bút danh của mình và biểu mẫu đổi mật khẩu (`test_the_account_page_needs_a_login_and_shows_the_pseudonym`). |

### FR-52 — Quản trị viên cấp và quản lý tài khoản trên web

**Mô tả:** Ở tab Tài khoản của trang quản trị, quản trị viên tạo một bút danh cụ thể hoặc một dãy đánh số tiếp nối dãy đang có (SV-001, GV-001, QT-001…; tối đa 200 tài khoản một lần, tạo đủ cả dãy hoặc không tạo tài khoản nào). Mỗi tài khoản nhận một **mật khẩu tạm** 12 ký tự không có ký tự dễ nhầm (i, l, o, 0, 1), chỉ trả về một lần (máy chủ không lưu bản rõ, phản hồi mang `Cache-Control: no-store`) và in được thành phiếu có dòng họ tên ghi tay để cất ngoài hệ thống. Tài khoản đang dùng mật khẩu tạm chỉ gọi được "tôi là ai", đổi mật khẩu và đăng xuất cho tới khi đặt mật khẩu riêng; mọi trang khác chuyển về `/account`. Quản trị viên cấp lại mật khẩu tạm (mọi phiên của tài khoản đó kết thúc), tắt hoặc bật tài khoản (tắt là đăng xuất ngay, dữ liệu giữ nguyên; xoá dữ liệu vẫn là thao tác riêng ở FR-35) và gỡ khoá đăng nhập. Không tự tắt hay tự cấp lại mật khẩu cho chính mình. Mỗi thao tác ghi nhật ký kiểm toán, không ghi mật khẩu. Giảng viên và quản trị viên không tự đăng ký; chỉ sinh viên tự đăng ký (BR-03, D063, D065).
**Ưu tiên:** S

| Acceptance Criteria |
| --- |
| **AC-52.1** — *Given* đã có SV-007, *When* tạo dãy 3 tài khoản sinh viên, *Then* được SV-008..SV-010, mỗi tài khoản một mật khẩu tạm khác nhau đúng mẫu `xxxx-xxxx-xxxx`, phản hồi `no-store`, danh sách không chứa băm mật khẩu và nhật ký không chứa mật khẩu (`test_a_series_continues_the_numbering_with_one_time_passwords`). |
| **AC-52.2** — *Given* tài khoản vừa được cấp, *When* đăng nhập bằng mật khẩu tạm, *Then* chỉ API đổi mật khẩu dùng được (API khác 403), trang khác chuyển về `/account`; đổi xong thì về trang chính của vai trò và dùng bình thường (`test_a_temporary_password_opens_nothing_but_the_password_change`). |
| **AC-52.3** — *Given* sinh viên đang đăng nhập, *When* quản trị viên cấp lại mật khẩu tạm, *Then* phiên của sinh viên kết thúc và lần đăng nhập sau phải đổi mật khẩu; quản trị viên không cấp lại cho chính mình được (`test_a_reset_ends_the_sessions_and_issues_a_new_one_time_password`). |
| **AC-52.4** — *Given* tài khoản đang đăng nhập, *When* bị tắt, *Then* phiên kết thúc và không đăng nhập lại được cho tới khi bật lại (`test_a_disabled_account_is_signed_out_and_cannot_sign_in`). |
| **AC-52.5** — *Given* bút danh đã có, bút danh chứa ký tự lạ, dạng mã số sinh viên, tiền tố sai hoặc hơn 200 tài khoản, *When* tạo, *Then* bị từ chối và không tài khoản nào được tạo (`test_creating_accounts_is_all_or_nothing_and_checks_names`). |
| **AC-52.6** — *Given* tài khoản sinh viên hoặc giảng viên, *When* gọi bất kỳ API quản lý tài khoản nào, *Then* nhận 403 (`test_only_an_administrator_manages_accounts`). |
| **AC-52.7** — *Given* tài khoản bị khoá sau năm lần đăng nhập sai, *When* quản trị viên gỡ khoá, *Then* đăng nhập được ngay (`test_an_administrator_lifts_a_lockout`). |

### FR-53 — Đếm việc đang chờ trên thanh điều khiển

**Mô tả:** Thanh điều khiển hiện con số cạnh mục có việc đang chờ: với sinh viên, số bài vừa được giảng viên quyết định kể từ lần cuối mở "Bài của tôi" và số mục ôn đến hạn hôm nay; với giảng viên, số bài trong hàng đợi duyệt. Mở "Bài của tôi" thì các bài mới được đánh dấu "Mới xác nhận" trong lượt xem đó và con số trở về 0. Chỉ là con số; không gửi thư, không gửi gì ra ngoài.
**Ưu tiên:** C

| Acceptance Criteria |
| --- |
| **AC-53.1** — *Given* giảng viên vừa duyệt một bài của sinh viên, *When* sinh viên xem thanh điều khiển, *Then* có con số 1 ở "Bài của tôi", danh sách bài mang thời điểm quyết định, và sau khi mở danh sách thì con số về 0 (`test_a_teacher_decision_is_new_until_the_student_opens_their_list`). |
| **AC-53.2** — *Given* có bài chờ duyệt, *When* giảng viên xem thanh điều khiển, *Then* con số bằng số bài trong hàng đợi (`test_a_teacher_sees_how_many_responses_wait_for_review`). |
| **AC-53.3** — *Given* trang của sinh viên và của giảng viên, *When* hiển thị, *Then* mỗi con số có chỗ của nó trên thanh điều khiển (`test_the_sidebar_carries_a_slot_for_each_count`). |

### FR-54 — Trang giải thích band và giới hạn của máy

**Mô tả:** Trang `/bands`, mở cho cả khách, nói band A1 đến C2 mô tả kiểu nói nào theo năm mặt (vốn từ, ngữ pháp, độ trôi chảy, mạch lạc, phát âm dễ nghe), diễn đạt lại bằng tiếng Việt theo tinh thần thang mô tả định tính của CEFR (bản bổ sung 2020), không phải bản dịch chính thức, chờ giảng viên Ngoại ngữ duyệt. Mỗi mặt mang **một trong ba nhãn**: máy đo gián tiếp (kèm máy dùng phép đo nào), máy không đo, không đánh giá (Tương tác). Trang ghi năm ngưỡng band (hai ngưỡng giữa đọc từ mô hình đang chấm, ba ngưỡng ngoài là quy ước chưa hiệu chuẩn), nói rõ máy chỉ có một điểm tổng, và nêu giới hạn: chưa hiệu chuẩn trên giọng Việt, người nói lắp hoặc có khó khăn về giọng nói có thể bị ước lượng độ trôi chảy thấp hơn thực tế, giọng không bị trừ điểm, giảng viên quyết định cuối cùng. Báo cáo có đường dẫn tới trang này cạnh band.
**Ưu tiên:** C

| Acceptance Criteria |
| --- |
| **AC-54.1** — *Given* khách chưa đăng nhập, *When* mở `/bands`, *Then* thấy hai ngưỡng của mô hình đang chấm, ít nhất hai mặt mang nhãn "máy không đo", mặt Tương tác mang nhãn "không đánh giá", và dòng giới hạn về người nói lắp (`test_the_band_page_labels_what_the_machine_does_not_measure`). |
| **AC-54.2** — *Given* báo cáo có band, *When* hiển thị, *Then* có đường dẫn tới `/bands` (`test_the_report_links_its_band_to_the_band_page`). |

### FR-55 — Chuẩn bị trước khi nói bài đánh giá

**Mô tả:** Trang nộp bài cho chuẩn bị **30 giây** như giao thức thu dữ liệu (`KE_HOACH_KHAO_SAT.md` §5.2): đề hiện ngay trên đồng hồ đếm ngược, hết giờ thì máy tự bắt đầu ghi âm. Không bắt buộc: sinh viên bấm ghi âm, chọn "Nói ngay" hay huỷ lúc nào cũng được; đổi đề thì đồng hồ dừng. Đồng hồ chỉ hiện khi ghi âm trực tiếp được và sinh viên đã đồng thuận.
**Ưu tiên:** C

| Acceptance Criteria |
| --- |
| **AC-55.1** — *Given* sinh viên mở trang nộp bài, *When* trang hiển thị, *Then* có khối chuẩn bị 30 giây (`test_the_submit_page_offers_thirty_seconds_of_preparation`). |
| **AC-55.2** — *Given* sinh viên bấm bắt đầu chuẩn bị, *When* đồng hồ chạy rồi huỷ, *Then* đồng hồ về 30; bắt đầu lại rồi chọn "Nói ngay" thì máy ghi âm ngay và dừng được để nghe lại (`test_thirty_seconds_of_preparation_then_the_answer_is_recorded`). |

## 3.9d. Hồ sơ cá nhân, đăng nhập Google, quản lý tài khoản đầy đủ — D029

Chủ dự án yêu cầu ngày 07/10/2026 làm đầy đủ trang quản lý tài khoản và hồ sơ cá nhân, có đăng nhập bằng Google. Năm yêu cầu dưới đây giữ nguyên ba ràng buộc cũ: không tự đăng ký (FR-32), không lưu tên thật, email hay thông tin liên lạc (FR-33), không thêm thư viện.

### FR-56 — Hồ sơ cá nhân

**Mô tả:** Trang `/account` gồm bốn mục: Hồ sơ, Bảo mật, Hoạt động và (với sinh viên) Dữ liệu. Hồ sơ có ảnh đại diện là **một biểu tượng trong 15 biểu tượng và một màu trong 10 màu** (không có ảnh chụp, không có ô "tên hiển thị" để không mời người dùng gõ tên thật), mục tiêu nói mỗi ngày của sinh viên (1, 2, 3, 5 hoặc 10 phút, dùng cho vòng "Hôm nay" và chuỗi ngày ở trang Luyện tập), giao diện sáng/tối/theo hệ thống và cỡ chữ (lưu trên trình duyệt). Ảnh đại diện hiện ở thanh điều khiển và danh sách tài khoản của quản trị viên. Giá trị ngoài danh sách bị từ chối. Mỗi lần sửa ghi nhật ký kiểm toán.
**Ưu tiên:** C

| Acceptance Criteria |
| --- |
| **AC-56.1** — *Given* sinh viên đã đăng nhập, *When* chọn biểu tượng, màu và mục tiêu 5 phút, *Then* hồ sơ lưu đúng ba giá trị; biểu tượng, màu hay mục tiêu ngoài danh sách nhận 422; nhật ký ghi các trường đã sửa (`test_a_profile_takes_only_listed_avatars_and_goals`). |
| **AC-56.2** — *Given* sinh viên đổi mục tiêu từ 3 lên 10 phút, *When* mở trang Luyện tập, *Then* mục tiêu ngày là 600 giây (`test_the_daily_goal_sets_the_target_on_the_path_page`). |
| **AC-56.3** — *Given* người dùng chọn ảnh đại diện, *When* mở trang bất kỳ, *Then* thanh điều khiển vẽ đúng biểu tượng và màu đó (`test_the_sidebar_draws_the_chosen_avatar`). |
| **AC-56.4** — *Given* sinh viên và giảng viên, *When* mở `/account`, *Then* sinh viên có ba mục (Hồ sơ, Bảo mật kèm lịch sử hoạt động, Dữ liệu), giảng viên có hai mục; mục tiêu nói mỗi ngày chọn ở thẻ "Hôm nay" của trang Luyện tập (D068) (`test_the_account_page_has_three_parts_for_a_student_and_two_for_staff`). |

### FR-57 — Phiên đăng nhập xem được và đăng xuất được từng phiên

**Mô tả:** Mục Bảo mật liệt kê các phiên đang mở của tài khoản: tên thiết bị ở mức thô (trình duyệt · hệ điều hành, không lưu chuỗi user-agent đầy đủ), cách đăng nhập (mật khẩu hay Google), lúc bắt đầu, lúc hết hạn, và đánh dấu "Máy này". Người dùng đăng xuất được từng phiên; đăng xuất phiên đang dùng là đăng xuất. Không đụng được phiên của tài khoản khác.
**Ưu tiên:** C

| Acceptance Criteria |
| --- |
| **AC-57.1** — *Given* một tài khoản đăng nhập trên Chrome macOS và Safari iPhone, *When* xem danh sách phiên từ máy Chrome, *Then* thấy hai phiên đúng tên thiết bị, phiên Chrome là "máy này"; đăng xuất phiên iPhone thì phiên đó nhận 401; đăng xuất phiên đang dùng thì chính nó nhận 401 (`test_a_person_sees_their_sessions_and_ends_one`). |
| **AC-57.2** — *Given* mã phiên của tài khoản khác, *When* gửi yêu cầu đăng xuất phiên đó, *Then* nhận 404 và phiên kia vẫn dùng được (`test_sessions_of_one_account_cannot_be_ended_by_another`). |

### FR-58 — Lịch sử hoạt động của tài khoản

**Mô tả:** Mục Hoạt động liệt kê, mới nhất trước: đăng nhập (bằng mật khẩu hay Google), lần đăng nhập sai và lúc tài khoản đang tạm khoá, đổi mật khẩu, đăng xuất phiên, liên kết/gỡ Google, sửa hồ sơ, và những gì quản trị viên làm với tài khoản (cấp lại mật khẩu, tắt/bật, gỡ khoá, đổi vai trò) — ghi là "Quản trị viên", không ghi bút danh của họ. Chỉ ghi lần đăng nhập sai với bút danh có thật; chuỗi gõ vào không khớp tài khoản nào không vào nhật ký.
**Ưu tiên:** C

| Acceptance Criteria |
| --- |
| **AC-58.1** — *Given* một lần đăng nhập, một lần sai mật khẩu và một lần đổi mật khẩu, *When* xem lịch sử, *Then* có ba dòng theo thứ tự mới nhất trước, dòng đăng nhập sai ghi lý do sai mật khẩu (`test_the_history_shows_sign_ins_failed_attempts_and_changes`). |
| **AC-58.2** — *Given* quản trị viên đăng xuất mọi phiên của sinh viên, *When* sinh viên xem lịch sử, *Then* dòng đó ghi là do người khác làm (`test_what_an_administrator_did_shows_as_an_administrator`). |
| **AC-58.3** — *Given* lần đăng nhập với bút danh không tồn tại, *When* xem nhật ký kiểm toán, *Then* không có dòng nào (`test_an_unknown_pseudonym_leaves_nothing_in_the_audit_log`). |

### FR-59 — Đăng nhập bằng Google cho tài khoản đã liên kết

**Mô tả:** Khi quản trị viên cấu hình `AICEFR_GOOGLE_CLIENT_ID` và `AICEFR_GOOGLE_CLIENT_SECRET`, trang đăng nhập có nút "Đăng nhập bằng Google" và mục Bảo mật có nút "Liên kết tài khoản Google". Luồng là OpenID Connect, mã uỷ quyền kèm PKCE (S256), `state` và `nonce` ngẫu nhiên giữ trong cookie HttpOnly mười phút; mã đổi lấy ID token ở điểm cuối token của Google qua TLS, rồi kiểm issuer, audience, hạn, thời điểm cấp và nonce. **Google không bao giờ tạo tài khoản:** người dùng đăng nhập bằng bút danh, liên kết Google một lần, sau đó đăng nhập được bằng Google; tài khoản Google chưa liên kết bị từ chối. Hệ thống chỉ lưu **một mã băm một chiều** của định danh Google, không lưu email, tên hay ảnh. Một tài khoản Google chỉ liên kết với một bút danh. Có thể giới hạn theo tên miền trường (`AICEFR_GOOGLE_DOMAIN`, yêu cầu email đã xác minh). Tài khoản đã tắt không đăng nhập được; tài khoản còn mật khẩu tạm vẫn phải đổi mật khẩu (FR-52). Người dùng hoặc quản trị viên gỡ được liên kết. Từ bản 1.7, cookie của luồng có chữ ký và quản trị viên có khung cấu hình (FR-74, BR-36).
**Ưu tiên:** C

| Acceptance Criteria |
| --- |
| **AC-59.1** — *Given* máy chủ chưa cấu hình Google, *When* mở trang đăng nhập hoặc bắt đầu luồng Google, *Then* không có nút Google và luồng trả về trang đăng nhập với thông báo chưa bật (`test_google_is_off_until_configured`). |
| **AC-59.2** — *Given* máy chủ đã cấu hình, *When* bắt đầu đăng nhập, *Then* trình duyệt được chuyển tới Google với `client_id`, `redirect_uri`, `scope=openid email`, `state`, `nonce` và thử thách PKCE S256 khớp cookie HttpOnly đường dẫn `/auth/google` (`test_start_sends_the_browser_to_google_with_state_nonce_and_pkce`). |
| **AC-59.3** — *Given* sinh viên liên kết Google, *When* lần sau đăng nhập bằng chính tài khoản Google đó, *Then* vào đúng bút danh, về đúng trang định tới, phiên ghi cách đăng nhập là Google; CSDL chỉ có mã băm 64 ký tự, không có email (`test_linking_then_signing_in_with_google`). |
| **AC-59.4** — *Given* tài khoản Google chưa liên kết và đăng ký đã tắt (`AICEFR_GOOGLE_SIGNUP=0`), *When* đăng nhập bằng Google, *Then* bị từ chối, không có phiên và không có tài khoản mới (`test_with_sign_up_off_an_unlinked_google_account_cannot_sign_in_or_create_one`). |
| **AC-59.5** — *Given* `state` giả, nonce khác, audience khác, issuer lạ hoặc token hết hạn, *When* quay về từ Google, *Then* bị từ chối và không có phiên (`test_a_forged_or_stale_round_trip_is_refused`). |
| **AC-59.6** — *Given* một tài khoản Google đã liên kết với SV-001, *When* SV-002 liên kết cùng tài khoản đó, *Then* bị từ chối (`test_one_google_account_links_to_one_pseudonym`). |
| **AC-59.7** — *Given* giới hạn tên miền, *When* liên kết bằng tài khoản ngoài tên miền hoặc email chưa xác minh, *Then* bị từ chối; đúng tên miền và đã xác minh thì liên kết được (`test_the_domain_restriction_requires_a_verified_school_account`). |
| **AC-59.8** — *Given* tài khoản đã liên kết rồi bị tắt, *When* đăng nhập bằng Google, *Then* bị từ chối (`test_a_disabled_account_cannot_sign_in_with_google`). |
| **AC-59.9** — *Given* người dùng hoặc quản trị viên gỡ liên kết, *When* đăng nhập bằng Google, *Then* bị từ chối như tài khoản chưa liên kết khi đăng ký đã tắt (`test_unlinking_google_by_the_person_or_an_administrator`). |
| **AC-59.10** — *Given* đăng ký bằng Google đang bật (D063) và tài khoản Google chưa liên kết, *When* đăng nhập bằng Google, *Then* hệ thống tạo một tài khoản sinh viên bút danh ngẫu nhiên, không lưu tên hay email, mở phiên và chuyển tới trang chính của vai trò (D064 bỏ `/terms`); lần sau cùng tài khoản Google đó đăng nhập vào đúng tài khoản ấy (`test_an_unlinked_google_account_signs_up_as_a_student`, `test_the_login_page_offers_sign_up_only_when_it_is_on`). |

### FR-60 — Quản trị viên xem chi tiết, đổi vai trò, đăng xuất mọi thiết bị

**Mô tả:** Bấm vào bút danh trong danh sách mở bảng chi tiết: trạng thái, lúc tạo, lần đăng nhập gần nhất, lần đổi mật khẩu gần nhất, liên kết Google, số lần đăng nhập sai liên tiếp, các phiên đang mở và lịch sử gần đây. Từ đó quản trị viên cấp lại mật khẩu tạm, đăng xuất tài khoản khỏi mọi thiết bị (giữ mật khẩu), gỡ liên kết Google, gỡ khoá, tắt/bật, sang mục xoá dữ liệu với bút danh điền sẵn, và đổi vai trò. Không tự đổi vai trò hay tự đăng xuất mọi thiết bị của chính mình. Danh sách tải được thành CSV (không có mật khẩu hay mã băm).
**Ưu tiên:** C

| Acceptance Criteria |
| --- |
| **AC-60.1** — *Given* sinh viên SV-001, *When* quản trị viên đổi vai trò thành giảng viên, *Then* SV-001 mở được hàng đợi duyệt ngay trong phiên đang có, nhật ký ghi vai trò trước và sau; tự đổi vai trò của mình nhận 409 (`test_an_administrator_changes_a_role_but_not_their_own`). |
| **AC-60.2** — *Given* một tài khoản đăng nhập trên hai máy, *When* quản trị viên đăng xuất nó khỏi mọi thiết bị, *Then* cả hai phiên nhận 401; làm với chính mình nhận 409 (`test_an_administrator_signs_an_account_out_everywhere`). |
| **AC-60.3** — *Given* tài khoản đã liên kết Google và đang đăng nhập, *When* quản trị viên mở chi tiết, *Then* thấy liên kết Google, phiên với tên thiết bị và lịch sử có lần đăng nhập và lần liên kết, không có băm mật khẩu (`test_the_account_detail_shows_sessions_link_and_history`). |

## 3.9e. Chấm mù kép và báo cáo đồng thuận — D030

Hiện thực hạng mục 2.1 của `docs/plan/HUONG_PHAT_TRIEN_TIEP.md` và mục 6 của `docs/plan/KE_HOACH_KHAO_SAT.md`: hai giám khảo chấm mỗi bài độc lập và mù, người thứ ba phân xử khi lệch, rồi báo độ đồng thuận giữa người với người trước khi so máy với người. Luồng này tách hẳn khỏi luồng duyệt (FR-30): không đụng bảng `response` hay `review_action`. Quy tắc nghiệp vụ: BR-05, BR-18..BR-25, BR-27.

### FR-61 — Đợt chấm mù

**Mô tả:** Quản trị viên tạo đợt chấm: đặt tên, chọn từ hai giám khảo trở lên (giảng viên hoặc quản trị viên), giới hạn số bài nếu muốn. Bài đủ điều kiện là bài đánh giá có bản ghi, đã chấm xong hoặc đang chờ duyệt, của người học **đang** đồng thuận cho nghiên cứu; mặc định chỉ lấy bài chưa vào đợt nào. Mỗi bài có đúng hai giám khảo (với hơn hai giám khảo, bài đi vòng qua các cặp để tải đều), thứ tự bài xáo riêng cho từng giám khảo; mẫu bài và thứ tự sinh từ một hạt giống ghi cùng đợt. Không ai được giao một bài mà họ đã xem kết quả của máy (BR-27); bài không còn đủ hai giám khảo như thế thì để ngoài đợt và được đếm. Đợt đóng và mở lại được.
**Ưu tiên:** S

| Acceptance Criteria |
| --- |
| **AC-61.1** — *Given* ba bài đủ điều kiện và một bài của người không đồng thuận nghiên cứu, *When* tạo đợt với hai giám khảo và hạt giống 42, *Then* đợt có ba bài, sáu phiếu, mỗi giám khảo có vị trí 1..3 riêng, bài của người không đồng thuận không có mặt, và không còn bài "chưa vào đợt" nào (`test_a_batch_gives_every_eligible_response_two_raters_each_in_their_own_order`). |
| **AC-61.2** — *Given* chỉ một giám khảo, một giám khảo là sinh viên, hoặc không có bài nào đủ điều kiện, *When* tạo đợt, *Then* nhận 422 và không tạo gì (`test_a_batch_needs_two_raters_and_something_to_rate`). |
| **AC-61.3** — *Given* GV-01 đã mở báo cáo bài thứ nhất và GV-02 đã mở lịch sử bài thứ hai, *When* tạo đợt chỉ với hai người đó, *Then* nhận 422; với thêm GV-03 thì cả hai bài vào đợt nhưng không bài nào về tay người đã xem nó; thêm một bài chưa ai xem rồi tạo lại với GV-01 và GV-02 thì đợt có một bài và báo hai bài để ngoài (`test_a_teacher_who_opened_the_machine_result_is_not_drawn_to_rate_that_response`). |

### FR-62 — Phiếu chấm mù

**Mô tả:** Giám khảo mở danh sách phiếu ở `/rate` (con số phiếu chưa làm hiện trên thanh điều khiển) và chấm từng phiếu ở `/rate/{mã phiếu}`: đề bài, bản ghi phát qua địa chỉ của phiếu (không có mã bài, tên tệp trung tính), biểu mẫu năm tiêu chí và điểm tổng thang 0–6 bước 0,5, band, một dòng lý do, hoặc "không chấm được" kèm lý do (bản ghi hỏng, không nghe rõ, nói sai đề). Phiếu **không chứa** bút danh, mã bài, điểm máy hay điểm của giám khảo khác. Trong lúc còn phải chấm mù một bài, báo cáo, lịch sử duyệt, khoá duyệt và quyết định duyệt của bài đó trả 403 cho giám khảo, và hàng đợi duyệt của họ không hiện bài đó. Phiếu nộp một lần; đợt đã đóng không nhận phiếu. Mỗi lần nghe bản ghi được ghi nhật ký. Hệ thống ghi lại ai đã mở kết quả của máy cho bài nào; phiếu đang nợ của người đã xem — chẳng hạn mở báo cáo trong lúc đợt tạm đóng — không nhận điểm nữa và hiện là "không còn mù" (BR-27); quản trị viên giao lại những phiếu đó cho một giám khảo khác, giữ nguyên chỗ chấm. Quản trị viên làm giám khảo cũng được che trên màn quản trị: danh sách bài không hiện bài họ còn phải chấm mù; bản xuất nghiên cứu, báo cáo và CSV của đợt trả 409 cho tới khi họ nộp xong. Con số bài chờ duyệt trên thanh điều khiển không đếm bài bị che khỏi hàng đợi của chính người đó.
**Ưu tiên:** S

| Acceptance Criteria |
| --- |
| **AC-62.1** — *Given* bài máy chấm 4,37 · B2, *When* giám khảo mở phiếu, *Then* phiếu chỉ có các khoá đã định và không chứa mã bài, bút danh, 4.37, B2, `assessment`, `evidence`, `comments`; bản ghi tải về mang tên `bai-1.wav` và được ghi nhật ký `blind_rating` (`test_the_rating_sheet_carries_no_pseudonym_response_id_or_machine_score`). |
| **AC-62.2** — *Given* phiếu của giám khảo A, *When* giám khảo C mở, tải bản ghi hay nộp, *Then* nhận 404; sinh viên nhận 403 (`test_a_rater_cannot_open_another_raters_sheet`). |
| **AC-62.3** — *Given* giám khảo còn phải chấm mù một bài, *When* họ mở báo cáo, lịch sử hay khoá duyệt bài đó, *Then* nhận 403 và hàng đợi của họ không có bài đó; chấm xong thì mở được (`test_the_machine_result_stays_closed_to_a_rater_until_they_have_rated`). |
| **AC-62.4** — *Given* phiếu thiếu tiêu chí, điểm 6,5, điểm 3,25, band C1, lý do trống, "không chấm được" mà vẫn ghi điểm hoặc thiếu lý do, *When* nộp, *Then* nhận 422; phiếu đúng thì lưu, nộp lần hai nhận 409 (`test_a_rating_follows_the_rating_sheet_rules`). |
| **AC-62.5** — *Given* bản ghi không nghe được, *When* giám khảo chọn "không chấm được" với lý do "không nghe rõ", *Then* phiếu lưu là không chấm được, không có điểm (`test_an_unscorable_recording_is_rated_as_such`). |
| **AC-62.6** — *Given* hai phiếu chưa làm, *When* giám khảo nộp một phiếu rồi quản trị viên đóng đợt, *Then* con số trên thanh điều khiển đi từ 2 xuống 1 rồi 0, phiếu còn lại nhận 409; mở lại đợt thì nộp được (`test_open_sheets_are_counted_in_the_sidebar_and_a_closed_batch_takes_no_more`). |
| **AC-62.7** — *Given* đợt đang mở và giám khảo nhận 403 khi mở báo cáo bài của mình, *When* quản trị viên đóng đợt, giám khảo mở báo cáo, rồi đợt được mở lại, *Then* phiếu hiện "không còn mù", nộp nhận 409, không còn tính vào con số phiếu chưa làm, bài trở lại hàng đợi của họ, đợt đếm một phiếu không còn mù; giám khảo kia vẫn chấm mù bình thường (`test_a_sheet_goes_void_once_its_rater_has_seen_the_machine_result`). |
| **AC-62.8** — *Given* quản trị viên là một trong hai giám khảo của đợt, *When* họ mở danh sách bài, báo cáo một bài, bản xuất nghiên cứu, báo cáo và CSV của đợt, *Then* danh sách không có bài của đợt, báo cáo bài nhận 403, ba thứ kia nhận 409; nộp xong thì mọi thứ mở lại (`test_an_administrator_who_rates_stays_blind_on_the_administration_screens`). |
| **AC-62.9** — *Given* hai bài chờ duyệt, *When* GV-01 được giao chấm mù cả hai, *Then* con số chờ duyệt trên thanh điều khiển của GV-01 về 0, của GV-03 vẫn là 2; GV-01 chấm xong thì lại là 2 (`test_the_waiting_count_leaves_out_what_the_teacher_rates_blind`). |
| **AC-62.10** — *Given* phiếu của GV-01 không còn mù, *When* quản trị viên giao lại cho GV-02 (đang chấm bài đó), GV-04 (đã xem kết quả của máy) rồi GV-03, *Then* hai lần đầu không tạo phiếu và báo lý do bỏ qua, lần ba tạo một phiếu cho GV-03 ở đúng chỗ chấm của GV-01, phiếu cũ biến mất, đợt hết phiếu không còn mù và chấm đủ được hai phiếu; thao tác được ghi nhật ký (`test_a_void_sheet_can_be_handed_to_another_rater`). |

### FR-63 — Phân xử

**Mô tả:** Bài có hai điểm tổng lệch từ 1,0, lệch band, hoặc chỉ một bên thấy không chấm được thì cần người thứ ba. Quản trị viên chọn người phân xử cho đợt; hệ thống tạo phiếu thứ ba cho mọi bài cần phân xử mà người đó chưa chấm và chưa xem kết quả của máy (bài bị bỏ qua được đếm theo từng lý do). Phiếu phân xử cũng mù như mọi phiếu khác.
**Ưu tiên:** S

| Acceptance Criteria |
| --- |
| **AC-63.1** — *Given* hai giám khảo chấm 2,5 · A2 và 3,5 · B1 cho hai bài, *When* giao phân xử cho chính một trong hai người, *Then* không tạo phiếu nào và báo bỏ qua hai bài; giao cho người thứ ba thì người đó có hai phiếu phân xử, phiếu không chứa điểm của hai người trước, và đợt không còn bài cần phân xử (`test_a_disagreement_goes_to_a_third_rater_who_did_not_rate_it`). |
| **AC-63.2** — *Given* hai giám khảo lệch nhau trên một bài và GV-03 đã mở báo cáo bài đó, *When* giao phân xử cho GV-03, *Then* không tạo phiếu nào và báo một bài bỏ qua vì đã xem kết quả của máy (`test_an_adjudicator_who_opened_the_machine_result_is_passed_over`). |

### FR-64 — Báo cáo đồng thuận và bản xuất phiếu chấm

**Mô tả:** Quản trị viên xem báo cáo của một đợt: số bài theo từng loại, rồi **đồng thuận giữa hai giám khảo** (kappa có trọng số bậc hai trên band, ICC(2,1) khi cùng một cặp chấm mọi bài hoặc ICC(1,1) khi cặp thay đổi, trùng band, kappa trên điểm làm tròn nửa điểm, Pearson, chênh lệch tuyệt đối trung bình, ma trận nhầm lẫn, Pearson từng tiêu chí), **sau đó** máy so với điểm đối chiếu (Pearson, RMSE, kappa band, ma trận nhầm lẫn, recall và precision từng band), sai số của nhóm bài máy chuyển giảng viên so với nhóm còn lại (RQ4), thời gian chấm trung vị. Khoảng tin cậy 95% lấy mẫu lại theo người nói, hạt giống cố định, ghi trong báo cáo; mốc của kế hoạch (kappa ≥ 0,70, ICC ≥ 0,75) hiện là mốc tham khảo chưa ký. Điểm máy là kết quả trước mọi quyết định của giảng viên. Bài của người đã rút đồng thuận bị bỏ ra và được đếm. Quản trị viên tải mọi phiếu thành CSV (bút danh người học và giám khảo, điểm máy). `tools/agreement_report.py` cho cùng con số dạng Markdown và JSON. Xoá dữ liệu người học thì xoá phiếu về bài của họ.
**Ưu tiên:** S

| Acceptance Criteria |
| --- |
| **AC-64.1** — *Given* ba bài máy chấm 3,0 · B1, một bài đã được giảng viên sửa thành 5,5, hai giám khảo chấm 3,0 và 3,5, *When* xem báo cáo, *Then* khối người–người đứng trước khối máy–người, chênh lệch hai giám khảo 0,5, RMSE của máy 0,25 (so với 3,0 của máy, không phải 5,5 của giảng viên), có thời gian chấm của sáu phiếu (`test_the_report_puts_humans_first_and_compares_the_machine_before_any_review`). |
| **AC-64.3** — *Given* đợt hai bài đã chấm đủ, *When* tải CSV, *Then* có bốn dòng mang bút danh giám khảo, điểm từng tiêu chí và điểm máy; thao tác được ghi nhật ký (`test_the_export_lists_every_rating_with_rater_pseudonyms_and_the_machine_score`). |
| **AC-64.4** — *Given* phiếu chấm về bài của SV-001, *When* quản trị viên xoá dữ liệu SV-001, *Then* không còn phiếu nào về bài đó, phiếu về bài khác còn nguyên (`test_erasing_a_participant_erases_what_raters_said_about_them`). |
| **AC-64.5** — *Given* một đợt đã chấm, *When* chạy `tools/agreement_report.py`, *Then* báo cáo JSON trùng với báo cáo trên màn hình, Markdown đặt mục người–người trước mục máy–người và không chứa mã bài (`test_the_command_line_report_gives_the_numbers_of_the_screen`). |
| **AC-64.6** — *Given* tài khoản giảng viên, *When* gọi API quản lý đợt, báo cáo hay bản xuất, *Then* nhận 403; đợt không tồn tại nhận 404 (`test_only_an_administrator_runs_batches`). |

## 3.9f. Thành tựu và nhịp luyện của chính mình — D032

Giữ người học quay lại luyện mà không biến việc luyện thành cuộc đua. Mở rộng cơ chế thói quen của D023 (mục tiêu ngày, chuỗi ngày có một ngày nghỉ mỗi tuần) bằng những gì các ứng dụng học hiện nay dùng — thành tựu, kỷ lục, so với tuần trước — và bỏ đi phần gây hại: bảng xếp hạng, phần thưởng dựa trên điểm, lời đe doạ mất chuỗi. Không đụng luồng chấm, hàng đợi duyệt hay dữ liệu nghiên cứu; giảng viên không thấy thành tựu của người học. Quy tắc nghiệp vụ: BR-04, BR-06, BR-28.

### FR-65 — Thành tựu ghi công sức luyện tập

**Mô tả:** Người học có 17 thành tựu trong năm nhóm: **Đều đặn** (chuỗi 3, 7 và 30 ngày; đủ mục tiêu ngày 1 và 10 ngày; quay lại sau ba ngày trở lên không luyện), **Thời gian nói** (lượt nói đầu tiên, 10 phút, 60 phút), **Lộ trình** (bài học đầu tiên, 10 bài học, xong một chặng), **Kiên trì** (một lượt nói tự do, qua một bước mà lần trước chưa qua, 10 lượt ôn), **Đánh giá** (bài đánh giá đầu tiên có kết quả; năm bài — đủ để trang Tiến độ nói về xu hướng). Chỉ đếm lượt luyện mà máy đo được tiếng nói, theo ngày giờ Việt Nam và mục tiêu ngày của chính người học; **không** dựa vào điểm, band hay tỷ lệ đạt và không so với ai (BR-28). Hệ thống xét thành tựu sau mỗi lượt luyện và lượt ôn, khi mở trang Luyện tập và khi mở danh sách thành tựu; đạt lúc nào lưu lúc đó, **không bao giờ lấy lại**. Lượt nói vừa đạt thành tựu được báo một lần trên trang bài học. Trang Luyện tập có thẻ Thành tựu: số đã đạt trên tổng, số mới, ba cái gần nhất, cái gần đạt nhất kèm thanh tiến độ. Trang Tiến độ của tôi có danh sách đầy đủ theo nhóm: cái đã đạt ghi ngày đạt, cái chưa đạt ghi mức đã làm trên mức cần, cái mới đạt mang nhãn "Mới" một lần rồi được đánh dấu đã xem. Chỉ chính người học đọc được thành tựu của mình; thành tựu có trong bản xuất dữ liệu cá nhân và bị xoá cùng dữ liệu người học.
**Ưu tiên:** S

| Acceptance Criteria |
| --- |
| **AC-65.1** — *Given* người học chưa có lượt luyện nào, *When* ghi hai lượt liền nhau, *Then* lượt thứ nhất trả về đúng một thành tựu "Lượt nói đầu tiên", lượt thứ hai không trả về thành tựu nào, và thành tựu được lưu là chưa xem (`test_a_first_recording_is_congratulated_once`). |
| **AC-65.2** — *Given* hai ngày luyện liên tiếp, *When* mở danh sách, *Then* có 17 mục trong năm nhóm, một mục đã đạt, chuỗi 3 ngày ghi 2/3 và chưa đạt, 10 phút ghi theo phút; phản hồi không có điểm, band hay xếp hạng; người chưa đăng nhập nhận 401 (`test_the_list_shows_how_far_each_one_is_without_a_score`). |
| **AC-65.3** — *Given* hai người học cùng có thành tựu mới, *When* một người đánh dấu đã xem, *Then* chỉ thành tựu của người đó hết "mới", mã không có thật không được tính, danh sách quá 17 mã nhận 422 (`test_new_achievements_are_marked_seen_by_their_owner_only`). |
| **AC-65.4** — *Given* người học đã đạt "Thử lại và qua", *When* giảng viên sửa lượt qua thành chưa qua và người học xoá lượt chưa qua trước đó, *Then* thành tựu vẫn còn (`test_an_achievement_is_never_taken_back`). |
| **AC-65.5** — *Given* lượt luyện lúc 00:30 ngày 6/10 giờ Việt Nam (vẫn là 5/10 theo UTC) giữa các ngày 3, 4, 5 và 7/10, *When* mở danh sách, *Then* chuỗi dài nhất là 5 ngày; đổi mục tiêu ngày từ 3 phút xuống 1 phút thì số ngày đủ mục tiêu tăng từ 1 lên 6; luyện lại sau ba ngày không luyện được tính là "Quay lại" (`test_habit_achievements_count_vietnam_days_and_the_learners_goal`). |
| **AC-65.6** — *Given* chặng đầu của lộ trình mẫu, *When* người học hoàn thành bài thứ nhất rồi mọi bài còn lại, *Then* "Bài học đầu tiên" đạt ngay sau bài thứ nhất, "Xong một chặng" chỉ đạt khi xong cả chặng (`test_completing_a_lesson_and_a_unit_reach_the_path_achievements`). |
| **AC-65.7** — *Given* một mục ôn đến hạn, *When* người học nói lượt ôn, *Then* phản hồi có danh sách thành tựu và "Mười lượt ôn" ghi 1/10 (`test_review_attempts_count_towards_the_review_achievement`). |
| **AC-65.8** — *Given* người học có lần lượt năm bài đánh giá có kết quả, *When* mở danh sách sau bài thứ nhất và sau bài thứ năm, *Then* "Bài đánh giá đầu tiên" rồi "Đủ để thấy xu hướng" lần lượt đạt, và trang Tiến độ bắt đầu nói về xu hướng (`test_assessments_with_a_result_count_towards_the_assessment_achievements`). |
| **AC-65.9** — *Given* hai người học có thành tựu, *When* một người tải dữ liệu cá nhân rồi quản trị viên xoá dữ liệu người đó, *Then* bản xuất có thành tựu kèm tên và mục đích, xoá xong không còn thành tựu nào của người đó, của người kia còn nguyên (`test_the_personal_export_and_erasure_cover_achievements`). |
| **AC-65.10** — *Given* người học mới trên trình duyệt, *When* nộp lượt nói đầu tiên, mở trang Luyện tập rồi bấm "Xem tất cả", *Then* thấy thông báo "Thành tựu mới: Lượt nói đầu tiên", thẻ ghi "1 mới", ô thành tựu mang nhãn "Mới", ô chưa đạt có thanh tiến độ; tải lại trang thì không còn ô nào "Mới" và trang không có chữ "band" (`test_a_first_recording_is_congratulated_then_listed_as_new_once`). |

### FR-66 — Nhịp luyện của chính mình: kỷ lục, ngày nghỉ được tính, so với tuần trước

**Mô tả:** Thẻ Hôm nay của trang Luyện tập thêm ba điều, đều chỉ so người học với chính họ: **kỷ lục** — chuỗi ngày dài nhất từng đạt, hoặc dòng "Đang là kỷ lục của bạn" khi chuỗi hiện tại là dài nhất; **ngày nghỉ được tính** — ngày không luyện mà chuỗi vẫn giữ theo luật một ngày nghỉ mỗi tuần của D023 — vẽ trên dải bảy ngày bằng ô viền đứt có chú thích, để người học thấy luật thay vì đoán; và **thời gian nói của bảy ngày qua đặt cạnh bảy ngày trước đó**. Không có lời nhắc "sắp mất chuỗi", không đếm ngược.
**Ưu tiên:** S

| Acceptance Criteria |
| --- |
| **AC-66.1** — *Given* chuỗi năm ngày đã qua và chuỗi hiện tại ba ngày có một ngày nghỉ hai hôm trước, *When* mở trang Luyện tập, *Then* API trả chuỗi 3, kỷ lục 5, ngày nghỉ đúng ngày đó, 120 giây bảy ngày qua và 150 giây bảy ngày trước; thẻ Thành tựu có ba thành tựu mới và "Tròn một tuần" 5/7 là cái gần đạt nhất (`test_the_practice_page_shows_the_record_rest_days_and_last_week`). |
| **AC-66.2** — *Given* lịch sử như AC-66.1 trên trình duyệt, *When* mở trang Luyện tập, *Then* thẻ Hôm nay ghi "3 ngày liên tiếp", "Kỷ lục của bạn: 5 ngày", đúng một ô ngày nghỉ có chú thích "nghỉ, chuỗi vẫn giữ" và "7 ngày qua: 2 phút" (`test_the_week_shows_the_record_and_the_rest_day`). |
| **AC-66.3** — *Given* các ngày luyện có một chuỗi bảy ngày và một chuỗi qua ngày nghỉ, *When* tính kỷ lục, *Then* kỷ lục là con số lớn nhất người học từng thấy trên thẻ Hôm nay (`test_the_longest_streak_is_the_best_the_learner_was_ever_shown`). |
| **AC-66.4** — *Given* chuỗi có một ngày nghỉ, và hai ngày nghỉ cách nhau dưới bảy ngày, *When* tính ngày nghỉ được tính, *Then* chỉ ngày nghỉ chuỗi thật sự dùng được nêu tên (`test_the_rest_days_of_the_current_streak_are_named`). |

## 3.9g. Gói dịch vụ của trường và thanh toán — D033, D034

Trường — khoa, trung tâm ngoại ngữ — là bên mua; sinh viên không trả tiền và không thấy lời mời mua nào (BR-29). Phân tích ba phương án và lý do chọn bán cho trường nằm ở `docs/plan/DE_XUAT_GOI_DICH_VU.md` (D033, còn ở trạng thái đề xuất); mục này đặc tả phần đã làm theo yêu cầu của chủ dự án (D034). Mọi thứ trong mục chỉ chạy khi bản triển khai bật thu phí (`AICEFR_BILLING`); tắt — mặc định — thì hệ thống chạy như trước, không giới hạn gì. Không có tiền thật nào được thu trong đồ án: cổng mặc định là cổng thanh toán thử; cổng VNPay có sẵn nhưng chỉ bật khi có mã website và chuỗi bí mật VNPay cấp cho một pháp nhân. Quy tắc nghiệp vụ: BR-03, BR-12, BR-26, BR-29..BR-33.

### FR-67 — Thang gói: Miễn phí, Dùng thử, Chuẩn, Nâng cao

**Mô tả:** Bật thu phí, bản triển khai bắt đầu **Dùng thử** ở lần đầu có người hỏi tới gói: 30 ngày, mọi tính năng, mặc định 50 sinh viên, chỉ một lần. Hết dùng thử, trường ở gói **Miễn phí**: tối đa 30 sinh viên, mọi thứ của người học, hàng đợi duyệt, lộ trình mẫu. Gói **Chuẩn** thêm soạn lộ trình riêng của trường (tạo, sửa, xuất bản, nhập, ghi giọng mẫu, hình) và thống kê lớp cùng theo dõi từng bài học; gói **Nâng cao** thêm tạo đợt chấm mù kép và báo cáo đồng thuận giữa giảng viên. Mỗi bậc chỉ thêm, không bớt. Gói trả tiền hết hạn còn 14 ngày ân hạn rồi về Miễn phí. Tab "Gói dịch vụ" của trang Quản trị so sánh ba gói cạnh nhau (dòng có ở mọi gói, dòng mỗi bậc thêm, số sinh viên, số bài đánh giá dự kiến, hỗ trợ), đánh dấu gói đang dùng, và hiện gói đang dùng, mức đang dùng, đơn hàng, tên tổ chức, ô cài mã giấy phép. Giảng viên đọc được gói và công cụ nó mở qua một API riêng; trang soạn lộ trình nói rõ khi gói chưa có soạn bài riêng.
**Ưu tiên:** S

| Acceptance Criteria |
| --- |
| **AC-67.1** — *Given* bản triển khai không bật thu phí, *When* quản trị viên tạo 200 tài khoản sinh viên, giảng viên tạo lộ trình và xem thống kê lớp, *Then* mọi việc thành công, tab Gói dịch vụ báo đang tắt kèm bảng so sánh, báo giá và đặt đơn nhận 409, không giấy phép nào được tạo (`test_with_billing_off_nothing_changes`). |
| **AC-67.2** — *Given* bật thu phí lần đầu, *When* quản trị viên mở tab hai lần, *Then* có đúng một gói Dùng thử 30 ngày với mọi tính năng; bảng so sánh ghi Miễn phí tối đa 30 sinh viên không công cụ nào, Chuẩn hai công cụ, Nâng cao ba (`test_the_first_look_starts_one_trial_with_everything`). |
| **AC-67.3** — *Given* ngày sau khi hết dùng thử, *When* giảng viên tạo lộ trình, xem thống kê lớp, mở hàng đợi, và sinh viên luyện, nộp bài, xem tiến độ, *Then* gói là Miễn phí; soạn lộ trình và thống kê nhận 403 nêu gói Chuẩn và Nâng cao; hàng đợi và mọi việc của sinh viên vẫn chạy; tạo thêm 5 sinh viên được (`test_after_the_trial_the_free_plan_closes_staff_tools_but_never_learning`). |
| **AC-67.4** — *Given* gói Chuẩn đã mua, *When* tới ngày thứ 14 sau khi hết hạn rồi ngày thứ 15, *Then* lần đầu còn gói Chuẩn ở trạng thái ân hạn với đủ công cụ, lần sau là Miễn phí kèm gói vừa hết (`test_a_paid_plan_keeps_its_tools_through_grace_then_falls_back_to_free`). |
| **AC-67.5** — *Given* lần lượt Dùng thử, Chuẩn, Nâng cao, *When* giảng viên tạo lộ trình, xem thống kê lớp và quản trị viên tạo đợt chấm mù, *Then* Dùng thử và Nâng cao mở cả ba, Chuẩn từ chối tạo đợt chấm mù với lời nêu gói Nâng cao, đợt đã có vẫn xem được (`test_each_plan_opens_its_staff_tools`). |
| **AC-67.6** — *Given* bảng gói, *When* so các bậc, *Then* công cụ của gói chỉ là ba công cụ của giảng viên, Miễn phí không có công cụ nào, mỗi bậc chứa trọn bậc dưới, Dùng thử bằng Nâng cao (`test_each_step_up_adds_something_and_none_locks_learning`). |

### FR-68 — Số sinh viên và số bài đánh giá dự kiến

**Mô tả:** Gói đang dùng quy định số tài khoản sinh viên được bật cùng lúc. Tạo tài khoản sinh viên (một hay theo dãy), bật lại tài khoản sinh viên đã tắt, đổi vai trò một tài khoản đang bật sang sinh viên mà vượt số đó thì nhận 409 với lời nói rõ gói, số cho phép, số đang có, còn lại bao nhiêu; tạo theo dãy vẫn là tất cả hoặc không (BR-12). Tài khoản giảng viên và quản trị không tính. Không tài khoản nào đang có bị tắt vì gói. Mỗi gói kèm một số bài đánh giá dự kiến mỗi sinh viên mỗi tháng (Miễn phí 2, Chuẩn 4, Nâng cao và Dùng thử 8); tab Gói dịch vụ đếm bài của tháng theo giờ Việt Nam, bỏ bài của người đang đồng thuận nghiên cứu, và cảnh báo ở 80% và 100% — không bao giờ từ chối bài (BR-30).
**Ưu tiên:** S

| Acceptance Criteria |
| --- |
| **AC-68.1** — *Given* gói cho 3 sinh viên, *When* tạo 4 tài khoản theo dãy, rồi 3, rồi 1, rồi 2 giảng viên, tắt một sinh viên, tạo 1, bật lại người đã tắt, đổi một giảng viên thành sinh viên, *Then* 409 không tạo ai, 200, 409, 200, 200, 200, 409, 409; một tài khoản có sẵn vượt số vẫn đăng nhập được (`test_the_plan_limits_new_student_accounts_only`). |
| **AC-68.2** — *Given* mức dự kiến 24 bài, *When* có 20 bài của người không đồng thuận nghiên cứu và 4 bài của người đồng thuận, rồi thêm 4 bài, *Then* tab đếm 20 và 4 riêng, cảnh báo 80% rồi 100%, và cả hai sinh viên vẫn nộp được bài (`test_assessments_over_the_monthly_figure_only_warn`). |

### FR-69 — Mua, nâng cấp và gia hạn qua cổng thanh toán

**Mô tả:** Quản trị viên chọn gói (Chuẩn hoặc Nâng cao), số sinh viên (10–5000) và thời hạn (6 tháng, hoặc 12 tháng giảm 15%), xem báo giá rồi bấm thanh toán. Báo giá nói loại giao dịch và ngày chạy: đang Miễn phí hay Dùng thử thì **mua mới** từ hôm nay; cùng gói cùng số sinh viên thì **gia hạn** nối tiếp; gói cao hơn hay nhiều sinh viên hơn thì **nâng cấp** từ hôm nay, trừ phần chưa dùng của gói trả tiền đang có theo ngày; gói thấp hơn hay ít sinh viên hơn thì bắt đầu khi gói đang có kết thúc. Phần phải trả dưới 10.000 đ được miễn, và đơn bằng 0 kích hoạt ngay không qua cổng. Đơn chờ thanh toán 15 phút; một đơn mới thay đơn đang chờ. Trình duyệt được chuyển tới trang của cổng; cổng báo kết quả về hai đường — trình duyệt quay lại trang kết quả và máy chủ của cổng gọi địa chỉ thông báo — và hệ thống chỉ ghi nhận kết quả đúng chữ ký, đúng số tiền, một lần (BR-33). Thanh toán xong, gói có hiệu lực theo báo giá, quản trị viên xem và in được biên nhận (không phải hoá đơn giá trị gia tăng). Cổng mặc định là cổng thử ngay trong ứng dụng, không có tiền thật; cổng VNPay (bản 2.1.0) bật bằng biến môi trường. Từ bản 1.7, nhiều cổng chạy cùng lúc và có thêm Stripe, MoMo (FR-71..FR-73).
**Ưu tiên:** S

| Acceptance Criteria |
| --- |
| **AC-69.1** — *Given* gói Dùng thử, *When* mua Chuẩn 50 sinh viên 6 tháng qua cổng thử, rồi trình duyệt và cổng báo lại cùng kết quả, *Then* báo giá 3.000.000 đ loại mua mới; gói Chuẩn 50 sinh viên có hiệu lực với tên tổ chức; đơn đã thanh toán có mã giao dịch; lần báo lại nhận "Order already confirmed"; có đúng hai giấy phép; biên nhận ghi số tiền và câu không phải hoá đơn; sự kiện của đơn ghi mỗi thông điệp khác nhau một lần — thông báo của cổng được áp dụng, lần trả về không — và đếm mỗi lần lặp y hệt trên dòng của nó (từ bản 1.7) (`test_buying_through_the_sandbox_installs_the_plan_once`). |
| **AC-69.2** — *Given* mua Chuẩn 100 sinh viên 12 tháng, *When* thanh toán, *Then* giá 12.000.000 đ, giảm 1.800.000 đ, trả 10.200.000 đ, và biên nhận có dòng giảm khi trả theo năm học (`test_a_school_year_is_discounted_and_shown_on_the_receipt`). |
| **AC-69.3** — *Given* hai đơn, *When* một thanh toán không thành công và một bị huỷ, *Then* trang kết quả nói đúng từng trường hợp, gói vẫn là Dùng thử, không có biên nhận (`test_a_failed_or_cancelled_payment_changes_nothing`). |
| **AC-69.4** — *Given* một đơn chờ, *When* gửi kết quả sai chữ ký, kết quả đúng chữ ký nhưng sai số tiền, kết quả cho đơn không có, *Then* trang kết quả không xác nhận, thông báo nhận mã 97, 04, 01, đơn vẫn chờ, gói không đổi (`test_a_forged_or_altered_result_is_refused`). |
| **AC-69.5** — *Given* Chuẩn 50 sinh viên 6 tháng đã dùng 91 ngày, *When* báo giá Nâng cao 50 sinh viên rồi mua, rồi mua lại Nâng cao 50, *Then* nâng cấp từ hôm nay được trừ 1.500.000 đ; lần sau là gia hạn đặt trước; mua thêm khi đang có gói đặt trước nhận 422 (`test_an_upgrade_is_credited_and_a_renewal_waits`). |
| **AC-69.6** — *Given* Chuẩn 100 sinh viên 12 tháng vừa mua, *When* mua Nâng cao 10 sinh viên 6 tháng, *Then* phần chưa dùng trả đủ, đơn 0 đ được kích hoạt không qua cổng (`test_an_upgrade_the_credit_covers_needs_no_payment`). |
| **AC-69.7** — *Given* đơn chờ quá 15 phút, *When* xem tab rồi cổng báo đã thanh toán, *Then* đơn hiện hết hạn chờ, rồi được ghi nhận đã thanh toán và gói có hiệu lực (`test_pending_orders_expire_and_a_late_payment_still_counts`). |
| **AC-69.8** — *Given* một đơn đang chờ, *When* đặt đơn mới, *Then* đơn cũ chuyển sang hết hạn chờ (`test_a_new_order_retires_the_one_still_waiting`). |
| **AC-69.9** — *Given* cổng VNPay với mã website và chuỗi bí mật thử, *When* đặt đơn, VNPay báo thành công qua thông báo rồi trình duyệt quay lại, và một đơn khác bị huỷ trên trang VNPay, *Then* địa chỉ thanh toán là trang thử của VNPay với số tiền nhân 100 và địa chỉ trả về đầy đủ; thông báo nhận "Confirm Success"; trang kết quả báo thành công kèm dòng môi trường thử của VNPay — từ bản 1.7 địa chỉ thử của VNPay được coi là môi trường thử, vì không có tiền thật; đơn huỷ để nguyên gói (`test_vnpay_is_redirected_to_and_its_messages_are_checked`). |
| **AC-69.10** — *Given* quản trị viên trên trình duyệt, *When* xem bảng so sánh, chọn gói Chuẩn, đặt 60 sinh viên, thanh toán thành công ở trang cổng thử, mở biên nhận và quay lại tab, *Then* bảng có ba gói và đúng dấu tích, báo giá "60 sinh viên × 6 tháng", số tiền 3.600.000 đ trên trang cổng và biên nhận, tab ghi gói Chuẩn đang dùng và đơn đã thanh toán (`test_an_administrator_buys_a_plan_and_gets_a_receipt`). |
| **AC-69.11** — *Given* quản trị viên trên trình duyệt, *When* chọn Nâng cao rồi huỷ ở trang cổng, *Then* trang kết quả ghi đã huỷ, gói không đổi, đơn ghi đã huỷ (`test_a_cancelled_payment_leaves_the_plan_as_it_was`). |

### FR-70 — Mã giấy phép theo hợp đồng; quyền và nhật ký

**Mô tả:** Trường trả theo hợp đồng và hoá đơn thì nhận một mã giấy phép (`AICEFR1.<nội dung>.<chữ ký>`, ký HMAC-SHA256 bằng `AICEFR_LICENSE_SECRET`), dán vào tab Gói dịch vụ để kích hoạt; mã sai chữ ký, sai nội dung, đã hết hạn hay đã cài bị từ chối kèm lý do; bản triển khai chưa đặt chuỗi bí mật thì không cài được mã. Chỉ quản trị viên xem tab, báo giá, đặt đơn, cài mã, đổi tên tổ chức và xem biên nhận; giảng viên chỉ đọc gói và công cụ của gói; sinh viên không thấy gì về gói hay thanh toán. Đặt đơn, đổi tên tổ chức, cài mã và mỗi kết quả thanh toán được ghi nhật ký kiểm toán (BR-26), kết quả ghi người thực hiện là cổng.
**Ưu tiên:** S

| Acceptance Criteria |
| --- |
| **AC-70.1** — *Given* mã giấy phép Nâng cao 400 sinh viên ký đúng, *When* cài, cài lại, rồi cài một mã ký bằng khoá khác, *Then* gói Nâng cao 400 sinh viên có hiệu lực và tên tổ chức lấy từ mã; lần hai nhận 409; mã giả nhận 422 nêu chữ ký (`test_a_licence_key_is_installed_once`). |
| **AC-70.2** — *Given* bản triển khai chưa đặt `AICEFR_LICENSE_SECRET`, *When* cài một mã, *Then* nhận 422 nêu biến đó và tab không hiện ô cài mã (`test_without_a_licence_secret_keys_are_refused`). |
| **AC-70.3** — *Given* giảng viên, sinh viên và khách, *When* gọi API gói, đặt đơn, xem biên nhận, *Then* giảng viên đọc được gói nhưng nhận 403 ở tab và biên nhận, sinh viên 403, khách 401 hoặc được đưa về đăng nhập; các trang của sinh viên không có chữ "gói dịch vụ" hay "thanh toán" (`test_only_an_administrator_deals_with_plans`). |
| **AC-70.4** — *Given* quản trị viên đổi tên tổ chức và mua một gói, *When* xem nhật ký, *Then* có dòng đổi tên và đặt đơn của quản trị viên, dòng đã thanh toán của cổng thử với mã đơn và số tiền (`test_plan_actions_are_audited`). |
| **AC-70.5** — *Given* điện thoại 390 px và một sinh viên, *When* mở tab Gói dịch vụ và các trang của sinh viên, *Then* tab không cuộn ngang, sinh viên không thấy chữ "gói dịch vụ" hay "thanh toán" (`test_the_tab_fits_a_phone_and_students_see_no_plan`). |

## 3.9h. Nhiều cổng thanh toán: Stripe và MoMo — D035

Chủ dự án muốn thử luồng thanh toán với Stripe vì Stripe có môi trường thử đầy đủ, và để ngỏ thêm MoMo, VNPay "cho đa dạng". Mục này mở rộng FR-69: một bản triển khai bật được nhiều cổng cùng lúc và quản trị viên chọn cổng cho từng đơn. Mỗi cổng mặc định chạy ở môi trường thử của chính nó; không có tiền thật nào trong đồ án (BR-34). Stripe chưa có Việt Nam trong danh sách quốc gia mở được tài khoản bán hàng (stripe.com/global, truy cập 07/10/2026), nên Stripe ở đây để thử luồng; bán thật ở Việt Nam sẽ qua VNPay hay MoMo với một pháp nhân đã đăng ký. Không thư viện SDK nào được thêm: thư viện chuẩn đủ cho vài yêu cầu HTTP mỗi đơn. Quy tắc nghiệp vụ: BR-32..BR-35.

### FR-71 — Chọn cổng thanh toán cho từng đơn

**Mô tả:** `AICEFR_PAYMENT_GATEWAYS` liệt kê các cổng theo thứ tự hiện — `sandbox` (cổng thử trong ứng dụng), `vnpay`, `stripe`, `momo`. Mỗi cổng dựng từ khoá của chính nó; cổng thiếu khoá, khoá sai dạng hay tên lạ không bật, và tab Gói dịch vụ nói lý do bằng một câu nêu **tên biến** còn thiếu, không bao giờ giá trị khoá. Ô "Thanh toán qua" liệt kê các cổng đang bật với cách người trả trả tiền, nhãn "Thử" và hướng dẫn trả thử của cổng (Stripe: thẻ 4242 4242 4242 4242); cổng đầu được chọn sẵn; nút thanh toán ghi số tiền và tên cổng. Đơn ghi cổng, có tiền thật hay không, và mã phiên của cổng nếu có; bảng đơn hàng và biên nhận ghi cổng. Cổng không mở được thanh toán (khoá sai, số tiền ngoài mức cổng nhận, mất kết nối) thì đơn ghi không thành công kèm lý do và quản trị viên nhận lời nói rõ (502). Cổng thu tiền thật cần `AICEFR_PAYMENTS_LIVE`, và khi có cổng thật thì mọi cổng ở môi trường thử bị bỏ (BR-34); kết quả của cổng này không ghi nhận đơn của cổng khác, của chế độ tiền khác hay của phiên khác (BR-35).
**Ưu tiên:** S

| Acceptance Criteria |
| --- |
| **AC-71.1** — *Given* cấu hình liệt kê Stripe, MoMo, VNPay và cổng thử nhưng chỉ có khoá bí mật của Stripe, *When* quản trị viên mở tab rồi đặt đơn không nêu cổng, nêu MoMo, nêu cổng thử, *Then* tab liệt kê Stripe rồi Cổng thử, Stripe có ghi chú thẻ thử; tab nói MoMo và VNPay chưa bật và Stripe thiếu khoá webhook, không lộ khoá nào; đơn không nêu cổng đi Stripe, MoMo nhận 422, cổng thử cho địa chỉ trang thử (`test_the_administrator_picks_the_gateway_and_sees_what_is_off`). |
| **AC-71.2** — *Given* danh sách cổng trong cấu hình, *When* dựng các cổng, *Then* cổng đủ khoá bật theo đúng thứ tự; cổng thiếu khoá hay tên lạ được báo một câu nêu tên biến, tên lặp không báo hai lần; Stripe ở chế độ thử thiếu khoá webhook vẫn bật kèm cảnh báo (`test_the_registry_builds_what_the_settings_ask_for`). |
| **AC-71.3** — *Given* khoá Stripe `sk_live_`, *When* chưa rồi đã bật `AICEFR_PAYMENTS_LIVE`, *Then* lần đầu Stripe không bật và tab nêu biến cần đặt; lần sau Stripe bật ở chế độ thật và cổng thử tự tắt, trang cổng thử trả 404 (`test_real_money_needs_to_be_switched_on`). |
| **AC-71.4** — *Given* cấu hình thu tiền thật của Stripe và địa chỉ thật của MoMo, *When* chưa bật `AICEFR_PAYMENTS_LIVE`, *Then* không cổng thật nào chạy; bật rồi thì cổng thử bị bỏ khỏi danh sách; Stripe khoá thử đặt cạnh trang thật của VNPay cũng bị bỏ, kèm lời nêu lý do (`test_real_money_is_never_a_default`). |
| **AC-71.5** — *Given* một đơn đặt qua Stripe, *When* cổng thử gửi kết quả có chữ ký đúng cho đơn đó, *Then* thông báo nhận mã 01, trang trả về không xác nhận, đơn vẫn chờ, sự kiện ghi bị từ chối; kết quả đúng của Stripe cũng bị từ chối khi khoá đã đổi sang chế độ tiền khác với lúc đặt đơn, và được ghi nhận khi trở lại đúng chế độ (`test_one_gateway_cannot_settle_another_gateways_order`). |
| **AC-71.6** — *Given* quản trị viên trên trình duyệt với Stripe ở chế độ thử và cổng thử, *When* xem tab, chọn cổng thử và thanh toán thành công, *Then* thấy hai lựa chọn có nhãn thử, ghi chú thẻ 4242 và cảnh báo thiếu khoá webhook; nút ghi "qua Stripe" rồi "qua Cổng thử"; bảng đơn ghi "Cổng thử (thử)" (`test_the_administrator_sees_each_gateway_and_pays_through_the_one_picked`). |
| **AC-71.7** — *Given* điện thoại 390 px, *When* mở tab Gói dịch vụ, *Then* ô chọn cổng hiện đủ và trang không cuộn ngang (`test_the_gateway_choice_fits_a_phone`). |

### FR-72 — Stripe Checkout ở chế độ thử

**Mô tả:** Stripe bật bằng `AICEFR_STRIPE_SECRET_KEY` (khoá `sk_test_…` là môi trường thử của Stripe) và `AICEFR_STRIPE_WEBHOOK_SECRET` (`whsec_…`, của điểm nhận webhook hoặc của `stripe listen`). Đặt đơn qua Stripe, hệ thống gọi API của Stripe mở một Checkout Session: tiền tệ VND, số tiền tính bằng đồng (VND không có đơn vị lẻ), mã đơn ở `client_reference_id` và metadata, khoá chống lặp theo mã đơn, trang tiếng Việt, phiên hết hạn sau 31 phút; trình duyệt đi tới trang Stripe trả về. Trả xong, Stripe đưa trình duyệt về `/billing/return/stripe?session_id=…`. Mã phiên chỉ là lời khai, nên hệ thống đọc lại phiên từ API của Stripe bằng khoá bí mật và chỉ tin `payment_status`, số tiền và tiền tệ của chính phiên đó; hệ thống chỉ hỏi Stripe về phiên do chính nó mở (BR-35). Stripe cũng gửi sự kiện tới `/api/v1/billing/notify/stripe`; sự kiện chỉ được tin khi tiêu đề `Stripe-Signature` là HMAC-SHA256 đúng của đúng các byte nhận được theo khoá webhook, trong vòng năm phút, cùng chế độ thử hay thật với khoá. `checkout.session.completed` (đã trả), `async_payment_succeeded`, `async_payment_failed` và `expired` đổi đơn; sự kiện khác được nhận rồi bỏ qua. Người trả rời trang Stripe khi chưa trả thì về trang nói chưa trừ tiền, đơn chờ tới khi phiên hết hạn. Không hỏi được Stripe thì trang nói chưa xác nhận được, đơn được ghi nhận khi webhook tới. Sự kiện của một phiên khác — cùng tài khoản Stripe, cùng mã đơn, cùng số tiền — không ghi nhận đơn; đơn đã xong thì trang trả về hiện từ CSDL mà không hỏi Stripe nữa; thân thông báo quá 256 KiB bị từ chối trước khi đọc hết; tiêu đề hay chữ ký có ký tự lạ nhận 400 chứ không làm lỗi máy chủ; lời gọi tới Stripe không đi theo chuyển hướng. Hệ thống chỉ giữ mã phiên và mã giao dịch của Stripe — không email, tên hay thẻ của người trả (BR-32). Khoá `sk_live_` cần khoá webhook và `AICEFR_PAYMENTS_LIVE`.
**Ưu tiên:** S

| Acceptance Criteria |
| --- |
| **AC-72.1** — *Given* khoá thử của Stripe, *When* mở thanh toán cho đơn 6.000.000 đ, *Then* hệ thống gửi `POST /v1/checkout/sessions` với khoá bí mật, khoá chống lặp theo mã đơn, `currency=vnd`, `unit_amount=6000000`, mã đơn ở `client_reference_id` và metadata, địa chỉ trả về có `{CHECKOUT_SESSION_ID}`, địa chỉ rời trang có `left=1`, hạn sau 31 phút, `locale=vi`; trả địa chỉ trang Stripe và mã phiên (`test_stripe_opens_a_checkout_session_in_dong_for_the_order`). |
| **AC-72.2** — *Given* Stripe từ chối vì số tiền quá nhỏ, rồi không kết nối được, *When* quản trị viên đặt đơn qua Stripe, *Then* nhận 502 với lời bắt đầu bằng "Stripe: " nêu lý do, đơn ghi không thành công với mã của Stripe, không còn đơn nào chờ, gói không đổi (`test_a_gateway_that_will_not_open_fails_the_order_with_a_reason`). |
| **AC-72.3** — *Given* đơn Chuẩn 50 sinh viên đặt qua Stripe, *When* người trả trả xong và trình duyệt quay về, rồi webhook tới, rồi trình duyệt quay về lần nữa, *Then* trang báo thành công và môi trường thử của Stripe, phiên được đọc lại từ API, gói Chuẩn có hiệu lực với mã giao dịch của Stripe; webhook nhận `{"received": true}`; lần quay về sau báo thành công mà Stripe không bị hỏi thêm; ba sự kiện được lưu, chỉ lần trả về được áp dụng; biên nhận ghi Stripe ở môi trường thử (`test_paying_through_stripe_is_read_back_and_counted_once`). |
| **AC-72.4** — *Given* phiên đã trả, chưa trả, đã hết hạn, hoặc tính bằng tiền khác, *When* đọc lại từ Stripe, *Then* lần lượt là đã thanh toán, chưa có kết quả, huỷ, và một số tiền không khớp đơn nào; chỉ giữ mã phiên, không email hay tên; mã phiên sai dạng hay là phiên thật trên khoá thử bị từ chối mà không hỏi Stripe (`test_stripe_return_is_read_back_from_stripe`). |
| **AC-72.5** — *Given* một sự kiện webhook, *When* chữ ký đúng, đúng nhưng cũ hơn năm phút, sửa một byte, khoá khác, thiếu tiêu đề, nhiều chữ ký v1 khi đổi khoá, sự kiện thật trên khoá thử, *Then* chỉ trường hợp đúng và trường hợp nhiều chữ ký có một chữ ký đúng được tin; thời điểm có ký tự lạ hay dài bất thường và chữ ký không phải ASCII bị từ chối, không gây lỗi; các loại sự kiện ánh xạ đúng kết quả, sự kiện khác được nhận rồi bỏ (`test_stripe_events_count_only_when_signed_and_fresh`). |
| **AC-72.6** — *Given* người trả đã trả rồi đóng trang, *When* webhook sai khoá, thân rỗng không chữ ký, gọi bằng GET, rồi webhook đúng tới, *Then* ba lần đầu nhận 400, tiêu đề có ký tự lạ nhận 400, thân quá 256 KiB nhận 413, sự kiện có chữ ký của một phiên khác mang mã đơn này nhận 200 nhưng đơn vẫn chờ, và gói không đổi; webhook đúng làm gói Chuẩn có hiệu lực; sự kiện không liên quan được nhận 200 (`test_the_stripe_webhook_alone_installs_the_plan`). |
| **AC-72.7** — *Given* một đơn qua Stripe, *When* người trả rời trang Stripe khi chưa trả, rồi phiên hết hạn, *Then* trang nói đã rời trang thanh toán, đơn vẫn chờ; sự kiện hết hạn làm đơn thành huỷ và gói không đổi (`test_leaving_stripe_changes_nothing_until_the_session_expires`). |
| **AC-72.8** — *Given* người trả đã trả, *When* trình duyệt quay về lúc không hỏi được Stripe, rồi tải lại, *Then* lần đầu trang nói chưa xác nhận được với Stripe và đơn vẫn chờ; lần sau báo thành công (`test_a_return_stripe_cannot_confirm_says_so`). |
| **AC-72.9** — *Given* một đơn đang chờ, *When* trang trả về nhận mã phiên đúng dạng nhưng không phải phiên của đơn nào, hoặc sai dạng, *Then* trang không xác nhận, Stripe không được hỏi lần nào, đơn vẫn chờ (`test_stripe_is_asked_only_about_checkouts_this_system_opened`). |
| **AC-72.10** — *Given* các loại khoá, *When* dựng cổng Stripe, *Then* `sk_test_` và `rk_test_` là chế độ thử kèm ghi chú thẻ thử; `sk_live_` có khoá webhook là chế độ thật; `sk_live_` thiếu khoá webhook, khoá công khai `pk_` hay khoá webhook sai dạng bị từ chối (`test_stripe_keys_decide_the_mode`). |
| **AC-72.11** — *Given* trình duyệt, *When* mở địa chỉ rời trang của Stripe, *Then* trang ghi "Bạn đã rời trang thanh toán", dòng môi trường thử của Stripe và nút về trang Gói dịch vụ (`test_coming_back_without_paying_says_nothing_was_charged`). |

### FR-73 — Ví MoMo

**Mô tả:** MoMo bật bằng `AICEFR_MOMO_PARTNER_CODE`, `AICEFR_MOMO_ACCESS_KEY`, `AICEFR_MOMO_SECRET_KEY`; địa chỉ mặc định là môi trường thử của MoMo (`test-payment.momo.vn`), địa chỉ khác cần `AICEFR_PAYMENTS_LIVE`. Đặt đơn qua MoMo, hệ thống gửi yêu cầu tạo giao dịch `captureWallet` tới `/v2/gateway/api/create`, ký HMAC-SHA256 trên các trường MoMo quy định theo đúng thứ tự (`accessKey` … `requestType`), kèm địa chỉ trả về và địa chỉ IPN; trình duyệt đi tới `payUrl`. Số tiền ngoài 1.000 đ – 50.000.000 đ mỗi giao dịch bị từ chối trước khi hỏi MoMo. Kết quả về hai đường như VNPay: trình duyệt quay về `/billing/return/momo` với kết quả trong địa chỉ, máy chủ MoMo gửi IPN dạng JSON tới `/api/v1/billing/notify/momo`; cả hai được ký theo các trường kết quả; hệ thống kiểm chữ ký, mã đối tác, số tiền và trả lời IPN bằng 204 No Content. Theo bảng mã của MoMo: 0 là đã trả; 1003, 1005, 1006, 1017 là huỷ hoặc hết hạn; các mã thất bại cuối (98, 99, 1001, 1002, 1004, 1007, 1026, 1080, 1081, 1088, 2019, 4001, 4002, 4100) là không thành công; mọi mã khác — 1000, 7000, 7002, 9000, hay một mã MoMo thêm sau — chưa phải kết quả cuối, nên kết quả sau cho cùng đơn vẫn ghi nhận được.
**Ưu tiên:** C

| Acceptance Criteria |
| --- |
| **AC-73.1** — *Given* khoá thử của MoMo, *When* mở thanh toán, *Then* yêu cầu gửi tới địa chỉ thử với số tiền là số nguyên, `requestType=captureWallet`, địa chỉ trả về và IPN, chữ ký tính lại theo thứ tự trường của MoMo khớp, không có `accessKey` hay khoá bí mật trong thân; số tiền quá mức bị từ chối mà không hỏi MoMo; lời từ chối của MoMo thành câu tiếng Việt kèm mã (`test_momo_signs_the_create_request_as_documented`). |
| **AC-73.2** — *Given* kết quả MoMo gửi lại, *When* mã 0, 1006, 1000, 1001, 4001, một mã lạ, đổi số tiền, mã đối tác khác, thiếu trường, khoá khác, chữ ký có ký tự lạ, thân không phải JSON hay lồng quá sâu, *Then* lần lượt là đã thanh toán, huỷ, chưa xong, không thành công, không thành công, chưa xong, và bảy trường hợp sau bị từ chối; trả về bằng chữ và IPN bằng số đều được; trả lời IPN là 204, 400 khi sai chữ ký, 500 khi lỗi (`test_momo_results_map_to_outcomes_and_forgeries_are_refused`). |
| **AC-73.3** — *Given* đơn Chuẩn 50 sinh viên qua MoMo, *When* IPN có chữ ký tới, trình duyệt quay về, IPN lặp lại, rồi một IPN sửa số tiền, *Then* IPN nhận 204 không thân và gói Chuẩn có hiệu lực; trang trả về báo thành công và môi trường thử của MoMo; IPN lặp nhận 204 không đổi gì và được đếm trên dòng của IPN đầu; IPN sửa nhận 400 (`test_momo_is_paid_through_its_ipn_answered_204`). |

## 3.9i. Đăng nhập Google: luồng không giả được và cài khoá dễ — D036

Chủ dự án hỏi đăng nhập Google có dùng OAuth PKCE không và nhờ thiết kế sẵn để đưa khoá sau. Luồng mã uỷ quyền có PKCE S256, `state` và `nonce` đã có từ D029 (FR-59) và đúng với khuyến nghị dùng PKCE cả cho client bí mật của RFC 9700 (01/2025, mục 2.1.1); Google công bố hỗ trợ S256 trong tài liệu discovery (`code_challenge_methods_supported`, truy cập 07/10/2026). Rà lại để viết mục này thấy một chỗ hở: cookie mang luồng chưa có chữ ký, nên ai đặt được cookie cho tên miền — một tên miền con, một mạng HTTP — có thể ghép phiên của nạn nhân với một luồng do mình bắt đầu. Mục này đóng chỗ đó và làm phần cài khoá: quản trị viên thấy ngay phải đăng ký gì với Google và còn thiếu gì. Quy tắc nghiệp vụ: BR-15, BR-16, BR-36.

### FR-74 — Cookie của luồng có chữ ký, cookie `__Host-` sau TLS, khung cấu hình

**Mô tả:** Cookie mang `state`, `nonce` và verifier PKCE của luồng có chữ ký HMAC-SHA256 theo một khoá riêng của bản triển khai, tạo ngẫu nhiên lần đầu cần tới và giữ trong CSDL (bảng `server_secret`), nên mọi tiến trình và mọi lần khởi động dùng chung; cookie thiếu chữ ký, sai chữ ký hay bị sửa bị bỏ **trước** khi hỏi Google (BR-36). Sau TLS (`AICEFR_HTTPS_ONLY`), cookie là `__Host-aicefr_oauth` (Secure, `Path=/`, không `Domain`) nên tên miền con không đặt được; trên localhost là `aicefr_oauth` ở đường dẫn `/auth/google`. Chữ ký không chặn được kẻ cài vào trình duyệt người khác một luồng thật do chính hắn bắt đầu, để người đó đăng nhập vào tài khoản của hắn — thứ chặn việc đó là tiền tố `__Host-` — nên địa chỉ chuyển hướng là `https` mà chưa bật `AICEFR_HTTPS_ONLY` thì luồng không bắt đầu (mã `insecure`). Thử thách PKCE là S256 đúng RFC 7636. Tab Cấu hình của trang Quản trị có khung "Đăng nhập bằng Google": đang bật hay chưa, địa chỉ chuyển hướng cần đăng ký với Google (có nút sao chép), Client ID, client secret đã đặt hay chưa (không bao giờ hiện giá trị), phạm vi xin, tên miền giới hạn, số tài khoản đã liên kết, và những gì còn thiếu: biến chưa đặt, Client ID sai dạng, địa chỉ `http://` trên máy không phải localhost, địa chỉ IP trần, `https` mà chưa bật `AICEFR_HTTPS_ONLY`. Chỉ quản trị viên xem được. Cách tạo OAuth client và đặt khoá ở `docs/plan/CAU_HINH_KHOA_BEN_NGOAI.md`.
**Ưu tiên:** C

| Acceptance Criteria |
| --- |
| **AC-74.1** — *Given* sinh viên đang đăng nhập, *When* người khác đặt vào trình duyệt của họ một cookie luồng "liên kết" cho tài khoản của họ, ký bằng khoá tự đặt hoặc không ký, rồi đưa họ tới địa chỉ quay về với một mã uỷ quyền, *Then* luồng bị từ chối với mã `state`, Google không được hỏi đổi mã lần nào, tài khoản vẫn chưa liên kết (`test_a_flow_cookie_this_server_did_not_sign_is_ignored`). |
| **AC-74.2** — *Given* một luồng, *When* đọc cookie của nó với đúng khoá, khoá khác, không chữ ký, sửa một ký tự ở nội dung hay ở chữ ký, nội dung viết lại cho tài khoản khác, ký tự không phải ASCII, *Then* chỉ trường hợp đầu đọc ra đúng luồng (`test_the_flow_cookie_is_signed_and_any_change_breaks_it`). |
| **AC-74.3** — *Given* `AICEFR_HTTPS_ONLY` bật, *When* bắt đầu rồi hoàn tất đăng nhập Google qua `https`, *Then* cookie là `__Host-aicefr_oauth` có `Secure`, `Path=/`, `HttpOnly`, không `Domain`; đăng nhập thành công và cookie luồng bị xoá (`test_behind_tls_the_flow_cookie_is_a_host_cookie`). |
| **AC-74.4** — *Given* một CSDL, *When* hai kho đọc khoá ký, đọc một khoá tên khác, và một luồng bắt đầu trước khi khởi động lại rồi hoàn tất sau đó, *Then* khoá dài 32 byte và như nhau, khoá tên khác thì khác, luồng hoàn tất được (`test_the_signing_key_is_made_once_and_kept`). |
| **AC-74.5** — *Given* ví dụ ở Phụ lục B của RFC 7636, *When* tính thử thách PKCE, *Then* ra đúng giá trị của RFC; verifier mới dài 43–128 ký tự trong bảng chữ không dành riêng và không lặp; địa chỉ tới Google có S256 và không chứa verifier (`test_the_pkce_challenge_is_s256_as_rfc_7636_shows`). |
| **AC-74.6** — *Given* khoá Google đã đặt, *When* quản trị viên mở trạng thái trên `http://testserver`, rồi với `AICEFR_PUBLIC_URL=https://…` và TLS, rồi với địa chỉ IP, rồi khi chưa đặt khoá, *Then* lần lượt thấy địa chỉ chuyển hướng kèm lời nhắc về `http://`; với `https` chưa bật TLS thì lời nhắc về `AICEFR_HTTPS_ONLY` và nút Google từ chối với mã `insecure`, bật rồi thì không còn lỗi, cookie `__Host-` và nút đi tới Google; lời nhắc về địa chỉ IP; `http://[::1]` không lỗi; hai biến còn thiếu. Client secret không bao giờ có trong câu trả lời; giảng viên nhận 403, khách 401 (`test_the_administrator_sees_what_to_register_with_google`). |
| **AC-74.7** — *Given* khoá Google đã đặt, *When* quản trị viên mở tab Cấu hình trên trình duyệt, *Then* khung "Đăng nhập bằng Google" ghi đang bật, địa chỉ chuyển hướng của máy, Client ID, "Đã đặt (không bao giờ hiển thị)", PKCE (S256), có nút Sao chép, và client secret không có trên trang (`test_the_config_tab_shows_what_to_register_with_google`). |
| **AC-74.8** — *Given* trang đăng nhập có nút Google, *When* bấm nút, *Then* trình duyệt sẽ tới Google với `response_type=code`, `scope=openid email`, `code_challenge_method=S256` và thử thách 43 ký tự, `state` khác `nonce`, `prompt=select_account`, địa chỉ chuyển hướng của máy; cookie luồng là HttpOnly, `SameSite=Lax`, đường dẫn `/auth/google`, có chữ ký (`test_the_google_button_leaves_with_a_pkce_challenge`). |

## 3.9j. Bằng chứng học tập: phát âm, thực nghiệm phản hồi, thời gian giảng viên, tiến bộ đáng tin — D039..D042

Bốn yêu cầu này trả lời bốn câu hỏi mà một hệ thống chấm tự động thường chỉ khẳng định mà không đo: người Việt hay sai phát âm ở đâu (D039), nhận xét có giúp người học hơn chỉ xem điểm không (D040), giảng viên tiết kiệm được bao nhiêu thời gian (D041), và khi nào một chênh lệch điểm đáng gọi là tiến bộ (D042). Chủ dự án báo ngày 11/10/2026 rằng GVHD đã duyệt cả bốn. Quy tắc nghiệp vụ: BR-02, BR-03, BR-37, BR-38, BR-39.

### FR-75 — Chẩn đoán phát âm theo lỗi đặc trưng của người Việt

**Mô tả:** Với mỗi từ của bài đọc to, nhắc lại, điền từ mà máy nghe khác chữ viết, hệ thống gắn tên lỗi khi chênh lệch khớp một trong năm luật (`vi-pron-v1`): đuôi -ed, đuôi -s/-es, âm cuối bị nuốt, âm th bị thay bằng t, d, s, z, f, cụm phụ âm đầu bị rút; thử theo thứ tự đuôi -ed, đuôi -s, âm th, cụm phụ âm đầu, rồi mới đến âm cuối — hai lỗi riêng của đuôi từ trước, lỗi chung "nuốt âm cuối" sau cùng, để "with" nghe thành "wit" là lỗi âm th. Những từ có chữ cuối giống đuôi mà không phải đuôi (need, hundred, was, always...) không tính là lần gặp; chữ cuối w, r, gh và h sau nguyên âm không tính là âm cuối. Trang Tiến độ của sinh viên có mục "Phát âm cần chú ý": mỗi lỗi kèm số lần mắc trên số lần gặp (từ cho cơ hội thể hiện lỗi đó), tỉ lệ chỉ nêu khi đủ 8 lần gặp, tối đa 5 ví dụ dẫn về đúng bài, và cách luyện. Chỉ tính bước đo được; từ giảng viên đã sửa thành "nghe được" không là lỗi (BR-39). `GET /api/v1/me/pronunciation`, 400 lượt gần nhất.
**Ưu tiên:** S

| Acceptance Criteria |
| --- |
| **AC-75.1** — *Given* các cặp chữ viết và chữ máy nghe như worked/work, cats/cat, think/tink, street/sreet, night/nigh, because/becau, *When* phân loại, *Then* mỗi cặp ra đúng một lỗi trong năm (`test_classify_names_the_pattern_behind_a_spelling_gap`). |
| **AC-75.2** — *Given* từ nghe đúng, một từ khác hẳn (like/lie), một từ không nghe được gì, *When* phân loại, *Then* không gắn lỗi nào (`test_classify_stays_silent_when_no_pattern_explains_the_gap`). |
| **AC-75.3** — *Given* một lỗi mới gặp 1 lần, rồi gặp 8 lần, *When* lập hồ sơ, *Then* lần đầu không có tỉ lệ, lần sau có tỉ lệ, ví dụ dừng ở 5 và lỗi đủ dữ liệu đứng trước (`test_profile_reports_a_rate_only_from_enough_opportunities`). |
| **AC-75.4** — *Given* một từ giảng viên đã sửa thành "nghe được" và một bước không đo được, *When* lập hồ sơ, *Then* không lỗi nào được đếm và bước không đo được không vào số bước (`test_profile_respects_teacher_corrections_and_skips_unmeasured_steps`). |
| **AC-75.5** — *Given* máy nghe "becau" khi câu mẫu có "because", *When* sinh viên ghi bước nhắc lại, *Then* nhãn của từ đó có `said` = "becau" và `pattern` = `final_consonant`; từ khác hẳn không có lỗi (`test_lesson_word_marks_name_the_vietnamese_pattern`). |
| **AC-75.6** — *Given* sinh viên ghi bước nhắc lại hai lần với cùng lỗi, *When* mở hồ sơ phát âm, *Then* âm cuối có 2 lỗi, đủ 8 lần gặp, tỉ lệ giữa 0 và 1, ví dụ dẫn về bài học và đứng đầu danh sách (`test_learner_profile_counts_errors_against_opportunities`). |
| **AC-75.7** — *Given* ba lượt có lỗi âm cuối và đuôi -ed, *When* sinh viên mở trang Tiến độ, *Then* mục phát âm ghi "3/12 lần · 25%" cho âm cuối kèm ví dụ «night» → «nigh» và cách luyện, còn đuôi -ed ghi chưa đủ dữ liệu 3/8 (`test_progress_page_names_the_pronunciation_patterns`). |

### FR-76 — Phát âm của cả lớp, không chỉ ra ai

**Mô tả:** Giảng viên và quản trị viên xem bản gộp FR-75 trên mọi sinh viên ở trang Thống kê lớp, kèm số người học có dữ liệu, để chọn nội dung luyện chung. Ví dụ chỉ còn từ và chữ máy nghe; không có bút danh, mã tài khoản hay đường dẫn tới bài của ai (BR-39). `GET /api/v1/teach/pronunciation`, 4000 lượt gần nhất.
**Ưu tiên:** C

| Acceptance Criteria |
| --- |
| **AC-76.1** — *Given* hai sinh viên cùng mắc lỗi âm cuối, *When* giảng viên mở bản của lớp, *Then* thấy 2 người học, 2 lỗi, ví dụ chỉ có `word` và `said`, không có bút danh hay mã tài khoản; sinh viên nhận 403 (`test_class_profile_is_for_staff_and_names_nobody`). |
| **AC-76.2** — *Given* giảng viên, *When* mở trang Thống kê lớp, *Then* thẻ "Phát âm của cả lớp" và thẻ "Hiệu quả cho giảng viên" tải được (`test_class_page_shows_teacher_time_and_class_pronunciation`). |

### FR-77 — Thực nghiệm phản hồi: chia nhóm và giữ phản hồi lại

**Mô tả:** Quản trị viên mở một thực nghiệm (`/admin/study`); mỗi lúc chỉ một thực nghiệm chưa đóng. Mọi sinh viên còn hoạt động và đang cho phép dùng dữ liệu nghiên cứu được chia ngẫu nhiên, cân bằng, vào nhóm "Phản hồi đầy đủ" và nhóm "Chỉ điểm" theo một hạt giống lưu lại; cần ít nhất 4 người. Khi thực nghiệm đang chạy, báo cáo bài đánh giá của người học nhóm "Chỉ điểm" chỉ còn điểm, mức và khoảng, có cờ `feedback_withheld`, trang báo cáo nói vì sao và chỉ cách rời. Phản hồi giữ lại suốt giai đoạn đang chạy và giai đoạn khảo sát, ở mọi đường trả nó ra: báo cáo, bản xuất cá nhân, hồ sơ năng lực, tiêu chí yếu nhất làm căn cứ gợi ý luyện tập và gợi ý bài học. Rời thực nghiệm, rút đồng ý nghiên cứu, bị xoá dữ liệu (FR-35) hay thực nghiệm đóng đều trả lại phản hồi đầy đủ (BR-37). Mở thực nghiệm và chuyển giai đoạn có nhật ký.
**Ưu tiên:** C

| Acceptance Criteria |
| --- |
| **AC-77.1** — *Given* 11 tài khoản, *When* chia nhóm hai lần với cùng hạt giống theo hai thứ tự khác nhau, *Then* kết quả như nhau, hai nhóm lệch nhau tối đa 1 người, hạt giống khác cho kết quả khác (`test_assignment_is_balanced_and_reproducible_from_the_seed`). |
| **AC-77.2** — *Given* 5 sinh viên đồng ý, 1 sinh viên không đồng ý, 1 giảng viên, *When* quản trị viên mở thực nghiệm, *Then* đúng 5 sinh viên được chia 2–3, mở thực nghiệm thứ hai bị 409, nhật ký ghi hạt giống (`test_study_enrols_active_students_half_in_each_arm`). |
| **AC-77.3** — *Given* chỉ 1 sinh viên đồng ý, *When* mở thực nghiệm, *Then* 422 và lý do nói cần ít nhất bao nhiêu người (`test_study_needs_enough_students`). |
| **AC-77.4** — *Given* hai bài có đủ nhận xét, bằng chứng, ưu tiên của hai sinh viên ở hai nhóm, *When* mỗi người mở báo cáo của mình và giảng viên mở bài của nhóm "Chỉ điểm", *Then* người nhóm "Chỉ điểm" thấy điểm 3,4 và B1, `feedback_withheld`, mọi danh sách phản hồi rỗng; người nhóm kia và giảng viên thấy đủ (`test_score_only_arm_gets_the_score_and_nothing_more`). |
| **AC-77.5** — *Given* người nhóm "Chỉ điểm", *When* họ rời thực nghiệm, rồi quản trị viên đóng thực nghiệm, *Then* báo cáo hiện đủ ngay, trạng thái ghi đã rời, và sau khi đóng không ai còn trong thực nghiệm (`test_leaving_the_study_or_closing_it_brings_feedback_back`). |
| **AC-77.7** — *Given* một người trong thực nghiệm, *When* quản trị viên xoá dữ liệu của họ, *Then* họ không còn trong danh sách tham gia (`test_erasure_takes_the_learner_out_of_every_study`). |
| **AC-77.8** — *Given* 4 sinh viên đồng ý, *When* quản trị viên bắt đầu trên trang, người nhóm "Chỉ điểm" mở báo cáo, rồi bấm "Rời thực nghiệm" ở trang Tiến độ, *Then* trang báo cáo nói về nhóm "Chỉ điểm" và không có nhận xét; sau khi rời, nhận xét hiện lại (`test_a_score_only_learner_sees_why_and_can_leave`). |
| **AC-77.9** — *Given* người nhóm "Chỉ điểm" có một bài đủ nhận xét, *When* quản trị viên chuyển thực nghiệm sang giai đoạn khảo sát, người đó mở báo cáo và tải bản xuất cá nhân, rồi quản trị viên đóng thực nghiệm, *Then* trong giai đoạn khảo sát báo cáo và bản xuất vẫn chỉ có điểm, không nhận xét, không ưu tiên; sau khi đóng, nhận xét hiện lại (`test_feedback_stays_held_back_through_the_survey_and_in_the_export`). |

### FR-78 — Khảo sát, phân tích và xuất dữ liệu của thực nghiệm

**Mô tả:** Thực nghiệm đi một chiều: đang chạy → khảo sát → đã đóng. Ở giai đoạn khảo sát, người tham gia trả lời 5 câu Likert 1–5 ở trang Tiến độ. Kết quả chỉ tính bài làm trong giai đoạn đang chạy (trước khi chuyển sang khảo sát). Kết quả cho mỗi nhóm: số tham gia, số người có bài đầu và bài cuối cách nhau ít nhất `min_days` ngày, mức tăng điểm trung bình và độ lệch chuẩn, số lần luyện, điểm khảo sát; và chênh lệch mức tăng "Phản hồi đầy đủ − Chỉ điểm" kèm khoảng tin cậy bootstrap 95 % (2000 lần, lấy lại trong từng nhóm, hạt giống của thực nghiệm) và Hedges g. Người đã rời hoặc không còn đồng ý không vào số nào. CSV một dòng mỗi người theo mã P001…, không bút danh, không mã tài khoản. Quy trình: `docs/research/PROTOCOL_D040.md`.
**Ưu tiên:** C

| Acceptance Criteria |
| --- |
| **AC-78.1** — *Given* điểm trước khi vào thực nghiệm và sau đó, *When* lấy cặp đầu–cuối với `min_days` = 14, *Then* bỏ điểm trước khi vào, lấy bài cuối cách bài đầu đủ 14 ngày; không có bài như vậy thì không có cặp (`test_pre_post_needs_a_later_score_far_enough_from_the_first`). |
| **AC-78.2** — *Given* hai nhóm khác biệt rõ, *When* tính, *Then* Hedges g > 2, khoảng bootstrap nằm trọn trên 0 và lặp lại đúng với cùng hạt giống; nhóm 1 người thì không có g (`test_effect_size_and_interval_point_the_same_way`). |
| **AC-78.3** — *Given* một người đã rời, *When* phân tích, *Then* họ không vào số tham gia hay mức tăng; mỗi nhóm một người thì có chênh lệch nhưng không có khoảng và g (`test_analysis_leaves_out_withdrawn_participants`). |
| **AC-78.4** — *Given* thực nghiệm đang chạy, *When* gửi khảo sát, chuyển sang khảo sát hai lần, gửi câu trả lời 6 điểm hay thiếu câu, rồi gửi đúng, *Then* lần lượt 409, 409 cho lần chuyển thứ hai, 422, 422, rồi lưu, và kết quả có 1 người trả lời với điểm đúng (`test_survey_opens_only_in_the_survey_phase_and_checks_answers`). |
| **AC-78.5** — *Given* 4 người tham gia, *When* tải CSV, *Then* có cột `participant,arm,withdrawn`, mã P001, không bút danh hay mã tài khoản nào; sinh viên nhận 403 ở danh sách thực nghiệm (`test_study_export_carries_codes_not_people`). |

### FR-79 — Thời gian giảng viên tiết kiệm được và phần máy tự xử lý

**Mô tả:** Khoá một bài để duyệt mở một phiên (`review_session`), quyết định hay đóng bài thì kết thúc phiên. Thẻ "Hiệu quả cho giảng viên" ở Thống kê lớp so trung vị phút duyệt một bài có máy với trung vị phút chấm mù một bài không có máy (phiếu D030), thời gian tiết kiệm = 1 − tỉ số hai trung vị; phiên quá 30 phút không tính và được đếm riêng; không nêu trung vị dưới 5 mẫu. Kèm tỉ lệ bài máy tự xong (hoàn tất, không cần giảng viên xác nhận, trên số bài đánh giá có điểm) và tỉ lệ giảng viên giữ nguyên mức của máy, cả hai có khoảng Wilson 95 %. `GET /api/v1/review/kpi` cho giảng viên và quản trị viên, theo gói như thống kê lớp.
**Ưu tiên:** C

| Acceptance Criteria |
| --- |
| **AC-79.1** — *Given* một bài cần duyệt, *When* giảng viên khoá rồi quyết định, *Then* có đúng một phiên đã kết thúc, hành động `decision`, đúng bài và đúng người duyệt (`test_review_lock_and_decision_leave_a_timed_session`). |
| **AC-79.2** — *Given* một phiên 4 phút, một phiên 60 phút, một phiên chưa xong, *When* tính phút, *Then* giữ 4 phút, 1 phiên bị bỏ vì quá 30 phút (`test_idle_review_sessions_are_left_out_and_counted`). |
| **AC-79.3** — *Given* 8 trên 10, *When* tính khoảng Wilson, *Then* ra [0,490; 0,943]; với 0 trên 0 thì không có khoảng (`test_wilson_interval_matches_the_textbook_value`). |
| **AC-79.4** — *Given* 4 phiên duyệt, rồi 5 phiên 2 phút và 5 phiếu 8 phút, *When* tính, *Then* lần đầu không có trung vị và không có thời gian tiết kiệm; lần sau tiết kiệm 75 % (`test_kpi_reports_time_saved_only_from_enough_samples`). |
| **AC-79.5** — *Given* chưa có phiên nào, rồi 5 phiên 2–6 phút và một phiên 45 phút, *When* giảng viên mở số đo, *Then* lần đầu n = 0 và không có trung vị; lần sau n = 5, trung vị 4 phút, 1 phiên bỏ dở; sinh viên nhận 403 (`test_teacher_kpi_reports_minutes_only_from_enough_sessions`). |

### FR-80 — Tiến bộ đáng tin theo sai số đo

**Mô tả:** Trang Tiến độ so trung bình tối đa 3 bài đầu với cùng số bài cuối; khác biệt chỉ là "tiến bộ" hay "giảm" khi |RCI| > 1,96 với RCI = chênh lệch / (SEM · √(2/k)); còn lại là "chưa vượt sai số đo"; dưới 2 bài là chưa đủ dữ liệu; chưa có SEM thì nói chưa đo được sai số (BR-38). Quản trị viên đặt SEM ở tab Cấu hình: từ cặp bài thử lại (hai bài cùng người, cùng đề, cách nhau tối đa 48 giờ, mỗi bài một cặp, SEM = SD hiệu / √2, ít nhất 10 cặp) hoặc nhập tay kèm nguồn; có nhật ký. `GET/POST /api/v1/admin/measurement-error`.
**Ưu tiên:** S

| Acceptance Criteria |
| --- |
| **AC-80.1** — *Given* ba bài trong một ngày và hai bài cách nhau bốn ngày, *When* lấy cặp thử lại, *Then* ba bài cho đúng một cặp, hai bài xa nhau không cho cặp nào (`test_retest_pairs_use_each_response_once_and_respect_the_window`). |
| **AC-80.2** — *Given* 10 cặp chênh ±0,2, *When* tính SEM, *Then* bằng SD hiệu / √2; 9 cặp thì không có SEM (`test_sem_is_sd_of_differences_over_root_two_and_needs_enough_pairs`). |
| **AC-80.3** — *Given* một bài, chưa có SEM, tăng 1 điểm với SEM 0,2, giảm 1 điểm, tăng 0,1 với SEM 0,3, *When* đánh giá, *Then* lần lượt chưa đủ dữ liệu, chưa có sai số, tiến bộ, giảm, chưa vượt sai số với ngưỡng 1,96 · SEM · √(2/k) (`test_reliable_change_verdicts`). |
| **AC-80.4** — *Given* sinh viên có 6 bài tăng 1,2 điểm, *When* xem tiến độ trước và sau khi quản trị viên nhập SEM 0,25 kèm nguồn, *Then* trước là chưa có sai số; nhập thiếu nguồn bị 422; sau là tiến bộ, nguồn `manual`, chênh lệch 1,2 vượt ngưỡng; sinh viên đặt SEM bị 403 (`test_progress_says_no_error_measured_until_an_admin_sets_one`). |
| **AC-80.5** — *Given* chưa có cặp nào rồi có 10 cặp, *When* quản trị viên chọn dùng bài thử lại, *Then* lần đầu 422 nói số cặp; lần sau SEM nguồn `retest` từ 10 cặp (`test_measured_error_needs_enough_retest_pairs`). |
| **AC-80.6** — *Given* quản trị viên ở tab Cấu hình, *When* chưa có cặp thử lại và nhập tay 0,25 kèm nguồn, *Then* khung ghi "Chưa đặt", nút dùng bài thử lại bị tắt, sau khi lưu ghi nguồn đã nhập (`test_admin_sets_the_measurement_error_with_its_source`). |

## 3.9k. Lộ trình ghép từ bài có sẵn, lược đồ có phiên bản, triển khai máy chủ — D045..D047

> Ba yêu cầu của chủ dự án ngày 14/10/2026: "chốt database", "làm thêm một model AI tạo lộ trình từ những lộ trình đã có, theo hướng giáo viên hoặc sinh viên muốn", "deploy web". Phương án của từng việc là **đề xuất** (D045, D046, D047 trong nhật ký quyết định đều PROPOSED), chờ chủ dự án xác nhận.

### FR-81 — Lộ trình riêng của người học

**Mô tả:** Ở trang Luyện tập, sinh viên nhập điều muốn luyện bằng tiếng Việt hoặc tiếng Anh, chọn chủ đề, tiêu chí, âm cần luyện và số bài (3–15). Hệ thống ghép một lộ trình từ các bài **đã xuất bản thuộc lộ trình đã xuất bản**. Lộ trình bắt đầu từ band của bài đánh giá gần nhất và đi lên. Hệ thống ưu tiên tiêu chí yếu nhất của bài đánh giá đó (đã qua cổng của thực nghiệm phản hồi, BR-37), các âm sinh viên hay nói sai (FR-75), bài chưa học và bài đang làm dở. Mỗi bài kèm lý do được chọn. Lộ trình được giữ đến khi sinh viên ghép lại hoặc bỏ; nó có trong bản xuất dữ liệu cá nhân và bị xoá cùng dữ liệu của sinh viên. Hệ thống không viết câu chữ nào (BR-40). `POST/GET/DELETE /api/v1/learn/plan`.
**Ưu tiên:** S

| Acceptance Criteria |
| --- |
| **AC-81.1** — *Given* câu "Muốn luyện kể chuyện du lịch, tập trung trôi chảy và âm cuối, từ A2 lên B1", *When* đọc mục tiêu, *Then* ra chủ đề Du lịch, tiêu chí Độ trôi chảy, âm cuối, band A2 và B1 (`test_a_wish_in_vietnamese_names_topics_criteria_sounds_and_bands`). |
| **AC-81.2** — *Given* năm bài, hai bài đã hoàn thành, một bài đang làm, *When* ghép 3 bài rồi 4 bài, *Then* lần đầu chỉ có ba bài chưa xong; lần sau mới thêm một bài đã xong để ôn (`test_a_learner_gets_new_lessons_first_and_finished_ones_only_to_fill_up`). |
| **AC-81.3** — *Given* tiêu chí yếu nhất là Độ trôi chảy, *When* ghép, *Then* bài luyện trôi chảy ghi lý do là tiêu chí yếu nhất trong bài đánh giá gần nhất (`test_the_learners_weakest_criterion_is_named_as_the_reason`). |
| **AC-81.4** — *Given* lộ trình mẫu, *When* sinh viên ghép 5 bài cho "du lịch, tập trung trôi chảy", *Then* có 5 bài trạng thái "chưa học", mỗi bài có lý do, có bài ghi chủ đề Du lịch, bài nào cũng mở được (`test_a_learner_gets_a_path_of_published_lessons_with_reasons`). |
| **AC-81.5** — *Given* sinh viên đã có lộ trình riêng, *When* ghép lại với "B2" rồi bỏ lộ trình, *Then* lộ trình mới thay lộ trình cũ và chỉ gồm bài B2; sau khi bỏ thì không còn lộ trình đang dùng (`test_asking_again_replaces_the_plan_and_closing_it_sets_it_aside`). |
| **AC-81.6** — *Given* một bài đã xuất bản nằm trong lộ trình còn nháp, *When* sinh viên ghép 30 bài và giảng viên ghép, *Then* lộ trình của sinh viên không có bài đó, đề xuất của giảng viên có (`test_a_draft_path_never_reaches_a_learners_plan`). |
| **AC-81.7** — *Given* sinh viên có lộ trình riêng, *When* tải bản xuất dữ liệu rồi bị xoá dữ liệu, *Then* bản xuất có `learning_plans` kèm mục đích; sau khi xoá không còn lộ trình nào của sinh viên (`test_plans_are_in_the_export_and_go_with_erasure`). |
| **AC-81.8** — *Given* sinh viên ở trang Luyện tập, *When* nhập mục tiêu, chọn âm cuối, bấm "Ghép lộ trình", tải lại trang rồi bấm "Bỏ lộ trình này", *Then* thấy 6 bài có lý do và đường dẫn tới bài; tải lại vẫn còn; bỏ thì trở về lời mời ghép (`test_a_learner_composes_a_path_and_sets_it_aside`). |
| **AC-81.9** — *Given* bài đánh giá gần nhất ra B1, yếu nhất Độ trôi chảy, *When* sinh viên ghép 4 bài không nhập band, *Then* các bài ở B1 hoặc B2 và có lý do là tiêu chí yếu nhất (`test_the_latest_assessment_steers_the_learners_path`). |

### FR-82 — Giảng viên ghép lộ trình từ bài có sẵn

**Mô tả:** Ở trang Soạn bài, giảng viên mô tả lộ trình muốn có: mục tiêu, band từ–đến, chủ đề, tiêu chí, âm cần luyện, số bài (3–30). Model chọn trong các bài đã xuất bản của mọi lộ trình chưa lưu trữ. Model chấm mức phù hợp theo sáu tín hiệu: band, tiêu chí, chủ đề, từ khớp, âm cần luyện và, với sinh viên, tiến độ. Model trải đều các bài giống nhau và tính một lần bài trùng giữa hai lộ trình. Thứ tự **học từ các lộ trình hiện có**: hồi quy logistic theo cặp trên các bài liền nhau. Khi chưa đủ 12 cặp, hoặc thứ tự học được không xếp đúng các lộ trình hiện có hơn quy tắc cố định (band rồi độ khó), model dùng quy tắc cố định và nói rõ. Giảng viên xem đề xuất kèm lý do, bỏ bớt bài, đặt tên và lưu thành lộ trình **nháp** gồm bản sao các bài; sinh viên chỉ thấy khi giảng viên xuất bản. Có nhật ký `lesson.path.compose`. `POST /api/v1/teach/paths/compose`, `POST /api/v1/teach/paths/compose/{plan_id}/save`.
**Ưu tiên:** S

| Acceptance Criteria |
| --- |
| **AC-82.1** — *Given* ba bài A2 và ba bài B1, *When* ghép 3 bài B1 rồi 5 bài B1, *Then* lần đầu chỉ có ba bài B1; lần sau thêm bài band liền kề kèm cảnh báo; bài cách hai band không bao giờ được chọn (`test_the_band_asked_for_comes_first_and_others_only_fill_in`). |
| **AC-82.2** — *Given* ba bài khác chủ đề và tiêu chí, *When* ghép với chủ đề Du lịch và tiêu chí Độ trôi chảy, *Then* bài du lịch luyện trôi chảy có điểm cao nhất, lý do nêu cả chủ đề lẫn tiêu chí (`test_topic_and_criterion_rank_the_matching_lessons_first_with_their_reasons`). |
| **AC-82.3** — *Given* bốn lộ trình đều đặt bài văn bản dài trước, *When* học thứ tự, *Then* model học được từ 20 cặp, xếp đúng 100 % cặp, trọng số độ dài văn bản âm (`test_the_order_teachers_use_is_learned_from_their_paths`). |
| **AC-82.4** — *Given* chưa đủ 12 cặp, *When* ghép, *Then* dùng quy tắc cố định và lộ trình có cảnh báo "chưa đủ" (`test_with_few_pairs_the_fixed_order_is_used_and_said`). |
| **AC-82.5** — *Given* đề xuất 6 bài A2–B1, *When* giảng viên giữ 4 bài và lưu, *Then* có lộ trình nháp gồm 4 bản sao mang mã mới theo đúng thứ tự; lưu lần hai bị 409; nhật ký ghi `lesson.path.compose` (`test_a_teacher_saves_the_kept_lessons_as_a_draft_path_of_copies`). |
| **AC-82.6** — *Given* một sinh viên và hai giảng viên, *When* sinh viên gọi ghép, giảng viên khác lưu đề xuất, giảng viên giữ một bài không có trong đề xuất, *Then* lần lượt 403, 403, 422; giảng viên gọi lộ trình riêng của sinh viên bị 403 (`test_only_staff_compose_and_only_the_author_saves`). |
| **AC-82.7** — *Given* giảng viên ở trang Soạn bài, *When* ghép 5 bài A2–B1 cho "ẩm thực và du lịch", bỏ bài cuối và lưu, *Then* đề xuất có 5 bài, có lý do chủ đề Ẩm thực; thông báo lưu 4 bài và lộ trình mới hiện trong danh sách (`test_a_teacher_keeps_part_of_a_proposal_as_a_draft_path`). |
| **AC-82.8** — *Given* chỉ có một bài và chủ đề Sức khoẻ không có bài nào, *When* ghép 5 bài, *Then* lộ trình có một bài và cảnh báo nói số bài tìm được và chủ đề còn thiếu (`test_too_few_lessons_is_said_not_hidden`). |

### FR-83 — Lược đồ cơ sở dữ liệu có phiên bản

**Mô tả:** Kho của dịch vụ `core` có lược đồ đánh phiên bản. Phiên bản 1 là lược đồ của D044; mọi thay đổi sau đó là một migration đánh số, ghi vào bảng `schema_migrations`. Dịch vụ `core` tự nâng kho lên phiên bản mới nhất khi khởi động, nhiều tiến trình cùng khởi động cũng chỉ áp dụng mỗi phiên bản một lần. Lược đồ chuẩn được commit ở `docs/db/schema_core.sql`; mọi bảng có trong từ điển dữ liệu `docs/db/TU_DIEN_DU_LIEU.md`. Lệnh `python -m aicefr.db_cli status|migrate|snapshot`.
**Ưu tiên:** M

| Acceptance Criteria |
| --- |
| **AC-83.1** — *Given* một kho mới, *When* tạo lược đồ, *Then* đúng từng collection và chỉ mục với `docs/db/schema_core.json` (`test_a_fresh_store_matches_the_committed_snapshot`). |
| **AC-83.2** — *Given* một kho dựng bởi bản D044, chưa có sổ phiên bản, *When* nâng cấp, *Then* áp dụng phiên bản 1 và 2 và cấu trúc giống hệt kho mới (`test_a_store_built_by_d044_reaches_the_same_structure`). |
| **AC-83.3** — *Given* bốn tiến trình cùng nâng cấp một kho, *When* chạy, *Then* không lỗi và mỗi phiên bản được ghi một lần (`test_processes_starting_together_record_each_version_once`). |
| **AC-83.4** — *Given* kho còn thiếu phiên bản, *When* chạy `db_cli status`, `migrate`, rồi `status`, *Then* lần đầu trả mã 1 và ghi "CHƯA áp dụng"; lần sau trả mã 0 (`test_status_says_what_is_pending`). |
| **AC-83.5** — *Given* cấu trúc chuẩn, *When* đối chiếu với từ điển dữ liệu, *Then* collection nào cũng được mô tả (`test_every_collection_is_in_the_data_dictionary`). |

### FR-84 — Triển khai lên máy chủ có HTTPS

**Mô tả:** Bộ triển khai `docker-compose.prod.yml` + `deploy/Caddyfile` + `deploy/vps/*.sh` chạy hệ thống trên một máy chủ Ubuntu. Caddy là lối vào duy nhất ở cổng 80 và 443, tự cấp chứng chỉ HTTPS cho tên miền trong `AICEFR_DOMAIN`; gateway không mở cổng nào. `core` và `web` đánh dấu cookie Secure và biết địa chỉ HTTPS của mình. Bản triển khai không bao giờ chép tệp `.env` từ máy phát triển. Có kịch bản sao lưu và khôi phục. Hướng dẫn: `docs/plan/TRIEN_KHAI_VPS.md`.
**Ưu tiên:** S

| Acceptance Criteria |
| --- |
| **AC-84.1** — *Given* cấu hình production, *When* đọc các cổng, *Then* chỉ Caddy mở 80 và 443 (`test_caddy_is_the_only_public_entry_on_80_and_443`). |
| **AC-84.2** — *Given* cấu hình production, *When* đọc biến môi trường của `core` và `web`, *Then* `AICEFR_HTTPS_ONLY=1` và `AICEFR_PUBLIC_URL` là địa chỉ https của tên miền (`test_core_and_web_mark_cookies_secure_and_know_their_https_address`). |
| **AC-84.3** — *Given* chưa đặt tên miền, *When* đọc cấu hình, *Then* tên miền là bắt buộc, không có giá trị mặc định (`test_the_domain_is_required_not_defaulted`). |
| **AC-84.4** — *Given* kịch bản `deploy.sh`, *When* đọc danh sách loại trừ, *Then* tệp `.env` không bao giờ được chép lên máy chủ (`test_the_deploy_never_ships_an_env_file`). |

### FR-85 — Tính lượt trên bản triển khai thương mại (kênh NetID)

**Mô tả:** Chỉ khi `AICEFR_METERING=on`, tức bản triển khai cho kênh NetID, mỗi bài nộp bị tính lượt theo bảng giá team chốt ngày 24/10/2026 (D057): bài tới 1 phút là 1 lượt (2.000 IDPoint, quy ước 1 IDPoint = 1 đồng), mỗi phút bắt đầu thêm 0,7 lượt (1.400 IDPoint), tối đa 5 phút; bài luyện tập trả 50%. Người bán đặt các mức này bằng `AICEFR_PRICE_*` và `AICEFR_IDPOINT_PER_RUN`. Mỗi bút toán ghi kèm số token Whisper đã dùng (1.500 token âm thanh cho mỗi cửa sổ 30 giây, thêm một cửa sổ kiểm tra ngôn ngữ, cộng số token chữ) để tính giá vốn và đối soát, không dùng để tính giá. Khi nộp, hệ thống giữ chỗ theo thời lượng tối đa của đề, lấy lượt miễn phí của chu kỳ trước (3 lượt, chu kỳ bắt đầu ngày 16) rồi tới ví; trang Nộp bài báo trước giá tối đa. Bài có kết quả thì thu theo thời lượng thật và trả lại phần thừa; mọi kết cục khác thì hoàn hết. Bản của trường và nghiên cứu không bao giờ giữ, thu hay từ chối gì (BR-29, BR-30), và bản tính lượt không chạy thực nghiệm nghiên cứu. Thiết kế: `docs/plan/TINH_GIA_THEO_TOKEN.md`.
**Ưu tiên:** C

| Acceptance Criteria |
| --- |
| **AC-85.1** — *Given* bảng giá `price-v3-per-recording`, *When* tính bài 1, 35 và 60 giây, *Then* đều 1 lượt = 2.000 IDPoint (`test_a_recording_up_to_a_minute_is_one_run`); bài 61–120 giây là 3.400 IDPoint, 5 phút trở lên là 7.600 (`test_every_further_minute_adds_seven_tenths_of_a_run_up_to_five`). |
| **AC-85.2** — *Given* còn lượt miễn phí và có ví, *When* giữ chỗ, *Then* lấy lượt miễn phí trước (`test_free_runs_are_used_before_the_wallet`). |
| **AC-85.3** — *Given* lượt miễn phí và ví cộng lại không đủ, *When* giữ chỗ, *Then* bị từ chối và không lấy gì (`test_a_hold_beyond_free_and_wallet_is_refused_and_takes_nothing`). |
| **AC-85.4** — *Given* một bài đã được giữ chỗ, *When* giữ lại cùng bài, *Then* không lấy thêm (`test_holding_the_same_key_twice_takes_once`). |
| **AC-85.5** — *Given* giữ 5 lượt, *When* bài có kết quả và dùng hết 2 lượt, *Then* thu 2 lượt và trả 3 lượt, vào ví trước (`test_a_result_charges_what_was_used_and_returns_the_rest`). |
| **AC-85.6** — *Given* bài đang giữ chỗ, *When* máy chấm báo lỗi, *Then* bài FAILED và lượt được hoàn (`test_a_failed_scoring_releases_the_hold`). |
| **AC-85.7** — *Given* 12 bài nộp cùng lúc, 3 lượt miễn phí và 2 lượt trong ví, *When* giữ chỗ, *Then* đúng 5 bài qua, số dư không âm (`test_concurrent_holds_never_overdraw`). |
| **AC-85.8** — *Given* bản của trường (`AICEFR_METERING` tắt), *When* nộp nhiều bài, *Then* không giữ, không thu, không từ chối (`test_with_metering_off_nothing_is_held_or_refused`). |
| **AC-85.9** — *Given* hết lượt, *When* nộp bài, *Then* HTTP 402 kèm lời giải thích, không lưu bài hay tệp ghi âm nào (`test_a_submission_without_runs_left_is_refused_with_402`). |
| **AC-85.10** — *Given* bản tính lượt, *When* quản trị viên tạo thực nghiệm nghiên cứu, *Then* bị từ chối (`test_the_metered_deployment_runs_no_research_study`). |

### FR-86 — Hiệu chuẩn band tuỳ chọn (D052)

**Mô tả:** Có thêm artifact `ridge_resp_v2_cal`: điểm của `ridge_resp_v2` giãn quanh trung bình với hệ số lambda và hai ngưỡng band ước lại, khớp bằng CV lồng theo người nói. Quản trị viên bật hay tắt như mọi mô hình (FR-36); mặc định không đổi. Báo cáo vẫn ghi chưa hiệu chuẩn.
**Ưu tiên:** C

| Acceptance Criteria |
| --- |
| **AC-86.1** — *Given* một đầu vào trong vùng huấn luyện, *When* chấm bằng hai artifact, *Then* điểm hiệu chuẩn bằng `mu + lambda * (điểm gốc - mu)` (`test_the_calibrated_score_is_the_base_score_stretched_around_mu`). |
| **AC-86.2** — *Given* artifact hiệu chuẩn, *When* tạo báo cáo, *Then* `is_calibrated` vẫn sai (`test_the_report_keeps_its_not_calibrated_warning`). |
| **AC-86.3** — *Given* bản cài mới, *When* chưa ai bật, *Then* mô hình mặc định vẫn là `ridge_resp_v2` (`test_the_default_model_is_unchanged`). |

### FR-87 — Gói lượt mua qua cổng thanh toán (D053)

**Mô tả:** Trên bản tính lượt có bật thanh toán, sinh viên mua gói lượt ở trang Lượt của tôi; khi cổng báo đã thanh toán, số lượt vào ví của chính người mua, đúng một lần.
**Ưu tiên:** C

| Acceptance Criteria |
| --- |
| **AC-87.1** — *Given* đơn gói 10 lượt, *When* cổng báo thành công nhiều lần, *Then* ví tăng đúng 10 lượt (`test_a_paid_pack_reaches_the_buyers_wallet_once`). |
| **AC-87.2** — *Given* dịch vụ tính lượt không trả lời lúc thanh toán, *When* gọi lại sau, *Then* lượt được cộng (`test_a_pack_paid_while_metering_was_away_is_credited_later`). |
| **AC-87.3** — *Given* bản không tính lượt, *When* đặt gói, *Then* 409 (`test_no_packs_where_runs_are_not_counted`). |

### FR-88 — Lớp học và giao bài (D054)

**Mô tả:** Giảng viên tạo lớp, thêm sinh viên, giao đề đánh giá kèm hạn nộp và xem ai nộp đúng hạn, muộn hay chưa nộp; sinh viên vào lớp bằng mã và xem bài được giao.
**Ưu tiên:** S

| Acceptance Criteria |
| --- |
| **AC-88.1** — *Given* một đề đã giao, *When* thành viên nộp bài đề đó, *Then* bài được tính là đã nộp đúng hạn (`test_a_submission_of_the_task_counts_as_handed_in`). |
| **AC-88.2** — *Given* bài làm trước lúc giao, *When* xem tiến độ, *Then* bài đó không được tính (`test_work_before_the_task_was_set_does_not_count`). |
| **AC-88.3** — *Given* lớp của giảng viên khác, *When* mở, *Then* 404 (`test_another_teachers_class_is_not_found`). |

### FR-89 — Nhắc việc trong ứng dụng (D055)

**Mô tả:** Trang Luyện tập hiện tối đa 3 lời nhắc, gấp trước: bài được giao sắp hạn hoặc quá hạn, chuỗi ngày, ôn tập đến hạn, mục tiêu hôm nay, hết lượt.
**Ưu tiên:** C

| Acceptance Criteria |
| --- |
| **AC-89.1** — *Given* không có việc gì, *When* mở trang, *Then* không có lời nhắc (`test_nothing_to_do_means_no_reminder`). |
| **AC-89.2** — *Given* chuỗi 4 ngày chưa giữ hôm nay, *When* mở trang, *Then* lời nhắc nêu ngày nghỉ được phép (`test_a_streak_not_kept_today_is_said_kindly_and_more_firmly_in_the_evening`). |

### FR-90 — Tự nghe lại có mốc đối chứng (D056)

**Mô tả:** Khi bật, sinh viên nghe lại các đoạn 6 giây của bài mình, gồm đoạn máy chọn và đoạn ngẫu nhiên không phân biệt, chọn một trong bốn câu giống nhau và ghi điều định nói; báo cáo cho quản trị viên so tỷ lệ xác nhận giữa hai loại đoạn.
**Ưu tiên:** C

| Acceptance Criteria |
| --- |
| **AC-90.1** — *Given* một bài có cờ, *When* mở bài nghe lại, *Then* có đoạn đối chứng tránh mọi chỗ bị gắn cờ và không lộ nguồn (`test_a_control_moment_avoids_everything_flagged`, `test_the_learner_is_never_told_which_moment_is_which`). |
| **AC-90.2** — *Given* bộ chọn không hơn ngẫu nhiên, *When* phân tích, *Then* chỉ số chính không đạt (`test_a_picker_no_better_than_chance_does_not_pass`). |
| **AC-90.3** — *Given* người học rút quyền dùng cho nghiên cứu, *When* phân tích, *Then* nhãn của họ bị loại (`test_only_the_owner_listens_and_the_analysis_counts_the_labels`). |

## 3.10. Yêu cầu xác nhận KHÔNG cài đặt (Won't)

| Mã | Nội dung | Lý do |
| --- | --- | --- |
| FR-W1 | Chấm tiêu chí Interaction từ hội thoại | Không có Task C; suy từ độc thoại vi phạm R1 mục 5 |
| FR-W2 | Fine-tune toàn bộ mô hình nền | Không đủ GPU và thời gian (C-05, C-08) |
| FR-W3 | Ứng dụng mobile native | Ngoài phạm vi 12 tuần |
| FR-W4 | Chatbot luyện nói / AI Conversation Partner | Ngoài construct (R4 mục 3) |
| FR-W5 | Tự động quyết định đậu/rớt, xếp lớp, cấp chứng chỉ | Bị cấm bởi C-09 và R4 mục 6.1 |
| FR-W7 | Sinh viên tự mua gói, gói cá nhân hay quảng cáo trên trang của sinh viên | Gói là của trường (BR-29); bán lẻ cho cá nhân phải bỏ BR-02, BR-03 và đặt người tham gia khảo sát vào hai mức khác nhau (D033) |
| FR-W6 | Bảng xếp hạng, điểm kinh nghiệm (XP), thành tựu dựa trên điểm hay band, lời nhắc "sắp mất chuỗi" | So với bạn cùng lớp làm người đứng cuối nản lòng; điểm và band có sai số cỡ nửa band nên không dùng làm thước thưởng được (BR-28, D032) |

---

# 4. USE CASE

## 4.1. Danh sách use case

| Mã | Tên | Actor chính | Actor phụ | FR liên quan | Ưu tiên |
| --- | --- | --- | --- | --- | --- |
| UC-01 | Nộp bài nói và nhận kết quả | Sinh viên | — | FR-01..05, FR-18..22, FR-39, FR-55 | M |
| UC-02 | Nộp lại bài khi bị từ chối vì chất lượng | Sinh viên | — | FR-06..09, FR-02 | M |
| UC-03 | Xử lý bài nói qua pipeline chấm điểm | — *(use case nội bộ, được UC-01 `include`)* | — | FR-05, FR-10..22 | M |
| UC-04 | Xem báo cáo có bằng chứng | Sinh viên | — | FR-24..27, FR-53, FR-54 | M |
| UC-05 | Giảng viên duyệt bài trong hàng đợi | Giảng viên | — | FR-28..31, FR-53 | M |
| UC-06 | Giảng viên sửa kết quả AI | Giảng viên | — | FR-30, FR-31 | M |
| UC-07 | Quản trị viên xử lý yêu cầu rút đồng thuận | Quản trị viên | Sinh viên | FR-34, FR-35 | M |
| UC-08 | Quản trị viên cấu hình ngưỡng QC | Quản trị viên | — | FR-08 | S |
| UC-09 | Quản trị viên kích hoạt phiên bản mô hình | Quản trị viên | — | FR-36 | S |
| UC-10 | Quản trị viên tạo tài khoản và phân vai trò | Quản trị viên | — | FR-32, FR-52 (D028), FR-60 (D029) | M |
| UC-11 | Xuất hồ sơ năng lực nói đã kiểm duyệt | Giảng viên | — | FR-38 | S |
| UC-12 | Huấn luyện lại mô hình từ manifest đã khóa | Quản trị viên | — | FR-18..20 | S |
| UC-13 | Sinh viên ký phiếu đồng thuận | Sinh viên | — | *(chưa có FR — xem ghi chú)* | M |
| UC-14 | Sinh viên rút đồng thuận và tự xóa bài | Sinh viên | — | FR-35 | M |
| UC-15 | Sinh viên xem tiến độ theo thời gian | Sinh viên | — | FR-27a, FR-65 (D032) | S |
| UC-16 | Sinh viên xuất dữ liệu cá nhân và hồ sơ năng lực | Sinh viên | — | FR-34, FR-38 | S |
| UC-17 | Đăng nhập và kết thúc phiên | Sinh viên, Giảng viên, Quản trị viên | — | FR-32, FR-51 (D028), FR-56..FR-59 (D029), FR-74 (D036) | M |
| UC-18 | Sinh viên luyện tập theo nhiệm vụ gợi ý | Sinh viên | — | FR-40..FR-44 (D023) | S |
| UC-19 | Sinh viên học theo lộ trình bài học | Sinh viên | — | FR-45, FR-46, FR-48, FR-50 (D025), FR-65, FR-66 (D032) | S |
| UC-20 | Giáo viên soạn lộ trình và theo dõi lượt luyện | Giảng viên | — | FR-45, FR-47, FR-49 (D025) | S |
| UC-21 | Giảng viên chấm mù bài nói trong đợt chấm | Giảng viên | — | FR-62, FR-63 (D030) | S |
| UC-22 | Quản trị viên tổ chức đợt chấm mù và xem độ đồng thuận | Quản trị viên | — | FR-61, FR-63, FR-64 (D030) | S |
| UC-23 | Quản trị viên mua, nâng cấp hoặc gia hạn gói dịch vụ | Quản trị viên | Cổng thanh toán | FR-67..FR-70 (D034), FR-71..FR-73 (D035) | S |

> **Vì sao không dòng nào còn ghi "Hệ thống" ở cột actor.** Bốn dòng trước đây
> ghi như vậy — UC-01, UC-03, UC-05, UC-11 — và đó là một **lỗi mô hình hoá**:
> trong sơ đồ use case, **hệ thống đang được thiết kế chính là ranh giới**, không
> phải một tác nhân. Tác nhân theo định nghĩa nằm **ngoài** ranh giới đó. Vẽ hệ
> thống thành một hình tròn bên ngoài rồi cho nó mũi tên trỏ ngược vào chính
> mình là tự mâu thuẫn.
>
> Ba tác nhân của đề tài này là **Sinh viên, Giảng viên đánh giá, Quản trị
> viên** — và chỉ ba. Nếu sau này có hệ thống **bên ngoài** tham gia (ví dụ LMS
> của trường gọi API), hệ thống đó mới là tác nhân, vì nó thật sự nằm ngoài ranh
> giới.
>
> UC-03 vì thế **không có tác nhân nào**: nó là một use case nội bộ, chạy vì
> UC-01 `include` nó. Điều đó hợp lệ trong UML — một use case được `include`
> không cần liên kết trực tiếp tới tác nhân; giá trị nó tạo ra đến tay sinh viên
> thông qua UC-01.

> **Vì sao có UC-13 … UC-17.** Bảng này ban đầu có 12 use case, và khi vẽ lại ba
> sơ đồ use case thì lộ ra rằng **sinh viên làm được nhiều việc hơn hẳn những gì
> bảng ghi**. Ba bằng chứng đo được, không phải nhận định:
>
> 1. **Năm trong bốn mươi mốt FR không use case nào phủ** — `FR-21a`, `FR-23`,
>    `FR-27a`, `FR-33`, `FR-37`. Ba cái giữa là ràng buộc nội bộ nên không cần
>    use case, nhưng **`FR-27a` — "Người học xem tiến độ của mình theo thời
>    gian" — là tính năng người học dùng trực tiếp và đã chạy** (`/my-progress`,
>    `GET /api/v1/me/progress`). Nay là UC-15.
> 2. **Hai use case giao sai tác nhân so với mã đang chạy.** UC-07 giao việc rút
>    đồng thuận cho quản trị viên, nhưng `POST /api/v1/me/consent/withdraw` và
>    `DELETE /api/v1/responses/{id}` cho sinh viên tự làm — chính ghi chú phạm vi
>    của FR-35 đã thừa nhận hai đường này. UC-11 giao việc xuất hồ sơ cho giảng
>    viên, nhưng mã chỉ có `GET /api/v1/me/profile.json` cho sinh viên tự xuất.
>    Nay tách thành UC-14 và UC-16, còn UC-07 và UC-11 giữ nguyên phần thuộc về
>    quản trị viên và giảng viên.
> 3. **Việc ký phiếu đồng thuận không có FR nào cả.** Nó đã chạy (màn hình
>    `/consent`, `POST /api/v1/me/consent`), được hệ thống bắt buộc
>    (`Consent.maySubmit()`, mã lý do `CONSENT_MISSING`), và tài liệu này chỉ
>    nhắc tới nó như **tiền điều kiện** của UC-01. Một hành vi bắt buộc mà không
>    có yêu cầu nào mô tả là một lỗ hổng của SRS, không phải của mã. UC-13 ghi
>    nhận nó; **phần FR tương ứng vẫn còn thiếu và cần bổ sung**, nên ô FR của
>    UC-13 để trống có chủ ý thay vì gán bừa một mã cho đủ.


## 4.2. Đặc tả chi tiết

### UC-01 — Nộp bài nói và nhận kết quả

| Mục | Nội dung |
| --- | --- |
| **Mã** | UC-01 |
| **Actor chính** | Sinh viên |
| **Mô tả** | Sinh viên tải lên bản ghi bài nói cho một đề bài và nhận kết quả ước lượng kèm bằng chứng |
| **Tiền điều kiện** | Sinh viên đã đăng nhập; đã ký phiếu đồng thuận (`consent_version` hợp lệ); đã chọn `task_id` |
| **Kích hoạt** | Sinh viên bấm "Nộp bài nói" |

**Luồng chính:**

1. Sinh viên chọn đề bài Task A hoặc Task B trên giao diện.
2. Hệ thống tạo phiên và trả `session_id` (FR-01).
3. Sinh viên chọn file audio và bấm tải lên.
4. Hệ thống kiểm tra định dạng, dung lượng, tạo `response_id`, lưu file gốc (FR-02).
5. Hệ thống chuẩn hóa audio về mono 16 kHz (FR-03).
6. Hệ thống chạy QC; kết quả `PASS` (FR-06, FR-07).
7. Hệ thống đưa response vào hàng đợi chấm, trả `job_id`, hiển thị "Đang xử lý" (FR-05).
8. Pipeline chạy (xem UC-03) và hoàn tất.
9. Giao diện tự làm mới, hiển thị band ước lượng, độ tin cậy, tối đa 6 bằng chứng và nhận xét theo mẫu (FR-24..27).
10. Nếu bài bị gắn cờ, giao diện hiện "Kết quả đang chờ giảng viên xác nhận".

**Luồng thay thế:**

- **3a. Định dạng không hỗ trợ:** Hệ thống trả `AUDIO_UNSUPPORTED`, hiển thị danh sách định dạng cho phép; quay lại bước 3.
- **6a. QC = REJECT:** Hệ thống dừng pipeline, hiển thị lý do và gợi ý khắc phục (FR-09); chuyển sang UC-02.
- **6b. QC = REVIEW:** Pipeline vẫn chạy nhưng response được gắn cờ; tiếp tục bước 7.
- **8a. ASR lỗi:** Trạng thái `FAILED` + `ASR_FAILED`; giao diện hiển thị "Không xử lý được bản ghi, vui lòng thử lại"; không hiển thị band (FR-12).
- **8b. Quá nhiều đặc trưng thiếu:** Trạng thái `REVIEW_REQUIRED` + `TOO_MANY_MISSING_FEATURES`; không hiển thị band (FR-17).

**Hậu điều kiện:**

- Thành công: tồn tại bản ghi response với `status = COMPLETED` hoặc `REVIEW_REQUIRED`, có band ước lượng, evidence, provenance đầy đủ; `teacher_verified = false`.
- Thất bại: tồn tại bản ghi response với `status ∈ {REJECTED, FAILED}`, `band = null`, có reason code.

---

### UC-03 — Xử lý bài nói qua pipeline chấm điểm

| Mục | Nội dung |
| --- | --- |
| **Mã** | UC-03 |
| **Actor chính** | — *(use case nội bộ; không có tác nhân, được UC-01 `include`)* |
| **Mô tả** | Thực thi toàn bộ chuỗi QC → ASR → feature → scoring → band → evidence → flag cho một response |
| **Tiền điều kiện** | Response tồn tại, `qc_status ∈ {PASS, REVIEW}`, model artifact đã nạp |
| **Kích hoạt** | Job được lấy khỏi hàng đợi |

**Luồng chính:**

1. Worker nạp `ProcessingRequest` với đủ các trường version.
2. Gọi ASR, sinh `transcript_verbatim`, `transcript_clean`, word timestamps, confidence (FR-10, FR-11).
3. Trích 7 đặc trưng fluency (FR-14).
4. Trích 4 đặc trưng từ vựng (FR-15).
5. Trích 3 đặc trưng chất lượng transcript (FR-16).
6. Đóng gói `feature_vector` kèm version và hash (FR-17).
7. Chạy Ridge → `score_feature` (FR-18).
8. Chạy BERT grader → `score_text` (FR-19).
9. Late fusion → `score_final` (FR-20).
10. Quy band và tính `boundary_distance` (FR-21).
11. Tính `confidence` (FR-22).
12. Đặt tiêu chí Interaction là `null` + `insufficient_evidence` (FR-23).
13. Sinh evidence và nhận xét theo mẫu (FR-24, FR-25).
14. Áp 4 quy tắc cờ review (FR-28).
15. Ghi kết quả vào DB và đặt job `COMPLETED` hoặc `REVIEW_REQUIRED`.

**Luồng thay thế:**

- **2a. ASR ném ngoại lệ hoặc timeout > 180 s:** Ghi `ASR_FAILED`/`ASR_TIMEOUT`, job → `FAILED`, dừng; không tạo feature/score.
- **2b. Transcript 0 từ:** Job → `REVIEW_REQUIRED` + `TRANSCRIPT_INCOMPLETE`, dừng trước bước 7.
- **6a. > 5/14 đặc trưng `null`:** Job → `REVIEW_REQUIRED` + `TOO_MANY_MISSING_FEATURES`, dừng trước bước 7.
- **8a. Transcript < 20 token:** Bỏ qua bước 8, đặt `fusion_mode = "feature_only"`, tiếp tục bước 9.
- **13a. Không evidence hợp lệ:** Nhận xét rỗng, tiếp tục bước 14.
- **15a. Ngoại lệ không lường trước:** Ghi log với `run_id` và `reason_code = "INTERNAL_ERROR"`, job → `FAILED`, dọn file tạm.

**Hậu điều kiện:** Job kết thúc ở đúng một trạng thái cuối; mọi file tạm đã xóa; file audio gốc không đổi (kiểm chứng bằng SHA-256).

---

### UC-05 — Giảng viên duyệt bài trong hàng đợi

| Mục | Nội dung |
| --- | --- |
| **Mã** | UC-05 |
| **Actor chính** | Giảng viên đánh giá |
| **Mô tả** | Giảng viên xem xét các bài bị gắn cờ và xác nhận kết quả AI |
| **Tiền điều kiện** | Giảng viên đăng nhập vai trò `teacher`; hàng đợi có ít nhất 1 bài |
| **Kích hoạt** | Giảng viên mở trang "Hàng đợi duyệt" |

**Luồng chính:**

1. Hệ thống hiển thị danh sách bài chờ, sắp xếp confidence tăng dần (FR-29).
2. Giảng viên chọn một bài.
3. Hệ thống khóa bài cho giảng viên này trong 15 phút và hiển thị: band AI, độ tin cậy, lý do gắn cờ, trình phát audio, transcript có đánh dấu vị trí pause/filler/từ confidence thấp, 6 evidence.
4. Giảng viên nghe audio, bấm vào một evidence để nhảy tới mốc thời gian tương ứng.
5. Giảng viên bấm "Đồng ý với kết quả AI".
6. Hệ thống tạo bản ghi review `action = APPROVE`, đặt `teacher_verified = true`, ghi audit (FR-30, FR-31).
7. Hệ thống loại bài khỏi hàng đợi và mở bài kế tiếp.

**Luồng thay thế:**

- **3a. Bài đang bị giảng viên khác khóa:** Hiển thị "Đang được [tên] xem", nút lưu vô hiệu; giảng viên chọn bài khác.
- **5a. Giảng viên không đồng ý:** Chuyển sang UC-06.
- **5b. Giảng viên bấm "Bỏ qua":** Bài quay lại hàng đợi, khóa được giải phóng, không tạo bản ghi review.
- **6a. Mất kết nối khi lưu:** Hệ thống hiển thị lỗi và giữ nguyên nội dung đã nhập trong form để thử lại.

**Hậu điều kiện:** Bài có `teacher_verified = true`, tồn tại đúng 1 bản ghi review mới và 1 bản ghi audit; báo cáo hiển thị "Đã được giảng viên xác nhận".

---

### UC-06 — Giảng viên sửa kết quả AI

| Mục | Nội dung |
| --- | --- |
| **Mã** | UC-06 |
| **Actor chính** | Giảng viên đánh giá |
| **Mô tả** | Giảng viên thay đổi band do AI đề xuất và ghi lý do |
| **Tiền điều kiện** | Giảng viên đang mở một bài trong hàng đợi và đang giữ khóa |
| **Kích hoạt** | Giảng viên bấm "Sửa kết quả" |

**Luồng chính:**

1. Hệ thống hiện ô chọn band (A2/B1/B2) và ô lý do bắt buộc.
2. Giảng viên chọn band mới, chọn mã lý do từ danh sách (`ASR_ERROR`, `AUDIO_QUALITY`, `RUBRIC_JUDGEMENT`, `BOUNDARY_CASE`, `OTHER`) và nhập ghi chú.
3. Giảng viên bấm lưu.
4. Hệ thống kiểm tra lý do không rỗng (FR-30).
5. Hệ thống tạo bản ghi review `action = OVERRIDE` với `ai_band` và `final_band`, đặt `teacher_verified = true`, ghi audit với `before_value`/`after_value` (FR-31).
6. Báo cáo hiển thị cả hai giá trị kèm ghi chú "Kết quả đã được giảng viên điều chỉnh".

**Luồng thay thế:**

- **4a. Lý do trống:** Hệ thống từ chối với thông báo, giữ nguyên form, không tạo bản ghi.
- **2a. Giảng viên chọn `OTHER`:** Ghi chú trở thành bắt buộc tối thiểu 20 ký tự.
- **5a. Bài đã được người khác duyệt trong lúc chờ:** Hệ thống trả HTTP 409, hiển thị kết quả mới nhất và yêu cầu giảng viên xem lại.

**Hậu điều kiện:** `final_band ≠ ai_band`; audit trail có đầy đủ giá trị trước/sau; hồ sơ `speaking_profile` (nếu xuất) dùng `final_band`.

---

### UC-07 — Quản trị viên xử lý yêu cầu rút đồng thuận

| Mục | Nội dung |
| --- | --- |
| **Mã** | UC-07 |
| **Actor chính** | Quản trị viên |
| **Mô tả** | Thực hiện xóa dữ liệu của một người tham gia khi họ rút đồng thuận |
| **Tiền điều kiện** | Có yêu cầu rút bằng văn bản; danh tính đã xác minh ngoài hệ thống; GVHD đã phê duyệt nếu protocol yêu cầu |
| **Kích hoạt** | Quản trị viên mở trang "Xử lý yêu cầu dữ liệu" |

**Luồng chính:**

1. Quản trị viên nhập `participant_id`.
2. Hệ thống chạy chế độ `dry_run` và liệt kê: số response, số file audio, số transcript, số báo cáo sẽ bị ảnh hưởng (FR-35).
3. Quản trị viên đối chiếu với yêu cầu và bấm "Xác nhận xóa".
4. Hệ thống yêu cầu nhập lại `participant_id` để xác nhận lần hai.
5. Hệ thống xóa audio gốc, audio chuẩn hóa, transcript, feature artifact và báo cáo.
6. Hệ thống ghi deletion log gồm `participant_id` giả danh, số lượng artifact, thời điểm, người thực hiện — không chứa PII.
7. Hệ thống hiển thị thông báo hoàn tất kèm câu nêu rõ mốc cutoff đối với mô hình đã huấn luyện trước đó.

**Luồng thay thế:**

- **2a. Không tìm thấy `participant_id`:** Hiển thị "Không có dữ liệu tương ứng"; kết thúc.
- **4a. Nhập lại sai:** Hủy thao tác, không xóa gì.
- **5a. Một file không xóa được (bị khóa/thiếu quyền):** Hệ thống dừng, ghi trạng thái `PARTIAL`, liệt kê artifact chưa xử lý để xử lý thủ công, không báo hoàn tất.

**Hậu điều kiện:** Không còn artifact có thể truy ngược tới người rút trong `research_root`; deletion log tồn tại và không chứa PII.

---

### UC-11 — Xuất hồ sơ năng lực nói đã kiểm duyệt

| Mục | Nội dung |
| --- | --- |
| **Mã** | UC-11 |
| **Actor chính** | Giảng viên đánh giá |
| **Mô tả** | Xuất `speaking_profile.json` cho một người học để dùng trong báo cáo môn học hoặc module khác |
| **Tiền điều kiện** | Người học có ít nhất 1 kết quả `teacher_verified = true` |
| **Kích hoạt** | Giảng viên bấm "Xuất hồ sơ" trên trang người học |

**Luồng chính:**

1. Giảng viên chọn người học và bấm xuất.
2. Hệ thống lọc các kết quả có `teacher_verified = true` (FR-38).
3. Hệ thống dựng JSON gồm: `speaker_id`, danh sách kết quả (band, ngày chấm, evidence refs), `band_status = "estimated"`, và khối `provenance` đủ 7 trường version.
4. Hệ thống validate theo `schemas/speaking_profile_v1.json`.
5. Hệ thống trả file tải về và ghi log thao tác xuất.

**Luồng thay thế:**

- **2a. Không có kết quả đã duyệt:** Trả JSON với mảng kết quả rỗng kèm thông điệp giải thích; không suy đoán band.
- **4a. Validate thất bại:** Không trả file; ghi lỗi schema với `run_id` để nhóm sửa; hiển thị "Không xuất được hồ sơ, đã ghi nhận lỗi".

**Hậu điều kiện:** File JSON hợp lệ theo schema; không chứa PII; có ghi log thao tác xuất với `speaker_id` giả danh.

---

### UC-10 — Quản trị viên tạo tài khoản và phân vai trò *(cập nhật bản 1.3: D028, D029)*

| Mục | Nội dung |
| --- | --- |
| **Mã** | UC-10 |
| **Actor chính** | Quản trị viên |
| **Mô tả** | Cấp tài khoản theo bút danh cho cả lớp, trông coi tài khoản suốt học kỳ |
| **Tiền điều kiện** | Quản trị viên đăng nhập vai trò `admin`. Tài khoản quản trị đầu tiên tạo bằng `python -m aicefr.accounts_cli` |
| **Kích hoạt** | Quản trị viên mở tab "Tài khoản" của trang Quản trị |
| **Quy tắc** | BR-02, BR-03, BR-11, BR-12, BR-13 |

**Luồng chính:**

1. Hệ thống hiện danh sách tài khoản (ảnh đại diện, bút danh, vai trò, lần đăng nhập gần nhất, trạng thái) và biểu mẫu tạo tài khoản.
2. Quản trị viên chọn vai trò, cách tạo "theo dãy số", số lượng; hệ thống xem trước dãy sẽ tạo, ví dụ "Sẽ tạo SV-011 → SV-040" (FR-52).
3. Quản trị viên bấm "Tạo tài khoản". Hệ thống tạo cả dãy trong một giao dịch, mỗi tài khoản một mật khẩu tạm, ghi nhật ký từng tài khoản.
4. Hệ thống hiện **phiếu tài khoản** (bút danh, mật khẩu tạm, địa chỉ đăng nhập, dòng họ tên ghi tay); quản trị viên in phiếu hoặc tải CSV, rồi ẩn phiếu.
5. Quản trị viên phát phiếu, ghi họ tên lên bản giấy và cất ngoài hệ thống.

**Luồng thay thế:**

- **2a. Tạo một bút danh cụ thể:** chọn "Một bút danh", nhập bút danh; bút danh sai quy tắc hoặc đã có thì bị từ chối, không tạo gì.
- **4a. Rời trang khi phiếu còn trên màn hình:** trình duyệt hỏi lại, vì mật khẩu tạm không xem lại được.
- **6. Quên mật khẩu:** quản trị viên bấm nút cấp mật khẩu tạm mới ở dòng tài khoản; mọi phiên của tài khoản đó kết thúc, phiếu mới hiện ra.
- **7. Tài khoản bị khoá do đăng nhập sai:** quản trị viên gỡ khoá.
- **8. Sinh viên nghỉ học:** quản trị viên tắt tài khoản (đăng xuất ngay, dữ liệu giữ nguyên); xoá dữ liệu là UC-07.
- **9. Xem chi tiết, đổi vai trò, đăng xuất mọi thiết bị, gỡ Google:** bấm bút danh mở bảng chi tiết (FR-60).
- **3a, 6a, 8a, 9a. Thao tác lên chính tài khoản của mình:** hệ thống từ chối (BR-13).

**Hậu điều kiện:** Mỗi tài khoản mới có vai trò, bút danh duy nhất và mật khẩu tạm phải đổi ở lần đăng nhập đầu; nhật ký có một dòng cho mỗi thao tác, không chứa mật khẩu.

---

### UC-17 — Đăng nhập và kết thúc phiên *(cập nhật bản 1.3: D028, D029)*

| Mục | Nội dung |
| --- | --- |
| **Mã** | UC-17 |
| **Actor chính** | Sinh viên, Giảng viên, Quản trị viên |
| **Mô tả** | Vào hệ thống bằng bút danh và mật khẩu hoặc bằng Google đã liên kết; quản lý mật khẩu, phiên và hồ sơ của mình |
| **Tiền điều kiện** | Có tài khoản do quản trị viên cấp, hoặc sinh viên tự đăng ký (BR-03) |
| **Kích hoạt** | Người dùng mở `/login` |
| **Quy tắc** | BR-08, BR-09, BR-10, BR-11, BR-14, BR-15, BR-16, BR-17 |

**Luồng chính:**

1. Người dùng nhập bút danh và mật khẩu (có nút hiện mật khẩu và cảnh báo Caps Lock), bấm "Đăng nhập".
2. Hệ thống kiểm mật khẩu, mở phiên 8 giờ, ghi nhật ký đăng nhập kèm tên thiết bị thô, đưa người dùng về trang chính của vai trò hoặc trang họ định tới.
3. Người dùng làm việc; thanh điều khiển hiện con số việc đang chờ (FR-53).
4. Người dùng mở menu tài khoản, chọn "Đăng xuất"; phiên bị thu hồi ngay.

**Luồng thay thế:**

- **1a. Đăng nhập bằng Google** (máy chủ có cấu hình): người dùng bấm "Đăng nhập bằng Google", chọn tài khoản ở Google, quay về; hệ thống kiểm `state`, `nonce`, PKCE và các claim, tìm bút danh đã liên kết, mở phiên. Tài khoản Google chưa liên kết bị từ chối kèm hướng dẫn (FR-59).
- **2a. Sai mật khẩu:** thông báo chung không nói bút danh có tồn tại hay không; lần thứ năm liên tiếp thì khoá 15 phút (BR-08).
- **2b. Mật khẩu tạm:** hệ thống đưa người dùng tới `/account`; mọi trang và API khác chờ tới khi đặt mật khẩu riêng (BR-11).
- **5. Đổi mật khẩu:** ở mục Bảo mật của `/account`, nhập mật khẩu hiện tại và mật khẩu mới đạt quy tắc (BR-10); các phiên khác kết thúc.
- **6. Liên kết Google:** ở mục Bảo mật, bấm "Liên kết tài khoản Google", xác nhận ở Google; hệ thống lưu mã băm định danh (BR-15, BR-16). Gỡ liên kết ở cùng chỗ.
- **7. Thấy phiên lạ:** ở mục Bảo mật, đăng xuất phiên đó hoặc mọi thiết bị khác, rồi đổi mật khẩu; mục Hoạt động cho biết lần đăng nhập và lần sai gần đây.
- **0a. Tự đăng ký (sinh viên, D065):** ở `/signup` nhập mật khẩu hai lần; hệ thống chọn bút danh ngẫu nhiên `SV-` + 6 ký tự hex, mở phiên và hiện **một lần** bút danh cùng mã khôi phục 16 ký tự (sao chép hoặc tải tệp .txt); người dùng đánh dấu đã lưu mới đi tiếp. Không có ô họ tên, email hay vai trò.
- **8. Quên mật khẩu (D065):** ở `/forgot` nhập bút danh, mã khôi phục và mật khẩu mới; mã đúng thì mật khẩu được thay, mọi phiên khác kết thúc, mã cũ hết hiệu lực và mã mới hiện một lần. Mã sai tính như một lần đăng nhập sai (BR-08). Chưa có mã thì tạo ở mục Bảo mật của `/account` (cả tài khoản đăng ký bằng Google), hoặc nhờ quản trị viên cấp mật khẩu tạm (UC-10; cấp mật khẩu tạm cũng huỷ mã khôi phục).

**Hậu điều kiện:** Có đúng một phiên mới cho lần đăng nhập thành công, mang cách đăng nhập và tên thiết bị; nhật ký có dòng đăng nhập hoặc lần sai (chỉ với bút danh có thật).

---

### UC-21 — Giảng viên chấm mù bài nói trong đợt chấm *(mới ở bản 1.3: D030)*

| Mục | Nội dung |
| --- | --- |
| **Mã** | UC-21 |
| **Actor chính** | Giảng viên (giám khảo) |
| **Mô tả** | Chấm độc lập các bài được phân trong một đợt chấm mù, không thấy bút danh, điểm máy hay điểm của giám khảo khác |
| **Tiền điều kiện** | Giám khảo đăng nhập; quản trị viên đã tạo đợt có phân phiếu cho họ (UC-22) |
| **Kích hoạt** | Giám khảo mở "Chấm mù" trên thanh điều khiển |
| **Quy tắc** | BR-18, BR-19, BR-20, BR-21, BR-26, BR-27 |

**Luồng chính:**

1. Hệ thống hiện các đợt có phiếu của giám khảo, mỗi đợt một thanh tiến độ và các phiếu đánh số theo thứ tự riêng của giám khảo.
2. Giám khảo bấm "Bắt đầu chấm" (hoặc "Chấm tiếp").
3. Hệ thống mở phiếu: đề bài, trình phát bản ghi, biểu mẫu; ghi lúc mở phiếu.
4. Giám khảo nghe hết bài, nhập năm điểm tiêu chí và điểm tổng (0–6, bước 0,5), chọn band, ghi một dòng lý do.
5. Giám khảo bấm "Nộp phiếu". Hệ thống kiểm phiếu, lưu, ghi nhật ký, mở phiếu kế tiếp.
6. Hết phiếu, hệ thống đưa giám khảo về danh sách, đợt hiện "đã chấm xong".

**Luồng thay thế:**

- **4a. Không chấm được:** giám khảo tích "Không chấm được bài này" và chọn lý do; các ô điểm ẩn đi.
- **5a. Phiếu sai quy tắc:** hệ thống chỉ ra ô sai, không lưu.
- **5b. Phiếu đã nộp hoặc đợt đã đóng:** hệ thống từ chối; phiếu đã nộp hiện ở dạng chỉ đọc.
- **3a. Phiếu phân xử:** phiếu ghi là bài phân xử; giám khảo chấm độc lập như mọi phiếu, không thấy điểm của hai người trước.
- **7. Giám khảo mở bài đó từ hàng đợi duyệt hay báo cáo:** hệ thống từ chối cho tới khi phiếu được nộp (BR-19).
- **7a. Đợt tạm đóng và giám khảo đã mở kết quả của máy cho bài đó:** khi đợt mở lại, phiếu hiện "không còn mù" và không nhận điểm (BR-27).

**Hậu điều kiện:** Mỗi phiếu đã nộp có đủ năm điểm, điểm tổng, band và lý do, hoặc cờ không chấm được kèm lý do; không đổi gì ở kết quả của máy hay hàng đợi duyệt.

---

### UC-22 — Quản trị viên tổ chức đợt chấm mù và xem độ đồng thuận *(mới ở bản 1.3: D030)*

| Mục | Nội dung |
| --- | --- |
| **Mã** | UC-22 |
| **Actor chính** | Quản trị viên |
| **Mô tả** | Tạo đợt chấm mù trên bài của người học đã đồng thuận nghiên cứu, giao phân xử, đọc báo cáo đồng thuận và xuất phiếu cho phân tích |
| **Tiền điều kiện** | Có ít nhất hai giảng viên; có bài đủ điều kiện (FR-61) |
| **Kích hoạt** | Quản trị viên mở tab "Chấm mù" của trang Quản trị |
| **Quy tắc** | BR-05, BR-18, BR-21..BR-25, BR-27 |

**Luồng chính:**

1. Hệ thống hiện số bài đủ điều kiện và danh sách giám khảo có thể chọn.
2. Quản trị viên đặt tên đợt, chọn giám khảo, giới hạn số bài nếu cần, bấm "Tạo đợt".
3. Hệ thống rút mẫu, phân hai giám khảo cho mỗi bài, xáo thứ tự từng người theo một hạt giống, ghi hạt giống và nhật ký.
4. Quản trị viên theo dõi tiến độ từng giám khảo trong danh sách đợt.
5. Khi có bài cần phân xử, quản trị viên chọn người phân xử và bấm "Giao phân xử".
6. Khi đủ phiếu, quản trị viên mở "Báo cáo": đồng thuận người–người trước, máy–người sau, kèm khoảng tin cậy theo người nói.
7. Quản trị viên tải CSV hoặc chạy `tools/agreement_report.py` cho phân tích và luận văn, rồi đóng đợt.

**Luồng thay thế:**

- **2a. Chưa đủ hai giám khảo hoặc không có bài:** hệ thống từ chối, không tạo đợt.
- **3a. Giám khảo đã xem kết quả của máy cho một bài:** bài đó đi tới cặp khác; không còn cặp nào thì để ngoài đợt và được báo số lượng (BR-27).
- **5a. Người phân xử đã chấm hoặc đã xem kết quả của máy cho một số bài cần phân xử:** những bài đó bị bỏ qua và được báo số lượng theo từng lý do.
- **6c. Quản trị viên cũng là giám khảo còn nợ phiếu trong đợt:** báo cáo và CSV của đợt chờ tới khi họ nộp xong (BR-27).
- **6a. Quá ít bài:** chỉ số không tính được hiện "—" kèm ghi chú lý do, không hiện số giả.
- **6b. Người học rút đồng thuận:** bài của họ bị bỏ khỏi báo cáo và bản xuất, số bài bị bỏ được ghi ra.

**Hậu điều kiện:** Đợt có hạt giống ghi lại; báo cáo và bản xuất chỉ chứa bài của người đang đồng thuận nghiên cứu; nhật ký ghi lần tạo đợt, phân xử, xem báo cáo và xuất.

---

### UC-23 — Quản trị viên mua, nâng cấp hoặc gia hạn gói dịch vụ *(mới ở bản 1.6: D034; cập nhật bản 1.7: D035)*

| Mục | Nội dung |
| --- | --- |
| **Mã** | UC-23 |
| **Actor chính** | Quản trị viên |
| **Actor phụ** | Cổng thanh toán (cổng thử trong ứng dụng, VNPay, Stripe hoặc MoMo) — hệ thống bên ngoài, gọi vào hệ thống để báo kết quả |
| **Mô tả** | So sánh các gói, mua mới, nâng cấp hoặc gia hạn gói của trường qua cổng thanh toán, nhận biên nhận |
| **Tiền điều kiện** | Bản triển khai bật thu phí; cổng thanh toán đã cấu hình |
| **Kích hoạt** | Quản trị viên mở tab "Gói dịch vụ" của trang Quản trị |
| **Quy tắc** | BR-26, BR-29..BR-35 |

**Luồng chính:**

1. Hệ thống hiện gói đang dùng, mức đang dùng và bảng so sánh Miễn phí, Chuẩn, Nâng cao.
2. Quản trị viên chọn gói, số sinh viên, thời hạn và cổng thanh toán trong các cổng đang bật; hệ thống báo giá: loại giao dịch, ngày chạy, giá, giảm theo năm, phần trừ của gói cũ, số phải trả.
3. Quản trị viên bấm thanh toán; hệ thống tạo đơn, ghi nhật ký và chuyển trình duyệt tới trang của cổng.
4. Người trả thanh toán trên trang của cổng.
5. Cổng gọi địa chỉ thông báo của hệ thống; hệ thống kiểm chữ ký và số tiền, ghi nhận đơn đã thanh toán và cài giấy phép, một lần.
6. Cổng đưa trình duyệt về trang kết quả; trang báo thành công và gói có hiệu lực từ ngày nào.
7. Quản trị viên mở biên nhận để in hoặc lưu PDF.

**Luồng thay thế:**

- **2a. Có gói đặt trước chưa bắt đầu:** báo giá bị từ chối kèm ngày gói đó bắt đầu.
- **3a. Số phải trả bằng 0 (phần trừ đủ trả):** gói được kích hoạt ngay, không qua cổng.
- **3b. Cổng không mở được thanh toán** (khoá sai, số tiền ngoài mức cổng nhận, mất kết nối): đơn ghi không thành công kèm lý do; quản trị viên chọn cổng khác hoặc thử lại.
- **4a. Người trả huỷ, hoặc thanh toán không thành công:** cổng báo kết quả; đơn ghi huỷ hoặc không thành công, gói không đổi.
- **4b. Người trả rời trang của cổng khi chưa trả (Stripe):** trang nói chưa trừ tiền; đơn chờ tới khi phiên thanh toán hết hạn rồi thành huỷ.
- **5a. Chữ ký sai, sai số tiền, hoặc không có đơn:** hệ thống không ghi nhận, trả mã lỗi tương ứng cho cổng, ghi sự kiện để đối soát.
- **5b. Trình duyệt quay về trước khi cổng báo:** trang kết quả ghi nhận kết quả có chữ ký; lần báo sau của cổng không đổi gì.
- **5c. Thanh toán tới sau khi đơn hết hạn chờ 15 phút:** vẫn được ghi nhận.
- **5d. Kết quả phải hỏi lại cổng (Stripe):** trang kết quả đọc lại phiên từ cổng, chỉ cho phiên do hệ thống mở; không hỏi được thì báo chưa xác nhận, đơn được ghi nhận khi webhook tới.
- **1a. Trường trả theo hợp đồng:** quản trị viên dán mã giấy phép thay cho bước 2–6.

**Hậu điều kiện:** Đơn ở trạng thái cuối, mỗi thông điệp của cổng được lưu; nếu đã thanh toán thì có một giấy phép mới; nhật ký có dòng đặt đơn và dòng kết quả. Không có số thẻ hay tài khoản ngân hàng nào trong hệ thống.

# 5. USER STORY VÀ ACCEPTANCE CRITERIA

100% user story dưới đây có acceptance criteria dạng Given/When/Then. Cột "FR" chỉ ra yêu cầu chức năng tương ứng.

| Mã | User story | Acceptance criteria (Given / When / Then) | FR | Ưu tiên |
| --- | --- | --- | --- | --- |
| US-01 | Là **sinh viên**, tôi muốn tải lên bản ghi bài nói để được chấm mà không phải cài phần mềm gì thêm | **G** tôi đã đăng nhập và mở trang nộp bài trên trình duyệt Chrome/Edge — **W** tôi chọn file `.m4a` 4 MB và bấm "Nộp" — **T** trong 5 giây tôi thấy thông báo "Đã nhận bài, đang xử lý" kèm mã bài dạng UUID | FR-02 | M |
| US-02 | Là **sinh viên**, tôi muốn biết ngay nếu bản ghi của tôi quá kém để thu lại, thay vì nhận điểm sai | **G** bản ghi có SNR 3 dB — **W** QC chạy xong — **T** tôi thấy thông báo nêu chỉ số đo được, ngưỡng yêu cầu và nút "Nộp lại", và không thấy bất kỳ band nào | FR-07, FR-09 | M |
| US-03 | Là **sinh viên**, tôi muốn xem mức CEFR ước lượng của bài nói | **G** bài đã chấm xong — **W** tôi mở trang kết quả — **T** tôi thấy một trong A2/B1/B2 kèm nhãn "ước lượng" và dòng chữ "Không phải chứng chỉ CEFR" | FR-21 | M |
| US-04 | Là **sinh viên**, tôi muốn biết hệ thống chắc chắn đến đâu về kết quả | **G** bài đã chấm xong — **W** tôi xem kết quả — **T** tôi thấy độ tin cậy dạng phần trăm và nhãn phân loại Cao (≥75%) / Trung bình (60–74%) / Thấp (<60%) | FR-22 | M |
| US-05 | Là **sinh viên**, tôi muốn nghe lại đúng đoạn mà hệ thống cho là tôi ngập ngừng | **G** báo cáo có evidence loại `LONG_PAUSE` tại 42,3 s — **W** tôi bấm vào evidence đó — **T** trình phát nhảy tới 42,3 s (sai số ≤ 0,5 s) và phát từ đó | FR-24 | M |
| US-06 | Là **sinh viên**, tôi muốn thấy bản ghi lời nói của mình dưới dạng văn bản | **G** ASR đã chạy — **W** tôi mở tab "Bản ghi lời" — **T** tôi thấy transcript, các từ có confidence < 0,50 được tô khác màu kèm chú thích "Máy có thể nghe nhầm từ này" | FR-10, FR-16 | M |
| US-07 | Là **sinh viên**, tôi muốn hệ thống chỉ đưa nhận xét dựa trên bằng chứng cụ thể, không nói chung chung | **G** báo cáo có 4 câu nhận xét — **W** tôi bấm vào biểu tượng bằng chứng cạnh mỗi câu — **T** mỗi câu mở ra ít nhất 1 evidence có mốc thời gian hoặc số liệu cụ thể | FR-25 | M |
| US-08 | Là **sinh viên**, tôi muốn biết nên luyện gì tiếp theo, nhưng không quá 2 việc | **G** báo cáo có độ tin cậy ≥ 60% — **W** tôi xem mục "Ưu tiên cải thiện" — **T** tôi thấy tối đa 2 mục, mỗi mục gắn với ít nhất 1 evidence | FR-26 | S |
| US-09 | Là **sinh viên**, tôi muốn biết khi nào kết quả cần giảng viên xác nhận | **G** bài bị gắn cờ review — **W** tôi mở kết quả — **T** tôi thấy nhãn "Chờ giảng viên xác nhận" và lý do diễn đạt bằng tiếng Việt, không phải mã lỗi kỹ thuật | FR-28 | M |
| US-10 | Là **sinh viên**, tôi muốn xem lại toàn bộ bài đã nộp và trạng thái của chúng | **G** tôi đã nộp 3 bài — **W** tôi mở trang "Bài của tôi" — **T** tôi thấy đúng 3 dòng với ngày nộp, đề bài, trạng thái và band (nếu có) | FR-04 | M |
| US-11 | Là **sinh viên**, tôi muốn chắc chắn không ai xem được bài của người khác qua tài khoản của tôi | **G** tôi đăng nhập bằng tài khoản của mình — **W** tôi đổi ID trên URL sang bài của người khác — **T** hệ thống trả trang "Không tìm thấy" (HTTP 404) | FR-04, FR-32 | M |
| US-12 | Là **sinh viên**, tôi muốn yêu cầu xóa toàn bộ dữ liệu của mình khi rút đồng thuận | **G** tôi gửi yêu cầu rút qua kênh đã công bố — **W** quản trị viên xử lý xong — **T** tôi nhận xác nhận nêu số lượng dữ liệu đã xóa và mốc cutoff áp dụng với mô hình đã huấn luyện | FR-35 | M |
| US-13 | Là **giảng viên**, tôi muốn thấy ngay những bài rủi ro nhất để ưu tiên duyệt trước | **G** hàng đợi có 10 bài — **W** tôi mở hàng đợi — **T** bài có độ tin cậy thấp nhất ở đầu danh sách và mỗi dòng hiện lý do gắn cờ | FR-29 | M |
| US-14 | Là **giảng viên**, tôi muốn nghe audio và đọc transcript trên cùng màn hình để đỡ chuyển qua lại | **G** tôi mở một bài để duyệt — **W** màn hình tải xong — **T** trình phát audio, transcript và danh sách evidence hiển thị cùng lúc trong một trang, không cần cuộn sang trang khác | FR-29, FR-24 | M |
| US-15 | Là **giảng viên**, tôi muốn xác nhận nhanh khi tôi đồng ý với AI | **G** tôi đang mở một bài — **W** tôi bấm "Đồng ý với kết quả AI" — **T** trong 2 giây bài rời khỏi hàng đợi, `teacher_verified` thành `true` và bài kế tiếp tự mở | FR-30 | M |
| US-16 | Là **giảng viên**, tôi muốn sửa band khi tôi không đồng ý, nhưng hệ thống phải buộc tôi ghi lý do | **G** tôi đổi band từ B1 sang B2 — **W** tôi bấm lưu mà chưa chọn mã lý do — **T** hệ thống chặn lưu và hiện "Bắt buộc nhập lý do khi sửa kết quả AI" | FR-30 | M |
| US-17 | Là **giảng viên**, tôi muốn xem lịch sử ai đã sửa kết quả và sửa vì lý do gì | **G** một bài đã bị sửa 2 lần — **W** tôi mở tab "Lịch sử" — **T** tôi thấy 2 dòng theo thứ tự thời gian với giá trị trước, giá trị sau, mã lý do và người thực hiện | FR-31 | M |
| US-18 | Là **giảng viên**, tôi muốn tránh việc hai người cùng duyệt một bài | **G** đồng nghiệp đang mở bài X — **W** tôi mở bài X — **T** tôi thấy nhãn "Đang được [tên] xem" và nút lưu bị vô hiệu hóa | FR-29 | S |
| US-19 | Là **giảng viên**, tôi muốn kết quả tôi đã duyệt không bị AI ghi đè khi chạy lại pipeline | **G** bài đã có `final_band = B2` do tôi duyệt — **W** quản trị viên chạy lại chấm với model mới — **T** `final_band` giữ nguyên B2, kết quả AI mới lưu thành version riêng | FR-30 | M |
| US-20 | Là **giảng viên**, tôi muốn xuất hồ sơ năng lực nói của sinh viên để dùng trong báo cáo môn học | **G** sinh viên có 2 kết quả đã duyệt — **W** tôi bấm "Xuất hồ sơ" — **T** tôi tải về file JSON hợp lệ theo schema, chứa đúng 2 kết quả, mọi mục có `band_status = "estimated"` | FR-38 | S |
| US-21 | Là **giảng viên**, tôi muốn chắc chắn hệ thống không tự ý chấm tiêu chí Interaction | **G** một bài Task A — **W** tôi mở kết quả chi tiết — **T** mục Interaction hiển thị "Chưa đủ bằng chứng" và không có điểm số | FR-23 | M |
| US-22 | Là **quản trị viên**, tôi muốn tạo tài khoản và gán vai trò cho giảng viên | **G** tôi đăng nhập vai trò admin — **W** tôi tạo tài khoản với vai trò `teacher` — **T** tài khoản đó truy cập được hàng đợi duyệt và bị từ chối (HTTP 403) khi gọi các endpoint quản trị | FR-32 | M |
| US-23 | Là **quản trị viên**, tôi muốn thay đổi ngưỡng QC mà không phải sửa code | **G** tôi sửa `qc_config.yaml` và tăng version lên `qc-v2` — **W** tôi khởi động lại dịch vụ và chấm bài mới — **T** bản ghi QC mới ghi `qc_config_version = "qc-v2"`, bản ghi cũ giữ nguyên `qc-v1` | FR-08 | S |
| US-24 | Là **quản trị viên**, tôi muốn kích hoạt phiên bản mô hình mới mà không làm hỏng báo cáo cũ | **G** hệ thống có `model_v1` và `model_v2` — **W** tôi kích hoạt `model_v2` — **T** báo cáo mới ghi `model_v2`, mọi báo cáo cũ vẫn hiển thị `model_v1` | FR-36 | S |
| US-25 | Là **quản trị viên**, tôi muốn kiểm tra được rằng log hệ thống không rò rỉ dữ liệu cá nhân | **G** một pipeline đã chạy đầy đủ trên fixture — **W** tôi chạy `pytest tests/test_log_privacy.py` — **T** test pass, xác nhận log không chứa email, mã số 7–10 chữ số hoặc đoạn transcript | FR-13, FR-37 | M |
| US-26 | Là **quản trị viên**, tôi muốn xem trước dữ liệu sẽ bị xóa trước khi xóa thật | **G** tôi nhập một `participant_id` — **W** tôi chạy chế độ xem trước — **T** hệ thống liệt kê số response, file audio, transcript, báo cáo sẽ bị xóa và chưa xóa gì cả | FR-35 | M |
| US-27 | Là **quản trị viên**, tôi muốn huấn luyện lại mô hình bằng một lệnh và tái lập được kết quả | **G** manifest dữ liệu và seed đã khóa — **W** tôi chạy `make train` hai lần — **T** hai lần cho ra cùng `rmse_dev` và `qwk_dev` tới 4 chữ số thập phân | FR-18, FR-19 | S |
| US-28 | Là **GVHD**, tôi muốn mọi báo cáo đều truy được về phiên bản mô hình và dữ liệu đã tạo ra nó | **G** một báo cáo bất kỳ — **W** tôi xem khối `provenance` — **T** tôi thấy đủ `model_version`, `feature_version`, `asr_model`, `band_map_version`, `calibration_version`, `qc_config_version`, `scored_at` | FR-27 | M |

| US-29 | Là **sinh viên**, tôi muốn thấy công sức luyện tập của mình được ghi nhận mà không bị đem so với bạn | **G** tôi vừa nói lượt đầu tiên trong một bài học — **W** máy đo xong — **T** tôi thấy "Thành tựu mới: Lượt nói đầu tiên", và ở trang Tiến độ thấy mọi thành tựu kèm mức tôi đã làm được, không có điểm, band hay bảng xếp hạng | FR-65 | S |
| US-30 | Là **sinh viên**, tôi muốn biết vì sao chuỗi ngày của tôi chưa đứt dù hôm qua tôi nghỉ, và tuần này tôi nói nhiều hơn tuần trước không | **G** tôi luyện thứ Hai, nghỉ thứ Ba, luyện thứ Tư — **W** tôi mở trang Luyện tập — **T** ô thứ Ba có viền đứt và chú thích "nghỉ, chuỗi vẫn giữ", thẻ ghi kỷ lục của tôi và số phút bảy ngày qua cạnh bảy ngày trước đó | FR-66 | S |

| US-31 | Là **quản trị viên của khoa**, tôi muốn thấy rõ mỗi gói thêm được gì cho giảng viên để quyết định có nâng cấp không | **G** trường đang dùng gói Miễn phí — **W** tôi mở tab Gói dịch vụ — **T** tôi thấy ba gói cạnh nhau, dòng nào có ở mọi gói, dòng nào mỗi bậc thêm, giá theo sinh viên mỗi tháng, và gói đang dùng được đánh dấu | FR-67 | S |
| US-32 | Là **quản trị viên của khoa**, tôi muốn trả tiền gói qua cổng thanh toán quen thuộc và có biên nhận | **G** tôi đã chọn gói Chuẩn 100 sinh viên 12 tháng — **W** tôi thanh toán thành công trên trang của cổng — **T** tôi quay về trang báo thành công, gói có hiệu lực ngay, biên nhận ghi giá, phần giảm theo năm và số đã trả | FR-69 | S |

| US-33 | Là **quản trị viên của khoa**, tôi muốn chọn trả qua Stripe, VNPay hay MoMo và biết cổng nào đang ở môi trường thử | **G** bản triển khai bật Stripe và MoMo ở môi trường thử — **W** tôi mở ô "Thanh toán qua" — **T** tôi thấy từng cổng với cách trả, nhãn "Thử" và cách trả thử; cổng thiếu khoá được nói rõ tên biến còn thiếu | FR-71 | S |
| US-34 | Là **quản trị viên hệ thống**, tôi muốn biết phải đăng ký địa chỉ nào với Google và còn thiếu gì để bật đăng nhập Google | **G** chưa đặt khoá Google — **W** tôi mở tab Cấu hình — **T** tôi thấy trạng thái, địa chỉ chuyển hướng để sao chép và tên biến còn thiếu; client secret không bao giờ hiện | FR-74 | C |

**Tổng: 34 user story, 34 acceptance criteria — tỷ lệ bao phủ 100%.**

---

# 6. YÊU CẦU PHI CHỨC NĂNG

Mọi NFR dưới đây đều có ràng buộc định lượng và phương pháp đo được ghi rõ. Máy tham chiếu: CPU 8 nhân, 16 GB RAM, không GPU, SSD (ràng buộc C-05).

| Mã | Loại | Yêu cầu định lượng | Cách đo / Kiểm chứng |
| --- | --- | --- | --- |
| **NFR-01** | Hiệu năng — độ trễ pipeline | Thời gian xử lý đầy đủ (QC → ASR → feature → scoring → report) cho một bài nói **120 giây** phải ≤ **60 giây** ở phân vị 90 (P90) trên máy tham chiếu | Script `benchmarks/bench_pipeline.py` chạy trên 30 fixture audio 120 s, ghi P50/P90/P99 vào `benchmarks/results.json`; CI fail nếu P90 > 60 s |
| **NFR-02** | Hiệu năng — phản hồi API | Các endpoint đồng bộ (`POST /sessions`, `GET /responses`, `GET /reports/{id}`, `GET /review/queue`) phải trả về trong ≤ **300 ms** ở P95 với DB chứa 1.000 response | Test tải bằng `locust` 20 người dùng ảo trong 5 phút; đọc P95 từ báo cáo locust; ngưỡng kiểm tra tự động trong `tests/test_perf_api.py` |
| **NFR-03** | Hiệu năng — thông lượng | Hệ thống xử lý được ≥ **40 bài nói 120 giây trong 60 phút** với 2 worker chạy song song, không lỗi OOM | Chạy kịch bản batch 40 file, đo tổng thời gian và RSS đỉnh bằng `psutil`; RSS đỉnh phải ≤ 12 GB |
| **NFR-04** | Độ chính xác — chấm điểm | Trên tập dev Speak & Improve 2025 chia theo speaker, mô hình fusion đạt **QWK(AI, nhãn) ≥ 0,60** và **RMSE ≤ 1,10** trên thang 0–6; **tỷ lệ lệch từ 2 band trở lên ≤ 5%** | `make evaluate` sinh `reports/eval_{model_version}.json` với QWK, RMSE, confusion matrix và khoảng tin cậy 95% bằng cluster bootstrap 2.000 vòng theo `speaker_id`, seed = 0 |
| **NFR-05** | Độ chính xác — ASR | WER của ASR trên tập 20 bài do người chép tay (from scratch) phải được **đo và báo cáo**; nếu WER > **35%** trên một nhóm điều kiện, hệ thống phải tự bật `ASR_LOW_CONFIDENCE` cho nhóm đó | `scripts/measure_wer.py` so transcript ASR với transcript tay bằng `jiwer`, xuất bảng WER theo nhóm SNR và theo band; kết quả lưu `reports/wer_report.md` |
| **NFR-06** | Độ chính xác — hiệu quả cờ review | Bộ quy tắc cờ phải bắt được ≥ **70% số bài lệch từ 2 band trở lên** trong khi gắn cờ ≤ **25% tổng số bài** | `scripts/evaluate_flags.py` dựng đường cong yield–flag rate trên tập có nhãn giảng viên; kiểm tra ngưỡng tự động, xuất `reports/flag_yield.md` |
| **NFR-07** | Bảo mật — xác thực | Mật khẩu băm bằng bcrypt cost ≥ **12**; phiên đăng nhập mang bằng **cookie có chữ ký** (`HttpOnly`, `SameSite=Lax`) tra bảng `auth_sessions` phía máy chủ, hết hạn sau ≤ **8 giờ** và bị vô hiệu ngay khi đăng xuất; khóa tài khoản **15 phút** sau **5 lần** đăng nhập sai liên tiếp. Chọn phiên phía máy chủ thay vì JWT vì JWT không thu hồi được trước hạn: đăng xuất không làm token mất hiệu lực, mà hệ thống có vai trò giảng viên sửa được điểm nên đó là điểm yếu thật | `tests/test_auth_security.py`: kiểm tra tiền tố hash `$2b$12$`, kiểm tra `expires_at` của bản ghi `auth_sessions` ≤ 8 h kể từ khi phát hành, kiểm tra cookie có cờ `HttpOnly` và `SameSite=Lax`, kiểm tra cookie sau khi đăng xuất trả HTTP 401, mô phỏng 6 lần đăng nhập sai và xác nhận HTTP 429 ở lần thứ 6 |
| **NFR-08** | Bảo mật — quét phụ thuộc và bí mật | **0 lỗ hổng mức High/Critical** trong dependency và **0 secret** trong repository tại mỗi lần push | GitHub Actions chạy `pip-audit` và `gitleaks detect` ở mọi PR; pipeline fail khi phát hiện bất kỳ mục High/Critical hoặc bất kỳ secret nào |
| **NFR-09** | Riêng tư — không rò rỉ PII trong log | **0 dòng log** chứa email, chuỗi số 7–10 chữ số, họ tên trong danh sách kiểm tra, hoặc đoạn ≥ 5 từ liên tiếp của transcript, trên một lần chạy pipeline đầy đủ | `tests/test_log_privacy.py` chạy pipeline trên fixture, quét toàn bộ file log bằng regex và so khớp n-gram; CI fail nếu tìm thấy ≥ 1 vi phạm |
| **NFR-10** | Riêng tư — thời gian đáp ứng yêu cầu xóa | Quy trình xóa dữ liệu của một người tham gia hoàn tất trong ≤ **7 ngày làm việc** kể từ khi xác minh, và thao tác kỹ thuật chạy trong ≤ **5 phút** cho một người có tối đa 20 response | Đo bằng timestamp trong deletion log (`verified_at` → `completed_at`); thao tác kỹ thuật đo bằng `tests/test_withdrawal_performance.py` trên dữ liệu synthetic |
| **NFR-11** | Khả dụng — tỷ lệ xử lý thành công | Tỷ lệ job kết thúc ở trạng thái xác định (`COMPLETED`/`REVIEW_REQUIRED`/`REJECTED`) trên tổng số job phải ≥ **98%**; trạng thái `FAILED` do lỗi nội bộ ≤ **2%** | Truy vấn bảng `jobs` cuối mỗi đợt thu; dashboard admin hiển thị tỷ lệ; kịch bản nghiệm thu chạy 100 bài liên tiếp và đếm |
| **NFR-12** | Khả dụng — khôi phục sau lỗi | Sau khi worker bị kill đột ngột, job đang chạy được đưa lại hàng đợi và hoàn tất trong ≤ **10 phút**; **0 file tạm** còn sót trong thư mục làm việc | `tests/test_worker_recovery.py`: kill worker giữa pipeline, khởi động lại, kiểm tra job hoàn tất và `os.listdir(tmp_dir)` rỗng |
| **NFR-13** | Khả năng bảo trì — chất lượng mã | Độ bao phủ test dòng lệnh ≥ **75%** toàn dự án và ≥ **90%** cho các module `qc`, `features`, `scoring`; **0 lỗi** `ruff` trên `src/` | `./kiemtra.sh` chạy `ruff format --check`, `ruff check`, `pytest --cov`. **Hiện trạng:** bao phủ 84%, ruff sạch. `mypy --strict` **chưa được cấu hình** nên phần đó chưa kiểm chứng; GitHub Actions đang tắt, xem `docs/ci/README.md` |
| **NFR-14** | Khả năng bảo trì — tính tái lập | Chạy `make train` hai lần với cùng manifest và seed cho ra `rmse_dev` và `qwk_dev` giống nhau tới **4 chữ số thập phân**; toàn bộ bảng metric của báo cáo sinh lại bằng **1 lệnh** | Job CI `reproducibility` chạy huấn luyện 2 lần và so sánh `metrics.json`; job fail nếu chênh lệch > 1e-4 |
| **NFR-15** | Tương thích | Giao diện web hoạt động đúng trên **Chrome ≥ 120**, **Edge ≥ 120**, **Firefox ≥ 121** ở độ phân giải ≥ **1366×768**; API tuân thủ **OpenAPI 3.1** và schema sinh tự động hợp lệ | Checklist kiểm thử thủ công 12 thao tác chính trên 3 trình duyệt, ghi `tests/manual/browser_matrix.md`; `tests/test_openapi.py` validate spec bằng `openapi-spec-validator` |
| **NFR-16** | Khả năng mở rộng | Đổi backend lưu trữ từ SQLite sang PostgreSQL **không sửa file nào trong `src/aicefr/` ngoài `storage/`** — tầng nghiệp vụ chỉ biết cổng `ResponseStore`. **Hiện trạng:** mới có adapter SQLite, chọn qua biến `AICEFR_DB` (không phải `DATABASE_URL`); adapter PostgreSQL chưa viết; thêm một đặc trưng mới chỉ cần sửa ≤ **2 file** và tăng `feature_version` | Sẽ chạy toàn bộ test suite lần lượt với SQLite và PostgreSQL khi có adapter thứ hai; đường đi chi tiết ghi ở `docs/web/SCALING.md` |
| **NFR-17** | Khả năng triển khai | Toàn bộ hệ thống khởi động bằng **1 lệnh** `docker compose up` và sẵn sàng nhận request trong ≤ **180 giây** trên máy tham chiếu. **Hiện trạng:** một lệnh là đúng, nhưng model **không** nằm trong image — lần chạy thật đầu tiên tải khoảng 1,5 GB rồi cache trên volume `aicefr-models`, nên yêu cầu "không cần Internet" mới đạt từ lần khởi động thứ hai trở đi | Job CI `smoke-offline` build image, chạy compose với `--network none` sau khi build, poll `GET /health` và đo thời gian tới khi trả HTTP 200 |
| **NFR-18** | Dung lượng lưu trữ | Mỗi response tiêu tốn ≤ **6 MB** tổng cộng (audio gốc ≤ 25 MB được nén lại còn bản chuẩn hóa ≤ 4 MB + artifact ≤ 2 MB); hệ thống chứa được **500 response** trong ≤ **3 GB** | `scripts/measure_storage.py` chạy trên 50 response mẫu, tính trung bình và ngoại suy; báo cáo lưu `reports/storage_report.md` |

**Tổng: 18 NFR, 18/18 có ràng buộc định lượng và phép đo cụ thể** (vượt yêu cầu tối thiểu ≥ 5 và mục tiêu ≥ 8).

---

# 7. YÊU CẦU DỮ LIỆU

## 7.1. Lược đồ cơ sở dữ liệu chính

Hiện thực hiện tại (cập nhật 19/09/2026): SQLite thuần, lược đồ khai báo bằng câu lệnh `CREATE TABLE` ngay trong các tệp kho. **Chín bảng đã có**: `response`, `review_action`, `review_lock`, `audit_log`, `app_config` (`storage/repository.py`); `account`, `auth_sessions` (`storage/auth_repository.py`); `task` (`storage/task_repository.py`); `consent` (`storage/consent_repository.py`). Các bảng còn lại trong lược đồ nghiên cứu đầy đủ dưới đây — **chưa hiện thực**.

Mỗi bảng trong số chín bảng đó nay có một lớp hợp đồng tương ứng trong `src/aicefr/contracts.py`, thay cho việc trả về `dict` thô từ câu truy vấn. Trước đây hình dạng của một dòng `review_lock` hay `audit_log` chỉ tồn tại trong đầu người viết câu SQL; nay nó là một lớp có tên, và luật đi kèm nằm cùng dữ liệu (`ReviewLock.has_expired()`, `AuthSession.has_expired()`, `Review.changed_band`).

| Bảng | Cột chính | Ghi chú |
| --- | --- | --- |
| `users` | `user_id` (UUID, PK), `login_name`, `password_hash`, `role` ∈ {student, teacher, admin}, `created_at`, `is_active` | Không lưu họ tên/email trong DB nghiên cứu |
| `sessions` | `session_id` (UUID, PK), `speaker_id`, `task_id`, `prompt_version`, `consent_version`, `pipeline_config_version`, `created_at` | `speaker_id` là alias giả danh ổn định |
| `responses` | `response_id` (UUID, PK), `session_id` (FK), `speaker_id`, `audio_ref`, `audio_sha256`, `duration_ms`, `status`, `submitted_at` | `audio_ref` là đường dẫn tương đối trong `research_root` |
| `qc_results` | `qc_id` (PK), `response_id` (FK), `duration_sec`, `sample_rate_hz`, `clipping_ratio`, `silence_ratio`, `snr_db`, `qc_status`, `reason_codes` (JSON), `qc_config_version` | 5 chỉ số của FR-06 |
| `asr_artifacts` | `asr_id` (PK), `response_id` (FK), `transcript_verbatim`, `transcript_clean`, `words` (JSON), `mean_confidence`, `asr_engine`, `asr_model`, `transcript_version` | Transcript lưu trong DB nghiên cứu đã mã hóa, không vào log |
| `feature_vectors` | `feature_id` (PK), `response_id` (FK), 14 cột đặc trưng (nullable), `feature_version`, `asr_artifact_hash`, `invalid_features` (JSON) | `null` là giá trị hợp lệ, mang nghĩa "không đo được" |
| `scores` | `score_id` (PK), `response_id` (FK), `score_feature`, `score_text`, `score_final`, `band`, `boundary_distance`, `confidence`, `fusion_mode`, `model_version`, `band_map_version`, `calibration_version`, `scored_at` | Nhiều bản ghi cho một response nếu chấm lại |
| `evidence` | `evidence_id` (UUID, PK), `response_id` (FK), `type`, `start_ms`, `end_ms`, `excerpt`, `metric_value`, `extractor_version` | ≤ 6 bản ghi hiển thị cho mỗi báo cáo |
| `reviews` | `review_id` (PK), `response_id` (FK), `reviewer_id`, `action` ∈ {APPROVE, OVERRIDE}, `ai_band`, `final_band`, `reason_code`, `note`, `reviewed_at` | `reviewer_id` giả danh |
| `audit_log` | `audit_id` (PK), `entity_type`, `entity_id`, `action`, `before_value` (JSON), `after_value` (JSON), `actor_id`, `created_at` | Append-only; không có route PUT/DELETE |
| `auth_sessions` | `auth_session_id` (UUID, PK), `user_id` (FK `users`), `issued_at`, `expires_at`, `revoked_at`, `user_agent_hash` | Phiên đăng nhập của NFR-07; **khác** bảng `sessions` (phiên đánh giá). Cookie chỉ mang `auth_session_id` đã ký; xoá hoặc đặt `revoked_at` là phiên mất hiệu lực ngay |
| `jobs` | `job_id` (UUID, PK), `response_id` (FK), `status`, `queued_at`, `started_at`, `finished_at`, `reason_code`, `run_id` | Dùng cho NFR-11, NFR-12 |
| `deletion_log` | `deletion_id` (PK), `participant_id`, `artifact_count`, `executed_by`, `executed_at`, `status` ∈ {COMPLETE, PARTIAL} | Không chứa PII |

Bảng `identity_map` (họ tên, email, mã sinh viên ↔ `participant_id`) **không** nằm trong CSDL này. Nó được lưu ở `identity_root` tách biệt, mã hóa, chỉ người giữ danh tính và GVHD truy cập (theo R7 mục 3 và 4).

## 7.2. Nguồn dữ liệu và license

| Nguồn | Dùng cho | Khối lượng | License / điều kiện | Ghi chú |
| --- | --- | --- | --- | --- |
| Speak & Improve Corpus 2025 | **Huấn luyện và tuning** mô hình chấm | 5.616 file tập dev, có nhãn CEFR 0–6 | Theo điều khoản của nhà phát hành corpus; ghi vào `docs/license_inventory.md` | Đã tải về, chia fold theo speaker |
| Dữ liệu bài nói sinh viên Việt Nam | **Chỉ kiểm định** (validation), không huấn luyện | Mục tiêu 60–90 speaker; tối thiểu 40 | Thu theo phiếu đồng thuận đã duyệt (R8) | Không đưa vào tập huấn luyện trong bất kỳ trường hợp nào |
| faster-whisper `small` | ASR | Model weights ~484 MB | MIT (ctranslate2) / model theo license gốc Whisper | Cache trong Docker image |
| BERT base (English) | Text grader backbone | ~440 MB | Apache 2.0 | Chỉ huấn luyện regression head |
| Fixture audio synthetic | Test tự động | ~30 file | Tự tạo, không chứa giọng người thật | Cho phép commit vào repo |

## 7.3. Lưu trữ

| Loại dữ liệu | Vị trí | Mã hóa | Ai truy cập |
| --- | --- | --- | --- |
| Bảng ánh xạ danh tính, phiếu đồng thuận | `identity_root` (ngoài repo, ngoài workspace mô hình) | Có, at rest | SV3 được ủy quyền + GVHD |
| Audio gốc và audio chuẩn hóa | `research_root/raw_audio/`, `research_root/normalized/` | Có, at rest | Nhóm theo vai trò + giảng viên đánh giá |
| Transcript, feature, score, evidence | CSDL nghiên cứu (SQLite/PostgreSQL) trên volume đã mã hóa | Có, at rest | Nhóm nghiên cứu |
| Model artifact và metric | `artifacts/models/`, `artifacts/reports/` | Không bắt buộc | SV1, SV2 |
| Log vận hành | `logs/` | Không bắt buộc (đã loại PII theo NFR-09) | Admin |

Nguyên tắc bắt buộc: **không commit audio thật, transcript thật, PII hoặc secret vào Git** (C-10, kiểm chứng bằng NFR-08).

## 7.4. Lưu giữ và xóa

| Nội dung | Quy tắc |
| --- | --- |
| Thời hạn lưu | Đề xuất 12 tháng sau ngày bảo vệ; **giá trị chính thức chờ ethics/GVHD duyệt** và phải khớp đúng nội dung ghi trong phiếu đồng thuận |
| Xóa khi rút đồng thuận | Theo FR-35 và UC-07: xem trước → xác nhận hai lần → xóa audio/transcript/feature/report → ghi deletion log không PII |
| Giới hạn phải công bố | Không hứa xóa dữ liệu khỏi mô hình đã huấn luyện và phát hành trước thời điểm rút; thông báo nêu rõ mốc cutoff (AC-35.4) |
| Bất biến dữ liệu thô | Không ghi đè audio gốc hay snapshot dataset; mỗi snapshot có version, checksum, `created_at`, `owner` |
| Sao lưu | Hai bản sao mã hóa ở hai vị trí đã duyệt; khóa khôi phục **không** nằm trong repository |
| Gói và thanh toán (D034, D035) | Bốn bảng `billing_*` giữ giấy phép, đơn hàng, thông điệp của cổng và tên tổ chức — không có dữ liệu của người học, không số thẻ hay tài khoản ngân hàng (BR-32); từ D035 đơn ghi thêm cổng, có tiền thật hay không và mã phiên của cổng (mã Checkout Session của Stripe), không email hay tên người trả mà Stripe giữ. Đơn hàng là chứng từ thanh toán của trường nên **không** theo hạn lưu bản ghi và không bị xoá khi xoá dữ liệu một người học; người đặt đơn ghi bằng mã tài khoản quản trị |
| Khoá ký của máy chủ (D036) | Bảng `server_secret` giữ khoá ngẫu nhiên ký cookie luồng đăng nhập Google — không phải dữ liệu của ai. Giữ suốt đời bản triển khai; xoá bảng chỉ làm các luồng Google đang dở (tối đa mười phút) phải bắt đầu lại. Không có trong bản xuất dữ liệu cá nhân |
| Thành tựu (D032) | Bảng `achievement` chỉ giữ mã thành tựu, ngày đạt và ngày xem — không bản ghi, bản chép hay điểm. Giữ tới khi xoá dữ liệu người học (FR-35), không theo hạn lưu bản ghi: xoá lượt luyện không lấy lại thành tựu (BR-28). Có trong bản xuất dữ liệu cá nhân |

---

# 8. YÊU CẦU GIAO DIỆN

Giao diện là ứng dụng web FastAPI + Jinja2 render phía máy chủ, gồm một trang chủ với điều hướng theo vai trò (C-03). Bảng màu tối thiểu, không hiệu ứng phức tạp; ưu tiên đọc được trên màn hình 1366×768 (NFR-15). Giao diện dùng chung tiến trình với tầng API `/api/v1`, nên mọi màn hình mô tả dưới đây đều gọi đúng các endpoint đã đặc tả ở mục 3 chứ không truy cập cơ sở dữ liệu trực tiếp.

## 8.1. Màn hình S1 — Đăng nhập

Ô nhập tên đăng nhập và mật khẩu, nút "Đăng nhập", thông báo lỗi chung ("Thông tin đăng nhập không đúng" — không tiết lộ tài khoản có tồn tại hay không). Sau 5 lần sai liên tiếp hiển thị thông báo khóa 15 phút (NFR-07).

## 8.2. Màn hình S2 — Nộp bài (vai trò Sinh viên)

- Danh sách đề bài dạng thẻ, mỗi thẻ có nội dung đề và thời lượng khuyến nghị. Có **hai loại đề**, và thời lượng của chúng không chọn tuỳ ý:
  - **Đề ngắn** (P3, P4) — **40–60 giây**. Nằm trọn trong dải mà mô hình chấm điểm được huấn luyện (26,7–60,7 giây), nên bài được chấm nguyên bài trong một lần.
  - **Đề dài** (P5) — **120–300 giây**. Nằm **ngoài** dải huấn luyện và cố ý như thế: bài loại này được chấm bằng cách cắt thành các cửa sổ 30–60 giây, chấm riêng từng cửa sổ rồi lấy trung vị (xem FR-21a). Thẻ đề ghi rõ điều đó trước khi người học bấm ghi âm, và kết quả **luôn** được chuyển cho giảng viên.

  `tests/test_tasks_and_admin.py` kiểm mọi đề bài thoả **một trong hai** đường: hoặc nằm trong dải huấn luyện của tệp mô hình, hoặc đủ dài để việc cắt cửa sổ có nghĩa và không vượt số cửa sổ tối đa lẫn trần QC.
- Vùng kéo-thả file audio, hiển thị giới hạn "≤ 25 MB, 20–300 giây, định dạng wav/mp3/m4a/webm".
- Nút "Ghi âm" đặt cạnh vùng kéo-thả, kèm đồng hồ `mm:ss` và cảnh báo ngưỡng 20–300 giây (FR-39). Nút này chỉ hiện khi máy chủ có `ffmpeg` và trình duyệt hỗ trợ `MediaRecorder`; ngược lại nút bị ẩn hoặc vô hiệu kèm dòng giải thích lý do, còn đường tải file luôn giữ nguyên.
- Thanh tiến trình tải lên và nhãn trạng thái: `Đang tải` → `Đang kiểm tra chất lượng` → `Đang nhận dạng` → `Đang chấm` → `Xong`.
- Khi bị từ chối: hộp cảnh báo màu vàng/đỏ ghi chỉ số đo được, ngưỡng yêu cầu, câu hướng dẫn tiếng Việt và nút "Nộp lại" (FR-09).

## 8.3. Màn hình S3 — Kết quả bài nói (vai trò Sinh viên)

Bố cục ba khối dọc:

1. **Khối tóm tắt:** band ước lượng cỡ lớn (A2/B1/B2) kèm nhãn "Kết quả ước lượng — không phải chứng chỉ CEFR"; thanh độ tin cậy có nhãn Cao/Trung bình/Thấp; nếu bị gắn cờ thì hiện băng thông báo "Chờ giảng viên xác nhận" kèm lý do bằng tiếng Việt.
2. **Khối bằng chứng:** trình phát audio với các dấu mốc trên thanh thời gian (pause dài màu cam, cụm filler màu tím, từ confidence thấp màu xám); bên dưới là danh sách ≤ 6 evidence, mỗi dòng có nhãn loại, mốc `mm:ss`, số đo và nút "Nghe đoạn này" (US-05).
3. **Khối nhận xét và ưu tiên:** ≤ 4 câu nhận xét theo mẫu, mỗi câu có biểu tượng liên kết tới evidence; ≤ 2 ưu tiên cải thiện. Khi độ tin cậy < 50%, khối ưu tiên được thay bằng dòng "Kết quả cần giảng viên xác nhận trước khi đưa gợi ý luyện tập" (AC-26.3).

Tab phụ **"Bản ghi lời"**: transcript đầy đủ, từ có confidence < 0,50 tô nền xám kèm tooltip "Máy có thể nghe nhầm từ này".

Chân trang: khối `provenance` gồm 7 trường version và thời điểm chấm (FR-27).

## 8.3b. Màn hình S3b — Tiến độ của tôi (vai trò Sinh viên)

Kết quả của chính người học xếp theo thời gian (FR-27a).

- Biểu đồ đường trên thang 0–6 **cố định**, không co theo dữ liệu.
- Điểm đã được giảng viên xác nhận và điểm máy ước lượng vẽ khác nhau, có chú giải.
- Một dòng nhận định xu hướng, hoặc câu "chưa đủ dữ liệu" / "chưa kết luận được" kèm lý do bằng số.
- Bảng từng bài kèm liên kết tới báo cáo, nút in / lưu PDF và nút tải hồ sơ năng lực.
- Mục **Thành tựu** (FR-65, bản 1.5): 17 ô trong năm nhóm; ô đã đạt có huy hiệu đặc và ngày đạt, ô chưa đạt có thanh tiến độ và mức đã làm trên mức cần, ô mới đạt mang nhãn "Mới" một lần. Không có điểm, band hay so sánh với người khác.

## 8.4. Màn hình S4 — Hàng đợi duyệt (vai trò Giảng viên)

- Bảng danh sách: cột `Mã bài`, `Đề bài`, `Band AI`, `Độ tin cậy`, `Lý do gắn cờ`, `Ngày nộp`, `Trạng thái khóa`. Mặc định sắp xếp độ tin cậy tăng dần.
- Bộ lọc theo reason code và theo band AI.
- Chỉ báo "Đang được [tên] xem" cho bài đang bị khóa (US-18).

## 8.5. Màn hình S5 — Duyệt một bài (vai trò Giảng viên)

Bố cục hai cột trên cùng một trang, không cần chuyển trang (US-14):

- **Cột trái:** trình phát audio có dấu mốc; transcript cuộn được, đồng bộ highlight theo vị trí đang phát.
- **Cột phải:** band AI + độ tin cậy + lý do gắn cờ; danh sách evidence bấm được để nhảy mốc; khối hành động gồm nút "Đồng ý với kết quả AI", nút "Sửa kết quả" (mở ô chọn band, danh sách mã lý do và ô ghi chú), nút "Bỏ qua".
- Khi sửa mà chưa chọn lý do: thông báo chặn lưu ngay tại chỗ (AC-30.2).

## 8.5b. Màn hình S5b — Thống kê lớp (vai trò Giảng viên)

Bức tranh chung của cả lớp, phục vụ FR-29 ở mức lớp thay vì mức từng bài.

- Bốn ô số: bài đã nộp, bài máy chấm được, số người nộp, bài đang chờ duyệt. Hai con số đầu **tách riêng** vì bài máy không chấm được vẫn là bài đã nộp.
- Khối **"giảng viên và máy có đồng ý với nhau không"**: số lượt duyệt, số lần giữ nguyên band, số lần đổi, tỷ lệ đồng ý. Đây là con số duy nhất trong toàn hệ thống cho biết mô hình đáng tin đến đâu **trên chính lớp này**, và nó chỉ lộ ra khi cộng dồn hàng chục quyết định — không màn hình chấm từng bài nào cho thấy được.
- Phân bố band và bảng theo đề, mỗi bảng kèm một câu nói rõ đọc nó thế nào là sai.
- **Không** có bảng xếp hạng sinh viên và **không** có bảng xếp hạng giảng viên: màn hình xếp hạng người thì sẽ được dùng để xếp hạng người.

## 8.6. Màn hình S6 — Quản trị (vai trò Quản trị viên)

Bốn tab:

1. **Tài khoản:** tạo/khóa tài khoản, gán vai trò.
2. **Cấu hình:** hiển thị `qc_config_version` đang chạy và nội dung ngưỡng (chỉ đọc trong giao diện; sửa qua file YAML).
3. **Mô hình:** danh sách `model_version` kèm metric, nút kích hoạt; chặn kích hoạt khi thiếu file trọng số (AC-36.2).
4. **Yêu cầu dữ liệu:** ô nhập `participant_id`, nút "Xem trước", bảng liệt kê artifact, nút "Xác nhận xóa" kèm bước nhập lại ID để xác nhận lần hai (UC-07).

## 8.7. Giao diện lập trình (API)

REST theo OpenAPI 3.1, tiền tố `/api/v1`. Các endpoint chính đã liệt kê ở mục 3. Mọi phản hồi lỗi dùng chung cấu trúc:

```json
{
  "error": {
    "reason_code": "AUDIO_TOO_SHORT",
    "message": "Bản ghi ngắn hơn 20 giây.",
    "run_id": "9f2c1a4e",
    "http_status": 422
  }
}
```

## 8.8. Giao diện phần cứng và phần mềm ngoài

| Giao diện | Mô tả |
| --- | --- |
| Microphone / file audio | Hệ thống nhận audio theo hai đường: file do người dùng tải lên, và bản ghi do trình duyệt tạo qua `MediaRecorder` (FR-39). Hệ thống **không** điều khiển phần cứng thu trực tiếp — mọi truy cập micro do trình duyệt cấp phép và quản lý; máy chủ chỉ nhận blob đã ghi xong. Khi thiếu `ffmpeg` hoặc thiếu quyền micro, lối ghi âm bị tắt ngay từ khi render trang và chỉ còn đường tải file |
| FFmpeg / ffprobe | Gọi qua subprocess; phiên bản ghi vào `provenance`. Bắt buộc phải có để chuyển mã WebM/Opus và MP4/AAC từ `MediaRecorder` về WAV mono 16 kHz (FR-39); thiếu nó thì chỉ tắt tính năng ghi âm chứ không làm hỏng luồng tải file |
| faster-whisper | Gọi qua thư viện Python trong tiến trình worker; model đọc từ cache cục bộ |
| Google OpenID Connect (D029, D036) | Chỉ khi đặt `AICEFR_GOOGLE_CLIENT_ID` và `AICEFR_GOOGLE_CLIENT_SECRET`. Trình duyệt tới trang của Google; máy chủ gọi điểm cuối token của Google một lần mỗi lần đăng nhập, gửi mã uỷ quyền, verifier PKCE, client id và secret; nhận ID token và chỉ giữ mã băm của `sub` |
| Cổng thanh toán (D034, D035) | Chỉ khi bật thu phí và cấu hình cổng. VNPay: chỉ chuyển trình duyệt và nhận IPN. Stripe: máy chủ gọi API Checkout Sessions (mở, đọc lại) và nhận webhook. MoMo: máy chủ gọi API tạo giao dịch và nhận IPN. Gửi đi mã đơn, số tiền, nội dung không dấu, địa chỉ trả về; không dữ liệu của người học |
| Không có | Hệ thống **không** gọi bất kỳ API bên ngoài nào trong luồng xử lý audio (C-04) |

---


## 8.9. Sơ đồ thiết kế tham chiếu

Toàn bộ sơ đồ thiết kế được đặt ở tài liệu `docs/sdd/SDD.md` và ở tab **"Sơ đồ thiết kế"** của tài liệu này. Bảng dưới liệt kê tám sơ đồ cùng phạm vi yêu cầu mà mỗi sơ đồ minh họa.

| Hình | Sơ đồ | Minh họa cho yêu cầu | File nguồn |
| --- | --- | --- | --- |
| 1a | Use case cho tác nhân Sinh viên — UC-01, UC-02, UC-03, UC-04 | FR-01 … FR-27, FR-39 | `diagrams/01a_usecase_sinhvien.mmd` |
| 1b | Use case cho tác nhân Giảng viên đánh giá — UC-05, UC-06, UC-11 | FR-28 … FR-31, FR-38 | `diagrams/01b_usecase_giangvien.mmd` |
| 1c | Use case cho tác nhân Quản trị viên — UC-07 … UC-10, UC-12 | FR-08, FR-18 … FR-20, FR-32, FR-34 … FR-36 | `diagrams/01c_usecase_quantri.mmd` |
| 2 | Sơ đồ lớp — mô hình miền: 6 thực thể, 10 đối tượng giá trị, 8 kiểu liệt kê, mọi thành viên ghi đủ kiểu | toàn bộ module M1 … M8 | `diagrams/02_class.drawio` |
| 2b | Kiến trúc — cổng và bộ chuyển đổi | M1 … M8 | `diagrams/02b_kien_truc.puml` |
| 3 | Sơ đồ tuần tự luồng nộp bài | FR-01 … FR-27 | `diagrams/03_sequence.mmd` |
| 4 | Sơ đồ hoạt động kèm nhánh lỗi | FR-06 … FR-23 | `diagrams/04_activity.mmd` |
| 5 | Sơ đồ thực thể liên kết — phần chấm điểm và vận hành | mục 7 Yêu cầu dữ liệu | `diagrams/05_erd.mmd` |
| 5c | Sơ đồ thực thể liên kết — định danh và đồng thuận | FR-01, FR-32, FR-35 | `diagrams/05c_erd_identity.mmd` |
| 5b | Sơ đồ thực thể liên kết — lược đồ nghiên cứu dự kiến, chưa hiện thực | mục 7 Yêu cầu dữ liệu | `diagrams/05b_erd_target.mmd` |
| 6 | Sơ đồ thành phần và triển khai | NFR-01 … NFR-18 | `diagrams/06_deployment.mmd` |

Sơ đồ được sinh từ mã nguồn dạng văn bản chứ không vẽ tay, nên khi thiết kế thay đổi thì sơ đồ được cập nhật bằng cách sửa mã và render lại. Cách này bảo đảm sơ đồ luôn khớp với mã nguồn, phục vụ việc đối chiếu ngẫu nhiên khi phản biện.

**Phạm vi của hình 2.** Hình 2 là **mô hình miền**, chỉ vẽ những khái niệm của bài toán chấm nói. Mỗi hộp mang một khuôn dập cho biết nó có danh tính hay không: «entity» được cấp mã định danh, tra cứu được và sửa được qua thời gian (`Account`, `Consent`, `Review`, `Task`, `Response`, `Assessment`, `Evidence`); «value object» so sánh bằng nội dung, bất biến, và khi đổi thì thay cả cục chứ không sửa từng trường (`QcResult`, `Transcript`, `Word`, `FeatureSet`, `CriterionCoverage`, `AnalysisWindow`, `Comment`, `Priority`).

Bốn lớp hạ tầng — `AuthSession` (FR-32), `ReviewLock` (FR-30), `AuditEntry` (FR-31), `AppConfig` (FR-08, FR-36) — **cố ý không nằm ở hình 2**. Chúng tồn tại vì hệ thống chạy trên máy tính, không vì bài toán chấm nói: một phiên đăng nhập hết hạn sau 8 giờ không phải khái niệm mà giảng viên hay sinh viên nói tới. Cả bốn vẫn là yêu cầu bắt buộc, vẫn là lớp thật trong `src/aicefr/contracts.py`, và được vẽ ở đúng tầng thiết kế của chúng: `auth_sessions` ở hình 5c, còn `review_lock`, `audit_log`, `app_config` ở hình 5.

Cổng và bộ chuyển đổi cũng không nằm ở hình 2 mà ở hình 2b, vì chúng trả lời câu hỏi khác: *hệ thống cắm vào thế giới bên ngoài ở đâu*.


# 9. RÀNG BUỘC PHÁP LÝ VÀ ĐẠO ĐỨC

## 9.1. Cơ sở pháp lý áp dụng

Hệ thống xử lý audio giọng nói, transcript, metadata và điểm đánh giá của người học — đều có thể là **dữ liệu cá nhân**. Hai văn bản áp dụng:

- **Luật Bảo vệ dữ liệu cá nhân số 91/2025/QH15**, hiệu lực từ 01/01/2026.
- **Nghị định 356/2025/NĐ-CP** quy định chi tiết thi hành Luật 91/2025/QH15, hiệu lực từ 01/01/2026.

Nghị định 13/2023/NĐ-CP **không còn là căn cứ áp dụng** cho dự án này và không được viện dẫn trong tài liệu hay mã nguồn.

Nội dung mục này là thiết kế tuân thủ ở mức thực hành kỹ thuật, **không thay thế tư vấn pháp lý** hoặc quy trình phê duyệt đạo đức của nhà trường.

## 9.2. Ánh xạ nguyên tắc sang yêu cầu kỹ thuật

| Nguyên tắc | Cách hệ thống đáp ứng | FR/NFR |
| --- | --- | --- |
| Mục đích cụ thể, rõ ràng | `consent_version` bắt buộc trên mọi phiên; điều khoản nêu rõ mục đích đánh giá Speaking A1–C2; không tái dùng cho nhận dạng người nói | FR-01 |
| Tối thiểu hóa dữ liệu | Không thu CCCD, địa chỉ, dữ liệu sức khỏe; DB nghiên cứu không có cột danh tính | FR-33 |
| Tách danh tính | `identity_map` nằm ngoài workspace nghiên cứu; định danh giả danh bị chặn nếu trông giống mã số sinh viên | FR-33, AC-01.3 |
| Bảo mật khi lưu trữ | Mã hóa at rest, phân quyền theo vai trò, băm mật khẩu bcrypt ≥ 12, quét secret ở mỗi PR | FR-32, NFR-07, NFR-08 |
| Hạn chế rò rỉ qua log | Whitelist trường log, test tự động quét email/mã số/transcript | FR-13, FR-37, NFR-09 |
| Quyền truy cập và xuất dữ liệu | Endpoint xuất dữ liệu cá nhân của chính người yêu cầu | FR-34 |
| Quyền rút và xóa | Quy trình xem trước → xác nhận hai lần → xóa → deletion log không PII, hoàn tất trong ≤ 7 ngày làm việc | FR-35, NFR-10, UC-07 |
| Giới hạn chuyển dữ liệu | Xử lý local-first tuyệt đối; không endpoint nào gửi audio/transcript ra ngoài | C-04, mục 8.8 |
| Minh bạch với người dùng | Mọi báo cáo hiển thị "ước lượng", version mô hình và nhãn chờ xác nhận | FR-27, AC-21.3 |
| Ứng phó sự cố | Quy trình 6 bước theo kế hoạch quản lý dữ liệu: ngừng truy cập → ghi nhận → báo GVHD → thu hồi quyền → đánh giá nghĩa vụ thông báo → ghi hành động khắc phục | R7 mục 8 |

## 9.3. Đạo đức đánh giá

| Nguyên tắc | Ràng buộc hệ thống |
| --- | --- |
| **Con người quyết định cuối cùng** | `teacher_verified` mặc định `false` và chỉ chuyển `true` sau hành động duyệt thực tế có audit record. Không quy tắc nào tự bật cờ này. Kết quả AI chưa duyệt luôn hiển thị nhãn trạng thái tương ứng. |
| **Không cấp chứng chỉ** | Không tồn tại chức năng, endpoint hay nút bấm nào sinh chứng chỉ. Mọi band mang `band_status = "estimated"`. Giao diện hiển thị câu "Không phải chứng chỉ CEFR" trên mọi báo cáo. |
| **Không quyết định học vụ tự động** | Không có chức năng pass/fail, xếp lớp hay tính điểm môn học. Hồ sơ xuất ra chỉ gồm kết quả đã được giảng viên duyệt. |
| **Không phạt accent** | Hệ thống không có đặc trưng nào đo "độ giống người bản ngữ"; các đặc trưng phát âm nằm ngoài phạm vi bản này. |
| **Không suy diễn thuộc tính nhạy cảm** | Không có mô hình, đặc trưng hay trường dữ liệu nào liên quan tới giới tính, dân tộc, cảm xúc, tính cách, sức khỏe hay hoàn cảnh kinh tế. |
| **Không suy diễn Interaction từ độc thoại** | Tiêu chí Interaction luôn `null` + `insufficient_evidence` (FR-23), có unit test chứng minh nó không tham gia tính điểm tổng. |
| **Công bố giới hạn** | Báo cáo nghiên cứu phải nêu WER, tỷ lệ lỗi nghiêm trọng, khoảng tin cậy và quần thể đã kiểm chứng. Không viết claim rộng hơn dữ liệu. |
| **Không công bố ô nhỏ** | Phân tích theo nhóm nhỏ chỉ mang tính thăm dò; không công bố bảng có ô dưới 5 người. |
| **Tính tự nguyện** | Việc tham gia không gắn với điểm môn học; người từ chối hoặc rút không chịu bất lợi. |

## 9.4. Tuyên bố phải hiển thị trong sản phẩm

Chuỗi văn bản sau được hardcode trong giao diện báo cáo và trong `speaking_profile.json`:

> "Kết quả này là ước lượng do hệ thống hỗ trợ tạo ra nhằm phục vụ đánh giá quá trình. Đây **không** phải chứng chỉ CEFR và **không** được dùng làm căn cứ duy nhất cho bất kỳ quyết định học vụ nào. Giảng viên là người quyết định cuối cùng."

---

# 10. MA TRẬN TRUY VẾT YÊU CẦU

Ma trận liên kết FR ↔ use case ↔ test case ↔ module code. Đây là bảng hội đồng dùng để đối chiếu tài liệu với mã nguồn.

Cột "Module code" ghi **đường dẫn có thật trong repository** tại thời điểm cập nhật tài liệu. Yêu cầu nào chưa có mã tương ứng thì ghi thẳng **"chưa hiện thực"** kèm lý do, không trỏ vào tên file chưa tồn tại.

| FR | Use case | Test case | Module code (đường dẫn thật trong repo) |
| --- | --- | --- | --- |
| FR-01 Tạo phiên | UC-01 | TC-01 `test_create_session_ok`, TC-02 `test_create_session_missing_version`, TC-03 `test_reject_pii_like_id` | `src/aicefr/api/main.py` (`nop_bai`), `src/aicefr/contracts.py` (`ProcessingRequest`) |
| FR-02 Upload audio | UC-01, UC-02 | TC-04 `test_upload_accepts_wav`, TC-05 `test_upload_rejects_unsupported`, TC-06 `test_upload_rejects_oversize` | `src/aicefr/api/main.py` (`nop_bai`, `MAX_BYTES`), `src/aicefr/api/schemas.py` |
| FR-03 Chuẩn hóa audio | UC-01, UC-03 | TC-07 `test_normalize_to_mono_16k`, TC-08 `test_raw_audio_immutable`, TC-09 `test_tmp_cleanup` | `src/aicefr/api/main.py` (đọc file, trộn về mono); phần đổi tần số mẫu về 16 kHz và chuyển mã bằng `ffmpeg` — **chưa hiện thực** |
| FR-04 Danh sách bài | UC-01 | TC-10 `test_list_own_responses`, TC-11 `test_cross_user_returns_404` | `src/aicefr/api/main.py` (`danh_sach`), `src/aicefr/storage/repository.py` (`list_all`) |
| FR-05 Kích hoạt chấm | UC-01, UC-03 | TC-12 `test_enqueue_returns_job_id`, TC-13 `test_duplicate_enqueue_is_idempotent` | `src/aicefr/pipeline.py` (`process`) gọi **đồng bộ** trong `src/aicefr/api/main.py`; hàng đợi nền và endpoint `GET /jobs/{job_id}` — **chưa hiện thực** |
| FR-06 Đo chỉ số QC | UC-01, UC-03 | TC-14 `test_qc_metrics_complete`, TC-15 `test_clipping_ratio_fixture`, TC-16 `test_qc_deterministic` | `src/aicefr/qc/audio_qc.py` (`silence_ratio`, `clipping_ratio`, `estimate_snr_db`) |
| FR-07 Ngưỡng QC | UC-02, UC-03 | TC-17 `test_reject_too_short`, TC-18 `test_review_high_silence`, TC-19 `test_multiple_reason_codes`, TC-20 `test_reject_has_no_band` | `src/aicefr/qc/audio_qc.py` (`QcThresholds`, `check`), `src/aicefr/contracts.py` (`QcStatus`, `ReasonCode`) |
| FR-08 Cấu hình QC | UC-08 | TC-21 `test_qc_config_version_recorded`, TC-22 `test_missing_version_aborts_startup` | `src/aicefr/qc/audio_qc.py` (`QcThresholds`, hằng số ngưỡng); file `config/qc_config.yaml` và nạp cấu hình có version — **chưa hiện thực** |
| FR-09 Chẩn đoán QC | UC-02 | TC-23 `test_reject_message_in_vietnamese`, TC-24 `test_no_band_on_reject_ui` | `src/aicefr/api/web.py` (`TRANG_KET_QUA`), `src/aicefr/api/main.py` (`nop_bai` sinh thông báo tiếng Việt) |
| FR-10 ASR timestamps | UC-03 | TC-25 `test_word_timestamps_present`, TC-26 `test_timestamps_monotonic`, TC-27 `test_asr_metadata_complete` | `src/aicefr/asr/whisper_adapter.py`, `src/aicefr/asr/base.py`, `src/aicefr/contracts.py` (`Word`, `Transcript`) |
| FR-11 Verbatim filler | UC-03 | TC-28 `test_filler_recall_fixture`, TC-29 `test_clean_transcript_removes_filler`, TC-30 `test_feature_source_mapping` | `src/aicefr/asr/whisper_adapter.py`, `src/aicefr/contracts.py` (`Transcript.is_verbatim`), `src/aicefr/features/extract.py` (đếm filler) |
| FR-12 Lỗi ASR | UC-03 | TC-31 `test_asr_exception_marks_failed`, TC-32 `test_empty_transcript_review`, TC-33 `test_asr_timeout` | `src/aicefr/asr/base.py` (`AsrError`), `src/aicefr/pipeline.py` (nhánh `ASR_FAILED`, `ASR_EMPTY_TRANSCRIPT`) |
| FR-13 Log không transcript | UC-03 | TC-34 `test_log_has_no_transcript_ngram` | **chưa hiện thực** (dự án chưa có module logging riêng) |
| FR-14 Đặc trưng fluency | UC-03 | TC-35 `test_speech_rate_value`, TC-36 `test_pause_threshold_filter`, TC-37 `test_run_length_null_on_single_token` | `src/aicefr/features/extract.py` (`vad_features`) |
| FR-15 Đặc trưng từ vựng | UC-03 | TC-38 `test_ttr_value`, TC-39 `test_mtld_null_short_text`, TC-40 `test_empty_transcript_all_null` | `src/aicefr/features/extract.py` (`text_features`, `MIN_WORDS`) |
| FR-16 Chất lượng transcript | UC-03 | TC-41 `test_low_conf_ratio`, TC-42 `test_low_conf_triggers_flag`, TC-43 `test_low_conf_list_capped_at_20` | `src/aicefr/features/extract.py` (`extract`), `src/aicefr/report/evidence.py` (từ confidence thấp) |
| FR-17 Vector có version | UC-03 | TC-44 `test_feature_vector_schema`, TC-45 `test_imputation_recorded`, TC-46 `test_too_many_missing_features` | `src/aicefr/features/extract.py` (`extract`), `src/aicefr/contracts.py` (`FeatureSet.feature_version`, `invalid`) |
| FR-18 Ridge scorer | UC-03, UC-12 | TC-47 `test_ridge_output_range`, TC-48 `test_ridge_deterministic`, TC-49 `test_model_artifact_exists` | `src/aicefr/scoring/scorer.py` (`load_model`, `predict_overall`); script huấn luyện Ridge — **chưa hiện thực** |
| FR-19 BERT grader | UC-03, UC-12 | TC-50 `test_text_grader_range`, TC-51 `test_truncation_flag`, TC-52 `test_backbone_frozen` | **chưa hiện thực** (chưa có mô hình chấm trên văn bản) |
| FR-20 Late fusion | UC-03 | TC-53 `test_fusion_arithmetic`, TC-54 `test_feature_only_mode`, TC-55 `test_missing_fusion_config_aborts` | **chưa hiện thực** (chưa có late fusion; hiện chỉ chấm trên đặc trưng) |
| FR-21 Quy band | UC-03 | TC-56 `test_band_mapping_b1`, TC-57 `test_boundary_distance`, TC-58 `test_band_status_is_estimated` | `src/aicefr/scoring/scorer.py` (`to_band`), `src/aicefr/contracts.py` (`Band`) |
| FR-22 Độ tin cậy | UC-03 | TC-59 `test_low_confidence_near_boundary`, TC-60 `test_high_confidence_clean_case`, TC-61 `test_calibration_version_present` | `src/aicefr/scoring/scorer.py` (`near_boundary`, `out_of_distribution`), `src/aicefr/contracts.py` (`CriterionCoverage.confidence`) |
| FR-23 Không chấm Interaction | UC-03 | TC-62 `test_interaction_always_null`, TC-63 `test_interaction_excluded_from_overall` | `src/aicefr/contracts.py` (`Criterion` — 5 giá trị, không có `interaction`) |
| FR-24 Sinh evidence | UC-01, UC-05 | TC-64 `test_long_pause_evidence`, TC-65 `test_evidence_refs_resolve`, TC-66 `test_no_evidence_from_null_feature`, TC-67 `test_evidence_count_cap` | `src/aicefr/report/evidence.py` (`build`), `src/aicefr/contracts.py` (`Evidence`) |
| FR-25 Nhận xét theo mẫu | UC-01 | TC-68 `test_every_comment_has_evidence`, TC-69 `test_no_evidence_no_comment`, TC-70 `test_comment_deterministic` | **chưa hiện thực** (chưa có bộ mẫu câu nhận xét) |
| FR-26 Ưu tiên cải thiện | UC-01 | TC-71 `test_priority_from_deviation`, TC-72 `test_priority_cap_two`, TC-73 `test_no_priority_low_confidence` | **chưa hiện thực** (chưa có bộ chọn ưu tiên cải thiện) |
| FR-27 Hiển thị version | UC-01, UC-11 | TC-74 `test_provenance_complete`, TC-75 `test_report_schema_valid` | `src/aicefr/contracts.py` (`Response.config_version`, `Transcript.model_version`, `Assessment.model_version`), `src/aicefr/api/web.py`; schema `schemas/report_v1.json` — **chưa hiện thực** |
| FR-28 Quy tắc cờ | UC-03, UC-05 | TC-76 `test_flag_low_confidence`, TC-77 `test_multiple_flag_reasons_unique`, TC-78 `test_no_flag_clean_case`, TC-79 `test_flag_yield_script` | `src/aicefr/review/router.py` (`route`, `ReviewDecision.needs_teacher`) |
| FR-29 Hàng đợi review | UC-05 | TC-80 `test_queue_sorted_by_confidence`, TC-81 `test_queue_filter_reason`, TC-82 `test_response_lock` | `src/aicefr/api/main.py` (`hang_doi`), `src/aicefr/storage/repository.py` (`queue_with_locks`), `src/aicefr/api/web.py` (`TRANG_DUYET`); cơ chế khóa bài đang xem — **chưa hiện thực** |
| FR-30 Duyệt/sửa | UC-05, UC-06 | TC-83 `test_approve_sets_verified`, TC-84 `test_override_requires_reason`, TC-85 `test_show_ai_and_final_band`, TC-86 `test_rescoring_preserves_final_band` | `src/aicefr/api/main.py` (`duyet_bai`), `src/aicefr/storage/repository.py` (`apply_review`), `src/aicefr/api/schemas.py` (`ReviewDecision`) |
| FR-31 Audit trail | UC-05, UC-06 | TC-87 `test_audit_records_before_after`, TC-88 `test_audit_is_append_only` | `src/aicefr/storage/repository.py` (`apply_review` ghi nhật ký, `audit`), `src/aicefr/api/main.py` (`nhat_ky`) |
| FR-32 Xác thực/phân quyền | UC-10 | TC-89 `test_student_forbidden_on_queue`, TC-90 `test_password_hash_format`, TC-91 `test_session_cookie_expiry` | **chưa hiện thực** (chưa có đăng nhập, phiên và phân quyền theo vai trò) |
| FR-33 Tách danh tính | UC-07 | TC-92 `test_no_identity_columns`, TC-93 `test_identity_separation` | `src/aicefr/api/schemas.py` (`validate_pseudonym`), `src/aicefr/storage/repository.py` (lược đồ chỉ lưu `speaker_id`) |
| FR-34 Xuất dữ liệu cá nhân | UC-07 | TC-94 `test_export_contains_own_data_only` | **chưa hiện thực** (chưa có chức năng xuất dữ liệu cá nhân) |
| FR-35 Xóa khi rút | UC-07 | TC-95 `test_withdraw_dry_run`, TC-96 `test_withdraw_removes_artifacts`, TC-97 `test_deletion_log_no_pii`, TC-98 `test_withdrawal_performance` | **chưa hiện thực** (chưa có quy trình xóa khi rút đồng thuận) |
| FR-36 Quản lý model version | UC-09 | TC-99 `test_activate_version_isolated`, TC-100 `test_activate_missing_weights_rejected` | `src/aicefr/scoring/scorer.py` (`DEFAULT_MODEL`, `load_model`, `ModelNotFoundError`), `src/aicefr/api/main.py` (`suc_khoe` báo phiên bản mô hình); màn hình kích hoạt version — **chưa hiện thực** |
| FR-37 Kiểm soát log | UC-03 | TC-101 `test_log_key_whitelist`, TC-102 `test_log_privacy_scan` | **chưa hiện thực** (chưa có structured logging và whitelist trường) |
| FR-38 Xuất hồ sơ | UC-11 | TC-103 `test_profile_only_verified`, TC-104 `test_profile_schema_valid`, TC-105 `test_empty_profile_no_guess` | **chưa hiện thực** (chưa có chức năng xuất hồ sơ năng lực nói) |
| FR-39 Ghi âm trực tiếp | UC-01 | TC-106 `test_recording_hidden_without_ffmpeg`, TC-107 `test_webm_transcoded_to_wav_16k`, TC-108 `test_transcode_failure_returns_422`, TC-109 `test_mic_recording_goes_through_qc` | **chưa hiện thực** (chưa có nút ghi âm ở tầng giao diện và chưa có bước chuyển mã `ffmpeg` ở tầng máy chủ) |
| FR-40 Ngân hàng nhiệm vụ luyện | UC-18 | `test_bank_has_one_task_per_criterion_and_band`, `test_practice_tasks_never_appear_in_the_assessment_task_list` | `src/aicefr/practice/bank.py`, `src/aicefr/storage/task_repository.py` (`seed_practice`) |
| FR-41 Đo mục tiêu luyện | UC-18 | `tests/test_practice_unit.py` (bộ đo), `tests/test_practice_integration.py` (pipeline) | `src/aicefr/practice/missions.py`, `src/aicefr/pipeline.py` (`_practice`) |
| FR-42 Gợi ý nhiệm vụ | UC-18 | `test_suggestion_follows_the_weakest_criterion_of_the_latest_assessment`, `test_speaking_profile_carries_the_practice_task_for_the_weakest_criterion` | `src/aicefr/practice/recommend.py`, `src/aicefr/storage/repository.py` (`latest_assessment`, `_profile_row`) |
| FR-43 Phản hồi và thói quen | UC-18 | `test_second_attempt_compares_with_the_previous_one_on_the_same_task`, các test chuỗi ngày | `src/aicefr/practice/feedback.py`, `src/aicefr/practice/streak.py`, `src/aicefr/api/static/practice_*.js` |
| FR-44 Tách bài luyện | UC-18 | `tests/test_practice_integration.py`, `tests/e2e/test_practice_e2e.py` | `src/aicefr/storage/repository.py` (cột `purpose`, `practice_summary`), `src/aicefr/api/main.py` |
| FR-45 Lộ trình, bài học, phiên bản | UC-19, UC-20 | `test_students_see_the_published_version_until_republished`, `test_attempt_records_lesson_version_and_rules_version`, `test_fresh_install_seeds_the_sample_path`, `test_lesson_completes_only_with_enough_passed_steps_and_the_free_step` | `src/aicefr/lessons/model.py`, `src/aicefr/lessons/progress.py`, `src/aicefr/lessons/seed.py`, `src/aicefr/storage/lesson_repository.py` |
| FR-46 Chín dạng bước, bộ đo bằng luật | UC-19 | `test_read_aloud_marks_each_reference_word_heard_missed_or_unsure`, `test_keyword_counts_any_form_of_the_word`, `test_gap_classifies_each_blank`, `test_words_outside_speech_are_not_counted`, `test_free_step_compares_rounds`, `test_practice_clip_qc_accepts_short_recordings_assessment_does_not` | `src/aicefr/lessons/checks.py`, `src/aicefr/lessons/align.py`, `src/aicefr/lessons/text.py`, `src/aicefr/lessons/runner.py` |
| FR-47 Giáo viên soạn bài | UC-20 | `test_generator_builds_the_four_stage_ladder_from_one_text`, `test_linter_warns_about_asr_traps`, `test_students_cannot_edit_paths`, `test_model_audio_that_does_not_match_its_text_is_flagged`, `test_path_export_import_roundtrip` | `src/aicefr/lessons/generate.py`, `src/aicefr/lessons/lint.py`, `src/aicefr/api/lessons_api.py`, `src/aicefr/api/static/teach_*.js` |
| FR-48 Ôn tập giãn cách | UC-19 | `test_missed_words_are_scheduled_for_tomorrow`, `test_review_boxes_follow_leitner_intervals` | `src/aicefr/lessons/review.py`, `src/aicefr/api/lessons_api.py` (`_schedule_reviews`, `_review_steps`) |
| FR-49 Theo dõi và sửa nhận định | UC-20 | `test_teacher_override_updates_the_result_and_is_audited`, `test_lesson_attempts_stay_out_of_queue_and_research_export` | `src/aicefr/api/lessons_api.py` (`teach_insights`, `teach_override`), `src/aicefr/storage/lesson_repository.py` (`apply_override`) |
| FR-50 Tiến độ ngày, bài nên học | UC-19 | `test_daily_goal_counts_seconds_spoken`, `test_next_lesson_follows_the_weakest_criterion` | `src/aicefr/lessons/progress.py` (`today_summary`, `next_lesson`) |
| FR-51 Đổi mật khẩu, quản lý phiên | UC-17 | `test_password_change_needs_the_current_password_and_ends_other_sessions`, `test_a_wrong_current_password_is_refused_and_counts_towards_the_lockout`, `test_the_password_policy_says_what_is_wrong`, `test_signing_out_other_devices_keeps_this_one`, `test_the_account_page_needs_a_login_and_shows_the_pseudonym` | `src/aicefr/api/accounts_api.py`, `src/aicefr/storage/auth_repository.py` (`change_password`, `revoke_sessions`), `src/aicefr/auth/passwords.py` (`check_new_password`) |
| FR-52 Quản lý tài khoản trên web | UC-10 | `test_a_series_continues_the_numbering_with_one_time_passwords`, `test_a_temporary_password_opens_nothing_but_the_password_change`, `test_a_reset_ends_the_sessions_and_issues_a_new_one_time_password`, `test_a_disabled_account_is_signed_out_and_cannot_sign_in`, `test_creating_accounts_is_all_or_nothing_and_checks_names`, `test_only_an_administrator_manages_accounts`, `test_an_administrator_lifts_a_lockout` | `src/aicefr/api/accounts_api.py`, `src/aicefr/storage/auth_repository.py` (`create_with_temporary_passwords`, `set_temporary_password`, `set_disabled`), `src/aicefr/api/deps.py` (`PASSWORD_CHANGE_PATHS`), `src/aicefr/api/static/admin.js` |
| FR-53 Đếm việc đang chờ | UC-04, UC-05 | `test_a_teacher_decision_is_new_until_the_student_opens_their_list`, `test_a_teacher_sees_how_many_responses_wait_for_review`, `test_the_sidebar_carries_a_slot_for_each_count` | `src/aicefr/api/accounts_api.py` (`my_badges`), `src/aicefr/storage/repository.py` (`seen_marker`, `count_reviewed_since`), `src/aicefr/api/static/common.js` |
| FR-54 Trang giải thích band | UC-04 | `test_the_band_page_labels_what_the_machine_does_not_measure`, `test_the_report_links_its_band_to_the_band_page` | `src/aicefr/report/bands.py`, `src/aicefr/api/templates/bands.html` |
| FR-55 Chuẩn bị trước khi nói | UC-01 | `test_the_submit_page_offers_thirty_seconds_of_preparation`, `test_thirty_seconds_of_preparation_then_the_answer_is_recorded` | `src/aicefr/api/static/submit.js`, `src/aicefr/api/static/recorder.js` (`startNow`) |
| FR-56 Hồ sơ cá nhân | UC-17 | `test_a_profile_takes_only_listed_avatars_and_goals`, `test_the_daily_goal_sets_the_target_on_the_path_page`, `test_the_sidebar_draws_the_chosen_avatar`, `test_the_account_page_has_four_parts_for_a_student_and_three_for_staff` | `src/aicefr/storage/auth_repository.py` (`update_profile`, `AVATAR_ICONS`, `DAILY_GOALS`), `src/aicefr/api/accounts_api.py` (`change_my_profile`), `src/aicefr/api/static/account.js` |
| FR-57 Phiên đăng nhập | UC-17 | `test_a_person_sees_their_sessions_and_ends_one`, `test_sessions_of_one_account_cannot_be_ended_by_another` | `src/aicefr/storage/auth_repository.py` (`sessions`, `revoke_session`), `src/aicefr/auth/sessions.py` (`device_label`) |
| FR-58 Lịch sử hoạt động | UC-17 | `test_the_history_shows_sign_ins_failed_attempts_and_changes`, `test_what_an_administrator_did_shows_as_an_administrator`, `test_an_unknown_pseudonym_leaves_nothing_in_the_audit_log` | `src/aicefr/storage/repository.py` (`account_activity`), `src/aicefr/api/main.py` (`login`), `src/aicefr/api/accounts_api.py` (`my_activity`) |
| FR-59 Đăng nhập Google | UC-17 | `test_google_is_off_until_configured`, `test_start_sends_the_browser_to_google_with_state_nonce_and_pkce`, `test_linking_then_signing_in_with_google`, `test_with_sign_up_off_an_unlinked_google_account_cannot_sign_in_or_create_one`, `test_an_unlinked_google_account_signs_up_as_a_student`, `test_a_forged_or_stale_round_trip_is_refused`, `test_one_google_account_links_to_one_pseudonym`, `test_the_domain_restriction_requires_a_verified_school_account`, `test_a_disabled_account_cannot_sign_in_with_google`, `test_unlinking_google_by_the_person_or_an_administrator` | `src/aicefr/auth/google.py`, `src/aicefr/api/google_api.py`, `src/aicefr/storage/auth_repository.py` (`account_identity`, `login_with_identity`) |
| FR-60 Quản trị tài khoản đầy đủ | UC-10 | `test_an_administrator_changes_a_role_but_not_their_own`, `test_an_administrator_signs_an_account_out_everywhere`, `test_the_account_detail_shows_sessions_link_and_history` | `src/aicefr/api/accounts_api.py` (`account_detail`, `change_role`, `revoke_account_sessions`, `unlink_account_google`), `src/aicefr/api/static/admin.js` |
| FR-61 Đợt chấm mù | UC-22 | `test_a_batch_gives_every_eligible_response_two_raters_each_in_their_own_order`, `test_a_batch_needs_two_raters_and_something_to_rate`, `test_a_teacher_who_opened_the_machine_result_is_not_drawn_to_rate_that_response` | `src/aicefr/research/assign.py`, `src/aicefr/storage/rating_repository.py` (`eligible`, `create_batch`, `seen_by`), `src/aicefr/api/rating_api.py` (`create_batch`) |
| FR-62 Phiếu chấm mù | UC-21 | `test_the_rating_sheet_carries_no_pseudonym_response_id_or_machine_score`, `test_a_rater_cannot_open_another_raters_sheet`, `test_the_machine_result_stays_closed_to_a_rater_until_they_have_rated`, `test_a_rating_follows_the_rating_sheet_rules`, `test_an_unscorable_recording_is_rated_as_such`, `test_open_sheets_are_counted_in_the_sidebar_and_a_closed_batch_takes_no_more`, `test_a_sheet_goes_void_once_its_rater_has_seen_the_machine_result`, `test_an_administrator_who_rates_stays_blind_on_the_administration_screens`, `test_the_waiting_count_leaves_out_what_the_teacher_rates_blind`, `test_a_void_sheet_can_be_handed_to_another_rater` | `src/aicefr/api/rating_api.py` (`_sheet`, `submit_sheet`, `_not_while_owed`, `replace_void_sheets`), `src/aicefr/api/main.py` (`_blind`, `_saw`), `src/aicefr/storage/rating_repository.py` (`machine_seen`), `src/aicefr/api/static/rate_*.js` |
| FR-63 Phân xử | UC-21, UC-22 | `test_a_disagreement_goes_to_a_third_rater_who_did_not_rate_it`, `test_an_adjudicator_who_opened_the_machine_result_is_passed_over` | `src/aicefr/research/agreement.py` (`needs_adjudication`), `src/aicefr/storage/rating_repository.py` (`add_adjudication`) |
| FR-64 Báo cáo đồng thuận, bản xuất | UC-22 | `test_the_report_puts_humans_first_and_compares_the_machine_before_any_review`, `test_the_export_lists_every_rating_with_rater_pseudonyms_and_the_machine_score`, `test_erasing_a_participant_erases_what_raters_said_about_them`, `test_the_command_line_report_gives_the_numbers_of_the_screen`, `test_only_an_administrator_runs_batches` | `src/aicefr/research/agreement.py`, `src/aicefr/api/rating_api.py` (`batch_report`, `batch_export`), `tools/agreement_report.py` |
| FR-65 Thành tựu ghi công sức | UC-15, UC-19 | `test_a_first_recording_is_congratulated_once`, `test_the_list_shows_how_far_each_one_is_without_a_score`, `test_new_achievements_are_marked_seen_by_their_owner_only`, `test_an_achievement_is_never_taken_back`, `test_habit_achievements_count_vietnam_days_and_the_learners_goal`, `test_completing_a_lesson_and_a_unit_reach_the_path_achievements`, `test_review_attempts_count_towards_the_review_achievement`, `test_assessments_with_a_result_count_towards_the_assessment_achievements`, `test_the_personal_export_and_erasure_cover_achievements`, `test_a_first_recording_is_congratulated_then_listed_as_new_once` | `src/aicefr/practice/achievements.py`, `src/aicefr/storage/lesson_repository.py` (`achievement`, `unlock`, `mark_seen`), `src/aicefr/api/lessons_api.py` (`_award`, `my_achievements`, `achievements_seen`), `src/aicefr/api/static/my_progress.js`, `src/aicefr/api/static/practice_path.js` (`achievementsCard`), `src/aicefr/api/static/lesson.js` (`celebrate`) |
| FR-66 Kỷ lục, ngày nghỉ được tính, so với tuần trước | UC-19 | `test_the_practice_page_shows_the_record_rest_days_and_last_week`, `test_the_week_shows_the_record_and_the_rest_day`, `test_the_longest_streak_is_the_best_the_learner_was_ever_shown`, `test_the_rest_days_of_the_current_streak_are_named` | `src/aicefr/practice/streak.py` (`longest_streak`, `rest_days`), `src/aicefr/lessons/progress.py` (`today_summary`), `src/aicefr/api/static/practice_path.js` (`todayCard`) |
| FR-67 Thang gói | UC-23 | `test_with_billing_off_nothing_changes`, `test_the_first_look_starts_one_trial_with_everything`, `test_after_the_trial_the_free_plan_closes_staff_tools_but_never_learning`, `test_a_paid_plan_keeps_its_tools_through_grace_then_falls_back_to_free`, `test_each_plan_opens_its_staff_tools`, `test_each_step_up_adds_something_and_none_locks_learning` | `src/aicefr/billing/plans.py`, `src/aicefr/billing/service.py` (`standing`, `require`, `features`, `overview`), `src/aicefr/api/billing_api.py`, `src/aicefr/api/lessons_api.py` (`AUTHORING`, `_plan_allows`), `src/aicefr/api/rating_api.py` (`create_batch`), `src/aicefr/api/static/admin_billing.js` |
| FR-68 Số sinh viên, bài đánh giá dự kiến | UC-23 | `test_the_plan_limits_new_student_accounts_only`, `test_assessments_over_the_monthly_figure_only_warn` | `src/aicefr/billing/service.py` (`check_new_students`, `usage`), `src/aicefr/api/accounts_api.py` (`_seats`) |
| FR-69 Mua qua cổng thanh toán | UC-23 | `test_buying_through_the_sandbox_installs_the_plan_once`, `test_a_school_year_is_discounted_and_shown_on_the_receipt`, `test_a_failed_or_cancelled_payment_changes_nothing`, `test_a_forged_or_altered_result_is_refused`, `test_an_upgrade_is_credited_and_a_renewal_waits`, `test_an_upgrade_the_credit_covers_needs_no_payment`, `test_pending_orders_expire_and_a_late_payment_still_counts`, `test_a_new_order_retires_the_one_still_waiting`, `test_vnpay_is_redirected_to_and_its_messages_are_checked`, `test_an_administrator_buys_a_plan_and_gets_a_receipt`, `test_a_cancelled_payment_leaves_the_plan_as_it_was` | `src/aicefr/billing/gateways.py` (`SandboxGateway`, `VnpayGateway`), `src/aicefr/ports.py` (`PaymentGateway`), `src/aicefr/billing/service.py` (`quote`, `place_order`, `settle`), `src/aicefr/storage/billing_repository.py`, `src/aicefr/api/templates/billing_*.html` |
| FR-70 Mã giấy phép, quyền, nhật ký | UC-23 | `test_a_licence_key_is_installed_once`, `test_without_a_licence_secret_keys_are_refused`, `test_only_an_administrator_deals_with_plans`, `test_plan_actions_are_audited`, `test_the_tab_fits_a_phone_and_students_see_no_plan` | `src/aicefr/billing/keys.py`, `src/aicefr/billing/service.py` (`install_key`), `src/aicefr/api/billing_api.py` |
| FR-71 Chọn cổng cho từng đơn | UC-23 | `test_the_administrator_picks_the_gateway_and_sees_what_is_off`, `test_the_registry_builds_what_the_settings_ask_for`, `test_real_money_needs_to_be_switched_on`, `test_real_money_is_never_a_default`, `test_one_gateway_cannot_settle_another_gateways_order`, `test_the_administrator_sees_each_gateway_and_pays_through_the_one_picked`, `test_the_gateway_choice_fits_a_phone` | `src/aicefr/billing/registry.py`, `src/aicefr/billing/service.py` (`place_order`, `settle`), `src/aicefr/api/billing_api.py`, `src/aicefr/api/static/admin_billing.js` |
| FR-72 Stripe Checkout | UC-23 | `test_stripe_opens_a_checkout_session_in_dong_for_the_order`, `test_stripe_refusals_read_as_sentences`, `test_stripe_return_is_read_back_from_stripe`, `test_stripe_events_count_only_when_signed_and_fresh`, `test_stripe_keys_decide_the_mode`, `test_paying_through_stripe_is_read_back_and_counted_once`, `test_the_stripe_webhook_alone_installs_the_plan`, `test_leaving_stripe_changes_nothing_until_the_session_expires`, `test_a_gateway_that_will_not_open_fails_the_order_with_a_reason`, `test_a_return_stripe_cannot_confirm_says_so`, `test_stripe_is_asked_only_about_checkouts_this_system_opened`, `test_coming_back_without_paying_says_nothing_was_charged` | `src/aicefr/billing/stripe_gateway.py`, `src/aicefr/billing/transport.py`, `src/aicefr/api/billing_api.py` (`billing_notify`, `billing_return`), `src/aicefr/api/templates/billing_result.html` |
| FR-73 Ví MoMo | UC-23 | `test_momo_signs_the_create_request_as_documented`, `test_momo_results_map_to_outcomes_and_forgeries_are_refused`, `test_momo_is_paid_through_its_ipn_answered_204` | `src/aicefr/billing/momo_gateway.py` |
| FR-74 Luồng Google có chữ ký, khung cấu hình | UC-17 | `test_the_flow_cookie_is_signed_and_any_change_breaks_it`, `test_the_pkce_challenge_is_s256_as_rfc_7636_shows`, `test_a_flow_cookie_this_server_did_not_sign_is_ignored`, `test_behind_tls_the_flow_cookie_is_a_host_cookie`, `test_the_signing_key_is_made_once_and_kept`, `test_the_administrator_sees_what_to_register_with_google`, `test_the_config_tab_shows_what_to_register_with_google`, `test_the_google_button_leaves_with_a_pkce_challenge` | `src/aicefr/auth/google.py` (`encode_flow`, `decode_flow`, `cookie_name`), `src/aicefr/api/google_api.py` (`_cookie`, `google_status`), `src/aicefr/storage/auth_repository.py` (`secret`, `count_identities`), `src/aicefr/api/static/admin.js` (`loadGoogleSetup`) |

**Truy vết NFR:**

| NFR | Kiểm chứng bởi | Vị trí |
| --- | --- | --- |
| NFR-01, NFR-03, NFR-18 | Benchmark script | `benchmarks/bench_pipeline.py`, `scripts/measure_storage.py` |
| NFR-02 | Test tải locust | `tests/perf/locustfile.py`, `tests/test_perf_api.py` |
| NFR-04, NFR-05, NFR-06 | Script đánh giá mô hình | `scripts/evaluate_model.py`, `scripts/measure_wer.py`, `scripts/evaluate_flags.py` |
| NFR-07, NFR-08 | Test bảo mật + CI | `tests/test_auth_security.py`, `.github/workflows/security.yml` |
| NFR-09 | Test riêng tư | `tests/test_log_privacy.py` |
| NFR-10 | Test hiệu năng xóa | `tests/test_withdrawal_performance.py` |
| NFR-11, NFR-12 | Test khôi phục | `tests/test_worker_recovery.py` |
| NFR-13, NFR-14 | CI chất lượng + tái lập | `.github/workflows/ci.yml`, job `reproducibility` |
| NFR-15 | Validate OpenAPI + ma trận trình duyệt | `tests/test_openapi.py`, `tests/manual/browser_matrix.md` |
| NFR-16 | CI matrix hai backend DB | `.github/workflows/ci.yml` |
| NFR-17 | Smoke offline | `.github/workflows/smoke-offline.yml` |

---

# 11. PHỤ LỤC — TIÊU CHÍ CHẤP NHẬN SẢN PHẨM CUỐI (DEFINITION OF DONE)

## 11.1. DoD cho một yêu cầu chức năng

Một FR chỉ được đánh dấu `DONE` khi đủ **6 điều kiện**:

1. Toàn bộ acceptance criteria của FR đó có test tự động tương ứng và test pass trên CI.
2. Mã nguồn nằm đúng module đã ghi trong ma trận truy vết mục 10.
3. Mã có type hints đầy đủ và `ruff` không báo lỗi. `mypy --strict` chưa được cấu hình nên tiêu chí đó chưa kiểm chứng.
4. Độ bao phủ test của module chứa FR đạt ngưỡng NFR-13.
5. Nếu FR thay đổi schema dữ liệu hoặc API, tài liệu SRS và file schema trong `schemas/` được cập nhật trong **cùng một pull request**.
6. Có ít nhất một thành viên khác trong nhóm review và approve pull request.

## 11.2. DoD cho toàn sản phẩm

| # | Tiêu chí | Cách kiểm chứng | Bắt buộc |
| --- | --- | --- | --- |
| 1 | Luồng end-to-end chạy được: upload → QC → ASR → feature → scoring → báo cáo → duyệt → lưu hồ sơ | Demo trực tiếp trên máy sạch bằng `docker compose up`, không sửa code giữa chừng | Có |
| 2 | 100% FR ưu tiên **Must** đã `DONE` theo mục 11.1 | Bảng trạng thái trong `docs/status/fr_status.md` | Có |
| 3 | Toàn bộ acceptance criteria trong SRS có test tương ứng | Đối chiếu ma trận mục 10; `pytest --collect-only` liệt kê đủ 105 test case | Có |
| 4 | Mọi lỗi trả về reason code, **không** có band mặc định trong bất kỳ nhánh lỗi nào | Chạy bộ 8 fixture lỗi (quá ngắn, clipping, im lặng, nhiễu, hỏng file, ASR fail, transcript rỗng, thiếu đặc trưng) và kiểm tra `band = null` | Có |
| 5 | `teacher_verified` không bao giờ tự bật | `pytest tests/test_teacher_verified_invariant.py` | Có |
| 6 | Tiêu chí Interaction luôn `null` + `insufficient_evidence` | TC-62, TC-63 | Có |
| 7 | Không có audio thật, transcript thật, PII hay secret trong repository | `gitleaks detect` + rà soát thủ công `git ls-files` | Có |
| 8 | Log không chứa PII | TC-102 (NFR-09) | Có |
| 9 | Quy trình xóa dữ liệu chạy được trên dữ liệu synthetic và sinh deletion log không PII | TC-95..TC-98 | Có |
| 10 | Toàn bộ bảng metric của báo cáo sinh lại được bằng **một lệnh** từ manifest đã khóa | `make evaluate` tạo lại `reports/eval_*.json` khớp giá trị đã nộp | Có |
| 11 | Huấn luyện tái lập: hai lần chạy cho kết quả giống tới 4 chữ số thập phân | Job CI `reproducibility` (NFR-14) | Có |
| 12 | Tất cả 18 NFR có bằng chứng đo lường được lưu trong `reports/` hoặc `benchmarks/` | Rà soát bảng truy vết NFR mục 10 | Có |
| 13 | README hướng dẫn chạy offline, có sơ đồ kiến trúc và bảng ánh xạ SRS ↔ module | Người ngoài nhóm dựng lại được hệ thống trong ≤ 30 phút theo README | Có |
| 14 | `model_card.md` ghi rõ dữ liệu huấn luyện, giới hạn, prohibited uses, retention | Rà soát tài liệu | Có |
| 15 | `docs/license_inventory.md` liệt kê license của từng corpus và model đã dùng | Rà soát tài liệu | Có |
| 16 | Demo có kịch bản dự phòng offline (video + JSON mẫu) phòng khi môi trường lỗi | Diễn tập demo ít nhất 1 lần trước buổi bảo vệ | Có |
| 17 | FR ưu tiên **Should** đã `DONE` hoặc có lý do cắt được ghi trong decision log | `docs/decision_log.md` | Nên |
| 18 | Báo cáo kết quả đo lường tuân thủ quy tắc tuyên bố: có quần thể, metric, khoảng bất định và giới hạn sử dụng | Rà soát theo checklist tuyên bố và giới hạn tuyên bố (R6 mục 5) | Có |

## 11.3. Điều kiện KHÔNG được đánh dấu hoàn thành

- Còn bất kỳ nhánh nào sinh band khi dữ liệu đầu vào không hợp lệ.
- Có bất kỳ chuỗi nào trong sản phẩm mang nghĩa "chứng chỉ CEFR", "đạt/không đạt" hoặc "kết quả chính thức".
- Tiêu chí Interaction được gán điểm từ bài độc thoại.
- `teacher_verified` bị đặt `true` bởi bất kỳ logic tự động nào.
- Số liệu kết quả trong báo cáo không có script/config/seed để tái lập.
- Còn tài liệu viện dẫn Nghị định 13/2023/NĐ-CP làm cơ sở pháp lý.
- Sơ đồ kiến trúc trong tài liệu mô tả module không tồn tại trong mã nguồn, hoặc ngược lại.

## 11.4. Lịch triển khai 12 tuần (W4–W15) đối chiếu DoD

| Tuần | Mốc | FR mục tiêu | Người chịu trách nhiệm |
| --- | --- | --- | --- |
| W4 | Vertical slice chạy được: upload → QC → ASR → feature → báo cáo kỹ thuật | FR-01..FR-03, FR-06, FR-07, FR-10..FR-14 | SV1 chính, SV3 hỗ trợ API |
| W5 | Đặc trưng đủ 14, đóng gói có version; huấn luyện Ridge trên S&I | FR-15..FR-18 | SV1 (feature), SV2 (model) |
| W6 | BERT grader + fusion + band mapper + confidence | FR-19..FR-22 | SV2 |
| W7 | Evidence, nhận xét theo mẫu, báo cáo có provenance; giao diện sinh viên kèm ghi âm trực tiếp | FR-23..FR-27, FR-39 | SV2 (evidence), SV3 (UI) |
| W8 | Cờ review, hàng đợi, duyệt/sửa, audit; giao diện giảng viên | FR-28..FR-31 | SV3 chính |
| W9 | Quản trị, quyền riêng tư, xuất/xóa dữ liệu, hồ sơ; đo toàn bộ NFR | FR-32..FR-38, NFR-01..NFR-18 | SV3 (hệ thống), SV2 (NFR độ chính xác) |
| W10 | Đóng băng mã nguồn, chạy kiểm định trên dữ liệu sinh viên, viết báo cáo, diễn tập demo | Không thêm FR mới | Cả nhóm |

**Quy tắc cắt phạm vi:** nếu một mốc trễ quá 3 ngày, cắt theo thứ tự: FR-39 → FR-26 → FR-34 → FR-36 → FR-08 → FR-38. Không bao giờ cắt FR-23, FR-28, FR-30, FR-31, FR-33, FR-35 vì đây là các yêu cầu bảo đảm tính đúng đắn về đo lường và pháp lý.

---

## Bảng ký duyệt

| Vai trò | Họ tên | Xác nhận | Ngày |
| --- | --- | --- | --- |
| SV1 — Speech pipeline | | ☐ | |
| SV2 — Scoring/ML | | ☐ | |
| SV3 — Hệ thống & tích hợp | | ☐ | |
| GV Ngoại ngữ | | ☐ | |
| GVHD | | ☐ | |

---

*Tài liệu này là phiên bản 1.3 (07/10/2026), baseline gốc là bản 1.0. Mọi thay đổi phải ghi vào nhật ký quyết định `markdown/week_01/21_week1_decision_log.md` kèm ảnh hưởng tới FR, quy tắc nghiệp vụ, use case, test case và module code tương ứng, và nâng số phiên bản ở bảng "Lịch sử phiên bản".*
