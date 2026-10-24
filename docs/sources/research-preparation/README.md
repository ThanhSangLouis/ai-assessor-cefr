# SCRUM-88 source handoff

**Task:** SCRUM-88 / W6-N03 — Đề bài, rubric chấm, kế hoạch thu. **Disposition:** `REFERENCE_ONLY`; nội dung nguồn là phương án, chưa phải protocol/rubric đã duyệt.

Nguồn được sao chép byte-for-byte từ `D:\LAPTRINH\TLCN\AI\ai-assessor-cefr`, revision `7614f3d9eec3b2673614b3ca6c4de8d3097221d3`:

| File nguồn | SHA-256 | Phần liên quan |
| --- | --- | --- |
| `docs/plan/KE_HOACH_KHAO_SAT.md` | `AF4787121BC0228C69D8FB4BF7CBB63D4DF8D3DBBEB85ACBAC955C896BB66964` | Kế hoạch khảo sát, đề bài, rubric 5 tiêu chí, phụ lục prompt |
| `markdown/week_01/06_cefr_A2_B1_B2_descriptor_map.md` | `3617A055FBB74B53A1C59A1BEA8944DBB4E146F1BD7C8CA17493F0E8912E7047` | Descriptor sáu tiêu chí, mọi mức `PROPOSED`, cần GV Ngoại ngữ duyệt |
| `markdown/week_01/07_construct_evidence_matrix.md` | `FEF8922831C76CA9708DA9567FF459EF96FB428C2FE70E24A0DF3A267AFC1E8C` | Mapping task/evidence/proxy/insufficient evidence; `DRAFT` |
| `markdown/week_01/14_ALTE_speaking_grid_draft.md` | `B716DC7124CB438BBF323B4A5628052356CD1DEAB5CBD3167B7CCB46D0677FC1` | Blueprint đề, thời lượng, prompt equivalence và rating; `DRAFT` |
| `markdown/week_01/16_data_management_plan.md` | `15013EE57FC59D6D331BD3A96A2284B567CAF6D2D646BB1A47E6009FFE0C50DE` | DMP cho dữ liệu và quy trình thu; `DRAFT` |
| `markdown/week_01/17_consent_requirements.md` | `BE483730FFDE5F1057887D16D8153BE6E50D754096E74A32D4EBDF5096689A96` | Nội dung consent, withdrawal và checkbox tối thiểu; `DRAFT` |
| `markdown/week_01/27_human_activity_runbook.md` | `6BB6F394665D0DA59133DA95722B690BB3BE95D8149839F5243986227852CD11` | Agenda workshop rubric, ethics review, role/approval evidence; hoạt động `NOT STARTED` |
| `markdown/week_01/28_ai_pedagogical_pre_review.md` | `493E95A97A82BBCCCAE827004AB5DD8C9F2CF60C39475CE45071682D32F543ED` | AI pre-review, không phải duyệt của GV; nêu các vấn đề anchor/pilot/rater |

## Kết quả đối chiếu và phần còn thiếu

Bản nháp gom prompt, form rating người chấm và kế hoạch thu nằm tại [SCRUM-88-draft-deliverables.md](SCRUM-88-draft-deliverables.md). Trạng thái `DRAFT`; các mâu thuẫn timing/criteria/scale và chốt của owner/GVHD vẫn mở.

- Có hai câu prompt cụ thể trong Appendix C của kế hoạch khảo sát, nhưng chưa có prompt ID/version, form được duyệt, blueprint equivalence hay bằng chứng usability/pilot.
- Có xung đột nội bộ về thời lượng: kế hoạch khảo sát/Appendix C đặt 40–60 giây; ALTE grid draft đề xuất Task A 90–120 giây và Task B khoảng 120 giây. Cần chốt một protocol trước khi cấu hình `demo-speaking` hoặc thu dữ liệu.
- Rubric cũng chưa thống nhất: Appendix B dùng 5 tiêu chí cho hai bài độc thoại; descriptor map/ALTE grid mô tả 6 tiêu chí gồm Interaction và đề xuất Task C. Repo dự án M05 hiện dùng 5 tiêu chí, Interaction null cho độc thoại. Cần chốt rubric, task coverage và version với owner/GVHD; không chuyển các ngưỡng từ tài liệu nguồn thành requirement tự động.
- Descriptor map và construct matrix là `DRAFT`; AI pre-review ghi rõ chưa có anchor người thật, ranh giới band chưa chuẩn hóa, Task C chưa pilot và nhận xét của AI không phải phê duyệt chuyên môn.
- DMP/consent và runbook cho collection vẫn chưa được phê duyệt/thực hiện. Chưa có evidence thu thử, ethics approval, ký consent hay prompt/rubric sign-off.
- M05 đã được duyệt cho scope trước đó; approval đó không đồng nghĩa rubric Speaking mới trong bộ hồ sơ nguồn đã được thẩm định.

UI local trên revision `82fe708` liệt kê `demo-speaking / 1` với thời lượng `40.0–60.0 giây`, nhưng mô tả đề trống và trang upload vẫn hiện placeholder. Đây là gap chỉ khi AC yêu cầu prompt được cấu hình/hiển thị trên web; task chưa có AC được cung cấp để kết luận. Phiếu chấm chưa được phân công không tự làm ticket tài liệu này thất bại.

QA cục bộ trên revision `82fe708` cho thấy task page có mô tả đề trống; chưa đủ nội dung để đối chiếu prompt/rubric được duyệt.

Repo nguồn có một thay đổi local không liên quan tại `src/aicefr/scoring/models/ridge_resp_v2.json`; file đó không được mở hay chuyển.
