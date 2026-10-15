# SCRUM-70 domain contract handoff

Status: frozen domain contract, 2026-10-15. Scope: pure practice, lesson content/rules, recommendation, review schedule, and progress calculations. Persistence and runtime pipeline APIs belong to their respective lanes.

## Practice

`aicefr.practice.contracts` exports immutable `PracticePurpose`, `MissionKind`, `PracticeStatus`, `PracticeReason`, `TimeSpan`, `WordEvidence`, `MissionGoal`, `PracticeMission`, `MissionMeasurement`, `PracticeResult`, `RecommendationEvidence`, and `Recommendation`. There are exactly seven mission kinds: `SPEAK_SECONDS`, `MAX_PAUSE`, `USE_WORDS`, `UNIQUE_WORDS`, `PAST_VERBS`, `CONDITIONALS`, `READ_ALOUD`. Each `MissionGoal` has its own kind, target, optional word list, and optional reference text. `PracticeMission.target_band` is catalogue metadata only.

`aicefr.practice.rules` is the single supported mission-rule registry; its current value is `MISSION_RULES_VERSION = "mission-rules-v1"`. `PracticeResult` deliberately has no assessment score, band, or verification field. It stores purpose, status, per-goal measurements, rules version, reasons, original transcript word count, clip duration, and bounded `speaking_s` derived from the union of VAD intervals. `SPEAK_SECONDS` retains its first-to-last-span mission rule; `speaking_s` is separate effort evidence. `MissionChecker` rejects unsupported mission versions before producing a result. Language-not-English/uncertain runner results and legacy values default to zero. Every half-open `WordEvidence(start_word_index, end_word_index)` and `TimeSpan(start_s, end_s)` is validated against those source bounds. Status is derived from measurements; measured PASS/FAIL values are required, while UNSURE/UNMEASURED cannot claim a value. Stable reasons include `LANGUAGE_NOT_ENGLISH`, `LANGUAGE_UNCERTAIN`, and `LEMMA_EQUIVALENT`.

```python
MissionChecker.check(
    mission: PracticeMission,
    transcript: Transcript,
    vad_spans: Sequence[TimeSpan],
    *, purpose: PracticePurpose,
) -> PracticeResult

list_missions() -> tuple[PracticeMission, ...]
get_mission(mission_id: str) -> PracticeMission
mission_catalogue_hash() -> str
```

The catalogue contains 15 deterministic missions: five criteria × A2/B1/B2 with `PR-FLU`, `PR-COH`, `PR-RAN`, `PR-ACC`, and `PR-PHO` identifiers. The practice minimum speaking duration is enforced by the runtime QC policy before evaluation.

## Recommendation

`RecommendationEvidence` is a read-only persisted-assessment projection with `response_id`, aware `created_at`, assessment `status`, optional actual `overall_score`/`overall_band`, and criterion coverage. It is not an invented `Assessment` reconstruction. `recommend_next(*, assessments: Sequence[RecommendationEvidence], completed_mission_ids: Collection[str] = ()) -> Recommendation` selects the newest eligible ESTIMATED or REVIEW_REQUIRED assessment with an actual score and band (timestamp then response ID tie order), picks the weakest covered criterion with stable criterion-order ties, and maps to the nearest mission band. If there is no eligible assessment it selects the A2 fluency fallback with `NO_ELIGIBLE_ASSESSMENT_FALLBACK_A2`. Recommendations never produce performance scores.

## Lessons

There are exactly nine `StepKind` values: `READ_ALOUD`, `REPEAT`, `LOOK_UP`, `GAP`, `KEYWORDS`, `STARTER`, `PICTURE`, `OUTLINE`, and `FREE`. Their four stages are `MODEL` (READ_ALOUD, REPEAT), `CONTROLLED` (LOOK_UP, GAP), `GUIDED` (KEYWORDS, STARTER, PICTURE, OUTLINE), and `FREE` (FREE). `LessonStep` uses one typed payload matching its kind and stage, plus `rules_version`. `LearningPath` contains ordered `LearningUnit`s; a `Lesson` is an editable draft with revision/content version. `PublishedLessonVersion.from_lesson(...)` requires publication lint, one shared step-rules version, an aware publication timestamp, and records a content hash and immutable version snapshot.

`aicefr.lessons.rules` is the single supported lesson-rule registry; its current value is `LESSON_RULES_VERSION = "lesson-rules-v1"`. Generated lessons use that constant. `lint_lesson(lesson, *, for_publish=False)` permits incomplete and unknown-version drafts; publish validation requires supported rule versions, all four stages in order, and a FREE step with two or three strictly decreasing positive round budgets. Domain limits reject oversized inputs; none are truncated: lessons contain at most 40 steps; bounded content collections contain at most 100 items; narrative text is at most 4,096 characters; aligned reference fields are at most 2,048 characters and 512 normalized tokens. `align` checks both reference and hypothesis lengths against 512 tokens before allocating its quadratic matrix. Evaluation rejects unsupported lesson rule versions, more than 512 ASR words/tokens, an ASR word string over 1,024 characters, or a text-only transcript over 32,768 characters. Supported `StepResult.rules_version` records the exact step rule used. Request consumers must return HTTP 422 for these domain validation/value errors rather than truncating evidence. Step evaluation API:

```python
evaluate_step(
    step: LessonStep,
    transcript: Transcript,
    vad_spans: Sequence[TimeSpan],
    *, round_index: int | None = None,
    elapsed_seconds: float | None = None,
) -> StepResult
```

`StepResult` persists `step_id`, kind/status, matched/target counts, elapsed time, bounded `speaking_s` from the union of VAD intervals, VAD evidence, and typed token evidence. Overlapping spans are not double-counted and union/end bounds cannot exceed supplied clip duration. Evidence retains expected/heard token, MATCH/SUBSTITUTE/DELETE/INSERT operation, confidence, and the original transcript word locator; VAD filtering never renumbers source ASR words. Missing/low confidence and lemma-equivalent substitutions yield UNSURE. A FREE result needs a valid round index and actual elapsed time; exceeding that round's budget is FAIL with time evidence. A missing expected word has no ASR confidence and yields UNSURE. GAP passes only for a complete contiguous expected answer phrase; interleaved words or a confident wrong answer fail.

Text utilities in `aicefr.lessons.text` are `normalize_text(text)`, `lemma(word)`, `same_word(left, right)`, and `find_phrase(phrase, words)`. Normalization and English lemma rules are versioned. `align(reference, heard)` returns deterministic minimum-edit MATCH/SUBSTITUTE/DELETE pairs plus inserted hypothesis indexes. Canonical surface matches are MATCH; lemma-equivalent surface forms remain SUBSTITUTE and are not promoted to a perfect pass.

The pure authoring codec in `aicefr.lessons.authoring` exposes `export_lesson(Lesson | PublishedLessonVersion) -> bytes` and `import_lesson(data, *, lesson_id) -> Lesson`. Whole-path interchange uses immutable `LessonBundleEntry(unit_id, lesson)`, `LearningPathBundle(path, lessons)`, and `ImportedPathDraft(path, lessons)` DTOs with `export_path(bundle) -> bytes` and `import_path(data, *, id_factory) -> ImportedPathDraft`. Path export follows the ordered path units and each unit's ordered `lesson_ids`; it rejects missing, duplicate, or foreign associations. Both formats are canonical UTF-8 JSON with schema version 1 and SHA-256 content checksums. Lesson files are limited to 1 MiB; path bundles are limited to 2 MiB, 100 units, 31 lessons, and 40 steps per lesson. Source IDs, revisions, content versions, ownership, publication authority, and media references are omitted. Imports always create `import-v1` drafts; path IDs are regenerated in deterministic path→unit→lesson order by a service-injected `id_factory(kind)`. The repository must validate the complete `ImportedPathDraft` and perform the write atomically.

## Review and progress

Review inputs are timezone-aware and all due dates are returned in `Asia/Ho_Chi_Minh`. `first_review(*, due_from)` schedules +1 calendar day. Passing moves box 1 → 2/+3 days, box 2 → 3/+7 days, and box 3+ → 4/done with no due date. Failure resets to box 1/+1 day. Time is injected; domain functions do not read the system clock.

`StepCompletion` stores attempt ID, step ID, kind, status, aware `attempted_at`, FREE `round_index`, and bounded finite `speaking_s` copied from the persisted typed `StepResult`. `lesson_completion(*, steps, attempts, required_fraction=0.8)` ignores unknown steps and kind mismatches, preserves any prior COMPLETE result for a non-FREE step across failed retries, and counts each distinct FREE round once when any compatible attempt for that round has positive `speaking_s`, regardless of result status. Silent rounds do not count; completion requires every configured round for every required FREE step. The integration boundary must filter attempts to the selected immutable lesson version. S03 achievements and streak rewards are outside this domain API.

## Consumer boundary

Storage owns repository records, IDs/owner scoping, version CAS, persistence, seed provenance, and audit events. Runtime/integration owns audio QC and ASR invocation, purpose routing, authorization, no-scorer/queue/export enforcement, and adapting validated ASR/VAD output to these calls. Domain code does not export or construct a Pydantic `Assessment`, and practice results never enter assessment scoring.
