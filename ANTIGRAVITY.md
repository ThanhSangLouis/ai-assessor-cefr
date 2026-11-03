# Antigravity — điểm vào repo

Đọc [AGENTS.md](AGENTS.md) và [skill SDD dùng chung](.agents/skills/sdd-antigravity-orchestrator/SKILL.md). Chỉ triển khai task có prompt trong scope module với Phase 05 `APPROVED`, đúng base revision/fingerprint và vùng file được phép sửa. Trả raw report, actual diff và kết quả kiểm tra theo mẫu của skill; không tự đánh dấu nghiệm thu.

> **QUY TẮC BẮT BUỘC:** Tuyệt đối **KHÔNG ĐƯỢC TỰ Ý CHẠY `git commit`** khi người dùng chưa yêu cầu rõ ràng. Dù hoàn thành công việc hay pass toàn bộ test, agent chỉ thay đổi mã nguồn/tài liệu, kiểm tra diff, chạy test và báo cáo kết quả. Chỉ thực hiện commit khi người dùng ra lệnh trực tiếp.
