# SCRUM-67 — Review kỹ thuật của Codex

Historical target `3b2d2b7`; reference Sang `40907cc`; actual implementation base `bab5f2513b1377013b2538143b50d30de650dc0f` (T01 main + dependency T02 `754ee9a`). Codex viết prompt/review/verification; Luna implement. Quyền trực tiếp của user cho task và PR được dùng trong phạm vi này; global M14 vẫn DRAFT, không tự ghi APPROVED hoặc nghiệm thu thay Sang/Nguyên.

## Các finding đã yêu cầu sửa

- Settlement phải kiểm order/checkout/gateway/mode/currency/amount/expiry, dùng transaction và giữ receipt/event duy nhất. Retry quote/order/license phải trả cùng kết quả, input khác bị từ chối. Proration dùng giá trị còn lại của kỳ đang trả, không cố định tháng 30 ngày.
- Stripe xác minh raw body; VNPay nhận form với amount ×100 và giờ GMT+7; MoMo phân biệt authorized/pending với captured. Header sandbox phải đi qua WSGI. Optional adapter chỉ chạy với config test và injected transport; không có production HTTP client.
- Billing thuộc organization của installation; mọi admin nhìn cùng entitlement/seat count. Không mở research permission qua plan. License installer là dependency được inject, application service không tự ghi SQL entitlement.
- Export giữ dữ liệu học tập/consent/study có ý nghĩa bằng allowlist, loại credential/session digest/provider identifier/license payload và dữ liệu người khác.
- Erasure không được lấy mọi cột `_id` làm tài nguyên sở hữu: lesson/task dùng chung không thuộc người học. Audit chỉ redaction đúng actor/object sở hữu, event/action/time giữ nguyên; event xóa cuối mang actor admin thật.
- API phải từ chối array/object thay actor ID và manifest JSON không phải object bằng lỗi kiểm soát, không trả 500. Có regression tests cho input lỗi.
- Backup phải kiểm lại admin và ghi audit trong transaction sau khi snapshot xong; nếu audit thất bại hoặc admin đã bị revoke thì dọn toàn bộ snapshot. Regression đã tái hiện cả hai lỗi trước khi Luna sửa.
- Retention recheck trạng thái dưới write lock; cleanup kiểm tham chiếu media dùng chung và retry bằng intent bền vững.

## Migration và rollback

Schema v9 có trigger bất biến ngăn xóa consent/rating, vì vậy erasure W5 đầy đủ cần migration cộng thêm v10. Không sửa checksum 005–009, không tắt foreign key hoặc DROP TRIGGER lúc xử lý request. Migration 010 định nghĩa ngoại lệ DELETE gắn cleanup intent `privacy_erasure` đang chạy và owner đúng; audit UPDATE chỉ cho phép redaction chính xác, audit DELETE vẫn cấm. Intent và erasure nằm trong cùng transaction; liên kết tạm bị dọn và intent hoàn tất sau khi xóa.

Trước nâng cấp, snapshot database/blob/protected key ở schema v4 hoặc v9. Failure injection phải rollback ledger/data về v9, reopen không nhân đôi; rollback vận hành bằng restore snapshot vào thư mục mới và dùng wheel tương ứng v9. Không mở bản v10 bằng binary cũ. Root kiểm độc lập all-table row count/hash, report, hai media family và chữ ký license sau restore; thử tampered blob phải bị từ chối.

## Policy và giới hạn bàn giao

Một SQLite installation là một organization. Catalog VND 99.000/199.000 là fixture sandbox để kiểm flow, chưa phải giá thương mại đã được nhóm duyệt. Ladder tăng dần theo task user; Trial được chuẩn hóa tăng dần thay vì mọi feature như bản tham chiếu. Free cho 30 student; seat chỉ chặn tạo student mới, không khóa học hoặc export. Quota assessment chỉ cảnh báo 80/100%; paid grace 14 ngày, annual discount 15%.

Provider merchant sandbox thật, live payment và model inference: NOT_RUN. Handoff backend cho N04 không đồng nghĩa full UI N04 đã hoàn thành. Review Sang về signature/statistical boundary và Nguyên về admin journey còn PENDING; Jira DONE cần các gate của task, không suy ra từ self-review.

## Kiểm tra chéo

Luna thực hiện thêm một lượt code inspection read-only cho ownership/privacy, migration trigger, backup/restore, signature/settlement/replay và license. Không phát hiện BLOCKER/MAJOR cụ thể trong candidate đã kiểm; không chạy test ở lượt này và không thay review độc lập của Sang/Nguyên. Codex giữ trách nhiệm kiểm evidence và chạy verification trên source cuối.
