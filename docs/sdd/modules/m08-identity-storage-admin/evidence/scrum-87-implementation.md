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
- A broader non-smoke regression was run during implementation and returned
  `125 passed, 4 skipped, 19 failed, 3 deselected`. The failures included
  Windows-only protected-file/symlink cases and stale fixture assumptions. The
  affected consent fixtures and Windows backup-manifest path were corrected;
  the focused checks above were rerun. An independent code review then found
  and helped fix a stale-consent checkbox preselection issue; a regression test
  now confirms that stale v1 choices remain unchecked for v2 and saving no
  choices persists both flags as false. A later selected regression run returned
  `86 passed, 2 skipped, 21 failed`: one failure was the stale consent fixture,
  now corrected and covered by the focused run; the remaining failures concern
  protected-file permissions, `os.getuid`, and symlink privileges on this
  Windows host. The broader regression was not rerun after the fixture fix.

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

## Remaining acceptance boundary

The tracked data-management plan still labels the 12-month retention value as a
proposal, and the application has no automatic audio deletion. The web and PDF
state both facts explicitly. Before collecting real participant data, the
project must record the applicable retention/deletion policy and operational
owner. This evidence records implementation and observed checks; it does not
replace the task owner's acceptance verdict or change SDD phase approvals.
