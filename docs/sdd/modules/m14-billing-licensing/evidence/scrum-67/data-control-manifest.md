# Phạm vi dữ liệu và kiểm soát — SCRUM-67

## Bản xuất dữ liệu cá nhân

Export đọc các bản ghi thuộc tài khoản hiện hành và chỉ trả các trường đã chọn: hồ sơ; phiên ở mức thời điểm, trạng thái và hạn dùng; lịch sử đồng ý; kết quả học tập và luyện tập của chính người học; số đo có kiểu số; bằng chứng học tập đã chiếu an toàn; khảo sát chỉ gồm câu trả lời Likert hợp lệ; cùng metadata biên nhận thuộc người dùng. Không xuất token/digest, khóa, nonce chống phát lại, chữ ký hoặc payload license, định danh bên thanh toán, dữ liệu người khác, câu trả lời nghiên cứu mù hay JSON tự do. Nội dung transcript/kết quả cá nhân được giữ khi trường nguồn nằm trong allowlist.

## Xóa tài khoản

Preview fingerprint bao phủ tài khoản, hồ sơ, phiên và metadata phiên, consent hiện tại/lịch sử, hoạt động, nội dung phản hồi/báo cáo, nỗ lực học tập, khảo sát/nghiên cứu, dữ liệu billing, durable job, cleanup intent/blob deletion và các liên kết audit thuộc tài khoản. Mọi thao tác xóa kiểm tra lại quyền admin, phiên và fingerprint bên trong transaction ghi. Thay đổi sau preview dẫn tới từ chối toàn bộ thao tác.

Migration v10 tạo ngoại lệ xóa hẹp có chủ đích: trigger chỉ cho xóa `consent_events` và `research_ratings` khi có intent đang chạy khớp resource kind và owner trong cùng transaction. Trigger mặc định vẫn chặn xóa; các trigger immutable update không bị gỡ. Assignment/rating bị xóa theo thứ tự khóa ngoại. Audit không bị xóa; chỉ cho phép xóa dấu actor/object liên quan và reason trong đúng hình dạng redaction, giữ nguyên event, action và thời điểm. IDs audit độc lập/shared resources không bị gom nhầm. Hồ sơ có tham chiếu bắt buộc được vô hiệu hóa và bỏ thông tin đăng nhập; enrollment pseudonym được thay bằng nhãn opaque của intent. Intent và audit tối thiểu là lịch sử xóa không chứa bí mật hay nội dung riêng tư.

## Retention, media và backup

Retention mặc định chỉ xem trước. Khi áp dụng, quyền và điều kiện đủ tuổi được tính lại dưới write lock; phản hồi đang chạy/xếp hàng, attempt chưa hoàn tất hoặc trạng thái không biết, job mới lên lịch được giữ lại. Dọn blob kiểm tra lại tham chiếu `responses` và `learning_media` dưới cùng transaction trước khi unlink; intent thất bại được giữ cho lần retry sau. Media bài học được công bố không được xem là orphan chỉ vì không còn phản hồi học viên.

Backup dùng SQLite snapshot nhất quán, lưu mọi blob được `responses` và `learning_media` tham chiếu, kiểm tra hash/kích thước và từ chối metadata blob mâu thuẫn. Manifest ghi phiên bản schema, số lượng, nhóm media và hash file. Khóa cục bộ cần để khôi phục license/OAuth được đưa vào backup hạn chế quyền, với owner hiện hành, file thường, không symlink/hardlink, mode `0600`; nội dung key không có trong export cá nhân hoặc HTTP response; manifest dành cho admin chỉ chứa tên file và hash kiểm tra. Restore kiểm tra checksum, integrity, FK, schema, blob và key rồi mở thử store ở thư mục mới; API chỉ chọn backup theo ID server đã cấp và không ghi đè thư mục dữ liệu đang chạy.
