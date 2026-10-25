# SCRUM-87 — implementation and verification evidence

**Task branch:** `feat/SCRUM-87-W6-N02-Phieu-dong-thuan-giay-khop-he-thong`
**Base revision:** `dfb186e` (`Record current SCRUM-87 source code audit`)
**Recorded:** 2026-10-25
**Data boundary:** fixture account only; no participant audio or personal data used.

## Implementation

- The active consent contract is `consent-v2`. `audio_storage_allowed` and
  `research_allowed` are separate fields in the web form, API, account history,
  SQLite consent row, and append-only consent event.
- Migration 12 adds the audio choice with default `false`; existing consent is
  not treated as permission to store audio.
- The upload page disables recording/submission until audio storage is allowed.
  The API and storage service also reject an upload without that choice; the
  WSGI check runs before reading the request body.
- The consent page links to `src/aicefr/api/static/consent-v2.pdf`. Web and
  paper choices use the same copy in `src/aicefr/api/consent_copy.py`; the PDF
  has separate blank `Đồng ý` / `Không đồng ý` boxes, participant/signature/date
  fields, and the same version.
- Withdrawal clears both choices and blocks later uploads. It does not erase
  audio already stored.

## Verification performed

- Focused consent, migration, identity, and upload-gate tests:
  **50 passed, 2 skipped**. Both skips require Windows symlink privileges.
- `ruff check` on changed Python files: **All checks passed**.
- `git diff --check`: no whitespace errors.
- Loopback browser QA with a fixture account: verified the version and PDF link,
  both choices are separate, research-only consent keeps upload disabled, and
  audio-only consent enables upload while research remains unchecked.
  The PDF was loaded through the app route and visually checked in Chromium.
- PDF render inspection with Poppler: one A4 page; Vietnamese text, checkboxes,
  signature fields, and footer were legible with no clipping or overlap.
- Interim regressions exposed stale consent fixtures and POSIX-only protected
  file checks. Those findings were corrected in task follow-up commit
  `32d8b43`; the earlier failing counts below this section are superseded by the
  final run recorded below.

## Independent review follow-up

- The reviewer found that an active legacy consent could preselect the wider
  v2 research option. The current consent form now preselects neither choice
  unless the stored record is active for the current version; the regression
  test exercises stale v1 research consent and an empty v2 submission.
- The reviewer also requested explicit migration default-deny and withdrawal
  event assertions; tests now verify the migrated audio flag is false and the
  append-only withdrawal event stores both choices as false.
- Web/PDF copy parity was checked by PDF text extraction and rendered-page
  inspection. No PDF parsing dependency was added to the test suite.

## Final regression after Windows follow-up

- Revision: `32d8b43` (`fix(SCRUM-87): validate protected files on Windows`).
- Full repository suite: `pytest -q` — **982 passed, 26 skipped, 0 failed**.
  The run used a temporary directory on `D:` because the host's `C:` drive ran
  out of space during an earlier attempt. Symlink tests requiring Windows
  Developer Mode/privilege and tests requiring external model/audio artifacts
  were skipped as reported by pytest.
- Ruff on all changed source and test files: **All checks passed**.
- `git diff --check`: passed.

## Remaining acceptance boundary

The tracked data-management plan still labels the 12-month retention value as a
proposal, and the application has no automatic audio deletion. The web and PDF
state both facts explicitly. Before collecting real participant data, the
project must record the applicable retention/deletion policy and operational
owner. This evidence records implementation and observed checks; it does not
replace the task owner's acceptance verdict or change SDD phase approvals.
