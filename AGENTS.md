# Hướng dẫn làm việc cho AI agents

Áp dụng cho toàn repo và mọi agent. Làm theo yêu cầu mới nhất của chủ dự án. Quy trình dưới đây kết hợp kỷ luật kiểm soát bối cảnh, phụ thuộc kỹ thuật, kiểm thử tập trung và cơ chế dừng an toàn (`BLOCKED`), nhưng vẫn linh hoạt theo quy mô để không biến việc nhỏ thành chuỗi thủ tục.

## 0. Chạy dự án

Được nhờ chạy project, cài môi trường hay chạy test: làm theo
[docs/plan/CHAY_DU_AN_CHO_AI.md](docs/plan/CHAY_DU_AN_CHO_AI.md) trước khi thử cách khác.
Tóm tắt: `./demo.sh` (cần Docker cho MongoDB); artifact mô hình nằm ngoài repo ở
`../aicefr-models`, thiếu thì `demo.sh` dùng artifact giả lập và điểm vô nghĩa; không
commit artifact, `.env`, dữ liệu ghi âm; không đẩy thẳng lên `main`.

Hỏi về production, EC2/AWS, GitHub Actions, CI, deploy, `.env` máy chủ hay sao lưu: đọc
[docs/plan/TRIEN_KHAI_CHO_AI.md](docs/plan/TRIEN_KHAI_CHO_AI.md) trước. Tóm tắt: merge vào
`main` + CI xanh là tự deploy lên EC2 (runner của GitHub SSH vào máy chủ, không có
self-hosted runner); `main` có branch protection; AI agent không SSH, không gọi AWS, không
đụng secret.

## 1. Quy trình 8 bước chuẩn (co giãn theo loại task)

Với việc nhỏ/trực tiếp, có thể gộp nhanh các bước 01–04. Với thay đổi code, bug fix hoặc liên module, thực hiện đầy đủ theo trình tự:

1. **01 — Intake:** Xác định rõ loại task, mục tiêu, phạm vi file/module và tiêu chí hoàn thành (acceptance criteria).
2. **02 — Context Discovery:** Đọc hướng dẫn theo phân cấp từ gốc đến thư mục đích (`AGENTS.md` con, `README.md`, và `01-requirement.md` / `03-specification.md` / `07-status.md` nếu thuộc module cụ thể). Chỉ mở `AI_CONTEXT.md` khi cần định hướng tổng thể.
3. **03 — Impact Analysis:** Kiểm tra shared types/utilities/components hiện có để tái sử dụng trước khi tạo mới; xác định phụ thuộc liên module, schema/generated code bị ảnh hưởng và rủi ro hồi quy (regression risk).
4. **04 — Plan & Gate Check:** Lập kế hoạch ngắn và chọn bộ test/check tương ứng phạm vi. Kiểm tra điều kiện `BLOCKED` hoặc điểm cần chủ dự án quyết định trước khi viết code.
5. **05 — Implementation:** Triển khai đúng phạm vi owner, giữ nguyên comment/docstring hiện hữu và tuân thủ thứ tự phụ thuộc kỹ thuật theo từng loại task ở Mục 2.
6. **06 — Verification:** Ưu tiên chạy focused test, lint và typecheck trên đúng file/module thay đổi; tránh build hoặc chạy toàn bộ test suite của repo khi không cần thiết. Chạy integration test khi thay đổi chạm contract/API liên module.
7. **07 — Review & Fix:** Xem lại `git diff`, đối chiếu yêu cầu ban đầu, kiểm tra không lọt thay đổi ngoài phạm vi hoặc dữ liệu nhạy cảm, sửa lỗi phát sinh và verify lại.
8. **08 — Handover:** Báo cáo ngắn gọn gồm: file đã đổi, lệnh và kết quả kiểm tra thực tế, các kiểm tra chưa chạy (`NOT_RUN`/`NOT_EVALUATED` hoặc để CI chạy), giới hạn còn lại, và các mục `BLOCKED`/cần chủ dự án chốt.

## 2. Điều chỉnh quy trình theo loại task

- **Việc trực tiếp, phạm vi rõ** *(chuyển/copy file, chạy lệnh/test có sẵn, đọc tài liệu, báo cáo trạng thái, sửa typo/lỗi nhỏ đã rõ)*: Thực hiện ngay; không tạo SDD, Task ID, phase, prompt hay yêu cầu `APPROVED` mới. Hỏi lại trước nếu đích file/lệnh chưa rõ hoặc có nguy cơ ghi đè dữ liệu.
- **Fix Bug (theo hướng test-first):** Kiểm tra phạm vi → Tìm test hiện có để mở rộng (ưu tiên hơn tạo file test mới) hoặc viết test tái hiện lỗi → Chạy xác nhận test `FAIL` → Đánh giá rủi ro ảnh hưởng → Sửa code trong phạm vi được phép → Chạy lại xác nhận test `PASS` và không gây hồi quy.
- **Update Function / Thay đổi tính năng:** Đối chiếu và cập nhật requirement/contract liên quan (nếu có) và đánh giá ảnh hưởng tới các màn hình/API gọi hàm đó trước khi sửa logic; cập nhật unit/integration test tương ứng.
- **Task Full-stack hoặc liên module:** Triển khai tuần tự theo phụ thuộc kỹ thuật thay vì sửa tự do hoặc chạy đồng thời thiếu đồng bộ:
  `Contract / API types (shared)` → `Backend / Service logic` → `API / Controllers` → `Frontend / UI` → `Tests & Verification`.
- **Thay đổi lớn hoặc rủi ro cao:** Tóm tắt tác động, phương án và quyết định còn thiếu; dừng ở checkpoint cần chủ dự án chốt trước khi triển khai sâu. Tạo hoặc cập nhật SDD khi task cần hợp đồng bền vững, nhiều owner/dependency, bằng chứng đồ án yêu cầu, hoặc chủ dự án chỉ định.
- **Handoff Antigravity:** Chỉ dùng khi chủ dự án yêu cầu hoặc task được giao cho Antigravity. Gửi brief gọn (mục tiêu, file/phạm vi, ràng buộc, lệnh check cần chạy); lưu prompt/evidence khi rubric hoặc task yêu cầu. Khi nhận kết quả, kiểm tra `git diff` và chạy/đối chiếu kết quả thực tế rồi báo cáo. Không đòi Phase 01–09 hay `APPROVED` mặc định.

## 3. Cơ chế `BLOCKED` và ranh giới phê duyệt

Không mặc định mọi task đều có thể tự động hoàn thành. Agent **phải dừng và báo `BLOCKED`** (hoặc yêu cầu xác nhận rõ từ chủ dự án) trước khi thực hiện các hành động sau:

- Thay đổi rubric chấm điểm, trọng số hoặc quy tắc quy đổi band CEFR (thuộc scope M05).
- Thay đổi kiến trúc liên module chưa có contract, thay đổi cơ chế auth/phân quyền, billing, hoặc migration làm biến đổi/xóa dữ liệu lưu trữ.
- Xử lý, commit hoặc phát tán secret, audio thật, dữ liệu cá nhân thật (PII) hoặc model weights không có quyền phân phối.
- Thực hiện `git push`, deploy, gọi/gửi dữ liệu ra dịch vụ ngoài, hoặc can thiệp môi trường production khi chưa được chủ dự án cho phép rõ.
- Tự ý ghi nhận verdict `APPROVED`, `PASS` (cấp độ nghiệm thu cổng) hay `DONE` thay cho chủ dự án. Phase và verdict trong `docs/sdd/` là hồ sơ của scope tương ứng, không phải thủ tục mặc định cho mọi yêu cầu. Chỉ cập nhật artifact thực sự bị ảnh hưởng.

## 4. Phạm vi, phối hợp và nguồn chuẩn

- **Thứ tự ưu tiên nguồn sự thật:** (1) Chỉ dẫn mới nhất của chủ dự án → (2) Quyết định/contract đã chốt của scope liên quan → (3) Code và test hiện hành → (4) Bản đồ định hướng trong `AI_CONTEXT.md`.
- **Quản lý phạm vi và xung đột:** Mỗi task có một owner và phạm vi file rõ khi làm việc nhóm. Trước khi sửa file dùng chung (shared packages/types, cấu hình), kiểm tra xung đột với owner/phiên khác. Không đưa thay đổi ngoài phạm vi vào commit.
- **Hướng dẫn theo thư mục:** Trước khi sửa file trong thư mục có `AGENTS.md` riêng, đọc hướng dẫn gần nhất và chỉ áp dụng trong phạm vi thư mục đó. Nếu sửa `.github/workflows/`, đọc `.github/AGENTS.md` trước (nếu tồn tại). Quy tắc workflow chung toàn repo chỉ đặt tại file gốc này; khi thay đổi, cập nhật qua Git và báo nhóm.
- **Xử lý thiếu dữ kiện:** Khi thiếu thông tin ảnh hưởng trực tiếp tới kết quả, nêu câu hỏi ngắn gọn hoặc giả định rõ ràng. Không biến chi tiết kỹ thuật có thể tự quyết trong phạm vi thành điểm chờ phê duyệt.
- **Thuật ngữ và nguồn gốc:** Dùng tên `dự án`, `repo dự án`, `mã nguồn dự án`, `implementation hiện tại` hoặc `revision hiện hành`. Tránh cách diễn đạt khiến repo bị hiểu nhầm là bản sao của nguồn khác. Thư mục `docs/sources/` lưu tài liệu nguồn và provenance do nhóm quản lý.

## 5. Kiểm tra, evidence và quy tắc miền CEFR

- **Báo cáo kiểm chứng trung thực:** Nêu rõ lệnh đã chạy, kết quả thực tế, revision và giới hạn còn lại. Ghi rõ `NOT_RUN` hoặc `NOT_EVALUATED` cho các kiểm tra chưa thực hiện (hoặc để CI chạy); phân biệt rõ dữ liệu fixture kiểm thử với dữ liệu người học thật hay kết quả CEFR thực nghiệm.
- **Nhật ký AI & Evidence đồ án:** Theo rubric đồ án, ghi mọi lần dùng AI vào sheet cá nhân trong workbook tuần tương ứng tại `docs/evidence/tc2-3-ai-usage/`. Evidence kỹ thuật lưu tại module/scope tương ứng; hồ sơ nộp dẫn link về bằng chứng gốc, tránh nhân bản claim.
- **Quy tắc miền đánh giá Speaking:** Bản nháp đánh giá sử dụng 5 tiêu chí: `Range`, `Accuracy`, `Fluency`, `Coherence`, `Phonology`; hiển thị overall score/band kèm coverage/evidence của từng tiêu chí. Với bài nói độc thoại, giữ nguyên `Interaction=null` và lý do `insufficient_evidence`.
