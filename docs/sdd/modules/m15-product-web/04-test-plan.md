# M15 — Test Plan

**Version:** v0.1 · **STATUS:** DRAFT.
UI logic/component contract tests required; browser E2E is required alternative for presentation behavior.

| Test ID | AC | Scenario | Expected | Level |
| --- | --- | --- | --- | --- |
| M15-TEST-001 | 001 | component states/theme/contrast/focus/labels | token/state/a11y pass | Component/browser |
| M15-TEST-002 | 002 | anonymous/student/teacher/admin nav + direct URL | correct nav and 401/403/404 | API/browser |
| M15-TEST-003 | 003 | upload/record/playback/rerecord/prep/submit errors | deterministic usable recorder | Browser |
| M15-TEST-004 | 004/005 | report all dispositions/null/old report | correct wording/recovery/no false zero | Template/browser |
| M15-TEST-005 | 004/005 | learning lesson/review/no-band/achievement/pronunciation | full mobile/desktop states | Browser |
| M15-TEST-006 | 004/006 | teacher review conflict/blind/authoring/override | recovery and no leak | Browser/security |
| M15-TEST-007 | 004/005 | admin account/config/data/rating/study/billing | all states/confirm/permissions | Browser |
| M15-TEST-008 | 001/004 | 360/390/768/1280 widths, zoom 200%, long text | no overflow/trap/covered action | Browser |
| M15-TEST-009 | 001/008 | reduced motion/print/art/screen reader tree | decorative only | Browser |
| M15-TEST-010 | 007 | build wheel/install/offline asset request | all local assets and licenses present | Packaging |
| M15-TEST-011 | 008 | QA result schema/screenshot hash/console/network | traceable evidence | Tooling |
| M15-TEST-012 | Claims | forbidden phrases/criterion score/secret/path | none in template/DOM | Static/browser |
