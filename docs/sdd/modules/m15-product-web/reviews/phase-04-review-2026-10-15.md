# M15 — Phase 04 Test Plan review — 15/10/2026

**PHASE RECORD ID:** M15-04-A1 · **SCOPE ID/ROOT:** M15 · `docs/sdd/modules/m15-product-web/`
**SUBJECT:** [Test Plan v0.2](../04-test-plan.md) sau khi chủ dự án duyệt M15 Specification v0.3 ở Phase 03.
**BASE REVISION:** `ced32e90509eee439c1660507d31b18c2854829a` trên `codex/w5-n01-n04-m15-sdd` cộng local documentation diff ngày 15/10/2026.
**TEST PLAN SHA-256 tại review:** `9e159ddf5e132f4f332bbbb08d8bc7223eacb44d0af385387f4a292f90fa2cfe`. Sau khi ghi user verdict vào metadata Test Plan, SHA-256 hiện tại là `9885734a74d561b792691795729a89d152060c6d391b225350cf351a2474900c`; không đổi test case/policy.
**USER VERDICT:** `APPROVED` ngày 15/10/2026 (Asia/Bangkok), trả lời trực tiếp “APPROVED Phase 04”. Verdict áp dụng cho Test Plan v0.2, không duyệt thay Plan/Tasks Phase 05 hoặc producer contract.

| Phase 04 check | Codex result | Evidence/giới hạn |
| --- | --- | --- |
| FR/AC → test case và expected | PASS cho thiết kế | Test Plan §Trace FR/AC → Test, M15-TEST-001–012; success/invalid/boundary/failure/recovery và permission/privacy case theo W5-N01–N04 |
| Test level/command/applicability | PASS cho thiết kế, chưa chạy | Python `pytest`/Playwright theo repo; UT, browser, coverage và wheel gate đã phân vai; `tests/web/` và M15 QA script sẽ được tạo khi implement |
| Security/privacy/a11y/responsive | PASS cho thiết kế | Direct URL/API, blind DOM/network, temporary password, receipt, 360/390/768/1280 px, keyboard/focus/contrast/reduced motion; owner policy còn chờ freeze |
| Không thêm requirement | PASS | Bám Requirement v0.2, Specification v0.3 và W5-N01–N04; W5-T04 clean-wheel final vẫn thuộc Thắng |
| Actual checks | `git diff --check`: PASS; automated M15 tests/browser/coverage: `NOT_RUN` | Chỉ sửa SDD; không gọi backend handoff hoặc mock là M15 PASS |

**OPEN FINDINGS / RISK:** Producer contracts M10–M14/M16 và canonical route chưa được cung cấp ở approved revision. M11 temp-password policy và M12 blind allowlist là security gate. Test Plan nêu expected theo quyết định M15 được chủ dự án chọn, nhưng các case integration tương ứng chưa thể thực thi/đánh `PASS` trước khi contract owner freeze. Nếu producer contract khác, cập nhật Specification/Test Plan và review lại đúng impact. Phase 05 không thể `READY` cho integration khi dependency này còn thiếu.

**UT/COVERAGE POLICY ĐỀ XUẤT ĐỂ USER DUYỆT:** UT/template/API cho logic testable là `REQUIRED`; browser E2E cho user-visible journey, a11y và responsive là `REQUIRED`; chạy `pytest-cov` line + branch trên final revision, ghi delta và critical uncovered branch. Không đặt tỷ lệ chung khi chưa có baseline và criticality theo slice; không dùng browser thay UT hoặc bỏ kiểm vì chưa có script.

**CODEX CHECK RESULT:** `PASS` cho độ đầy đủ của thiết kế test; execution `NOT_RUN` vì chưa implement. **CODEX RECOMMENDATION tại review:** `RECOMMEND APPROVAL` cho Phase 04 Test Plan v0.2 với dependency được giữ làm gate Phase 05. **NEXT ACTION:** hoàn thiện/review Plan & Tasks Phase 05, kiểm contract owner và chỉ sau Phase 05 `APPROVED` mới phát prompt Antigravity.
