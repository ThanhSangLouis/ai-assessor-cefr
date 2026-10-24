# Xây dựng hệ thống AI hỗ trợ đánh giá năng lực nói tiếng Anh theo CEFR cho sinh viên đại học Việt Nam ở trình độ A2-B2

## 28. AI pedagogical pre-review trước G1

| Thuộc tính | Giá trị |
| --- | --- |
| Mục đích | Đánh giá hồ sơ dưới góc nhìn chuyên môn giảng dạy/đánh giá Speaking để hỗ trợ người duyệt thật |
| Trạng thái | COMPLETED - AI PRE-REVIEW, NOT HUMAN APPROVAL |
| Người thực hiện | Codex, không đại diện GV Ngoại ngữ/GVHD |
| Phiên bản | 1.0 |
| Ngày | 12/09/2026 |
| Nguồn | Hồ sơ W1, CEFR Companion Volume 2020, Manual 2009/2026 và ALTE Speaking Grid đã dẫn trong hồ sơ |

Tài liệu này đưa ra phán đoán chuyên môn có lý giải, nhưng không phải bài làm familiarisation của sinh viên, không phải kết quả chấm của rater và không thay chữ ký hoặc quyết định của giáo viên. Mọi quyết định D002-D016 vẫn giữ `PROPOSED` cho đến khi đúng người có thẩm quyền xác nhận.

## 1. Kết luận sư phạm

**Kết luận pre-review: READY FOR HUMAN REVIEW WITH REQUIRED REVISIONS.**

Bộ hồ sơ có nền construct tốt, giữ đúng intended use low-stakes và xử lý đúng ba rủi ro quan trọng: không chấm Interaction từ độc thoại, không coi accent Việt là lỗi và không biến thiếu bằng chứng thành điểm mặc định. Tuy nhiên chưa đủ điều kiện dùng làm công cụ chấm thật vì rubric chưa có anchor người thật, ranh giới A2/B1/B2 chưa được standardise, Task C chưa pilot và overall rule chưa có bằng chứng.

## 2. Đánh giá theo tiêu chí chất lượng công cụ đo

| Hạng mục | Nhận xét pre-review | Mức sẵn sàng | Sửa bắt buộc trước sử dụng |
| --- | --- | --- | --- |
| Intended use | Formative/diagnostic được nêu nhất quán; non-claims rõ | Tốt | Giữ disclaimer trên mọi report/UI |
| Construct | Sáu tiêu chí bám qualitative features và phân biệt construct với proxy | Tốt | GV Ngoại ngữ xác nhận wording và phạm vi lớp học |
| Range/Accuracy | Descriptor có progression hợp lý, không đồng nhất feature với band | Khá | Thêm anchor và ví dụ lỗi ảnh hưởng nghĩa ở từng boundary |
| Fluency | Nhấn mạnh khả năng duy trì lời nói, không chỉ tốc độ | Tốt | Pilot pause/repair trong ngữ cảnh task; không dùng ngưỡng số cứng để gán band |
| Interaction | Quy tắc missingness đúng; human interlocutor là phương án có giá trị hơn prerecorded prompt | Chưa khóa | Pilot standardisation, contingency, repair và interlocutor effect |
| Coherence | Phân biệt listing, linear sequence và supported discourse | Khá | Thêm ví dụ phát triển ý ở Task A/B và xử lý off-topic |
| Phonology | Dùng intelligibility/effort; không yêu cầu native-like accent | Tốt | Huấn luyện rater bằng cặp ví dụ accent mạnh nhưng intelligible và breakdown thật |
| Task A/B | Chức năng giao tiếp và thời lượng candidate hợp lý | Khá | Pilot floor/ceiling, topic familiarity và prompt equivalence |
| Task C | Blueprint có contingency nhưng tính chuẩn hóa chưa được đo | Yếu trước pilot | Dùng branching script, intervention rules, ghi âm hai phía và turn timestamps |
| Rating protocol | Blind independent rating, two-pass và listening limit giảm anchoring/halo | Khá | Dry run 4-6 mẫu; đo thời gian, disagreement và tải nhận thức |
| Overall band | Không trung bình cơ học là đúng về validity | Chưa đủ | Khóa guided-judgement rule hoặc chỉ báo criterion profile ở MVP |
| Fairness/privacy | Accent rule, PII separation và local-first phù hợp population | Khá | Approved storage, encryption/access test và audit comment rater |

## 3. Khuyến nghị cho các quyết định D002-D016

Các giá trị dưới đây là **khuyến nghị để người duyệt xem xét**, không phải trạng thái quyết định.

| ID | Khuyến nghị AI | Lý do/điều kiện |
| --- | --- | --- |
| D002 | Nên chấp nhận | Intended use formative/diagnostic là phù hợp bằng chứng dự kiến và giảm tác hại |
| D003 | Nên chấp nhận có rà wording | Sáu tiêu chí phù hợp construct; cần GV Ngoại ngữ kiểm tra ví dụ vận hành |
| D004 | Nên chấp nhận | Interaction cần contingent interaction; A/B không tạo evidence đủ |
| D005 | Nên chấp nhận | Mediation cần task/validation riêng, không khả thi trong MVP hiện tại |
| D006 | Nên chấp nhận | Intelligibility là trọng tâm phù hợp; accent không phải deficit |
| D007 | Chấp nhận có điều kiện | Chỉ có hiệu lực khi đã chỉ định 2 rater + 1 adjudicator và có lịch thực tế |
| D008 | Nên chấp nhận | Speaker-level split là invariant chống leakage |
| D009 | Nên chấp nhận | Confirmation set phải bị khóa trước model freeze |
| D010 | Nên chấp nhận | Local-first phù hợp privacy/reproducibility; external API chỉ opt-in có consent |
| D011 | Cần sửa trước duyệt | Cỡ subset Task C phải theo feasibility/precision analysis, không lấy 25-30 như con số tự chứng minh |
| D012 | Nên chấp nhận | Không trung bình cơ học; trước validation nên ưu tiên criterion profile |
| D013 | Chấp nhận cho pilot | Human interlocutor chuẩn hóa tạo bằng chứng Interaction tốt hơn; phải đo interlocutor effect |
| D014 | Chấp nhận cho pilot | Paired subset counterbalanced phù hợp RQ6; cỡ subset còn chờ analysis |
| D015 | Giữ PROPOSED | Planning range chưa có artifact precision tái lập; không được gọi là kết quả đo |
| D016 | Nên chấp nhận | Public corpora không đủ đúng population/construct cho claim xác nhận chính |

## 4. Nhận xét rubric như một giáo viên Speaking

1. Descriptor hiện đủ làm nền cho workshop nhưng chưa đủ để chấm nhất quán. Mỗi boundary cần ít nhất hai anchor và một near-boundary sample do rater thật thảo luận.
2. Không được hạ band chỉ vì câu trả lời ngắn nếu task/QC không tạo đủ cơ hội nói; trường hợp đó phải dùng `insufficient_evidence` hoặc task-completion flag.
3. Accuracy phải xét mức lỗi cản trở nghĩa và mức kiểm soát, không đếm lỗi thô từ ASR.
4. Fluency phải phân biệt pause để lập kế hoạch với breakdown kéo dài; speech rate chỉ là evidence phụ.
5. Interaction phải quan sát response, initiative, turn management và repair; latency hệ thống phải tách khỏi thời gian phản hồi người học.
6. Phonology phải dựa trên intelligibility và listener effort; giọng Việt rõ và dễ hiểu không phải lỗi.
7. Rater cần ghi evidence ngắn gọn cho band và reason code khi không đủ bằng chứng; không bắt buộc tạo transcript đầy đủ.

## 5. Findings cần xử lý

| Finding | Mức | Vấn đề | Hành động |
| --- | --- | --- | --- |
| PED-01 | P1 | Nếu dùng prerecorded prompt tree để chấm Interaction, construct có thể bị thiếu | Chỉ dùng sau pilot chứng minh contingency; nếu không để `Interaction=null` |
| PED-02 | P1 | Overall band chưa có mapping/standardisation | Không sinh overall tự động trong vertical slice W3; chỉ report kỹ thuật |
| PED-03 | P1 | Không có rater/anchor thật | Không gọi label AI hoặc synthetic là gold/reference |
| PED-04 | P2 | Task B có nguy cơ floor effect cho A2 | Dùng ba bullet scaffold, instruction không cao hơn A2 và pilot comprehension |
| PED-05 | P2 | Descriptor chưa có decision rules cho profile uneven | Manual phải cho phép sáu criterion khác band và ghi guided judgement riêng |
| PED-06 | P2 | Workload two-pass chưa đo | Dry run và ghi thời gian/rater fatigue trước khi khóa tỷ lệ double-rating |

## 6. Phần không thể được AI đóng thay

- Bài đọc, descriptor sorting và quiz của SV1/SV2/SV3.
- Ý kiến và sign-off của GV Ngoại ngữ/GVHD.
- Chỉ định rater/adjudicator và cam kết thời gian.
- Chấm anchor, agreement và adjudication trên audio có quyền sử dụng.
- Ethics/storage approval và kiểm thử tài khoản/quyền truy cập thật.
- G1/G2 gate result và `teacher_verified=true`.

## 7. Đề nghị cho G1

Người duyệt có thể dùng bảng ở Mục 3 làm agenda. G1 chỉ nên `PASS` hoặc `CONDITIONAL PASS` khi D002-D016 có kết luận thật, mọi mục defer có owner/deadline, rater plan khả thi và DMP có đường đi đến approved storage. Nếu chưa có các bằng chứng này, trạng thái đúng vẫn là `NOT HELD` hoặc `FAIL/REVISE`, không phải `APPROVED`.
