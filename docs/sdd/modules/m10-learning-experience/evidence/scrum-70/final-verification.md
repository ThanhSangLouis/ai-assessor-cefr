# SCRUM-70 — Final verification

Baseline lịch sử: `3b2d2b78ba5bb35bd162b8f3e5de21ade946d237`.
Tham chiếu chức năng: `40907cc35b3d04408f9a8713f16d9be99f4cd6c7`.
Actual parent: `a4c119fdbcf5e17a09372099cb1dc07de853b698` (tree giống51eff1f).
Final source/test commit: `e792ae6`.

## Kết quả đo

| Check | Kết quả thực tế |
| --- | --- |
| Full pytest không smoke, branch coverage | **PASS — 889 passed, 0 failed, 2 smoke deselected; 252,84s** |
| Pure learning coverage | **PASS — statement1352/1407=96,091%; branch437/492=88,821%**, ngưỡng90%/85% |
| Toàn dự án | Statement12352/13801=89,501%; branch3685/4732=77,874%; 129excluded lines |
| Learning repository | Statement939/1181=79,509%; branch295/500=59,000% |
| Learning API | Statement434/564=76,950%; branch169/242=69,835% |
| Ruff toàn src/tests/scripts/tools | PASS |
| Format check trên51file Python thay đổi | PASS; không format sweep legacy |
| Diff whitespace, old migrations005–010 | PASS; migration cũ không đổi |
| Forbidden files | PASS; không audio/model/DB/secret vào Git |
| Changed text secret scan | PASS trên5nhóm pattern key/token; không thay kiểm soát permission |
| Seed oracle độc lập | PASS18unit/31lesson/15practice/16authored, thứ tự đúng, mọi published version đọc được, FK sạch, rerun0DBwrite |
| Fresh offline wheel install/boot | PASS; import từ site-packages, migration011 có mặt,129/129Python/SQL/JS byte-identical |
| Browser desktop/mobile API handoff | **PASS107/107**, console/page/request/external errors0 |

Coverage pure gồm domain/contracts/bank/rules/recommend, lesson model/align/text/checks/lint/progress/review/authoring. Không gộp service/runner/seed/repository/API vào ngưỡng pure; các lớp đó có evidence integration/transaction/permission riêng. Toàn dự án giảm so baseline S01 (statement90,824%, branch80,189%) do bổ sung runtime/API/repository; không áp nhầm ngưỡng pure cho toàn repo. So S01 có thêm2excluded dòng: invariant fail-fast kiểm catalogue cố định15missions ở cuối bank (`pragma: no cover`); được công bố rõ, không loại service/repository khỏi toàn dự án. Nhánh chưa phủ chủ yếu nằm ở defensive validation, legacy/authoring permutations và service failure/replay branches; không claim100% coverage hay miễn reviewer review.

## Lệnh và evidence

Chạy trong worktree scrum-70, shared venv ở repo chính:

```sh
PYTHONPATH=src AICEFR_MODEL_DIR=/home/thanglvc/Documents/HCMUTE/TLCN/ai-assessor-cefr-runtime/models \
COVERAGE_FILE=/tmp/.coverage-root70-final \
/home/thanglvc/Documents/HCMUTE/TLCN/ai-assessor-cefr/.venv/bin/pytest \
-q -m 'not smoke' --cov=aicefr --cov-branch \
--cov-report=json:/home/thanglvc/Documents/HCMUTE/TLCN/ai-assessor-cefr-runtime/evidence/scrum-70-2026-10-15/final-coverage.json \
--cov-report=term
```

Raw evidence ngoài Git tại `/home/thanglvc/Documents/HCMUTE/TLCN/ai-assessor-cefr-runtime/evidence/scrum-70-2026-10-15/`:

- `final-tests.log`, `final-coverage.json`, `coverage-summary.json`, `source-manifest.json`, `secret-scan.json`.
- `root-seed-oracle-final.json`: seed SHA256 `1257f9140768dd86db31026e4205b7ac5b707918f9aace4ab0a4d3109d79782a`. Hash trước khi bổ sung typed revision không phải hash final.
- `wheel-qa/clean-final/`: wheel, build/install/import logs, `result.json`, `browser_qa.py`, screenshot và QA report. Agent ban đầu lưu dưới runtime/runtime/evidence; Codex đã copy nguyên hồ sơ vào đường dẫn chuẩn này và kiểm lại SHA/byte parity/result.
- Wheel SHA256 `2de8c61d994fffe4bad5f502025fe06d7507b070f34f3e706502e5e67145fee0`.
- `real-practice/result.json`: preflight model Whisper/VAD thật,36,05s,82words,25,8speaking seconds; rule outcomeFAIL là kết quả feedback, pipelinePASS. Scorer/calibration thiếu có chủ đích; assessment/report/queue/job counts0, retry giống hệt. Đây là preflight trước correction API, không thay final wheel/browser/full checks. Audio có quyền từ hồ sơ W3, giữ ngoài Git.
- `full-tests.log`: lần đầu883PASS/3FAIL do fixture cũ; đã sửa, targeted27PASS và full final889PASS. Lỗi harness ban đầu giữ riêng trong wheel logs; không dùng làm kết quả final.

Codex đã tự chạy full tests, seed oracle, Ruff/format/diff/forbidden/secret, kiểm source manifest/wheel bytes và boot bằng installed Python `-I` ngoài checkout. Browser evidence được kiểm nội dung JSON và screenshot mobile; ASR/VAD browser dùng fixture, không claim speech accuracy.

## Đối chiếu work packages

| Package | Evidence |
| --- | --- |
| S02.1 catalogue15missions/7kinds | practice domain tests; bank/contracts/rules; seed manifest |
| S02.2 purpose riêng, không scorer/band/queue | runtime/API tests; real-practice preflight; browser DB counts |
| S02.3 recommendation/fallback | deterministic domain tests; API handoff |
| S02.4 lesson9kinds/4stages/alignment/lemma/QC | lessons domain tests + pure coverage; runner VAD/LID tests |
| S02.5 authoring/media/lint/publish/import-export | authoring codec and HTTP journey/security tests; immutable old version, CAS/rollback |
| S02.6 seed18/31 và bảo vệ teacher data | repository real SQLite tests, version/hash/idempotency/move checks; root oracle |
| S02.7 review1/3/7/override/audit/delete | review domain, two-connection CAS tests, owner erase/export/retention/restore tests; positive browser review/replay |

Browser thực hiện mỗi viewport: teacher tạo/publish path-unit-lesson đủ4stage; student hoàn thành6step và2FREEround; FAILretry không thu hồi hoặc tăng progress; reviewPASS qua actual runner, same-key replay trả original, box1→2/revision0→1 đúng một lần. HTTP auth401/CSRF403/role403/foreign404/stale409 có URL/result đối chiếu. Không tạo assessment/report/research rows. Practice result không có CEFR score/band; target_band của nội dung là mức bài học, không phải điểm người học.

## Handoff và verdict

[API inventory](integration-handoff.md), [domain contract](domain-contract-handoff.md), [storage report](storage-report.md), [review record](../../reviews/SCRUM-70-review.md).

Task kỹ thuật sẵn sàng review/PR. UI N02/N03, achievement/streak/pronunciation S03 không nằm trong PR này. Reviewer Thắng/Nguyên, user acceptance và JiraDONE: **PENDING**. Không tự merge hoặc đổi status. Sau khi tạo PR, dừng theo yêu cầu mới nhất của user.

Final documentation guards:315Markdown files checked,0broken internal links;17historical outside-repo links skipped explicitly. Forbidden scan712tracked/stagedfilesPASS; staged diff whitespacePASS. AI log trong repo chính, sheet Sang tới dòng27; các sheet khác và công thức được giữ nguyên khi ghi/đọc lại workbook.
