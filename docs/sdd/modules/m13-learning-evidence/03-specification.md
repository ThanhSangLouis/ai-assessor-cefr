# M13 — Specification

**Version:** v0.1 · **STATUS:** DRAFT.

## Pronunciation

Input is normalized expected/heard word labels plus measured/corrected state. Pattern priority: `ed_ending`, `s_es_ending`, `final_consonant`, `th_substitution`, `initial_cluster_reduction`. Profile counts opportunities and errors, sorts sufficient evidence first, then rate/count; example carries only owned lesson/attempt locator for student and redacted word pair for cohort.

## Study lifecycle

`DRAFT → RUNNING → SURVEY → CLOSED`; only one RUNNING/SURVEY study. Enrollment snapshot uses active student + research consent, stable sort then seeded shuffle. `StudyGate` filters feedback in service serialization before template/API. Withdrawal is append-only and rechecked with consent.

## Analysis

Pre/post uses first eligible assessment after enrollment and latest assessment at least `min_days` later. Bootstrap resamples within arm with stored seed, default 2000. Output fields are nullable with `reason_code`, n and config; CSV mapping P-code is batch-local deterministic.

## Teacher time

Claim opens `ReviewSession`; decision/close/release ends it with action. Duration >30 minutes is excluded and counted. Compare assisted review vs blind sheet duration only when both n≥5. Wilson interval uses count/denominator from assessment-only records.

## Reliable change

`k=min(3, early_count, late_count)`; delta = mean(late k) − mean(early k); threshold = `1.96 * SEM * sqrt(2/k)`. SEM record has value, method `retest|manual`, source, sample count, actor and time. Retest pairing is deterministic, same owner/task and ≤48h, each response once.

## API/UI

Student pronunciation/study/survey/reliable-change; teacher cohort pronunciation/KPI; admin study lifecycle/report/export and SEM config. Every metric payload includes status, n, source/config version and disclosure.
