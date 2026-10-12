# M15 — Research và UI Adaptation Map

**Version:** v0.1 · **STATUS:** DRAFT.
Nguồn: Sang `40907cc`, `docs/web/SPEC_WEB.md`, D024/D026/D027/D031/D037 và pages hiện hành; chỉ đọc.

| REF | Giá trị | Target use | Decision |
| --- | --- | --- | --- |
| M15-REF-01 | role IA/navigation | giữ journey, map route target | ADAPT |
| M15-REF-02 | recorder nghe lại trước nộp | dùng component chung | ADOPT |
| M15-REF-03 | roadmap/lesson/teacher/admin layouts | dùng anatomy/states | INSPIRE |
| M15-REF-04 | Roboto local/icon sprite | package cùng license | ADAPT |
| M15-REF-05 | hill/contour art and motion | giữ decorative behavior, generate deterministically | ADAPT |
| M15-REF-06 | browser tests | chuyển thành target route/contract matrix | ADAPT |

Target hiện dùng HTML WSGI đơn giản, JS nhỏ và package-data chỉ có `api/static/*.js`. Plan phải bổ sung templates/CSS/SVG/font/package metadata; không đưa frontend framework mới nếu không có quyết định riêng.
