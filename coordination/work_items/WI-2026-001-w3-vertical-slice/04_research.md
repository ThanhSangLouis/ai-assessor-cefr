# WI-2026-001 W3 vertical slice - Dependency research

| Field | Value |
| --- | --- |
| `work_id` | `WI-2026-001-w3-vertical-slice` |
| `version` | `V2` |
| `status` | `DRAFT_V2` |
| `checked_at` | `2026-09-12` |

## Official-source findings

| Dependency | Verified candidate | Relevant fact | Official source |
| --- | --- | --- | --- |
| Python | `>=3.11,<3.14` | Matches project baseline; local host currently has Python 3.13 | [Python](https://www.python.org/) |
| FastAPI | `0.141.1` | PyPI latest checked; requires Python >=3.10; MIT | [FastAPI PyPI](https://pypi.org/project/fastapi/) |
| Pydantic | `2.13.5` | Stable v2 release checked; use v2 models, not `pydantic.v1` | [Pydantic PyPI](https://pypi.org/project/pydantic/) |
| pytest | `9.1.1` | Supports Python 3.10+ and Windows/POSIX | [pytest PyPI](https://pypi.org/project/pytest/) |
| Ruff | `0.16.7` | Current release seen in PyPI history on 10/09/2026 | [Ruff PyPI](https://pypi.org/project/ruff/) |
| mypy | `2.3.1` | Current release checked; CPython 3.11-3.14 wheels listed | [mypy PyPI](https://pypi.org/project/mypy/) |
| faster-whisper | `1.2.1` optional `asr` dependency | Requires Python >=3.9; PyAV bundles FFmpeg libraries; a model name can trigger Hub download | [faster-whisper PyPI](https://pypi.org/project/faster-whisper/), [official README](https://github.com/SYSTRAN/faster-whisper/blob/master/README.md) |

## Decisions proposed for V2

- Use Python 3.11-3.13 compatibility; CI matrix can start with 3.11 and the local 3.13 runtime.
- Keep `faster-whisper` behind optional dependency group `asr`; default tests use a fake adapter.
- Production/local adapter accepts only an existing local model directory in this work item. Passing a Hub model name is rejected, preventing implicit network download.
- Use PyAV through faster-whisper for decode in ASR. A separate FFmpeg executable is not mandatory for the first vertical slice; if later needed for normalization parity, add it through a new reviewed change.
- Do not install `fastapi[standard]` automatically. Add only packages required by the exact transport implementation after V3 approval.
- Pin direct dependencies in the first project config; record transitive lock and license inventory in the raw report.

## Candidate QC configuration

Các giá trị sau là default vận hành cho synthetic/dev validation, không phải threshold đã được kiểm định trên người học:

| Key | Candidate | Behavior |
| --- | ---: | --- |
| `max_upload_bytes` | 26,214,400 (25 MiB) | Reject trước decode |
| `max_duration_ms` | 300,000 | Reject input dài hơn phạm vi MVP |
| `review_below_duration_ms` | 15,000 | `REVIEW_REQUIRED`; không score |
| `target_sample_rate_hz` | 16,000 | Working PCM cho QC/ASR |
| `target_channels` | 1 | Mono working representation; raw input giữ nguyên |
| `high_silence_ratio` | 0.80 | Candidate review flag |
| `clipping_peak_threshold` | 0.999 | Định nghĩa clipped sample candidate |
| `high_clipping_ratio` | 0.01 | Candidate review flag |

Mỗi report phải ghi `qc_config_version`. Pilot/validation có thể tạo version mới; report cũ giữ provenance.

## Remaining blockers

- Human G1/G2 decisions vẫn chưa có.
- Không dependency nào được cài hoặc adapter production được implement trước V3 approval/prompt lock.
- Model file/license/cache location và approved storage chưa được quyết định; ASR smoke vì thế là optional, offline-only.
