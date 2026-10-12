# M09 — Specification

**Version:** v0.1 · **STATUS:** DRAFT · Phase 03 chưa được duyệt.

## Domain contract

```text
TrustAssessment
- language: LanguageEvidence(method, version, confidence, decision)
- relevance: GuardEvidence(kind, value, threshold_version, spans, decision)
- prediction_set: ConformalSet(alpha, bands, calibration_id, checksum)
- criterion_indicators: list[CriterionIndicator(name, coverage, label, evidence_refs)]
- reasons: ordered unique list[ReasonCode]
- disposition: CONTINUE | REVIEW_REQUIRED | NOT_EVALUATED | REJECTED
```

Reason code tối thiểu: `LANGUAGE_NOT_ENGLISH`, `LANGUAGE_UNCERTAIN`, `OFF_TOPIC_SUSPECTED`, `PROMPT_READING_SUSPECTED`, `SCORE_NEAR_BOUNDARY`, `CALIBRATION_MISSING`, `CALIBRATION_HASH_MISMATCH`, `LONG_RESPONSE_REVIEW`.

## Processing flow

1. Pipeline nhận transcript/segment/provenance hợp lệ từ M03–M04.
2. LID và validity shields tạo evidence độc lập, không sửa feature/scorer input.
3. Nếu prerequisite chấm thiếu, trả `NOT_EVALUATED`; nếu policy từ chối rõ, trả `REJECTED`; uncertainty còn lại là `REVIEW_REQUIRED`.
4. Scorer tạo overall candidate; conformal adapter tạo band set từ calibration artifact đã verify.
5. Report builder ghép result + trust evidence; reasons được de-duplicate theo thứ tự ổn định.
6. Repository ghi report và review candidate trong transaction/idempotency contract của M16.

## Internal API

- `LanguageIdentifier.evaluate(transcript, segments) -> LanguageEvidence`
- `ValidityShield.evaluate(task, transcript, segments) -> tuple[GuardEvidence, ...]`
- `ConformalPredictor.predict(score, artifact) -> ConformalSet`
- `TrustPolicy.decide(language, guards, conformal, prerequisites) -> TrustDecision`
- `RefusalBenchmark.run(manifest, config, seed) -> BenchmarkSummary`

Mọi dataclass/model phải immutable hoặc không bị mutate sau persistence; timestamp/seed được inject để test deterministic.

## Report/API payload

`GET /api/v1/reports/{response_id}` bổ sung `trust`, `prediction_set`, `criterion_indicators`, `provenance`; field mới optional khi đọc report cũ. Student chỉ nhận message an toàn và recovery; teacher/admin nhận thêm method/version/evidence nhưng không nhận path artifact.

## UI states

- `CONTINUE`: hiển thị band/set và disclosure.
- `REVIEW_REQUIRED`: banner lý do tiếng Việt, không dùng màu làm tín hiệu duy nhất, có trạng thái chờ giảng viên.
- `NOT_EVALUATED`: không render band; nêu prerequisite thiếu và cách thử lại/liên hệ.
- `REJECTED`: nêu input không phù hợp và cho nộp lại; không chuyển thành “điểm thấp”.

## Security, privacy và failure

- Hash artifact trước khi parse; schema/version/finite-number validation; giới hạn kích thước.
- Không nhận threshold từ request; config server-side có version.
- Không ghi transcript/evidence text vào log; evidence trong report chỉ gồm span tối thiểu được phép.
- Unknown reason code render fallback an toàn; tool không ghi đè artifact đầu vào.
