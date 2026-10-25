# W7 — 26/10–01/11/2026 — Chuyển toàn bộ repo gốc sang repo nộp bài, ký Bản cam kết, thu thử

**Phiên bản:** v0.1 — BẢN THẢO, chờ nhóm và chủ dự án chốt (mục 8). Chưa có `USER VERDICT`.
**Ngày lập:** 25/10/2026, múi giờ Asia/Ho_Chi_Minh.
**Người soạn:** Sang (với Claude). Đẩy lên dưới dạng bản thảo để cả nhóm góp ý trong PR; nhóm chốt mục 8 bằng review trước khi merge.

**Nguồn đã đọc ngày 25/10:**

- Repo gốc `ThanhSangLouis/ai-assessor-cefr`, `main` tại `0853c95`: 626 tệp, khoảng 31.700 dòng Python, 10.300 dòng JS; `pytest -m "not e2e"` 1424 qua, E2E 79/79 qua trên MongoDB 7; quyết định D001–D057.
- Repo nhóm `thanglb2005/ai-assessor-cefr` (PRIVATE), `main` tại `82fe708` (merge PR #49): 930 tệp, kiến trúc cũ (`local/`, `portal/`, `trust/`, chạy một tiến trình).
- Kế hoạch W6 và bản thảo Bản cam kết W6-S01 (bản trên máy của Sang), Jira sprint W6.
- Quyết định của chủ dự án ngày 25/10: chuyển **tất cả** tính năng; **mỗi thành viên tự chuyển phần module của mình**; artifact suy ra từ Speak & Improve **để ngoài repo, ghim SHA**.

---

## 0. Mục tiêu và nguyên tắc

**Mục tiêu W7:** cuối tuần, `main` của repo nộp bài chạy đúng hệ thống của repo gốc: ba dịch vụ (core, speech, web) sau gateway nginx, MongoDB, Redis, tất cả tính năng D001–D057; toàn bộ test xanh. Từ đây **đóng băng tính năng**: W8 trở đi chỉ thu dữ liệu, đo, sửa lỗi, viết luận văn.

**"Hoàn thiện" ở đây nghĩa là hoàn thiện tính năng, không phải hoàn thiện đồ án.** Các KPI của Bản cam kết (đồng thuận người–người, máy–người, thực nghiệm người dùng) chưa đo được trước W8–W11. D045–D057 vẫn PROPOSED cho tới khi người có thẩm quyền ghi APPROVED. Báo cáo tuần và luận văn không được ghi các KPI là đã đạt.

**Năm nguyên tắc (không đổi được trong tuần):**

1. **Mỗi người chuyển module của mình** (bảng mục 4). Commit đứng tên người chuyển; người khác review. Git là bằng chứng đóng góp cá nhân (Rubric TC2, G4).
2. **Khai nguồn mọi PR:** "chuyển từ ThanhSangLouis/ai-assessor-cefr@0853c95, đường dẫn …". Rubric mục 6 coi mã chép không khai nguồn là đạo văn (V4).
3. **Không đưa số liệu hay artifact suy ra từ Speak & Improve vào repo:** `ridge_resp_*.json`, `conformal_*.json`, `ridge_resp_v2_cal.json`, số đo trong tài liệu. Artifact nằm ngoài Git, code nạp theo đường dẫn cấu hình và kiểm SHA-256. Test dùng bộ artifact giả sinh từ dữ liệu tổng hợp.
4. **Không làm hỏng `main` giữa chừng:** mọi PR chuyển code vào nhánh tích hợp `migrate/w7-repo-goc`; chỉ một PR cuối vào `main`, khi đủ điều kiện mục 5.
5. **Giữ tài liệu và hồ sơ của nhóm:** `docs/sdd/modules/`, `docs/evidence/`, `docs/reports/`, AI Prompt Log, `docs/plan/` của repo nhóm giữ nguyên và được cập nhật cho khớp code mới. Không thay bằng tài liệu của repo gốc.

---

## 1. Hiện trạng khi vào W7

| Hạng mục | Repo gốc (`0853c95`) | Repo nhóm (`82fe708`) |
| --- | --- | --- |
| Kiến trúc | Ba dịch vụ (D043, D044), MongoDB (D048), Redis + BullMQ (D050), database riêng mỗi dịch vụ, S3, Prometheus (D051) | Một tiến trình, kho cũ |
| Tính năng có thêm | Lộ trình bài học, ghép lộ trình (D046), gói dịch vụ + Stripe/MoMo + Google (D033–D036), tính lượt NetID và bảng giá (D049, D053, D057), lớp học (D054), nhắc việc (D055), nghe lại có đối chứng (D056), hiệu chuẩn band (D052) | Phần đã chuyển ở W5 (#35–#47) |
| Kiểm thử | 1424 + 79 E2E; CI 4 job | 985 + 15 bỏ qua (W6) |
| Artifact S&I | **Đang commit trong `src/aicefr/scoring/models/`** — phải gỡ trước khi chuyển | Ngoài repo, ghim SHA |
| Tài liệu | SDD một tệp, SRS FR-01..FR-90, decision log | SDD theo module 01–07 có phase verdict |

**Ba việc chặn phải làm đầu tuần:**

- **Gỡ artifact S&I khỏi repo gốc** (W7-S01), kể cả khỏi lịch sử nhánh sẽ chuyển: chuyển bằng cách chép tệp, không đẩy lịch sử Git của repo gốc sang.
- **Kiểm kê phần chỉ repo nhóm có** (W7-G1), để không mất thứ gì khi thay code.
- **Sửa Bản cam kết** trước khi ký (W7-S04): bản thảo W6 ghi "không làm thu tiền thật; tích hợp NetID không thuộc sản phẩm nộp". Nay đưa sang tất cả thì phải ghi lại: thanh toán chỉ chạy chế độ thử, kênh NetID là phần mở rộng, không thuộc KPI.

---

## 2. Cách chuyển và lịch theo ngày

Hai repo khác kiến trúc nên không chuyển từng module song song lên `main` được: nền (contracts, kho, bus, dịch vụ) phải có trước, module mới đặt lên được. Bốn đợt, trên nhánh `migrate/w7-repo-goc`:

| Ngày | Đợt | Việc | Ai |
| --- | --- | --- | --- |
| T2 26/10 | 0 — Chuẩn bị | Gỡ artifact S&I khỏi repo gốc (S01); kiểm kê phần chỉ repo nhóm có (G1); tạo nhánh tích hợp; ký Bản cam kết đã sửa nếu GVHD sẵn sàng (S04) | Sang, cả nhóm, Thắng |
| T3–T4 27–28/10 | 1 — Nền | Contracts, ports, cấu hình, MongoDB + migration, bus Redis, RPC, gateway, khung ba dịch vụ, compose, CI 4 job | Thắng |
| T4–T6 28–30/10 | 2 — Module | Mỗi người chuyển module của mình lên nền, kèm test và cập nhật SDD module | Sang, Nguyên, Thắng |
| T6 30/10 | 3 — Tích hợp | Toàn bộ test + E2E xanh trên nhánh tích hợp; chạy thật một bài (Whisper, Ridge với artifact ngoài repo) | Cả nhóm |
| T7 31/10 | 4 — Vào `main` | PR cuối, hai người review, CI xanh, merge; thu thử 6–8 sinh viên trên `main` mới | Thắng merge; Nguyên tổ chức thu thử |
| CN 01/11 | Hồ sơ | Báo cáo tuần W7, AI Prompt Log W07, đóng sprint | Cả nhóm |

**Dự phòng:** nếu đến hết T6 30/10 nhánh tích hợp chưa xanh, **thu thử chạy trên `main` cũ**, việc chuyển lùi sang W8 đợt đầu. Không thu dữ liệu thật trên hệ thống chưa qua test.

---

## 3. Task theo từng người

Quy ước: mã `W7-<người><số>`; mỗi task một ticket Jira trong sprint W7. **P0** phải xong trong tuần; **P1** nên xong; **P2** nếu còn thời gian. Mỗi PR chuyển code: khai nguồn, kèm test, cập nhật `06-tasks.md` và `07-status.md` của module, và một dòng AI Prompt Log.

### 3.0. Cả nhóm

#### W7-G1 — Kiểm kê trước khi thay (P0, T2)

- **Việc:** mỗi người đối chiếu module của mình giữa hai repo; ghi những gì **chỉ repo nhóm có** (test, evidence, cấu hình, xử lý riêng) vào `docs/evidence/w7-migration/kiem-ke.md`. Mỗi mục ghi: giữ (chuyển ngược sang code mới), bỏ (có lý do), hoặc đã có tương đương ở repo gốc.
- **Xong khi:** kiểm kê đủ 16 module, không còn mục "chưa rõ".

#### W7-G2 — Tích hợp và vào `main` (P0, T6–T7)

- **Việc:** chạy toàn bộ kiểm tra mục 5 trên nhánh tích hợp; PR cuối vào `main` có hai người review; merge sau CI xanh. Cập nhật README, hướng dẫn chạy máy và hướng dẫn teammate.
- **Xong khi:** `main` mới xanh; tag `w7-feature-freeze`.

#### W7-G3 — Báo cáo tuần và nhật ký AI (P0, CN)

- **Việc:** báo cáo W7 lên `projects-fit.hcmute.edu.vn` và `docs/reports/week-07/`. AI Prompt Log W07 ghi đúng việc chuyển code của từng người, đối chiếu được với commit (G4).
- **Xong khi:** ảnh chụp cổng Khoa; log không còn ô trống.

### 3.1. Sang — lõi chấm, Trust Layer, học tập, bằng chứng nghiên cứu (M03, M04, M05, M09, M10, M12, M13)

#### W7-S01 — Gỡ artifact S&I khỏi repo gốc, nạp từ ngoài và ghim SHA (P0, T2, chặn mọi việc khác)

- **Việc:** chuyển `ridge_resp_*`, `conformal_*`, `ridge_resp_v2_cal` ra ngoài Git. Scorer và Trust Layer nạp theo `AICEFR_MODEL_DIR` và kiểm SHA-256 ghim trong cấu hình, như repo nhóm đang làm (M05-TASK-002). Test dùng bộ artifact giả sinh từ dữ liệu tổng hợp, không chứa hệ số thật. Tài liệu không còn số đo S&I.
- **Xong khi:** `git grep` không còn hệ số hay số đo S&I trong cây sẽ chuyển; 1424 + 79 test vẫn xanh với artifact giả; chạy thật được với artifact thật đặt ngoài repo.

#### W7-S02 — Chuyển M03, M04, M05, M09 (P0, T4–T5)

- **Việc:** `asr/`, `audio` phía nhận dạng, `features/`, `scoring/` (Ridge, conformal, hiệu chuẩn band D052), `pipeline.py` phần chấm, dịch vụ `speech` (worker), `tools/calibrate_*.py`, `tools/bench_asr.py`; test tương ứng. Cập nhật SDD M03–M05, M09.
- **Phụ thuộc:** đợt 1 của Thắng (contracts, bus, kho).

#### W7-S03 — Chuyển M10, M12, M13 (P0, T5–T6)

- **Việc:** `lessons/`, `practice/` (nhiệm vụ, chuỗi ngày, thành tích, nhắc việc D055), `pronunciation/`, `research/` (đồng thuận, thực nghiệm, độ lặp lại), `report/replay.py` (D056), phần `learning` và `rating`, `study`, `replay` của dịch vụ core; test tương ứng. Cập nhật SDD M10, M12, M13.
- **Phụ thuộc:** W7-S02; trang của Nguyên (W7-N02).

#### W7-S04 — Sửa và ký Bản cam kết (P0, T2–T4, SCRUM-61)

- **Việc:** sửa bản thảo W6-S01 cho khớp hệ thống sau chuyển:
  - mục "Không làm" ghi lại: thanh toán chỉ chế độ thử, không thu tiền thật;
  - kênh NetID là phần mở rộng, không thuộc KPI;
  - thêm lớp học, nhắc việc, nghe lại vào danh sách chức năng, ghi rõ đâu là cam kết, đâu là kéo dãn;
  - gửi GVHD và lấy chữ ký.

  Đây là mốc M1, quy tắc chặn G1.
- **Xong khi:** bản có chữ ký nộp lên website trước 01/11, hoặc có lịch ký cụ thể nếu GVHD chưa sẵn sàng.

#### W7-S05 — Chạy thật trên nhánh tích hợp (P1, T6)

- **Việc:** lặp lại W6-S03 trên code mới: Whisper small, Silero, Ridge, Trust Layer với artifact thật ngoài repo. Ghi provenance; **không** ghi điểm hay số đo S&I.

### 3.2. Thắng — nền tảng, dữ liệu, tài khoản, gói dịch vụ, triển khai (M02, M08, M11, M14, M16)

#### W7-T01 — Nền của kiến trúc mới (P0, T3–T4, chặn đợt 2)

- **Việc:** chuyển `contracts.py`, `ports.py`, `config.py`, `encoding.py`, `formatting.py`, `observability.py`; `storage/db.py` và `migrations.py` (MongoDB, D048); `platform/` (bus, RedisBus, RPC, gateway, callers, D050); `infra/` (blob store kể cả S3, hàng đợi, giới hạn tần suất, D051); `services/runtime.py`, `services/__init__.py`, `services/core/app.py`, khung ba dịch vụ; `docker-compose*.yml`, `deploy/`, `Dockerfile*`, `.github/workflows/ci.yml` (4 job). Test nền: `test_schema`, `test_services_split`, `test_bus*`, `test_blobs`, `test_observability*`.
- **Xong khi:** nhánh tích hợp có nền chạy được, CI 4 job xanh trên phần đã chuyển.

#### W7-T02 — Chuyển M02, M08, M11 (P0, T4–T5)

- **Việc:** `audio/` phía giải mã, `qc/`; `auth/` (mật khẩu, phiên, Google D036); kho tài khoản, đồng thuận, audit; dịch vụ `identity`; `retention.py`, `maintenance_cli.py`, `accounts_cli.py`, `db_cli.py`; test tương ứng. Cập nhật SDD M02, M08, M11.

#### W7-T03 — Chuyển M14 và kênh tính lượt (P0, T5)

- **Việc:** `billing/` (gói, giấy phép, Stripe, MoMo, VNPay, cổng thử; D033–D035); `metering/` và kho sổ lượt (D049, D053, D057); dịch vụ `billing` và `metering`; test tương ứng. Cập nhật SDD M14, thêm mục kênh NetID.
- **Lưu ý:** mọi cổng mặc định chế độ thử; không đưa khoá thật vào repo (`docs/plan/CAU_HINH_KHOA_BEN_NGOAI.md`).

#### W7-T04 — Chuyển decision log, SRS, SDD tổng (P1, T6)

- **Việc:** gộp D037–D057 của repo gốc vào decision log của repo nhóm, giữ trạng thái gốc (PROPOSED vẫn là PROPOSED); cập nhật SRS lên FR-90; đưa sơ đồ 02, 02b, 02c, 06 mới vào SDD. Không ghi APPROVED thay người duyệt.

### 3.3. Nguyên — giao diện, báo cáo, giảng viên duyệt, thực nghiệm người dùng (M01, M06, M07, M15)

#### W7-N01 — Chuyển M01, M06, M07 (P0, T4–T5)

- **Việc:** API nộp bài và bài của tôi (`responses_api`), báo cáo chẩn đoán (`report/` evidence, nhận xét, mô tả band), hàng đợi và duyệt (`review/`, `review_api`, `admin_api`), lớp học và giao bài (`classes_api`, D054); test tương ứng. Cập nhật SDD M01, M06, M07.

#### W7-N02 — Chuyển M15: toàn bộ trang (P0, T5–T6)

- **Việc:** dịch vụ `web` (`pages.py`, `bff.py`), `api/templates/`, `api/static/`: mọi trang, gồm Lượt của tôi, Lớp học, Bài được giao, nhắc việc, thẻ nghe lại. Thêm 79 test E2E (Playwright) và chạy với MongoDB 7. Cập nhật SDD M15.
- **Phụ thuộc:** API của các module khác đã có trên nhánh tích hợp.

#### W7-N03 — Thu thử 6–8 sinh viên (P0, T7)

- **Việc:** theo kế hoạch khảo sát: phiếu đồng thuận giấy cùng `consent_version` với hệ thống, đề bài, thiết bị. Chạy trên `main` mới, hoặc `main` cũ nếu kích hoạt dự phòng mục 2. Ghi lỗi gặp phải thành issue.
- **Xong khi:** biên bản thu thử; danh sách lỗi; không có dữ liệu cá nhân trong repo.

---

## 4. Ánh xạ code repo gốc → module → người chuyển

| Thư mục / tệp ở repo gốc | Module | Người chuyển |
| --- | --- | --- |
| `contracts.py`, `ports.py`, `config.py`, `encoding.py`, `formatting.py`, `observability.py`, `platform/`, `infra/`, `services/runtime.py`, `services/core/app.py`, `storage/db.py`, `storage/migrations.py`, `deploy/`, compose, CI | M16 (nền) | Thắng |
| `audio/` (giải mã), `qc/` | M02 | Thắng |
| `auth/`, `storage/auth_*`, `storage/consent_*`, `storage/audit_*`, `services/core/identity/`, `retention.py`, CLI | M08, M11 | Thắng |
| `billing/`, `metering/`, `storage/billing_*`, `storage/metering_*`, `services/core/billing/`, `services/core/metering/` | M14 | Thắng |
| `asr/`, `features/`, `scoring/`, `pipeline.py`, `services/speech/`, `tools/calibrate_*`, `tools/bench_asr.py` | M03, M04, M05, M09 | Sang |
| `lessons/`, `practice/`, `pronunciation/`, `research/`, `report/replay.py`, `storage/lesson_*`, `plan_*`, `rating_*`, `study_*`, `replay_*`, `services/core/learning/`, `rating_api`, `study_api`, `replay_api` | M10, M12, M13 | Sang |
| `report/` (trừ replay), `review/`, `responses_api`, `review_api`, `admin_api`, `classes_api`, `storage/repository.py`, `task_*`, `classroom_*` | M01, M06, M07 | Nguyên |
| `services/web/`, `api/templates/`, `api/static/`, `tests/e2e/` | M15 | Nguyên |

Test đi cùng module. Tệp dùng chung mà bảng chưa nhắc tên: người chuyển nền (Thắng) chuyển, hai người còn lại review.

---

## 5. Definition of Done W7

| # | Điều kiện | Cách kiểm |
| --- | --- | --- |
| 1 | `main` repo nhóm chạy hệ thống mới | `docker compose up` lên đủ gateway, core, speech, web, MongoDB, Redis; `/readyz` mọi dịch vụ trả 200 |
| 2 | Toàn bộ test xanh | `pytest -m "not e2e"` ≥ số của repo gốc (1424) cộng test riêng giữ lại từ kiểm kê; E2E 79/79 với `AICEFR_TEST_MONGO` |
| 3 | CI 4 job xanh | định dạng + lint + test; MongoDB + Redis; build ảnh + compose; quét khoá |
| 4 | Không có số liệu S&I | `git grep` theo danh sách hệ số và số đo; `check_forbidden_files.py` |
| 5 | Mỗi module có commit của chủ module | `git log --author` theo từng người trên nhánh tích hợp |
| 6 | Mọi PR khai nguồn | mô tả PR có "chuyển từ ThanhSangLouis/ai-assessor-cefr@0853c95" |
| 7 | SDD 16 module khớp code | `06-tasks.md`, `07-status.md` cập nhật; sơ đồ 02, 02b, 02c khớp (test sơ đồ xanh) |
| 8 | Kiểm kê xong | `docs/evidence/w7-migration/kiem-ke.md` không còn mục chưa rõ |
| 9 | Bản cam kết | đã ký, hoặc có lịch ký trước 23/11 |
| 10 | Thu thử | biên bản 6–8 sinh viên, danh sách lỗi |
| 11 | Hồ sơ | báo cáo W7 trên cổng Khoa; AI Prompt Log W07 đầy đủ |

---

## 6. Rủi ro và phương án

| Rủi ro | Mức | Phương án |
| --- | --- | --- |
| Một tuần không đủ để chuyển khoảng 31.700 dòng và cập nhật SDD 16 module | Cao | Nền xong trước T4 là điều kiện cứng; module nào trễ thì nhánh tích hợp vẫn merge phần đã xanh, phần còn lại vào W8. Thu thử dùng dự phòng mục 2 |
| Mất tính năng hay test chỉ repo nhóm có | Trung bình | Kiểm kê W7-G1 trước khi thay |
| Số liệu S&I lọt vào repo | Cao (giấy phép) | W7-S01 làm đầu tiên; điều kiện DoD 4; chuyển bằng chép tệp, không đẩy lịch sử Git repo gốc |
| Đóng góp cá nhân bị mờ (một người đẩy cả repo) | Cao (Rubric TC2, G4) | Nguyên tắc 1 và điều kiện DoD 5 |
| Bị coi là đạo văn vì code đổ vào một lần | Cao (Rubric mục 6) | Khai nguồn từng PR; mỗi người giải thích được phần mình chuyển (hội đồng hỏi ngẫu nhiên ≥ 3 vị trí trong mã) |
| Bản cam kết mâu thuẫn với hệ thống | Trung bình | W7-S04 sửa trước khi ký |
| MongoDB 8 không chạy trên runner CI (kernel 6.19+) | Thấp | Dùng `mongo:7.0` như repo gốc |

---

## 7. Không làm trong W7

- Thêm tính năng mới (đóng băng sau khi chuyển).
- Đổi trạng thái quyết định PROPOSED thành APPROVED thay người duyệt.
- Thu tiền thật, bật khoá thật của Stripe, MoMo, Google.
- Công bố số đo trên Speak & Improve.

---

## 8. Quyết định cần nhóm chốt trước T2 26/10

1. **Lịch:** đồng ý đóng băng tính năng cuối W7 (sớm hơn mốc M3 cuối W13).
2. **Nhánh tích hợp và PR cuối:** đồng ý cách làm mục 2 thay vì PR từng module thẳng vào `main`.
3. **Phạm vi Bản cam kết:** kênh NetID và thanh toán ghi là mở rộng, chế độ thử, ngoài KPI.
4. **Dự phòng thu thử:** đồng ý thu trên `main` cũ nếu nhánh tích hợp chưa xanh hết T6 30/10.
5. **Thời hạn repo gốc:** sau khi chuyển xong, repo gốc chỉ còn là bản tham chiếu; mọi thay đổi từ W8 làm trên repo nhóm.

---

## 9. Jira sprint W7 (26/10–01/11)

| Ticket đề xuất | Người | Ưu tiên |
| --- | --- | --- |
| W7-G1 Kiểm kê trước khi thay | Cả nhóm | P0 |
| W7-G2 Tích hợp và vào `main` | Cả nhóm (Thắng merge) | P0 |
| W7-G3 Báo cáo tuần, AI Prompt Log W07 | Cả nhóm | P0 |
| W7-S01 Gỡ artifact S&I, nạp từ ngoài, ghim SHA | Sang | P0 |
| W7-S02 Chuyển M03, M04, M05, M09 | Sang | P0 |
| W7-S03 Chuyển M10, M12, M13 | Sang | P0 |
| W7-S04 Sửa và ký Bản cam kết (SCRUM-61) | Sang | P0 |
| W7-S05 Chạy thật trên nhánh tích hợp | Sang | P1 |
| W7-T01 Nền kiến trúc mới | Thắng | P0 |
| W7-T02 Chuyển M02, M08, M11 | Thắng | P0 |
| W7-T03 Chuyển M14 và kênh tính lượt | Thắng | P0 |
| W7-T04 Decision log, SRS, SDD tổng | Thắng | P1 |
| W7-N01 Chuyển M01, M06, M07 | Nguyên | P0 |
| W7-N02 Chuyển M15 và E2E | Nguyên | P0 |
| W7-N03 Thu thử 6–8 sinh viên | Nguyên | P0 |

Việc còn mở từ W6 mang sang: SCRUM-52 (email CUP&A), SCRUM-81 (chấm mù tập huấn), SCRUM-54 (góp ý GVHD về "Đánh giá để học").

---

## 10. Hướng dẫn chép code (đưa nguyên mục này cho AI của mình làm theo)

**Nguồn:** repo gốc `ThanhSangLouis/ai-assessor-cefr` tại commit `0853c95`. Cả nhóm đã có quyền đọc. **Đích:** repo nộp bài `thanglb2005/ai-assessor-cefr`, nhánh tích hợp `migrate/w7-repo-goc`.

Chép **đúng phần của mình** theo bảng mục 4. Không chép phần của người khác, kể cả khi thấy thiếu: ghi lại rồi báo người đó.

**Một lần, khi bắt đầu:**

```bash
git clone git@github.com:ThanhSangLouis/ai-assessor-cefr.git ../repo-goc   # chỉ để đọc
cd ../repo-goc && git checkout 0853c95 && cd -
git fetch origin && git checkout migrate/w7-repo-goc && git pull
git checkout -b port/<mã-module>-<tên-ngắn>                                 # vd port/m15-trang
```

**Chép một thư mục của mình** (vd Nguyên, M15):

```bash
rsync -a --delete ../repo-goc/src/aicefr/api/templates/ src/aicefr/api/templates/
rsync -a --delete ../repo-goc/src/aicefr/api/static/    src/aicefr/api/static/
rsync -a          ../repo-goc/src/aicefr/services/web/  src/aicefr/services/web/
```

- **Test đi cùng:** chép các tệp `tests/test_*.py` của module mình, và với M15 thì cả `tests/e2e/`.
- **Không bao giờ chép:**
  - `src/aicefr/scoring/models/*.json`: artifact Speak & Improve, để ngoài Git (W7-S01);
  - `.env`, `*.db`, audio, ảnh chụp có dữ liệu thật;
  - thư mục `.git` của repo gốc.
- **Mã cũ cùng module** trong repo nhóm, nếu repo gốc đã có bản thay thế: xoá trong cùng PR, liệt kê trong mô tả PR.

**Kiểm trước khi commit:**

```bash
ruff check src tests && ruff format --check src tests
pytest -m "not e2e" -q                     # phần nền chưa có thì test của module có thể chưa chạy được: ghi rõ trong PR
git status                                 # chỉ có tệp trong vùng của mình
```

**Commit và PR vào `migrate/w7-repo-goc`** (không vào `main`):

```bash
git commit -m "port(M15): trang và test E2E từ repo gốc

Chuyển từ ThanhSangLouis/ai-assessor-cefr@0853c95:
src/aicefr/api/templates, src/aicefr/api/static, src/aicefr/services/web, tests/e2e."
git push -u origin HEAD
gh pr create --base migrate/w7-repo-goc --title "port(M15): ..." --body "Chuyển từ ThanhSangLouis/ai-assessor-cefr@0853c95 ..."
```

- **Mô tả PR ghi đủ:** các đường dẫn đã chép; mã cũ đã xoá; test đã chạy và kết quả; việc còn chờ người khác (vd "chờ nền của Thắng để chạy được test API").
- **Nhật ký và Jira:** ghi một dòng AI Prompt Log W07, cập nhật `06-tasks.md` và `07-status.md` của module.

**Thứ tự để khỏi kẹt:**
1. Thắng tạo nhánh `migrate/w7-repo-goc` và chép phần nền (W7-T01) trước.
2. Sang gỡ artifact S&I (W7-S01).
3. Sau hai việc trên, mọi người chép module của mình; test chạy được đầy đủ khi nền đã vào nhánh.
