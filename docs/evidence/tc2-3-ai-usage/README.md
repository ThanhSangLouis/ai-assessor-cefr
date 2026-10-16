# TC2.3 — Làm chủ và kiểm soát AI

**Nguồn tiêu chí:** rubric PDF tại docs/rubric/. Trạng thái của folder: PARTIAL

## Hồ sơ cần có

AI Usage Log, prompt gốc, mục đích dùng AI, file sinh ra, phần người làm chủ/kiểm tra; log Antigravity theo module.

## Minh chứng hiện có

| Artifact | Vai trò | Tình trạng |
| --- | --- | --- |
| [AI Prompt Log theo tuần](#ai-prompt-log-theo-tuan) | Sáu workbook; mỗi file có sheet Thắng, Sang, Nguyên và Tổng hợp | W04 có 8 bản ghi bổ sung của Nguyên ngày 12/10 theo yêu cầu; W05 có 3 bản ghi Nguyên trong PR này; W06 chưa có bản ghi |
| [Kiểm tra task và tạo PR W4 của Nguyên](nguyen/pr-W4-20261012.md) | Ba yêu cầu thực tế ngày 12/10; phạm vi commit và ánh xạ workbook | W05 trong PR: 3 dòng Nguyên/Codex; không khép lịch sử W04 còn thiếu |
| [Chuyển log Nguyên sang W04](nguyen/chuyen-log-sang-W04-20261012.md) | Ánh xạ 7 dòng từ W05 sang W04 và yêu cầu chuyển file | Ngoại lệ nơi lưu theo chỉ dẫn Nguyên; giữ ngày thực tế 12/10/2026 |
| [Biên tập prompt của Nguyên](nguyen/prompt-log-bien-tap-20261012.md) | Đối chiếu nội dung gốc và phiên bản diễn đạt chuyên nghiệp của W05, hàng 6–12 | Biên tập theo yêu cầu ngày 12/10; bản gốc được giữ để kiểm tra |
| [Audit AI log W04 của Nguyên](nguyen/W04-audit.md) | Xác nhận thiếu lịch sử; phạm vi tìm nguồn và quy tắc phục hồi | HISTORICAL_EVIDENCE_MISSING; không backfill từ commit |
| [AI Usage Log](ai-usage-log.md) | Bốn bản ghi Codex lúc khởi tạo; prompt mới ghi trong Excel | Lịch sử |
| [AI Usage Log của Sang W1–W3](sang/README.md) ([CSV đầy đủ](sang/ai-usage-log-sang-W1-W3.csv)) | Bản xuất 55 dòng từ ba tab Sang trong Google Sheet, mỗi dòng có PR/commit; kèm 7 lỗi của AI đã phát hiện và sửa, quy trình kiểm soát đầu ra AI | Đủ W1–W3 (04/10/2026) |
| [Prompt Log các module](../../sdd/prompt-log.md) | Log prompt theo module/feature và người thực hiện | Đọc trạng thái từng scope |
| [W3 Prompt Log](../../sdd/features/w3-local-integration/prompts/prompt-log.md) | Prompt gốc/amendment/correction đã lưu trước giao ba Luna; Codex review | Actual delegation 02/10/2026, sheet Thắng |
| [W3 Review](../../sdd/features/w3-local-integration/reviews/review-01.md) | Findings từ actual diff, correction và independent checks | User verdict PENDING |
| [AGENTS.md](../../../AGENTS.md) và [skill SDD chung](../../../.agents/skills/sdd-antigravity-orchestrator/SKILL.md) | Quy tắc/skill nhóm dùng từ bàn giao W2 | Đã lưu trong repo; không thay log prompt hay chứng minh file rule W1 |

## AI Prompt Log theo tuần

Mỗi tuần từ **thứ Hai đến Chủ nhật**. W01 bắt đầu ngày 14/09/2026 theo lịch dự án.
Phân loại theo ngày ghi ở cột A; tên task có W2/W3 không làm thay đổi tuần của bản ghi.

| File | Khoảng ngày | Thắng | Nguyên | Sang | Tổng prompt |
| --- | --- | --- | --- | --- | --- |
| [W01](AI%20Prompt%20Log%20-%20W01%20-%202026-09-14_2026-09-20.xlsx) | 14–20/09/2026 | 0 | 0 | 14 | 14 |
| [W02](AI%20Prompt%20Log%20-%20W02%20-%202026-09-21_2026-09-27.xlsx) | 21–27/09/2026 | 4 | 0 | 17 | 21 |
| [W03](AI%20Prompt%20Log%20-%20W03%20-%202026-09-28_2026-10-04.xlsx) | 28/09–04/10/2026 | 21 | 9 | 24 | 54 |
| [W04](AI%20Prompt%20Log%20-%20W04%20-%202026-10-05_2026-10-11.xlsx) | 05–11/10/2026; có bổ sung 12/10 của Nguyên | 20 | 8 | 17 | 45 |
| [W05](AI%20Prompt%20Log%20-%20W05%20-%202026-10-12_2026-10-18.xlsx) | 12–18/10/2026 | 28 | 3 | 6 | 37 |
| [W06](AI%20Prompt%20Log%20-%20W06%20-%202026-10-19_2026-10-25.xlsx) | 19–25/10/2026 | 0 | 0 | 0 | 0 |

Ngày 16/10/2026, thêm sáu bản ghi thực tế của Sang cho SCRUM-71/72. Tổng hợp được tính lại theo các dòng hiện có trong workbook tại base của PR: Thắng 28, Nguyên 3, Sang 6, tổng 37. Không phục hồi hoặc suy đoán các bản ghi lịch sử không có trong file này.

Số lượng tại thời điểm tách ngày 08/10/2026: giữ đủ **46 bản ghi gốc**, thêm một
bản ghi cho yêu cầu tách file, tổng cộng **47**. Sheet `Tổng hợp` có công thức và
giá trị hiển thị đã kiểm tra cho từng tuần; số liệu tiếp tục cập nhật khi có log mới.
Sau đó chuẩn bị W05 và W06 trống theo yêu cầu; log cho lượt chuẩn bị được ghi tại
W04, sheet Thắng, hàng 19 với ngày 08/10/2026. Tổng ở thời điểm chuẩn bị là **48 bản ghi**;
hai file tuần 5–6 có đủ sheet, định dạng và công thức, chưa có bản ghi. Lượt rà soát
thư mục ngày 08/10/2026 được ghi tại W04, hàng 20; tổng sau lượt rà soát là **49 bản ghi**.
Lượt xóa tham chiếu cũ và cache pip theo yêu cầu được ghi tại W04, sheet Thắng, hàng 21; tổng sau lượt dọn là **50 bản ghi**. Minh chứng: [dọn thư mục](../cleanup-2026-10-08.md).

Workbook nguồn bắt đầu có log từ 25/09/2026 nên tại thời điểm tách W01 và sheet Sang được giữ trống. Ngày 08/10/2026, theo yêu cầu của Thắng, đã nhập đủ **55 bản ghi** từ [CSV của Sang](sang/ai-usage-log-sang-W1-W3.csv): W01 14, W02 17, W03 24. Phân tuần theo ngày gốc, thứ Hai–Chủ nhật. CSV giữ nguyên; prompt và minh chứng được bảo toàn. Cột F kèm phiên bản/model, nội dung AI tạo và phần Sang sửa/hoàn thiện để giữ đủ thông tin trong mẫu sáu cột. Dòng 28/09 đã được CSV khử trùng, không nhập hai lần.

Bản tổng hợp trước khi tách được sao lưu ngoài Git tại
`../ai-assessor-cefr-runtime/backups/AI Prompt Log-before-week-split-2026-10-08.xlsx`.
Manifest kiểm tra và ánh xạ hàng cũ → file/hàng mới ở
`../ai-assessor-cefr-runtime/evidence/weekly-prompt-logs-2026-10-08.json`.
Từ nay ghi tiếp vào file của tuần tương ứng.

Ngày 11/10/2026 Sang ghi **17 bản ghi** W04 vào sheet Sang, theo cùng mẫu sáu cột (cột F kèm phiên bản/model, nội dung AI tạo và phần Sang sửa/hoàn thiện). Mỗi dòng có minh chứng là PR: repo cá nhân `ThanhSangLouis/ai-assessor-cefr` PR #5–#17 (private, cần cấp quyền đọc cho GVHD) và PR #32 của repo này. Prompt được viết lại cho rõ nhưng bám đúng yêu cầu gốc trong phiên làm việc; không có số liệu suy ra từ S&I.

## Quy ước ghi AI Prompt Log

Mỗi prompt ghi một dòng trong sheet của người thực hiện: Thắng, Sang hoặc Nguyên, trong file của tuần tương ứng. Điền ngày (cột A), tên người tạo (B), công cụ AI (C), công việc (D), prompt (E) và link minh chứng (F). Sheet `Tổng hợp` đếm các dòng có ngày trong phạm vi hàng 6–306 của từng sheet trong cùng file; thống kê công cụ cộng cả ba sheet.

Ba dòng mẫu `abc` đã được xóa nội dung ngày 25/09/2026 để không bị tính như prompt thật. Các bản ghi khởi tạo ngày 25/09 được giữ; lượt W3 02/10 ghi thêm user instruction, prompt gốc, amendments/corrections và xác nhận quyền audio vào sheet Thắng, với full text và file evidence. Tool column dùng `Codex` để summary formulas hiện có đếm đúng; executor `gpt-6-luna` và vai trò Codex review ghi trong activity/prompt. Không ghi giờ công hay hoạt động của Sang/Nguyên thay họ. Chỉ dùng số liệu sau khi mỗi dòng có prompt/evidence thật; templates chưa có ngày không được tính như prompt thực.

Ngày 02/10/2026, Thắng xác nhận tám prompt Codex W2 `W2-P01–W2-P08` đã được sử dụng thực tế ngày **28/09/2026**. Các bản ghi đã bỏ nhãn `MẪU`/`CHƯA GỬI`, dùng tool `Codex` và điền ngày 28/09/2026; giữ nguyên nội dung prompt. Sau khi tách, chúng nằm ở sheet Thắng của W03, hàng 6–13; yêu cầu đính chính ngày 02/10/2026 ở hàng 26. Quy ước thứ Hai–Chủ nhật đặt ngày 28/09 vào W03 dù tên task là W2.

## Còn thiếu / cần xác minh

Lượt W3 dùng Luna, không giả mạo prompt Antigravity. Link Jira cho local W3 Task IDs và tệp AI rules có nguồn gốc W1 chưa có để xác minh. Bộ rule/skill trong repo là bản dùng chung cho W2; authority override W3 ghi rõ tại Requirement, không thay log hay user acceptance.

Khi có evidence mới, thêm dòng gồm: Evidence ID, nguồn/path hoặc URL, ngày, owner, Prompt/Task/AC nếu áp dụng, revision/checksum và trạng thái xác minh. Chỉ ghi số liệu và trạng thái PASS khi có phép đo cùng evidence tương ứng.

Lượt khởi chạy repo Sang trên localhost:8002 ngày 08/10/2026 được ghi tại W04, sheet Thắng, hàng 22; tổng sau lượt khởi chạy là **51 bản ghi**. Evidence local ở `../ai-assessor-cefr-runtime/sang/verification.json` và `asr-smoke.json`.

Sau khi nhập CSV Sang, tổng sau lượt nhập là **107 bản ghi** (55 dòng Sang và một log cho lượt nhập tại W04, sheet Thắng, hàng 23). Công thức và giá trị hiển thị của `Tổng hợp` đã được đối chiếu. W05–W06 tiếp tục trống. Bản sao lưu workbook trước khi nhập tại `../ai-assessor-cefr-runtime/backups/before-sang-csv-import-2026-10-08/`; manifest ánh xạ từng dòng CSV → file/hàng Excel tại `../ai-assessor-cefr-runtime/evidence/sang-csv-import-2026-10-08.json`.

Lượt chuẩn bị commit/push ngày 08/10/2026 ghi tại W04, sheet Thắng, hàng 24; tổng sau lượt chuẩn bị **108 bản ghi**. Người dùng đã duyệt tên commit và cho phép commit/push sau lượt chuẩn bị.

Lượt thực hiện commit/push theo xác nhận của Thắng ghi tại W04, sheet Thắng, hàng 25; tổng tại thời điểm đó **109 bản ghi**. Kết quả thực thi và commit remote lưu trong evidence local `pre-push-2026-10-08.json`.

Ngày 12/10/2026, ghi **5 bản ghi thực tế** tại W05, sheet Nguyên, hàng 6–10: đọc plan W4; yêu cầu hoàn thiện task; xác nhận chưa có khảo sát/lịch sử AI W04; chỉ dẫn giả định ba vị trí giám khảo; cho phép fix binary read M08 và nhận thông báo Thắng. Minh chứng dẫn tới [báo cáo cá nhân W4](../../reports/week-04/bao-cao-tuan-04-nguyen.md) và [audit W04](nguyen/W04-audit.md). Công thức Tổng hợp đã tính lại: tổng 5, Nguyên 5, Codex 5; kiểm tra render và không có lỗi công thức. Các sheet/formula/định dạng khác được bảo toàn. Hoạt động ngày 12/10 thuộc W05 dù task là W4. Số 0 trong sheet Nguyên W04 là số bản ghi có nguồn, không chứng minh Nguyên không dùng AI trong tuần đó.

Tiếp theo trong ngày 12/10, Nguyên yêu cầu sửa lời văn prompt theo phong cách chuyên nghiệp. Đã biên tập năm dòng W05 hiện có và ghi thêm hai yêu cầu chỉnh log tại hàng 11–12; **tổng W05 tại thời điểm đó là 7**. Cột E được ghi rõ là lời văn đã biên tập, giữ nguyên ý nghĩa, ngày dùng AI và tool; [hồ sơ đối chiếu](nguyen/prompt-log-bien-tap-20261012.md) giữ nội dung gốc. Cột F dẫn tới minh chứng cụ thể; chiều cao các hàng được điều chỉnh để đọc đủ nội dung. Tổng hợp đếm 7 cho Nguyên/Codex và toàn workbook, các công thức và sheet khác giữ nguyên. Không dùng phiên bản biên tập làm bằng chứng prompt đã được gửi nguyên văn trong quá khứ.

Sau đó Nguyên yêu cầu **chuyển nội dung vào file W04**. Bảy dòng được chuyển sang W04, hàng 6–12; yêu cầu chuyển được ghi ở hàng 13. Tại thời điểm chuyển, W04 có 8 dòng Nguyên, tổng workbook 45; W05 còn 0 dòng. Đây là ngoại lệ nơi lưu theo chỉ dẫn mới nhất của Nguyên. Ngày dùng AI vẫn **12/10/2026**, thuộc W05 theo lịch; phụ đề và minh chứng W04 ghi rõ phần bổ sung sau tuần. Bảng trên đếm nội dung đang lưu trong từng file. Khoảng lịch sử 05–11/10 của Nguyên vẫn thiếu nguồn, không được coi là đã khôi phục từ các dòng ngày 12/10.

Lượt kiểm tra task/tạo PR ngày 12/10 của Nguyên ghi **3 bản ghi mới** tại W05. [Record PR](nguyen/pr-W4-20261012.md) và [checks](nguyen/pr-W4-20261012-checks.json) giữ prompt gốc, ánh xạ hàng và phạm vi bảo toàn workbook. Bản local đầy đủ có 10 dòng (ba dòng mới ở hàng 13–15); bản đưa vào PR của Nguyên có ba dòng mới ở hàng 6–8, giữ bảy bản ghi ngoài phạm vi trong workspace. Ngày dùng AI thực tế vẫn 12/10, các công thức Tổng hợp và sheet của người khác được bảo toàn.
