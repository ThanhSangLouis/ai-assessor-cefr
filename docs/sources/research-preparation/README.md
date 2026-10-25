# SCRUM-89 — đối chiếu nguồn cho tập huấn hai người chấm

**Nguồn:** `D:\LAPTRINH\TLCN\AI\ai-assessor-cefr`, HEAD `7614f3d9eec3b2673614b3ca6c4de8d3097221d3` (24/10/2026). **Disposition:** `REFERENCE_ONLY`; chưa có bằng chứng tập huấn/calibration hoàn tất.

| File được chuyển nguyên trạng | SHA-256 | Phần liên quan |
|---|---|---|
| `KE_HOACH_KHAO_SAT.md` ← `docs/plan/KE_HOACH_KHAO_SAT.md` | `AF4787121BC0228C69D8FB4BF7CBB63D4DF8D3DBBEB85ACBAC955C896BB66964` | Đề xuất 10 bài chuẩn; weighted kappa ≥ 0,70 và ICC(2,1) ≥ 0,75. |
| `06_cefr_A2_B1_B2_descriptor_map.md` ← `markdown/week_01/06_cefr_A2_B1_B2_descriptor_map.md` | `3617A055FBB74B53A1C59A1BEA8944DBB4E146F1BD7C8CA17493F0E8912E7047` | Descriptor phục vụ đào tạo; `PROPOSED`. |
| `14_ALTE_speaking_grid_draft.md` ← `markdown/week_01/14_ALTE_speaking_grid_draft.md` | `B716DC7124CB438BBF323B4A5628052356CD1DEAB5CBD3167B7CCB46D0677FC1` | Rater/blind-rating procedure; `DRAFT`. |
| `21_week1_decision_log.md` ← `markdown/week_01/21_week1_decision_log.md` | `7143EDA0D09E203B80E7087ED8A82A5CAE1D273D67D5A96551F31F82AA62CA70` | D007 (2 rater + adjudicator) vẫn `PROPOSED`; G1 `NOT HELD`. |
| `22_G1_review_minutes.md` ← `markdown/week_01/22_G1_review_minutes.md` | `CBF3149FD41A82D9BCAF6BC1DCB4C5C5C734E19B2D0BA495791ECDB17FB34A5A` | Biên bản trống; cuộc họp ghi `NOT HELD`. |
| `25_G1_review_pack.md` ← `markdown/week_01/25_G1_review_pack.md` | `022F8BB6D194451E7516EC9A16C84E3C11D30B115AF1998351709D359E920606` | Gate `NOT HELD`, roster `NOT STARTED`. |
| `27_human_activity_runbook.md` ← `markdown/week_01/27_human_activity_runbook.md` | `6BB6F394665D0DA59133DA95722B690BB3E95D8149839F5243986227852CD11` | Checklist/agenda; human activity `NOT STARTED`. |
| `28_ai_pedagogical_pre_review.md` ← `markdown/week_01/28_ai_pedagogical_pre_review.md` | `493E95A97A82BBCCCAE827004AB5DD8C9F2CF60C39475CE45071682D32F543ED` | AI pre-review only; không phải human approval; gợi ý dry run 4–6 bài. |

## Kết quả đối chiếu

Không tìm thấy training manual/slide đã duyệt, audio/anchor có quyền dùng, roster hai rater thật, attendance, phiếu điểm, agreement result, remediation hay sign-off. Runbook mới là quy trình chuẩn bị; không chứng minh hoạt động đã diễn ra.

Các candidate calibration còn khác nhau: kế hoạch khảo sát đề xuất 10 bài và ngưỡng weighted kappa/ICC; đề cương v3.1 đề xuất 12–15 bài tập, QWK < 0,60 là stop gate. Dry run 4–6 bài để kiểm tải vận hành là một mục đích khác. Owner/GVHD cần chọn protocol, rubric/version, anchor và ngưỡng trước khi tập huấn thật.

Trang chấm mù trên target ở revision `82fe708` không có phiếu được phân công nên chưa kiểm được quy trình hai rater trên web. Đây là dependency UI riêng; không chứng minh hoạt động tập huấn offline đã/không diễn ra. Không tuyên bố đạt reliability khi chưa có phép đo thực tế.
