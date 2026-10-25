# SCRUM-83 — Evidence nền tảng DoD W5

**Evidence ID:** `SCRUM-83-W5-DOD-BASELINE`  
**Ngày rà:** 25/10/2026  
**Owner theo nhánh:** Thắng  
**Code baseline reviewed:** `82fe708af80f0b50eb540c65b5c583f64868d2c8`
**Evidence introduced in:** `f6a8ef0934af09bed36b7e36530137a2372d0049`
**Kết luận:** đã lập baseline evidence; W5 vẫn `PENDING`, chưa có verdict nghiệm thu của chủ dự án.

## Phạm vi và cách đọc

Ảnh Jira chỉ cung cấp tiêu đề SCRUM-83, không có mô tả/Acceptance Criteria đầy đủ. Bảng dưới dùng 12 điều kiện tại [Definition of Done W5](../plan/week-05.md#11-definition-of-done-w5) làm checklist evidence. Đây là inventory liên kết tới hồ sơ gốc, không phải lần chạy lại kiểm thử hay verdict Phase 09. Các kết quả cũ được gắn với revision/ngày chạy riêng; không ghép chúng thành một lần verification trên cùng SHA.

Code baseline `82fe708` là parent của commit evidence `f6a8ef0`; baseline này có source tích hợp tới PR #49. Một số evidence dưới đây được tạo trước `82fe708`; bảng giữ rõ giới hạn đó. Không có final W5 DoD package hoặc owner acceptance trên code baseline này.

## Đối chiếu 12 điều kiện DoD W5

| # | Điều kiện | Trạng thái evidence | Bằng chứng hiện có và phần còn thiếu |
| --- | --- | --- | --- |
| 1 | Feature matrix không còn hàng “Chưa có”; khác biệt còn lại được owner chấp nhận | `PARTIAL` | [Feature-gap matrix](../plan/week-05.md#3-hiện-trạng-và-khoảng-trống-phải-đóng) và [browser report M15](../sdd/modules/m15-product-web/evidence/scrum-74-76/integration-report.md) ghi các hành trình/API chưa hỗ trợ hoặc còn read-only. Chưa có record chấp nhận các gap còn lại. |
| 2 | Local mode khởi động sạch; ba role hoàn tất critical journey | `PARTIAL` | [M16 G0](../sdd/modules/m16-monolith-runtime/evidence/w5-g0-2026-10-15/W5-G0.md) có wheel boot và browser smoke ở baseline; [M15 integration](../sdd/modules/m15-product-web/evidence/scrum-74-76/integration-report.md) có role/route matrix. Chưa có lần chạy mọi critical journey trên một final SHA. |
| 3 | Wheel sạch; SQLite, blob store, worker và model readiness phản ánh đúng trạng thái | `PARTIAL` | M16 G0, [SCRUM-65](../sdd/modules/m16-monolith-runtime/evidence/scrum-65/integration-report.md), [SCRUM-66](../sdd/modules/m11-identity-account/evidence/scrum-66/review.md) và [SCRUM-67](../sdd/modules/m14-billing-licensing/evidence/scrum-67/verification.md) có kiểm tra task-local. Môi trường/revision khác nhau; chưa có gói final tích hợp chứng minh toàn bộ điều kiện cùng lúc. |
| 4 | Pipeline thật chạy ít nhất một audio có quyền, có model/version/provenance | `EVIDENCE_PRESENT — giới hạn rõ` | [W6-S03 / SCRUM-80](../sdd/modules/m09-trust-layer/evidence/w6-s03-real-pipeline.md) ghi một audio TTS do macOS tạo, hash và phiên bản model, chạy trên `cabcc44`. Đây là smoke kỹ thuật, không phải giọng người học hay đo độ chính xác CEFR; `NOT_MEASURED`/`NOT_EVALUATED` được giữ nguyên. |
| 5 | Migration/restore smoke PASS; report cũ đọc được | `PARTIAL` | [M16 G0](../sdd/modules/m16-monolith-runtime/evidence/w5-g0-2026-10-15/W5-G0.md) và [SCRUM-67 verification](../sdd/modules/m14-billing-licensing/evidence/scrum-67/verification.md) có migration/backup/restore evidence task-local. Chưa nối thành một kiểm tra final trên cùng SHA và chưa chứng minh mọi report cũ trong final environment. |
| 6 | Full suite, format, lint, wheel, secret scan, coverage PASS trên final revision | `OPEN` | Có kết quả task-local, nhưng chưa có một final gate bao trùm mọi tiêu chí trên `82fe708`. M16 G0 ghi format baseline `FAIL`; SCRUM-67 ghi global legacy format chưa đạt. Cần phân biệt changed-file checks với toàn repo và chạy lại theo W6-T01 khi có final candidate. |
| 7 | Browser desktop/mobile PASS cho public/student/teacher/admin | `PARTIAL` | [M15 integration report](../sdd/modules/m15-product-web/evidence/scrum-74-76/integration-report.md) có các route/viewport và screenshot trên revision `0827b37`; báo cáo cũng liệt kê interaction, accessibility và security cases chưa chạy. Chưa phải browser matrix trên `82fe708`/final candidate. |
| 8 | Không còn finding BLOCKER/MAJOR hoặc risk được owner chấp nhận | `OPEN` | Các report task-local có giới hạn và mục chờ reviewer/owner; chưa có một disposition tổng hợp và không có record accepted-risk cuối cho W5. |
| 9 | README/run guide/env/API inventory/evidence manifest khớp code | `PARTIAL` | Có run guide và manifest theo module; các status/evidence ở M11–M16 chưa đồng bộ hoàn toàn với task-local results. Đây là đầu vào trực tiếp cho SCRUM-84, không nên tự suy ra từ PR đã merge. |
| 10 | AI Prompt Log W05 của từng người đúng ngày/công việc | `PRESENT — completeness not rechecked` | Workbook W05 có trong repo; lượt rà SCRUM-83 này chưa kiểm tra từng sheet và từng dòng với lịch sử sử dụng AI. |
| 11 | SDD/status phản ánh thực tế, không tự ghi approval/acceptance | `PARTIAL` | [W6-S02 sync M09](../sdd/modules/m09-trust-layer/evidence/w6-s02-sync.md), M10/M12/M13 có cập nhật status; M11/M14/M16 và global phase vẫn còn `DRAFT`/`PENDING` hoặc task-local trạng thái khác nhau. Cần tiếp tục qua SCRUM-84, không đổi verdict thay owner. |
| 12 | Chủ dự án review package cuối và đưa verdict | `PENDING` | Chưa thấy verdict nghiệm thu W5. Theo DoD, trạng thái W5 vẫn `PENDING` trước verdict, kể cả khi từng kiểm tra kỹ thuật có kết quả tốt. |

## Blocker traceability

Ảnh chủ dự án cung cấp ghi SCRUM-83 là `W6-T02 — Bằng chứng nền tảng của DoD W5`. Primary checkout có file local chưa được Git theo dõi `docs/plan/week-06.md` ở trạng thái `DRAFT`, trong đó W6-T02 được mô tả là backend task closeout; file này không thuộc code baseline `82fe708` hay task branch này. Nội dung Acceptance Criteria Jira chưa có trong tài liệu được cung cấp và chưa truy cập được từ phiên này. Vì vậy report này chỉ là inventory 12 điều kiện DoD theo tiêu đề trong ảnh; không dùng nó để đóng một backend task khác hoặc tuyên bố W5 đạt DoD. Cần chốt mapping SCRUM-83 ↔ W6-T02 trước verdict task.

## Kết luận task-local

Evidence baseline đã được tập hợp và các revision/giới hạn được nêu rõ. Kết quả này **không** chứng minh W5 đạt DoD: các điều kiện 6, 8, 9 và 12 còn mở; một số điều kiện khác mới có evidence trên revision cũ hoặc từng task riêng. Không cập nhật Jira, không đổi SDD phase và không đánh dấu W5 `DONE` trong report này.
