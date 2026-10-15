# SCRUM-66 — Nhật ký điều phối Luna

Ngày 15/10/2026. Owner: Thắng. Theo yêu cầu người dùng, Luna triển khai code; Codex viết prompt và review độc lập.

Hai revision tham chiếu W5: target `3b2d2b7`, Sang `40907cc`. Implementation base: `b2b573f` từ T01. Ba prompt A1 được lưu trước dispatch; fingerprint lúc phát hành: `d66d2836052ce56f8067c635e3e2f4021eb9aa545bcb6b1f83664310ecb8f4e1`. Nội dung prompt đã phát hành được giữ nguyên.

| Prompt | Vùng sở hữu ban đầu | Trạng thái phát hành |
| --- | --- | --- |
| SCRUM-66-accounts-A1 | account/session/consent/repository | Đã lưu trước dispatch |
| SCRUM-66-google-A1 | PKCE/ID token/transport/replay | Đã lưu trước dispatch |
| SCRUM-66-api-A1 | WSGI/DI/API/consumer handoff | Đã lưu trước dispatch |

## Phản hồi và mở rộng phân công trong cùng phiên

Đây là bản tóm tắt các phản hồi thực tế, không phải nguyên văn hoặc approval của reviewer:

- Accounts: danh mục 15 icon/10 màu; từ chối goal bool; expiry session/password tạm; admin DTO có disabled/locked; audit mutation; password CAS kiểm lại credential/session trong transaction; batch failure injection; consent opt-out void assignment/withdraw enrollment và export; nâng coverage nhánh security.
- API: legacy admin tạo/đổi account phải dùng cùng AccountService; được giao thêm portal/service.py và portal/data.py có giới hạn. Sửa thứ tự exception để giữ foreign-resource 404, lockout 429, temp gate 403; HTTPS dùng cookie `__Host-`; access log không chứa query; erasure scrub credential nhưng giữ lịch sử bất biến có FK. Bổ sung form đổi password và assertion HTTP status sau khi root phát hiện 500 trong log clean-wheel.
- Google: được giao thêm `tests/api/test_google_identity_api.py` để kiểm real service + HTTP adapter với RSA offline; sau đó `tests/storage/test_identity_compatibility.py` để kiểm v4→v9, dữ liệu cũ và reopen. Không sửa source của lane khác.

Mỗi file source/test chỉ có một agent sửa tại một thời điểm. Root tổng hợp evidence và thực hiện full verification; không giả lập kết quả Google thật hoặc nghiệm thu Nguyên/Sang.
