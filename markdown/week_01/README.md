# Xây dựng hệ thống AI hỗ trợ đánh giá năng lực nói tiếng Anh theo CEFR cho sinh viên đại học Việt Nam ở trình độ A2-B2

## Bộ hồ sơ công việc tuần 1

Bộ hồ sơ này tách lộ trình tuần 1 thành 24 artifact bắt buộc đánh số `00`-`23`. Thực hiện theo thứ tự số; cập nhật trạng thái và decision log hằng ngày. Các file `24-28` là QA, pre-read, synthetic test, runbook và AI pre-review bổ sung; không file nào thay biên bản/sign-off G1.

## Trạng thái hiện tại ngày 12/09/2026

- Desk research và rà soát chéo tài liệu đã được làm lại; các phần có thể chuẩn bị trước được giữ ở trạng thái `DRAFT`.
- Descriptor sorting, familiarisation quiz, workshop Pedagogy Lab, xác nhận nhân sự, ethics review và họp G1 **chưa có bằng chứng thực hiện**.
- G1 hiện là `NOT HELD`; package W2/W3 chỉ được chuẩn bị ở trạng thái draft, chưa phải công việc đã human-approved.
- D001 và các quyết định vận hành D017-D019 đã được người dùng xác nhận. Các lựa chọn construct, task, rater, mẫu và thống kê D002-D016 vẫn theo trạng thái `PROPOSED` trong `21_week1_decision_log.md`.
- Git baseline `c0ddd8a` trên branch `main` đã thay blocker repository; lịch sử trước baseline không được coi là đã phục hồi.

## Thứ tự nguồn chuẩn

1. Yêu cầu hiện tại của người dùng và `AGENTS.md`.
2. Quyết định `APPROVED` trong `21_week1_decision_log.md`.
3. Specification tuần 1 đã được người có thẩm quyền duyệt.
4. `../De_cuong_AI_Assessor_CEFR_v3.1_ALDM-L.md` chỉ là tài liệu tổng hợp kỹ thuật; chỗ nào mâu thuẫn với decision log phải được ghi là conflict, không tự chọn.

## Cách sử dụng

1. Bắt đầu từ lịch `00` và glossary `01`.
2. Hoàn thành familiarisation `02-04` trước khi chốt construct.
3. Duyệt construct và evidence `05-08` với giảng viên Ngoại ngữ.
4. Chốt scope/research `09-13`.
5. Hoàn thiện specification/governance `14-19`.
6. Viết, ghi quyết định và họp G1 bằng `20-22`.
7. Chỉ mở backlog `23` sau khi G1 pass hoặc conditional pass có deadline.
8. Không đổi `PROPOSED` thành `APPROVED`, không điền kết quả hoạt động và không ghi tên người duyệt nếu chưa có bằng chứng thực tế.

## Danh sách file

- [00_week1_schedule](00_week1_schedule.md)
- [01_glossary](01_glossary.md)
- [02_source_reading_log](02_source_reading_log.md)
- [03_descriptor_sorting_result](03_descriptor_sorting_result.md)
- [04_cefr_familiarisation_check](04_cefr_familiarisation_check.md)
- [05_construct_definition](05_construct_definition.md)
- [06_cefr_A2_B1_B2_descriptor_map](06_cefr_A2_B1_B2_descriptor_map.md)
- [07_construct_evidence_matrix](07_construct_evidence_matrix.md)
- [08_open_questions_for_pedagogy_lab](08_open_questions_for_pedagogy_lab.md)
- [09_scope_and_intended_use](09_scope_and_intended_use.md)
- [10_target_population](10_target_population.md)
- [11_claims_and_nonclaims](11_claims_and_nonclaims.md)
- [12_research_questions_v1](12_research_questions_v1.md)
- [13_definition_of_done](13_definition_of_done.md)
- [14_ALTE_speaking_grid_draft](14_ALTE_speaking_grid_draft.md)
- [15_validation_argument_map](15_validation_argument_map.md)
- [16_data_management_plan](16_data_management_plan.md)
- [17_consent_requirements](17_consent_requirements.md)
- [18_RACI](18_RACI.md)
- [19_risk_register](19_risk_register.md)
- [20_chapter_1_draft](20_chapter_1_draft.md)
- [21_week1_decision_log](21_week1_decision_log.md)
- [22_G1_review_minutes](22_G1_review_minutes.md)
- [23_week2_backlog](23_week2_backlog.md)
- [24_week1_rebuild_review](24_week1_rebuild_review.md) — báo cáo kiểm tra, không thuộc bộ đầu ra G1 bắt buộc
- [25_G1_review_pack](25_G1_review_pack.md) — gói pre-read và ma trận hoàn thành, không thay sign-off
- [26_synthetic_dmp_test_report](26_synthetic_dmp_test_report.md) — kết quả kiểm tra DMP bằng dữ liệu synthetic
- [27_human_activity_runbook](27_human_activity_runbook.md) — kịch bản chạy các hoạt động cần người thật
- [28_ai_pedagogical_pre_review](28_ai_pedagogical_pre_review.md) — nhận xét sư phạm của AI để hỗ trợ G1, không thay human approval

## Trạng thái chuẩn

- `DRAFT`: đang soạn.
- `IN REVIEW`: đã gửi người duyệt.
- `REVISE`: cần sửa.
- `APPROVED`: được dùng làm đầu vào tuần sau.
- `SUPERSEDED`: đã có phiên bản thay thế.

Trạng thái hoạt động dùng riêng: `NOT STARTED`, `IN PROGRESS`, `COMPLETED`, `BLOCKED`. Trạng thái cổng dùng riêng: `NOT HELD`, `PASS`, `CONDITIONAL PASS`, `FAIL`. Không dùng các trạng thái này để thay thế approval của tài liệu.
