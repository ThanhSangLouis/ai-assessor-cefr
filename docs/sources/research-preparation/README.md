# SCRUM-87 source handoff

**Task:** SCRUM-87 / W6-N02 — Phiếu đồng thuận giấy khớp hệ thống. **Disposition:** `REFERENCE_ONLY`, chưa phải approval hay consent form hoàn chỉnh.

Nguồn được sao chép byte-for-byte từ `D:\LAPTRINH\TLCN\AI\ai-assessor-cefr`, revision `7614f3d9eec3b2673614b3ca6c4de8d3097221d3`:

| File nguồn | SHA-256 | Liên quan |
| --- | --- | --- |
| `docs/plan/KE_HOACH_KHAO_SAT.md` | `AF4787121BC0228C69D8FB4BF7CBB63D4DF8D3DBBEB85ACBAC955C896BB66964` | Appendix A: nội dung consent rút gọn và đề xuất lựa chọn sử dụng audio/nghiên cứu |
| `markdown/week_01/17_consent_requirements.md` | `BE483730FFDE5F1057887D16D8153BE6E50D754096E74A32D4EBDF5096689A96` | Checklist consent; nguồn ghi rõ `DRAFT` |
| `markdown/week_01/16_data_management_plan.md` | `15013EE57FC59D6D331BD3A96A2284B567CAF6D2D646BB1A47E6009FFE0C50DE` | DMP về data inventory, roles, retention, withdrawal và approval; `DRAFT` |
| `markdown/week_01/26_synthetic_dmp_test_report.md` | `F25C8763BBC48598164EB606ED49236B35FC7F0C5688AEA975A900DD655CE114` | Kết quả kiểm DMP bằng synthetic; `COMPLETED WITH LIMITATIONS` |
| `markdown/week_01/27_human_activity_runbook.md` | `6BB6F394665D0DA59133DA95722B690BB3BE95D8149839F5243986227852CD11` | Quy trình human review consent/ethics, evidence và sign-off; hoạt động ghi `NOT STARTED` |

## Kết quả đối chiếu và phần còn thiếu

Bản dự thảo phiếu và bảng ánh xạ đã được chuẩn bị tại [SCRUM-87-consent-form-draft.md](SCRUM-87-consent-form-draft.md). Trạng thái vẫn `DRAFT / REFERENCE_ONLY`; cần chốt các mục mở và review mẫu trường/GVHD/ethics trước khi phát hành.

- Không tìm thấy phiếu giấy hoàn chỉnh hoặc dấu vết chữ ký/duyệt GVHD/ethics. Appendix A trong kế hoạch chỉ là bản rút gọn.
- Checklist consent và DMP đều `DRAFT`. DMP nói retention phải được ethics/GVHD chốt; mốc 12 tháng trong kế hoạch khảo sát chỉ là đề xuất, chưa phải chính sách có hiệu lực.
- Runbook yêu cầu chốt nơi lưu, encryption/key owner, role access, retention, withdrawal cutoff, contact và cloud/external API. Hoạt động W1 trong runbook vẫn `NOT STARTED`.
- Báo cáo synthetic chỉ kiểm một phần workflow: encryption-at-rest và role access `NOT TESTED`. Kết quả của repo nguồn không phải verification của repo dự án.
- UI ở revision `82fe708` có consent version/state và opt-in nghiên cứu dữ liệu tổng hợp, không có lựa chọn riêng về lưu audio. Cần quyết định field/checkbox nào là điều kiện để ghi âm/xử lý cho bài hiện tại và field nào cho tái sử dụng nghiên cứu; sau đó map từng lựa chọn sang giấy và UI.

Không dùng các file này để mở thu thập dữ liệu hoặc ghi nhận consent thật.

QA cục bộ trên revision `82fe708`: consent đổi trạng thái khi accept/withdraw; sau withdraw, upload bị API chặn với `403 CONSENT_VERSION_STALE`. Đây là quan sát demo, không phải verdict nghiệm thu.

Repo nguồn có một thay đổi local không liên quan tại `src/aicefr/scoring/models/ridge_resp_v2.json`; file đó không được mở hay chuyển.
