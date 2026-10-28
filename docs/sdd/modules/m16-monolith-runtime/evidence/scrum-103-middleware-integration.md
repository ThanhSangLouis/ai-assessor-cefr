# M16 middleware integration support — SCRUM-103

**Date:** 2026-10-28

**Branch:** `feat/SCRUM-103-W7-N02-M15-trang-va-test-E2E`

**Base:** `1abd17f0f4ac40bdfe78f8a21672fd302eac7fe0`
**Authorization:** project owner explicitly expanded SCRUM-103 to include the M16 middleware needed by the web/E2E app.

## Change

Added `src/aicefr/api/middleware.py` from `ThanhSangLouis/ai-assessor-cefr@0853c951e796b299d81dc363c3e0e20616c4e631`. It defines `RequestContextMiddleware`, `SecurityHeadersMiddleware` and `LoginRateLimitMiddleware`, already imported by `services/runtime.py` and `api/main.py`.

A focused regression found that when `RequestContextMiddleware` converted an unhandled exception into a generic 500 response, the inner `SecurityHeadersMiddleware` had already unwound. The fallback response therefore missed security and API no-store headers. A shared `_apply_security_headers` helper now applies the same policy to normal and fallback responses.

## Verification

- `pytest -q tests/test_middleware.py --no-cov`: 5 passed, covering request IDs, security/cache headers, HTTPS-only HSTS, login throttling and generic errors.
- `ruff check src/aicefr/api/middleware.py tests/test_middleware.py`: passed.
- `compileall` for the middleware and focused tests: passed.
- `git diff --check`: passed after the SCRUM-103/M16 documentation update.

## Dependency integration and final verification

After this initial M16 checkpoint, the project owner authorized integrating SCRUM-92 foundation PR #66 and SCRUM-102 PR #67. Both dependencies are already in the PR's `main` base; neither is part of this SCRUM-103 diff. The assessment package is available to `api.main` and the E2E server.

- The 47-test focused middleware/SCRUM-102 integration command passed.
- The full E2E suite passed all 79 cases on isolated MongoDB 7.0.45 with synthetic, SHA-pinned model fixtures.
- The integrated admin model-list endpoint now uses `aicefr.scoring.artifacts.model_dir()`; its prior import of nonexistent `scorer.MODEL_DIR` returned an internal error.
- Ruff, Python compilation and `git diff --check` are recorded at the final revision.

The latest owner instruction directs [PR #68](https://github.com/thanglb2005/ai-assessor-cefr/pull/68) to `main`, overriding Jira's original `migrate/w7-repo-goc` target. SCRUM-103 remains `In Progress` in Jira; this middleware evidence does not record owner acceptance.

M16 task status and verdicts are unchanged. **M16 owner review is pending**; this integration evidence does not mark M16 or SCRUM-103 `PASS`, `DONE` or accepted.
