# Báo cáo codec authoring SCRUM-70

**Phạm vi:** codec thuần cho import/export lesson và toàn bộ cây learning path; bounded effort evidence/progress; và provenance rule-version. Source owner là domain lane (`lessons/authoring.py`, model/rules và test domain); storage owner vẫn chịu transaction, authorization và audit. Nhánh dựa trên `51eff1f`; không sửa main checkout, không commit/push.

Codec dùng canonical UTF-8 JSON, schema version 1 và SHA-256 trên nội dung đã serialize. Lesson tối đa 1 MiB; bundle path tối đa 2 MiB, 100 unit, 31 lesson, 40 step/lesson. Bundle theo thứ tự path → unit → lesson, loại bỏ source ID, revision/content version, owner và thông tin publish/media. Import tạo draft `import-v1`, ID do service cấp theo thứ tự `path`, rồi từng `unit` và `lesson`. DTO hoàn chỉnh được trả về trước khi repository mở transaction; repository phải validate toàn bundle và ghi atomically.

**Kiểm thử thực tế** (workdir `worktrees/scrum-70`):

```text
PYTHONPATH=src /home/thanglvc/Documents/HCMUTE/TLCN/ai-assessor-cefr/.venv/bin/pytest tests/lessons tests/practice -q
55 passed in 2.81s

/home/thanglvc/Documents/HCMUTE/TLCN/ai-assessor-cefr/.venv/bin/ruff check src/aicefr/lessons/authoring.py tests/lessons/test_authoring.py src/aicefr/lessons/model.py src/aicefr/lessons/checks.py src/aicefr/lessons/progress.py src/aicefr/practice/contracts.py src/aicefr/practice/missions.py tests/lessons/test_domain.py tests/practice/test_domain.py
All checks passed!

PYTHONPATH=src COVERAGE_FILE=/tmp/.coverage-domain-authoring70 /home/thanglvc/Documents/HCMUTE/TLCN/ai-assessor-cefr/.venv/bin/coverage run -m pytest tests/lessons tests/practice -q
55 passed in 2.81s
COVERAGE_FILE=/tmp/.coverage-domain-authoring70 /home/thanglvc/Documents/HCMUTE/TLCN/ai-assessor-cefr/.venv/bin/coverage report --include='*/aicefr/lessons/authoring.py,*/aicefr/lessons/progress.py,*/aicefr/lessons/checks.py,*/aicefr/practice/missions.py,*/aicefr/practice/contracts.py' -m
authoring.py: 93% statement / 118 of 130 branches covered (90.8%); progress.py: 100%; checks.py: 92%; practice missions/contracts: 94% / 95%.
```

Test boundaries cover all nine step kinds, draft and published lesson input, path hierarchy round-trip/order/ID remap, source object immutability, malformed/checksum/schema/duplicate/oversized/deep/nonfinite/owner/media/path-reference input, invalid typed content and ID factory failures. VAD tests verify overlap union, clip-duration bound, and a two-span fixture where first-to-last speaking mission measurement stays 32 seconds while the new effort scalar is 29 seconds. Progress tests confirm old passes survive failed retries and duplicate FREE attempts do not count as additional rounds.

Rule provenance is frozen by `lessons.rules.SUPPORTED_LESSON_RULES_VERSIONS` and `practice.rules.SUPPORTED_MISSION_RULES_VERSIONS` (currently `lesson-rules-v1` and `mission-rules-v1`). Drafts may retain unknown lesson rules, while publish lint rejects them; lesson evaluation and mission checking reject unsupported versions before generating results. `StepResult` stores the version actually applied.

**Kiểm thử cuối sau rule-provenance fix** (workdir `worktrees/scrum-70`):

```text
PYTHONPATH=src COVERAGE_FILE=/tmp/.coverage-final-domain70 /home/thanglvc/Documents/HCMUTE/TLCN/ai-assessor-cefr/.venv/bin/coverage run -m pytest tests/lessons tests/practice tests/storage/test_learning_repository.py -q
66 passed in 7.57s

COVERAGE_FILE=/tmp/.coverage-final-domain70 /home/thanglvc/Documents/HCMUTE/TLCN/ai-assessor-cefr/.venv/bin/coverage report --include='*/aicefr/lessons/authoring.py,*/aicefr/lessons/progress.py,*/aicefr/lessons/checks.py,*/aicefr/practice/missions.py,*/aicefr/practice/contracts.py,*/aicefr/lessons/rules.py,*/aicefr/practice/rules.py,*/aicefr/lessons/lint.py' -m
authoring.py 93% statement / 118 of 130 branches (90.8%); progress.py 100%; checks.py 92%; lint.py 91%; rules registries 100%; practice missions/contracts 94%/95%.

/home/thanglvc/Documents/HCMUTE/TLCN/ai-assessor-cefr/.venv/bin/ruff check src/aicefr/lessons/rules.py src/aicefr/practice/rules.py src/aicefr/lessons/model.py src/aicefr/lessons/lint.py src/aicefr/lessons/checks.py src/aicefr/lessons/generate.py src/aicefr/practice/bank.py src/aicefr/practice/missions.py tests/lessons/test_domain.py tests/practice/test_domain.py
All checks passed!
```

**Giới hạn còn lại:** transaction “một lesson lỗi thì không ghi dở bundle” thuộc storage repository, không thể chứng minh bằng codec thuần; repository owner xác nhận sẽ validate DTO trước transaction và có test atomic riêng. API/runtime phải chuyển lỗi phiên bản luật không hỗ trợ và các lỗi validation khác thành HTTP 422 trước khi trả fallback result. Đã gửi chính xác DTO/signatures và giới hạn cho integration/storage owner.
