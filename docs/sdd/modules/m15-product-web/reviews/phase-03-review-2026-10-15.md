# M15 — Phase 03 Research + Specification review — 15/10/2026

**PHASE RECORD ID:** M15-03-A2 · **SCOPE ID/ROOT:** M15 · `docs/sdd/modules/m15-product-web/`

**SUBJECT:** Research v0.3 (`RUN`) + Specification v0.3 DRAFT; Requirement v0.2 có Phase 01 user verdict `APPROVED`.

**BASE REVISION:** `d60e8a4b9f63a0b0259ada8971e23bafdb1df041` (pull mới, backend SCRUM-65/66/67 đã merge) + local M15 documentation diff trên `codex/w5-n01-n04-m15-sdd`.

**SHA-256 tại lúc review:** Requirement `E7AD991965DC55E14E3453E85DDE15A9B3BB93CFD1B1CBB83B89637D17616D30`; Research `A14360CF8286118B020063E727988A8944A5BCFBB44FA9D9EC0F1B6D63F13B52`; Specification `1EFE461527934C909D2FB6957F28B057407F305BC645F07A4205D600305E198D`. Sau khi ghi user verdict vào metadata Specification, SHA-256 hiện tại của file là `5608422edaa6fc74f3500707dec07903b252a8348e9626914b1cc76cef4582e1`; không đổi page contract/traceability.

**USER VERDICT:** `APPROVED` ngày 15/10/2026 (Asia/Bangkok), theo chỉ dẫn trực tiếp “Phase 03 còn PENDING/BLOCKED ... Aproved đi và cấp prompt cho antigravity làm”. **USER DESIGN DIRECTION:** chủ dự án chọn các đề xuất Codex cho M15-P03-01–05 và sẽ cung cấp contract đã duyệt. Approval này áp dụng cho thiết kế M15 v0.3 tại Phase 03; không phải verdict của M10–M14/M16 và không xác nhận contract producer chưa được cung cấp.

## Codex self-review sau pull

| Check | Result | Evidence |
| --- | --- | --- |
| Research mode/provenance | PASS cho static inspection | User chọn `RUN`; source Sang Git object `40907cc`; hai subagent read-only theo public/student và teacher/admin; Codex kiểm claim quan trọng; browser nguồn `NOT_RUN` |
| Scope/FR→AC→Test/W5 | PASS cho bản nháp | Requirement v0.2; Specification v0.3 §Page contracts/Traceability; task W5-N01–N04 |
| Backend mới sau pull | PARTIAL | M11 SCRUM-66 [API contract](../../m11-identity-account/evidence/scrum-66/api-contract.md), [UI handoff](../../m11-identity-account/evidence/scrum-66/ui-handoff.md); M14 SCRUM-67 [data API](../../m14-billing-licensing/evidence/scrum-67/data-api-contract.md), [UI handoff](../../m14-billing-licensing/evidence/scrum-67/ui-handoff.md). Technical task `READY FOR REVIEW`; global module verdict PENDING |
| Page/state/error/privacy/a11y/responsive | PARTIAL | Specification có state và role draft; M10/M12/M13/M16 consumer contract, role matrix, metric disclosure và route quyết định chưa freeze |
| Checks thật | `git diff --check`: PASS; automated test/browser M15: `NOT_RUN` | Chỉ sửa SDD; không dùng backend test/source screenshot làm evidence M15 |

## Findings còn mở

1. **M15-P03-01 · BLOCKER · contract producer chưa được duyệt.** M10/M12/M13 vẫn Phase 01 `PENDING`; M11/M14/M16 global approval cũng PENDING dù T01/T02/T03 có implementation/handoff kỹ thuật. M15 cần schema/example, enum, role/entitlement, M12 forbidden-field, M13 metric disclosure và package contract theo version được owner Thắng/Sang duyệt. Backend `READY FOR REVIEW` không tự thành SDD `APPROVED`.
2. **M15-P03-02 · MAJOR · route migration chưa chốt.** Target sau pull giữ `/`→`/login`, `/student/consent`, `/student/responses/{id}`, `/teacher/reviews` và `/admin/*`; M11 thêm `/password-change`/`/api/v1/me/*`, M14 thêm `/api/v1/admin/billing/*`. W5 đề xuất product URL khác. Specification đã lập inventory; owner M01/M07/M10–M14/M15 cần canonical/alias/redirect theo method, server auth/consent và link stability. User chọn hướng giữ link hiện hành có kiểm quyền trong migration; bảng route cuối chưa có.
3. **M15-P03-03 · BLOCKER · temp-password policy M11 cần hòa giải.** Actual M11 `api-contract.md` ghi admin create/reset trả mật khẩu tạm một lần; W5 yêu cầu phiếu in; M11-AC-006 DRAFT cấm password trong API/DOM/export. User chọn hướng phát một lần tới admin để in phiếu, CSV account thường không mang password; M11 owner vẫn phải ghi ngoại lệ được duyệt, purge/cache/download/no-log và test leak. M15 không tự thay M11 Requirement.
4. **M15-P03-04 · MAJOR · blind allowlist và dual-role gate chưa freeze.** M12 Phase 01 `PENDING`, dù source `rating_api.py:131–176` có sheet allowlist. Cần route/payload deny matrix xuyên queue/assignment/audio/report/history/admin agreement/export, kể cả admin kiêm rater; local draft lifetime/purge/timeout retry theo W5. Source page dùng `optional_account` không chứng minh target được quyền bỏ server gate.
5. **M15-P03-05 · MAJOR · M14 UI view-model/receipt contract chưa được owner chấp nhận.** Actual SCRUM-67 handoff có sandbox overview→quote→order→settle→receipt và data controls, nhưng chỉ backend technical review; user/Nguyên/Sang acceptance PENDING. Cần enum order vs return/verify, receipt 403/404, back/refresh, sandbox wording và integration evidence trước W5-N04.

## Gói quyết định đã chọn, chờ contract version

| Finding | Hướng chủ dự án đã chọn | Owner/hồ sơ còn cần |
| --- | --- | --- |
| P03-01 | Producer cung cấp schema/example/enum/quyền và contract test cho M15 consumer | Sang: M10/M12/M13; Thắng: M11/M14/M16; version/revision và verdict |
| P03-02 | Chốt canonical URL, giữ link hiện hành có kiểm quyền trong migration | Nguyên với owner M01/M07/M10–M14; bảng GET/POST/API và auth/consent |
| P03-03 | Phiếu mật khẩu tạm một lần cho admin, CSV account thường không mang password | Thắng/M11 sửa/duyệt Requirement/Spec ngoại lệ và purge/cache/no-log |
| P03-04 | Allowlist blind theo endpoint, deny machine/identity khi assignment còn blind, kể cả admin kiêm rater | Sang/M12, Thắng/M11 duyệt role/payload/draft policy |
| P03-05 | Tách persisted order state khỏi return/verify; receipt chỉ PAID/đúng quyền; sandbox W5 | Thắng/M14 duyệt view-model/enum và UI handoff revision |

**CODEX CHECK RESULT tại thời điểm review:** `BLOCKED` bởi P03-01–05. **CODEX RECOMMENDATION tại thời điểm review:** `CHANGES REQUIRED`. Chủ dự án đã đưa verdict `APPROVED` sau khi các finding này được trình bày; finding còn mở chuyển thành dependency bắt buộc kiểm lại ở Phase 05 trước prompt integration. Approval không biến technical check thành `PASS`.

**NEXT ACTION:** review Test Plan Phase 04. Khi nhận contract producer, kiểm với code/handoff ở revision hiện hành; nếu khác giả định trong M15 Specification thì cập nhật và re-review đúng impact trước Phase 05/prompt. Plan/Tasks Phase 05 vẫn cần user verdict riêng; Antigravity implementer, Codex subagent chỉ read-only theo quyết định user.
