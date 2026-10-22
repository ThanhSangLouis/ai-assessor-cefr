# M13 — W6-S02 đồng bộ SDD với code (SCRUM-79)

Ngày chạy: 21/10/2026 · base `main` `cabcc44` (sau merge PR #47) · Python 3.12 trong `.venv` của repo.

## PR đã merge được đối chiếu

#42 (SCRUM-71, merge `3a0dba1`), #43 (SCRUM-72, merge `36ab740`). Trạng thái từng task: [06-tasks](../06-tasks.md).

## Lệnh đã chạy

```bash
.venv/bin/python -m pytest -q -m "not smoke" -p no:cacheprovider --cov=aicefr.pronunciation --cov=aicefr.research --cov=aicefr.practice --cov-branch --cov-report=term tests/portal/test_learning_features.py tests/portal/test_research_api.py tests/test_achievements_unit.py tests/test_pronunciation_unit.py
```

## Kết quả

- Test: **44 passed**, 0 failed.
- Coverage (statement + branch, phạm vi gói của module): `pronunciation/vietnamese.py` 98% · `research/study.py` 74% · `research/teacher_time.py` 95% · `research/reliable_change.py` **25%**.
- Toàn bộ suite trên cùng commit (đo 21/10/2026 khi lập kế hoạch W6): 985 passed, 15 skipped, coverage 85%; `ruff check` sạch.

## Khoảng trống còn lại

- `reliable_change.py` (SEM / reliable change) gần như chưa có unit test — TASK-004 để PARTIAL.
- Kết luận thực nghiệm người học vẫn `NOT_EVALUATED`; chỉ khẳng định code/test.

## Giới hạn

Đây là bằng chứng kỹ thuật do Sang tự chạy, không phải verdict. Phase 01–05 vẫn DRAFT/PENDING; Phase 07–09 (review, verification, acceptance) chờ reviewer và user ghi verdict. Không chứa số liệu Speak & Improve, audio hay dữ liệu cá nhân.
