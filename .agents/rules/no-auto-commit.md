# Quy tắc bắt buộc: Không tự ý Git Commit

- **Tuyệt đối KHÔNG tự ý chạy lệnh `git commit`** nếu người dùng chưa chỉ định hoặc chưa giao việc commit.
- Sau khi hoàn thành bất kỳ tác vụ nào (viết tính năng, sửa lỗi, cập nhật tài liệu, chạy kiểm thử pass 100%), agent chỉ dừng lại ở việc:
  1. Kiểm tra mã nguồn và diff (`git status`, `git diff`).
  2. Chạy test xác minh.
  3. Báo cáo kết quả và thay đổi cho người dùng.
- **Chỉ thực hiện `git commit` khi và chỉ khi** người dùng ra lệnh trực tiếp (ví dụ: "commit đi", "commit giúp tôi", "tạo commit").
