# SCRUM-88 — đối chiếu nguồn cho đề, rubric và kế hoạch thu

**Nguồn:** `D:\LAPTRINH\TLCN\AI\ai-assessor-cefr`, HEAD `7614f3d9eec3b2673614b3ca6c4de8d3097221d3` (24/10/2026). **Disposition:** `REFERENCE_ONLY`; chưa có protocol/rubric đã duyệt.

Đã đối chiếu thêm `origin/main` `09b4e8d`: chỉ có dòng D057 về giá, không liên quan; C001/C002 và các tài liệu task không đổi. Bản sao ghim theo local source HEAD `7614f3d`.

| File được chuyển nguyên trạng | SHA-256 | Phần liên quan |
|---|---|---|
| `KE_HOACH_KHAO_SAT.md` ← `docs/plan/KE_HOACH_KHAO_SAT.md` | `AF4787121BC0228C69D8FB4BF7CBB63D4DF8D3DBBEB85ACBAC955C896BB66964` | Hai prompt ứng viên, khung phiếu 5 tiêu chí, timing và kế hoạch thu/pilot. |
| `06_cefr_A2_B1_B2_descriptor_map.md` ← `markdown/week_01/06_cefr_A2_B1_B2_descriptor_map.md` | `3617A055FBB74B53A1C59A1BEA8944DBB4E146F1BD7C8CA17493F0E8912E7047` | Descriptor 6 tiêu chí; toàn bộ mức còn `PROPOSED`. |
| `14_ALTE_speaking_grid_draft.md` ← `markdown/week_01/14_ALTE_speaking_grid_draft.md` | `B716DC7124CB438BBF323B4A5628052356CD1DEAB5CBD3167B7CCB46D0677FC1` | Blueprint đề thay thế, ghi rõ `DRAFT`. |
| `21_week1_decision_log.md` ← `markdown/week_01/21_week1_decision_log.md` | `7143EDA0D09E203B80E7087ED8A82A5CAE1D273D67D5A96551F31F82AA62CA70` | C001/C002 đang chặn G2/collection; G1 `NOT HELD`; các quyết định liên quan vẫn `PROPOSED`. |

## Kết quả đối chiếu

Không tìm thấy prompt bank, rubric/rating sheet hay collection plan đã được phê duyệt. Tài liệu survey có nội dung cụ thể nhưng không có version/approval record. Hai phương án nguồn còn mâu thuẫn: 40–60 giây và 5 tiêu chí so với 90–120/120 giây, 6 tiêu chí gồm Interaction. Decision log yêu cầu xử lý C001/C002 trước khi chốt Task C hoặc thu dữ liệu.

Target M05 hiện được duyệt theo 5 tiêu chí và `Interaction=null/insufficient_evidence` cho độc thoại. Browser QA trước đó trên revision `82fe708` ghi `demo-speaking` không có mô tả; chưa có phiếu được phân công nên không thể kiểm rubric trên UI. Hai quan sát này không tự xác định acceptance nếu chưa có AC yêu cầu cấu hình web.

Còn thiếu quyết định owner/GVHD về prompt/version/timing, rubric/anchor, equivalence/usability pilot, population/sample và xử lý bài lỗi, consent/data handling, cùng bằng chứng phê duyệt. Không dùng các phương án nguồn làm yêu cầu đã duyệt.

## Recheck code-level source (HEAD `09b4e8d68d46b87a7219bfb009118d29b515c6c7`)

Repo nguồn hiện đồng bộ với `origin/main`; working tree chỉ còn thay đổi local ở file model không liên quan. Source code có task bank cụ thể, nhưng task IDs không khớp `demo-speaking` ở target:

| File nguồn được kiểm tra | SHA-256 | Nội dung |
|---|---|---|
| `src/aicefr/storage/task_repository.py` | `E9A20C5C95DFCD2C4D2722C325C805B8E80CE07191DD35298F6196121F129E9A` | Task P3/P4/P5, prompt version `v1`; P3/P4 40–60 giây, P5 120–300 giây. |
| `src/aicefr/contracts.py` | `A9035E4F3460DFE68AD7A35642FC95704A965778BD7A79FF61B817561C506DE4` | Rubric implementation có năm tiêu chí; `Interaction` không nằm trong enum. |
| `tests/test_tasks_and_admin.py` | `84322B881E77E1635CB8F66BD26395C3F813697DEFC8DF74C83D715D8FA12607` | Kiểm task catalog có prompt text và task versions. |

Không tìm thấy ID `demo-speaking` trong source repo. Các prompt P3/P4/P5 là dữ liệu implementation của repo nguồn; chưa có mapping được duyệt sang task khảo sát/ID target. Vì vậy không thay nội dung `demo-speaking` bằng một prompt tùy chọn khi chưa có prompt/version được owner/GVHD chốt. Hai prompt trong survey plan vẫn là ứng viên, không có sign-off.

Target browser observation trước đó về mô tả `demo-speaking` trống vẫn là gap của demo fixture. Nếu AC yêu cầu đề đã duyệt xuất hiện trên web thì cần mapping/version và owner approval trước khi cấu hình.
