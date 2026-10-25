# SCRUM-88 — browser review

**Date:** 25/10/2026  
**Branch:** `feat/SCRUM-88-W6-N03-De-bai-rubric-cham-ke-hoach-thu`  
**Code revision reviewed:** `6de3206` (task branch, not merged)  
**Environment:** Windows, Python 3.12, local WSGI server on `127.0.0.1`, Chromium through Playwright CLI.

## Scope and fixture boundary

Browser review used only fixture accounts and a generated one-second tone to make a blind rating assignment. The fixture tone contains no speech. One fixture student was marked research-consented only so the local rating batch could be displayed; no person was recruited, no real audio was recorded, and no rating was submitted. This does not measure prompt usability, CEFR accuracy, or rater agreement.

## Browser observations

| Flow | Result |
| --- | --- |
| Student task list | Both prompts appear with distinct titles, version `1`, and the 40–60-second duration. |
| Student upload page | The selected prompt is visible; 30-second preparation controls and file-upload controls render. No upload was made in this browser flow. |
| Teacher blind rating | The assigned page shows the same prompt, expected response duration, and audio player. The teacher view does not show the participant ID, response ID, machine score, or the other rater's score. |
| Rubric details | Expanding “Rubric mô tả mức A2–B2” shows all five criterion anchors, 0–6 scoring in 0.5 steps, holistic overall scoring, separate band selection, and `Interaction=null/insufficient_evidence` for monologues. The form has five criterion inputs plus a separate overall score and band. |

Screenshots captured from the local fixture UI:

- [Student task list](../../../../../../output/playwright/scrum88-student-tasks.png)
- [Student upload page](../../../../../../output/playwright/scrum88-student-upload.png)
- [Blind rating form with rubric expanded](../../../../../../output/playwright/scrum88-blind-rating-rubric.png)

Chromium logged `Transition was aborted because of invalid state. ViewTransition opt-in disabled` during navigation to the teacher rating page. The page, prompt, audio player, rubric, and controls still rendered and responded. This is recorded as a non-blocking browser console issue; the screen remains usable.

## Automated checks

- `pytest tests/local/test_foundation_runtime.py -q`: **8 passed, 1 failed**. The only failure is the existing symlink check, which Windows rejected with `WinError 1314` because this session lacks symlink privilege. The SCRUM-88 prompt and legacy-seed cases passed.
- Focused local run excluding that OS-dependent symlink case: **8 passed, 1 deselected**.
- `pytest tests/portal/test_research_api.py::test_blind_rating_keeps_machine_fields_and_identity_out_of_the_rater_flow -q`: **1 passed**.
- Ruff on the changed Python files: **passed**.
- `git diff --check`: **passed**.
- Markdown link check: **370 files checked, no broken in-repository links**; 17 links to the sibling runtime repository were reported as external and skipped.

## Follow-up gates

The separate audio-storage choice belongs to SCRUM-87 and was not verified by this task's browser run. SCRUM-89 must complete its two-rater training gate before any main collection or official scoring begins.

## Review disposition

The browser checks support the SCRUM-88 prompt display and rubric-in-form requirements on the local fixture UI. The ViewTransition console message remains visible during teacher navigation. The browser fixture only verifies layout, loaded prompt/audio controls, and field availability; it is not evidence that the research collection or two-rater training gate has been run. No Phase verdict or task acceptance is recorded here.
