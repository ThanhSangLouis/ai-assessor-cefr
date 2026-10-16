# SCRUM-70 integration handoff

## Runtime and boundary

The learning services share the application SQLite store and BlobStore. Practice and lesson attempts are persisted through `LearningRepository`, run through the dedicated no-score `PracticeRunner`, and never enter assessment response/report/scorer/teacher-review queues. Student learning routes require a current session, student role, and active consent; teacher authoring, insights, and override routes require teacher/admin role. Unsafe requests retain the WSGI same-origin CSRF check.

The default local composition seeds the sample learning catalogue idempotently before serving the learning routes. A missing assessment scorer does not disable the practice runner. If ASR is unavailable, the attempt is stored as `NOT_EVALUATED` with a stable reason. Learning does not fabricate silence, transcript, or measurement results when ASR/VAD is unavailable.

API JSON revisions accept bounded integers or digit strings and reject booleans, floats, malformed values, and overflow before calling a mutation. Multipart lesson versions and round indices are parsed from digit strings with bounds. Stale CAS revisions and conflicting idempotency keys return 409. Invalid domain payloads return 422; malformed transport input returns 400; wrong roles return 403; absent or foreign owner-scoped objects return 404. Audio routes check allowlisted filename extension against declared MIME and then use the bounded decoder path.

## Endpoint inventory

| Audience | Endpoints |
| --- | --- |
| Student | `GET /api/v1/practice` and `/api/v1/practice/missions`; `GET /api/v1/practice/missions/{mission_id}`; `POST/GET /api/v1/practice/attempts`; `GET/DELETE /api/v1/practice/attempts/{attempt_id}`; `GET /api/v1/practice/recommendation` |
| Student | `GET /api/v1/learn/path`; `GET /api/v1/learn/lessons/{lesson_id}`; `GET /api/v1/learn/lessons/{lesson_id}/versions/{version}`; `GET /api/v1/learn/lessons/{lesson_id}/progress?version={version}`; `GET /api/v1/learn/lessons/{lesson_id}/versions/{version}/steps/{step_id}/media/{media_id}` |
| Student | `POST/GET /api/v1/learn/step-attempts`; `GET/DELETE /api/v1/learn/step-attempts/{attempt_id}`; `GET /api/v1/learn/reviews/due`; `POST /api/v1/learn/reviews/{review_id}/attempts` |
| Teacher/admin | `GET /api/v1/teacher/learn/insights/{owner_id}`; `POST /api/v1/teacher/learn/paths/import`; `GET /api/v1/teacher/learn/paths/{path_id}/export`; `POST/GET/DELETE /api/v1/teacher/learn/paths`; `POST /api/v1/teacher/learn/paths/{path_id}/publish`; `POST /api/v1/teacher/learn/paths/{path_id}/reorder`; `POST/DELETE /api/v1/teacher/learn/paths/{path_id}/units` |
| Teacher/admin | `POST /api/v1/teacher/learn/lessons/import`; `GET /api/v1/teacher/learn/lessons/{lesson_id}/export`; `POST/GET/DELETE /api/v1/teacher/learn/lessons`; `POST /api/v1/teacher/learn/lessons/{lesson_id}/publish`; `POST /api/v1/teacher/learn/lessons/{lesson_id}/lint`; `DELETE /api/v1/teacher/learn/lessons/{lesson_id}/steps/{step_id}`; `POST /api/v1/teacher/learn/lessons/{lesson_id}/steps/reorder` |
| Teacher/admin | `POST /api/v1/teacher/learn/lessons/{lesson_id}/versions/{version}/steps/{step_id}/media`; `GET` the returned scoped media URL for draft preview; `POST /api/v1/teacher/learn/step-attempts/{attempt_id}/override` |

Path import/export uses bounded typed JSON. Bundles do not include binary sample media; uploaded audio is held by a version/step-scoped immutable media artifact and the published lesson payload supplies its media locator. Teacher override is a separate append-only audit event and does not rewrite the saved learner result.

## Verification run

The following checks passed in the SCRUM-70 worktree:

- `tests/api/test_learning_api.py tests/api/test_learning_validation.py tests/api/test_learning_journeys.py`: 21 passed. Covers session/role/consent/CSRF boundaries, unknown and foreign resources, strict revision parsing, teacher path/unit/lesson authoring and publication, exact-version student reads, stale path CAS, media/version journeys, a multipart practice submit/replay/conflict, and a due-review submit that remains not evaluated when ASR is absent.
- `tests/local/test_foundation_runtime.py tests/practice/test_runtime.py tests/portal/test_portal.py -k 'foundation or practice_runtime or runner or schema10 or teacher_override_feedback'`: 10 passed. Covers the scorer-isolated runtime, runner error handling, verified schema-10 restore migration, and retention of teacher override feedback with its source.
- Ruff check passed for `src/aicefr/api/learning.py`, `src/aicefr/lessons/service.py`, and `tests/api/test_learning_api.py`; those owned files were formatted.

The repository-wide test/coverage run, clean-wheel smoke test, and browser QA are run by the root integration owner; no coverage percentage or browser result is claimed here. No front-end learning UI is included in this backend handoff.
