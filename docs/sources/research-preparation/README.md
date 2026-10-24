# SCRUM-87 source handoff

**Task:** SCRUM-87 / W6-N02 — Phiếu đồng thuận giấy khớp hệ thống. **Disposition:** `REFERENCE_ONLY`, chưa phải approval hay consent form hoàn chỉnh.

Nguồn được sao chép byte-for-byte từ `D:\LAPTRINH\TLCN\AI\ai-assessor-cefr`, revision `7614f3d9eec3b2673614b3ca6c4de8d3097221d3`:

| File nguồn | SHA-256 | Liên quan |
| --- | --- | --- |
| `docs/plan/KE_HOACH_KHAO_SAT.md` | `AF4787121BC0228C69D8FB4BF7CBB63D4DF8D3DBBEB85ACBAC955C896BB66964` | Appendix A: nội dung consent rút gọn và đề xuất lựa chọn sử dụng audio/nghiên cứu |
| `markdown/week_01/17_consent_requirements.md` | `BE483730FFDE5F1057887D16D8153BE6E50D754096E74A32D4EBDF5096689A96` | Checklist consent; nguồn ghi rõ `DRAFT` |

Tài liệu nguồn không chứng minh đã có phiếu hoàn chỉnh, duyệt GVHD/đạo đức hay consent của người tham gia. UI ở revision `82fe708` có đồng ý theo version và checkbox opt-in nghiên cứu dữ liệu tổng hợp, nhưng không có lựa chọn riêng về lưu audio. Không dùng các file này để mở thu thập dữ liệu.

QA cục bộ trên revision `82fe708`: consent đổi trạng thái khi accept/withdraw; sau withdraw, upload bị API chặn với `403 CONSENT_VERSION_STALE`. Đây là quan sát demo, không phải verdict nghiệm thu.

Repo nguồn có một thay đổi local không liên quan tại `src/aicefr/scoring/models/ridge_resp_v2.json`; file đó không được mở hay chuyển.
