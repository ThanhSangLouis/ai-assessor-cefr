# Xây dựng hệ thống AI hỗ trợ đánh giá năng lực nói tiếng Anh theo CEFR cho sinh viên đại học Việt Nam ở trình độ A2-B2

## Lộ trình chi tiết tuần 1: chốt nền tảng đo lường, phạm vi và điều kiện nghiên cứu

> Baseline được rà soát lại ngày 02/09/2026. “Chốt” trong lộ trình có nghĩa là phải có quyết định và sign-off thực tế; nội dung soạn sẵn hoặc do AI hỗ trợ không tự trở thành `APPROVED`. Trạng thái hiện tại xem `week_01/README.md`, decision log `21` và review `24`.

## 1. Mục tiêu của tuần 1

Tuần 1 chưa tập trung huấn luyện mô hình AI. Mục tiêu chính là xác định rõ hệ thống sẽ đánh giá năng lực nào, dựa trên bằng chứng nào, dành cho ai và được phép sử dụng kết quả trong phạm vi nào.

Đến cuối tuần, nhóm phải trả lời được sáu câu hỏi:

1. “Năng lực nói tiếng Anh” trong đề tài được định nghĩa như thế nào?
2. A2, B1 và B2 khác nhau ở những biểu hiện quan sát được nào?
3. Những loại nhiệm vụ nói nào cần thiết để tạo đủ bằng chứng?
4. AI được phép hỗ trợ đến đâu và giảng viên giữ trách nhiệm gì?
5. Hệ thống có thể đưa ra tuyên bố nào và không được tuyên bố điều gì?
6. Dữ liệu, người chấm và thủ tục đạo đức đã đủ điều kiện để bước sang tuần 2 hay chưa?

## 2. Các kết luận phải thống nhất trước khi làm

### 2.1. CEFR là khung tham chiếu, không phải thuật toán chấm

CEFR cung cấp hệ thống khái niệm, các mức tham chiếu và descriptor. CEFR không quy định phải dùng Whisper, LLM, tốc độ nói, một công thức tính điểm hay một ngưỡng QWK cụ thể. Những lựa chọn kỹ thuật đó thuộc trách nhiệm của nhóm nghiên cứu và phải được kiểm định.

### 2.2. Đề tài đánh giá performance để suy luận về proficiency

Máy và giảng viên chỉ quan sát được một số bài nói cụ thể. Từ các performance này, nghiên cứu mới suy luận thận trọng về năng lực của người học. Vì vậy, một bài hoặc một prompt không đủ đại diện cho toàn bộ năng lực Speaking.

### 2.3. Production, Interaction và Mediation không đồng nhất

- **Spoken production:** người học nói theo lượt dài, ví dụ kể chuyện, mô tả hoặc trình bày quan điểm.
- **Spoken interaction:** người học phải nghe, phản hồi, giữ lượt, yêu cầu làm rõ và cùng phát triển hội thoại.
- **Mediation:** người học xử lý hoặc truyền đạt lại nội dung, làm trung gian, hỗ trợ người khác hiểu hoặc cùng kiến tạo ý nghĩa.

Mediation không tự động trở thành một tiêu chí chỉ vì nhiệm vụ có hội thoại. Trong phạm vi MVP, mediation chỉ nên là hướng mở rộng, trừ khi nhóm thiết kế một nhiệm vụ riêng có nguồn thông tin và người nhận rõ ràng.

### 2.4. Sáu tiêu chí dùng trong đề tài

| Tiêu chí | Ý nghĩa cần chốt trong tuần 1 | Điều không được hiểu sai |
| --- | --- | --- |
| Range | Phạm vi cấu trúc và từ vựng người học có thể huy động để diễn đạt | Không đo bằng độ dài câu hoặc số từ đơn thuần |
| Accuracy | Mức kiểm soát ngữ pháp và từ vựng khi thực hiện nhiệm vụ | Không tính mọi lỗi ASR thành lỗi người học |
| Fluency | Khả năng duy trì lời nói, xử lý do dự, pause và tự sửa trong ngữ cảnh nhiệm vụ | Không đồng nhất với nói càng nhanh càng tốt |
| Interaction | Khởi tạo, phản hồi, giữ lượt, phối hợp và yêu cầu làm rõ | Không chấm từ bài độc thoại |
| Coherence | Phát triển, tổ chức và liên kết ý thành một diễn ngôn có thể theo dõi | Không chỉ đếm từ nối |
| Phonology | Intelligibility, sound articulation và prosodic features như stress, rhythm, intonation | Không phạt accent Việt nếu thông điệp vẫn dễ hiểu |

### 2.5. Mục đích sử dụng

Hệ thống được chốt là **formative/diagnostic, low-stakes**:

- AI đưa ra mức A2/B1/B2 ước lượng, hồ sơ sáu tiêu chí, confidence và bằng chứng.
- Giảng viên duyệt các trường hợp bất định và đưa ra quyết định cuối cùng.
- Hệ thống không cấp chứng chỉ CEFR.
- Hệ thống không tự quyết định đậu/rớt, xếp lớp hoặc kết quả học vụ.

## 3. Phân công trong tuần 1

| Vai trò | Trách nhiệm chính trong tuần 1 | Thời lượng gợi ý |
| --- | --- | --- |
| SV1 - Speech pipeline | Đọc phần Phonology, Fluency, Spoken production; lập bản đồ bằng chứng có thể lấy từ audio; ghi các giới hạn của ASR/audio | 22-26 giờ |
| SV2 - Đo lường và mô hình | Chủ trì CEFR familiarisation, construct, RQ, descriptor A2-B2, chuỗi lập luận validation | 26-30 giờ |
| SV3 - Sản phẩm và dữ liệu | Hoàn thành ALTE Grid bản nháp, intended use, RACI, consent, data plan, risk register và biên bản | 22-26 giờ |
| Giảng viên Ngoại ngữ | Xác nhận construct, cách hiểu descriptor, phạm vi rubric và điều kiện chấm | 4-6 giờ |
| GVHD | Duyệt tên đề tài, RQ, phạm vi, dữ liệu, nhân sự và cổng G1 | 1-2 giờ |

Các mốc giờ trên là ước lượng quản trị dự án, không phải yêu cầu của CEFR.

## 4. Công việc chuẩn bị trước ngày 1

Người phụ trách: SV2 chủ trì, SV3 hỗ trợ.

- Tạo thư mục `week_01` và các file Markdown theo danh sách đầu ra ở Mục 11.
- Tạo bảng phân công đọc tài liệu; mỗi nguồn có một người đọc chính và một người kiểm tra chéo.
- Lập glossary ban đầu: CEFR, descriptor, construct, performance, proficiency, production, interaction, mediation, rater, adjudicator, validity, reliability, feasibility và calibration.
- Đặt lịch bốn cuộc họp: kickoff, workshop construct, họp data/ethics và review G1.
- Xác nhận khả năng tham gia của ít nhất 2 rater và 1 adjudicator; chưa cần chấm trong tuần 1.

Đầu ra:

- `00_week1_schedule.md`
- `01_glossary.md`
- Lịch họp và danh sách người chịu trách nhiệm.

## 5. Ngày 1 - Familiarisation với CEFR

### Mục tiêu

Cả nhóm hiểu CEFR theo cùng một cách trước khi định nghĩa rubric hoặc chọn feature.

### Buổi sáng: kickoff và định vị tài liệu

1. GVHD hoặc SV2 trình bày bài toán trong 15 phút, không trình bày giải pháp kỹ thuật chi tiết.
2. Phân biệt ba tầng:
   - communicative activities: người học làm gì;
   - communicative competences: người học huy động nguồn lực như thế nào;
   - evidence/measurement: hệ thống quan sát được dấu hiệu gì.
3. Đọc tập trung các phần:
   - CEFR Companion Volume: action-oriented approach, production, interaction, linguistic/pragmatic competence và Appendix 3;
   - CEFR 2001: validity, reliability, feasibility và các loại assessment;
   - Manual: Familiarisation trước Specification;
   - ALTE Speaking Grid: truy vết Part A theo ID 1-19 và Part B theo ID 20-36; lưu ý phần giới thiệu của chính tài liệu nói “34 questions”, không dùng tổng số câu làm claim;
   - Manual for Language Test Development and Examining sửa đổi 2026: validity argument, fairness, data protection, documentation và automated rating;
   - tài liệu mediation: khác biệt giữa interaction và mediation.

### Buổi chiều: hoạt động familiarisation

1. Mỗi người nhận các descriptor A2, B1, B2 đã bỏ nhãn mức.
2. Tự sắp xếp descriptor theo ba mức.
3. So sánh kết quả theo cặp, sau đó thảo luận toàn nhóm.
4. Tô màu từ khóa phân biệt mức, ví dụ:
   - A2: simple, routine, short, familiar, support;
   - B1: straightforward, connected, familiar/non-routine, reasonable control;
   - B2: clear, detailed, systematic, spontaneous, supporting detail.
5. Làm bài kiểm tra ngắn gồm các câu hỏi:
   - CEFR có bắt buộc một thuật toán chấm không?
   - Có được chấm Interaction từ bài độc thoại không?
   - Accent Việt có đồng nghĩa với Phonology thấp không?
   - Mediation có đồng nghĩa với dịch thuật không?
   - Descriptor activity và descriptor competence khác nhau thế nào?

### Đầu ra ngày 1

- `02_source_reading_log.md`: nguồn, phần đã đọc, ý chính và ảnh hưởng đến đề tài.
- `03_descriptor_sorting_result.md`: kết quả trước/sau thảo luận và điểm chưa thống nhất.
- `04_cefr_familiarisation_check.md`: câu hỏi kiểm tra và câu trả lời chuẩn.

### Tiêu chí hoàn thành

- Tất cả thành viên phân biệt đúng production, interaction và mediation.
- Không ai xem CEFR như một công thức chấm có sẵn.
- Nhóm nhận biết được criterion level và plus level; MVP chỉ cam kết A2, B1, B2.
- Các điểm còn bất đồng được đưa vào danh sách câu hỏi cho giảng viên.

## 6. Ngày 2 - Chốt construct Speaking A2-B2

### Mục tiêu

Tạo định nghĩa vận hành của năng lực nói và bản đồ descriptor A2-B2 để giảng viên duyệt.

### Buổi sáng: workshop với giảng viên Ngoại ngữ

1. Chốt phạm vi communicative activities:
   - spoken production bắt buộc;
   - spoken interaction chỉ được chấm khi có hội thoại;
   - mediation để ngoài MVP.
2. Chốt sáu tiêu chí của Appendix 3: Range, Accuracy, Fluency, Interaction, Coherence và Phonology.
3. Với mỗi tiêu chí, trả lời:
   - tiêu chí đại diện cho phần nào của construct;
   - biểu hiện A2, B1, B2 khác nhau ở đâu;
   - nhiệm vụ nào có thể tạo bằng chứng;
   - con người có thể quan sát gì;
   - máy có thể đo dấu hiệu nào;
   - dấu hiệu máy không được phép thay thế điều gì.

### Buổi chiều: lập construct-evidence map

Tạo bảng tối thiểu có các cột:

| Trường | Nội dung |
| --- | --- |
| Criterion | Một trong sáu tiêu chí |
| CEFR basis | Descriptor hoặc scale làm căn cứ |
| A2/B1/B2 distinction | Khác biệt chính giữa ba mức |
| Eliciting task | Nhiệm vụ tạo bằng chứng |
| Human-observable evidence | Điều rater nghe và đánh giá |
| Machine-observable proxy | Dấu hiệu audio/transcript/turn log |
| Confounders | ASR error, noise, topic knowledge, prompt, device |
| Missing-evidence rule | Khi nào phải trả “chưa đủ bằng chứng” |

Quyết định bắt buộc:

- Interaction của Task A/B phải là `not_scored` hoặc `insufficient_evidence`.
- Phonology lấy intelligibility làm trọng tâm; accent chỉ được mô tả khi ảnh hưởng khả năng hiểu.
- Fluency cần xét pause phù hợp với thông điệp, không dùng speech rate đơn lẻ.
- Accuracy phải có quy tắc tách lỗi ASR khỏi lỗi người học.
- Overall band chưa được tính bằng trung bình cơ học trước khi rubric và dữ liệu được kiểm định.

### Đầu ra ngày 2

- `05_construct_definition.md`
- `06_cefr_A2_B1_B2_descriptor_map.md`
- `07_construct_evidence_matrix.md`
- `08_open_questions_for_pedagogy_lab.md`

### Tiêu chí hoàn thành

- Giảng viên giải thích được ý nghĩa của từng tiêu chí bằng lời của mình.
- Mỗi tiêu chí có ít nhất một nhiệm vụ dự kiến tạo bằng chứng.
- Không có proxy kỹ thuật nào được coi là đồng nghĩa trực tiếp với mức CEFR.
- Ranh giới giữa accent, intelligibility và pronunciation error được ghi rõ.
- Ở data boundary, Interaction thiếu bằng chứng dùng `level=null` + `score_status=insufficient_evidence`; không điền 0/A2 hoặc suy từ tiêu chí khác.

## 7. Ngày 3 - Chốt mục đích, đối tượng và loại assessment

### Mục tiêu

Xác định hệ thống được phép sử dụng trong bối cảnh nào và kết quả có ý nghĩa gì.

### Buổi sáng: intended use và target population

Chốt các thông tin theo ALTE Speaking Grid:

- Target language: English.
- Target levels: A2, B1, B2.
- Target population: sinh viên đại học Việt Nam, từ 18 tuổi.
- Context: học tiếng Anh như ngoại ngữ ở đại học.
- Intended use: formative và diagnostic, low-stakes.
- Delivery channel: audio recording; phương thức Task C vẫn `PROPOSED` và phải chứng minh tạo đủ bằng chứng tương tác.
- Rating: analytic profile kết hợp overall guided judgement.
- Raters: AI và 2 rater độc lập; adjudicator xử lý bất đồng.
- Feedback: criterion-specific, có evidence và cờ teacher review.

### Buổi chiều: claims, non-claims và RQ

Tạo bảng hai cột:

| Có thể nghiên cứu/tuyên bố | Không được tuyên bố |
| --- | --- |
| Mức A2/B1/B2 ước lượng trên đúng mẫu nghiên cứu | Chứng chỉ CEFR chính thức |
| Mức đồng thuận AI-human và human-human | AI thay thế giám khảo |
| Giá trị bổ sung của audio, transcript và interaction | Khả năng tổng quát cho A1, C1, C2 hoặc mọi quốc gia |
| Ảnh hưởng của WER, noise, prompt và device | Accent Việt là lỗi |
| Confidence và quy tắc teacher review | Confidence là xác suất tuyệt đối đúng trong mọi bối cảnh |

Rà soát RQ:

1. AI-human agreement so với human-human ceiling.
2. Fusion có cải thiện so với audio-only và transcript-only hay không.
3. WER, noise, duration, device và prompt ảnh hưởng sai số thế nào.
4. Calibration và confidence có phát hiện ca cần giảng viên duyệt hay không.
5. Feedback có evidence có dễ hiểu và hành động được hay không.
6. Kết quả có ổn định giữa prompt tương đương, lần chạy và nhiễu hay không.

### Đầu ra ngày 3

- `09_scope_and_intended_use.md`
- `10_target_population.md`
- `11_claims_and_nonclaims.md`
- `12_research_questions_v1.md`
- `13_definition_of_done.md`

### Tiêu chí hoàn thành

- Intended use không mâu thuẫn với output của hệ thống.
- Không có chức năng high-stakes trong phạm vi MVP.
- Tất cả RQ đều có dữ liệu dự kiến và phương pháp trả lời.
- Các tuyên bố vượt quá dữ liệu người Việt A2-B2 được loại bỏ.

## 8. Ngày 4 - Đặc tả sơ bộ, validation argument, pháp lý và nhân sự

### Mục tiêu

Biến phạm vi đã chốt thành kế hoạch tạo bằng chứng và điều kiện vận hành nghiên cứu.

### Buổi sáng: hoàn thành ALTE Speaking Grid bản nháp

Điền phần “test as a whole”:

- số lượng task dự kiến;
- tổng thời lượng và preparation time;
- construct;
- intended use;
- target population;
- rating method và criteria;
- số rater và cách xử lý bất đồng;
- loại feedback.

Điền phần “component task” riêng cho Task A, B và C:

- topic và domain;
- ngôn ngữ hướng dẫn;
- duration/preparation;
- recorded hay real-time;
- mức kiểm soát của prompt;
- interaction type;
- discourse type;
- response type;
- kỹ năng tích hợp;
- communicative purpose;
- rhetorical function;
- register;
- expected CEFR range.

Đây là bản nháp để phát hiện thiếu coverage; prompt cụ thể chỉ được khóa ở tuần 2.

### Buổi chiều: validation argument và data/ethics

Áp dụng Manual dưới dạng chuỗi bằng chứng phù hợp với khóa luận:

| Giai đoạn | Áp dụng trong đề tài |
| --- | --- |
| Familiarisation | W1: nhóm và giảng viên thống nhất CEFR/descriptor |
| Specification | W1-W2: construct, task, rubric, intended use và coverage |
| Standardisation | W4: rater training, anchor, practice và kiểm tra agreement |
| Standard setting | Chỉ thực hiện ở mức phù hợp dữ liệu; không tuyên bố cut-score chính thức nếu chưa đủ bằng chứng |
| Validation | Chạy xuyên suốt: pilot, human-human, AI-human, reliability, calibration, error analysis và usability |

Hoàn thành data/ethics plan:

- consent tách khỏi file audio;
- participant ID giả;
- không đưa tên, email, MSSV vào model workspace;
- quyền từ chối/rút/xóa dữ liệu;
- mục đích sử dụng audio và transcript;
- thời hạn lưu trữ;
- người được quyền truy cập;
- quy trình xử lý incident;
- không suy luận cảm xúc, giới tính, tính cách hoặc nguồn gốc xã hội;
- không dùng dữ liệu ngoài phạm vi consent để huấn luyện dịch vụ khác.

Hoàn thành RACI:

- ai sở hữu rubric;
- ai thay đổi prompt;
- ai giữ khóa liên kết danh tính;
- ai chạy model;
- ai được xem nhãn;
- ai adjudicate;
- ai phê duyệt release.

### Đầu ra ngày 4

- `14_ALTE_speaking_grid_draft.md`
- `15_validation_argument_map.md`
- `16_data_management_plan.md`
- `17_consent_requirements.md`
- `18_RACI.md`
- `19_risk_register.md`

### Tiêu chí hoàn thành

- Mọi task dự kiến đều có communicative purpose rõ ràng.
- Nhóm nhận diện được construct-irrelevant variance từ đọc/listening/topic knowledge.
- Có 2 rater và 1 adjudicator dự kiến bằng văn bản.
- PII và dữ liệu mô hình có nơi lưu tách biệt.
- Validation được coi là quá trình liên tục, không phải việc chỉ làm ở tuần cuối.
- Automated rating có kế hoạch kiểm tra accuracy/agreement, reliability, robustness, explainability, monitoring và privacy theo Manual phát triển test sửa đổi 2026.

## 9. Ngày 5 - Tích hợp, viết Chương 1 và duyệt G1

### Buổi sáng: kiểm tra chéo

Mỗi thành viên kiểm tra tài liệu của một người khác:

- SV1 kiểm tra construct-evidence map và các giới hạn kỹ thuật.
- SV2 kiểm tra ALTE Grid, RQ và validation argument.
- SV3 kiểm tra tính đầy đủ của scope, ethics, RACI và output.

Kiểm tra tính nhất quán:

- Tên đề tài phải giống nhau trong mọi file.
- Phạm vi luôn là sinh viên đại học Việt Nam, từ 18 tuổi, A2-B2.
- Interaction chỉ xuất hiện ở task có hội thoại.
- Mediation không được ghi là tiêu chí MVP.
- Phonology dùng intelligibility, sound articulation và prosody.
- AI chỉ chấm sơ bộ; giảng viên quyết định cuối cùng.

### Buổi chiều: họp cổng G1

Trình bày cho GVHD và đại diện giảng viên Ngoại ngữ:

1. Tên đề tài và phát biểu bài toán.
2. Construct và sáu tiêu chí.
3. Production, interaction và mediation boundary.
4. Intended use, target population và non-claims.
5. RQ và dữ liệu cần để trả lời.
6. Kế hoạch rater/adjudicator.
7. Data/ethics plan.
8. Rủi ro và phương án cắt phạm vi.

Mỗi quyết định phải có trạng thái:

- `APPROVED`: được dùng làm đầu vào tuần 2;
- `REVISE`: có người chịu trách nhiệm và hạn sửa;
- `OPEN`: chưa giải quyết, có ảnh hưởng được mô tả;
- `BLOCKING`: không được sang tuần 2 nếu chưa xử lý.

### Lane viết

Hoàn thành Chương 1:

- 1.1. Bối cảnh;
- 1.2. Vấn đề nghiên cứu;
- 1.3. Mục tiêu;
- 1.4. Câu hỏi nghiên cứu;
- 1.5. Phạm vi và giới hạn;
- 1.6. Vị trí trong ALDM-L;
- 1.7. Vai trò AI, giảng viên và sinh viên;
- 1.8. Đóng góp dự kiến.

### Đầu ra ngày 5

- `20_chapter_1_draft.md`
- `21_week1_decision_log.md`
- `22_G1_review_minutes.md`
- `23_week2_backlog.md`
- Bản scope/construct/RQ v1 đã khóa.

## 10. Ngày dự phòng - sửa theo G1 và đóng gói

Chỉ sử dụng khi có mục `REVISE` hoặc `BLOCKING`.

- Sửa tài liệu theo biên bản, không thay đổi miệng mà không ghi log.
- Gửi lại đúng người đã yêu cầu sửa để xác nhận.
- Gắn phiên bản `v1.0-week1-approved` cho tài liệu đã khóa.
- Sao lưu vào hai vị trí; kiểm tra không có audio/PII bị đưa nhầm vào kho mã nguồn.
- Nếu chưa có rater, thu hẹp đề tài thành exploratory pilot và tiếp tục tuyển rater trước G2.

## 11. Danh sách đầu ra bắt buộc của tuần 1

| Mã | File Markdown | Người sở hữu | Điều kiện hoàn thành |
| --- | --- | --- | --- |
| W1-D01 | `01_glossary.md` | SV2 | Thuật ngữ có định nghĩa và nguồn |
| W1-D02 | `02_source_reading_log.md` | Cả nhóm | Năm nguồn đều có phần đọc và kết luận |
| W1-D03 | `05_construct_definition.md` | SV2 + GV Ngoại ngữ | Sáu tiêu chí và boundary được duyệt |
| W1-D04 | `06_cefr_A2_B1_B2_descriptor_map.md` | SV2 | Có A2/B1/B2 cho sáu tiêu chí |
| W1-D05 | `07_construct_evidence_matrix.md` | SV1 + SV2 | Có task, human evidence, machine proxy và confounder |
| W1-D06 | `09_scope_and_intended_use.md` | SV3 | Đối tượng, mục đích và channel rõ |
| W1-D07 | `11_claims_and_nonclaims.md` | SV2 | Không có claim chứng chỉ/thay giám khảo |
| W1-D08 | `12_research_questions_v1.md` | SV2 | Mỗi RQ có dữ liệu và phương pháp dự kiến |
| W1-D09 | `14_ALTE_speaking_grid_draft.md` | SV3 | Điền phần toàn bài và Task A/B/C |
| W1-D10 | `15_validation_argument_map.md` | SV2 | Có Familiarisation-Specification-Standardisation-Validation |
| W1-D11 | `16_data_management_plan.md` | SV3 | PII, retention, access, withdrawal rõ |
| W1-D12 | `18_RACI.md` | SV3 | Mỗi công việc có owner và approver |
| W1-D13 | `19_risk_register.md` | Cả nhóm | Có trigger, tác động, owner và dự phòng |
| W1-D14 | `20_chapter_1_draft.md` | Cả nhóm | Hoàn thành nội dung Chương 1 |
| W1-D15 | `22_G1_review_minutes.md` | SV3 | Có quyết định và chữ/xác nhận của bên duyệt |

## 12. Checklist nghiệm thu G1

G1 chỉ được đánh dấu `PASS` khi tất cả mục sau đạt:

- [ ] Tên đề tài được GVHD duyệt và giống nhau trong mọi tài liệu.
- [ ] Đối tượng được giới hạn ở sinh viên đại học Việt Nam từ 18 tuổi, A2-B2.
- [ ] Intended use là formative/diagnostic, low-stakes.
- [ ] Sáu tiêu chí được định nghĩa và có căn cứ từ CEFR Companion Volume.
- [ ] Production, interaction và mediation được phân biệt rõ.
- [ ] Có quy tắc “không đủ bằng chứng” cho Interaction.
- [ ] Phonology tập trung vào intelligibility, không chấm accent như lỗi tự thân.
- [ ] AI chỉ đưa ra đánh giá sơ bộ; giảng viên quyết định cuối cùng.
- [ ] RQ có dữ liệu và phương pháp dự kiến để trả lời.
- [ ] Có xác nhận dự kiến của 2 rater và 1 adjudicator.
- [ ] Consent và data management plan đã được soạn.
- [ ] Không có PII trong model workspace.
- [ ] Chuỗi validation và các bằng chứng cần thu đã được lập.
- [ ] Chương 1 hoàn thành và thống nhất với scope.
- [ ] Không còn quyết định `BLOCKING` chưa có phương án.

## 13. Rủi ro riêng của tuần 1 và cách xử lý

| Rủi ro | Dấu hiệu kích hoạt | Xử lý ngay |
| --- | --- | --- |
| Hiểu CEFR như bảng quy đổi feature thành band | Có đề xuất “speech rate = B2” hoặc “WER cao = Accuracy thấp” | Quay lại construct-evidence map; ghi proxy và confounder riêng |
| Không có giảng viên sở hữu rubric | Rubric do nhóm CNTT tự chốt | Dừng G1; tìm đại diện Khoa Ngoại ngữ hoặc giảm thành prototype kỹ thuật |
| Không đủ rater | Chưa xác nhận 2 rater + 1 adjudicator | Mở danh sách dự phòng; không bỏ double-rating chỉ để kịp tiến độ |
| Phạm vi quá rộng | Thêm mediation, chatbot, LMS, tutor hoặc C1/C2 | Đưa vào stretch/future work; giữ MVP A2-B2 và assessment |
| Sáu tiêu chí gây quá tải người chấm | Rater không phân biệt được tiêu chí hoặc chấm theo ấn tượng chung | Thiết kế quy trình hai lượt: global impression rồi analytic profile; kiểm thử ở W4 |
| Nhầm interaction với monologue | Task A/B vẫn có điểm Interaction | Bắt buộc `insufficient_evidence`; Interaction chỉ lấy từ Task C |
| Nhầm accent với lỗi phát âm | Rater muốn trừ điểm chỉ vì nghe “giọng Việt” | Dùng intelligibility và effort của người nghe làm chuẩn; ghi trong rating manual |
| Ethics chưa rõ | Không biết ai giữ audio hoặc cách xóa dữ liệu | Không tuyển người tham gia; hoàn thiện consent/data plan trước |

## 14. Những việc không làm trong tuần 1

- Không huấn luyện mô hình chấm chính thức.
- Không tự đặt trọng số sáu tiêu chí.
- Không thu dữ liệu nghiên cứu chính khi chưa có consent và G1.
- Không dùng LLM để tự sinh nhãn gold.
- Không tuyên bố hệ thống “được CEFR chứng nhận”.
- Không thiết kế dashboard nâng cao.
- Không chốt prompt cuối trước khi construct và task coverage được duyệt.

## 15. Tài liệu sử dụng

1. Council of Europe. *Common European Framework of Reference for Languages: Learning, Teaching, Assessment* (CEFR 2001), đặc biệt Chương 2, Chương 3, Chương 4, Chương 5 và Chương 9.
2. Council of Europe. *Common European Framework of Reference for Languages: Learning, Teaching, Assessment - Companion Volume* (2020), đặc biệt các phần về action-oriented approach, oral production, oral interaction, communicative language competences, Phonological Control và Appendix 3.
3. Council of Europe. *Relating Language Examinations to the Common European Framework of Reference for Languages: Learning, Teaching, Assessment - A Manual*, đặc biệt các bước Familiarisation, Specification, Standardisation và Validation.
4. ALTE CEFR Special Interest Group. *The CEFR Grid for Speaking Tests* (2014), Part 1 và Part 2.
5. North, B. và Piccardo, E. *Developing Illustrative Descriptors of Aspects of Mediation for the CEFR* (2016), đặc biệt phần phân biệt reception, production, interaction và mediation.
6. Council of Europe & ALTE. *New revised Manual for Language Test Development and Examining: For use with the CEFR* (2026), đặc biệt Chương 1-2, Mục 5.2 và Appendix I.
