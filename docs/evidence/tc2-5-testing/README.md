# TC2.5 — Kiểm thử phần mềm

**Nguồn tiêu chí:** rubric PDF tại docs/rubric/.
**Trạng thái:** cập nhật 28/11/2026 trên `main` `2dfa4fc`. Có kế hoạch tổng, test case theo tính năng kèm ca lỗi, mã test chạy trong CI, độ phủ, danh sách defect. Chờ GVHD xác nhận.

## Hồ sơ cần có

Test plan, test case, test code, kết quả chạy, coverage, defect log và trạng thái sửa.

## Minh chứng hiện có

| Mã | Minh chứng | Nội dung |
| --- | --- | --- |
| TS-01 | [Kế hoạch kiểm thử tổng](../../test/TEST_PLAN.md) | Mục tiêu, phạm vi, 7 tầng, môi trường, tiêu chí vào/ra, rủi ro |
| TS-02 | 27 kế hoạch con `docs/test/TEST_PLAN_D*.md` | Test case có mã (ví dụ `TC-SR-I03`), rủi ro được kiểm, tên hàm test; ca lỗi đặt cùng ca đúng |
| TS-03 | Mã test `tests/` (124 tệp, 15 tệp E2E) | 1.901 test: 428 unit, 407 tích hợp có marker, khoảng 1.000 test API qua `TestClient`, 61 E2E Playwright |
| TS-04 | Kết quả CI `main` `2dfa4fc`, 26/11/2026 ([run 45749465088](https://github.com/ThanhSangLouis/ai-assessor-cefr/actions/runs/45749465088)) | 1.802 passed, 49 skipped (E2E, runner không có trình duyệt). Trên MongoDB 7 + Redis 7 thật: 1.814 passed, 37 skipped |
| TS-05 | Độ phủ | **91,07 %** dòng (14.976 dòng, 1.337 chưa phủ); CI chặn dưới 70 %. Tệp `coverage.xml` ở artifact `bao-cao-do-phu` của run trên |
| TS-06 | [Danh sách defect](../../test/DEFECTS.md) | 25 lỗi đã sửa (8 mức Cao, gồm 5 lỗi bảo mật SEC-01..05), 2 lỗi mở, 2 giới hạn đã biết; mỗi dòng có commit hoặc PR |
| TS-07 | Test cho bản lưu API và đo uptime | `tests/test_openapi_export.py`, `tests/test_uptime_report.py` (28/11) |

## Còn thiếu / giới hạn

- Chưa có WER chuẩn hay kiểm định CEFR trên người học Việt Nam. Độ chính xác mô hình báo ở chương thực nghiệm, không phải ở đây.
- E2E chạy trên máy, chưa chạy trên CI (runner không cài Chromium).

## Lịch sử (W3, 10/2026)

| Evidence | Phạm vi | Trạng thái |
| --- | --- | --- |
| [W3 Test Plan](../../sdd/features/w3-local-integration/04-test-plan.md) | W3-TEST-001–008 map W3-AC-001–005 | Tests phải đối chiếu final source |
| [W3 Review](../../sdd/features/w3-local-integration/reviews/review-01.md) | Defect findings/corrections và test quality | Codex actual diff review |
| [W3 Evidence Manifest](../../sdd/features/w3-local-integration/evidence/evidence-manifest.md) | Regression/coverage/browser/persistence output | Số liệu dùng đúng revision trong từng report |
| [Real ASR/VAD smoke](../../sdd/features/w3-local-integration/evidence/real-speech-smoke.md) | Hai audio local, actual engine/features | WAV PASS; MP3 codec warnings được ghi; WER/accuracy NOT_MEASURED |
