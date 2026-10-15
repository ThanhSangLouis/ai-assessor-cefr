# SCRUM-66 — Review và verification độc lập

W5 target `3b2d2b7`, Sang `40907cc`. Implementation base `b2b573f`; product revision đã kiểm: `311b02952e61ff0889ed82fc1b695a8ea79411ad`. PR #36 đã merge, main base `840efb9` có cùng tree với implementation base. Không cập nhật bản Sang.

## Kết quả kỹ thuật

**READY FOR REVIEW** cho backend SCRUM-66. Luna triển khai theo ba vùng sở hữu; Codex review diff, yêu cầu sửa và tự chạy verification. Không còn finding BLOCKER/MAJOR đã biết trong phạm vi backend sau các lần sửa bên dưới. Chưa thay thế review user flow của Nguyên hoặc review privacy của Sang; không tự nghiệm thu module M11/Jira DONE.

| Work package | Kết quả và evidence |
| --- | --- |
| T02.1 | Profile allowlist 15 icon/10 màu, goal chính xác, không field PII; account/session/consent v4→v9 và reopen bảo toàn. [Compatibility](identity-compatibility-report.md). |
| T02.2 | Policy password, temp gate/expiry, lockout, rotation/revoke và CAS; regression concurrency. [Accounts](accounts-report.md). |
| T02.3 | Session ID opaque, current/coarse device, expiry/ownership; activity/audit lọc credential; UPDATE-only touch chống resurrect. |
| T02.4 | Single/batch ≤200 atomic, failure injection rollback toàn bộ; reset/role/disable/revoke/unlink và self-guard; legacy routes chung policy. |
| T02.5 | PKCE/state/nonce/HMAC, RSA RS256/JWKS và validated claims, replay CAS, link/login/unlink; real HTTP adapter tests offline. [Google](google-report.md). |
| T02.6 | Versioned event/effective consent; withdraw/opt-out void assignments, withdraw enrollment và loại research export; history bất biến vẫn giữ. |
| T02.7 | [API contract + status/authorization](api-contract.md), [UI handoff](ui-handoff.md), [browser](wheel-browser.json). |

Full non-smoke: **PASS — 425 passed, 0 failed, 0 skipped, 2 deselected**, 78.37 s. Baseline: 358 passed; thêm 67 test. [Log](final-pytest.log), [JUnit](final-pytest.xml), [coverage](coverage-summary.json).

| Service | Line | Branch |
| --- | ---: | ---: |
| AuthService (`auth/service.py`) | 94.12% | 90.00% |
| AccountService | 97.24% | 91.67% |
| GoogleIdentityService | 92.87% | 86.23% |
| Google HTTPS transport | 98.28% | 94.44% |

Các pure service đạt target line ≥90% / branch ≥85%. Global coverage: line 89.01%, branch 75.03%, combined 85.83%; baseline line 89.47%, branch 74.28%, combined 86.15%. Mức combined giảm 0.32 điểm phần trăm khi thêm HTTP/repository branches; không giấu bằng exclude hoặc claim giữ nguyên coverage. Critical security branches có direct tests. API adapter line 73.75% / branch 66.00%; repository identity 87.26% / 71.01%.

Lint toàn `src tests scripts`: **PASS**. Format 28 Python file thay đổi: **PASS**. Global formatter: **FAIL** trên 22 file legacy ngoài diff (baseline T01 đã ghi 23); không claim global format PASS. Markdown links, forbidden-file scan và diff whitespace: **PASS**. [Static](static.json), [global format](global-format.log).

Wheel build: **PASS**. Wheel chứa đúng toàn bộ Python source của revision đã review, không mismatch. Venv sạch cài core offline không có cryptography vẫn boot và dùng account được; optional `[google]` cài offline cryptography 50.0.2 thành công. Browser Chromium dùng server từ wheel, không editable/source import: admin login → create temp account → forced-change page HTTP 200 và đủ field → password rotation → account access; cross-origin cookie mutation bị chặn. Log không chứa sentinel OAuth code/state. [Wheel/browser](wheel-browser.json), [server log](wheel-server.log). Lượt cuối không có HTTP 500.

## Finding đã sửa

| ID | Mức | Vấn đề → cách kiểm lại |
| --- | --- | --- |
| F01 | MAJOR | Legacy admin create bỏ qua temp policy → cùng AccountService; consumer regression. |
| F02 | MAJOR | Foreign resource bị map 401 do exception inheritance → giữ 404, lockout 429/temp 403. |
| F03 | MAJOR | Password/admin reset dùng authorization trước hashing → recheck credential/live session trong transaction; injected revoke/reset race. |
| F04 | BLOCKER | Touch UPSERT có thể tạo lại session vừa revoke → UPDATE-only, race qua SQLite connection thứ hai. |
| F05 | MAJOR | Password-change page thiếu renderer gây 500 trong wheel → form có UTF-8 body; assert HTTP 200/required inputs rồi rebuild/retest. |
| F06 | MAJOR | Erasure lỗi FK với identity/immutable consent → xóa mutable data, scrub credential/disable stub khi còn FK, withdraw participation; regression và preview trung thực. |
| F07 | MAJOR | Profile cho identifier tùy ý/HTTPS cookie tên thường/query access log → fixed catalog, __Host cookie, safe method/status/size log và redaction tests. |

## Giới hạn và handoff

Google production OAuth/live JWKS và credential thực: **NOT_RUN**, ngoài scope production setup. Các token ở tests là synthetic và được ký RSA offline. N01/N04 bốn tab account/admin UI, responsive/keyboard và nghiệm thu Nguyên/Sang: **PENDING**, nhận API/handoff ổn định từ T02. Không claim hoàn tất M11-TEST-009 thuộc UI lane. Không deploy/merge hoặc sửa Jira DONE.

Schema vẫn v9; không đổi SQL/checksum T01, không thêm DB thứ hai/global mutable singleton hoặc D043 dependency. Optional crypto là dependency mới duy nhất. Database/blob demo gốc không bị thay đổi; backup/restore T01 vẫn giữ ngoài Git. Các log và wheel được hash trong [manifest](manifest.json).
