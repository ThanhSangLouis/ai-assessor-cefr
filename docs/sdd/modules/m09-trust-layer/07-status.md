# M09 — Status

| Mục | Trạng thái |
| --- | --- |
| Lifecycle | proposed |
| Phase hiện tại | 01 — Requirement review |
| Requirement | v0.1 DRAFT · user verdict PENDING |
| Research mode | RUN đề xuất · user decision PENDING |
| Research/Specification/Test Plan/Plan/Tasks | v0.1 planning packet DRAFT; chưa có hiệu lực phase |
| Implementation | CODE_MERGED trên `main` (PR #40, theo chỉ dẫn trực tiếp của user; đồng bộ 21/10/2026) |
| Review/Verification/Acceptance | PENDING — reviewer/user chưa ghi verdict |
| Prompt hiện hành | NONE ISSUED |

Các artifact 02–06 được chuẩn bị đồng thời theo yêu cầu lập kế hoạch chi tiết, nhưng không thay thứ tự phê duyệt. Chỉ phát prompt/implement sau khi Phase 01, 03, 04 và 05 lần lượt được user `APPROVED`.

## W5-G1 / SCRUM-63 ngày 15/10/2026

User yêu cầu thực hiện thay Sang; [contract đối chiếu](W5-G1-parity-contract.md) giữ reference40907cc và invariant của repo nhóm. Technical criteria đã ghi rõ; Jira đang Testing, user/reviewer verdict PENDING. Việc này không tự phê duyệt global M09 hoặc đổi Jira Done.

## SCRUM-69 — Implementation theo chỉ dẫn trực tiếp

User yêu cầu thực hiện thay Sang, tài khoản/tác giả commit Sang và log sheet Sang trong repo chính. G1 contract PR39 đã tạo trước S01; actual branch base9748814, sourcebased60e8a4 (600test PASS đã đo ở T03/source giống nhau). Historical target3b2d2b7, referenceSang40907cc giữ cố định.

Ba Luna lane domain/conformal/integration đã nhận [prompt A1](prompts/SCRUM-69-prompt-log.md). Global artifacts vẫn DRAFT/PENDING, local implementation theo quyền user; Nguyên UI/reviewer/user acceptance PENDING. T04 đang giữ checkpoint riêng, không gộp thay đổi dở.

### SCRUM-69 — Task-local verification 15/10/2026

Code `34da102`: full780PASS, no skips,2smoke deselected; statement90.8241%,branch80.1893%; Ruff/changed-format/build đạt. Wheel sạch byte-match104/104, browser65checksPASS desktop/mobile, real ASR/VAD/model2audioPASS và restart đọc reportPASS. Xem [final verification](evidence/scrum-69/final-verification.md) và [root review](reviews/SCRUM-69-review.md). User đã yêu cầu thực thi và tạo PR từng task; không thay global phase DRAFT hoặc tự ghi acceptance/JiraDone. Reviewer/user verdict PENDING.

## Đồng bộ W6-S02 / SCRUM-79 — 21/10/2026

Code của module đã merge vào `main` qua PR #40 (SCRUM-69, merge `a4c119f`) theo chỉ dẫn trực tiếp của user, trong khi verdict Phase 01–05 vẫn PENDING. Bảng task đã cập nhật trạng thái code ([06-tasks](06-tasks.md)); chạy lại test trên `main` `cabcc44`: 171 passed ([bằng chứng](evidence/w6-s02-sync.md)). Lần đồng bộ này không đổi phase, không ghi APPROVED/DONE; review, verification và acceptance chờ reviewer/user.

## W7-S02 — Chuyển M09 sang kiến trúc ba dịch vụ (25/10/2026)

- PR `port/m03-m05-m09-cham` vào nhánh tích hợp `migrate/w7-repo-goc`, xếp trên PR nền `port/m16-nen-w7` (W7-T01). Người làm: Sang. Chưa có verdict.
- Kết quả test ghi trong mô tả PR. Lý do: trên riêng nhánh tích hợp, test chưa chạy được cho tới khi mọi module đã chuyển, nên kết quả được đo bằng cách phủ tạm phần của người khác từ repo gốc.
- Không có số đo Speak & Improve trong code, test hay tài liệu của PR.
