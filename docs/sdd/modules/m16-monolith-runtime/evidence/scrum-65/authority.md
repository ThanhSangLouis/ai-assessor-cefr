# SCRUM-65 — Chỉ dẫn triển khai trực tiếp

Target lịch sử 3b2d2b7; reference 40907cc; base nhánh người dùng chỉ định 9968abc.
Ngày 15/10/2026. Người dùng yêu cầu: “Làm task này đi, t đã tạo sẵn nhánh, nào done thì tạo PR, bạn chỉ review và tạo promt cho các subagent luna implement code cho nhanh và tiết kiệm, nào oke thì tạo PR”.

Áp dụng chỉ dẫn này để giao Luna implementation thay mặc định Antigravity/read-only subagent trong skill, Codex chỉ soạn contract/prompt/review/evidence và chạy kiểm tra độc lập. Không suy ra approval toàn bộ M11–M16 hoặc nghiệm thu thay Sang. Jira đọc thực tế: G0/G2 Done, G1 To Do, SCRUM-65 In Progress; PR35 đã merge. Task được triển khai trong nhánh riêng theo chỉ dẫn trực tiếp; G1/Sang review vẫn là dependency ghi rõ trước acceptance/merge.

Giữ base nhánh 9968abc do người dùng chọn; 3b2d2b7 là baseline lịch sử để so sánh, không gọi hai revision là một. Không reset nhánh hoặc bỏ Windows fix của main. Chỉ phát PR khi code/test/review đã đạt và ghi limitation; không tự transition Done hoặc merge.
