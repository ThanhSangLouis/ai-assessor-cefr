# M15 — Product Web Experience — Requirement

**SCOPE ID:** M15 · **TYPE:** module · **OWNER:** Nguyên
**ROOT:** `docs/sdd/modules/m15-product-web/` · **VERSION:** v0.2 · **STATUS:** APPROVED — Phase 01, 2026-10-16
**ACTIVE SLICE:** W5-N01 — hệ thống thiết kế, trang công khai, tài khoản và hành trình đánh giá của sinh viên
**RELATED:** M01, M02, M05, M06, M08–M13, M16
**RESEARCH MODE:** `RUN` — chủ dự án đã chọn ngày 2026-10-16.
**ACCESSIBILITY TARGET:** tiêu chí hành vi; không claim mức conformance.
**USER VERDICT:** `APPROVED` — chủ dự án, 2026-10-16

## Mục tiêu

Cung cấp một giao diện web thống nhất cho khách chưa đăng nhập và sinh viên, hỗ trợ hành trình từ trang công khai, consent và tài khoản đến ghi/nộp bài nói, theo dõi tiến độ, xem report/evidence và phục hồi lỗi. Giao diện chỉ hiển thị dữ liệu, quyền và trạng thái do server/module producer cung cấp; không tự tạo role, score, band, consent hoặc trạng thái xử lý.

## Phạm vi W5-N01

### Trong phạm vi

1. **W5-N01.1 — Design system và shell:** design token theo ý nghĩa; component/state dùng chung có accessibility; navigation cho khách và sinh viên; Roboto, icon/art lưu local; light/dark theme; responsive và reduced motion.
2. **W5-N01.2 — Trang công khai:** landing page, login và trang giải thích band với wording dựa trên evidence.
3. **W5-N01.3 — Consent và tài khoản:** trạng thái đồng thuận; bốn tab tài khoản (hồ sơ, bảo mật, hoạt động, dữ liệu); phiên đăng nhập; trạng thái Google link/configuration do M11 cung cấp.
4. **W5-N01.4 — Đầu vào đánh giá:** thời gian chuẩn bị 30 giây có nút bỏ qua rõ ràng; ghi âm/upload, nghe lại, ghi lại, nộp bài, tiến độ xử lý và phục hồi lỗi upload.
5. **W5-N01.5 — Lịch sử và report:** lịch sử phản hồi, tiến độ, bằng chứng trong report và audio seek; gồm trạng thái không có dữ liệu, thiếu bằng chứng và retry.
6. **W5-N01.6 — Student evidence blocks:** chỉ hiển thị dữ liệu reliable change, phát âm và study do M13 phê duyệt, kèm nguồn, số mẫu và trạng thái thiếu dữ liệu.
7. **W5-N01.7 — Browser evidence:** kiểm tra desktop/mobile, keyboard, focus, theme, motion, overflow, console và network gắn với revision được kiểm tra.

### Ngoài phạm vi W5-N01

- Trang giảng viên và chấm mù (W5-N03), trang learning/practice/lesson (W5-N02), trang quản trị và billing (W5-N04).
- Tự triển khai producer API, policy auth/authorization, QC/scoring/report/statistics hoặc database schema do module khác sở hữu. W5-N01 tiêu thụ contract đã được duyệt.
- Public deployment, CDN/font/analytics bên thứ ba hoặc hành vi phụ thuộc dịch vụ bên ngoài đang hoạt động.
- Đánh dấu task hoàn tất bằng trang mock. Fixture được dùng cho component test; hành trình hoàn chỉnh phải tích hợp contract local đã duyệt.

## Functional Requirements (Yêu cầu chức năng) — M15 module

Các requirement tổng thể của M15 được giữ nguyên; phần W5-N01 bên dưới bổ sung chi tiết cho riêng lát cắt đang thực hiện.

- **M15-FR-001:** một design system cho public/student/teacher/admin: token, component, icons, Roboto local, light/dark, responsive và accessibility states.
- **M15-FR-002:** role navigation; desktop sidebar, tablet compact, mobile top+bottom navigation; badge/count không lộ quyền/dữ liệu.
- **M15-FR-003:** public landing/login/bands nói đúng giới hạn: hỗ trợ đánh giá, không chứng chỉ/đậu-rớt/độ chính xác chưa đo.
- **M15-FR-004:** student critical journey consent → record/upload → progress → report → evidence/audio → history/progress/account.
- **M15-FR-005:** learning journey roadmap → lesson/review/result/achievement/pronunciation; practice không band.
- **M15-FR-006:** teacher journey queue/review/stats, blind rate, authoring, insight override với conflict/recovery.
- **M15-FR-007:** admin journey account/task/model/config/audit/data/rating/study/billing với confirm/loading/empty/error/success.
- **M15-FR-008:** background art/motion decorative only, no pointer/overflow/print/screen-reader impact; reduced motion disables nonessential animation.
- **M15-FR-009:** browser QA desktop 1280×800 và mobile 390×844; critical console/failed request/external request bằng 0 trừ mock khai báo.

## Acceptance Criteria (Tiêu chí chấp nhận) — M15 module

- **M15-AC-001:** component states và contrast/focus/keyboard/labels đạt cho cả theme/viewport.
- **M15-AC-002:** mỗi role chỉ thấy và truy cập đúng navigation/action; server vẫn là nguồn authorization.
- **M15-AC-003:** recorder luôn cho nghe lại, ghi lại hoặc nộp; 30 giây preparation có skip và trạng thái rõ.
- **M15-AC-004:** mọi page chính có loading/empty/error/retry/success; dialog trả focus; mobile không overflow hoặc che action/content.
- **M15-AC-005:** report/trust/research/pronunciation/billing wording không vượt evidence; null/insufficient không biến thành 0.
- **M15-AC-006:** blind DOM/network không lộ forbidden fields; secret/path/token không vào DOM.
- **M15-AC-007:** wheel sạch chứa toàn bộ template/CSS/JS/icons/art/font/license và chạy không tải asset ngoài.
- **M15-AC-008:** screenshot/result JSON/console-network summary trace được tới route/viewport/revision.

## W5-N01 Requirement Refinement

Các requirement dưới đây làm rõ M15-FR-001–004 và M15-FR-008–009 cho W5-N01. M15-FR-005–007 và các luồng N02–N04 không thay đổi trong refinement này.

- **M15-N01-FR-001 — Shell và component:** trang N01 dùng chung token/component local cho typography, color, spacing, focus, control, status, loading, empty, error, disclosure và recorder/report. Light/dark theme và responsive layout giữ nguyên ý nghĩa, khả năng đọc và thao tác.
- **M15-N01-FR-002 — Navigation cho khách/sinh viên:** khách truy cập được trang công khai và login; sinh viên đã đăng nhập chỉ thấy navigation/action dành cho sinh viên. Server quyết định role, ownership và consent; mở URL trực tiếp vẫn nhận đúng kết quả allow/deny/not-found từ server.
- **M15-N01-FR-003 — Wording trang công khai:** landing/login/bands mô tả công cụ hỗ trợ đánh giá kỹ năng nói cho học tập. Không tuyên bố chứng chỉ, quyết định đậu/rớt hoặc độ chính xác chưa đo.
- **M15-N01-FR-004 — Consent và tài khoản:** consent accept/withdraw và trạng thái account/session/Google phản ánh contract M11 đã duyệt. Account có đủ bốn tab và giải thích trạng thái chưa cấu hình/disabled mà không lộ credential hoặc dữ liệu nội bộ.
- **M15-N01-FR-005 — Hành trình đánh giá:** sinh viên có thể chuẩn bị, ghi âm hoặc upload, nghe lại, ghi lại hoặc nộp bài, xem tiến độ xử lý và phục hồi lượt nộp bị từ chối, lỗi hoặc gián đoạn mà không tạo thao tác trùng.
- **M15-N01-FR-006 — Tiến độ, report và lịch sử:** sinh viên chỉ mở được history, progress và report của mình; trạng thái report/audio hỗ trợ loading, unavailable, retry và hoàn tất mà không tự tạo dữ liệu.
- **M15-N01-FR-007 — Disclosure student evidence:** evidence từ M09/M13 chỉ xuất hiện khi contract producer cho phép. Khi áp dụng, nguồn, sample count, threshold, `insufficient_evidence`/`NOT_EVALUATED` và trạng thái thiếu dữ liệu được giữ rõ.
- **M15-N01-FR-008 — Art và motion:** art trang trí được lưu local, không chặn thao tác, tạo horizontal overflow, mang thông tin duy nhất hoặc xuất hiện khi in. Reduced-motion preference tắt chuyển động không thiết yếu.
- **M15-N01-FR-009 — Browser quality evidence:** browser result ghi revision, route, role, viewport, assertion, screenshot hash và console/network summary. Asset sản phẩm không cần tải từ nguồn ngoài.

## Acceptance Criteria (Tiêu chí chấp nhận) — W5-N01

| ID | FR liên quan | Tiêu chí quan sát được |
| --- | --- | --- |
| **M15-N01-AC-001** | N01-FR-001, N01-FR-008 | Mọi trang N01 dùng token/component chung. Form/control có label, keyboard operation, visible focus, disabled/loading/error state và giữ nguyên ý nghĩa ở light/dark theme. Accessibility kiểm theo hành vi; không claim mức conformance. |
| **M15-N01-AC-002** | N01-FR-002, N01-FR-004 | Public/student navigation khớp route/role contract đã duyệt. Direct URL, foreign response ID, thiếu session hoặc thiếu consent được kiểm tra ở server; ẩn link không được xem là authorization. |
| **M15-N01-AC-003** | N01-FR-003 | Landing/login/bands không có tuyên bố chứng chỉ, đậu/rớt hoặc độ chính xác chưa đo. Wording nói rõ output là estimate/supporting evidence khi phù hợp. |
| **M15-N01-AC-004** | N01-FR-004 | Consent và bốn tab account hiển thị đúng loading/empty/success/error/disabled theo contract. Consent withdrawal và lỗi session/account có bước tiếp theo để phục hồi, không lộ secret. |
| **M15-N01-AC-005** | N01-FR-005 | Preparation kéo dài 30 giây và có nút skip rõ. Trước khi nộp, sinh viên nghe lại, ghi lại hoặc submit được. Upload bị từ chối/lỗi network có đường retry/recovery; thao tác lặp không tạo submission trùng. |
| **M15-N01-AC-006** | N01-FR-006, N01-FR-007 | Progress/history/report/audio hiển thị state theo contract. Overall score/band không trình bày thành năm điểm criterion riêng; evidence/coverage từng criterion được tách biệt. Evidence null/thiếu không hiển thị thành 0. Bài độc thoại giữ `Interaction=null` với `insufficient_evidence`. |
| **M15-N01-AC-007** | N01-FR-001, N01-FR-008 | Asset sản phẩm được lưu local. Kiểm tra responsive tại 360, 390, 768, 1280 CSS px (bao gồm 390×844 và 1280×800), zoom 200%, print và reduced motion không làm cắt/che primary action hoặc tạo horizontal overflow. |
| **M15-N01-AC-008** | N01-FR-009 | Browser result JSON có final revision, route, role, viewport và assertion; screenshot có SHA-256 đã đối chiếu. Console error, failed request và external request chưa khai báo bằng 0 trên hành trình bắt buộc. |
| **M15-N01-AC-009** | N01-FR-001, N01-FR-004–006 | DOM/response N01 không để lộ session token, password, client secret, filesystem path nội bộ, transcript/audio của owner khác hoặc data bị chặn theo role/consent contract. Blind-evaluation fields thuộc W5-N03. |
| **M15-N01-AC-010** | N01-FR-001, N01-FR-008 | Font, icon và art có thể đóng gói local cùng license/provenance metadata; clean-wheel check được tích hợp với M16/W5-T04 và không được nhận là hoàn tất riêng bởi N01. |

## Dependencies và handoff

Phase 05 readiness cần contract có version, owner review và test example cho các trang liên quan: M11 identity/consent/account/session/Google; M01 response/task status; M02 upload/QC; M06 report/audio/history; M08 trạng thái student-visible phát sinh từ review nếu có; M09 trust/refusal evidence; M13 study/pronunciation/reliable-change disclosure; M16 asset/package/runtime. Sau khi nhận đủ input producer, M15 lập canonical route/method/role/consent matrix và page-to-contract map. Technical handoff không tự thay verdict của owner.

## Decision register của Phase 01

| Quyết định | Hiện trạng | Cần chủ dự án chốt |
| --- | --- | --- |
| Research mode | `RUN`, chủ dự án chọn 2026-10-16 | Ghi kết quả ở `02-research.md`; review cùng Phase 03. |
| Accessibility target | Chủ dự án chọn tiêu chí hành vi, không claim mức conformance, 2026-10-16 | Phản ánh trong Specification/Test Plan; không gọi đây là WCAG conformance. |
| Route/API matrix | Phụ thuộc contract producer và route ownership review | Phân biệt route/state quan sát được với route/API proposal; chỉ freeze contract sau owner review liên module. |

## Ngoài phạm vi

Native mobile app, public deployment, third-party tracking/assets, scoring/model/rubric changes, backend authorization implementation, teacher/admin workflow và acceptance W5-N02–N04. Thay đổi rubric/band mapping phải quay lại M05 và được duyệt.
