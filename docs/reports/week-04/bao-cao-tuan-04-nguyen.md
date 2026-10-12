# Báo cáo W4 — Nguyên

**Tuần được đối chiếu:** 05–11/10/2026. **Ngày hoàn thiện hồ sơ chuyển tiếp:** 12/10/2026 (W05). **Owner:** Nguyên — M01 Intake, M06 Diagnostic Report, M07 Teacher Review. **Base revision:** `3b2d2b78ba5bb35bd162b8f3e5de21ade946d237`; branch local `codex/w4-nguyen-completion`, có working fix M08 và test. **Xác nhận GVHD / nghiệm thu:** `PENDING`.

Nguồn phân công: [plan W4 v2](../../plan/week-04.md), mục 3 và 5. Không backdate hoạt động ngày 12/10 về W4 hoặc quy công implementation W3/PARITY-001 cho Nguyên.

## Task và kết quả có bằng chứng

| Task | Kết quả đã thực hiện | Trạng thái / phần còn cần |
| --- | --- | --- |
| W4-N1 — SQLite report | Đối chiếu repository hiện có; test survive reopen, caller transaction và rollback qua | `TECHNICALLY_VERIFIED`; code có từ W3/PARITY-001, không claim Nguyên triển khai trong W4 |
| W4-N2 — M06/M07 pipeline | Đối chiếu transaction coordinator; phát hiện và sửa binary read Windows của M08 sau khi Nguyên cho phép; regression test chạy red trước fix, green sau fix | `TECHNICALLY_VERIFIED`; cross-owner/formal verdict còn chờ |
| W4-N3 — UI tự làm mới | Kiểm tra meta refresh 5 giây ở QUEUED/RUNNING và không refresh 4 trạng thái cuối | `TECHNICALLY_VERIFIED`; browser current revision NOT_RUN, không lấy browser W3 làm phép chạy mới |
| W4-N4 — Status SDD | Đồng bộ Status, actual code targets, Tasks/Test Plan/Plan notes, Evidence Manifest và Review Records của M01/M06/M07 | `UPDATED`; formal Phase 01/03/04/05/07/08/09 vẫn PENDING |
| W4-N5 — Khảo sát/phỏng vấn TC1 | Hoàn thiện bộ câu hỏi sinh viên, guide giảng viên, consent, quy trình phân tích, data template rỗng và manifest | `PREPARED`; Nguyên xác nhận chưa có phản hồi thật, thu thập NOT_RUN |
| W4-N6 — Hai giám khảo + người phân xử | Hoàn thiện roster giả danh, mẫu lời mời/cam kết, protocol chấm độc lập và phân xử | `PREPARED`; chỉ giả định có ba vị trí, cam kết thực tế NOT_VERIFIED |
| W4-C1 — Báo cáo cá nhân | Tài liệu này sẵn để Nguyên nộp/chỉnh theo mẫu bộ môn | Có file local; chưa nộp projects-fit hay có xác nhận GVHD |
| W4-C2 — AI log | Audit lịch sử W04; prompt/clarification/quyền sửa ngày 12/10 ban đầu ghi W05, được biên tập rồi chuyển vào sheet Nguyên W04 theo yêu cầu trực tiếp; giữ ngày thực tế | Lịch sử 05–11/10 `HISTORICAL_EVIDENCE_MISSING`; W04 có 8 dòng bổ sung ngày 12/10. Ba yêu cầu kiểm tra/tạo PR được ghi W05; xem [record PR](../../evidence/tc2-3-ai-usage/nguyen/pr-W4-20261012.md) về phạm vi workbook đưa vào PR |

## Technical verification trên working source

- Lệnh scoped suite: `.venv/Scripts/python.exe -m pytest -p no:cacheprovider -q -m 'not smoke' tests/api tests/report tests/review tests/local tests/pipeline tests/portal tests/storage`, kèm branch coverage và JUnit như [record M01](../../sdd/modules/m01-intake-student/evidence/M01-W4-20261012.md).
- Kết quả: **127 passed, 3 skipped, 0 failed**; Ruff scoped exit 0; auto-refresh probe exit 0.
- Hai skipped vì Ridge artifact chưa cấu hình; một skipped vì quyền tạo symlink trên Windows. Không có inference model thực, browser current run, WER, CEFR accuracy hoặc metric đồng thuận từ lượt này.
- Coverage statements/branches: M01 **85,53% / 68,75%**, M06 **91,42% / 76,25%**, M07 **84,96% / 62,07%**. Chưa có threshold module đã duyệt; không coi số đo này là verdict chất lượng hoặc validation CEFR.

Suite đầu: 3 failed / 107 passed / 2 skipped. Root cause M08 mở blob ở chế độ text Windows, làm sai byte/checksum. Nguyên cho phép sửa và nhận việc thông báo Thắng. Thay đổi chỉ ở `storage/blob.py` và regression test; giữ giới hạn size/regular-file, checksum và O_NOFOLLOW. Không claim Thắng đã approve hoặc đã nhận thông báo.

Raw commands/results, hashes và working source diff nằm tại [checks.json](../../sdd/modules/m01-intake-student/evidence/w4-2026-10-12/checks.json); [pytest.log](../../sdd/modules/m01-intake-student/evidence/w4-2026-10-12/pytest.log), [coverage](../../sdd/modules/m01-intake-student/evidence/w4-2026-10-12/coverage.json) và [review/fix M07](../../sdd/modules/m07-teacher-review/evidence/M07-W4-20261012.md) là nguồn đo. Không nhân đôi raw report ở hồ sơ rubric.

WORKSPACE FINGERPRINT: 960894780b0898c161a279774c4bf603c4725f1a8ffe16a9a32d781473228dac

Fingerprint và raw technical checks phía trên thuộc snapshot kiểm tra trước các lượt biên tập/chuyển AI log. [Record chuyển sang W04](../../evidence/tc2-3-ai-usage/nguyen/chuyen-log-sang-W04-20261012.md) ghi vị trí log, ngày thực tế và fingerprint sau cập nhật hồ sơ; source kỹ thuật giữ nguyên.

## Hồ sơ để triển khai với người thật

- [W4-N5: khảo sát/phỏng vấn](../../evidence/tc1-problem/W4-N5-khao-sat-phong-van.md), [data template](../../evidence/tc1-problem/W4-N5-data-template.json), [manifest](../../evidence/tc1-problem/W4-N5-evidence-manifest.md).
- [W4-N6: giám khảo và phân xử](../../sdd/modules/m07-teacher-review/evidence/W4-N6-giam-khao-va-phan-xu.md).
- [AI log W04 audit](../../evidence/tc2-3-ai-usage/nguyen/W04-audit.md); [quy tắc workbook theo tuần](../../evidence/tc2-3-ai-usage/README.md).

Khảo sát và cam kết cần phản hồi/xác nhận thực tế mới khép task. Nguyên chỉ dẫn giả định có giám khảo; hồ sơ giữ rõ giả định, không tạo danh tính, chữ ký hoặc ngày đồng ý. Mẫu dữ liệu không được tính là người tham gia; real data/audio/signatures giữ ngoài Git theo manifest và quyền truy cập.

## Next actions để khép phần còn lại

1. Nguyên review hồ sơ và thông báo Thắng về fix M08 đã cho phép; Thắng/Sang review contract liên module. Formal SDD bắt đầu bằng verdict Phase 01 và lựa chọn Research, rồi xử lý các phase sau theo thứ tự.
2. Dùng instrument N5 để thu phản hồi thật; ghi nguồn, ngày, consent, tổng hợp và trace finding → FR/AC → đề xuất/owner verdict.
3. Xác nhận R1/R2/A1 là ba người riêng biệt với năng lực, rubric/version, lịch và nguồn cam kết. Sang/GVHD cùng chốt rubric, dataset và rule phân xử trước khi chấm; agreement hiện NOT_EVALUATED.
4. Phục hồi prompt W04 nếu còn nguồn; không suy ngày/công cụ/prompt từ commit `e2e7fea`. Nộp báo cáo cá nhân qua kênh bộ môn khi Nguyên thực hiện.

Đây là hồ sơ current technical/preparation record. Không có verdict APPROVED/DONE cho module, kết quả khảo sát, cam kết đã ký, remote PR review hoặc xác nhận GVHD được tạo từ lượt này.

## Kiểm tra trước PR — 12/10/2026

Bộ kiểm tra toàn repo (không gồm smoke) đạt **309 passed, 14 skipped, 2 deselected, 0 failed/error**, Ruff toàn `src tests scripts` đạt. Mười ba test bỏ qua do model artifact ngoài Git chưa cấu hình; một test cần quyền tạo symlink Windows. [Checks](../../sdd/modules/m01-intake-student/evidence/pr-2026-10-12/checks.json), [log](../../sdd/modules/m01-intake-student/evidence/pr-2026-10-12/pytest.log), [JUnit](../../sdd/modules/m01-intake-student/evidence/pr-2026-10-12/pytest.xml) và [coverage](../../sdd/modules/m01-intake-student/evidence/pr-2026-10-12/coverage.json) ghi command, revision và SHA-256 source đã kiểm tra.

`main` remote tại lúc kiểm tra là `ee504c9832ffb9989ab7bde35439663c0df32e85`; commit sau base chỉ bổ sung tài liệu W5, không đổi source/test. PR giới hạn task của Nguyên, báo cáo cá nhân và AI log liên quan theo chỉ dẫn mới nhất. Kết quả kỹ thuật không khép N5, N6, lịch sử AI W04 hay formal SDD.
