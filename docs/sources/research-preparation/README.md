# SCRUM-88 — tài liệu đề, rubric và kế hoạch thu

**Nguồn:** `D:\LAPTRINH\TLCN\AI\ai-assessor-cefr`, tài liệu khảo sát tại HEAD `7614f3d9eec3b2673614b3ca6c4de8d3097221d3`, source code recheck tại `09b4e8d68d46b87a7219bfb009118d29b515c6c7`. Xem [tài liệu SCRUM-88 đã triển khai](SCRUM-88-materials.md). Chủ dự án xác nhận ngày 25/10/2026 GVHD đã đồng ý duyệt, chủ dự án được ủy quyền chốt; không cần biên bản riêng.

Đã đối chiếu thêm `origin/main` `09b4e8d`: chỉ có dòng D057 về giá, không liên quan; C001/C002 và các tài liệu task không đổi. Bản sao ghim theo local source HEAD `7614f3d`.

| File được chuyển nguyên trạng | SHA-256 | Phần liên quan |
|---|---|---|
| `KE_HOACH_KHAO_SAT.md` ← `docs/plan/KE_HOACH_KHAO_SAT.md` | `AF4787121BC0228C69D8FB4BF7CBB63D4DF8D3DBBEB85ACBAC955C896BB66964` | Hai prompt ứng viên, khung phiếu 5 tiêu chí, timing và kế hoạch thu/pilot. |
| `06_cefr_A2_B1_B2_descriptor_map.md` ← `markdown/week_01/06_cefr_A2_B1_B2_descriptor_map.md` | `3617A055FBB74B53A1C59A1BEA8944DBB4E146F1BD7C8CA17493F0E8912E7047` | Descriptor 6 tiêu chí; toàn bộ mức còn `PROPOSED`. |
| `14_ALTE_speaking_grid_draft.md` ← `markdown/week_01/14_ALTE_speaking_grid_draft.md` | `B716DC7124CB438BBF323B4A5628052356CD1DEAB5CBD3167B7CCB46D0677FC1` | Blueprint đề thay thế, ghi rõ `DRAFT`. |
| `21_week1_decision_log.md` ← `markdown/week_01/21_week1_decision_log.md` | `7143EDA0D09E203B80E7087ED8A82A5CAE1D273D67D5A96551F31F82AA62CA70` | C001/C002 đang chặn G2/collection; G1 `NOT HELD`; các quyết định liên quan vẫn `PROPOSED`. |

## Căn cứ vận hành

`KE_HOACH_KHAO_SAT.md` là kế hoạch vận hành cho SCRUM-88: hai bài độc thoại, 30 giây chuẩn bị, 40–60 giây trả lời, rubric năm tiêu chí, mục tiêu 60–90 người (sàn 60), pilot 6–8 người riêng. Hai prompt của kế hoạch được seed vào local demo với task ID `demo-speaking` và `demo-speaking-opinion`.

`14_ALTE_speaking_grid_draft.md` và decision log W1 được giữ để truy vết, không thay thế gói vận hành SCRUM-88. Task này không mở Task C, không tuyên bố đo Interaction trên độc thoại và không đưa RQ6/paired-form reliability vào phân tích. C001/C002 lịch sử không chặn phần việc nằm ngoài phạm vi này; các dòng gốc vẫn được giữ nguyên.

## Kết quả đối chiếu lịch sử

Các tài liệu W1 từng có nhiều phương án và trạng thái chờ duyệt. Theo chỉ dẫn mới nhất của chủ dự án, dùng `KE_HOACH_KHAO_SAT.md` làm căn cứ vận hành cho task này; các phương án khác chỉ dùng làm provenance.

Target M05 đã được duyệt theo 5 tiêu chí và `Interaction=null/insufficient_evidence` cho độc thoại. Browser QA trước đó trên revision `82fe708` ghi `demo-speaking` không có mô tả; SCRUM-88 bổ sung hai prompt fixture và hướng dẫn rubric trực tiếp trên phiếu chấm.

Task này không tuyển người, không thu audio và không tạo dataset. Consent, danh sách người tham gia và lịch tập huấn là các bước phối hợp với SCRUM-87/89; dữ liệu thật chỉ được lưu ngoài Git theo kế hoạch.

## Recheck code-level source (HEAD `09b4e8d68d46b87a7219bfb009118d29b515c6c7`)

Repo nguồn hiện đồng bộ với `origin/main`; working tree chỉ còn thay đổi local ở file model không liên quan. Source code có task bank cụ thể, nhưng task IDs không khớp `demo-speaking` ở target:

| File nguồn được kiểm tra | SHA-256 | Nội dung |
|---|---|---|
| `src/aicefr/storage/task_repository.py` | `E9A20C5C95DFCD2C4D2722C325C805B8E80CE07191DD35298F6196121F129E9A` | Task P3/P4/P5, prompt version `v1`; P3/P4 40–60 giây, P5 120–300 giây. |
| `src/aicefr/contracts.py` | `A9035E4F3460DFE68AD7A35642FC95704A965778BD7A79FF61B817561C506DE4` | Rubric implementation có năm tiêu chí; `Interaction` không nằm trong enum. |
| `tests/test_tasks_and_admin.py` | `84322B881E77E1635CB8F66BD26395C3F813697DEFC8DF74C83D715D8FA12607` | Kiểm task catalog có prompt text và task versions. |

Không tìm thấy ID `demo-speaking` trong source repo; P3/P4/P5 là task bank của implementation nguồn. Hai prompt theo kế hoạch khảo sát được giữ thành task fixture riêng trên target, không tuyên bố chúng là mapping tương đương P3/P4/P5.

Target browser observation về mô tả `demo-speaking` trống được xử lý bằng hai prompt fixture có version và thời lượng rõ; data-dir cũ chỉ được cập nhật tại chỗ khi placeholder chưa có bài nộp, còn version đã dùng được giữ lịch sử và chuyển sang v2. [Báo cáo browser QA](../../sdd/modules/m13-learning-evidence/evidence/scrum-88/report.md) ghi rõ kết quả, giới hạn và ảnh chụp giao diện.
