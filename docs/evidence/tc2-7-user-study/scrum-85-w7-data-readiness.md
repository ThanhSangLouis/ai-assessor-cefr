# SCRUM-85 — Checklist vận hành cho buổi thu thử W7

**Evidence ID:** `SCRUM-85-W7-DATA-READINESS`  
**Ngày kiểm tra:** 25/10/2026 · **Owner:** Thắng
**Integrated baseline:** `main` `f540cb88643214cd1d4444f2dd0d81f4463119fa`
**Task acceptance:** `OWNER ACCEPTED DONE` (25/10/2026) · **Data availability:** `OWNER CONFIRMED` · **Collection/inspection in this verification:** `NOT_RUN`

## Kết quả rà soát

Checklist dưới đây được đối chiếu với code hiện hành và chạy bằng tài khoản fixture trên server loopback. Chủ dự án xác nhận dữ liệu thu thử đã có và chấp nhận SCRUM-85 hoàn tất. Lượt kiểm chứng này không truy cập, kiểm kê hay sao chép dataset; xác nhận owner không phải phép kiểm tra nội dung, provenance, consent hoặc retention.

| Hạng mục | Kết quả kiểm chứng | Bằng chứng |
| --- | --- | --- |
| Consent hiện hành | Trang sinh viên hiển thị `consent-v2` và link PDF cùng version. Checkbox lưu audio hoạt động độc lập với checkbox research; fixture lưu audio `true`, research `false`. | [Consent screenshot](../../../output/playwright/SCRUM-85-consent.png) |
| Batch account/temp password | M11 API và luồng temporary-password được kiểm qua identity tests. Admin UI hiện chỉ tạo từng account và nhập password thủ công; không có màn hình batch hoặc receipt mật khẩu tạm. | [Identity/consent test log](evidence/scrum-85/identity-consent-tests.log), [admin accounts screenshot](../../../output/playwright/SCRUM-85-admin-accounts.png) |
| Xóa dữ liệu | Admin UI chạy erasure preview cho fixture: 0 bài, 0 bytes audio; không xác nhận xóa trong lượt browser này. Erasure apply được bao phủ bởi fixture tests của data-operations. | [Erasure preview screenshot](../../../output/playwright/SCRUM-85-erasure-preview.png), [scoped tests](https://github.com/thanglb2005/ai-assessor-cefr/blob/7febd5bb099c12d0c3c62862e2ef61f37cb25f56/docs/evidence/scrum-83/selected-tests.log) |
| Retention/orphan | Admin UI hiện preview retention 180 ngày và orphan; fixture trả 0 bài, 0 blob. Không chạy apply trên dữ liệu pilot. | [Maintenance screenshot](../../../output/playwright/SCRUM-85-maintenance.png) |
| Backup/restore | Clean-wheel smoke đã backup database, restore sang thư mục mới và đọc lại report fixture thành công. UI nói rõ backup thao tác qua CLI `maintenance backup`, không có nút backup/restore. | [Clean-wheel result](https://github.com/thanglb2005/ai-assessor-cefr/blob/7febd5bb099c12d0c3c62862e2ef61f37cb25f56/docs/evidence/scrum-83/clean-wheel-smoke.log), [report JSON](https://github.com/thanglb2005/ai-assessor-cefr/blob/7febd5bb099c12d0c3c62862e2ef61f37cb25f56/docs/evidence/scrum-83/w5-foundation-smoke.json) |
| Browser | Login, consent, admin accounts, erasure preview và maintenance render/operate được. Chromium ghi `Transition was aborted because of invalid state. ViewTransition opt-in disabled` lúc điều hướng; trang vẫn render. Có thêm verbose notice thiếu `autocomplete` trên password field. | [Admin data screenshot](../../../output/playwright/SCRUM-85-admin-data-before.png), [browser console log](evidence/scrum-85/browser-console.log) |

Các ảnh được chụp từ UI local với fixture tổng hợp; không chứa dữ liệu người học thật. Python browser runner riêng không chạy vì máy chưa cài Chromium headless-shell cho Python Playwright; các hành trình UI ở trên đã được thao tác bằng Playwright CLI trên Chromium thật.

## Checklist trước buổi thu

1. Dùng revision triển khai đã chốt; xác nhận `/student/consent` và PDF cùng là `consent-v2` trước khi tạo tài khoản.
2. Tạo tài khoản sinh viên qua M11 batch API `/api/v1/admin/accounts`; kiểm tra temporary-password gate. Admin UI chỉ hỗ trợ tạo từng tài khoản. Không đưa password tạm vào Git, workbook, ảnh chụp hoặc log; chuyển cho người nhận qua kênh riêng đã thống nhất.
3. Mỗi người tham gia tự xem nội dung consent và chọn riêng lưu audio; research opt-in mặc định không bật. Ghi lại đúng `consent_version` và hai giá trị lựa chọn trong manifest giả danh.
4. Trước khi ghi dữ liệu thật, GVHD/chủ dự án cần chốt retention và cách xóa. Consent UI hiện ghi thời hạn chưa được chốt, mốc 12 tháng chỉ là đề xuất và ứng dụng chưa tự xóa audio theo lịch.
5. Cấp quyền cho người vận hành vào storage được kiểm soát ngoài repo. Manifest chỉ ghi pseudonymous ID, consent version/state, thời điểm, checksum và storage reference; không ghi tên, email, audio, password hoặc mapping nhận dạng vào Git.
6. Trước/sau buổi thu, chạy retention/orphan preview và kiểm tra số liệu trước khi xác nhận thao tác apply. Dùng erasure preview với đúng actor ID và xác nhận lại ID; không xóa từ preview nếu chưa có yêu cầu hợp lệ.
7. Tạo backup ngoài data-dir bằng CLI `maintenance backup`, kiểm manifest/checksum và restore sang thư mục mới trước khi thu. Không ghi đè backup hoặc đưa backup vào Git.
8. Chỉ export nghiên cứu cho account đã opt-in. Kiểm soát access và xóa theo chính sách được chốt; backup không tự thay đổi khi chạy erasure.
9. Lưu biên nhận vận hành bằng evidence đã khử định danh. Không coi fixture/test data, TTS hoặc số liệu kỹ thuật là kết quả pilot hay CEFR validation.

## Điều kiện chưa được kiểm chứng

- Chủ dự án xác nhận dữ liệu thu thử đã có; dataset, roster, provenance, consent records và audio không được mở hoặc kiểm kê trong lượt này. Kết quả thực nghiệm/CEFR vẫn `NOT_EVALUATED`.
- Retention policy trên giao diện chưa được chốt. Vì vậy report chỉ xác nhận checklist và thao tác fixture, không tuyên bố buổi thu người học đã sẵn sàng.
- UI chưa có batch-account flow; batch/temp-password là API contract được test, không phải thao tác trên giao diện.
- Model inference không chạy; clean-wheel smoke xác nhận đúng trạng thái thiếu model và report `NOT_EVALUATED`, không có band giả.

Owner acceptance xác nhận task #85 hoàn tất; phần policy và điều kiện sử dụng dữ liệu thật tiếp tục được theo dõi riêng ở SCRUM-34.
