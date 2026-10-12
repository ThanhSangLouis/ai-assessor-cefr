# M06 — 04 Test Plan (Kế hoạch kiểm thử)

> **BẢN NHÁP W2 (v0.1, 25/09/2026).** Chuẩn bị theo yêu cầu chủ dự án; Phase 01 của M06 vẫn `DRAFT/PENDING`. Nội dung dưới đây chưa là Specification/Plan được duyệt và không cấp quyền phát prompt triển khai.

Test ở đây là **ca dự kiến**, chưa được chạy. Fixture tạo bởi nhóm chỉ kiểm tra logic; không thay âm thanh người dùng hoặc dữ liệu kiểm định CEFR.

| Test ID | FR/AC | Level | Tình huống | Kỳ vọng |
| --- | --- | --- | --- | --- |
| M06-TEST-001 | M06-FR-001 / M06-AC-001 | Unit | Không có evidence hợp lệ | Không sinh comment khẳng định; hiện missing reason |
| M06-TEST-002 | M06-FR-001 / M06-AC-002 | Unit | Pause/word ref hợp lệ từ cùng response | Link mốc và source version đúng |
| M06-TEST-003 | M06-FR-001 / M06-AC-001 | Boundary | Ref khác response/ngoài duration/stale version | Bỏ comment và ghi reason, không bịa ref |
| M06-TEST-004 | M06-FR-002 / M06-AC-002 | Unit + API | Assessment NOT_EVALUATED, không review action | Không có band; teacher_verified false |
| M06-TEST-005 | M06-FR-002 / M06-AC-002 | Integration W3 | M07 ghi review action hợp lệ | Report hiển thị AI result và teacher final/audit ref tách biệt |
| M06-TEST-006 | M06-FR-002 / M06-AC-003 | Unit + API | M05 trả một overall estimate và coverage đủ năm tiêu chí | Report có một overall score/band, năm coverage, Interaction null/reason; không có năm score lặp |

## Chính sách chạy và bằng chứng

- Tạo test cùng task triển khai; ưu tiên unit test cho logic thuần, integration test cho boundary I/O, và kiểm tra UI/API khi hành vi nhìn thấy được.
- Khi soạn plan ngày 25/09, test chưa chạy. Ngày 28/09, chỉ dẫn trực tiếp của chủ dự án tạo direct workspace evidence với test/path thực trong `evidence/M06-EVID-DIRECT-20260928.md`; đây là technical evidence, không phải Phase 04/08 verification hay user verdict.
- Coverage là chỉ báo để tìm nhánh quan trọng chưa được kiểm thử. Chính sách threshold/no-regression chỉ được chốt ở Phase 04/05 sau khi có stack và baseline đo được.
- Bằng chứng Phase 06/08: command, thời điểm, exit code, số test, phần skipped/fail, coverage report nếu áp dụng, revision/fingerprint, file trong `evidence/`. Browser QA nếu có phải ghi môi trường và ảnh/trạng thái thực.
- Test với audio có quyền sử dụng là smoke/integration riêng; không đưa audio, transcript chứa PII hoặc secret vào Git/log. Chưa có data/consent/approval thì đánh dấu `NOT_RUN` thay vì tạo kết quả thay thế.

**CODEX CHECK RESULT:** DRAFT — mỗi AC có ca kiểm tra; lệnh và coverage policy còn chờ stack. **User verdict Phase 04:** PENDING.


## Actual verification — W4-N4, 12/10/2026

Các Test ID ở bảng giữ nguyên là thiết kế DRAFT. [M06-W4-20261012](evidence/M06-W4-20261012.md) đối chiếu từng Test/FR/AC với implementation và test actual; suite liên quan 127 passed / 3 skipped / 0 failed. Đây là technical verification sau direct instruction; Phase 04/08 và user acceptance vẫn PENDING. Coverage thực đo nằm trong evidence; không tự đặt threshold hoặc biến fixture thành metric CEFR.
