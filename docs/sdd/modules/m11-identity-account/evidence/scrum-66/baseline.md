# SCRUM-66 — Baseline

- Implementation base: `b2b573fce8da5ce679fbfc034c91b8f0aed3e7f0` (SCRUM-65 / PR #36).
- Historical target: `3b2d2b78ba5bb35bd162b8f3e5de21ade946d237`.
- Reference Sang: `40907cc35b3d04408f9a8713f16d9be99f4cd6c7`.
- Detached checkout: `/tmp/aicefr-scrum66-baseline`.
- Full non-smoke baseline: **PASS**, 358 passed, 2 deselected, 48.49 s.
- Log và coverage JSON ngoài Git: `ai-assessor-cefr-runtime/evidence/scrum-66-2026-10-15/baseline-pytest.log`, `baseline-coverage.json`.
- Schema đầu vào: v9 từ T01; không sửa SQL migration đã phát hành. Kiểm tra đường nâng v4 và bảo toàn account/session được thực hiện lại trong suite compatibility.
- Backup/restore demo v4 đã được thực hiện trong T01; T02 chỉ sử dụng database test/copy. Không migrate hoặc thay đổi database demo gốc.
