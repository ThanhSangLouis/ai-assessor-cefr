# SCRUM-67 — Baseline

W5 target `3b2d2b7`, Sang `40907cc`; actual base `bab5f2513b1377013b2538143b50d30de650dc0f` (main T01 `840efb9` + T02 `754ee9a`). Không cập nhật bản Sang hoặc sửa SQL/checksum v9.

Detached checkout `/tmp/aicefr-scrum67-baseline`. Full non-smoke: **PASS — 425 passed, 0 failed/skip, 2 deselected**, 76.24 s. Log và coverage ngoài Git: `ai-assessor-cefr-runtime/evidence/scrum-67-2026-10-15/baseline-pytest.log`, `baseline-coverage.json`. Model artifact lấy từ runtime/models; không gọi payment provider hoặc model download.

Global SDD approval và reviewer acceptance chưa được suy ra từ baseline PASS. Demo SQLite/blob gốc không thay đổi; backup/restore verification T03 dùng dữ liệu test riêng.
