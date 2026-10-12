# M16 — Monolith Runtime and Operations — Requirement

**SCOPE ID:** M16 · **TYPE:** module · **OWNER:** Thắng
**ROOT:** `docs/sdd/modules/m16-monolith-runtime/` · **VERSION:** v0.1 · **STATUS:** DRAFT
**RELATED:** M01–M15
**RESEARCH MODE:** `RUN` đề xuất — cần gap analysis target và Sang `40907cc`, đồng thời loại hoàn toàn D043.
**USER VERDICT:** PENDING

## Goal

Tích hợp mọi module Week 5 vào một modular monolith cài/chạy được bằng một entrypoint, một SQLite database và worker local bền vững; migration, backup/restore, CI, health và package đủ để tái lập trên máy sạch.

## Requirements

- **M16-FR-001:** một composition root/route registry/entrypoint `python -m aicefr.local serve`; không app song song, internal HTTP/RPC hoặc broker.
- **M16-FR-002:** additive versioned SQLite migration từ schema hiện hành; preflight backup, transaction, foreign key, idempotent rerun và failure rollback.
- **M16-FR-003:** durable local job có job/response/attempt/lease/schema/idempotency; CAS write, bounded retry, interrupted recovery và no duplicate result/audit.
- **M16-FR-004:** readiness kiểm config/SQLite/blob/worker lease/model artifact; liveness chỉ process; không lộ path/secret.
- **M16-FR-005:** personal export/erasure/retention/cleanup/backup/restore bao phủ dữ liệu W5, giữ minimal non-identifying audit.
- **M16-FR-006:** wheel chứa code/migrations/templates/static/icon/art/font/license; clean venv install/boot offline trừ optional model asset.
- **M16-FR-007:** CI format/lint/unit/integration/coverage/build/forbidden-dependency/secret scan; smoke tách rõ prerequisite.
- **M16-FR-008:** observability có request/correlation ID nhưng không actor/transcript/audio/path làm label/log; bounded error body.
- **M16-FR-009:** D043 bị cấm: không `services/`, `platform/`, PostgreSQL, RabbitMQ, Nginx gateway, multi-container Compose, `psycopg`, `pika`.

## Acceptance Criteria

- **M16-AC-001:** database v4/sample migrate giữ count/hash/report/consent/review; migration rerun không đổi dữ liệu.
- **M16-AC-002:** forced migration failure rollback, backup restore mở được report cũ và app boot.
- **M16-AC-003:** worker crash/lease expiry/retry/concurrency tạo đúng một terminal result; không kẹt RUNNING.
- **M16-AC-004:** wheel clean install chạy three-role journey; thiếu model trả readiness/NOT_EVALUATED đúng, không fake.
- **M16-AC-005:** export/erasure/retention/cleanup retry không secret/orphan/cross-owner loss.
- **M16-AC-006:** health/error/log không lộ secret/path/PII; metrics cardinality bounded.
- **M16-AC-007:** full checks và browser package chạy trên cùng final revision/fingerprint.
- **M16-AC-008:** forbidden architecture/dependency scan bằng 0.

## Out of scope

Microservice, PostgreSQL/RabbitMQ, production deployment, HA/multi-node worker, Kubernetes, public Internet.
