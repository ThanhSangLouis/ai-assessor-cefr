# Gói tài liệu nguồn và handoff theo task

## SCRUM-87 — đối chiếu nguồn cho phiếu đồng thuận giấy

**Nguồn:** `D:\LAPTRINH\TLCN\AI\ai-assessor-cefr`, HEAD `7614f3d9eec3b2673614b3ca6c4de8d3097221d3` (24/10/2026). **Disposition:** `REFERENCE_ONLY`; chưa có phiếu đã duyệt.

Đã đối chiếu thêm `origin/main` `09b4e8d` (nhánh nguồn đi trước 7 commit): các file consent liên quan không đổi và không có đầu ra consent mới.

| File được chuyển nguyên trạng | SHA-256 | Phần liên quan |
|---|---|---|
| `KE_HOACH_KHAO_SAT.md` ← `docs/plan/KE_HOACH_KHAO_SAT.md` | `AF4787121BC0228C69D8FB4BF7CBB63D4DF8D3DBBEB85ACBAC955C896BB66964` | Phụ lục A là nội dung consent rút gọn; §11 ghi phiếu ký duyệt là đầu ra dự kiến. |
| `17_consent_requirements.md` ← `markdown/week_01/17_consent_requirements.md` | `BE483730FFDE5F1057887D16D8153BE6E50D754096E74A32D4EBDF5096689A96` | Checklist nội dung; trạng thái `DRAFT`, không thay mẫu của trường. |
| `16_data_management_plan.md` ← `markdown/week_01/16_data_management_plan.md` | `15013EE57FC59D6D331BD3A96A2284B567CAF6D2D646BB1A47E6009FFE0C50DE` | Retention, quyền truy cập và xóa còn chờ duyệt; 12 tháng chỉ là đề xuất. |

### Kết quả đối chiếu

Không tìm thấy biểu mẫu giấy hoàn chỉnh, chữ ký hay phê duyệt ethics/GVHD trong repo nguồn. Không chuyển báo cáo test synthetic hoặc runbook vì chúng không phải nội dung cần có trong phiếu. Source plan ghi phiếu ký duyệt là việc sẽ làm ở W6, không phải kết quả đã có.

Target UI hiện có consent bắt buộc và lựa chọn nghiên cứu tùy chọn, nhưng chưa có lựa chọn lưu audio riêng. Browser QA trước đó trên revision `82fe708` ghi nhận trạng thái này; đây là đối chiếu giao diện, không phải phê duyệt consent.

Còn thiếu mẫu được trường/GVHD/ethics duyệt; câu chữ và phiên bản ánh xạ với UI; mục đích lưu/xử lý audio cho bài hiện tại so với tái sử dụng nghiên cứu; retention/xóa, chủ sở hữu và quyền truy cập; contact/khiếu nại; và bằng chứng sign-off. Không dùng tài liệu này để bắt đầu thu dữ liệu hoặc ghi nhận consent thật.

### Recheck code-level source (HEAD `09b4e8d68d46b87a7219bfb009118d29b515c6c7`)

Repo nguồn hiện đồng bộ với `origin/main`; working tree chỉ còn thay đổi local ở file model không liên quan. Nguồn có code consent tách hai lựa chọn, ngoài các tài liệu reference ở trên:

| File nguồn được kiểm tra | SHA-256 | Chức năng |
|---|---|---|
| `src/aicefr/api/templates/consent.html` | `3AA6EEBEE1EC0AC0EE7E4C774E96B1DBBF1EE5133F438BA28176974C48F02E97` | Hiển thị checkbox riêng cho lưu audio và tái sử dụng nghiên cứu. |
| `src/aicefr/api/static/consent.js` | `BE32F3947BD82CBDBB7EAED67E1102FBFC5FA70F00FFF987DF2839BF162DD686` | Gửi hai lựa chọn riêng lên API. |
| `src/aicefr/storage/consent_repository.py` | `185B423277B0FD021AF970E473DBFE0101AA33198F1A9E504046AC05F770ABFB` | Lưu/version hóa hai consent; `may_submit` phụ thuộc audio consent còn hiệu lực. |
| `tests/test_consent.py` | `9713A1B5B92F0E940BF57C93356EC0E2397B5A5E4EABEDBEBAF06666844A2369` | Test consent bằng test data. |

Đối chiếu target hiện tại: M08/M11 và WSGI consent chỉ có `research_allowed`, chưa có `audio_storage_allowed`. Source consent dùng FastAPI/Mongo; target dùng WSGI/SQLite và contract khác. Chưa chuyển code vì ticket hiện là phiếu giấy khớp implementation target, còn thêm lựa chọn audio vào target sẽ đổi consent contract/schema/API và cần scope/SDD owner review. Source UI là bằng chứng về lựa chọn ở **repo nguồn**, không phải trạng thái giao diện target.

Kết luận về biểu mẫu giữ nguyên: source code có hai lựa chọn, nhưng source vẫn không có phiếu giấy đã ký/được duyệt; phụ lục consent trong kế hoạch còn là đề xuất.

### Target branch follow-up — SCRUM-87 (25/10/2026)

The comparison above records the target state at its audit revision. The SCRUM-87
task branch subsequently added a target-side `audio_storage_allowed` consent
choice and linked a printable `consent-v2` form. No source-repository code was
copied into the target; the target contract and SQLite migration were implemented
for its WSGI/storage architecture. The current implementation and test/browser
evidence are recorded at
`docs/sdd/modules/m08-identity-storage-admin/evidence/scrum-87-implementation.md`.

The retention section remains explicit: the tracked data-management plan calls
12 months a proposal, and the app does not automatically erase stored audio.
This branch does not claim an approved retention policy or real-data collection.

---

## SCRUM-88 — tài liệu đề, rubric và kế hoạch thu

**Nguồn:** `D:\LAPTRINH\TLCN\AI\ai-assessor-cefr`, tài liệu khảo sát tại HEAD `7614f3d9eec3b2673614b3ca6c4de8d3097221d3`, source code recheck tại `09b4e8d68d46b87a7219bfb009118d29b515c6c7`. Xem [tài liệu SCRUM-88 đã triển khai](SCRUM-88-materials.md). Chủ dự án xác nhận ngày 25/10/2026 GVHD đã đồng ý duyệt, chủ dự án được ủy quyền chốt; không cần biên bản riêng.

Đã đối chiếu thêm `origin/main` `09b4e8d`: chỉ có dòng D057 về giá, không liên quan; C001/C002 và các tài liệu task không đổi. Bản sao ghim theo local source HEAD `7614f3d`.

| File được chuyển nguyên trạng | SHA-256 | Phần liên quan |
|---|---|---|
| `KE_HOACH_KHAO_SAT.md` ← `docs/plan/KE_HOACH_KHAO_SAT.md` | `AF4787121BC0228C69D8FB4BF7CBB63D4DF8D3DBBEB85ACBAC955C896BB66964` | Hai prompt ứng viên, khung phiếu 5 tiêu chí, timing và kế hoạch thu/pilot. |
| `06_cefr_A2_B1_B2_descriptor_map.md` ← `markdown/week_01/06_cefr_A2_B1_B2_descriptor_map.md` | `3617A055FBB74B53A1C59A1BEA8944DBB4E146F1BD7C8CA17493F0E8912E7047` | Descriptor 6 tiêu chí; toàn bộ mức còn `PROPOSED`. |
| `14_ALTE_speaking_grid_draft.md` ← `markdown/week_01/14_ALTE_speaking_grid_draft.md` | `B716DC7124CB438BBF323B4A5628052356CD1DEAB5CBD3167B7CCB46D0677FC1` | Blueprint đề thay thế, ghi rõ `DRAFT`. |
| `21_week1_decision_log.md` ← `markdown/week_01/21_week1_decision_log.md` | `7143EDA0D09E203B80E7087ED8A82A5CAE1D273D67D5A96551F31F82AA62CA70` | C001/C002 đang chặn G2/collection; G1 `NOT HELD`; các quyết định liên quan vẫn `PROPOSED`. |

### Căn cứ vận hành

`KE_HOACH_KHAO_SAT.md` là kế hoạch vận hành cho SCRUM-88: hai bài độc thoại, 30 giây chuẩn bị, 40–60 giây trả lời, rubric năm tiêu chí, mục tiêu 60–90 người (sàn 60), pilot 6–8 người riêng. Hai prompt của kế hoạch được seed vào local demo với task ID `demo-speaking` và `demo-speaking-opinion`.

`14_ALTE_speaking_grid_draft.md` và decision log W1 được giữ để truy vết, không thay thế gói vận hành SCRUM-88. Task này không mở Task C, không tuyên bố đo Interaction trên độc thoại và không đưa RQ6/paired-form reliability vào phân tích. C001/C002 lịch sử không chặn phần việc nằm ngoài phạm vi này; các dòng gốc vẫn được giữ nguyên.

### Kết quả đối chiếu lịch sử

Các tài liệu W1 từng có nhiều phương án và trạng thái chờ duyệt. Theo chỉ dẫn mới nhất của chủ dự án, dùng `KE_HOACH_KHAO_SAT.md` làm căn cứ vận hành cho task này; các phương án khác chỉ dùng làm provenance.

Target M05 đã được duyệt theo 5 tiêu chí và `Interaction=null/insufficient_evidence` cho độc thoại. Browser QA trước đó trên revision `82fe708` ghi `demo-speaking` không có mô tả; SCRUM-88 bổ sung hai prompt fixture và hướng dẫn rubric trực tiếp trên phiếu chấm.

Task này không tuyển người, không thu audio và không tạo dataset. Consent, danh sách người tham gia và lịch tập huấn là các bước phối hợp với SCRUM-87/89; dữ liệu thật chỉ được lưu ngoài Git theo kế hoạch.

### Recheck code-level source (HEAD `09b4e8d68d46b87a7219bfb009118d29b515c6c7`)

Repo nguồn hiện đồng bộ với `origin/main`; working tree chỉ còn thay đổi local ở file model không liên quan. Source code có task bank cụ thể, nhưng task IDs không khớp `demo-speaking` ở target:

| File nguồn được kiểm tra | SHA-256 | Nội dung |
|---|---|---|
| `src/aicefr/storage/task_repository.py` | `E9A20C5C95DFCD2C4D2722C325C805B8E80CE07191DD35298F6196121F129E9A` | Task P3/P4/P5, prompt version `v1`; P3/P4 40–60 giây, P5 120–300 giây. |
| `src/aicefr/contracts.py` | `A9035E4F3460DFE68AD7A35642FC95704A965778BD7A79FF61B817561C506DE4` | Rubric implementation có năm tiêu chí; `Interaction` không nằm trong enum. |
| `tests/test_tasks_and_admin.py` | `84322B881E77E1635CB8F66BD26395C3F813697DEFC8DF74C83D715D8FA12607` | Kiểm task catalog có prompt text và task versions. |

Không tìm thấy ID `demo-speaking` trong source repo; P3/P4/P5 là task bank của implementation nguồn. Hai prompt theo kế hoạch khảo sát được giữ thành task fixture riêng trên target, không tuyên bố chúng là mapping tương đương P3/P4/P5.

Target browser observation về mô tả `demo-speaking` trống được xử lý bằng hai prompt fixture có version và thời lượng rõ; data-dir cũ chỉ được cập nhật tại chỗ khi placeholder chưa có bài nộp, còn version đã dùng được giữ lịch sử và chuyển sang v2. [Báo cáo browser QA](../../sdd/modules/m13-learning-evidence/evidence/scrum-88/report.md) ghi rõ kết quả, giới hạn và ảnh chụp giao diện.

---

## SCRUM-89 — đối chiếu nguồn cho tập huấn hai người chấm

**Nguồn:** `D:\LAPTRINH\TLCN\AI\ai-assessor-cefr`, HEAD `7614f3d9eec3b2673614b3ca6c4de8d3097221d3` (24/10/2026). **Disposition:** `REFERENCE_ONLY`; chưa có bằng chứng tập huấn/calibration hoàn tất.

Đã đối chiếu thêm `origin/main` `09b4e8d`: chỉ có dòng D057 về giá, không liên quan; D007 và các tài liệu task không đổi. Bản sao ghim theo local source HEAD `7614f3d`.

| File được chuyển nguyên trạng | SHA-256 | Phần liên quan |
|---|---|---|
| `KE_HOACH_KHAO_SAT.md` ← `docs/plan/KE_HOACH_KHAO_SAT.md` | `AF4787121BC0228C69D8FB4BF7CBB63D4DF8D3DBBEB85ACBAC955C896BB66964` | Đề xuất 10 bài chuẩn; weighted kappa ≥ 0,70 và ICC(2,1) ≥ 0,75. |
| `06_cefr_A2_B1_B2_descriptor_map.md` ← `markdown/week_01/06_cefr_A2_B1_B2_descriptor_map.md` | `3617A055FBB74B53A1C59A1BEA8944DBB4E146F1BD7C8CA17493F0E8912E7047` | Descriptor phục vụ đào tạo; `PROPOSED`. |
| `14_ALTE_speaking_grid_draft.md` ← `markdown/week_01/14_ALTE_speaking_grid_draft.md` | `B716DC7124CB438BBF323B4A5628052356CD1DEAB5CBD3167B7CCB46D0677FC1` | Rater/blind-rating procedure; `DRAFT`. |
| `21_week1_decision_log.md` ← `markdown/week_01/21_week1_decision_log.md` | `7143EDA0D09E203B80E7087ED8A82A5CAE1D273D67D5A96551F31F82AA62CA70` | D007 (2 rater + adjudicator) vẫn `PROPOSED`; G1 `NOT HELD`. |

### Kết quả đối chiếu

Không tìm thấy training manual/slide đã duyệt, audio/anchor có quyền dùng, roster hai rater thật, attendance, phiếu điểm, agreement result, remediation hay sign-off. Readiness record này không chứng minh hoạt động đã diễn ra.

Các tài liệu tham khảo có đề xuất calibration khác nhau: kế hoạch khảo sát nêu 10 bài cùng weighted kappa/ICC; đề cương v3.1 nêu 12–15 bài tập và QWK < 0,60 làm stop gate; dry run 4–6 bài là kiểm tải vận hành riêng. Với SCRUM-89, acceptance criteria hiện hành là 10 mẫu được phép dùng, hai lượt chấm độc lập trên mỗi mẫu và weighted kappa mục tiêu ≥ 0,70. Không thay số lượng mẫu hoặc gate của task bằng đề xuất ở tài liệu tham khảo. Rubric/version và quyền sử dụng audio vẫn phải được xác nhận trước khi chạy thật.

Trang chấm mù trên target ở revision `82fe708` không có phiếu được phân công nên chưa kiểm được quy trình hai rater trên web. Đây là dependency UI riêng; không chứng minh hoạt động tập huấn offline đã/không diễn ra. Không tuyên bố đạt reliability khi chưa có phép đo thực tế.

### Recheck code-level source (HEAD `09b4e8d68d46b87a7219bfb009118d29b515c6c7`)

Repo nguồn hiện đồng bộ với `origin/main`; working tree chỉ còn thay đổi local ở file model không liên quan. Source code có quy trình chấm mù kép và UI quản trị:

| File nguồn được kiểm tra | SHA-256 | Vai trò |
|---|---|---|
| `src/aicefr/research/assign.py` | `7D6347A3D6AE08FBE45D5703F8754ECE580A516267221C5289CF8AF4FB417E25` | Phân hai rater/response, thứ tự riêng và assignment. |
| `src/aicefr/research/agreement.py` | `232523F50B0177AC0AFB571225BDCA1A0D9FC57064BAE4D45ECD59845E06EA58` | Agreement, đối chiếu và phân xử. |
| `docs/test/TEST_PLAN_D030.md` | `4571E86FFFC80D4B75845037FB18F9E9FEA7A54D2B3B4FA87F3FEBCFBFA42781` | Test plan ghi test E2E cho rater/admin UI; dữ liệu test được nêu là synthetic. |
| `tests/e2e/test_ratings_e2e.py` | `11BA84869DC7D1A38BE0B3F9711FCE5A9600761324E66FB7F958D50B8386AB43` | Browser flow với tài khoản và fixture test. |

Test plan nguồn ghi 58 unit/statistical, 23 integration và 2 E2E test đã qua ở revision của nó. Đây là kết quả test phần mềm theo tài liệu nguồn, không phải attendance/calibration của người thật. Không có roster xác nhận, buổi tập huấn, anchor/audio được cấp quyền, raw ratings, agreement measurement hoặc sign-off.

Target M12 có implementation/UI một phần nhưng status review/acceptance còn pending; màn hình không có assignment vì chưa có batch/bài đủ điều kiện. Source code chạy theo API/runtime khác nên không chuyển thẳng file; việc tập huấn offline và kết quả thực tế vẫn cần bằng chứng riêng.

### SCRUM-89 — điều kiện chạy buổi tập huấn

Task chưa thể ghi nhận hoàn tất: chưa có hai giảng viên được phân công, 10 audio mẫu có quyền sử dụng cho mục đích tập huấn, hoặc batch chấm mù trên target. SCRUM-81 đang `To Do` và là phụ thuộc trực tiếp để tạo batch, nhận hai lượt chấm độc lập, rồi xuất agreement report.

Khi đủ điều kiện, thực hiện ngay trên chức năng M12 của target:

1. Dùng gate theo SCRUM-89: 10 bài mẫu được phép dùng, hai lượt chấm độc lập mỗi bài và weighted kappa mục tiêu ≥ 0,70. Xác nhận rubric/task version áp dụng trước buổi chấm.
2. Chỉ chọn audio đã được phép lưu và dùng cho tập huấn; cấp ID giả danh, không đưa tên, audio, transcript hoặc dữ liệu liên hệ vào Git.
3. Tạo batch qua SCRUM-81; xáo thứ tự riêng cho từng người chấm. Hai giảng viên không xem điểm AI, danh tính/trình độ người nói, hoặc bài chấm của người còn lại trước khi nộp.
4. Xuất agreement report từ hệ thống và đối chiếu với gate đã chốt (task đặt mục tiêu weighted kappa `≥ 0.70`). Nếu chưa đạt, ghi rõ tiêu chí bất đồng và huấn luyện lại trước khi bắt đầu chấm chính thức; không sửa điểm để ép đạt ngưỡng.
5. Lưu report đã giả danh ở nơi evidence được duyệt; repository chỉ nhận số lượng mẫu, rubric/version, metric thực đo, kết luận gate và reference không chứa PII/audio. Không lập biên bản họp riêng theo chỉ dẫn của chủ dự án.

**Trạng thái hiện tại:** `BLOCKED` chờ SCRUM-81 tạo luồng/batch, hai giảng viên thật và 10 audio mẫu được phép dùng. Chưa có rating hoặc agreement metric; không tạo điểm giả và không tuyên bố buổi tập huấn đã diễn ra.
