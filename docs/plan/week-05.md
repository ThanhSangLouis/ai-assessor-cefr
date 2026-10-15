# W5 — 12–18/10/2026 — sản phẩm chạy được và đồng nhất chức năng với bản tham chiếu

**Phiên bản:** v0.4 — DRAFT, đã bổ sung SDD M09–M16, traceability và gói triển khai chi tiết cho từng task; chờ chủ dự án duyệt theo checkpoint.

**Ngày lập:** 12/10/2026, múi giờ Asia/Ho_Chi_Minh.

**Mốc code đã kiểm tra sau khi cập nhật từ GitHub:**

- Repo nhóm cần hoàn thiện: `thanglb2005/ai-assessor-cefr` tại `3b2d2b78ba5bb35bd162b8f3e5de21ade946d237`.
- Bản dùng để đối chiếu hành vi: `ThanhSangLouis/ai-assessor-cefr` tại `40907cc35b3d04408f9a8713f16d9be99f4cd6c7` — commit monolith cuối cùng, đã có D039–D042.
- Hai nhánh `main` đều đã khớp `origin/main` tại thời điểm lập kế hoạch.
- `db00fe2`, merge `939a774` và trạng thái `0539e05` chứa D043 microservice nên không thuộc phạm vi Week 5.
- Bản Sang còn một thay đổi local trong `docs/ai-usage-log.md`; thay đổi này chỉ là nhật ký chạy local và không thuộc baseline chức năng.

**Trạng thái kiểm tra sau khi pull:** chưa chạy lại toàn bộ test, smoke hoặc browser QA trên baseline Week 5. Mọi số đo cũ chỉ dùng để biết lịch sử, không dùng làm kết quả W5.

---

## 1. Mục tiêu tuần 5

Đến cuối tuần, repo nhóm phải có một bản chạy được mà người dùng quan sát thấy đầy đủ các luồng và tính năng đang có ở bản Sang tại commit nêu trên. “Đồng nhất chức năng” trong kế hoạch này có nghĩa là:

1. Cùng vai trò người dùng, cùng hành trình chính, cùng điều kiện cho phép hoặc từ chối.
2. Cùng dữ liệu đầu vào, kết quả, trạng thái loading/empty/error/success và cách phục hồi.
3. Cùng các giới hạn trung thực của hệ thống: không cấp chứng chỉ, không tự quyết định đậu/rớt, bài luyện không có band, thiếu bằng chứng thì không bịa điểm.
4. Cùng mức hoàn thiện giao diện: bố cục, điều hướng, component, thông báo, responsive, dark/light mode, chuyển động và accessibility.
5. Cùng năng lực vận hành ở bản monolith: một ứng dụng Python, SQLite, worker local và model lưu ngoài Git; test và tài liệu đủ để người khác dựng lại trên một máy.
6. Không yêu cầu hai repo giống từng dòng code. Repo nhóm phải giữ dữ liệu và contract đã kiểm chứng của M01–M08, đồng thời đưa các tính năng mới vào một hệ thống thống nhất, không tồn tại hai ứng dụng song song.

### Kết quả cuối tuần phải nhìn thấy được

- Khách chưa đăng nhập xem được trang giới thiệu và trang giải thích band.
- Sinh viên đăng nhập, quản lý hồ sơ và phiên, xác nhận đồng thuận, làm bài đánh giá, làm bài học/luyện tập, xem báo cáo, tiến độ, thành tựu và dữ liệu cá nhân.
- Giảng viên xem hàng đợi, duyệt bài, xem thống kê, soạn lộ trình, sửa nhận định của lượt luyện và thực hiện chấm mù khi được phân công.
- Quản trị viên quản lý tài khoản, mô hình, ngưỡng QC, dữ liệu, thực nghiệm phản hồi, đợt chấm mù, sai số đo, gói dịch vụ và thanh toán thử.
- Pipeline thật vẫn chạy QC → ASR → đặc trưng → scoring → report; lỗi hoặc thiếu model phải ra trạng thái đúng, không dùng kết quả giả để che lỗi.
- Có một lệnh chạy monolith được kiểm chứng từ môi trường sạch; restart không làm mất job, report hoặc phiên hợp lệ.

### Ngoài phạm vi W5

- Không deploy production, không mở public Internet, không mua VPS.
- Không thu tiền thật. Stripe/MoMo/VNPay chỉ chạy sandbox/test khi có khóa phù hợp; cổng thử nội bộ là đường kiểm tra mặc định.
- Không đưa audio, transcript, PII, token, client secret hoặc database thật vào Git.
- Không tuyên bố độ chính xác CEFR, WER, hiệu quả phản hồi hay tiết kiệm thời gian nếu chưa có dữ liệu đo hợp lệ.
- Không fine-tune foundation model và không thay rubric/band threshold đã được khóa chỉ để đạt parity giao diện.
- Không triển khai D043: không tạo sáu service, Nginx gateway, PostgreSQL, RabbitMQ, RPC nội bộ hoặc Docker Compose nhiều container.
- Không đưa các thư mục `services/`, `platform/` hay dependency `psycopg`/`pika` vào repo nhóm trong W5.

---

## 2. Gate bắt buộc trước khi viết code

### W5-SDD — Bộ SDD điều khiển implementation

Week 5 không triển khai trực tiếp từ mô tả trong file kế hoạch này. Mỗi thay đổi phải truy ngược tới Requirement, Specification, Test Plan, Plan và Task của đúng module dưới đây. Các artifact hiện là **planning packet DRAFT**: việc soạn trước để review không có nghĩa các phase đã được duyệt, và không được phát prompt hay bắt đầu code trước khi chủ dự án duyệt tuần tự Phase 01, 03, 04 và 05.

| Module | Trách nhiệm W5 | Owner | Task W5 chính | Status |
| --- | --- | --- | --- | --- |
| [M09 — Trust Layer](../sdd/modules/m09-trust-layer/01-requirement.md) | LID, validity shield, conformal, indicator, refusal evidence | Sang | W5-S01; N01/N03 consume | Phase 01 DRAFT |
| [M10 — Learning Experience](../sdd/modules/m10-learning-experience/01-requirement.md) | Practice, lesson, review, achievement, streak | Sang | W5-S02/S03; N02/N03 | Phase 01 DRAFT |
| [M11 — Identity & Account](../sdd/modules/m11-identity-account/01-requirement.md) | Profile, password, session, admin account, Google, consent | Thắng | W5-T02; N01/N04 | Phase 01 DRAFT |
| [M12 — Blind Evaluation](../sdd/modules/m12-blind-evaluation/01-requirement.md) | Batch, blind sheet, adjudication, agreement | Sang | W5-S04; N03/N04 | Phase 01 DRAFT |
| [M13 — Learning Evidence](../sdd/modules/m13-learning-evidence/01-requirement.md) | Pronunciation, feedback study, teacher-time, reliable change | Sang | W5-S03/S04; N01–N04 | Phase 01 DRAFT |
| [M14 — Billing & Licensing](../sdd/modules/m14-billing-licensing/01-requirement.md) | Plan, sandbox payment, receipt, license | Thắng | W5-T03; N04 | Phase 01 DRAFT |
| [M15 — Product Web](../sdd/modules/m15-product-web/01-requirement.md) | Design system và toàn bộ public/student/teacher/admin UI | Nguyên | W5-N01–N04 | Phase 01/03/04 APPROVED; Phase 05 APPROVED cho 001A và SCRUM-74–76/M15-TASK-003–006 theo [status](../sdd/modules/m15-product-web/07-status.md) |
| [M16 — Monolith Runtime](../sdd/modules/m16-monolith-runtime/01-requirement.md) | Migration, worker, package, CI, data ops, final integration | Thắng | W5-T01/T04 | Phase 01 DRAFT |

Quy tắc áp dụng:

1. Owner đọc `07-status.md` của module trước khi sửa và chỉ dùng artifact version đã được duyệt.
2. Task W5 là container phân công cho một người; module task trong `06-tasks.md` là đơn vị code/review nhỏ. Một task W5 chỉ `DONE` khi mọi module task được ánh xạ tới nó đã đạt gate.
3. Thay đổi payload/schema dùng chung phải merge bằng contract change riêng và cập nhật module liên quan trước khi UI hoặc consumer tiếp tục.
4. Khi phát hiện requirement mới ngoài M09–M16, dừng ở Requirement; không nhét thêm vào task hiện có để kịp tuần.
5. M01–M08 vẫn là nguồn contract nền. M09–M16 mở rộng W5 và không tự thay verdict lịch sử của M01–M08.

### W5-G0 — Chốt baseline và vùng sở hữu

Owner: Thắng. Reviewer: Sang và Nguyên.

- Tạo nhánh `feat/W5-product-parity` từ `3b2d2b7`.
- Ghi hai commit baseline ở đầu mọi task và report.
- Không cập nhật bản Sang giữa tuần. Nếu bản Sang có commit mới, ghi vào backlog W6; chỉ thay baseline W5 khi cả nhóm quyết định bằng văn bản.
- Mỗi file chỉ có một owner đang sửa tại một thời điểm. Thay đổi contract dùng chung phải qua PR nhỏ riêng trước khi ba lane tiếp tục.
- Chạy baseline: full test không smoke, lint, format check, wheel build, local boot và browser smoke tối thiểu. Ghi đúng `PASS`, `FAIL` hoặc `NOT_RUN`.
- Sao lưu database/blob demo trước migration; kiểm tra khả năng restore trước khi chạy migration trên dữ liệu local hiện có.

### W5-G1 — Chốt nghĩa của “giống bản Sang”

Kế hoạch dùng hành vi ở commit `40907cc` làm chuẩn cho các tính năng mới. Khi hành vi đó mâu thuẫn với rule an toàn đã có trong repo nhóm, rule an toàn thắng và khác biệt phải được ghi trong report. Các invariant không được phá:

- `Interaction=null` với độc thoại thiếu bằng chứng tương tác.
- `teacher_verified` chỉ bật sau hành động của giảng viên có audit.
- Bài luyện và bước bài học không sinh CEFR band.
- LID/lạc đề/đọc lại đề chỉ chuyển review, không trừ điểm.
- Score/band phải có model version, calibration/provenance và evidence hợp lệ.
- Dữ liệu nghiên cứu chỉ xuất khi consent nghiên cứu còn hiệu lực.
- Mọi quyền xem/sửa/xóa phải kiểm tra owner và role ở server, không dựa vào nút bị ẩn trên giao diện.

### W5-G2 — Chốt migration và rollback

- Migration phải giữ nguyên account, session hợp lệ, consent, response, audio/blob, report, review action, task version, audit, model registry và config đang có.
- Mỗi migration có test từ database v4 hiện tại lên schema mới.
- Không xóa bảng/cột cũ trong W5. Nếu cần thay cấu trúc, dùng bước copy + verify + switch; chỉ đánh dấu phần cũ deprecated.
- Rollback kỹ thuật: dừng app, phục hồi SQLite/blob backup và chạy lại commit trước migration. Mọi thử nghiệm migration dùng bản sao dữ liệu, không chạy trực tiếp lên dữ liệu cần giữ.

---

## 3. Hiện trạng và khoảng trống phải đóng

Repo nhóm đã có pipeline local, auth/consent, upload/recording, report, review, SQLite, portal quản trị, thống kê cơ bản, export/xóa dữ liệu, worker, health/readiness, backup/retention và bài nói dài. Những phần dưới đây chưa có hoặc chưa đạt cùng hành vi với bản Sang:

| Nhóm | Trạng thái đầu W5 | Kết quả phải đạt |
| --- | --- | --- |
| Trust Layer | Chưa có LID, lạc đề/đọc lại đề, conformal set và chỉ báo theo tiêu chí | Có đủ rule, reason code, provenance, refusal benchmark và UI giải thích |
| Luyện tập | Chưa có | Có ngân hàng nhiệm vụ, feedback theo luật, gợi ý tiếp theo, không band |
| Lộ trình bài học | Chưa có | Có lộ trình → chặng → bài → bước, soạn/xuất bản/ôn tập/sửa nhận định |
| Thành tựu và nhịp luyện | Chưa có | 17 thành tựu, streak, ngày nghỉ, so sánh 7 ngày, không leaderboard |
| Hồ sơ và Google | Có profile/export cơ bản; chưa có UX 4 tab và Google PKCE | Đủ hồ sơ, phiên, activity, Google link/unlink, admin account detail |
| Chấm mù kép | Chưa có | Có batch, hai rater, adjudication, agreement report và CSV |
| Billing | Chưa có | Có plan/license/order/receipt; sandbox mặc định; Stripe/MoMo/VNPay tùy cấu hình |
| Bằng chứng học tập | Chưa có | Có phát âm VN, feedback study, teacher-time KPI, reliable change |
| Giao diện | HTML WSGI đơn giản, ít component | Đủ trang, role navigation, recorder dùng chung, art, font, motion, responsive |
| Kiến trúc chạy | Đang là modular monolith local-first | Giữ nguyên monolith; thêm chức năng bằng module/service nội bộ, không tách tiến trình |
| Hồ sơ SDD | Nhiều module còn lệch code | Cập nhật đúng trạng thái thực, không tự ghi APPROVED |

---

## 4. Kiến trúc modular monolith phải giữ

### 4.1. Ranh giới module

| Module | Trách nhiệm | Không được làm |
| --- | --- | --- |
| `identity` | account, password, session, Google, consent, audit danh tính | Không đọc điểm, transcript hoặc model artifact |
| `assessment` | task đánh giá, response, report, teacher review, blind rating, study | Không quản lý password hoặc thanh toán |
| `learning` | practice, lesson, step attempt, review schedule, achievement, pronunciation | Không sinh CEFR band từ bài luyện |
| `billing` | plan, quote, order, payment event, license, entitlement | Không khóa chức năng học cơ bản của sinh viên |
| `speech` | decode, QC, ASR, feature, scoring, pipeline job | Không sở hữu account, consent UI hoặc payment |
| `web` | page, static asset, browser interaction, BFF mỏng | Không chứa rule chấm điểm hay authorization chỉ ở client |

Tổ chức code dự kiến, mở rộng trên cấu trúc đang có:

```text
src/aicefr/
├── api/               # WSGI endpoint, page entry và static asset
├── local/             # composition root, worker, CLI và lệnh chạy
├── auth/              # account, session, consent và Google
├── audio/             # decode và recording boundary
├── qc/                # đo và policy chất lượng audio
├── asr/               # ASR adapter, LID và guard liên quan transcript
├── features/          # đặc trưng và rule lạc đề/đọc lại đề
├── scoring/           # scorer, conformal và criterion indicators
├── pipeline/          # điều phối một response đầu-cuối
├── report/            # report contract, evidence và persistence
├── review/            # teacher review, blind rating và audit
├── portal/            # service/router/template cho ba vai trò
├── storage/           # SQLite repositories và migration
├── practice/          # mission, recommendation, achievement và streak
├── lessons/           # model, alignment, checks, progress và seed
├── pronunciation/     # rule vi-pron-v1
├── research/          # agreement, study, KPI và reliable change
└── billing/           # plan, gateway, signature và payment rule thuần
```

Các package QC/ASR/features/scoring/report/review hiện có tiếp tục là lõi nghiệp vụ. Route chỉ parse request, gọi application service và map response; không đặt rule nghiệp vụ trong router/template.

### 4.2. Một chế độ chạy monolith

- Entry point giữ `python -m aicefr.local serve ...`.
- Một process web và worker local hiện có cùng dùng SQLite qua repository rõ ràng; worker dùng connection riêng và lease để tránh hai worker xử lý cùng job.
- Blob/audio, model và database nằm ngoài Git; đường dẫn lấy từ config, không hard-code theo máy.
- Có thể bật Whisper/Silero/Ridge thật bằng config; thiếu artifact bắt buộc phải fail readiness hoặc trả `NOT_EVALUATED`, không fallback thành điểm giả.
- Không có HTTP/RPC nội bộ, message broker, gateway hoặc database thứ hai trong W5.

Domain rule chỉ có một bản và được gọi từ web, CLI, worker qua application service dùng chung.

### 4.3. Contract nội bộ

- WSGI/router xác thực session, kiểm role/owner/consent rồi mới gọi service; client không được tự khai actor hoặc role bằng header/form.
- Application service giữ transaction boundary và điều phối repository/domain; repository không gọi template, còn template không truy cập SQLite trực tiếp.
- Background job có `job_id`, `response_id`, `attempt`, lease, timestamp, schema version và idempotency key.
- Worker ghi kết quả bằng compare-and-set; restart hoặc retry không tạo report/audit trùng.
- Mọi mutation ghi audit trong cùng SQLite transaction khi có thể; thao tác blob dùng cleanup intent để phục hồi khi file I/O thất bại.
- Request ID đi từ WSGI request tới job/audit/log nhưng không chứa actor ID, transcript hoặc đường dẫn dữ liệu.

### 4.4. Database và migration

Thắng tạo migration theo thứ tự, mỗi nhóm có forward test và rollback note:

1. Identity: profile, avatar, speaking goal, temporary-password flag, session metadata, Google subject hash, server secret, account activity.
2. Learning: path, unit, lesson, immutable published version, step, media, attempt, step result, spaced-review schedule, teacher override, achievement, streak snapshot.
3. Assessment: blind-rating batch/assignment/form/adjudication; review session timing; study/cohort/survey; measurement-error setting.
4. Billing: plan, entitlement, quote, order, payment message, receipt, signed license.
5. Operations: durable job, lease, retry, idempotency, cleanup intent và audit cho worker local.

Ràng buộc bắt buộc:

- Foreign key và unique key chặn duplicate assignment, duplicate payment và duplicate achievement.
- Delete theo response phải cascade đúng rating/study link được phép, nhưng audit append-only giữ record tối thiểu không chứa PII.
- Published lesson version bất biến; sửa nội dung tạo version mới.
- Payment event lưu raw payload đã lọc secret, hash/signature result và processing status để đối soát.
- SQLite bật foreign key, transaction rõ ràng và migration version; repository test dùng file database thật thay vì chỉ mock.

---

## 5. Kế hoạch code chi tiết theo nhóm chức năng

Mục này mô tả phạm vi kỹ thuật. Task dùng để giao việc và đánh dấu hoàn thành chỉ là các mã `W5-T*`, `W5-S*`, `W5-N*` tại mục 9.

### Nhóm A — Nền tảng chạy và contract dùng chung

Task triển khai: `W5-T01`, `W5-T04`. Phụ thuộc: W5-G0–G2.

Vùng code: `pyproject.toml`, `src/aicefr/local/`, `src/aicefr/api/`, `src/aicefr/portal/`, `src/aicefr/storage/`, `.github/workflows/` và script kiểm tra tương ứng.

Việc phải làm:

1. Bổ sung dependency thật sự cần cho feature monolith, nổi bật là `simplemma`; không thêm `psycopg`, `pika` hoặc service framework.
2. Mở rộng composition root hiện có để khởi tạo auth, learning, rating, research và billing repository/service bằng dependency injection; không tạo global mutable singleton.
3. Thêm SQLite migration runner có version, backup check và transaction boundary thống nhất.
4. Mở rộng durable worker hiện có với lease, retry có giới hạn, interrupted-job recovery và idempotency; không tạo message bus.
5. Giữ một router/app; tách handler theo miền để file không phình thành một khối khó review.
6. Bổ sung liveness/readiness cho SQLite, blob store, worker lease và model artifact; không trả path/secret trong payload.
7. Wheel phải đóng gói đủ template, JavaScript, CSS, icon, art, font và metadata cần chạy.
8. CI chạy format, lint, unit/integration, wheel build, forbidden-file/secret scan và coverage.

Acceptance:

- Cài từ wheel trong venv sạch và khởi động bằng một lệnh.
- Worker restart/retry không tạo kết quả trùng và không để response kẹt `RUNNING`.
- Readiness phản ánh đúng SQLite/blob/worker/model; liveness không lộ cấu hình nhạy cảm.
- Không xuất hiện package, dependency hoặc cấu hình D043.

### Nhóm B — Trust Layer và pipeline đánh giá

Task triển khai: `W5-S01`. Phụ thuộc: contract job của Nhóm A.

Vùng code: `src/aicefr/asr/`, `src/aicefr/features/`, `src/aicefr/scoring/`, `src/aicefr/pipeline/`, `src/aicefr/report/`, `tools/` và test tương ứng.

Việc phải làm:

1. LID: nhận diện bài không phải tiếng Anh; lưu method/version/confidence/reason; confidence thấp chuyển review.
2. Lá chắn lạc đề và đọc lại đề: tính bằng evidence quan sát được; chỉ thêm review reason, không trừ score.
3. Conformal CV+: đọc calibration artifact có checksum; alpha mặc định `0.10`; set chứa từ hai band trở lên sinh `SCORE_NEAR_BOUNDARY`.
4. Chỉ báo Range/Accuracy/Fluency/Coherence/Phonology phải gắn nhãn “chỉ báo”, không trình bày như năm điểm độc lập.
5. Report lưu đầy đủ provenance cho guard/model/calibration; report cũ vẫn render được.
6. Tool calibration/refusal benchmark nhận config/seed/input manifest, sinh output có hash; không đọc confirmation set để tune.
7. Bài dài vẫn dùng policy cửa sổ hiện hành; mọi cửa sổ phải hợp lệ mới aggregate và luôn đưa teacher review.

Acceptance:

- Test success, boundary, missing artifact, checksum sai, non-English, off-topic, prompt-reading và retry cùng job.
- Không reason nào làm giảm điểm trực tiếp.
- UI giải thích vì sao cần review bằng tiếng Việt, không lộ internal threshold không cần thiết.

### Nhóm C — Luyện tập, lộ trình bài học và ôn tập

Task triển khai: `W5-S02`, phần repository của `W5-T01`, UI ở `W5-N02` và authoring UI ở `W5-N03`.

Vùng code: `src/aicefr/practice/`, `src/aicefr/lessons/`, learning service, repositories và các trang practice/teach.

Việc phải làm:

 1. Practice bank: 15 nhiệm vụ ban đầu, 5 tiêu chí × 3 band; `purpose=PRACTICE`; bảy `MissionKind` dùng rule cố định và evidence span.
 2. Không đưa practice attempt vào scorer, teacher queue, assessment stats hoặc research export mặc định.
 3. Recommendation: chọn tiêu chí yếu nhất từ bài đánh giá gần nhất, rồi chọn nhiệm vụ phù hợp band; fallback rõ khi chưa có bài đánh giá.
 4. Lesson hierarchy: Path → Unit → Lesson → Step; A2/B1/B2, 18 chặng, 31 bài seed; topic và display order ổn định.
 5. Mỗi lesson đi qua Mẫu → Có kiểm soát → Có hướng dẫn → Tự do; bậc cuối 2–3 lượt, giới hạn thời gian giảm dần.
 6. Chín loại bước dùng alignment/lemma/rule; ASR không được nhận transcript mẫu làm prompt gợi ý.
 7. Teacher authoring: create/edit/reorder/delete draft, validation/lint, record sample audio, preview, publish immutable version, export/import.
 8. Spaced review: lịch 1/3/7 ngày; endpoint lấy mục ôn hôm nay; attempt được xóa theo quyền owner.
 9. Teacher insight: nghe lại, xem rule evidence, override nhận định; override không tạo CEFR score và không chặn sinh viên.
10. Seed/migration chạy idempotent; không ghi đè nội dung teacher đã sửa hoặc attempt cũ.

Acceptance:

- Practice result không có `overall_score`, `band` hoặc `teacher_verified`.
- Lesson published không sửa tại chỗ.
- Recommendation giải thích được rule.
- Test alignment, lemma, silence, 1-second QC, review schedule, import/export, seed idempotency và permission.

### Nhóm D — Thành tựu, streak và tiến độ học

Task triển khai: `W5-S03`, `W5-N02`.

Vùng code: practice progress, learning repository, my-progress và lesson UI.

Việc phải làm:

1. Cài 17 thành tựu theo năm nhóm: đều đặn, thời gian nói, lộ trình, kiên trì và đánh giá.
2. Chỉ đếm effort từ lượt có speech hợp lệ; không dùng score/band/pass rate làm điều kiện thưởng.
3. Achievement đã đạt không bị lấy lại khi attempt bị xóa hoặc teacher override.
4. Tính ngày theo Asia/Ho_Chi_Minh; một ngày nghỉ/tuần; lưu record đủ để chạy lại deterministic.
5. Hiển thị current streak, record, nghỉ được tính, 7 ngày gần nhất so với 7 ngày trước và achievement gần đạt.
6. Badge “mới” chỉ hiện một lần và được đánh dấu seen ở server.

Acceptance:

- Không leaderboard, XP, cảnh báo mất streak hoặc countdown gây áp lực.
- Timezone boundary, deletion, retry, duplicate event và seen state có unit test.

### Nhóm E — Tài khoản, hồ sơ, phiên và Google

Task triển khai: `W5-T02`, phần account UI của `W5-N01` và admin UI của `W5-N04`.

Vùng code: `src/aicefr/auth/`, auth application service, auth repository, account/admin pages.

Việc phải làm:

1. Account page có bốn tab: Hồ sơ, Bảo mật, Hoạt động, Dữ liệu.
2. Profile chỉ dùng 15 avatar icon × 10 màu; không upload ảnh/tên thật; speaking goal 1/2/3/5/10 phút.
3. Theme/font size lưu client; dữ liệu account/goal lưu server.
4. Đổi password: xác minh password hiện tại; 8 ký tự, tối đa 72 byte, khác alias; revoke phiên khác; password tạm buộc đổi trước mọi thao tác khác.
5. Session list có thiết bị thô, created/last seen/current; logout từng phiên hoặc tất cả phiên khác.
6. Admin tạo một account hoặc batch tối đa 200 theo transaction; password tạm hiện đúng một lần; reset/unlock/enable/disable/change role/logout all/unlink Google; không tự thao tác nguy hiểm lên chính mình.
7. Google OIDC authorization code + PKCE S256 + state + nonce; cookie flow ký HMAC; validate issuer/audience/expiry/nonce; chỉ account đã link, không auto-signup, không lưu email/name/avatar.
8. HTTPS dùng `__Host-` cookie; thiếu cấu hình phải báo disabled rõ, không fallback insecure.
9. Admin config chỉ hiển thị client secret đã đặt/chưa đặt, redirect URI, scopes và domain restriction; tuyệt đối không trả secret.

Acceptance:

- Test session fixation/revocation, lockout, temporary password, batch rollback, role escalation, forged OAuth cookie, state/nonce/PKCE, duplicate Google subject và secret exposure.

### Nhóm F — Teacher review, chấm mù kép và báo cáo đồng thuận

Task triển khai: `W5-S04`, storage của `W5-T01`, teacher UI ở `W5-N03` và admin UI ở `W5-N04`.

Vùng code: review service, assessment rating API, `src/aicefr/research/agreement.py`, `assign.py`, storage và teacher/admin UI.

Việc phải làm:

1. Giữ claim TTL/revision/audit hiện tại; mỗi claim mở `review_session`; quyết định/close/release kết thúc session.
2. Admin tạo batch từ response của người học có research consent; lưu seed; hai rater/response; thứ tự shuffle riêng.
3. Blind page không lộ alias, response ID, AI score, report, reviewer khác hoặc metadata có thể suy danh tính.
4. Người đã xem machine result của response không được nhận assignment mù cho response đó.
5. Phiếu gồm 5 tiêu chí, overall 0–6 bước 0.5, band, một dòng rationale hoặc unrateable reason; submit một lần.
6. Adjudication khi chênh overall ≥1.0, lệch band hoặc chỉ một bên unrateable; adjudicator không phải hai rater cũ.
7. Report agreement trình human-human trước machine-human; bootstrap theo speaker; CSV pseudonymous.
8. Thêm CLI/tool tái tạo report từ batch ID và seed.

Acceptance:

- Test mọi đường vòng ẩn danh, repeat submit, assignment collision, consent withdrawal, adjudicator conflict, metric boundary và insufficient sample.

### Nhóm G — Bằng chứng học tập D039–D042

Task triển khai: `W5-S03`, `W5-S04`, storage của `W5-T01`, student UI ở `W5-N01`–`W5-N02` và teacher/admin UI ở `W5-N03`–`W5-N04`.

1. **Phát âm Việt:** `vi-pron-v1` nhận 5 nhóm lỗi; chỉ dùng word label của lesson attempt; teacher-corrected word bị loại; dưới 8 exposure chỉ báo chưa đủ dữ liệu; tối đa 5 ví dụ; cohort aggregation không lộ ai.
2. **Feedback study:** randomization cân bằng, seed lưu lại, chỉ người có research consent; server-side withholding cho nhóm “Chỉ điểm”; 5 câu Likert; withdraw bất cứ lúc nào; bootstrap 95% CI và Hedges g; CSV mã P001…
3. **Teacher time:** median assisted review so với blind rating; bỏ dở sau 30 phút; không nêu số dưới 5 mẫu; machine-auto-complete và teacher-kept-band có Wilson 95% CI.
4. **Reliable change:** so trung bình tối đa 3 bài đầu/cuối; threshold `1.96 × SE(diff)`; SEM từ tối thiểu 10 cặp retest trong 48 giờ hoặc admin nhập kèm nguồn; không dùng RMSE thay SEM.

Acceptance:

- Mọi kết luận có sample count và trạng thái insufficient-data.
- Student, teacher và admin nhìn đúng mức chi tiết theo quyền.
- Delete/withdraw cập nhật cohort/study đúng nhưng không làm audit mất tính truy vết.

### Nhóm H — Gói dịch vụ, giấy phép và thanh toán thử

Task triển khai: `W5-T03`, `W5-N04`.

Vùng code: `src/aicefr/billing/`, billing application service/repository, admin billing pages, config.

Việc phải làm:

1. Plan ladder: Free, Trial 30 ngày, Standard, Advanced; feature chỉ tăng dần; learning của sinh viên không bị khóa.
2. Seat/student limit, AI assessment warning quota, 12-month discount 15%, prorated upgrade, queued renewal/downgrade, 14-day grace.
3. Quote → order → payment session → callback/webhook → receipt → entitlement; mọi bước có idempotency key và audit.
4. Cổng thử nội bộ ký payload; VNPay 2.1.0; Stripe test Checkout; MoMo test `captureWallet`; chỉ load gateway được cấu hình.
5. Xác minh signature, amount, currency, order, gateway và live/test mode trước khi complete.
6. Live payment bị khóa bởi explicit config và không dùng trong W5 QA.
7. Signed license HMAC cho hợp đồng ngoài app; verify expiry/features/student limit.
8. Admin UI có plan comparison, quote, orders, receipt, gateway status và missing-config guidance; không lộ key.

Acceptance:

- Replay, amount tampering, wrong gateway, expired callback, duplicate webhook, timeout và partial failure có test.
- Không có network call thật trong unit/integration CI.

### Nhóm I — Dữ liệu cá nhân, vận hành và bảo trì

Task triển khai: `W5-T01`, `W5-T03`, `W5-T04`.

1. Personal export bổ sung profile, session metadata phù hợp, practice/lesson attempts, achievements, study participation và payment receipt nếu có; không xuất secret/hash.
2. Erasure preview/confirm bao phủ bảng mới, blob/media và cleanup retry; giữ audit tối thiểu không nhận dạng.
3. Retention dry-run mặc định; explicit apply; service-aware cleanup.
4. Backup gồm SQLite, upload, lesson media và manifest hash; restore smoke bắt buộc.
5. Metrics không dùng actor/response/transcript/path làm label.
6. Request/correlation ID xuyên WSGI → application service → worker nhưng log không chứa transcript/audio/PII.

---

## 6. Kế hoạch giao diện chi tiết

Owner chính: Nguyên. Review nội dung AI: Sang. Review quyền và dữ liệu: Thắng.

### 6.1. Design system

- Font Roboto local cho body và heading; preload đúng subset tiếng Việt; fallback không gây layout shift lớn.
- Màu: xanh mực làm màu chính, đỏ rượu làm accent có kiểm soát, surface trung tính; cả light/dark đạt contrast AA.
- Component dùng chung: button, icon button, input, select, tabs, badge, status dot, card, table, dialog, toast, empty/error state, skeleton, pagination, disclosure và audio player.
- Icon dùng sprite SVG tự vẽ; mọi icon-only button có accessible name.
- Background “bậc thang tiếng nói”: contour trên phải, đồi bốn tầng dưới phải; teacher/admin nhạt hơn; không nhận pointer; ẩn khi print; không gây horizontal scroll.
- Motion: page enter, disclosure, progress, dialog, 3D landing và hill breathing; `prefers-reduced-motion` tắt toàn bộ animation không thiết yếu.
- Desktop ≥1024 px: sidebar trái cố định. Tablet: sidebar thu gọn. Mobile 360–430 px: top bar + bottom navigation; action chính luôn reachable bằng một tay.
- Trạng thái của mọi component: default, hover, focus-visible, active, disabled, loading, empty, success và error.

### 6.2. Trang public

| Trang | Nội dung và tương tác bắt buộc |
| --- | --- |
| `/` | Hero ít chữ; giới hạn “hỗ trợ đánh giá”; ba bậc A2/B1/B2; CTA login; đồ họa 3D và hill scene; không hứa chứng chỉ |
| `/login` | Alias/password; Google button chỉ khi configured; lockout/error không lộ account tồn tại; hill scene sau form |
| `/bands` | A2/B1/B2; 5 mặt; nhãn máy đo gián tiếp/không đo/không đánh giá; threshold từ model active; lưu ý nói lắp và Interaction |

### 6.3. Sinh viên

| Trang | Chi tiết |
| --- | --- |
| `/consent` | Version, required/optional choices, research opt-in riêng, withdraw consequence, validation và confirm dialog |
| `/account` | Bốn tab Hồ sơ/Bảo mật/Hoạt động/Dữ liệu; avatar icon/color; speaking goal; theme/font; sessions; Google; export/withdraw |
| `/student/upload` | Chọn task; 30 giây chuẩn bị có skip; upload hoặc recorder; nghe lại; Nộp/Ghi lại; progress; định dạng/dung lượng/error recovery |
| `/progress/{id}` | QUEUED/RUNNING/COMPLETED/REVIEW_REQUIRED/FAILED; auto-refresh có backoff; reason tiếng Việt; link report khi sẵn |
| `/report/{id}` | Overall + band + interval; teacher-final nếu có; ưu tiên luyện; chỉ báo 5 mặt; feedback/evidence/audio seek; limitation/provenance thu gọn |
| `/my-responses` | Filter assessment/practice, status, date, task; pagination; resume/view/delete theo quyền |
| `/my-progress` | Trend, reliable change, pronunciation, 17 achievements, streak, 7-day compare, feedback-study survey nếu được phân |
| `/practice` | Roadmap A2→B1→B2; 18 units/31 lessons; đường nối; current/review state; bài chưa tới lượt làm mờ nhưng không khóa |
| `/practice/lessons/{id}` | Step rail, prompt/media, recorder chung, measurement result, retry/continue, teacher correction note |
| `/practice/review` | Mục ôn hôm nay theo lịch 1/3/7; empty state; batch progress |
| `/practice/results/{id}` | Mission result/evidence, so lần trước, next recommendation; tuyệt đối không band |

### 6.4. Giảng viên

| Trang | Chi tiết |
| --- | --- |
| `/review` | Bảng bốn cột, filter, claim owner/TTL, status, “Duyệt bài tiếp theo”, paging và empty state |
| `/review/{id}` | Sticky audio player; transcript/evidence; AI result; reason tiếng Việt; approve/correct/reject/release/close; preset rationale; conflict recovery |
| `/review/stats` | AI vs teacher-final tách riêng; band chart; QC/review count; pronunciation cohort; teacher-time KPI; insufficient-data state |
| `/rate` | Blind assignments, due/completed, không lộ machine result hoặc identity |
| `/rate/{id}` | Audio + blind form, autosave local draft, one-time submit, unrateable path, confirm dialog |
| `/teach` | Danh sách path/draft/published; create/import/export; entitlement state |
| `/teach/lessons/{id}` | Lesson builder, reorder, 9 step types, lint, preview, sample audio, publish version |
| `/teach/insights` | Attempts cần xem, evidence, audio, machine observation, teacher override và audit |

### 6.5. Quản trị viên

Trang `/admin` dùng tab hoặc section rõ ràng; URL/state giữ được khi reload:

- Tổng quan: health/readiness, worker local/model/database/blob store, không hiện secret/path nhạy cảm.
- Tài khoản: create single/batch, password phiếu in, detail, role, reset, lock/unlock, enable/disable, sessions, Google, CSV.
- Task đánh giá: version/create/close; không sửa wording của version đã có response.
- Models: registry, compatibility, checksum/pin, activate confirmation.
- Config: QC version/CAS, Google setup status, measurement error và source.
- Audit: filter actor/action/time/request ID; payload đã redact.
- Dữ liệu: research export, erasure preview/confirm, maintenance/retention/backup.
- Chấm mù: batch setup/list/status/adjudication/agreement report/CSV.
- Study: start, phase transition, participation/survey counts, report/CSV và exploratory disclaimer.
- Billing: plan, quote, orders, gateways, receipts, license; sandbox label nổi bật.

Trang payment/result/receipt phải phân biệt rõ `PENDING`, `PAID`, `FAILED`, `CANCELLED`, retry an toàn và không tự refresh gây double-submit.

### 6.6. Browser QA matrix

Chạy Chromium tối thiểu ở 1280×800 và 390×844; với critical journey chạy thêm Firefox nếu môi trường có sẵn.

- Public: landing → login → bands.
- Student: consent → upload/record → progress → report → evidence seek → practice lesson → result → progress/account.
- Teacher: queue → claim → review → close; blind rate; teach draft → preview → publish → insight override.
- Admin: create account → config/model → rating batch → study → billing sandbox → erasure preview.
- Mỗi lane kiểm console error, failed request, external request, horizontal overflow, keyboard navigation, focus return sau dialog, reduced motion, light/dark và screenshot.

---

## 7. API và error contract

API dùng `/api/v1`; browser page giữ URL thân thiện hiện có. Mỗi endpoint mới phải có success test và authorization failure test.

Nhóm endpoint cần hoàn thiện:

- Auth/account: login/logout/me/consent/password/profile/sessions/activity/Google.
- Assessment: submit/status/report/audio/history/progress/tasks/practice summary.
- Review/rating: queue/claim/release/decision/KPI/stats/rating batches/forms/adjudication/report/export.
- Learning: paths/lessons/steps/attempts/media/review/achievements/pronunciation/teacher authoring/insights.
- Admin: accounts/models/config/export/erase/measurement error/health/audit.
- Study: create/status/report/export/enrollment/survey/withdraw.
- Billing: plans/quotes/orders/gateway open/callback/webhook/receipts/license.

Error body thống nhất:

```json
{
  "error": {
    "code": "STABLE_REASON_CODE",
    "message": "Thông báo tiếng Việt an toàn cho người dùng",
    "request_id": "opaque-id",
    "details": {}
  }
}
```

- `details` không chứa secret, path nội bộ, transcript hoặc PII.
- `400` input sai; `401` chưa đăng nhập; `403` sai role/consent; `404` absent và foreign resource; `409` revision/claim/idempotency conflict; `422` business validation; `429` rate/lockout; `503` model/worker local/dependency chưa sẵn.
- UI map reason code sang tiếng Việt và recovery action; không hiển thị raw exception.

---

## 8. Phân công và ranh giới file

Tất cả task trong bảng dưới là **bắt buộc hoàn thành trong W5**, không phải backlog tùy chọn. Một người chỉ được ghi hoàn thành phần W5 của mình khi mọi task mang tên người đó đạt `Task Done Gate` ở mục 9.

| Người | Task bắt buộc | Vùng sở hữu chính | Reviewer bắt buộc |
| --- | --- | --- | --- |
| Thắng | `W5-T01`–`W5-T04` | composition root, SQLite/migration, auth, account, billing, vận hành, CI | Sang review backend/AI contract; Nguyên review luồng admin khi có UI impact |
| Sang | `W5-S01`–`W5-S04` | Trust Layer, practice, lessons, achievement, pronunciation, research/measurement | Thắng review persistence/security; Nguyên review dữ liệu cần hiển thị |
| Nguyên | `W5-N01`–`W5-N04` | design system, page/template/static, student/teacher/admin UX, browser QA | Thắng review quyền/API; Sang review wording và evidence AI |

File dùng chung cần khóa theo lượt: manifest, composition root, schema migration, base template, global stylesheet, route registry và test fixtures. PR thay contract dùng chung phải merge trước các PR phụ thuộc; không resolve conflict bằng cách chọn nguyên một phía.

---

## 9. Task bắt buộc theo từng người

### 9.1. Thắng — nền tảng, dữ liệu, tài khoản, billing và tích hợp

#### W5-T01 — Monolith foundation, SQLite migration và worker

- **Owner:** Thắng.
- **Reviewer:** Sang.
- **Phụ thuộc:** W5-G0–G2.
- **Chặn:** `W5-T02`, `W5-T03`, phần persistence của `W5-S02`–`W5-S04`, toàn bộ browser QA trên database đã migration.
- **Vùng code:** `pyproject.toml`, `src/aicefr/local/`, `src/aicefr/storage/`, composition root, migration runner, worker và test repository/local.

**Implementation bắt buộc:**

1. Đo baseline test/coverage và ghi revision; backup SQLite/blob demo và restore thử được.
2. Mở rộng schema cho profile/session/Google, learning, achievement, rating, study, measurement error, billing, durable job và cleanup intent.
3. Viết migration từ database v4; migration chạy lặp không nhân đôi dữ liệu; foreign key, unique key và transaction được bật đúng.
4. Mở rộng composition root bằng dependency injection; không thêm global mutable singleton hoặc database thứ hai.
5. Worker có lease, giới hạn retry, interrupted-job recovery và idempotency; restart không tạo report/audit trùng.
6. Readiness kiểm SQLite, blob store, worker và model artifact; response không lộ path/secret.
7. Wheel đóng gói đầy đủ code, migration, template/static metadata cần chạy.

**Test bắt buộc:** migration preserve count/hash/report; rollback khi migration lỗi; SQLite foreign key/unique; worker duplicate/restart/lease; clean-wheel boot; readiness success/failure.

**Evidence bắt buộc:** migration matrix trước/sau, backup/restore log, targeted pytest, wheel install/boot log, diff và checklist không có D043 dependency.

**Task Done Gate:** chỉ `DONE` khi database cũ migrate và restore được, app khởi động từ wheel sạch, worker restart an toàn và reviewer không còn finding `BLOCKER/MAJOR`.

#### W5-T02 — Identity, account, session, consent và Google PKCE

- **Owner:** Thắng.
- **Reviewer:** Nguyên kiểm user flow; Sang kiểm không làm lộ dữ liệu vào AI/report.
- **Phụ thuộc:** `W5-T01` schema/profile/session.
- **Cung cấp API cho:** `W5-N01`, `W5-N04`.
- **Vùng code:** `src/aicefr/auth/`, account/session/consent repository, portal/API handler liên quan và test auth.

**Implementation bắt buộc:**

1. Profile với avatar icon/màu, speaking goal; không có ảnh thật hoặc tên thật.
2. Đổi password đúng rule, password tạm buộc đổi, revoke phiên khác, session list và logout từng phiên.
3. Admin tạo một/batch account tối đa 200 theo transaction; reset password tạm, unlock, enable/disable, đổi role, logout all, unlink Google; chặn tự thao tác nguy hiểm.
4. Account activity ghi login, failed login và security change cho alias tồn tại nhưng không log credential.
5. Google authorization code + PKCE S256 + state + nonce; flow cookie ký HMAC; validate issuer/audience/expiry/nonce; không auto-signup, không lưu email/name/avatar.
6. Consent và research opt-in giữ version; withdraw làm vô hiệu quyền nghiên cứu và study participation đúng contract.

**Test bắt buộc:** lockout, temporary password, revoke session, session fixation, batch rollback, role escalation, forged OAuth cookie, invalid state/nonce/issuer/audience, duplicate subject, consent withdrawal và secret exposure.

**Evidence bắt buộc:** API contract/result, security test log, account migration check và browser handoff checklist cho Nguyên.

**Task Done Gate:** chỉ `DONE` khi toàn bộ mutation có authorization/audit, security tests xanh và UI có đủ API ổn định để chạy account journey.

#### W5-T03 — Billing sandbox, license và data operations

- **Owner:** Thắng.
- **Reviewer:** Sang kiểm signature/statistical export boundary; Nguyên kiểm admin flow.
- **Phụ thuộc:** `W5-T01`; account/admin contract của `W5-T02`.
- **Cung cấp API cho:** `W5-N04`.
- **Vùng code:** `src/aicefr/billing/`, billing/data repository, admin API, export/erase/retention/backup và test tương ứng.

**Implementation bắt buộc:**

1. Free/Trial/Standard/Advanced, entitlement tăng dần, không khóa việc học; quote, order, receipt, grace period, proration và renewal/downgrade.
2. Cổng thử nội bộ là mặc định; VNPay/Stripe/MoMo chỉ được enable bằng config test; live payment khóa cứng ngoài W5.
3. Verify signature, order, amount, currency, gateway, mode; callback/webhook idempotent và chống replay.
4. Signed license HMAC có expiry/features/student limit và audit.
5. Personal export bao phủ dữ liệu W5 mà không chứa password/session hash/secret.
6. Erasure preview/confirm, retention dry-run/apply, backup/restore và cleanup retry bao phủ bảng/blob mới.

**Test bắt buộc:** tampered amount/signature, wrong gateway/mode, replay, duplicate webhook, timeout, transaction rollback, export permission, erase preview/confirm, retention và backup restore.

**Evidence bắt buộc:** sandbox flow log, tampering regression, data-control manifest, secret scan và API handoff cho admin UI.

**Task Done Gate:** chỉ `DONE` khi không có network call thật trong CI, mọi payment mutation idempotent, data operation restore được và reviewer security không còn finding bắt buộc.

#### W5-T04 — Tích hợp monolith, CI, run guide và final technical package

- **Owner:** Thắng.
- **Reviewer:** Sang kiểm pipeline/model; Nguyên kiểm critical journey/browser package.
- **Phụ thuộc:** `W5-T01`–`W5-T03`, `W5-S01`–`W5-S04`, `W5-N01`–`W5-N04`.
- **Vùng code/tài liệu:** composition root, route registry, CI, health/readiness, README, local-run guide, env example, evidence manifest.

**Implementation bắt buộc:**

1. Nối tất cả module vào một entrypoint; không có app thứ hai hoặc route trùng.
2. Một lệnh khởi động được student/teacher/admin journey; model thiếu phải báo đúng, model có sẵn chạy pipeline thật.
3. CI chạy format, lint, full tests, coverage, wheel, forbidden-file và secret scan.
4. Chạy restore smoke rồi mở report cũ; chạy real audio smoke với audio có quyền và lưu evidence ngoài Git.
5. Cập nhật hướng dẫn cài/chạy/config/backup/restore; không có bước ngầm phụ thuộc state máy cá nhân.
6. Tổng hợp final revision, commands, counts, coverage, browser result, open limitation và AI Prompt Log W05 của Thắng.

**Task Done Gate:** chỉ `DONE` khi full required checks chạy trên final revision, monolith dựng được từ môi trường sạch, critical journey qua và package đủ để Codex review độc lập.

### 9.2. Sang — AI pipeline, learning engine và bằng chứng nghiên cứu

#### W5-S01 — Trust Layer và refusal behavior

- **Owner:** Sang.
- **Reviewer:** Thắng.
- **Phụ thuộc:** job/report contract của `W5-T01`; scorer/artifact hiện hành.
- **Cung cấp dữ liệu cho:** `W5-N01`, `W5-N03`.
- **Vùng code:** `src/aicefr/asr/`, `features/`, `scoring/`, `pipeline/`, `report/`, calibration/refusal tools và test.

**Implementation bắt buộc:** LID; off-topic/prompt-reading guard; conformal CV+ alpha 0.10; multi-band set sinh `SCORE_NEAR_BOUNDARY`; năm criterion indicators có nhãn “chỉ báo”; provenance/version/checksum; refusal benchmark reproducible.

**Test bắt buộc:** English/non-English, on/off-topic, prompt reading, confidence boundary, missing/wrong-checksum calibration, one/multi-band set, no-direct-score-penalty, old-report compatibility và retry cùng job.

**Evidence bắt buộc:** test vector, calibration/refusal output hash, targeted coverage, changed behavior matrix và UI payload handoff.

**Task Done Gate:** chỉ `DONE` khi không guard nào trực tiếp trừ điểm, mọi uncertainty route đúng teacher review và report có provenance đầy đủ.

#### W5-S02 — Practice missions, lesson engine và spaced review

- **Owner:** Sang.
- **Reviewer:** Thắng kiểm persistence/API contract; Nguyên kiểm payload dùng cho UI.
- **Phụ thuộc:** repository interface của `W5-T01`.
- **Cung cấp dữ liệu cho:** `W5-N02`.
- **Vùng code:** `src/aicefr/practice/`, `lessons/`, learning application service và test domain/integration.

**Implementation bắt buộc:** 15 practice missions; bảy `MissionKind`; recommendation giải thích được; Path→Unit→Lesson→Step; bốn bậc lesson; chín step types; alignment/lemma; QC tối thiểu một giây; publish immutable version; seed 18 chặng/31 bài idempotent; lịch ôn 1/3/7; teacher override không thành điểm.

**Test bắt buộc:** mission rule/evidence, no-band invariant, recommendation fallback, alignment/lemma/silence, publish immutability, reorder/import/export, seed idempotency, schedule boundary, permission và delete attempt.

**Evidence bắt buộc:** domain/API payload examples, seed manifest/hash, targeted tests/coverage và danh sách invariant cho UI.

**Task Done Gate:** chỉ `DONE` khi assessment/practice data tách đúng, lesson published bất biến, không có band trong practice và recommendation/review schedule deterministic.

#### W5-S03 — Achievement, streak và phát âm Việt

- **Owner:** Sang.
- **Reviewer:** Thắng kiểm storage/delete; Nguyên kiểm wording/display state.
- **Phụ thuộc:** `W5-S02`; achievement/pronunciation tables của `W5-T01`.
- **Cung cấp dữ liệu cho:** `W5-N02` và `W5-N01` trang progress.

**Implementation bắt buộc:** 17 achievements theo effort; streak/timezone Asia/Ho_Chi_Minh/ngày nghỉ; 7-day comparison; seen state; `vi-pron-v1` với năm nhóm lỗi; exposure threshold 8; tối đa 5 examples; loại teacher-corrected word; cohort aggregation không lộ danh tính.

**Test bắt buộc:** timezone boundary, retry/duplicate, deletion không thu hồi achievement, seen state, error classification, exposure 7/8, example cap, corrected word exclusion và anonymous cohort.

**Evidence bắt buộc:** achievement catalogue, pronunciation fixtures, unit/integration results và payload states đủ/thiếu dữ liệu.

**Task Done Gate:** chỉ `DONE` khi không có reward theo score/band, không leaderboard, pronunciation không bị gọi là điểm và cohort không thể truy ngược cá nhân.

#### W5-S04 — Blind metrics, feedback study, teacher-time và reliable change

- **Owner:** Sang.
- **Reviewer:** Thắng kiểm privacy/persistence; Nguyên kiểm presentation contract.
- **Phụ thuộc:** rating/study/review-session/measurement-error schema của `W5-T01`; review events hiện hành.
- **Cung cấp dữ liệu cho:** `W5-N03`, `W5-N04`.

**Implementation bắt buộc:** seeded two-rater assignment; adjudication rule; human-human trước machine-human metrics; speaker bootstrap; feedback study balancing/withholding/survey/withdraw/Hedges g; teacher-time median và Wilson CI; reliable change từ SEM với insufficient-data state.

**Test bắt buộc:** assignment collision, blind eligibility, adjudicator conflict, consent withdrawal, deterministic randomization, server-side feedback withholding, bootstrap seed, sample thresholds 5/10, SEM source, retest 48 giờ và không dùng RMSE thay SEM.

**Evidence bắt buộc:** metric fixtures/expected outputs, privacy review, deterministic rerun hashes, coverage và payload handoff.

**Task Done Gate:** chỉ `DONE` khi metric không chạy trên mẫu không đủ, mọi kết luận kèm sample/CI/source phù hợp và blind/research data không lộ alias.

### 9.3. Nguyên — toàn bộ trải nghiệm người dùng và browser QA

#### W5-N01 — Design system, public pages, account và assessment student flow

- **Owner:** Nguyên.
- **Reviewer:** Thắng kiểm auth/API; Sang kiểm wording CEFR/AI.
- **Phụ thuộc:** auth API `W5-T02`; Trust payload `W5-S01`.
- **Vùng code:** base template, global CSS/JS, icons/art/fonts, landing/login/bands/consent/account/upload/progress/report/my-responses/my-progress.

**Implementation bắt buộc:** role navigation; desktop sidebar/mobile top+bottom nav; Roboto local; light/dark; art/motion/reduced-motion; reusable component states; recorder nghe lại trước nộp; chuẩn bị 30 giây; report ưu tiên kết quả/evidence/recovery; account bốn tab; full responsive/accessibility states.

**Browser/test bắt buộc:** public→login; consent; upload/record/re-record; progress; report/audio seek; account/session/Google disabled+configured mock; 1280×800 và 390×844; keyboard/focus/contrast/reduced-motion/no-overflow; template forbidden claims.

**Evidence bắt buộc:** screenshot matrix, browser result JSON, console/network summary, template tests và API mismatch list đã đóng.

**Task Done Gate:** chỉ `DONE` khi student critical journey hoàn chỉnh trên desktop/mobile, không console error/failed request và không có thông tin chỉ truyền bằng màu/chuyển động.

#### W5-N02 — Practice, lesson, progress, achievement và pronunciation UI

- **Owner:** Nguyên.
- **Reviewer:** Sang kiểm learning semantics; Thắng kiểm owner permission.
- **Phụ thuộc:** `W5-S02`, `W5-S03`; persistence/API wiring của `W5-T01`.
- **Vùng code:** practice roadmap/review/result, lesson player/builder shared components, progress/achievement/pronunciation blocks.

**Implementation bắt buộc:** roadmap A2→B1→B2 dạng đường đi; 18 chặng/31 bài; lesson step rail; recorder/media/result/retry/continue; ôn hôm nay; practice result không band; achievement/streak cards; pronunciation đủ/thiếu dữ liệu; empty/loading/error/recovery cho mọi page.

**Browser/test bắt buộc:** lesson success/failure/retry; review schedule; result no-band assertion; achievement seen; mobile sticky action không che nội dung; delete attempt permission; teacher correction note.

**Evidence bắt buộc:** desktop/mobile screenshots, DOM assertions cho no-band, browser logs và trace page→API→state.

**Task Done Gate:** chỉ `DONE` khi student hoàn tất được một lesson và một review item, mọi state hiển thị đúng và UI không tạo claim vượt dữ liệu Sang cung cấp.

#### W5-N03 — Teacher review, blind rating, authoring và insights UI

- **Owner:** Nguyên.
- **Reviewer:** Thắng kiểm quyền/claim; Sang kiểm blind/metric/lesson contract.
- **Phụ thuộc:** review contract hiện hành, `W5-S02`, `W5-S04`, API/storage của `W5-T01`.
- **Vùng code:** review queue/detail/stats, rate list/form, teach paths/lesson builder/insights và JS tương ứng.

**Implementation bắt buộc:** queue bốn cột/filter/claim TTL/next; sticky player và evidence; approve/correct/reject/release/close với conflict recovery; blind form không lộ identity/machine result; one-time submit; lesson create/reorder/lint/preview/publish; insight override có audit; stats AI và teacher-final tách riêng.

**Browser/test bắt buộc:** claim contention/revision conflict; blind URL leakage attempts; one-time submit; unrateable/adjudication states; lesson draft→preview→publish; insight override; keyboard navigation và responsive table/card conversion.

**Evidence bắt buộc:** browser result/screenshot, blind-leak security checklist, DOM/API assertions và defect log.

**Task Done Gate:** chỉ `DONE` khi teacher journey chạy đầu-cuối, blind page không lộ dữ liệu cấm qua UI/API và mọi mutation có success/error/conflict recovery.

#### W5-N04 — Admin UI, full browser regression và UI handoff

- **Owner:** Nguyên.
- **Reviewer:** Thắng kiểm admin/security/payment; Sang kiểm research/measurement wording.
- **Phụ thuộc:** `W5-T02`, `W5-T03`, `W5-S04`, cùng các page hoàn tất ở `W5-N01`–`W5-N03`.
- **Vùng code:** admin overview/accounts/tasks/models/config/audit/data/rating/study/billing pages, global responsive polish, browser QA scripts và UI evidence.

**Implementation bắt buộc:** account single/batch/temp-password print; model/config/QC/Google/SEM; data export/erase/maintenance; rating batch/adjudication/agreement; study lifecycle/report/CSV; billing plan/order/receipt/gateway status; sandbox label; complete loading/empty/error/success/confirm state.

**Browser/test bắt buộc:** ba role không vượt quyền; admin critical journey; sandbox payment success/failure/replay-visible-state; study and rating; erasure preview; no secret/path in DOM; full desktop/mobile regression; console/failed/external request = 0 ngoại trừ request mock đã khai báo.

**Evidence bắt buộc:** full browser matrix/result JSON/screenshots, accessibility checklist, visual regression list, UI/API inventory và AI Prompt Log W05 của Nguyên.

**Task Done Gate:** chỉ `DONE` khi tất cả page public/student/teacher/admin trong mục 6 đã có trạng thái đầy đủ, browser QA chạy trên final integrated revision và không còn finding UI `BLOCKER/MAJOR`.

### 9.4. Work package bắt buộc bên trong từng task

Các mã `.1`, `.2` dưới đây là checklist bắt buộc, không phải task tùy chọn. Owner không được bỏ một work package rồi vẫn đánh dấu task cha `DONE`. Mỗi package phải có actual diff, test được nêu và đường dẫn evidence trong report task.

#### W5-T01 — Work packages

| ID | Đầu ra bắt buộc | Input/contract | Check trước bàn giao |
| --- | --- | --- | --- |
| W5-T01.1 | Baseline manifest, test/coverage hiện tại, SQLite/blob backup và restore log | target `3b2d2b7`, M16-FR-002 | M16-TEST-001/002, không ghi PASS nếu chưa chạy |
| W5-T01.2 | Migration registry + lock + preflight/verify; đường nâng từ schema hiện hành và fresh install | M16 Specification | failure injection rollback, rerun idempotent |
| W5-T01.3 | Schema identity, learning, rating/research, billing, job/cleanup theo từng migration nhỏ | M10–M14 schema contracts | FK/unique/index/transaction tests bằng file SQLite thật |
| W5-T01.4 | Repository interfaces và providers; application service không mở DB trực tiếp | M09–M14 payload/model freeze | contract tests, không import vòng/global singleton |
| W5-T01.5 | Durable job lease/CAS/retry/recovery/idempotency | M16-FR-003 | crash, duplicate, two-worker, max-retry tests |
| W5-T01.6 | Readiness/liveness, package-data và clean-wheel boot tối thiểu | M15/M16 | M16-TEST-005/008/010; forbidden D043 scan |

#### W5-T02 — Work packages

| ID | Đầu ra bắt buộc | Input/contract | Check trước bàn giao |
| --- | --- | --- | --- |
| W5-T02.1 | Profile allowlist, API và migration compatibility | M11-FR-001 | M11-TEST-001/010 |
| W5-T02.2 | Password policy, temp-password gate, lockout và session rotation | M11-FR-002/003 | M11-TEST-002/003 |
| W5-T02.3 | Session list/revoke/current device/activity/redacted audit | M11-FR-004 | foreign session 404, no credential log |
| W5-T02.4 | Admin single/batch atomic operations và self-action guard | M11-FR-005 | M11-TEST-004/005, batch rollback |
| W5-T02.5 | Google PKCE/signed flow/ID-token validation/link-login-unlink | M11-FR-006/007 | M11-TEST-006/007, all failure branches |
| W5-T02.6 | Consent version/research withdrawal propagation | M11-FR-008 | M11-TEST-008 + M12/M13 downstream contract |
| W5-T02.7 | API examples, authorization matrix và UI handoff | M15 view-model needs | consumer contract test trước N01/N04 |

#### W5-T03 — Work packages

| ID | Đầu ra bắt buộc | Input/contract | Check trước bàn giao |
| --- | --- | --- | --- |
| W5-T03.1 | Plan/entitlement/usage/quote/proration/grace rules | M14-FR-001–003 | M14-TEST-001/002 |
| W5-T03.2 | Billing repository và state machine | M14 Specification | event/order unique, rollback/race tests |
| W5-T03.3 | Sandbox gateway + settle signature/idempotency/replay defense | M14-FR-004/006 | M14-TEST-003–005 |
| W5-T03.4 | Optional test adapters + disabled/live guard + setup status | M14-FR-005 | no real network in CI, M14-TEST-006/008 |
| W5-T03.5 | Signed license canonical payload/key version/audit | M14-FR-007 | M14-TEST-007 |
| W5-T03.6 | Export/erase/retention/backup coverage cho bảng/blob W5 | M16-FR-005 | M16-TEST-006/007 + data manifest |

#### W5-T04 — Work packages

| ID | Đầu ra bắt buộc | Check trước bàn giao |
| --- | --- | --- |
| W5-T04.1 | Một composition root và route registry; tất cả module được inject | route duplication/import-cycle/boot test |
| W5-T04.2 | Error/reason registry, request ID và redacted observability thống nhất | M16-TEST-008; API contract regression |
| W5-T04.3 | CI format/lint/targeted/full/coverage/build/forbidden/secret gates | cùng final revision, không \` |
| W5-T04.4 | Clean venv wheel install/boot + backup restore + old report read | M16-TEST-005/007 |
| W5-T04.5 | Real-audio smoke nếu prerequisite có; nếu thiếu ghi `NOT_RUN` + blocker | model/audio provenance, không fake fallback |
| W5-T04.6 | Final evidence manifest, run/config/backup/restore guide và AI log | SHA/fingerprint/commands/counts/limits đầy đủ |

#### W5-S01 — Work packages

| ID | Đầu ra bắt buộc | Check trước bàn giao |
| --- | --- | --- |
| W5-S01.1 | Immutable Language/Guard/Conformal/Trust models + reason enum | M09-TEST-001/002 schema contract |
| W5-S01.2 | LID và confidence-boundary policy | English/non-English/boundary unit tests |
| W5-S01.3 | Off-topic/prompt-reading evidence, no-score-penalty invariant | same scorer input/output regression |
| W5-S01.4 | Conformal artifact loader/hash/schema/set | M09-TEST-003, no fallback |
| W5-S01.5 | Pipeline/report/review integration + old report compatibility | M09-TEST-004/005/007/008 |
| W5-S01.6 | Calibration/refusal CLI, manifest/seed/hash và no-leakage evidence | M09-TEST-006/009 + handoff payload |

#### W5-S02 — Work packages

| ID | Đầu ra bắt buộc | Check trước bàn giao |
| --- | --- | --- |
| W5-S02.1 | Mission catalogue 5×3/versioned seed + seven rule kinds | M10-TEST-001 |
| W5-S02.2 | Purpose-aware learning pipeline không scorer/queue/export | M10-TEST-002 |
| W5-S02.3 | Deterministic recommendation + fallback/explanation | M10-TEST-003 |
| W5-S02.4 | Lesson/version/step domain, nine step rules/alignment/lemma/QC | M10-TEST-004/005 |
| W5-S02.5 | Authoring/lint/media/preview/publish/import-export | permissions, immutable publish, roundtrip |
| W5-S02.6 | Seed 18/31 idempotent và không overwrite teacher data | M10-TEST-006 + manifest/hash |
| W5-S02.7 | Spaced review và teacher override/audit | M10-TEST-007/010/011 |

#### W5-S03 — Work packages

| ID | Đầu ra bắt buộc | Check trước bàn giao |
| --- | --- | --- |
| W5-S03.1 | Achievement catalogue 17 item + effort-only Facts | test source/object không có score/band field |
| W5-S03.2 | Unlock/idempotency/no-revoke/seen/export-erasure hooks | M10-TEST-008/011 |
| W5-S03.3 | Streak VN timezone/rest day/current record/7-day comparison | midnight, duplicate/retry/deletion boundary tests |
| W5-S03.4 | `vi-pron-v1` five-pattern classifier/order/fixtures | M13-TEST-001 |
| W5-S03.5 | Student profile exposure 7/8/cap5/correction exclusion | M13-TEST-002 |
| W5-S03.6 | Anonymous cohort aggregation + payload disclosure | no identity/link, role tests |

#### W5-S04 — Work packages

| ID | Đầu ra bắt buộc | Check trước bàn giao |
| --- | --- | --- |
| W5-S04.1 | Seeded two-rater assignment/eligibility/machine-seen exclusion | M12-TEST-001–004 |
| W5-S04.2 | Immutable sheet/adjudication/reference/agreement/bootstrap | M12-TEST-005–008 |
| W5-S04.3 | Feedback study assignment/lifecycle/server-side gate/withdraw | M13-TEST-003/004 |
| W5-S04.4 | Survey/pre-post/bootstrap/Hedges g/pseudonymous CSV | M13-TEST-005–007 |
| W5-S04.5 | Review-session timing/median/Wilson KPI | M13-TEST-008 |
| W5-S04.6 | SEM config/retest pairing/reliable-change states | M13-TEST-009/010 |
| W5-S04.7 | Privacy/statistical payloads, deterministic hashes và insufficient matrix | M12/M13 security + API handoff |

#### W5-N01 — Work packages

| ID | Đầu ra bắt buộc | Check trước bàn giao |
| --- | --- | --- |
| W5-N01.1 | Token/component/base shell/role navigation/theme/Roboto/assets | M15-TEST-001/002/008–010 |
| W5-N01.2 | Landing/login/bands với claim guard | M15-TEST-012, mobile/desktop |
| W5-N01.3 | Consent và account bốn tab/Google states | M11-TEST-007/009 |
| W5-N01.4 | Recorder/upload/preparation/playback/rerecord/submit | M15-TEST-003 |
| W5-N01.5 | Progress/history/report/audio evidence/trust states | M15-TEST-004, old/new report |
| W5-N01.6 | Reliable change/pronunciation/student-study blocks | M13-TEST-004/011, null/insufficient wording |
| W5-N01.7 | Student browser pack desktop/mobile/a11y/network/console | screenshot + result JSON + hashes |

#### W5-N02 — Work packages

| ID | Đầu ra bắt buộc | Check trước bàn giao |
| --- | --- | --- |
| W5-N02.1 | A2→B1→B2 roadmap 18/31 and next/review states | API/DOM order and empty/error states |
| W5-N02.2 | Lesson player/step rail/media/recorder/result/retry/continue | success/failure/multi-round browser tests |
| W5-N02.3 | Review-due batch and 1/3/7 feedback | M10-TEST-007/009 |
| W5-N02.4 | Practice result/recommendation/previous comparison with no-band assertion | M10-AC-002/003 DOM/API assertions |
| W5-N02.5 | Achievement/streak/pronunciation đủ-thiếu data | M10/M13 payload-state matrix |
| W5-N02.6 | Mobile sticky/focus/delete permission/teacher-correction states | M15-TEST-005/008 |

#### W5-N03 — Work packages

| ID | Đầu ra bắt buộc | Check trước bàn giao |
| --- | --- | --- |
| W5-N03.1 | Review queue/filter/count/claim TTL/next/empty | contention, expiry and role tests |
| W5-N03.2 | Review detail player/evidence/actions/conflict recovery | stale revision/close/release tests |
| W5-N03.3 | Blind list/sheet/local draft/one-time/unrateable | M12-TEST-003/005/009, DOM/network leak scan |
| W5-N03.4 | Stats AI vs teacher, cohort pronunciation, KPI insufficient | M13-TEST-002/008/011 |
| W5-N03.5 | Teach path/lesson builder/reorder/lint/preview/publish/import-export | M10-TEST-004/006/009/010 |
| W5-N03.6 | Insight audio/evidence/override/audit + responsive/keyboard | M10-TEST-009/010 |

#### W5-N04 — Work packages

| ID | Đầu ra bắt buộc | Check trước bàn giao |
| --- | --- | --- |
| W5-N04.1 | Admin overview/accounts/temp-password/config/model/QC/Google | role/self-action/secret/path tests |
| W5-N04.2 | Data export/erase preview-confirm/maintenance/backup states | M16-TEST-006/007 browser handoff |
| W5-N04.3 | Rating batch/adjudication/agreement/export screens | M12-TEST-002/006–009 |
| W5-N04.4 | Study lifecycle/report/CSV/SEM config screens | M13-TEST-003/005–011 |
| W5-N04.5 | Billing plan/quote/order/result/receipt/gateway sandbox states | M14-TEST-005/008/009 |
| W5-N04.6 | Full cross-role authorization, direct URL and forbidden DOM scan | M15-TEST-002/006/007/012 |
| W5-N04.7 | Final browser/a11y/responsive/motion package on integrated revision | M15-TEST-001–012, console/network/external request summary |

### 9.5. Thứ tự merge theo dependency, không theo lịch ngày

1. **Contract foundation:** W5-T01.1–T01.4 và payload/enums của M09–M14 được review trước; đây là input cho Sang/Nguyên.
2. **Independent domain slices:** W5-S01.1–S01.4, S02.1/S02.3/S02.4, S03.1/S03.4 và S04 pure logic có thể làm song song khi contract đã freeze.
3. **Persistence/integration slices:** W5-T01.5–T01.6 cùng repository-backed portions của S01–S04; mỗi slice merge sau targeted migration/repository test.
4. **Identity/billing APIs:** W5-T02, W5-T03 hoàn tất consumer contract trước N01/N04 tương ứng.
5. **UI vertical slices:** N01 → N02/N03 → N04 full regression; từng UI task chỉ bắt đầu khi API cụ thể đã freeze, không chờ toàn bộ backend.
6. **Final gate:** W5-T04 chỉ đóng sau final merge của 11 task còn lại và N04.7 chạy lại trên cùng revision.

Nếu một contract thay đổi sau consumer đã bắt đầu, producer phải cập nhật schema/example/contract test trước; consumer rebase và chạy lại targeted test. Không “sửa tạm ở UI” để che mismatch.

### 9.6. Ma trận SDD → task → evidence

| Task W5 | Module task bắt buộc | Test/AC chính | Evidence tối thiểu |
| --- | --- | --- | --- |
| W5-T01 | M16-TASK-001–003; M10/11/12/13/14 repository tasks | M16-AC-001–004; migration tests từng module | baseline, migration matrix, worker/clean-wheel logs |
| W5-T02 | M11-TASK-001–005 | M11-AC-001–007 | auth security log, API examples, audit/redaction scan |
| W5-T03 | M14-TASK-001–004; M16-TASK-004 | M14-AC-001–007; M16-AC-005 | payment tamper/replay, license, data-control manifest |
| W5-T04 | M09/10/11/12/13/14 final tasks; M15-TASK-007; M16-TASK-005/006 | all module integration AC | final SHA/fingerprint, full checks, smoke, docs |
| W5-S01 | M09-TASK-001–004 | M09-AC-001–007 | vectors, artifact/output hashes, coverage, payload |
| W5-S02 | M10-TASK-002–004 | M10-AC-001–006 | seed manifest, rule fixtures, API examples |
| W5-S03 | M10-TASK-005; M13-TASK-002 | M10-AC-007; M13-AC-001/002 | catalogue, timezone/pronunciation fixtures, privacy check |
| W5-S04 | M12-TASK-002/003; M13-TASK-003/004 | M12-AC-001–006; M13-AC-003–007 | deterministic hashes, metric fixtures, privacy review |
| W5-N01 | M11-TASK-006; M13-TASK-005; M15-TASK-001/002 | M11-AC-008; M15-AC-001–005 | student screenshots/result JSON/console-network |
| W5-N02 | M10-TASK-006; M15-TASK-003 | M10-AC-008; M15-AC-004/005 | lesson/review trace, no-band DOM evidence |
| W5-N03 | M10-TASK-007; M12-TASK-004; M13-TASK-006; M15-TASK-004 | teacher/blind/authoring AC | security checklist, conflicts, browser evidence |
| W5-N04 | M11-TASK-007; M12-TASK-005; M13-TASK-007; M14-TASK-005; M15-TASK-005/006 | admin/security/full UI AC | full matrix, a11y, secret scan, defect log |

### 9.7. Quy tắc trạng thái task

- `TODO`: chưa bắt đầu hoặc dependency chưa sẵn.
- `BLOCKED`: chưa được phép bắt đầu vì SDD/dependency/quyết định bắt buộc chưa sẵn; phải ghi blocker và điều kiện gỡ.
- `IN_PROGRESS`: owner đang implement; chỉ một owner sửa vùng code đã khóa.
- `IN_REVIEW`: có actual diff, test và evidence để reviewer kiểm tra.
- `CHANGES_REQUIRED`: còn finding bắt buộc; chưa được tính hoàn thành.
- `DONE`: đạt đúng `Task Done Gate`, review xong và evidence gắn final task revision.
- Không dùng “gần xong”, “xong code”, “đợi test” thay cho `DONE`.
- Task phụ thuộc không được đánh dấu `DONE` nếu integration với dependency chưa chạy.
- Mỗi owner phải hoàn tất toàn bộ bốn task của mình trong W5; task chưa đạt phải ghi `PENDING/BLOCKED` cùng lý do và không được tuyên bố phần việc cá nhân hoàn thành.

Trạng thái khởi tạo của cả 12 task là `BLOCKED`: M09–M16 chưa có user verdict Phase 01/03/04/05. Sau khi module liên quan được duyệt đủ và dependency trực tiếp sẵn sàng, owner chuyển task sang `TODO`, rồi `IN_PROGRESS`; không backdate trạng thái.

---

## 10. Test plan và quality gate

### 10.1. Automated tests

1. Unit: domain rule thuần của Trust Layer, lessons, achievements, research, payment signature và entitlement.
2. Repository: SQLite file thật; migration; transaction rollback; unique/foreign key; delete/retention.
3. API: payload/status/error, role/owner/consent, idempotency, CAS và redact.
4. Integration: submit → local worker job → report → review; practice lesson → evidence → progress; payment sandbox; blind rating; study.
5. Security: session/CSRF-or-origin, OAuth state/nonce/PKCE/cookie signature, header spoofing, internal route, callback signature, secret scan.
6. UI contract: template render, required disclosure, forbidden claims, route/navigation, asset packaging và art generation deterministic.
7. Browser E2E: matrix ở mục 6.6.
8. Operations: restart app/worker, duplicate job, SQLite busy/unavailable, partial callback, interrupted cleanup và restore backup.

### 10.2. Required commands

Các lệnh chính xác được chốt lại sau khi manifest W5 merge; tối thiểu phải có:

```bash
ruff format --check src tests tools scripts
ruff check src tests tools scripts
python -m pytest -q -m "not smoke" --cov=aicefr --cov-branch --cov-report=xml --cov-report=term-missing
python -m pytest -q -m smoke
python -m build
```

Nếu thư mục không tồn tại, sửa command trong cùng PR CI; không che lỗi bằng `|| true`.

### 10.3. Coverage policy

- Không thấp hơn combined baseline đo lại ở G0.
- Code mới thuộc auth, permission, Trust Layer, payment signature, assignment, consent, migration và reliable change phải có branch test cho success + refusal/failure.
- Global threshold CI tối thiểu 70% chỉ là sàn rubric, không thay review critical uncovered branches.
- Báo cáo coverage phải ghi revision, command, line/branch, delta và critical uncovered lines.

### 10.4. Không được nghiệm thu khi

- Có test fail/skip bị che hoặc browser console error trong critical journey.
- App chỉ chạy với state cũ của máy người implement nhưng không dựng được từ clean environment.
- Migration làm mất report/audio/consent/review/audit cũ.
- Student xem được dữ liệu người khác; teacher/admin page dựa vào ẩn nút thay vì server authorization.
- Bài luyện có band hoặc ảnh hưởng assessment metric.
- Blind rater thấy identity/machine result.
- Payment callback không chống replay/tampering.
- Giao diện desktop đẹp nhưng mobile overflow, keyboard trap hoặc reduced motion không hoạt động.

---

## 11. Definition of Done W5

W5 chỉ được đề xuất hoàn thành khi đủ toàn bộ điều kiện sau:

 1. Feature matrix mục 3 không còn hàng `Chưa có`; mọi khác biệt còn lại có lý do được chủ dự án chấp nhận.
 2. Local mode khởi động từ hướng dẫn sạch; ba role hoàn thành critical journey.
 3. Monolith cài được từ wheel sạch; SQLite, blob store, worker và model readiness phản ánh đúng trạng thái.
 4. Pipeline thật chạy ít nhất một audio có quyền; model/version/evidence đầy đủ; không fake fallback.
 5. Migration và restore smoke PASS; report cũ đọc được.
 6. Full automated suite, format, lint, wheel, secret scan và required coverage PASS trên final revision.
 7. Browser QA desktop/mobile PASS cho public/student/teacher/admin, có screenshot và machine-readable result.
 8. Không còn finding BLOCKER/MAJOR; accepted risk phải do chủ dự án ghi nhận.
 9. README/run guide/env example/API-page inventory và evidence manifest khớp code.
10. Mỗi người cập nhật AI Prompt Log W05 đúng ngày và công việc thật; không ghi giờ hoặc kết quả suy đoán.
11. SDD/status liên quan được cập nhật theo thực tế nhưng không tự ghi `APPROVED`, `DONE` hoặc user acceptance.
12. Chủ dự án review package cuối và đưa verdict. Trước verdict, trạng thái W5 là `PENDING` dù technical checks đều PASS.

---

## 12. Rủi ro và phương án xử lý

| ID | Rủi ro | Dấu hiệu sớm | Xử lý |
| --- | --- | --- | --- |
| W5-R1 | Khối lượng lớn hơn năng lực một tuần | Một task nền tảng còn `BLOCKED` làm nhiều task phụ thuộc không thể review | Ưu tiên gỡ dependency theo task graph; không bỏ test/quyền/dữ liệu để chạy theo số lượng trang; báo rõ task chưa đạt |
| W5-R2 | Ba người sửa cùng base template/schema | Conflict lặp, fixture hỏng nhiều lane | Khóa file dùng chung theo mục 8, merge contract PR trước |
| W5-R3 | Migration làm hỏng dữ liệu demo cũ | Count/hash khác sau migrate | Stop, restore backup, sửa forward migration; không chạy trên dữ liệu khác |
| W5-R4 | Router/template bắt đầu chứa rule nghiệp vụ | Một rule phải sửa ở nhiều endpoint | Giữ application service/domain là nơi duy nhất chứa rule; thêm unit test trực tiếp |
| W5-R5 | Worker retry tạo xử lý trùng | Hai report/audit cho một response | Idempotency key + unique constraint + lease/retry regression test |
| W5-R6 | Google/payment phụ thuộc khóa ngoài | Không có credential W5 | Mock server + sandbox/in-app gateway; UI báo disabled; không yêu cầu gửi secret qua chat |
| W5-R7 | Blind leakage qua endpoint cũ | Rater mở report/queue bằng URL khác | Central blind guard ở server và security regression cho mọi đường đọc |
| W5-R8 | UI nhiều hiệu ứng làm chậm/khó dùng | CLS, scroll ngang, focus mất | Budget asset, progressive enhancement, reduced motion, keyboard/mobile QA |
| W5-R9 | Claim khoa học vượt evidence | UI nói “tiến bộ/hiệu quả” với sample thấp | Insufficient-data state bắt buộc; count/CI/source đi kèm |
| W5-R10 | Copy cả bug hoặc config riêng của bản Sang | Hard-coded path/key/branding xuất hiện | Review từng module theo contract repo nhóm; secret/config/data scan trước merge |

---

## 13. Quy tắc PR và bằng chứng

- Một PR chỉ nên chứa một nhóm hành vi có thể review: monolith foundation, Trust Layer, learning core, UI shell, account, rating, research hoặc billing.
- Tên commit có Task ID W5; không commit thẳng `main`.
- PR mô tả requirement, schema/API thay đổi, screenshot khi có UI, test command/result, migration/rollback và open risk.
- Reviewer mở actual diff, chạy targeted tests và kiểm quyền/edge case; comment “looks good” không thay checklist.
- Evidence W5 ghi final commit, environment, command, output, screenshot hash và limitation. Không tái dùng PASS của commit trước correction.
- Không push/deploy/external payment/Google config từ kế hoạch này nếu chưa có quyền riêng cho thao tác đó.

---

## 14. Quyết định cần xác nhận khi duyệt kế hoạch

1. Kiến trúc đã được chủ dự án chốt ngày 12/10/2026: giữ modular monolith; D043 và toàn bộ hạ tầng tách service không thuộc W5.
2. Cần xác nhận billing vẫn là sandbox/test, không thu tiền thật.
3. Owner và task bắt buộc đã được khóa theo mục 8–9; cần xác nhận quy tắc bắt buộc review chéo.
4. Cần xác nhận không giảm scope âm thầm khi hết tuần; phần chưa đạt phải ghi `PENDING/BLOCKED` và chuyển kế hoạch sau bằng quyết định của nhóm.
5. Cần duyệt Phase 01 và lựa chọn `RESEARCH MODE: RUN` cho M09–M16; sau đó review/duyệt tuần tự Specification, Test Plan và Plan/Tasks trước khi code.

**Codex self-review:** kế hoạch đã bao phủ runtime, code boundary, migration, API, từng vai trò/màn hình, responsive/accessibility, security, test, evidence và rollback; không phát hành implementation prompt ở trạng thái DRAFT.

**CODEX RECOMMENDATION:** `RECOMMEND APPROVAL` cho Requirement/Research mode của M09–M16 sau khi nhóm xác nhận sandbox billing, review chéo và cách xử lý task chưa đạt. Chưa đề xuất Phase 05 approval hoặc bắt đầu implementation trong trạng thái hiện tại.

**USER VERDICT:** `PENDING`.
