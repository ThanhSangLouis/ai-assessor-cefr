# M15 — Research và UI Adaptation Map

**Version:** v0.3 · **STATUS:** DRAFT, review cùng Specification tại Phase 03.
**Research mode:** `RUN`, chủ dự án chọn ngày 15/10/2026.
**Target:** repo dự án revision `d60e8a4b9f63a0b0259ada8971e23bafdb1df041` sau pull. **Reference:** repo Sang, đúng Git object `40907cc35b3d04408f9a8713f16d9be99f4cd6c7` tại `D:\LAPTRINH\TLCN\AI\ai-assessor-cefr`; đã đọc bằng `git show`/`git ls-tree`, không dùng HEAD tham chiếu mới hơn. Browser QA trong Research: `NOT_RUN`.

Hai subagent đọc-only được user yêu cầu chia theo chức năng: public/student/learning W5-N01/N02 và teacher/blind/admin/billing W5-N03/N04. Mỗi lane trả tối đa tám finding có nguồn/gap; Codex kiểm lại các claim quan trọng trên đúng Git object và target. Subagent không sửa file/test/đưa phase verdict.

| Nguồn tại `40907cc` | Git blob ID | Nội dung kiểm |
| --- | --- | --- |
| `docs/web/SPEC_WEB.md` | `95c637891a6b70cea9e13a15fe61342718804beb` | D024/D026/D027/D031/D037, page/UX criteria |
| `src/aicefr/api/templates/base.html` | `dd90d85b01c80fd7187f65a4e817e52eeb3ac835` | role nav, skip link, theme, local font |
| `src/aicefr/api/templates/_recorder.html` | `076373dce32f7e2f40d35bbec860b80719f3b7bc` | recorder và listen-before-submit |
| `src/aicefr/api/static/recorder.js` | `55e1060eab0d62eafe90575be07160c7144f1435` | record/file review state, recovery |
| `pyproject.toml` | `93442f1c70e29498aa2850e4c01a910e3f72130f` | template/CSS/SVG/font/license packaging |
| `tests/test_frontend_contracts.py` | `4ff5b2a98486454d1ac7c38535ed5f1b929ceecd` | static contract checks |

| REF | Giá trị | Target use | Decision |
| --- | --- | --- | --- |
| M15-REF-01 | role IA/navigation | giữ journey, map route target | ADAPT |
| M15-REF-02 | recorder nghe lại trước nộp | dùng component chung theo M01/M02 capability/limit | ADAPT |
| M15-REF-03 | roadmap/lesson/teacher/admin layouts | dùng anatomy/states | INSPIRE |
| M15-REF-04 | Roboto local/icon sprite | package cùng license | ADAPT |
| M15-REF-05 | hill/contour art and motion | giữ decorative behavior, generate deterministically | ADAPT |
| M15-REF-06 | browser tests | chuyển thành target route/contract matrix | ADAPT |
| M15-REF-07 | source `static/progress.js:67–85` chuyển mọi state ngoài `QUEUED/RUNNING` sang report/result | `FAILED/REVIEW_REQUIRED` có state/recovery riêng | REJECT logic nguyên trạng |
| M15-REF-08 | source blind allowlist và admin temporary-password slip | dùng M12 allowlist, M11 one-time policy đã duyệt | ADAPT có điều kiện |

Target hiện dùng HTML WSGI đơn giản, JS nhỏ và package-data chỉ có `api/static/*.js`. Plan phải bổ sung templates/CSS/SVG/font/package metadata; không đưa frontend framework mới nếu không có quyết định riêng.

## Đối chiếu target sau pull và constraint

1. **Student flow:** source `static/recorder.js:246–255,299–314` đưa bản ghi lẫn file chọn qua bước preview; target `src/aicefr/api/static/recorder.js:55–63` ẩn preview khi chọn file rồi cho submit. Source có preparation 30 giây/skip; target form chưa có. Đây là gap tĩnh so với M15-AC-003, chưa là kết quả browser QA. Target `api/templates.py` hiển thị progress status thô; source progress terminal logic ở REF-07 không thể áp dụng nguyên trạng. Target `api/static/report.js:2–12` không báo lỗi khi audio seek/play thất bại.
2. **Role và blind:** source `main.py:574–615` dùng `optional_account` trên một số page GET; không suy ra đã rò dữ liệu. Source `rating_api.py:131–176` dựng blind sheet field-by-field; target phải chốt server page/API gate và allowlist xuyên queue/assignment/audio/report/history/admin agreement/export theo M12. Source `static/rate_one.js:99–163` không có local draft/confirm W5 yêu cầu; M15 không tuyên bố source đã có các state này.
3. **Learning/teacher:** source có 18 chặng/31 bài và A2/B1/B2 roadmap, thuộc M10 seed/data contract; không là nhiệm vụ M15 tự tạo. Nhãn cấp lộ trình không được biến thành assessment band của lesson/result. Authoring save/publish và teacher claim/revision recovery phải theo M10/M07 contract target, không copy API nguồn.
4. **M11 backend đã merge:** `docs/sdd/modules/m11-identity-account/evidence/scrum-66/{api-contract,ui-handoff}.md` ghi profile/catalog, consent/session/activity/Google, `PASSWORD_CHANGE_REQUIRED`, CSRF Origin và admin create/reset trả temporary password đúng một lần. M11-AC-006 DRAFT cấm password trong API/DOM/export, mâu thuẫn actual one-time response và W5 phiếu in. Chủ dự án chọn hướng phát một lần cho admin, CSV thường không chứa password; owner M11 vẫn phải sửa/duyệt ngoại lệ, purge/cache/no-log và contract version. Backend SCRUM-66 `READY FOR REVIEW`, không tự là approval module/N01/N04.
5. **M14 backend đã merge:** `docs/sdd/modules/m14-billing-licensing/evidence/scrum-67/{data-api-contract,ui-handoff}.md` cung cấp overview→quote→order→sandbox settle→receipt và erasure/retention/backup API. Source `templates/billing_result.html:15–70` tách order state với return/verify `left/unconfirmed/invalid/amount`; target M14 cần freeze enum/view-model/receipt auth. W5 chỉ sandbox/test. Backend SCRUM-67 `READY FOR REVIEW`, reviewer Nguyên/Sang/user còn PENDING; không là UI N04 đã xong.
6. **Assets và QA:** source Roboto local/OFL, SVG art, reduced motion, print/contrast và browser tests là pattern để adapt. Target `pyproject.toml` mới package `api/static/*.js`; wheel/browser QA M15 trên revision tích hợp vẫn `NOT_RUN`. Source test hoặc backend browser smoke không chứng minh M15-AC-001–008.

Các REF decision là đề xuất kỹ thuật, không thêm requirement hay thay verdict module khác. Chủ dự án đã chọn hướng xử lý M15-P03-01–05 ngày 15/10/2026; contract producer/version còn thiếu nên Research tiếp tục DRAFT cùng Phase 03.
