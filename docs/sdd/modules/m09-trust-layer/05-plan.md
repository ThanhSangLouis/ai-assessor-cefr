# M09 — Plan

**Version:** v0.1 · **STATUS:** DRAFT · Phase 05 chưa được duyệt.

## Code plan

- Mở rộng `src/aicefr/asr/` cho LID contract, `features/` cho validity evidence, `scoring/` cho conformal adapter, `pipeline/coordinator.py` cho orchestration và `report/` cho schema compatibility.
- Không tạo `services/`, process hay HTTP call nội bộ; dependency được inject từ M16 composition root.
- Artifact loader dùng cùng pattern pin/hash của M05; calibration data/model nằm ngoài Git trừ fixture nhỏ có provenance rõ.
- Reason mapping là một registry server-side dùng chung cho API/UI; domain không chứa câu tiếng Việt trình bày.

## Dependency order

1. Freeze report/job schema với M16.
2. Implement immutable domain models và policy unit tests.
3. Implement artifact loader/conformal, LID/guards.
4. Integrate pipeline/report/review routing và migration compatibility.
5. Add tools, API payload, UI handoff, targeted coverage.
6. Integrate M15 UI và chạy regression/full verification.

## Rollback

Field report mới optional; config feature flag có thể dừng guard/conformal nhưng không được tạo điểm giả. Rollback code vẫn đọc report đã có; không xóa provenance/reason đã ghi.

## Required review

Thắng review transaction/idempotency/security; Nguyên review reason payload và states; Sang chịu trách nhiệm test vector, artifact provenance và không vượt claim khoa học.
