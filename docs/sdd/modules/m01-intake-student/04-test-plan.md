# M01 — 04 Test Plan (Kế hoạch kiểm thử)

> **BẢN NHÁP W2 (v0.1, 25/09/2026).** Chuẩn bị theo yêu cầu chủ dự án; Phase 01 của M01 vẫn `DRAFT/PENDING`. Nội dung dưới đây chưa là Specification/Plan được duyệt và không cấp quyền phát prompt triển khai.

Test ở đây là **ca dự kiến**, chưa được chạy. Fixture tạo bởi nhóm chỉ kiểm tra logic; không thay âm thanh người dùng hoặc dữ liệu kiểm định CEFR.

| Test ID | FR/AC | Level | Tình huống | Kỳ vọng |
| --- | --- | --- | --- | --- |
| M01-TEST-001 | M01-FR-001 / M01-AC-001 | API integration | Student có consent nộp file hợp lệ | Tạo một Response `QUEUED` với owner từ session |
| M01-TEST-002 | M01-FR-001 / M01-AC-001 | API integration | Thiếu consent hoặc role khác student | Không có Response/blob mới; trả lỗi quyền |
| M01-TEST-003 | M01-FR-002 / M01-AC-002 | API integration | Owner A truy cập response của B | Không lộ status/report của B |
| M01-TEST-004 | M01-FR-002 / M01-AC-002 | Unit + API | Pipeline chuyển sang `REVIEW_REQUIRED` rồi `FAILED` | UI/API giữ đúng trạng thái và không gắn score khi thiếu evidence |
| M01-TEST-005 | M01-FR-001 / M01-AC-001 | Boundary | File rỗng/sai định dạng/quá giới hạn cấu hình | Từ chối trước tạo Response; reason rõ |

## Chính sách chạy và bằng chứng

- Tạo test cùng task triển khai; ưu tiên unit test cho logic thuần, integration test cho boundary I/O, và kiểm tra UI/API khi hành vi nhìn thấy được.
- Khi soạn plan ngày 25/09, test chưa chạy. Ngày 28/09, chỉ dẫn trực tiếp của chủ dự án tạo direct workspace evidence với test/path thực trong `evidence/M01-EVID-DIRECT-20260928.md`; đây là technical evidence, không phải Phase 04/08 verification hay user verdict.
- Coverage là chỉ báo để tìm nhánh quan trọng chưa được kiểm thử. Chính sách threshold/no-regression chỉ được chốt ở Phase 04/05 sau khi có stack và baseline đo được.
- Bằng chứng Phase 06/08: command, thời điểm, exit code, số test, phần skipped/fail, coverage report nếu áp dụng, revision/fingerprint, file trong `evidence/`. Browser QA nếu có phải ghi môi trường và ảnh/trạng thái thực.
- Test với audio có quyền sử dụng là smoke/integration riêng; không đưa audio, transcript chứa PII hoặc secret vào Git/log. Chưa có data/consent/approval thì đánh dấu `NOT_RUN` thay vì tạo kết quả thay thế.

**CODEX CHECK RESULT:** DRAFT — mỗi AC có ca kiểm tra; lệnh và coverage policy còn chờ stack. **User verdict Phase 04:** PENDING.


## Actual verification — W4-N4, 12/10/2026

Các Test ID ở bảng giữ nguyên là thiết kế DRAFT. [M01-W4-20261012](evidence/M01-W4-20261012.md) đối chiếu từng Test/FR/AC với implementation và test actual; suite liên quan 127 passed / 3 skipped / 0 failed. Đây là technical verification sau direct instruction; Phase 04/08 và user acceptance vẫn PENDING. Coverage thực đo nằm trong evidence; không tự đặt threshold hoặc biến fixture thành metric CEFR.
