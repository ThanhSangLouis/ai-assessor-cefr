# M12 — W6-S02 đồng bộ SDD với code (SCRUM-79)

Ngày chạy: 21/10/2026 · base `main` `cabcc44` (sau merge PR #47) · Python 3.12 trong `.venv` của repo.

## PR đã merge được đối chiếu

#43 (SCRUM-72, merge `36ab740`). Trạng thái từng task: [06-tasks](../06-tasks.md).

## Lệnh đã chạy

```bash
.venv/bin/python -m pytest -q -m "not smoke" -p no:cacheprovider --cov=aicefr.research.assign --cov=aicefr.research.agreement --cov=aicefr.api.research --cov-branch --cov-report=term tests/portal/test_research_api.py tests/test_agreement.py tests/test_assign_unit.py
```

## Kết quả

- Test: **60 passed, 2 skipped (cần sklearn)**, 0 failed.
- Coverage (statement + branch, phạm vi gói của module): 571 stmt / 52 miss · 254 branch / 40 partial · **88%**.
- Toàn bộ suite trên cùng commit (đo 21/10/2026 khi lập kế hoạch W6): 985 passed, 15 skipped, coverage 85%; `ruff check` sạch.

## Khoảng trống còn lại

- Report CLI của TASK-003 chưa có — mới có API.
- Checklist rò rỉ Network/DOM trên trình duyệt (điều kiện Done) chưa chạy; thuộc UI của Nguyên + SCRUM-68.

## Giới hạn

Đây là bằng chứng kỹ thuật do Sang tự chạy, không phải verdict. Phase 01–05 vẫn DRAFT/PENDING; Phase 07–09 (review, verification, acceptance) chờ reviewer và user ghi verdict. Không chứa số liệu Speak & Improve, audio hay dữ liệu cá nhân.
