# Xây dựng hệ thống AI hỗ trợ đánh giá năng lực nói tiếng Anh theo CEFR cho sinh viên đại học Việt Nam ở trình độ A2-B2

## 00. Trạng thái vào tuần 2

| Thuộc tính | Giá trị |
| --- | --- |
| Trạng thái W2 | BLOCKED BY G1 |
| Công việc được phép | Research/survey, source register, license review, acquisition/manifest plan |
| Công việc chưa được phép khóa | Rubric, Task C, rater protocol, collection, production schema, model experiment |
| Ngày kiểm tra | 12/09/2026 |

## 1. Requirement

- Public data không được dùng để mở rộng population claim ngoài sinh viên đại học Việt Nam từ 18 tuổi, A2-B2.
- Public corpus khác miền chỉ là auxiliary evidence; tập dữ liệu tự thu, consent đúng và human rating đúng protocol mới là bằng chứng xác nhận chính.
- Không tải corpus vào repository. Không đăng ký/đồng ý license thay người có thẩm quyền.
- Không dùng dataset split nếu không bảo đảm speaker-level separation.
- Không gọi holistic label hoặc pronunciation score là nhãn của sáu tiêu chí CEFR.

## 2. Entry gate

| Điều kiện | Hiện trạng | Hệ quả |
| --- | --- | --- |
| G1 PASS/CONDITIONAL PASS | NOT HELD | Chưa mở implementation W2 |
| D002-D006 construct/intended use | PROPOSED | Không khóa rubric/task blueprint |
| D007 rater protocol | PROPOSED | Không tạo gold/reference labels |
| D013 Task C | PROPOSED | Không triển khai interaction task |
| Approved storage/license owner | Chưa có | Không tải corpus có audio |
| Public data survey | Hoàn tất vòng 1 | Có thể lập shortlist và acquisition plan |
| Workflow Codex-Antigravity-Git | APPROVED - D017; baseline `c0ddd8a` theo D019 | Có thể soạn package/diff; chưa implement vì G1 và V3 còn thiếu |

## 3. Kết luận vào W2

Có thể tiếp tục **chuẩn bị ở trạng thái draft** cho W2-01 đến W2-16, nhưng không được khóa rubric/task/schema, tải dữ liệu hoặc gọi acceptance hoàn tất trước G1 và các approval tương ứng. Package chuẩn bị AI nằm ở `04_ai_pedagogical_candidate_package.md`.
