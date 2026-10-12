# AI Assessor CEFR — context cấp dự án

**Trạng thái ngày 12/10/2026:** W2–W4 đã có mã nguồn/evidence lịch sử trên `main`; W5 đang ở bước lập SDD và Plan, chưa được phép implement. Baseline repo dự án là `3b2d2b7`; baseline chức năng để đối chiếu là bản Sang monolith `40907cc`. D043 microservice và mọi commit từ `db00fe2` trở đi không thuộc W5. Scope planning hiện hành gồm [kế hoạch W5](docs/plan/week-05.md) và M09–M16; đọc `07-status.md` của đúng module trước khi làm. Mọi module W5 đang Phase 01 `DRAFT/PENDING`, chưa phát prompt.

Mục tiêu dự kiến là một hệ thống hỗ trợ đánh giá bài nói tiếng Anh độc thoại A2–B2 cho sinh viên đại học Việt Nam, phục vụ học tập và giảng viên duyệt. Mọi band/điểm là ước lượng; không cấp chứng chỉ hay tự quyết định đậu/rớt. Chủ dự án đã chọn 5 tiêu chí trong báo cáo tuần 1 làm bản nháp W2. Output W2 chỉ hiển thị overall score/band và coverage của từng tiêu chí; `Interaction=null` với lý do thiếu bằng chứng từ độc thoại. Rubric Speaking có phê duyệt học thuật vẫn chưa có trong nguồn đã kiểm tra.

- Quy tắc chung: [`AGENTS.md`](AGENTS.md); skill dùng chung: [`.agents/skills/sdd-antigravity-orchestrator/SKILL.md`](.agents/skills/sdd-antigravity-orchestrator/SKILL.md).
- Bản đồ tài liệu: [`docs/README.md`](docs/README.md); [nguồn đề tài do nhóm tạo](docs/sources/README.md).
- Roadmap và kế hoạch tuần: [`docs/plan/three-week-roadmap.md`](docs/plan/three-week-roadmap.md); W5 dùng [`docs/plan/week-05.md`](docs/plan/week-05.md).
- Chỉ mục prompt/evidence theo module: [`docs/sdd/prompt-log.md`](docs/sdd/prompt-log.md).
- Hồ sơ minh chứng theo rubric: [`docs/evidence/README.md`](docs/evidence/README.md).
- Nguồn yêu cầu/tiến độ cho từng module: `docs/sdd/modules/<module>/01-requirement.md` và `07-status.md`.
- W3: [Specification](docs/sdd/features/w3-local-integration/03-specification.md), [Tasks](docs/sdd/features/w3-local-integration/06-tasks.md), [Prompt Log](docs/sdd/features/w3-local-integration/prompts/prompt-log.md), [Evidence](docs/sdd/features/w3-local-integration/evidence/evidence-manifest.md), [Review](docs/sdd/features/w3-local-integration/reviews/review-log.md).
- W5 SDD mới: M09 Trust Layer, M10 Learning Experience, M11 Identity & Account, M12 Blind Evaluation, M13 Learning Evidence, M14 Billing & Licensing, M15 Product Web, M16 Monolith Runtime tại `docs/sdd/modules/`; mọi artifact 02–06 hiện chỉ là planning packet DRAFT và không thay approval tuần tự.
- [Hướng dẫn chạy local](docs/local-run.md); dữ liệu, audio và model giữ ngoài Git. Runtime không tự tải weights, không tạo tài khoản/consent hay transcript/score kiểm thử mặc định.
- Tổng kết W1 và giả định giờ công: docs/reports/week-01/tong-ket-w1.md.
- Báo cáo tuần 1 bản gốc: `docs/reports/week-01/bao-cao-tuan-01.docx`.
- Rubric đánh giá đồ án: `docs/rubric/`.

`ai-assessor-cefr` là dự án chính thức do nhóm phát triển từ đầu theo SDD. `docs/sources/` lưu đề cương, model provenance và hồ sơ kỹ thuật nội bộ do nhóm tạo; mỗi nguồn quan trọng có checksum hoặc đường dẫn xuất xứ. Trạng thái và quyền duyệt W2 đọc từ từng module, vì một số scope chỉ nghiệm thu phần W2 hoặc còn chờ cross-owner review. Kết quả trong hồ sơ kỹ thuật nội bộ không phải kết quả của repo này; chỉ dùng phép đo gắn revision trong evidence hiện hành. Chưa có validation CEFR trên người học hay phê duyệt rubric học thuật mới từ lượt W3 này.
