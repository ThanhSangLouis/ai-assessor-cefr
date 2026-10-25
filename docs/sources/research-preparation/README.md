# SCRUM-89 — đối chiếu nguồn cho tập huấn hai người chấm

**Nguồn:** `D:\LAPTRINH\TLCN\AI\ai-assessor-cefr`, HEAD `7614f3d9eec3b2673614b3ca6c4de8d3097221d3` (24/10/2026). **Disposition:** `REFERENCE_ONLY`; chưa có bằng chứng tập huấn/calibration hoàn tất.

Đã đối chiếu thêm `origin/main` `09b4e8d`: chỉ có dòng D057 về giá, không liên quan; D007 và các tài liệu task không đổi. Bản sao ghim theo local source HEAD `7614f3d`.

| File được chuyển nguyên trạng | SHA-256 | Phần liên quan |
|---|---|---|
| `KE_HOACH_KHAO_SAT.md` ← `docs/plan/KE_HOACH_KHAO_SAT.md` | `AF4787121BC0228C69D8FB4BF7CBB63D4DF8D3DBBEB85ACBAC955C896BB66964` | Đề xuất 10 bài chuẩn; weighted kappa ≥ 0,70 và ICC(2,1) ≥ 0,75. |
| `06_cefr_A2_B1_B2_descriptor_map.md` ← `markdown/week_01/06_cefr_A2_B1_B2_descriptor_map.md` | `3617A055FBB74B53A1C59A1BEA8944DBB4E146F1BD7C8CA17493F0E8912E7047` | Descriptor phục vụ đào tạo; `PROPOSED`. |
| `14_ALTE_speaking_grid_draft.md` ← `markdown/week_01/14_ALTE_speaking_grid_draft.md` | `B716DC7124CB438BBF323B4A5628052356CD1DEAB5CBD3167B7CCB46D0677FC1` | Rater/blind-rating procedure; `DRAFT`. |
| `21_week1_decision_log.md` ← `markdown/week_01/21_week1_decision_log.md` | `7143EDA0D09E203B80E7087ED8A82A5CAE1D273D67D5A96551F31F82AA62CA70` | D007 (2 rater + adjudicator) vẫn `PROPOSED`; G1 `NOT HELD`. |

## Kết quả đối chiếu

Không tìm thấy training manual/slide đã duyệt, audio/anchor có quyền dùng, roster hai rater thật, attendance, phiếu điểm, agreement result, remediation hay sign-off. Readiness record này không chứng minh hoạt động đã diễn ra.

Các tài liệu tham khảo có đề xuất calibration khác nhau: kế hoạch khảo sát nêu 10 bài cùng weighted kappa/ICC; đề cương v3.1 nêu 12–15 bài tập và QWK < 0,60 làm stop gate; dry run 4–6 bài là kiểm tải vận hành riêng. Với SCRUM-89, acceptance criteria hiện hành là 10 mẫu được phép dùng, hai lượt chấm độc lập trên mỗi mẫu và weighted kappa mục tiêu ≥ 0,70. Không thay số lượng mẫu hoặc gate của task bằng đề xuất ở tài liệu tham khảo. Rubric/version và quyền sử dụng audio vẫn phải được xác nhận trước khi chạy thật.

Trang chấm mù trên target ở revision `82fe708` không có phiếu được phân công nên chưa kiểm được quy trình hai rater trên web. Đây là dependency UI riêng; không chứng minh hoạt động tập huấn offline đã/không diễn ra. Không tuyên bố đạt reliability khi chưa có phép đo thực tế.

## Recheck code-level source (HEAD `09b4e8d68d46b87a7219bfb009118d29b515c6c7`)

Repo nguồn hiện đồng bộ với `origin/main`; working tree chỉ còn thay đổi local ở file model không liên quan. Source code có quy trình chấm mù kép và UI quản trị:

| File nguồn được kiểm tra | SHA-256 | Vai trò |
|---|---|---|
| `src/aicefr/research/assign.py` | `7D6347A3D6AE08FBE45D5703F8754ECE580A516267221C5289CF8AF4FB417E25` | Phân hai rater/response, thứ tự riêng và assignment. |
| `src/aicefr/research/agreement.py` | `232523F50B0177AC0AFB571225BDCA1A0D9FC57064BAE4D45ECD59845E06EA58` | Agreement, đối chiếu và phân xử. |
| `docs/test/TEST_PLAN_D030.md` | `4571E86FFFC80D4B75845037FB18F9E9FEA7A54D2B3B4FA87F3FEBCFBFA42781` | Test plan ghi test E2E cho rater/admin UI; dữ liệu test được nêu là synthetic. |
| `tests/e2e/test_ratings_e2e.py` | `11BA84869DC7D1A38BE0B3F9711FCE5A9600761324E66FB7F958D50B8386AB43` | Browser flow với tài khoản và fixture test. |

Test plan nguồn ghi 58 unit/statistical, 23 integration và 2 E2E test đã qua ở revision của nó. Đây là kết quả test phần mềm theo tài liệu nguồn, không phải attendance/calibration của người thật. Không có roster xác nhận, buổi tập huấn, anchor/audio được cấp quyền, raw ratings, agreement measurement hoặc sign-off.

Target M12 có implementation/UI một phần nhưng status review/acceptance còn pending; màn hình không có assignment vì chưa có batch/bài đủ điều kiện. Source code chạy theo API/runtime khác nên không chuyển thẳng file; việc tập huấn offline và kết quả thực tế vẫn cần bằng chứng riêng.

## SCRUM-89 — điều kiện chạy buổi tập huấn

Task chưa thể ghi nhận hoàn tất: chưa có hai giảng viên được phân công, 10 audio mẫu có quyền sử dụng cho mục đích tập huấn, hoặc batch chấm mù trên target. SCRUM-81 đang `To Do` và là phụ thuộc trực tiếp để tạo batch, nhận hai lượt chấm độc lập, rồi xuất agreement report.

Khi đủ điều kiện, thực hiện ngay trên chức năng M12 của target:

1. Dùng gate theo SCRUM-89: 10 bài mẫu được phép dùng, hai lượt chấm độc lập mỗi bài và weighted kappa mục tiêu ≥ 0,70. Xác nhận rubric/task version áp dụng trước buổi chấm.
2. Chỉ chọn audio đã được phép lưu và dùng cho tập huấn; cấp ID giả danh, không đưa tên, audio, transcript hoặc dữ liệu liên hệ vào Git.
3. Tạo batch qua SCRUM-81; xáo thứ tự riêng cho từng người chấm. Hai giảng viên không xem điểm AI, danh tính/trình độ người nói, hoặc bài chấm của người còn lại trước khi nộp.
4. Xuất agreement report từ hệ thống và đối chiếu với gate đã chốt (task đặt mục tiêu weighted kappa `≥ 0.70`). Nếu chưa đạt, ghi rõ tiêu chí bất đồng và huấn luyện lại trước khi bắt đầu chấm chính thức; không sửa điểm để ép đạt ngưỡng.
5. Lưu report đã giả danh ở nơi evidence được duyệt; repository chỉ nhận số lượng mẫu, rubric/version, metric thực đo, kết luận gate và reference không chứa PII/audio. Không lập biên bản họp riêng theo chỉ dẫn của chủ dự án.

**Trạng thái hiện tại:** `BLOCKED` chờ SCRUM-81 tạo luồng/batch, hai giảng viên thật và 10 audio mẫu được phép dùng. Chưa có rating hoặc agreement metric; không tạo điểm giả và không tuyên bố buổi tập huấn đã diễn ra.
