# M15 — Product Web Experience — Requirement

**SCOPE ID:** M15 · **TYPE:** module · **OWNER:** Nguyên
**ROOT:** `docs/sdd/modules/m15-product-web/` · **VERSION:** v0.2 · **STATUS:** APPROVED
**RELATED:** M01, M06–M14, M16
**RESEARCH MODE:** `RUN` — chủ dự án chọn ngày 15/10/2026; kiểm chứng inventory UI/UX D024/D026/D027/D031/D037 và accessibility/responsive behavior.
**USER VERDICT:** APPROVED — chủ dự án, 15/10/2026 (Asia/Bangkok).

## Mục tiêu, người dùng và ranh giới

M15 cung cấp một web UI thống nhất cho khách, sinh viên, giảng viên và quản trị viên trong modular monolith. Scope gồm page/template, design token/component, static asset, tương tác browser và browser QA. Authorization, scoring, rule học tập, thanh toán, dữ liệu nghiên cứu và persistence do module nghiệp vụ sở hữu; M15 dùng contract được owner module duyệt.

| Task container của Nguyên theo `docs/plan/week-05.md` | Hành trình thuộc M15 | Module cung cấp contract |
| --- | --- | --- |
| W5-N01 | Public → login/consent → record/upload → progress/report/history/account | M01, M06, M08, M09, M11, M13 |
| W5-N02 | Practice → lesson/review → result/progress/achievement/pronunciation | M10, M13 |
| W5-N03 | Teacher queue/review/stats → blind rating → authoring/insight | M07, M10, M12, M13 |
| W5-N04 | Admin account/config/data/rating/study/billing → full cross-role browser QA | M11–M14, M16 |

`M15-TASK-007` thuộc W5-T04 của Thắng (tích hợp/package cuối), không thuộc bốn task của Nguyên. Page inventory trong W5 là input để chốt page/state/API matrix ở Phase 03; route/payload mới chỉ có hiệu lực khi owner contract liên quan duyệt.

## Requirements

- **M15-FR-001:** một design system cho public/student/teacher/admin: token, component, icons, Roboto local, light/dark, responsive và accessibility states.
- **M15-FR-002:** role navigation; desktop sidebar, tablet compact, mobile top+bottom navigation; badge/count không lộ quyền/dữ liệu.
- **M15-FR-003:** public landing/login/bands nói đúng giới hạn: hỗ trợ đánh giá, không chứng chỉ/đậu-rớt/độ chính xác chưa đo.
- **M15-FR-004:** student critical journey consent → record/upload → progress → report → evidence/audio → history/progress/account.
- **M15-FR-005:** learning journey roadmap → lesson/review/result/achievement/pronunciation; practice không band.
- **M15-FR-006:** teacher journey queue/review/stats, blind rate, authoring, insight override với conflict/recovery.
- **M15-FR-007:** admin journey account/task/model/config/audit/data/rating/study/billing với confirm/loading/empty/error/success.
- **M15-FR-008:** background art/motion decorative only, no pointer/overflow/print/screen-reader impact; reduced motion disables nonessential animation.
- **M15-FR-009:** browser QA desktop 1280×800 và mobile 390×844; critical console/failed request/external request bằng 0 trừ mock khai báo.

## Acceptance Criteria

- **M15-AC-001:** component tương tác có trạng thái áp dụng, accessible name/label, focus nhìn thấy được và dùng được bằng keyboard; text/điều khiển đạt contrast AA theo Test Plan đã duyệt ở cả light/dark, desktop/mobile.
- **M15-AC-002:** navigation/action theo role và quyền thực; direct URL hoặc API không được phép bị server từ chối, không dựa vào việc ẩn nút ở browser để bảo vệ dữ liệu.
- **M15-AC-003:** sau record/upload hợp lệ, sinh viên nghe lại được audio, có thể ghi lại hoặc nộp; preparation 30 giây có skip và trạng thái còn lại rõ; lỗi thiết bị/upload có đường phục hồi.
- **M15-AC-004:** mỗi page chính có loading/empty/error/retry/success/confirm/conflict phù hợp với hành động/API trong matrix Phase 03; dialog trả focus; mobile không overflow hoặc che action/content.
- **M15-AC-005:** assessment chỉ có một overall score/band khi đủ bằng chứng; năm tiêu chí chỉ hiển thị coverage/evidence, không biến thành năm điểm; `Interaction=null` với `insufficient_evidence` cho độc thoại; practice/lesson không có CEFR band; null/insufficient không biến thành 0; claim trust/research/pronunciation/billing bám evidence và trạng thái thật.
- **M15-AC-006:** blind DOM và network payload không chứa trường danh tính hoặc kết quả máy bị cấm theo M12; secret/token/path nội bộ không xuất vào DOM hoặc browser response.
- **M15-AC-007:** wheel sạch chứa toàn bộ template/CSS/JS/icons/art/font/license và chạy không tải asset ngoài.
- **M15-AC-008:** screenshot, result JSON và console/network summary trace được tới route, role, viewport, bước/assertion và revision tích hợp; browser QA không chỉ dựa vào ảnh.

## Out of scope

Native mobile app, public deployment, third-party CDN/font/analytics, pixel-perfect copy mọi chi tiết source nếu xung đột target SDD.

## Phụ thuộc và quyết định còn mở

- UI cho M10–M14 chỉ triển khai integration sau khi payload, error, authorization và forbidden-field contract tương ứng được owner duyệt/freeze. Backend T01/T02/T03 ở revision `d60e8a4` có handoff kỹ thuật, nhưng global module verdict vẫn `PENDING`; mock chỉ phục vụ component test, không là evidence nghiệm thu integration.
- Snapshot Sang `40907cc` và `docs/web/SPEC_WEB.md` là nguồn tham khảo; Research `RUN` kiểm đúng Git object, không lấy source behavior làm contract target khi mâu thuẫn SDD.
- **Quyết định scope ngày 15/10/2026:** chủ dự án chọn `docs/plan/week-05.md` và W5-N01–N04 cho phần việc của Nguyên.
- Phase 02 Research chạy theo lựa chọn `RUN`; Phase 03–05 vẫn `PENDING`, không có quyền phát prompt triển khai.
