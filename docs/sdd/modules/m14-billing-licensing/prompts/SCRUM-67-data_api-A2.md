# SCRUM-67 follow-up — security coverage and browser verification

Continue in the existing `scrum-67` worktree without committing or pushing. Add meaningful tests for authorization, malformed and duplicate request data, stale erasure previews, rollback, retention races, cleanup retry, backup/restore corruption, missing protected keys, symlinks and path isolation. Preserve every production guard; do not exclude code from coverage to improve percentages.

Two bounded defects may be repaired with regression tests: reject invalid or oversized opaque actor/confirmation/fingerprint fields before service calls, and return a controlled error for malformed restore manifests. Keep other product code frozen and report any further defect before expanding scope. Include owned cleanup intents, response-bound durable jobs/media cleanup rows and related audit IDs in erasure fingerprints, with stale-preview tests.

Add a reproducible Playwright Chromium harness for a disposable clean-wheel server on loopback. It should sign in configured admin/student fixtures, quote and order through sandbox APIs, settle and replay a sandbox callback signed with the local test key, fetch the receipt, verify student/admin and CSRF denial, run personal export/retention preview, and create plus restore a backup to a fresh server-selected location. Block outbound browser traffic. Never print credentials, key material, raw error bodies or other private response content. Record unavailable prerequisites rather than substituting a mock browser run.

Run focused and relevant full tests, Ruff/format and `git diff --check`; report exact outcomes and residual coverage gaps in Vietnamese. Store this rewritten follow-up prompt as evidence and keep the original request text out of prompt logs.
