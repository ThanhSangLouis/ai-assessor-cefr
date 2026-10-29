# Xây dựng hệ thống AI hỗ trợ đánh giá năng lực nói tiếng Anh theo CEFR cho sinh viên đại học Việt Nam ở trình độ A2-B2

## 25. Gói review G1 và ma trận hoàn thành tuần 1

| Thuộc tính | Giá trị |
| --- | --- |
| Mục đích | Gói pre-read cô đọng để GVHD/GV Ngoại ngữ duyệt các quyết định tuần 1 |
| Trạng thái tài liệu | DRAFT - READY FOR REVIEW |
| Trạng thái cổng | NOT HELD |
| Phiên bản | 1.1 |
| Ngày cập nhật | 12/09/2026 |
| Nguồn chuẩn | `AGENTS.md`, yêu cầu người dùng, quyết định APPROVED và hồ sơ `00-24` |

Tài liệu này không phải biên bản họp, không thay chữ ký và không nâng bất kỳ quyết định nào thành `APPROVED`.

## 1. Requirement đã khóa ở cấp dự án

- Population: sinh viên đại học Việt Nam từ 18 tuổi, dải A2-B2.
- Intended use: hỗ trợ formative/diagnostic, low-stakes.
- Không cấp chứng chỉ CEFR, tự động đậu/rớt, placement hoặc thay quyết định của giảng viên.
- Sáu criterion candidate: Range, Accuracy, Fluency, Interaction, Coherence, Phonology.
- Mọi score/feedback phải truy được về evidence; thiếu evidence trả `null`/`insufficient_evidence`.
- Không suy Interaction từ độc thoại; không phạt accent Việt; `teacher_verified` mặc định `false`.
- Local-first; không đưa audio/transcript/PII lên dịch vụ ngoài khi chưa có consent/data approval rõ ràng.

## 2. Research và survey đã hoàn thành ở mức desk research

| Hạng mục | Bằng chứng | Trạng thái |
| --- | --- | --- |
| CEFR/Companion/Manual/ALTE/mediation | `02_source_reading_log.md` và source links | COMPLETED - desk research only |
| Bản đồ repo và tài liệu tuần 1 | `README.md`, `24_week1_rebuild_review.md` | COMPLETED |
| Mâu thuẫn tài liệu | Conflict register C001-C010 trong `21_week1_decision_log.md` | COMPLETED - resolution chuyên môn cần duyệt; C006/C010 đã xử lý bằng D019 |
| Source claim pháp lý hiện hành | `16_data_management_plan.md`, `17_consent_requirements.md` | VERIFIED SOURCE; institutional review pending |
| Code/dependency/runtime | Chưa có codebase vận hành; Git baseline mới `c0ddd8a` trên `main` | SURVEYED; C006/C010 resolved, implementation vẫn chờ V3 |
| Pedagogical pre-review | `28_ai_pedagogical_pre_review.md` | COMPLETED - AI support only; human approval pending |

Desk research không thay thế familiarisation, descriptor sorting, quiz hoặc chuyên môn của người duyệt.

## 3. Specification đề nghị duyệt

| ID | Quyết định đề nghị | Khuyến nghị | Nếu chưa duyệt |
| --- | --- | --- | --- |
| D002 | Intended use | Formative/diagnostic, low-stakes | Không collection/implementation |
| D003 | Construct | Sáu criterion theo Companion Appendix 3 | Không khóa rubric |
| D004 | Interaction evidence | Chỉ chấm response có contingent interaction đủ | `Interaction=null` |
| D005 | Mediation | Ngoài MVP | Nếu thêm, phải mở lại scope/task/validation |
| D006 | Phonology | Intelligibility; không native-accent target | Không khóa rubric/rater training |
| D007 | Human protocol | 2 rater độc lập + 1 adjudicator | Không tạo reference/gold label |
| D008 | Split | Speaker/group-level, test chống leakage | Không chạy experiment |
| D009 | Confirmation set | Chỉ mở sau model freeze | Không được gọi là holdout sạch |
| D010 | Processing | Local-first; external API chỉ opt-in + approval/consent | Không upload dữ liệu thật |
| D011 | Task C sample | Candidate subset 25-30, chỉ sau pilot khả thi | Không claim Interaction coverage toàn mẫu |
| D012 | Overall | Guided judgement; không trung bình cơ học trước validation | Chỉ báo criterion profile |
| D013 | Task C method | Human interlocutor chuẩn hóa theo branching script; recorded fallback | Thu hẹp claim/Interaction missing |
| D014 | Parallel forms | Paired subset cùng speaker, counterbalanced | Bỏ/đổi RQ6 |
| D015 | Sample/precision | 70-90, sàn 60 chỉ là planning range; cần analysis tái lập | Không claim power/precision đã chứng minh |

## 4. Spec vận hành candidate cho pilot

- Task A: 90-120 giây, 30 giây chuẩn bị, kể/mô tả trải nghiệm quen thuộc.
- Task B: 120 giây, 30 giây chuẩn bị, ba bullet scaffold, trình bày quan điểm về đời sống sinh viên.
- Task C: 3-4 phút, human interlocutor theo branching script, ít nhất ba exchange có contingency, ghi âm hai phía.
- Tổng phiên khoảng 8-10 phút kể cả instruction/chuyển task; khóa bằng timing pilot.
- Human rater nghe audio và thấy prompt/task ID; không thấy ASR transcript, AI output, identity hoặc rating khác ở vòng độc lập.
- Tối đa hai lượt nghe ở vòng độc lập; lượt bổ sung chỉ ở adjudication và có reason code.
- Off-topic/task relevance là flag riêng. Criterion đủ evidence vẫn có thể chấm; criterion thiếu trả `null`.
- Interaction chỉ có score khi evidence ref bao phủ response, initiative và repair/clarification/contingency theo rubric; nếu không trả `insufficient_evidence`.

Chi tiết và rationale nằm trong `08_open_questions_for_pedagogy_lab.md` và `14_ALTE_speaking_grid_draft.md`.

## 5. Test plan trước Implement/collection

| Nhóm test | Điều kiện tối thiểu |
| --- | --- |
| Construct/task | Monologue không tạo Interaction score; thiếu evidence không thành điểm mặc định; accent không bị dùng như lỗi tự thân |
| Rating | Rater độc lập không thấy AI/rating khác; `teacher_verified` không tự bật; disagreement/adjudication có audit trail |
| Data/schema | Field/version/evidence ref đầy đủ; evidence ID tồn tại; lỗi input trả reason code |
| Privacy | Synthetic withdrawal/deletion, access denial, log scan, backup restore và checksum đều đạt |
| ML validity | Không speaker leakage; confirmation set bị khóa; cùng manifest/preprocessing/seed cho baseline comparison |
| Reproducibility | Config, seed, fold version, dependency/model version và artifact hash được lưu |

Không có test nào được ghi `PASS` trong tài liệu này vì chưa có implementation hoặc lần chạy thực tế.

## 6. Ma trận hoạt động tuần 1

| Hoạt động/đầu ra | Trạng thái thật | Có thể đóng bằng hồ sơ hiện tại? | Hành động còn lại |
| --- | --- | --- | --- |
| Requirement/scope/non-claims | READY FOR REVIEW | Chưa | GVHD duyệt D002 và các non-claims |
| Desk research | COMPLETED | Có, ở mức desk research | Người đọc chính vẫn cần familiarisation riêng |
| Source reading của SV1/SV2/SV3 | NOT STARTED | Không | Mỗi người điền log đọc |
| Descriptor sorting | NOT STARTED | Không | Chạy activity thật và lưu kết quả ẩn danh |
| CEFR familiarisation quiz | NOT STARTED | Không | Chạy quiz thật; không bịa điểm |
| Construct/descriptor/evidence map | READY FOR REVIEW | Chưa | GV Ngoại ngữ duyệt D003-D006 |
| Open questions | RECOMMENDATIONS PREPARED | Chưa | Reviewer đóng bằng decision ID/ngày |
| RQ/validation argument | READY FOR REVIEW | Chưa | GVHD/SV2 duyệt estimand và D008-D009/D014-D015 |
| ALTE task spec | READY FOR REVIEW | Chưa | Duyệt timing, Task C và rater view |
| DMP/consent | READY FOR ETHICS REVIEW; SYNTHETIC TEST PARTIAL PASS | Chưa | Chốt retention, storage, key/access owner; test encryption/access thật |
| Rater/adjudicator roster | NOT STARTED | Không | Điền tên thật sau khi được chỉ định |
| Chapter 1 draft | READY FOR REVIEW | Chưa | GVHD review claim/citation |
| G1 meeting/sign-off | NOT HELD | Không | Tổ chức họp và ghi `22_G1_review_minutes.md` |

## 7. Agenda quyết định 30 phút cho G1

1. Duyệt hoặc sửa D002-D006: intended use và construct.
2. Duyệt D007, chỉ định rater/adjudicator hoặc owner tuyển/chốt người.
3. Duyệt D013: Task C human interlocutor hay fallback và giới hạn claim.
4. Duyệt D014-D015: paired subset, planning sample và yêu cầu precision analysis.
5. Chốt owner/deadline cho retention, encryption/key, ethics và familiarisation.
6. Chọn `PASS`, `CONDITIONAL PASS` hoặc `FAIL` trong biên bản; mọi điều kiện phải có owner/deadline.

## 8. Điều kiện bàn giao sang tuần 2

Chỉ mở backlog W2 khi:

- G1 đã họp và có danh sách tham dự/kết luận thực tế;
- các decision blocking có trạng thái, approver và ngày;
- construct/Interaction/Phonology được GV Ngoại ngữ xác nhận;
- rater plan và DMP/consent có owner/deadline rõ;
- familiarisation/sorting/quiz có bằng chứng thật hoặc được ghi thành điều kiện bắt buộc có deadline;
- D019/baseline Git đã được ghi nhận; mọi implementation work item dùng base/head commit cụ thể.

Cho đến lúc đó, trạng thái trung thực của tuần 1 là: **deliverables prepared; human activities and G1 approval pending; W1 NOT DONE**.

Runbook cho toàn bộ phần cần người thật nằm tại `27_human_activity_runbook.md`; kết quả DMP synthetic nằm tại `26_synthetic_dmp_test_report.md`; nhận xét chuyên môn hỗ trợ nằm tại `28_ai_pedagogical_pre_review.md`.
