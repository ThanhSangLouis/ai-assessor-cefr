# M10 — W6-S02 đồng bộ SDD với code (SCRUM-79)

Ngày chạy: 21/10/2026 · base `main` `cabcc44` (sau merge PR #47) · Python 3.12 trong `.venv` của repo.

## PR đã merge được đối chiếu

#41 (SCRUM-70, merge `425bb4f`), #42 (SCRUM-71, merge `3a0dba1`). Trạng thái từng task: [06-tasks](../06-tasks.md).

## Lệnh đã chạy

```bash
.venv/bin/python -m pytest -q -m "not smoke" -p no:cacheprovider --cov=aicefr.practice --cov=aicefr.lessons --cov-branch --cov-report=term tests/practice tests/lessons tests/api/test_learning_api.py tests/api/test_learning_journeys.py tests/api/test_learning_validation.py tests/storage/test_learning_repository.py tests/portal/test_learning_features.py tests/test_achievements_unit.py
```

## Kết quả

- Test: **121 passed**, 0 failed.
- Coverage (statement + branch, phạm vi gói của module): 2230 stmt / 173 miss · 696 branch / 110 partial · **90%**.
- Toàn bộ suite trên cùng commit (đo 21/10/2026 khi lập kế hoạch W6): 985 passed, 15 skipped, coverage 85%; `ruff check` sạch.

## Khoảng trống còn lại

- `practice/streak.py` 81%, `practice/progress.py` 90% — cần thêm test nhánh biên (đổi ngày, múi giờ).
- UI TASK-006/007 thuộc Nguyên; TASK-008 chờ SCRUM-68.

## Giới hạn

Đây là bằng chứng kỹ thuật do Sang tự chạy, không phải verdict. Phase 01–05 vẫn DRAFT/PENDING; Phase 07–09 (review, verification, acceptance) chờ reviewer và user ghi verdict. Không chứa số liệu Speak & Improve, audio hay dữ liệu cá nhân.
