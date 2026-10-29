# BÁO CÁO TIẾN ĐỘ TUẦN 2

## Xây rubric và nhiệm vụ nói

| Thông tin | Nội dung |
| --- | --- |
| Tên đề tài | Xây dựng hệ thống AI hỗ trợ đánh giá năng lực nói tiếng Anh theo CEFR cho sinh viên đại học Việt Nam ở trình độ A2-B2 |
| Nhóm thực hiện | `[Điền họ tên và MSSV]` |
| Giảng viên hướng dẫn | `[Điền họ tên]` |
| Thời gian báo cáo | Tuần 2 theo kế hoạch; tổng hợp đến 12/09/2026 |
| Trạng thái tuần | **Gói thiết kế ứng viên đã chuẩn bị; hoạt động pilot/calibration chưa thực hiện** |
| Phụ thuộc | **Bị chặn bởi G1 chưa họp** |
| Cổng nghiệm thu | **G2 `NOT HELD` — chưa được phép ghi PASS/APPROVED** |
| Phiên bản minh chứng Git | `d9058bdc89951ad048c3d4008f3a45f8d0952f7e` |

## 1. Mục tiêu tuần

Tuần 2 nhằm chuyển mô tả CEFR thành công cụ chấm có thể quan sát và kiểm chứng: descriptor A2/B1/B2 cho sáu tiêu chí, bộ nhiệm vụ nói, prompt bank, rating form, reason codes, quy trình chấm độc lập, anchor và hiệu chuẩn rater. G2 chỉ đạt khi mỗi tiêu chí có nhiệm vụ tạo evidence, rater giải thích được điểm và thiết kế Task C/latency đã được thử nghiệm.

## 2. Tóm tắt kết quả

Nhóm đã chuẩn bị một **gói ứng viên sư phạm–đo lường** bao phủ phần lớn backlog thiết kế tuần 2. Gói này gồm rubric analytic, rating manual, prompt Task A/B, hai kịch bản Task C dạng branching, rating form, reason-code schema, cấu trúc `speaking_profile`, protocol đo latency, kế hoạch anchor/calibration, schema dữ liệu, fixture plan, đặc tả precision analysis và contract test plan.

Song song, nhóm đã khảo sát nguồn dữ liệu công khai, xây kế hoạch tiếp nhận và đặc tả manifest. Kết luận desk research là chưa có corpus công khai nào thay thế được dữ liệu chính đúng population và đủ sáu tiêu chí cho claim xác nhận. Không có corpus nào được tải vì license, storage và G1 chưa được duyệt.

Toàn bộ nội dung trên vẫn là `DRAFT CANDIDATE` hoặc `PROPOSED`; chưa có rater thật, anchor thật, pilot, agreement hoặc human approval.

## 3. Công việc đã thực hiện

| Hạng mục | Sản phẩm đã chuẩn bị | Trạng thái |
| --- | --- | --- |
| Rubric A2-B2 | Descriptor ứng viên cho Range, Accuracy, Fluency, Interaction, Coherence và Phonology; có lựa chọn insufficient evidence | `DRAFT CANDIDATE` |
| Rating manual | Hai lượt nghe, blind independent rating, confidence, adjudication trigger và quy tắc tránh bias | `DRAFT CANDIDATE` |
| Task A/B | Prompt kể/mô tả và nêu quan điểm, thời lượng và evidence chính | `DRAFT CANDIDATE` |
| Task C | Hai scenario branching, constraint, clarification, intervention rule và ghi timestamp | `DRAFT CANDIDATE` |
| Prompt equivalence | Nguyên tắc cùng blueprint, counterbalance và paired subset | `DRAFT PLAN` |
| Rating form/reason codes | Schema trường bắt buộc, reason codes QC/ASR/task/review/privacy | `DRAFT CANDIDATE` |
| Speaking profile | Ví dụ synthetic cố ý không tạo điểm CEFR; `teacher_verified=false` | `DRAFT CANDIDATE` |
| Latency protocol | Tách human response latency khỏi system capture latency | `DRAFT CANDIDATE` |
| Anchor/calibration | Kế hoạch dùng audio có quyền sử dụng, blind rating và thảo luận boundary | `PLAN PREPARED` |
| Data schema/test invariants | Entity, version/provenance, speaker split, evidence reference và privacy invariants | `SPEC/TEST PLAN PREPARED` |
| Precision analysis | Đặc tả scenario, seed, cluster, ordinal outcome và uncertainty | `SPEC PREPARED; NO OUTPUT` |
| Khảo sát public data | Source register, shortlist, giới hạn sử dụng và acquisition gate | `DESK RESEARCH COMPLETED` |
| Lane viết luận văn | Có nguyên liệu thiết kế cho Chương 2; chưa có bằng chứng Chương 2 đã được GVHD duyệt hoàn tất | `NOT VERIFIED AS COMPLETE` |

## 4. Minh chứng chính

- [Bản đồ hồ sơ tuần 2](../week_02/README.md).
- [Gói ứng viên sư phạm và đo lường tuần 2](../week_02/04_ai_pedagogical_candidate_package.md).
- [Sổ nguồn dữ liệu công khai/có đăng ký](../week_02/01_public_data_source_register.md).
- [Kế hoạch tiếp nhận dữ liệu ngoài](../week_02/02_data_acquisition_plan.md).
- [Đặc tả manifest cho corpus ngoài](../week_02/03_dataset_manifest_spec.md).
- [Tiền thẩm định sư phạm liên quan rubric/Task C](../week_01/28_ai_pedagogical_pre_review.md).

## 5. Các nguyên tắc chất lượng đã được đưa vào thiết kế

- Interaction chỉ được chấm khi task có contingent interaction; Task A/B luôn trả `insufficient_evidence` cho tiêu chí này.
- Accent Việt không bị coi là lỗi; Phonology dựa trên intelligibility, listener effort và breakdown có bằng chứng.
- Lỗi ASR không được dùng trực tiếp như lỗi Accuracy của người học.
- Thiếu evidence không được chuyển thành A2, điểm 0 hoặc điểm mặc định.
- `teacher_verified` mặc định `false` và chỉ được đổi khi có audit record của hành động giảng viên thật.
- Rater độc lập không xem AI prediction, transcript ASR hoặc rating của người khác trước adjudication.
- Mọi artifact quan trọng cần version, provenance, pseudonymous ID và evidence reference hợp lệ.

## 6. Đánh giá chuyên môn dưới góc nhìn giáo viên

### Điểm mạnh

- Rubric ứng viên mô tả progression A2-B1-B2 hợp lý và không đồng nhất band với một chỉ số kỹ thuật đơn lẻ.
- Rating manual giảm anchoring/halo nhờ blind rating, hai lượt nghe và tách adjudication khỏi chấm độc lập.
- Task A/B có mục tiêu giao tiếp rõ; Task B đã có scaffold để giảm nguy cơ instruction quá khó cho A2.
- Task C đã đưa vào contingency, clarification và repair thay vì chỉ đo thời gian phản hồi.
- Rating form cho phép profile không đồng đều giữa sáu tiêu chí, phù hợp thực tế người học.

### Điểm còn yếu

- Chưa có ít nhất hai anchor và một near-boundary sample cho từng boundary; rater chưa chứng minh cách hiểu thống nhất.
- Task C chưa pilot nên còn rủi ro đo khả năng xử lý kịch bản/interlocutor thay vì năng lực Interaction ổn định.
- Overall band chưa có guided-judgement rule được standardise; trước validation nên báo criterion profile thay vì tự sinh overall.
- Chưa đo workload của two-pass rating, rater fatigue, disagreement pattern hoặc thời gian adjudication.
- Chưa chạy precision-analysis script nên các con số quy mô mẫu vẫn chỉ là planning assumptions.
- Chưa có dữ liệu người thật hoặc kết quả pilot; do đó chưa thể báo agreement, độ chính xác hoặc hiệu quả rubric.

### Nhận định tổng hợp

Nếu đánh giá như một giáo viên, tuần 2 **đã có một bản thiết kế tốt để tổ chức workshop và dry run**, nhưng **chưa phải công cụ chấm có thể sử dụng**. Điểm nghẽn quan trọng nhất là thiếu rater/anchor thật và thiếu pilot Task C. G2 chưa đủ bằng chứng để nghiệm thu.

## 7. Phần chưa hoàn tất và hành động cần làm

| Việc còn thiếu | Hành động | Bằng chứng nghiệm thu |
| --- | --- | --- |
| Phê duyệt đầu vào G1 | Tổ chức G1 và khóa các quyết định construct/task/data | Biên bản G1, approver, ngày và điều kiện thật |
| Human review rubric | Workshop với GV Ngoại ngữ, sửa wording và boundary rules | Rubric version mới + change log |
| Anchor set | Chọn audio có consent/license, phủ A2/B1/B2 và near-boundary | Manifest, provenance và reference ratings thật |
| Rater calibration | Hai rater chấm độc lập, thảo luận evidence, re-rate | Rating records, observed agreement và unresolved cases |
| Dry run Task A/B | Thử 4-6 mẫu phù hợp, đo instruction load/floor/ceiling | Pilot notes và quyết định sửa prompt |
| Pilot Task C/latency | Chuẩn hóa branching/intervention, ghi hai phía và timestamp cùng clock | Turn log, latency validity và finding về interlocutor effect |
| Overall rule | Chọn guided judgement hoặc hoãn overall ở MVP | Decision log và testable specification |
| Precision analysis | Viết/chạy script với config, seed và nhiều scenario | Script, config, output hash và review |
| G2 review | Hội đồng/rater xác nhận evidence coverage và tính khả dụng | Biên bản G2: `PASS`, `CONDITIONAL PASS` hoặc `FAIL` thật |

## 8. Kế hoạch chuyển tiếp

1. Hoàn tất G1 trước khi biến gói ứng viên thành rubric/protocol chính thức.
2. Tổ chức human review, sau đó phát hành rubric/prompt version mới thay vì sửa âm thầm bản draft.
3. Chạy dry run và calibration bằng audio có quyền sử dụng; báo observed result, không đặt số giả.
4. Quyết định Task C dựa trên evidence pilot. Nếu không tạo contingent interaction ổn định, loại Task C và để Interaction ngoài MVP.
5. Chỉ mở G2 khi rater giải thích được band bằng evidence và mọi criterion có task tạo cơ hội quan sát hợp lệ.

## 9. Kết luận tuần

Tuần 2 đã hoàn thành tốt phần **chuẩn bị thiết kế**: rubric ứng viên, task blueprint, protocol, schema và test plan đã có cấu trúc nhất quán. Tuy nhiên, chưa có bằng chứng thực nghiệm hoặc xác nhận của người chấm. Kết luận chính thức là:

> **Candidate package prepared; human review, anchor calibration, pilot and G2 approval pending; W2 NOT DONE.**

| Xác nhận | Nội dung |
| --- | --- |
| Đại diện nhóm | `[Ký/ghi họ tên sau khi kiểm tra nội dung]` |
| Giảng viên hướng dẫn | `[Ý kiến và chữ ký thực tế]` |
| Ngày trình | `[Điền ngày]` |
