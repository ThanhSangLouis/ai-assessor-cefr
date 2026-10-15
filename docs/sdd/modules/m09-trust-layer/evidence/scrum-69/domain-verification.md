# SCRUM-69 — Bằng chứng kiểm tra domain, LID và guards

## Baseline và phạm vi

- Historical target: `3b2d2b78ba5bb35bd162b8f3e5de21ade946d237`.
- Sang reference (chỉ đọc): `40907cc35b3d04408f9a8713f16d9be99f4cd6c7`.
- Base thực tế của worktree: `9748814cd783656c2a2f0780549349b2d1032707`.
- `HEAD` khi chạy kiểm tra vẫn là base trên; thay đổi đang ở working tree, chưa commit.

Domain lane sở hữu model/reason policy, LID, guard và test thuần: `src/aicefr/trust/{__init__,contracts,policy}.py`, `src/aicefr/asr/language.py`, `src/aicefr/features/relevance.py`, phần metadata/reason additions trong `src/aicefr/contracts.py`, `src/aicefr/asr/{local,service}.py`, `tests/trust/` và các regression test ASR liên quan. `src/aicefr/trust/service.py`, pipeline, report và API thuộc integration lane; domain lane không chỉnh các file đó.

Threshold guard đối chiếu Sang reference 40907cc: lạc đề chỉ bị nghi ngờ khi bài có ít nhất 30 từ và không có từ khóa chủ đề; đọc lại đề chỉ bị nghi ngờ với prompt tiếng Anh, bài ít nhất 10 từ và tỷ lệ 3-gram trùng từ 0.50. Đây là heuristic có version, chưa hiệu chuẩn trên dữ liệu người học và không phải claim về accuracy. LID dùng fixture tổng hợp; không có audio người học hoặc phép đo thực nghiệm trong lượt này.

## Lệnh và kết quả thực tế

Lệnh coverage đã chạy trên worktree tại base nêu trên:

```bash
PYTHONPATH=src AICEFR_MODEL_DIR=/home/thanglvc/Documents/HCMUTE/TLCN/ai-assessor-cefr-runtime/models COVERAGE_FILE=/tmp/.coverage-domain69 /home/thanglvc/Documents/HCMUTE/TLCN/ai-assessor-cefr/.venv/bin/python -m pytest tests/trust tests/asr tests/features --cov=aicefr.trust --cov=aicefr.asr.language --cov=aicefr.features.relevance --cov-report=json:/tmp/domain69-cov.json
```

Kết quả: **111 passed**, `pytest-cov` ghi JSON tại `/tmp/domain69-cov.json`; không có test skip trong lần chạy này. Coverage theo pure-logic file:

| File | Line | Branch |
| --- | ---: | ---: |
| `src/aicefr/trust/contracts.py` | 98.62% | 95.83% |
| `src/aicefr/trust/policy.py` | 96.67% | 90.91% |
| `src/aicefr/asr/language.py` | 96.97% | 100% |
| `src/aicefr/features/relevance.py` | 100% | 100% |

Lệnh được yêu cầu tính cả package `aicefr.trust`, nên tổng coverage là **69.31% line / 69.17% branch**. Nguyên nhân là `src/aicefr/trust/service.py` thuộc integration lane và có **0%** trong bộ test này; con số tổng không đại diện riêng cho domain logic. `src/aicefr/trust/__init__.py` đạt 100% line, không có branch.

Ruff đã chạy trên các file domain, LID, guards và test liên quan; kết quả `All checks passed!`. Không chạy full suite, browser/integration QA hoặc real-audio/model evaluation trong domain lane. Không có kết luận về độ chính xác LID/guard, coverage thống kê conformal trên người học hoặc hành vi runtime tích hợp.

Coverage JSON và dữ liệu đo được ở `/tmp` là artifact cục bộ của lượt kiểm tra; báo cáo này lưu các số thực tế cần cho review, không tuyên bố phép đo đó là kết quả trên dữ liệu thật.
