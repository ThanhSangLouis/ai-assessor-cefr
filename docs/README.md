# Bản đồ tài liệu

| Nơi lưu | Nội dung | Quy tắc |
| --- | --- | --- |
| `../AGENTS.md`, `../ANTIGRAVITY.md`, `../.agents/skills/sdd-antigravity-orchestrator/` | Một bộ quy tắc/skill SDD dùng chung cho cả ba người và điểm vào Antigravity | Dùng bản trong repo, không dựa vào skill cài riêng trên từng máy |
| `plan/three-week-roadmap.md` | Tổng quan các mốc và quyết định còn mở | Dẫn tới kế hoạch tuần riêng |
| `plan/week-01.md` … `week-05.md` | Kế hoạch/record theo tuần | W5 là task bắt buộc theo người, giữ modular monolith |
| `sdd/modules/<slug>/` | SDD độc lập theo M01–M16 | M01–M08 là nền hiện hành; M09–M16 là scope W5 DRAFT, mỗi module có Status local |
| `sdd/features/w3-local-integration/` | Scope tích hợp W3, ba lane Luna, Codex review | Quyền implement trực tiếp từ Thắng; formal verdict PENDING |
| `local-run.md` | Cài đặt, CLI/demo, cấu hình model local và restart | Audio/model/DB ngoài Git; không tự tải weights khi chạy |
| `sdd/prompt-log.md` | Chỉ mục log prompt module đã phát hành | Prompt thật nằm trong prompts/ của từng module; M09–M16 chưa phát prompt |
| `evidence/` | Hồ sơ minh chứng theo rubric và checklist 12 mục | Dẫn tới artifact gốc, không nhân đôi số liệu |
| `design/week-01/` | Hai bản hình sơ đồ lớp do nhóm đưa vào | Dùng bản sáng để review; bản tối là biến thể trình bày |
| `reports/week-01/` | Tổng kết W1, báo cáo Word gốc và 4 hình được tách từ báo cáo | Giữ Word nguyên bản; hình lưu riêng để dẫn chiếu |
| `rubric/` | PDF rubric gốc | Giữ một nguồn chuẩn, PDF có thể tìm kiếm văn bản |
| `sources/` | Hai đề cương DOCX gốc, model provenance và khảo sát kỹ thuật có checksum | Nguồn học thuật và hồ sơ kỹ thuật nội bộ do nhóm tạo |

## Nguồn và tình trạng

- `reports/week-01/bao-cao-tuan-01.docx` là tài liệu **đã có trước** khi khởi tạo cấu trúc này, chưa được mình sửa nội dung hay xác nhận các claim trong đó.
- Bốn ảnh trong `reports/week-01/figures/` khớp byte-for-byte với image1–image4 nhúng trong báo cáo Word W1. Bản đang lưu trong báo cáo là nguồn chính thức cho W1. File kỹ thuật nội bộ `../ai-assessor-cefr-thamchie/docs/sdd/images/02_class.png` có SHA-256 hiện tại `c86c4bc0a2c9b310569924e9afe0b9fad7674d0c210534afeae600d0c0534ae8` và khác ảnh nhúng; hai bản được phân biệt rõ để bảo toàn provenance.
- `design/week-01/class-diagram-light.png` và `class-diagram-dark.png` là hai ảnh do nhóm cung cấp cho W1 và đã được sắp xếp lại vị trí lưu. Chúng **khác** hình `reports/week-01/figures/02_class.png` nhúng trong Word; mỗi bộ được giữ theo đúng nguồn và mục đích sử dụng.
- `rubric/Rubric_Do_An_Mon_Hoc_CNPM_sinhvien.docx.pdf` là PDF rubric gốc của nhóm, được lưu nguyên bản từ `../ai-assessor-cefr-thamchie/docs/rubric/`; PDF có thể tìm kiếm văn bản trực tiếp.

## Tài liệu lịch sử được chọn lọc

Repo chỉ giữ những tài liệu trực tiếp hỗ trợ yêu cầu, nghiên cứu, thiết kế và evidence của kế hoạch ba tuần. Các roadmap 7/10/12/15 tuần, notebook và artifact dẫn xuất tiếp tục được quản lý trong kho nội bộ của nhóm để tránh trùng lặp. Khi một quyết định hoặc hình cụ thể cần cho module, owner ghi nguồn trong Requirement/Research và lưu đúng artifact cần thiết.

Trước khi sử dụng báo cáo tuần 1 làm căn cứ nghiệm thu, cần rà soát các ví dụ số đo/ca sử dụng, tuyên bố pháp lý, độ chính xác mô hình và trạng thái phê duyệt. Một số tài liệu lịch sử mô tả 6 tiêu chí/Task C, còn phạm vi W2 dùng bài độc thoại với 5 tiêu chí và `Interaction=null`. Xem câu hỏi mở trong kế hoạch.

## Danh mục tài liệu nội bộ đã sàng lọc

| Tài liệu nội bộ | Trạng thái | Lý do |
| --- | --- | --- |
| docs/rubric/ | Đã lưu PDF gốc | Tiêu chí đánh giá của đồ án |
| docs/sdd/images/01a*, 01b*, 01c*, 02_class.png | Đã lưu 4 hình tại reports/week-01/figures/ | Bốn hình nhúng trong báo cáo Word W1, đã kiểm tra hash |
| docs/srs/SRS.md, docs/sdd/SDD.md | Quản lý tại kho nội bộ; trích dẫn khi cần | Phạm vi 41 FR/12 tuần khác kế hoạch ba tuần; approval của dự án theo Status từng module |
| markdown/week_01/01_glossary.md, 16_data_management_plan.md, 21_week1_decision_log.md | Quản lý tại kho nội bộ; đưa quyết định đã duyệt vào module | Có ích cho thuật ngữ và quản trị dữ liệu; một số quyết định còn PROPOSED |
| docs/reports/, markdown/weekly_reports/, docs/ai-usage-log.md | Ghi báo cáo và log theo hoạt động của dự án | Mỗi claim tiến độ, metric và AI usage dẫn tới evidence của revision hiện hành |
| docs/plan/, markdown/ còn lại, artifacts/derived/, notebooks/ | Quản lý tại kho nội bộ | Trùng phiên bản, khác thời lượng kế hoạch hoặc là artifact dẫn xuất |

## Prompt Antigravity và evidence

Bộ hồ sơ nộp theo rubric nằm tại [docs/evidence/](evidence/README.md); M06 Diagnostic Report tạo báo cáo cho một bài nói. Hồ sơ rubric có thư mục riêng cho TC1, TC2.1–TC2.7, TC3–TC6 và hồ sơ quy trình. Prompt, raw report, evidence và review nằm trong scope/module. Xem [chỉ mục Prompt Log](sdd/prompt-log.md) và [W3 Prompt Log](sdd/features/w3-local-integration/prompts/prompt-log.md). Prompt phải được lưu thành file và ghi log trước khi bàn giao. Status từng module/scope dẫn tới record mới nhất; W3 không tự thay nghiệm thu W2 đang PENDING. [AI Prompt Log theo tuần](evidence/tc2-3-ai-usage/README.md#ai-prompt-log-theo-tuan) có sáu workbook tính từ thứ Hai đến Chủ nhật, trong đó W05–W06 được chuẩn bị trống; sheet Thắng của W03 ghi prompt thực tế của lượt W3 ngày 02/10/2026.
