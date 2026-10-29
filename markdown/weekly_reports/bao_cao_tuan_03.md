# BÁO CÁO TIẾN ĐỘ TUẦN 3

## Đặc tả pipeline chạy xuyên suốt

| Thông tin | Nội dung |
| --- | --- |
| Tên đề tài | Xây dựng hệ thống AI hỗ trợ đánh giá năng lực nói tiếng Anh theo CEFR cho sinh viên đại học Việt Nam ở trình độ A2-B2 |
| Nhóm thực hiện | `[Điền họ tên và MSSV]` |
| Giảng viên hướng dẫn | `[Điền họ tên]` |
| Thời gian báo cáo | Tuần 3 theo kế hoạch; tổng hợp đến 12/09/2026 |
| Trạng thái tuần | **Planning/specification đã chuẩn bị; implementation chưa bắt đầu** |
| Phụ thuộc | **Bị chặn bởi G1, G2 và phê duyệt work item V3** |
| Cổng nghiệm thu | **G3 `NOT HELD` — chưa có demo end-to-end để đánh giá** |
| Work item | `WI-2026-001-w3-vertical-slice`, trạng thái `DRAFT_V2` |
| Phiên bản minh chứng Git | `d9058bdc89951ad048c3d4008f3a45f8d0952f7e` |

## 1. Mục tiêu tuần

Tuần 3 theo lộ trình phải tạo một pipeline cho một response khoảng hai phút đi qua upload/ingest, kiểm tra chất lượng audio, ASR, trích xuất feature và xuất report kỹ thuật mà không lộ danh tính. G3 chỉ đạt khi có một lần chạy end-to-end và bằng chứng test thực tế.

Trong trạng thái hiện tại, nhóm chỉ được thực hiện Requirement, Research, Survey, Specification, Test Plan và Plan. Implementation phải chờ G1/G2 cùng gói V3 được người dùng phê duyệt theo quy trình Codex–Antigravity–Git.

## 2. Tóm tắt kết quả

Nhóm đã xây dựng đặc tả vertical slice an toàn cho audio synthetic/non-sensitive. Thiết kế dùng một interface chính `ResponseProcessor` để che giấu ingest, audio probing, QC, ASR adapter, feature extraction, hashing, artifact handling và cleanup. Các boundary nặng như audio decoder, ASR engine và artifact store được đưa qua adapter để unit/integration test chạy deterministic mà không tải model lớn hoặc cần internet.

Pipeline đầu tiên cố ý chỉ tạo **báo cáo kỹ thuật**, không tạo điểm CEFR, feedback học tập, calibration hoặc `teacher_verified=true`. Các failure path về audio hỏng, QC không đạt, ASR lỗi, thiếu version và log privacy đã được mô tả trước khi implement.

Chưa có codebase chức năng, chưa tích hợp faster-whisper, chưa xử lý audio mẫu, chưa tạo JSON runtime và chưa chạy G3. Vì vậy đây là tiến độ thiết kế, không phải kết quả phần mềm đã vận hành.

## 3. Công việc đã thực hiện

| Giai đoạn bắt buộc | Kết quả | Trạng thái |
| --- | --- | --- |
| Requirement | Khóa outcome: một request synthetic/local đi qua pipeline và trả report kỹ thuật typed | `PREPARED` |
| Research | Xác minh dependency candidate và các lưu ý về FFmpeg/model download bằng nguồn chính thức | `PREPARED` |
| Survey | Khảo sát repo, dependency/code hiện có và xác nhận chưa có implementation để kế thừa | `COMPLETED` |
| Specification | Mô tả request/report, status, provenance, QC/ASR/features, error behavior và out-of-scope | `DRAFT_V2` |
| Test Plan | Bao phủ happy path, audio lỗi, QC, ASR failure, privacy, Interaction, teacher verification, reproducibility và cleanup | `PREPARED` |
| Plan | Chia task và xác định chuỗi phê duyệt/implement/review theo D017 | `DRAFT_V2` |
| Git/audit | Có baseline hợp lệ và commit tham chiếu cho package | `COMPLETED` |
| Implement | Chưa tạo module/API/CLI/database adapter hoặc feature extractor | `NOT STARTED` |
| Review runtime | Chưa có diff implementation hoặc test output để review | `NOT APPLICABLE YET` |

## 4. Đặc tả đầu ra kỹ thuật dự kiến

| Thành phần | Hành vi đã đặc tả |
| --- | --- |
| Input | `response_id`, `speaker_id` giả danh, `task_id`, local `audio_ref`, version config/prompt và task mode |
| QC | Đo giá trị kỹ thuật, gắn flag/reason code; threshold là candidate versioned, không mô tả như đã validation |
| ASR | Dùng adapter local/fake; lưu engine/model/config version và khả dụng timestamp; không ghi transcript vào log |
| Features | Trả feature versioned cùng validity; feature không hợp lệ là `null` có reason code |
| Interaction | Chỉ có turn/timing evidence kỹ thuật khi dữ liệu tạo đủ điều kiện; không suy ra CEFR score |
| Scoring | Cố định `not_scored_vertical_slice`; không tạo band/confidence giả |
| Verification | `teacher_verified=false`, `review_audit_ref=null` |
| Privacy | Không trả direct identity; safe error không chứa transcript hoặc path nhạy cảm |

## 5. Minh chứng chính

- [Trạng thái vào tuần 3](../week_03/00_week3_entry_status.md).
- [Đặc tả draft vertical slice](../week_03/01_vertical_slice_draft_spec.md).
- [Work item brief](../../coordination/work_items/WI-2026-001-w3-vertical-slice/01_brief.md).
- [Work item specification](../../coordination/work_items/WI-2026-001-w3-vertical-slice/02_specification.md).
- [Plan, tasks và test plan](../../coordination/work_items/WI-2026-001-w3-vertical-slice/03_plan_tasks_test_plan.md).
- [Nghiên cứu dependency và cấu hình QC candidate](../../coordination/work_items/WI-2026-001-w3-vertical-slice/04_research.md).
- [Quy trình phối hợp Codex–Antigravity–Git](../../coordination/README.md).

## 6. Kế hoạch kiểm thử trước implementation

| Nhóm test | Kỳ vọng |
| --- | --- |
| Happy path | Report typed, deterministic, có version/hash/provenance và không tạo điểm CEFR |
| Audio corrupt/unsupported | `REJECTED` + reason code; không gọi ASR |
| Too short/silence/clipping | `REVIEW_REQUIRED` hoặc `REJECTED` theo config candidate; không bịa feature |
| ASR failure | Lỗi được giữ bằng status/reason code; không tiếp tục với transcript rỗng giả thành công |
| Privacy | Log không chứa transcript, audio hoặc direct identity |
| Speaker/Interaction | Monologue không có Interaction score |
| Human review | `teacher_verified` không thể tự chuyển `true` |
| Reproducibility | Cùng fixture/config/seed cho cùng output ở phần deterministic |
| Artifact safety | Temporary artifact được cleanup; raw input không bị sửa |
| Integration smoke | Chỉ chạy local có marker sau khi dependency/model/cache được duyệt; không cần internet mặc định |

Đây là **test plan**, chưa phải kết quả test của implementation.

## 7. Đánh giá chuyên môn dưới góc nhìn giáo viên/hội đồng

### Điểm mạnh

- Scope vertical slice được thu nhỏ hợp lý, tách kiểm chứng pipeline kỹ thuật khỏi tuyên bố chấm CEFR.
- Typed contract, version/provenance và reason codes tạo nền tái lập và truy vết tốt.
- Thiết kế fake adapter giúp kiểm thử ổn định, tránh phụ thuộc model lớn và tránh dùng dữ liệu người thật.
- Failure path được xem là đầu ra có ý nghĩa, không nuốt lỗi QC/ASR rồi tạo điểm mặc định.
- Privacy và construct được bảo vệ ngay trong contract: không direct identity, không điểm Interaction từ độc thoại, không tự bật xác nhận giảng viên.

### Điểm còn yếu

- Chưa có executable evidence nên chưa đánh giá được hiệu năng, độ ổn định, độ chính xác QC/ASR hoặc tính đầy đủ của JSON report.
- Chưa khóa exact Pydantic schema/reason-code enum với gói tuần 2.
- Chưa có quyết định về artifact storage, retention cho dữ liệu dev và vị trí model cache.
- Chưa chứng minh FFmpeg/faster-whisper có thể vận hành trên máy mục tiêu trong chế độ offline.
- Chưa có API/UI/database; các deliverable kỹ thuật theo lịch tuần 3 vẫn chưa được triển khai.

### Nhận định tổng hợp

Nếu đánh giá như một giáo viên/hội đồng, phần tuần 3 **có thiết kế kỹ thuật thận trọng và testable**, nhưng **không thể nghiệm thu G3 chỉ dựa trên tài liệu**. Mức hiện tại là “sẵn sàng để khóa gói triển khai sau phê duyệt”, không phải “pipeline đã chạy”.

## 8. Phần chưa hoàn tất và điều kiện triển khai

| Việc còn thiếu | Điều kiện trước khi làm | Bằng chứng cần có |
| --- | --- | --- |
| Khóa schema/reason codes | G2 review hoặc quyết định có thẩm quyền | Schema/version và change log |
| Chốt storage/cache/dependency | Approved local paths, retention và model policy | Config V3 không hard-code path máy cá nhân |
| Phê duyệt work item V3 | Người dùng duyệt đúng work ID + V3 | Approval thực tế và prompt `PROMPT_LOCKED` |
| Implement vertical slice | Antigravity làm đúng base commit và allowed files theo D017 | Commit riêng, raw report và actual diff |
| Test | Có implementation và fixture synthetic | Unit/integration outputs, lint/typecheck/test results |
| Review | Codex kiểm tra actual diff và chạy lại test | Review findings/fix loop nếu cần |
| G3 demo | Pipeline thực sự hoạt động | Một response synthetic khoảng hai phút chạy ingest → QC → ASR → feature → report, không lộ identity |

## 9. Kế hoạch chuyển tiếp

1. Hoàn tất G1 và G2 hoặc ghi rõ quyết định cho phép một vertical slice không chấm điểm.
2. Giải quyết các open item của `DRAFT_V2`, phát hành V3 với allowed files, dependency và lệnh test chính xác.
3. Xin người dùng phê duyệt work item V3; sau đó khóa implementation prompt theo base commit.
4. Antigravity implement/test; Codex review actual diff và evidence theo D017.
5. Chạy demo G3 bằng fixture synthetic/local được phép, ghi lại status, version và reason codes.
6. Chỉ sau G3 mới xem xét pilot audio có consent; không mở rộng sang scoring/LLM/UI hoàn chỉnh trong vertical slice đầu tiên.

## 10. Kết luận tuần

Tuần 3 đã hoàn thành phần phân tích và thiết kế để giảm rủi ro triển khai, đồng thời giữ đúng nguyên tắc không tạo điểm CEFR khi chưa có rubric/rater validation. Tuy nhiên, deliverable cốt lõi của tuần là pipeline chạy xuyên suốt chưa tồn tại. Kết luận chính thức là:

> **Requirement/research/spec/test plan prepared; implementation and G3 evidence absent; W3 NOT DONE.**

| Xác nhận | Nội dung |
| --- | --- |
| Đại diện nhóm | `[Ký/ghi họ tên sau khi kiểm tra nội dung]` |
| Giảng viên hướng dẫn | `[Ý kiến và chữ ký thực tế]` |
| Ngày trình | `[Điền ngày]` |
