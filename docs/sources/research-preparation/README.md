# SCRUM-89 source handoff

**Task:** SCRUM-89 / W6-N04 — Tập huấn hai người chấm. **Disposition:** `REFERENCE_ONLY`; quy trình trong nguồn là đề xuất, chưa phải gói tập huấn được duyệt.

Nguồn được sao chép byte-for-byte từ `D:\LAPTRINH\TLCN\AI\ai-assessor-cefr`, revision `7614f3d9eec3b2673614b3ca6c4de8d3097221d3`:

| File nguồn | SHA-256 | Phần liên quan |
| --- | --- | --- |
| `docs/plan/KE_HOACH_KHAO_SAT.md` | `AF4787121BC0228C69D8FB4BF7CBB63D4DF8D3DBBEB85ACBAC955C896BB66964` | Section 6.2: đề xuất chấm thử 10 bài và weighted kappa ≥ 0.70 |
| `markdown/week_01/06_cefr_A2_B1_B2_descriptor_map.md` | `3617A055FBB74B53A1C59A1BEA8944DBB4E146F1BD7C8CA17493F0E8912E7047` | Rubric descriptor sáu tiêu chí để làm tài liệu đào tạo; `DRAFT` |
| `markdown/week_01/07_construct_evidence_matrix.md` | `FEF8922831C76CA9708DA9567FF459EF96FB428C2FE70E24A0DF3A267AFC1E8C` | Cơ sở evidence/task và giới hạn chấm; `DRAFT` |
| `markdown/week_01/14_ALTE_speaking_grid_draft.md` | `B716DC7124CB438BBF323B4A5628052356CD1DEAB5CBD3167B7CCB46D0677FC1` | Đề xuất rating protocol, hai rater và phân xử; `DRAFT` |
| `markdown/week_01/16_data_management_plan.md` | `15013EE57FC59D6D331BD3A96A2284B567CAF6D2D646BB1A47E6009FFE0C50DE` | Điều kiện quyền truy cập/rating audio và bảo vệ dữ liệu; `DRAFT` |
| `markdown/week_01/17_consent_requirements.md` | `BE483730FFDE5F1057887D16D8153BE6E50D754096E74A32D4EBDF5096689A96` | Yêu cầu consent và quyền dùng dữ liệu; `DRAFT` |
| `markdown/week_01/27_human_activity_runbook.md` | `6BB6F394665D0DA59133DA95722B690BB3BE95D8149839F5243986227852CD11` | Checklist chỉ định rater, human workshop, sign-off và stop conditions; hoạt động `NOT STARTED` |
| `markdown/week_01/28_ai_pedagogical_pre_review.md` | `493E95A97A82BBCCCAE827004AB5DD8C9F2CF60C39475CE45071682D32F543ED` | AI pre-review về anchors, dry run và rater workload; không phải human approval |

## Kết quả đối chiếu và phần còn thiếu

- Kế hoạch chỉ định 10 bài mẫu đồng thuận trước và ngưỡng weighted kappa ≥ 0,70 để đủ điều kiện bắt đầu chấm. Mốc này là đề xuất nguồn, chưa thấy chủ task/GVHD phê duyệt.
- AI pre-review đề xuất dry run 4–6 bài để đo thời gian, bất đồng và tải nhận thức; cần phân biệt dry run vận hành này với bộ 10 bài calibration, chốt mục đích và acceptance cho từng bộ.
- Runbook yêu cầu xác nhận chuyên môn, lịch, conflict of interest, độc lập khỏi AI output và approval reference của Rater 1/2/Adjudicator. Hoạt động trong runbook vẫn `NOT STARTED`; không có dấu vết hai rater thật đã nhận lịch/tập huấn.
- Chưa thấy training manual/slide, bộ mẫu có quyền dùng và answer key chuẩn, phiếu ghi điểm độc lập, phép tính agreement, kết quả đạt/chưa đạt, quy trình huấn luyện lại hoặc sign-off. DMP/consent vẫn `DRAFT`; quyền dùng các audio mẫu cần được xác nhận.
- Descriptor map/ALTE grid gồm 6 tiêu chí, trong khi Appendix B của kế hoạch chấm độc thoại ghi 5 tiêu chí. Chốt rubric/version trước khi dùng làm giáo trình tập huấn.

Trang chấm mù trên revision `82fe708` hiển thị “Chưa có phiếu chấm” vì chưa có đợt được phân công; đó là trạng thái demo, không phải bằng chứng task thiếu nếu tập huấn được làm offline. Nếu nghiệm thu yêu cầu hai tài khoản thực hành chấm độc lập trên web, dependency này chưa đáp ứng: M12 còn `DRAFT/PENDING`, M07 hiện có thể lộ AI result. Không dùng đề xuất nguồn để tuyên bố đã hoàn thành tập huấn hay đạt ngưỡng reliability.

QA cục bộ trên revision `82fe708` cho thấy chưa có phiếu được phân công; chưa thể kiểm thử hai người chấm.

Repo nguồn có một thay đổi local không liên quan tại `src/aicefr/scoring/models/ridge_resp_v2.json`; file đó không được mở hay chuyển.

## Draft deliverables cho task

| Artifact | Trạng thái | Mục đích |
|---|---|---|
| [SCRUM-89-training-packet-draft.md](SCRUM-89-training-packet-draft.md) | `DRAFT — NOT APPROVED — NOT RUN` | Gate, agenda facilitator, tách dry run 4–6 mẫu khỏi calibration 10 mẫu và danh sách quyết định cần owner/GVHD chốt. |
| [SCRUM-89-calibration-evidence-template.md](SCRUM-89-calibration-evidence-template.md) | Mẫu trống · `NOT_RUN` | Ghi preflight, dry run, calibration, chỉ số sau khi tính thực tế và sign-off; không chứa dữ liệu cá nhân/audio. |

Các draft này chưa đóng task: rubric/version, bộ audio có quyền dùng, answer key, rater thật, blind workflow và metric/threshold vẫn `PENDING`/`NOT_VERIFIED`. M07/M12 status không được thay đổi.
