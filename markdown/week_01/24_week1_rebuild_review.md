# Xây dựng hệ thống AI hỗ trợ đánh giá năng lực nói tiếng Anh theo CEFR cho sinh viên đại học Việt Nam ở trình độ A2-B2

## 24. Báo cáo làm lại và review bộ hồ sơ tuần 1

| Thuộc tính | Giá trị |
| --- | --- |
| Phạm vi | Desk research, survey, tái đặc tả và QA bộ `week_01` |
| Trạng thái tài liệu | DRAFT - báo cáo kỹ thuật, không phải G1 sign-off |
| Người thực hiện | Codex hỗ trợ; nhóm/GV phải kiểm tra và xác nhận phần thuộc thẩm quyền |
| Phiên bản | 1.2 |
| Ngày | 02/09/2026 |

## 1. Requirement

- Dựng lại tuần 1 theo `AGENTS.md` và lộ trình chi tiết, không tự mở rộng phạm vi.
- Giữ population là sinh viên đại học Việt Nam từ 18 tuổi, A2-B2.
- Giữ intended use formative/diagnostic, low-stakes; không certification, pass/fail, placement hoặc thay quyết định giảng viên.
- Sáu criterion mục tiêu: Range, Accuracy, Fluency, Interaction, Coherence, Phonology.
- Mọi score/feedback truy được evidence; thiếu Interaction phải trả `null`/`insufficient_evidence`.
- Không giả lập hoạt động, metric, approval, rater, ethics hoặc sign-off.

## 2. Research

Nguồn chính thức đã kiểm tra ngày 02/09/2026:

1. [CEFR 2001](https://rm.coe.int/1680459f97).
2. [CEFR Companion Volume 2020](https://rm.coe.int/cefr-companion-volume-with-new-descriptors-2020/16809ea0d4).
3. [Manual for Relating Examinations to the CEFR 2009](https://rm.coe.int/1680667a2d).
4. [New revised Manual for Language Test Development and Examining 2026](https://rm.coe.int/new-revised-manual-for-language-test-development-and-examining-joint-p/48802cc30d).
5. [The CEFR Grid for Speaking Tests 2014](https://rm.coe.int/16806979df).
6. [North & Piccardo: mediation descriptors](https://rm.coe.int/developing-illustrative-descriptors-of-aspects-of-mediation-for-the-co/1680713e2c).
7. [Luật Bảo vệ dữ liệu cá nhân 91/2025/QH15](https://vanban.chinhphu.vn/?classid=1&docid=214590&pageid=27160&typegroup=) và [Nghị định 356/2025/NĐ-CP](https://vanban.chinhphu.vn/?classid=0&docid=216387&pageid=27160).

Kết luận áp dụng:

- CEFR không cung cấp thuật toán chấm; claim alignment phải có specification, standardisation và validation evidence.
- Manual 2026 yêu cầu automated rating được kiểm tra accuracy, reliability, robustness, explainability và monitoring.
- Fairness, stakeholder communication, documentation và data protection là một phần của validity argument.
- ALTE Grid có bất nhất nội tại giữa câu giới thiệu “34 questions” và numbering 1-36; truy vết bằng question ID.

## 3. Survey

- Workspace hiện là bộ tài liệu, chưa có codebase/`pyproject.toml`/CI/test runner.
- `.git` có cấu trúc thiếu refs/index nên `git status` không chạy được; chưa thể dùng Git để xác nhận diff/history.
- Tất cả artifact W1 ban đầu ở `DRAFT`; không có bài làm sorting/quiz, biên bản workshop, tên rater/adjudicator, quyết định ethics hoặc G1 sign-off.
- Đề cương v3.1 có nhiều lựa chọn được viết như “chốt”, nhưng decision log W1 chỉ xác định D001; D002-D012 vẫn `PROPOSED`.
- Không tìm thấy Phụ lục S hoặc script/config/output mô phỏng được đề cương dùng để biện minh MDE/quy mô mẫu.

## 4. Spec baseline sau làm lại

| Boundary | Quy tắc |
| --- | --- |
| Approval | Chỉ decision log được dùng để biết quyết định đã duyệt; draft đầy nội dung không đồng nghĩa approved |
| Interaction | Chỉ chấm khi task tạo đủ evidence tương tác; nếu thiếu: `level=null`, `score_status=insufficient_evidence` |
| Phonology | Tập trung intelligibility; accent không phải lỗi tự thân |
| Evidence | `evidence_id` phải tồn tại, có provenance/version/quality; LLM không được tự tạo evidence |
| Human review | QC/ASR risk/conflict/missing evidence phải có `review_reason`; `teacher_verified=false` mặc định |
| Evaluation | Split theo speaker; preprocessing/tuning/calibration trong fold; common-response paired comparison |
| Data | Local-first; identity tách research workspace; không audio/transcript/PII trong Git hoặc log |
| Claims | Số chưa đo giữ `[CẦN ĐO]`; sample/metric mục tiêu không được gọi là kết quả |

## 5. Test plan

| ID | Kiểm tra | Kỳ vọng |
| --- | --- | --- |
| T01 | Tên đề tài/phạm vi trong `week_01` | Không có mở rộng population ngoài đại học Việt Nam 18+, A2-B2 |
| T02 | Interaction semantics | Có `null`/`insufficient_evidence`; không có điểm giả từ monologue |
| T03 | Evidence/teacher verification | Có invariant evidence; `teacher_verified` mặc định false |
| T04 | Decision/approval | D002-D015 không bị nâng thành `APPROVED`; G1 là `NOT HELD` |
| T05 | RACI | Mỗi hàng công việc có đúng một cell chứa `A`/`A/R` |
| T06 | Research reproducibility | C003/D015/R19 ghi rõ thiếu precision artifact |
| T07 | Cross-document conflicts | Task C và parallel-form được ghi ở decision/open-question/risk/backlog |
| T08 | Privacy | Có local-first, PII separation, no-content logging và synthetic deletion test |
| T09 | Markdown links/tables | Link tương đối tồn tại; bảng chính giữ số cột nhất quán ở mức kiểm tra tĩnh |

## 6. Plan và implementation

- Cập nhật README/schedule để phân biệt document status, activity status và gate status.
- Bổ sung nguồn chính thức, gồm Manual 2026 và pháp luật Việt Nam hiện hành.
- Sửa construct/evidence/missing-data invariants.
- Chuyển các giả định Task C, paired prompt và sample size thành decision/blocker rõ ràng.
- Sửa RACI về đúng một Accountable mỗi hàng.
- Cập nhật risk register, Chapter 1, G1 minutes và W2 backlog.
- Chỉ đồng bộ phần liên quan trong roadmap/đề cương tổng hợp; không sửa artifact nhị phân.
- Thêm `.gitignore` bảo vệ secret, identity map, consent đã điền, audio thật, transcript/rating thô, participant report và log local.

## 7. Review result

Kết quả kiểm tra tĩnh ngày 02/09/2026:

| Test | Kết quả | Bằng chứng |
| --- | --- | --- |
| T01 | PASS | Không còn mở rộng “cao đẳng” như population hợp lệ; các lần xuất hiện A1/C1/C2, placement/chứng chỉ đều nằm trong exclusion/non-claim |
| T02 | PASS | Contract `level=null` + `score_status=insufficient_evidence`; matrix ghi rõ A/B không chấm Interaction |
| T03 | PASS | Evidence invariant và `teacher_verified=false` xuất hiện ở construct/evidence/scope |
| T04 | PASS | Static scan không tìm D002-D015 ở trạng thái `APPROVED`; G1 được ghi `NOT HELD` |
| T05 | PASS | Script đếm cell RACI xác nhận đúng một `A`/`A/R` cho mỗi hàng công việc |
| T06 | PASS | C003, D015 và R19 cùng ghi thiếu artifact precision analysis |
| T07 | PASS | D013-D014, Q14/Q25/Q27, R08/R21 và W2-05/W2-06 truy vết hai conflict |
| T08 | PASS có giới hạn | Không có filename audio/secret/identity/consent đã điền; đã thêm `.gitignore`; chưa thể kiểm tra access/encryption thực tế |
| T09 | PASS | Link Markdown tương đối đều tồn tại; script đếm pipe không phát hiện bảng lệch cột |

Không có test code/lint/typecheck vì workspace chưa có codebase, `pyproject.toml`, Makefile hoặc CI. `git status` không chạy được vì `.git` hiện chỉ có `HEAD`, `config`, `description`, `hooks`, `info`, `objects` và thiếu metadata repository cần thiết; review không tự sửa/xóa `.git`.

Việc review này không thể xác minh:

- mức hiểu CEFR của thành viên;
- ý kiến chuyên môn của GV Ngoại ngữ/GVHD;
- nhân sự và giờ cam kết của rater/adjudicator;
- approval ethics/pháp lý của trường;
- feasibility/precision của quy mô mẫu;
- validity/reliability/accuracy của hệ thống khi chưa có dữ liệu.

Do đó, trạng thái đúng của W1 vẫn là `NOT DONE`, G1 là `NOT HELD`.

## 8. Bổ sung sau review

Sau vòng QA ban đầu, bộ hồ sơ được hoàn thiện thêm ở phần có thể làm mà không cần giả lập con người:

- `02`: thêm sáu bản ghi desk research có kết luận, rủi ro và câu hỏi duyệt.
- `08`: thêm khuyến nghị cụ thể cho Q01-Q28, giữ nguyên trạng thái chưa phê duyệt.
- `14`: điền candidate timing, Task C protocol, rater view và cách xử lý missing Interaction.
- `16`: thêm logical storage roots, retention proposal và test plan privacy bằng synthetic data.
- `21`: cụ thể hóa phương án khuyến nghị D013-D015.
- `22`: liên kết G1 pre-read và đưa decision ID vào agenda.
- `25`: tạo gói G1 review và ma trận trạng thái toàn bộ hoạt động tuần 1.

Kiểm tra tĩnh được chạy lại ngày 02/09/2026: link Markdown tương đối `PASS`, bảng Markdown nhất quán số cột `PASS`, D002-D015 không có quyết định bị tự nâng thành `APPROVED` `PASS`. Các placeholder còn lại đều thuộc biểu mẫu hoạt động, nhân sự, ethics hoặc sign-off cần người thật; chúng được giữ có chủ đích.

## 9. Thực thi phần còn lại có thể tự động hóa

- Thêm `tools/week1_dmp_synthetic_check.py`, không có production dependency và chỉ tạo dữ liệu tạm synthetic.
- Lần chạy cuối `PASS`: identity separation, boundary schema, log privacy, checksum/restore, withdrawal/deletion và cleanup.
- `NOT TESTED`: encryption at rest và role access control vì chưa có approved storage/tài khoản thật.
- Thêm `26_synthetic_dmp_test_report.md` ghi command, config, kết quả, sự cố và giới hạn.
- Thêm `27_human_activity_runbook.md` để SV/GV chạy familiarisation, sorting, quiz, Pedagogy Lab, rater appointment, ethics review và G1 mà không giả lập bằng chứng.

## 10. Cập nhật tiếp nối ngày 12/09/2026

- Object store Git cũ được kiểm tra có 1.222 blob, 6 tree và 0 commit; không có refs/index/logs/remote để phục hồi lịch sử.
- Theo D019, metadata hỏng được sao lưu riêng và workspace hiện tại được commit thành baseline `c0ddd8a` trên branch `main`; C006/C010 được giải quyết ở mức repository.
- DMP synthetic được chạy lại: sáu kiểm tra logic `PASS`; encryption-at-rest và role access vẫn `NOT_TESTED`.
- `28_ai_pedagogical_pre_review.md` được bổ sung để hỗ trợ G1; tài liệu không thay human sign-off.
- Hồ sơ W2/W3 draft có thể tiếp tục được version/diff bằng Git, nhưng G1/G2 và V3 vẫn là stop condition trước implementation.
