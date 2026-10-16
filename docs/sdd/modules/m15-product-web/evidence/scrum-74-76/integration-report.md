# M15 integrated browser evidence — SCRUM-74–76

**Run date:** 2026-10-16
**Revision:** `0827b37b4f560d5087e1c57e9011ed79acc837dc`
**Branch:** `feat/SCRUM-76-W5-N04-Admin-UI-full-browser-regression-va-UI-handoff`
**Readiness:** `READY_FOR_REVIEW`; Phase 09 owner acceptance `PENDING`.

## Environment and fixture boundary

The browser run used Headless Chromium 155 against `http://127.0.0.1:18765` with local synthetic accounts only: student, teacher and admin. The student had base consent active; optional research consent remained unchecked. Data lived in a temporary SQLite database under `D:\CodexTemp`. No passwords, cookies, tokens, audio or personal data are included in this record.

## Route and responsive results

Each listed page was loaded with its corresponding role at 360, 390, 768 and 1280 CSS pixels. Every listed route returned HTTP 200 and `document.documentElement.scrollWidth` equaled the viewport width. The student-only direct request to `/admin` returned the expected 403; anonymous `/admin` returned 401 during pre-auth setup.

| Role | Routes | HTTP | Widths | Horizontal overflow |
| --- | --- | --- | --- | --- |
| Anonymous | `/`, `/bands`, `/login` | 200 | 360 / 390 / 768 / 1280 | None |
| Student | `/my-progress`, `/student/tasks`, `/practice?path=<fixture>`, `/practice/lessons/<fixture>` | 200 | 360 / 390 / 768 / 1280 | None |
| Teacher | `/teacher/reviews`, `/rate`, `/teacher/stats`, `/teach/insights`, `/teach` (known path opened by ID) | 200 | 360 / 390 / 768 / 1280 | None |
| Admin | `/admin`, `/admin/accounts`, `/admin/erase`, `/admin/maintenance`, `/admin/models`, `/admin/config`, `/admin/audit`, `/admin/health`, `/admin/ratings`, `/admin/studies` | 200 | 360 / 390 / 768 / 1280 | None |

The `/admin/studies` run exposed an inline-form overflow at 390px. The form now wraps its label, input and button on narrow screens; the retest measured 390/390 with no overflow. Admin `console error` was 0 after the fix. Clean public, supported student, teacher and admin sessions had zero console errors. The expected student 403 produced one browser resource error, which is the server authorization result.

## Supported API and interaction evidence

- Student task/progress/reliable-change/learning progress/achievement/pronunciation endpoints returned 200. Practice path, lesson, progress and attempt-list endpoints returned 200. No attempt or assessment was submitted.
- Teacher review queue and blind assignment list returned 200 with empty fixture queues. The known teacher path and per-owner insights returned 200. The path screen reports read-only/unknown publish state because the current M10 response does not expose it; insights do not invent cohort aggregation.
- Admin rating setup/batches and billing overview/order reads returned 200. No eligible assessment response existed, so no rating batch was created. One synthetic M13 study draft was created with HTTP 201 and reopened; report returned 200, participant count was 0, and it was left unstarted.
- Observed app requests stayed on loopback. No external service was called.

## Duplicate-mutation guard follow-up

After static review, the committed `admin_study.js` and `admin_ratings.js` were loaded into an isolated local Chromium harness with delayed mock API responses. Double-clicking study creation, study start, and rating-batch close each produced exactly one mock POST. The harness reported zero console errors. This verifies the client-side duplicate-submit guard only; it does not exercise backend mutation/error cases, so `M15-TEST-007` remains `PARTIAL`.

## Explicitly not run

No audio was uploaded or submitted, so the run does not claim recorder permission, upload validation, preview/re-record/double-submit, scoring, report-state, or CEFR-result coverage. It also does not claim reviewer contention/blind submit/authoring conflict coverage, sensitive admin mutations, keyboard/focus, 200% zoom, reduced-motion, print, screen-reader tree, complete forbidden-field scans, or the clean-wheel gate. M15-TEST-001–012 coverage is itemized in `integration-report.json`; these cases are not marked as passed. The fixture contains no assessment score, and no score was fabricated.

## Screenshot manifest

| File | SHA-256 | Bytes |
| --- | --- | ---: |
| `admin-dashboard-desktop.png` | `f9e4290f2e57669b5563103b487d0b71b802033aaf55d949df41d93f2058785d` | 155359 |
| `admin-dashboard-mobile.png` | `69b2c894fea369d12df776df739b8d4b056ece7c788ed592bd6012801c48716f` | 78541 |
| `admin-ratings-desktop.png` | `3d435a6356159fea71b80ea8ca829a774aadfe73f0e4cff615ffb76dfcc60361` | 158850 |
| `admin-ratings-mobile.png` | `4ee2e347f9cc2300c68a4c7a091527d3bacc31e92044ef5d8b7b7ab285aaf6bd` | 94010 |
| `admin-studies-draft-desktop.png` | `3e1050e7ad0f1ca20a808e9c75fc7163dda6a7bccb67f766ae737c2ae19f2652` | 144766 |
| `admin-studies-draft-mobile.png` | `e009167f6698b0aea8328fdda79741241a003f8a99ff1bb5d6c01620e4fd23b1` | 58804 |
| `public-bands-desktop.png` | `601c6653ffcffb9a7cbfb5d91f97acfac0fd1d23f1e928dfc419ab0f4edb13d4` | 203576 |
| `public-bands-mobile.png` | `826eaf95bcd89a9a25f47a8ae2c2ce4e2f13b8baa084598ae426da76288a4f7d` | 142583 |
| `public-home-desktop.png` | `0c523a1f8d525e5eb5c81694c82f0f2e9c5c8aa933d88009d73695be37b4bcbb` | 371731 |
| `public-home-mobile.png` | `8342124cf42a988cd4010efee81f39f49e99196e6ae3d0a222c5517d3ed89645` | 187624 |
| `student-admin-denied-mobile.png` | `0b6a43c4d6452d25233107600ea559b1293a9e6546d83406a6a6cc44c3970a3e` | 155223 |
| `student-lesson-desktop.png` | `a98944e1ad369ae5943e65a84109da4bf48e7721f462c2157bb257c7c4462a57` | 177089 |
| `student-lesson-mobile.png` | `2bda9c002b67937f352170e5e3c5faef5d5496200969fe0e8e45d721d742b0cc` | 92533 |
| `student-practice-path-desktop.png` | `923ef11a055b1313fa26d1502ae6196a4c6b01b1f599a96571db72ebc59c6a4c` | 177722 |
| `student-practice-path-mobile.png` | `055209c5355670a78935afdf7f084169bcb78c878b1ee8a7ccfa1996df13ee39` | 87318 |
| `student-progress-desktop.png` | `d9a643186f12c59db9c09412b8660728efac10fa38d271a7132e4294eb5e6327` | 191371 |
| `student-progress-mobile.png` | `c5f4bd95ae9f1eac6cb38b2af7ce82b443f24e0e34fdb970234b24eccd15f0c1` | 95315 |
| `teacher-blind-rating-desktop.png` | `554cc9ac199bcf850f22cbe712328d1201de0e8596f774dd29d9d11e9400fa62` | 183247 |
| `teacher-blind-rating-mobile.png` | `f4a0edbe1efc7e26fb0adbb3d6b2f3f98d878923bc15ee117ad0bef2e75e4a37` | 118743 |
| `teacher-insights-desktop.png` | `5ab61f7f6bbaec654498803647a11e9014de32287dee419e44d5a91a71aff2a7` | 177367 |
| `teacher-insights-mobile.png` | `40795a5c9689d4c7f5f091ecfe463f6c667273e1b64c44f2d0965a3d8e14d26a` | 92950 |
| `teacher-lesson-editor-desktop.png` | `30725afdc92064e4eee0d93f6e9c9180da704697b447277697ee8080f04228b8` | 194495 |
| `teacher-lesson-editor-mobile.png` | `e370a8141becb8e9c832d22981ce35e475d6d7fc6c4ccb1f36f9b0dcb617e1f4` | 81111 |
| `teacher-path-published-desktop.png` | `d83529b61ba805d083347c495bc6556143216327dc2bd6eb953ec088e5ce82b2` | 177841 |
| `teacher-path-published-mobile.png` | `3e83056f571f3ce95d5d1dba57d6fb80a1172ec31391aef5690267f809c70206` | 100596 |
| `teacher-reviews-desktop.png` | `6a2c888764ae18aaf1d4278f225be11d338156bee6bbd4ae6d910a7e16110925` | 180981 |
| `teacher-reviews-mobile.png` | `09c8612c6d94776e521cc68203f0d360f3631ff4a98f909fe3d9a00c153897d3` | 110585 |

The two `teacher-lesson-editor-*.png` images are supplemental screenshots from the preceding integrated preflight; the route/viewport outcomes above come from the revision-specific final sessions.
