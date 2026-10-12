# M06 — Diagnostic Report (Báo cáo chẩn đoán)

| Metadata | Giá trị |
| --- | --- |
| SCOPE ID / TYPE | M06 / module |
| SCOPE ROOT | `docs/sdd/modules/m06-diagnostic-report/` |
| OWNER | Nguyên (đề xuất W2–W3) |
| LIFECYCLE | proposed |
| PHASE 01 | DRAFT — chờ người dùng duyệt |
| RESEARCH MODE | Đề xuất `SKIP`; người dùng quyết định trong Phase 01 |
| TARGET | W2–W3 |
| RELATED SCOPES | M03 transcript, M04 features, M05 assessment, M07 teacher review |
| SOURCE BASIS | [Tài liệu nguồn do nhóm tạo](../../../sources/README.md), [báo cáo W1](../../../reports/week-01/bao-cao-tuan-01.docx); SDD hiện hành quyết định phạm vi, contract và approval của module |
| CODE TARGET | `src/aicefr/report/` — actual hiện có, gồm SQLite repository |

## Requirement (Yêu cầu)

**Mục tiêu:** Tạo báo cáo chẩn đoán cho một bài nói, truy được nhận xét về audio/transcript/feature thật. Đây là chức năng sản phẩm; hồ sơ minh chứng theo rubric nằm ở `docs/evidence/`.

**Trong phạm vi:** Dẫn chứng của bài nói (Evidence ID, timestamp/word ref), comment template, hiển thị trạng thái provisional/teacher verified và báo cáo một bài. M05 sở hữu điểm; M07 sở hữu quyết định duyệt; M06 trình bày dữ liệu đó.

**Ngoài phạm vi W2–W3:** LLM nhận xét tự do; suy ra tác động cải thiện điểm nếu chưa có dữ liệu; thống kê tiến bộ suy diễn.

| ID | Functional Requirement (Yêu cầu chức năng) |
| --- | --- |
| M06-FR-001 | Mỗi comment/priority có evidence ref tồn tại và phù hợp criterion; thiếu evidence thì không sinh comment. |
| M06-FR-002 | Báo cáo tách score AI tạm và kết quả đã duyệt, hiển thị giới hạn low-stakes. |

## Acceptance Criteria (Tiêu chí chấp nhận)

| ID | Bằng chứng phải kiểm tra |
| --- | --- |
| M06-AC-001 | Không có evidence hợp lệ: báo cáo ghi thiếu bằng chứng, không có nhận xét khẳng định. |
| M06-AC-002 | Fixture có pause/word timestamp: evidence link đến đúng mốc và source version; `teacher_verified` mặc định false. |
| M06-AC-003 | Với M05 hợp lệ, report chỉ có một overall score/band ước lượng, năm coverage/evidence theo tiêu chí và `Interaction=null/insufficient_evidence`; không có năm điểm lặp. |

## W2 scope note (Ranh giới tuần 2)

W2 tạo báo cáo chẩn đoán cho một bài với ref hợp lệ và trạng thái chưa duyệt; M05 sở hữu một điểm/band overall, M07 sở hữu quyết định của giảng viên, M06 chỉ kết xuất overall cùng coverage của năm tiêu chí.

## Điều kiện chung và câu hỏi mở

- Unit test dùng fixture tạo bởi nhóm; smoke/integration chỉ dùng audio có quyền sử dụng. Fixture kiểm thử không là số liệu thực nghiệm; không log audio, transcript hoặc PII.
- ID, enum, schema/API xuyên module phải được cả owner liên quan review; mọi feature code chỉ bắt đầu sau khi Phase 01, 03, 04 và 05 của **module này** được người dùng duyệt theo thứ tự.
- Chủ dự án đã chọn 5 tiêu chí độc thoại làm bản nháp W2; rubric học thuật vẫn cần xác minh. Giữ field `Interaction=null` cùng lý do `insufficient_evidence` cho độc thoại. Dữ liệu/model và lịch 3 tuần xem [roadmap](../../../plan/three-week-roadmap.md).

