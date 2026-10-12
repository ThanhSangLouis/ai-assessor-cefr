# W4 — 05–11/10/2026 — nối đầu-cuối và chuẩn hoá repo nộp bài

**Phiên bản:** v2. Đối chiếu lại ngày 11/10/2026 với hai repo:
- **repo nộp bài** `thanglb2005/ai-assessor-cefr` @ `35d3514`;
- **repo gốc** `ThanhSangLouis/ai-assessor-cefr` @ `87887dd`.

**Bản trước:** v1 viết ngày 04/10 dựa trên `2b428ce` (bản nội bộ, chưa từng commit vào repo).

**Trạng thái:** tuần 4 kết thúc ngày 11/10. File này ghi kế hoạch đã sửa cùng kết quả thật của từng việc, và chuyển phần chưa xong sang tuần 5.

**Cách dùng:**
- `docs/plan/*` là file dùng chung. Sang đưa file này vào repo (PR #33) theo đồng ý của nhóm; Thắng và Nguyên review.
- Không chép số liệu suy ra từ S&I vào file này, vì repo vẫn đang public.

---

## 0. Những chỗ v1 lệch so với thực tế

| # | v1 nói | Thực tế ngày 11/10 | Sửa trong v2 |
|---|---|---|---|
| L1 | Bốn lỗ hổng chặn demo: không có coordinator, không có composition root, chưa có ASR/VAD thật, báo cáo chỉ nằm trong bộ nhớ | Đã xử lý hết:<br>• coordinator `pipeline/coordinator.py` và `python -m aicefr.local` (W3, PR #31, 05/10);<br>• báo cáo SQLite `report/sqlite.py`, portal quản trị và thống kê (PARITY-001, 08/10);<br>• ASR/VAD thật có smoke (PR #32, 11/10) | Mục 1 ghi lại hiện trạng; các việc T2, T3, N1, N2, S1, S2 chuyển thành XONG |
| L2 | Repo gốc chỉ có Trust Layer, LID và lá chắn lạc đề (D022); để sang W5–W6 | Từ 06/10 tới 08/10, repo gốc có thêm **D023–D037**: luyện tập, lộ trình bài học, giao diện mới, tài khoản và Google, chấm mù kép, thành tựu, gói dịch vụ và thanh toán, ảnh nền, sơ đồ lớp v3 dạng OOP, refactor | Thêm mục 2: bảng phân loại tính năng nào chuyển sang repo nộp bài, ai làm, khi nào, và tính năng nào **không bao giờ** chuyển |
| L3 | Sơ đồ lớp v3 trên Drive là thiết kế đích của nhóm (D021) | Ngày 08/10, trang "So do lop v3" đổi sang bản OOP gọn:<br>• `Actor` trừu tượng với ba lớp con `Student`, `Teacher`, `Admin`; bỏ kiểu liệt kê `Role`;<br>• có thêm `Order`, `License`, interface `PaymentGateway` của D034–D035 | Thêm việc W5: tách khỏi trang thiết kế dùng chung những lớp không thuộc repo nộp bài; ghi cách map lớp con vai trò xuống cột `role` |
| L4 | Repo gốc và repo nộp bài dùng cùng kiến trúc, chuyển code là "chép theo PR có khai nguồn" | Repo gốc là FastAPI + Jinja2, đường dẫn `/api/v1`; repo nộp bài là WSGI + SQLite riêng (PARITY-001 ghi rõ không cam kết tương thích) | Chuyển tính năng = **viết lại theo contract của module**; chỉ chép được phần thuần logic (M03–M05), và vẫn khai nguồn `ThanhSangLouis/ai-assessor-cefr@<sha>` |
| L5 | Tên tệp `asr/faster_whisper_engine.py`, `features/silero_vad.py`; Jira SCRUM-23, SCRUM-26 | Adapter đặt ở `asr/local.py`, `features/local.py` (W3); PR #32 gắn SCRUM-22 (DEP-06) | Ghi theo tên thật; không đổi tên tệp vì coordinator đang import |
| L6 | Hồ sơ: R6 status SDD sẽ khớp code trong W4 | M01, M06, M07 vẫn ghi "Phase 01"; M02 "Phase 06"; M08 "06–08, chờ review" | Chuyển sang W5 cho từng owner |
| L7 | Mọi PR từ 05/10 có review (T5, C4) | Có 0 ruleset và 0 PR có review trên GitHub. PARITY-001 được commit thẳng lên `main`, không qua PR | Giữ T5, C4 ở W5, ưu tiên cao vì ảnh hưởng TC2.4 |

---

## 1. Hiện trạng repo nộp bài ngày 11/10 (`35d3514`)

| Module | Owner | Code | SDD |
|---|---|---|---|
| M01 Intake | Nguyên | form nộp bài, ghi âm WebM, trang trạng thái (PARITY-001) | **Phase 01** — lệch code |
| M02 Audio QC | Thắng | decoder 16 kHz, QC policy, ghi âm | Phase 06, chưa đóng 07–09 |
| M03 ASR | Sang | service, hallucination, identity, `asr/local.py` (faster-whisper thật) | Mọi task đã implement; M03-TASK-002 Phase 08 PASS, **chờ verdict 07–09** |
| M04 Features | Sang | extractor, text, pauses, `features/local.py` (Silero thật) | M04-TASK-003 Phase 08 PASS, **chờ verdict 07–09** |
| M05 Scoring | Sang | artifact, ridge, scorer (`artifact` công khai), coverage, `windows.py` | Đã nghiệm thu W2, W3 |
| M06 Report | Nguyên | service, evidence validator, `report/sqlite.py` | **Phase 01** — lệch code |
| M07 Review | Nguyên | service, SQLite, routing, nhận và trả bài, mở lại quyết định | **Phase 01** — lệch code |
| M08 Identity/Storage | Thắng | auth, consent, SQLite, blob, portal quản trị, xoá dữ liệu | 06–08, chờ review |

**Kiểm tra:**
- CI trên `35d3514` (Python 3.11): 305 test qua, 17 bỏ qua; ruff sạch.
- Trên máy, khi có artifact Ridge: 322 test qua; 2 smoke qua.
- Chạy local: `python -m aicefr.local`, hướng dẫn ở `docs/local-run.md`.

**Gate W4** ("một lệnh chạy server; sinh viên nộp → QC → ASR → features → scoring → report → giảng viên duyệt; thiếu model thì `NOT_EVALUATED`") **đạt về kỹ thuật**: W3 browser QA và PARITY-001 đã chạy thật. Riêng mục 6, "repo đạt checklist", thì **chưa đạt** (xem mục 4).

---

## 2. Repo gốc ↔ repo nộp bài: chuyển tính năng nào

**Nguyên tắc:**
- **Chỉ chuyển đúng vùng của owner.** Sang làm M03–M05 và phần thuần logic gắn với chúng. Tính năng thuộc vùng người khác thì owner đó làm lại, hoặc đồng ý bằng PR cho người khác làm.
- **Chuyển = viết lại theo contract và SDD của repo nộp bài**, kèm khai nguồn `ThanhSangLouis/ai-assessor-cefr@<sha>`. Không chép nguyên giao diện FastAPI.
- **Tính năng làm thay đổi phạm vi sản phẩm** (luyện tập, bài học, thành tựu) chỉ chuyển sau khi nhóm và GVHD chốt bản cam kết sản phẩm (tuần 6–7). Đề xuất "Đánh giá để học" (SCRUM-54) vẫn đang chờ GVHD.
- **Không đưa số liệu hay artifact suy ra từ S&I** vào repo nộp bài khi chưa có trả lời của CUP&A.

| Repo gốc | Nội dung | Quyết định cho repo nộp bài | Owner | Tuần |
|---|---|---|---|---|
| D020 | Ứng viên mô hình nền | Chỉ là tài liệu nghiên cứu; không chuyển code | Sang | — |
| D021 + bản OOP 08/10 | Sơ đồ lớp v3 | Thiết kế dùng chung. Cần tách các lớp thanh toán (D034–D035) khỏi trang dùng chung, và ghi cách map lớp con vai trò xuống cột `role` | Sang (sơ đồ), Thắng (contract) | W5 |
| **D022** | Trust Layer CV+, LID và lá chắn lạc đề/đọc lại đề, chỉ báo theo tiêu chí | **Chuyển**: M03 (LID), M04/M05 (lạc đề, chỉ báo, khoảng conformal). Mỗi tính năng một PR, có Spec/Test Plan bổ sung | Sang | W5–W6 |
| D022 phụ | Công tắc nhiệt độ giải mã, đo độ lặp lại; QĐ-09 bỏ `filler_ratio` khỏi bằng chứng Fluency | Repo nộp bài đã không dùng `filler_ratio`. Phần đo độ lặp lại chuyển cùng D022 nếu cần cho metric | Sang | W6 |
| D023 | Luyện tập theo nhiệm vụ | **Chờ chốt phạm vi.** Nếu được duyệt, phần đo mục tiêu thuộc M04/M05 (Sang), giao diện thuộc M01 (Nguyên) | Sang + Nguyên | sau cam kết |
| D024, D026, D027, D031, D037 | Giao diện theo vai trò, phong cách học thuật, thanh bên, chiều sâu, ảnh nền | Thuộc vùng giao diện của Nguyên. Chỉ tham khảo; Nguyên quyết định làm lại hay không | Nguyên | tuỳ Nguyên |
| D025 | Lộ trình bài học do giáo viên soạn | **Chờ chốt phạm vi**; nếu làm thì cần module mới và cả nhóm review contract | Cả nhóm | sau cam kết |
| D028, D029 | Tài khoản, hồ sơ, phiên, mật khẩu tạm | Repo nộp bài đã có phần lớn qua PARITY-001 (M08). Đối chiếu để bù chỗ thiếu | Thắng | W5–W6 |
| **D029/D036 (Google)** | Đăng nhập Google PKCE | **Không chuyển**: chỉ ở repo gốc theo quyết định ngày 07/10 | — | — |
| D030 | Chấm mù kép và báo cáo đồng thuận | **Chuyển khi bắt đầu thu điểm giám khảo** (cần cho metric đồng thuận người–người). Phần thống kê thuộc M05/nghiên cứu (Sang), luồng chấm thuộc M07 (Nguyên) | Sang + Nguyên | W6–W7 |
| D032 | Thành tựu, nhịp luyện | Chờ chốt phạm vi (đi cùng D023) | — | sau cam kết |
| **D033–D035** | Gói dịch vụ, thanh toán Stripe/MoMo/VNPay | **Không chuyển**: chỉ ở repo gốc; license S&I phi thương mại chặn thu tiền thật | — | — |
| Refactor 08/10 | `SqliteStore`, helper audit, gom phân quyền | Không áp dụng trực tiếp vì cấu trúc khác. Có thể dùng làm checklist rà trùng lặp khi review | Mỗi owner | W5 |

---

## 3. Phân công W4 và kết quả thật

### Thắng (M02, M08, dùng chung)

| ID | Việc | Kết quả 11/10 | Minh chứng |
|---|---|---|---|
| W4-T1 | U1: chuyển repo sang private, cấp quyền đọc cho GVHD | **Chưa làm** — repo vẫn PUBLIC, chưa có LICENSE. Cần quyền admin (Sang chỉ có WRITE) | — |
| W4-T2 | Pipeline coordinator | **XONG** | `pipeline/coordinator.py`, PR #31 |
| W4-T3 | Composition root và lệnh chạy server | **XONG**, dạng `python -m aicefr.local` thay cho `aicefr.api.server` | `local/`, `docs/local-run.md` |
| W4-T4 | Test tích hợp đầu-cuối trong CI | **XONG một phần**: `tests/local`, `tests/portal`, `tests/pipeline` chạy trong CI; browser QA chạy trên máy (`scripts/qa`), chưa vào CI | PR #31, PARITY-001 |
| W4-T5 | U4: ruleset `main` | **Chưa làm** — 0 ruleset, 0 PR có review; PARITY-001 commit thẳng lên `main` | — |
| W4-T6 | Thêm ruff vào CI | **XONG một phần**: có `ruff check`, chưa có `ruff format --check` | `.github/workflows` |
| W4-T7 | Đóng Phase 07–09 cho M02, M08 | **Chưa** — M02 Phase 06, M08 chờ review | `07-status.md` |

### Sang (M03, M04, M05)

| ID | Việc | Kết quả 11/10 | Minh chứng |
|---|---|---|---|
| W4-S1 | M03-TASK-002: ASR thật | **XONG**: smoke S1/S2 chạy thật, không mạng; DEP-06 dùng audio giọng tổng hợp do nhóm tự tạo | PR #32, M03-EV-004 |
| W4-S2 | M04-TASK-003: Silero VAD | **XONG**: M04-TEST-016 và smoke S1 qua | PR #32, M04-EV-002 |
| W4-S3 | Ghép M04→M05 và M05-TASK-004 | **XONG**: thêm `RidgeScorer.artifact` và chuyển coordinator, portal, local sang dùng; M05-TASK-004 nghiệm thu 03/10 | PR #32, PR #25 |
| W4-S4 | U1 phần tài liệu: gỡ số liệu S&I (SCRUM-51) | **XONG** trong tệp đang theo dõi; lịch sử Git chưa viết lại (chờ quyết định nhóm và GVHD) | PR #32 |
| W4-S5 | U3: email CUP&A (SCRUM-52) | **Đã soạn, chưa gửi** | PR #33, `docs/evidence/00-process/email-cupa-W4-S5.md` |
| W4-S6 | Phase 07–09 cho S1, S2 | Phase 07 review PASS; Phase 08 PASS trên `35d3514`; Phase 09 đã chuẩn bị. **Chờ Sang ghi verdict** | PR #33 |
| W4-S7 | Error analysis | **XONG** (W3) | PR #27 |
| W4-S8 | Sửa status cũ | **XONG** | PR #25 |
| W4-S9 | Lý do QC theo transcript | **XONG** | PR #26 |

### Nguyên (M01, M06, M07)

| ID | Việc | Kết quả 11/10 | Minh chứng |
|---|---|---|---|
| W4-N1 | Kho báo cáo SQLite | **XONG** — làm trong W3/PARITY-001, không phải Nguyên | `report/sqlite.py` |
| W4-N2 | Nối M06, M07 vào pipeline | **XONG** qua coordinator | PR #31 |
| W4-N3 | UI trạng thái tự làm mới | **XONG**: trang trạng thái tự tải lại 5 giây một lần (`meta refresh`) | `api/templates.py` |
| W4-N4 | Cập nhật status SDD M01, M06, M07 | **Chưa** — vẫn Phase 01 | `07-status.md` |
| W4-N5 | Khảo sát TC1, phỏng vấn | **Chưa có minh chứng trong repo** | — |
| W4-N6 | Cam kết hai giám khảo và một người phân xử | **Chưa có minh chứng trong repo** | — |

### Cả nhóm

| ID | Việc | Kết quả 11/10 |
|---|---|---|
| W4-C1 | Báo cáo tuần trên projects-fit; `docs/reports/week-02..04` | Có `week-03` (`.docx`) và báo cáo tuần 4 của Sang (PR #33); **thiếu `week-02`**. Trong repo còn tệp khoá Word `~$o-cao-tuan-03.docx` cần xoá |
| W4-C2 | AI Prompt Log khớp git | W04: Thắng 20 dòng, Sang 17 dòng, **Nguyên 0** |
| W4-C3 | Thống nhất danh tính commit, `.mailmap` | **Chưa** — `git log` có 7 danh tính cho 3 người ("Louis", "Panda", hai email của Nguyên…), chưa có `.mailmap` |
| W4-C4 | Review PR chéo | **Chưa** — 0 PR có review trên GitHub |

---

## 4. Checklist "repo nộp bài chuẩn" (kiểm lại ngày 11/10)

| # | Mục | Owner | Kết quả |
|---|---|---|---|
| R1 | Private, GVHD có quyền đọc | Thắng | ✗ Public |
| R2 | README đủ hướng dẫn | Thắng | ~ README đã có lệnh chạy và trỏ tới `docs/local-run.md`; còn thiếu sơ đồ module và link SDD/evidence |
| R3 | Bảo vệ `main`, PR có review | Thắng | ✗ |
| R4 | CI: lint, format, unit, tích hợp, chặn file cấm, badge | Thắng | ~ Thiếu `ruff format --check` và badge |
| R5 | Không dữ liệu cấm, không số liệu S&I trong tệp đang theo dõi | Cả nhóm | ~ Tệp hiện tại sạch phần M03–M05; lịch sử Git còn số liệu. Cần rà `docs/sources/scoring-audit.md` (Thắng) |
| R6 | Status SDD khớp code | Mỗi owner | ✗ M01, M06, M07 Phase 01; M02, M08 chưa đóng |
| R7 | Báo cáo tuần 2–4 | Cả nhóm | ✗ Thiếu tuần 2 |
| R8 | AI log khớp git | Cả nhóm | ~ Thiếu log của Nguyên |
| R9 | 3 người, 3 danh tính commit | Cả nhóm | ✗ |
| R10 | Hồ sơ rubric lên PARTIAL | Thắng | Chưa kiểm |
| R11 | License cho code của nhóm | Cả nhóm | ✗ |

---

## 5. Chuyển sang W5 (12–18/10)

1. **Thắng:** T1 (private, ưu tiên cao nhất), T5 (ruleset), `ruff format --check` và badge, T7; rà số liệu S&I trong `docs/sources/`; xoá tệp khoá Word.
2. **Sang:**
   - ghi verdict Phase 07–09 của M03-TASK-002, M04-TASK-003;
   - gửi email CUP&A;
   - thu audio của nhóm có đồng ý để chạy lại smoke trên giọng thật;
   - bắt đầu chuyển D022 (LID → lá chắn lạc đề → Trust Layer), mỗi phần một PR có Spec/Test Plan;
   - tách các lớp thanh toán khỏi trang "So do lop v3" dùng chung (L3).
3. **Nguyên:** N4 (status M01, M06, M07 khớp code), log AI W04, N5, N6.
4. **Cả nhóm:** C3 `.mailmap`, C4 review chéo cho mọi PR từ W5, báo cáo tuần 2, chốt tính năng nào của repo gốc đưa vào bản cam kết sản phẩm (mục 2, hàng "Chờ chốt phạm vi").

**Nhắc mốc (theo email bộ môn 02/10/2026 và Rubric V2-1):**
- Bản cam kết sản phẩm cuối kèm bộ metric phải thống nhất bằng văn bản, có chữ ký sinh viên và GVHD, trong **tuần 7–10**. Hạn chót là **trước tuần 11 (23/11/2026)**.
- Nhóm nên nộp nháp ở tuần 6–7.
- Các tính năng "chờ chốt phạm vi" ở mục 2 phải quyết trước khi viết bản cam kết.

## 6. Follow-up của Nguyên — 12/10/2026 (W05)

Giữ nguyên snapshot/kết quả 11/10 ở các mục trên. [Báo cáo cá nhân của Nguyên](../reports/week-04/bao-cao-tuan-04-nguyen.md) ghi evidence và kết quả xử lý chuyển tiếp:

- N1–N3 đã đối chiếu và kiểm tra lại. Phát hiện binary-read bug Windows trong M08; Nguyên cho phép fix và nhận việc thông báo Thắng. Suite liên quan sau fix: 127 passed / 3 skipped / 0 failed; lệnh/revision/working diff và giới hạn được dẫn ở báo cáo.
- N4 đã đồng bộ hiện trạng/evidence M01/M06/M07; Phase formal 01 và các verdict vẫn PENDING, không suy approval từ implementation.
- N5 có bộ khảo sát/phỏng vấn, consent/data template và manifest; Nguyên xác nhận chưa có kết quả thật, thu thập NOT_RUN.
- N6 có roster/protocol/mẫu cam kết. Ba vị trí là giả định theo chỉ dẫn Nguyên; cam kết thật NOT_VERIFIED.
- AI log W04 đã audit nhưng thiếu lịch sử gốc. Prompt ngày 12/10 ban đầu ghi W05, sau đó chuyển sang sheet Nguyên W04 theo chỉ dẫn trực tiếp của Nguyên; giữ ngày 12/10 và ghi rõ bổ sung sau tuần. Không coi các dòng chuyển này là lịch sử dùng AI ngày 05–11/10.

Task thu thập người thật, khôi phục lịch sử và verdict SDD chưa được ghi DONE. Tài liệu này không thay trạng thái owner/module khác hoặc claim cả nhóm đã nghiệm thu.
