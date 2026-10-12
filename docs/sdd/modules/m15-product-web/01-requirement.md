# M15 — Product Web Experience — Requirement

**SCOPE ID:** M15 · **TYPE:** module · **OWNER:** Nguyên
**ROOT:** `docs/sdd/modules/m15-product-web/` · **VERSION:** v0.1 · **STATUS:** DRAFT
**RELATED:** M01, M06–M14, M16
**RESEARCH MODE:** `RUN` đề xuất — cần inventory UI/UX D024/D026/D027/D031/D037 và accessibility/responsive behavior.
**USER VERDICT:** PENDING

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

- **M15-AC-001:** component states và contrast/focus/keyboard/labels đạt cho cả theme/viewport.
- **M15-AC-002:** mỗi role chỉ thấy và truy cập đúng navigation/action; server vẫn là nguồn authorization.
- **M15-AC-003:** recorder luôn cho nghe lại, ghi lại hoặc nộp; 30 giây preparation có skip và trạng thái rõ.
- **M15-AC-004:** mọi page chính có loading/empty/error/retry/success; dialog trả focus; mobile không overflow hoặc che action/content.
- **M15-AC-005:** report/trust/research/pronunciation/billing wording không vượt evidence; null/insufficient không biến thành 0.
- **M15-AC-006:** blind DOM/network không lộ forbidden fields; secret/path/token không vào DOM.
- **M15-AC-007:** wheel sạch chứa toàn bộ template/CSS/JS/icons/art/font/license và chạy không tải asset ngoài.
- **M15-AC-008:** screenshot/result JSON/console-network summary trace được tới route/viewport/revision.

## Out of scope

Native mobile app, public deployment, third-party CDN/font/analytics, pixel-perfect copy mọi chi tiết source nếu xung đột target SDD.
