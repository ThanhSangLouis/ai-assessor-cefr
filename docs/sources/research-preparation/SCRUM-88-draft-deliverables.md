# SCRUM-88 — Đề bài, rubric chấm và kế hoạch thu (bản nháp)

| Thuộc tính | Giá trị |
| --- | --- |
| Task | SCRUM-88 — Đề bài, rubric chấm, kế hoạch thu |
| Phiên bản tài liệu | 0.1 · 25/10/2026 |
| Trạng thái | `DRAFT — CHỜ OWNER/GVHD REVIEW`; không phải protocol được duyệt |
| Phạm vi | Đề độc thoại A/B, biểu mẫu rating của người chấm, kế hoạch thu đề xuất |
| Nguồn | Tài liệu đã chuyển trong thư mục này, SDD M05 của repo dự án |

Tài liệu này gom các đầu ra có thể soạn từ nguồn hiện có. Prompt, descriptors, ngưỡng mẫu và quy trình thu dưới đây chưa được GV Ngoại ngữ/GVHD duyệt; chưa được cấu hình vào hệ thống hoặc dùng để thu dữ liệu thật. SCRUM-88 chưa có acceptance criteria/definition of done được cung cấp trong repo. Mapping `SCRUM-88 ↔ W6-N03` vẫn cần reconcile với W6 plan `DRAFT`.

## 1. Quyết định cần chốt trước khi đóng phiên bản

| Mục | Hiện trạng nguồn/repo | Đề xuất làm việc | Người cần quyết định |
| --- | --- | --- | --- |
| Thời lượng A/B | `KE_HOACH_KHAO_SAT.md` và UI hiện hành dùng 40–60 giây; ALTE grid draft ghi Task A 90–120 giây, Task B khoảng 120 giây. | Giữ 40–60 giây làm candidate vì khớp task page hiện tại và collection draft; không khóa chính thức trước khi người phụ trách rubric xác nhận. | Owner task + GV Ngoại ngữ/GVHD |
| Phạm vi tiêu chí | M05 đã duyệt cho scope trước đó: năm tiêu chí coverage Range, Accuracy, Fluency, Coherence, Phonology; không có criterion score/band của máy. Interaction luôn `null/insufficient_evidence` với độc thoại. Source descriptor/grid có sáu tiêu chí, gồm Interaction/Task C. | SCRUM-88 hiện chỉ draft hai task độc thoại và năm tiêu chí. Không đưa Interaction vào điểm của hai bài này. Mọi thay đổi output/band contract phải quay lại M05. | Owner M05 + GV Ngoại ngữ/GVHD |
| Điểm rubric người | Appendix B đề xuất 0–6 cho từng tiêu chí và overall; M05 overall hiện là 1.0–6.0. Không có mapping đã duyệt giữa các thang/anchor. | Giữ ô điểm numeric ở trạng thái “chờ chốt”; trước tiên thống nhất rubric/version, đơn vị điểm, quy tắc tính overall và band mapping. Không tự suy ra công thức từ descriptors. | Owner M05 + GV Ngoại ngữ/GVHD |
| Ngôn ngữ prompt | Appendix C ghi câu tiếng Việt; ALTE grid đề xuất instruction tiếng Anh đơn giản. | Dùng hai bản tiếng Anh ở Mục 2 làm bản dịch làm việc, kèm bản Việt nguồn để reviewer xác nhận equivalence. | GV Ngoại ngữ |
| Cỡ mẫu/ngưỡng | Kế hoạch nguồn đề xuất 60–90 người, phân tầng, pilot 6–8 người và nhiều ngưỡng metric. | Chỉ xem là planning options; chưa dùng làm cam kết nghiên cứu nếu chưa được GVHD/owner phê duyệt. | Owner nghiên cứu + GVHD |

## 2. Hai đề độc thoại — candidate, chưa khóa

### `SCR88-PROMPT-A` — Trải nghiệm học tập

**Bản nguồn tiếng Việt:** “Kể về một lần bạn học được điều gì đó mới ngoài trường lớp. Bạn đã học gì, học như thế nào, và vì sao nó đáng nhớ?”

**Bản tiếng Anh làm việc:** “Talk about a time when you learned something new outside class. What did you learn, how did you learn it, and why was it memorable?”

**Blueprint dự kiến:** narration/description về trải nghiệm quen thuộc; độc thoại; không chấm Interaction; 30 giây chuẩn bị và 40–60 giây trả lời nếu timing được duyệt.

### `SCR88-PROMPT-B` — Ý kiến về việc làm thêm

**Bản nguồn tiếng Việt:** “Có ý kiến cho rằng sinh viên nên đi làm thêm trong lúc học. Bạn đồng ý hay không, và vì sao?”

**Bản tiếng Anh làm việc:** “Some people think university students should have a part-time job while they study. Do you agree or disagree? Why?”

**Blueprint dự kiến:** opinion/reasoning về chủ đề quen thuộc với sinh viên; độc thoại; không chấm Interaction; 30 giây chuẩn bị và 40–60 giây trả lời nếu timing được duyệt.

### Checklist review prompt

- [ ] GV Ngoại ngữ xác nhận độ tự nhiên, tải từ vựng/ngữ pháp và độ phù hợp A2–B2 của bản tiếng Anh.
- [ ] Review xác nhận mỗi prompt có cùng số yêu cầu, độ quen thuộc và cơ hội thể hiện năm tiêu chí; nếu không tương đương, quy định cách counterbalance/thứ tự.
- [ ] Gán prompt version và ghi prompt ID/version vào response manifest trước pilot.
- [ ] Pilot usability/timing được duyệt; báo mọi thay đổi sau pilot bằng version mới.
- [ ] Owner xác nhận đề nào sẽ xuất hiện trong `demo-speaking` và có yêu cầu hiển thị trên web hay chỉ bàn giao tài liệu.

Các ô checklist đang mở; không có bằng chứng pilot hoặc human approval trong package nguồn.

## 3. Phiếu rating của người chấm — cấu trúc nháp

Đây là phiếu độc lập cho **human rater**, không thay đổi output của hệ thống. Không hiển thị hoặc cung cấp AI score/band, tên người nói, trình độ đầu vào hay rating của người chấm còn lại trong vòng chấm độc lập.

### Thông tin lượt chấm

| Trường | Giá trị điền |
| --- | --- |
| Pseudonymous response code | `[mã không định danh]` |
| Prompt ID/version | `[SCR88-PROMPT-A/B · version]` |
| Rubric version | `[chờ phê duyệt]` |
| Rater ID | `[role ID giả danh]` |
| Ngày/giờ chấm | `[ISO date/time]` |
| Audio có thể chấm? | `[Có / Không]` |
| Nếu không chấm được, lý do | `[hỏng/không nghe rõ/sai đề/khác — ghi rõ]` |

### Quan sát tiêu chí đề xuất

Descriptors sau đây được rút gọn từ descriptor map `DRAFT`; chúng là gợi ý để GV xem, chưa phải anchors hoặc rating scale đã chuẩn hóa. Ghi evidence/time range trước khi chọn mô tả phù hợp. Không điền điểm số tiêu chí cho tới khi thang điểm được duyệt.

| Tiêu chí | Mô tả A2 (đề xuất) | Mô tả B1 (đề xuất) | Mô tả B2 (đề xuất) | Evidence / time range / ghi chú |
| --- | --- | --- | --- | --- |
| Range | Câu/mẫu cơ bản và từ vựng cho tình huống quen thuộc; đôi khi phải đơn giản hóa ý. | Đủ ngôn ngữ cho chủ đề quen thuộc và một số tình huống ít dự đoán; còn do dự/vòng diễn đạt. | Đủ phạm vi để mô tả, trình bày quan điểm và hỗ trợ ý; ít phải hạn chế thông điệp. | `[ghi bằng chứng nghe được]` |
| Accuracy | Dùng được mẫu đơn giản; lỗi cơ bản còn lặp nhưng thường vẫn hiểu ý. | Kiểm soát tương đối mẫu thường dùng; lỗi tăng khi câu phức tạp nhưng ý định rõ. | Kiểm soát ngữ pháp tương đối cao; lỗi hiếm khi gây hiểu nhầm. | `[ghi bằng chứng nghe được]` |
| Fluency | Lượt nói ngắn; pause, false start hoặc sửa lời còn rõ. | Có thể duy trì lời nói; pause/sửa lời còn thấy trong đoạn dài. | Nhịp nói tương đối đều; ít pause dài nổi bật. | `[ghi bằng chứng nghe được]` |
| Coherence | Nối câu bằng connector phổ biến; trình bày như các ý đơn giản. | Nối ý ngắn thành trình tự tuyến tính, dễ theo dõi. | Diễn ngôn rõ hơn, có phát triển/hỗ trợ ý và cohesive devices. | `[ghi bằng chứng nghe được]` |
| Phonology | Phát âm đủ hiểu; đôi lúc cần lặp; ảnh hưởng L1 có thể làm tăng effort. | Nhìn chung intelligible; ảnh hưởng L1 còn nhưng không ngăn hiểu ý. | Âm nhìn chung rõ; stress/intonation hỗ trợ thông điệp; không yêu cầu accent bản ngữ. | `[ghi bằng chứng nghe được]` |

### Nhận định overall và khả năng chấm

| Trường | Giá trị |
| --- | --- |
| Overall human score | `[thang và rule đang chờ owner/GVHD chốt; nguồn đề xuất 0–6, M05 hiện dùng 1.0–6.0]` |
| Overall band | `[A2 / B1 / B2 / chưa thể gán]` |
| Unratable? | `[Có / Không]` |
| Lý do/evidence cho overall | `[ghi ngắn gọn, chỉ dựa trên audio và rubric đã duyệt]` |
| Mức chắc chắn / ghi chú bất đồng | `[chờ protocol thống nhất]` |

Không tính trung bình năm dòng tiêu chí thành overall cho tới khi có quy tắc aggregation được phê duyệt. Phiếu chưa được cấp mã version cuối và chưa dùng để chấm người thật.

## 4. Kế hoạch thu — khung đề xuất

Mọi con số trong bảng là kế hoạch tham khảo từ source package, không phải quyết định đã duyệt.

| Bước | Thao tác dự kiến | Evidence/record cần có | Gate |
| --- | --- | --- | --- |
| 0. Chốt protocol | Duyệt prompt, rubric/version, timing, sample plan, consent, DMP và storage. | Quyết định/approval ref; version manifest. | Chưa duyệt thì không tuyển hoặc thu. |
| 1. Sàng lọc/consent | Xác nhận eligibility và consent đúng mục đích; gán pseudonymous ID, identity mapping để riêng theo DMP. | Consent version/ref, eligibility reason, manifest không có PII. | Từ chối consent không ảnh hưởng học tập/quyền lợi; điều kiện cụ thể chờ GVHD/ethics. |
| 2. Thu thử (nếu được duyệt) | Source đề xuất 6–8 người, dữ liệu pilot tách khỏi tập chính. | Issue log về prompt comprehension, timing, thiết bị, consent flow; không gộp pilot vào main data. | Pilot cần approval và consent phù hợp trước khi diễn ra. |
| 3. Phiên thu candidate | Source đề xuất hai bài độc thoại, 30 giây prep, 40–60 giây ghi âm; bài tập micro 20 giây không tính điểm. Ghi thiết bị/phòng ở mức tối thiểu cần thiết. | Prompt ID/version, task ID/version, consent version, thiết bị và QC status. | Timing và retake rules cần được GVHD/owner chốt. |
| 4. QC/retake | Nghe/kiểm tra lỗi kỹ thuật theo rule đã duyệt; chỉ ghi nhận lý do retake/loại. | QC reason, số lần thử, quyết định tiếp tục/retake/không dùng. | Không tự loại bài vì chất lượng lời nói hoặc band. |
| 5. Rating | Hai rater chấm độc lập/mù theo rubric được khóa; phiếu và thứ tự có version. | Phiếu rating pseudonymous, timestamp, rubric version; chưa nhập AI output vào phiếu. | Phụ thuộc SCRUM-89: rater được tập huấn và đạt điều kiện calibration đã duyệt. |
| 6. Bảo vệ/retention | Lưu audio, identity map, ratings và log theo DMP đã duyệt; withdrawal/deletion theo cutoff đã thông báo. | Storage/access evidence, deletion procedure, retention rule và contact. | Nơi lưu, retention, access owner và deletion cutoff hiện chưa được duyệt. |

### Cỡ mẫu / phân tầng để review

Kế hoạch nguồn đề xuất tổng 60–90 sinh viên, sàn 60, hai response/người; A2 ≥25, B1 20–30, B2 ≥15; pilot 6–8 người không nhập tập chính. Các mục tiêu này chưa có approval trong SDD SCRUM-88. Cần owner/GVHD xem tính khả thi, tiêu chí eligibility, nguồn phân tầng và cách xử lý thiếu lớp/band trước khi đưa vào protocol cuối.

## 5. Đầu ra dự kiến và điều kiện review

Các mục dưới đây là checklist đề xuất để owner bổ sung/duyệt AC của ticket, không phải AC hiện hành:

- [ ] Prompt A/B có ID, version, ngôn ngữ hướng dẫn và timing đã thống nhất.
- [ ] Rubric form có criteria, descriptors/anchors, mức điểm, band mapping, unratable reasons, overall rule và evidence field; GV Ngoại ngữ/GVHD phê duyệt version.
- [ ] Collection protocol chốt population, eligibility, cỡ mẫu/phân tầng, pilot, timing, retake/QC, dữ liệu thu, consent và DMP.
- [ ] Prompt/rubric usability pilot có raw notes đã giả danh; không gọi là kết quả validation học thuật.
- [ ] Mọi câu hỏi còn mở có owner/deadline và decision reference; module M05 được cập nhật nếu thay đổi rubric/band contract.
- [ ] Nếu yêu cầu đề xuất xuất hiện trên web, task phải chỉ định route/seed/config source và browser acceptance; `demo-speaking` hiện mô tả rỗng trên QA revision `82fe708`.

## 6. Blockers và câu hỏi cần owner/GVHD trả lời

1. Chọn timing nào: 40–60 giây theo task page/kế hoạch khảo sát, hay thời lượng ALTE draft dài hơn?
2. Chỉ dùng hai bài độc thoại A/B trong SCRUM-88 hay chuẩn bị Task C? Nếu có C, cần thiết kế interlocutor/pilot riêng; không suy Interaction từ độc thoại.
3. Chốt năm tiêu chí của M05 cho rubric người chấm hay sáu tiêu chí draft? Nếu có Interaction, evidence interaction đến từ task nào?
4. Chọn thang nào cho human ratings: 0–6 theo nguồn hay scale khác; rule nào tạo overall và band? Làm rõ khác với M05 overall 1.0–6.0 và không đưa criterion-level score vào product output.
5. Cỡ mẫu, tầng A2/B1/B2, tiêu chí chọn người, pilot và các ngưỡng agreement/validation nào đã được GVHD chấp thuận?
6. Có được cấu hình prompt lên web trong SCRUM-88 không, hay chỉ bàn giao protocol và prompt document? Nếu có, cần phase approval và task/module scope tương ứng.

## Nguồn và giới hạn

- [Kế hoạch khảo sát nguồn](KE_HOACH_KHAO_SAT.md): hai prompt candidate, timing, phiếu 5 tiêu chí và collection draft; `REFERENCE_ONLY`.
- [Descriptor map](06_cefr_A2_B1_B2_descriptor_map.md), [construct/evidence matrix](07_construct_evidence_matrix.md), [ALTE grid](14_ALTE_speaking_grid_draft.md): đều `DRAFT/PROPOSED`.
- [AI pedagogical pre-review](28_ai_pedagogical_pre_review.md): AI pre-review, không thay human review/approval.
- Target SDD: [M05 Requirement](../../sdd/modules/m05-scoring/01-requirement.md), [M05 Specification](../../sdd/modules/m05-scoring/03-specification.md). M05 approval trước đây không phê duyệt rubric/protocol mới trong tài liệu này.

Không có người tham gia, audio, rating hay kết quả pilot/calibration nào được tạo hoặc đưa vào repo.
