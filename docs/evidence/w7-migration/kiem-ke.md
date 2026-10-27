# W7-G1 — Kiểm kê trước khi thay code

**Mục đích:** trước khi code của module được thay bằng bản chuyển từ `ThanhSangLouis/ai-assessor-cefr@059fa28`, ghi những gì **chỉ repo nộp bài có** để không mất. Mỗi mục có một quyết định:
- **giữ**: chuyển ngược sang code mới;
- **bỏ**: có lý do;
- **đã có tương đương**: ở repo gốc, kèm tệp chứng minh.

**Base của repo nộp bài:** `main` `5a170db`. Mỗi chủ module điền phần của mình; không còn mục "chưa rõ" thì W7-G1 xong.

| Module | Chủ | Trạng thái kiểm kê |
| --- | --- | --- |
| M01, M06, M07, M15 | Nguyên | chưa điền |
| M02, M08, M11, M14, M16 | Thắng | **xong 27/10/2026**, bảng dưới |
| M03, M04, M05, M09, M10, M12, M13 | Sang | **xong 25/10/2026**, bảng dưới |

## Sang — M03, M04, M05, M09 (W7-S02)

| Phần chỉ repo nộp bài có | Quyết định | Căn cứ ở repo gốc |
| --- | --- | --- |
| `asr/local.py`: adapter faster-whisper offline | đã có tương đương | `asr/whisper_adapter.py` (mlx-whisper trên macOS, faster-whisper nơi khác) |
| `asr/language.py`: nhận dạng ngôn ngữ độc lập | đã có tương đương | `WhisperAsrEngine.detect_language`; test `test_validity_shield.py` |
| `asr/identity.py`: định danh model ASR (M03-FR-003) | đã có tương đương | `trained_with.asr_model` trong artifact, pipeline đối chiếu; `test_reliability.py` |
| `asr/service.py`, `asr/validation.py`: trạng thái transcript, kiểm timestamp | đã có tương đương | `pipeline.py`, `asr/fake.py`, `asr/vad.py`; test `test_behavior.py`, `test_pipeline.py` |
| `asr/hallucination.py` bản config `hallucination-v1` | đã có tương đương | `asr/hallucination.py` của repo gốc; test `test_reliability.py`, `test_repeatability.py` |
| `features/extractor.py`, `pauses.py`, `text.py`, `local.py` (Silero offline) | đã có tương đương | `features/extract.py` (`text_features`, `vad_features`), `asr/vad.py`; test `test_features.py`, `test_behavior.py` |
| `scoring/artifact.py`: nạp artifact ngoài repo, kiểm SHA-256 | đã có tương đương | `scoring/artifacts.py` (W7-S01), cùng giá trị ghim; test `test_artifacts.py` |
| `scoring/ridge.py`, `coverage.py`: toán Ridge, coverage năm tiêu chí | đã có tương đương | `scoring/scorer.py` (`predict_overall`, `CriterionCoverage`); test `test_scorer.py` |
| `trust/` (contracts, policy, service): bằng chứng tin cậy, quyết định chuyển giảng viên | đã có tương đương | `scoring/conformal.py` (CV+, D022), `features/relevance.py`, định tuyến ở `review/router.py` (M07); test `test_conformal.py`, `test_validity_shield.py` |
| `pipeline/coordinator.py`: nối M01–M07 đồng bộ | đã có tương đương | `pipeline.py` + `services/speech/worker.py` (chấm qua bus, D050) |
| `tools/calibrate_conformal.py`, `refusal_benchmark.py`, `_trust_cli.py` | đã có tương đương | `tools/calibrate_conformal.py`, `tools/refusal_benchmark.py` của repo gốc; test `test_refusal_benchmark.py` |
| Test theo thư mục `tests/asr`, `features`, `scoring`, `trust`, `pipeline`, `tools`, `tests/api/test_trust_api.py` | bỏ | Viết cho API cũ đã gỡ; hành vi tương ứng nằm trong các test liệt kê ở cột phải các dòng trên |
| `tests/smoke/` (chạy Whisper và Silero thật, marker `smoke`) | bỏ khỏi bộ test, **giữ mục đích** | Thay bằng lần chạy thật có ghi provenance ở W7-S05 và `tools/bench_asr.py`; không tự chạy được trên CI vì cần model |

## Sang — M10, M12, M13 (W7-S03)

| Phần chỉ repo nộp bài có | Quyết định | Căn cứ ở repo gốc |
| --- | --- | --- |
| `lessons/authoring.py`: mã hoá JSON lộ trình, bài học để soạn | đã có tương đương | API soạn bài `services/core/learning/lessons_api.py` (`/api/v1/teach/...`, xuất lộ trình), `lessons/composer.py` |
| `lessons/service.py`, `lessons/rules.py` | đã có tương đương | `lessons/runner.py`, `lessons/checks.py`, `services/core/learning/facade.py` |
| `practice/contracts.py`, `progress.py`, `rules.py`, `runner.py`, `service.py` | đã có tương đương | `practice/missions.py`, `streak.py`, `feedback.py`, `nudges.py` (D055); test `test_practice_unit.py`, `test_practice_integration.py` |
| `research/service.py`: dịch vụ chấm mù, nghiên cứu trên SQLite | đã có tương đương | `storage/rating_repository.py`, `study_repository.py`, `rating_api`, `study_api`; test `test_ratings.py`, `test_learning_evidence.py` |
| `storage/learning.py`: kho học tập, chấm mù, nghiên cứu trên SQLite | đã có tương đương | `storage/lesson_repository.py`, `plan_repository.py`, `rating_repository.py`, `study_repository.py`, `replay_repository.py` (MongoDB, D048) |
| `api/learning.py`, `api/research.py` | đã có tương đương | `services/core/learning/{lessons_api,plans_api}.py`, `services/core/assessment/{rating_api,study_api,replay_api}.py` |
| `tools/agreement_report.py` bản SQLite | đã có tương đương | `tools/agreement_report.py` của repo gốc; test `test_agreement.py` |
| `tests/test_pronunciation_unit.py`: 21 test thuần cho `pronunciation/vietnamese.py` | **giữ** | Chạy trên module mới: 21/21 qua sau khi đổi phép kiểm mã mẫu theo mã đang chạy (`s_ending`, `th_sound`, `cluster`); spec M13 03 đổi theo, chờ review |
| Test `tests/lessons`, `tests/practice`, `tests/api/test_learning_*.py`, `tests/storage/test_learning_*.py` | bỏ | Viết cho API và kho cũ đã gỡ; hành vi tương ứng trong `test_lessons_*`, `test_practice_*`, `test_learning_*`, `test_achievements*`, `test_agreement.py`, `test_assign_unit.py`, `test_ratings.py`, `test_replay.py` |

Không có mục "chưa rõ" trong phần của Sang.

## Thắng — M02, M08, M11, M14, M16 (W7-T01, W7-T02, W7-T03)

| Phần chỉ repo nộp bài có | Quyết định | Căn cứ ở repo gốc |
| --- | --- | --- |
| `audio/service.py`: giải mã SoundFile/Ffmpeg | đã có tương đương | `src/aicefr/audio/` (`SoundFileDecoder`, `FfmpegDecoder`, `FirstMatchDecoder`) |
| `qc/service.py`, `qc/policy.py`: đo im lặng, vỡ tiếng, thời lượng | đã có tương đương | `src/aicefr/qc/` (`checker.py`, `measure.py`); test `test_audio_qc.py` |
| `auth/service.py`: mật khẩu PBKDF2, phiên đăng nhập, liên kết Google OAuth PKCE | đã có tương đương | `src/aicefr/auth/` (`passwords.py`, `sessions.py`, `google.py`, `pseudonyms.py`); test `test_auth.py`, `test_security.py`, `test_google_flow.py`, `test_google_unit.py` |
| `storage/auth_repository.py`: lưu trữ tài khoản, phiên trên SQLite | đã có tương đương | `src/aicefr/storage/auth_repository.py` (MongoDB collections `accounts`, `sessions`, `account_identities`, `seen_markers`, `server_secrets`, D048) |
| `storage/consent_repository.py`: lưu trữ và phiên bản đồng thuận trên SQLite | đã có tương đương | `src/aicefr/storage/consent_repository.py` (MongoDB `consents`, D048); test `test_consent.py` |
| `storage/audit_repository.py`: nhật ký kiểm toán trên SQLite | đã có tương đương | `src/aicefr/storage/audit_repository.py` (MongoDB `audit_logs`, D048); gắn micro giây ghép đúng thứ tự |
| `retention.py`, `maintenance_cli.py`: chính sách dọn dẹp và lưu trữ có thời hạn | đã có tương đương | `src/aicefr/retention.py`, `src/aicefr/maintenance_cli.py`; test `test_retention.py` |
| `accounts_cli.py`: quản trị tài khoản qua dòng lệnh | đã có tương đương | `src/aicefr/accounts_cli.py`; test `test_accounts_cli.py` |
| `billing/service.py`: quản lý gói dịch vụ và giấy phép trên SQLite | đã có tương đương | `src/aicefr/billing/` (`plans.py`, `licenses.py`, `quotes.py`, `gateways.py`, `stripe_gateway.py`, `momo_gateway.py`), `services/core/billing/`, `storage/billing_repository.py` |
| Kênh tính lượt NetID (IDPoint) | đã có tương đương | `src/aicefr/metering/` (`service.py`), `services/core/metering/`, `storage/metering_repository.py` (D049, D053, D057) |
| `local/` runtime cũ (đơn tiến trình SQLite) | bỏ | Thay bằng kiến trúc 3 dịch vụ: `services/core/`, `services/speech/`, `services/web/` sau Nginx gateway (D043, D044) |
| `limits.py`, `storage/{sqlite,paths,providers,blob,jobs}.py` | bỏ | Thay bằng `infra/blobs.py` (hỗ trợ S3/SeaweedFS, D051), `platform/redis_bus.py` (Redis BullMQ + Streams, D050), `storage/db.py` (MongoDB, D048) |
| `storage/migrations/*.sql` (v1..v9 SQLite) | bỏ | Thay bằng MongoDB migrations có sổ phiên bản `storage/migrations.py` (D048) |
| Tests cũ: `tests/test_local_runtime.py`, `test_limits.py`, `test_sqlite_storage.py` | bỏ | Thay bằng các test của nền kiến trúc mới: `test_contracts.py`, `test_ports.py`, `test_services_split.py`, `test_bus_redis.py`, `test_blobs.py`, `test_observability_unit.py`, `test_platform_unit.py`, `test_deploy_config.py` |

Không có mục "chưa rõ" trong phần của Thắng.

