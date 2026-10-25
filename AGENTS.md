# Quy tắc chung cho nhóm và AI agents

**Áp dụng cho toàn bộ repo.** Thắng, Sang, Nguyên và mọi phiên làm việc Codex/Antigravity đọc file này cùng [skill SDD dùng chung](.agents/skills/sdd-antigravity-orchestrator/SKILL.md) trước khi làm W2. Bản trong repo là phiên bản nhóm dùng; nếu máy cá nhân có bản khác, dùng bản trong repo. Khi sửa quy trình, cập nhật một bản này qua Git và báo cả nhóm.

## Nguồn quyết định và trạng thái

1. Chỉ dẫn mới nhất của chủ dự án và các quyết định đã được họ xác nhận.
2. Requirement, Research (nếu chọn RUN), Specification, Test Plan, Plan/Tasks đã được duyệt trong `docs/sdd/modules/<module>/`.
3. File quy tắc này và skill SDD. `AI_CONTEXT.md` là bản đồ ngắn, không thay Specification.
4. `docs/sources/` lưu tài liệu gốc, model provenance và hồ sơ kỹ thuật nội bộ do chính nhóm tạo. Requirement và evidence của dự án được xác định theo SDD đã duyệt và revision hiện hành.

### Phê duyệt trong phạm vi dự án

- Theo chỉ dẫn của chủ dự án ngày 25/10/2026, với các task nghiên cứu/thu thập dữ liệu của nhóm, GVHD là đầu mối duyệt; không yêu cầu thêm phê duyệt riêng từ GV Ngoại ngữ. Chủ dự án đã được GVHD ủy quyền chốt và nghiệm thu các task này.
- Không bắt buộc biên bản hoặc hồ sơ họp riêng. Xác nhận trực tiếp của chủ dự án trong chat là căn cứ cho verdict; cập nhật người duyệt, ngày và quyết định vào `07-status.md` khi phase/task có status tương ứng.
- Quy tắc này thay đổi thẩm quyền và hình thức ghi nhận, không tự chọn thay nội dung chuyên môn còn mâu thuẫn. Chỉ ghi `APPROVED` khi chủ dự án đã chốt đúng artifact/version/phạm vi cụ thể.

W1 (14–18/09/2026) **DONE theo chủ dự án**; minh chứng lịch sử vẫn có mục cần bổ sung. Các SDD W2 hiện là **DRAFT, Phase 01 PENDING**. Việc chia người đọc/review tài liệu được thực hiện ngay; prompt triển khai cho Antigravity chỉ phát khi module có Phase 01, 03, 04 và 05 `APPROVED` theo đúng thứ tự. Không ghi `APPROVED`, `PASS`, `DONE` thay chủ dự án hoặc từ kết quả dự kiến.

## Một quy trình SDD cho cả ba người

- Mỗi module M01–M08 sở hữu `01-requirement.md`, Research khi được chọn, `03-specification.md`, `04-test-plan.md`, `05-plan.md`, `06-tasks.md`, `07-status.md` và `prompts/`, `evidence/`, `reviews/` riêng. Đọc `07-status.md` trước khi sửa scope. Thay đổi contract liên module phải nêu impact, thống nhất với owner liên quan và duyệt lại phase bị ảnh hưởng.
- Người phụ trách module chuẩn bị nội dung và kiểm tra nguồn; Codex viết prompt, điều phối checkpoint và review actual diff/evidence; Antigravity triển khai và chạy test/browser QA theo prompt đã duyệt; chủ dự án quyết định verdict. Các thành viên có thể dùng phiên Codex riêng cho module của mình, nhưng cùng skill và cùng quy tắc này.
- Mỗi task chỉ có một owner, vùng file được sửa và dependency rõ trong `docs/plan/week-02.md`/SDD. Trước khi sửa source chung, thông báo owner module liên quan; không để hai phiên AI cùng sửa một vùng source tại một thời điểm. Dùng branch/commit riêng có Task ID, review diff trước khi gộp. Không đưa thay đổi ngoài task vào commit.
- Prompt Antigravity phải được lưu tại `docs/sdd/modules/<module>/prompts/` và ghi Prompt ID, Task ID, base revision/fingerprint vào log local **trước khi gửi**. Antigravity trả raw report, diff/commit và lệnh/kết quả kiểm tra; lưu tại `evidence/` local, review tại `reviews/`, cập nhật `07-status.md`. Bản chat hay lời nhắc “dùng skill” không tự lưu prompt/evidence.

## Minh chứng, dữ liệu và chất lượng

- Mỗi người ghi **mọi lần dùng AI** vào sheet mang tên mình trong workbook của tuần tương ứng tại `docs/evidence/tc2-3-ai-usage/`, theo mẫu `AI Prompt Log - Wxx - YYYY-MM-DD_YYYY-MM-DD.xlsx`: ngày, người, công cụ, công việc, prompt, link minh chứng. Tuần tính từ thứ Hai đến Chủ nhật và xếp theo ngày sử dụng AI, không theo tên task/module. Xem [danh sách file tuần](docs/evidence/tc2-3-ai-usage/README.md). Sheet `Tổng hợp` trong từng file cộng cả ba sheet của tuần đó. Prompt triển khai còn phải có bản file/log tại module. `docs/evidence/` là hồ sơ nộp theo rubric, dẫn về bằng chứng gốc trong module; tránh nhân bản file và claim.
- Chỉ dùng số liệu đo được trên **repo dự án** và revision ghi rõ. Kiểm thử, coverage, ASR/model version, consent và nguồn audio phải có evidence truy cập được. Ghi `NOT_RUN`/`NOT_EVALUATED` khi chưa có phép đo. Dữ liệu kiểm thử do nhóm tạo được gọi là `fixture` hoặc `test data`; kết quả CEFR thực nghiệm phải dẫn tới bộ dữ liệu và phép đo tương ứng.
- Bản nháp sản phẩm dùng 5 tiêu chí Range, Accuracy, Fluency, Coherence, Phonology; chỉ hiển thị overall score/band và coverage/evidence của từng tiêu chí. `Interaction=null` với `insufficient_evidence` cho bài độc thoại. Overall không được trình bày thành năm điểm tiêu chí. Mọi thay đổi rubric/band mapping phải quay về SDD M05 và được duyệt.
- Không commit secret, audio hoặc dữ liệu cá nhân thật, model weights không có quyền phân phối. Tuân thủ `.gitignore`; manifest ghi nơi giữ bằng chứng bị hạn chế truy cập. Không push, deploy, gửi dữ liệu ra dịch vụ ngoài hoặc thay đổi production nếu chưa có quyền rõ từ chủ dự án.

## Cách mô tả dự án

- `ai-assessor-cefr` là dự án chính thức do nhóm phát triển từ đầu theo SDD để phục vụ đồ án và báo cáo.
- Trong tài liệu, prompt và báo cáo, dùng các tên `dự án`, `repo dự án`, `mã nguồn dự án`, `implementation hiện tại` hoặc `revision hiện hành`.
- Tránh các cụm `dựng lại`, `viết lại`, `làm lại`, `bản dựng mới`, `repo mới`, `source mới` và cách diễn đạt khiến dự án bị hiểu là clone hoặc bản sao của một source khác.
- `../ai-assessor-cefr-runtime/backups/ai-assessor-cefr-thamchie-before-cleanup-2026-10-08` lưu hồ sơ kỹ thuật nội bộ do chính nhóm phát triển trong giai đoạn hình thành đề tài. Chỉ dẫn tới hồ sơ này qua `docs/sources/` khi cần giải thích provenance, quyết định kỹ thuật hoặc tính khả thi.
- Gọi dữ liệu do nhóm chuẩn bị để kiểm thử là `fixture` hoặc `dữ liệu kiểm thử do nhóm tạo`. Mọi số liệu báo cáo phải có lệnh chạy, revision và evidence tương ứng.

## Bắt đầu W2

Đọc [kế hoạch W2](docs/plan/week-02.md), [bản đồ tài liệu](docs/README.md), module được giao và Status của nó. Gửi review/đề xuất sửa SDD theo FR/AC/Test/Task ID. Chỉ sau verdict Phase 05 mới tạo prompt triển khai với helper `.agents/skills/sdd-antigravity-orchestrator/scripts/workspace_fingerprint.py`. Nếu thông tin quan trọng còn thiếu, ghi câu hỏi/blocker ở module và hỏi chủ dự án; chỉ ghi kết quả đã có evidence thực tế.
