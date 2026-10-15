# SCRUM-67 — Quyền thực hiện và baseline

User giao task W5-T03 cùng branch và đủ work package, tiếp nối phân công Luna implement/Codex prompt-review/PR. Không giả lập global M14 approval hoặc nghiệm thu Sang/Nguyên. Historical target `3b2d2b7`, reference Sang `40907cc`; actual base `bab5f25` gồm nhánh67 ban đầu `840efb9` và dependency T02 `754ee9a` bằng merge local, không merge PR37/main.

W5 chỉ sandbox/test, live payment khóa cứng. Không cấu hình production/thu tiền thật/deploy callback/network provider thật. Giữ nguyên SQL/checksum migration 005–009; bổ sung migration 010_privacy để thực hiện erasure theo quyền trực tiếp của task. Giá/catalog sandbox là policy fixture để test flow; không trình bày là giá thương mại đã được nhóm duyệt. Root quản lý evidence/prompt log bằng diễn giải vừa phải; không chép nguyên văn user hoặc ghi yêu cầu nhắc log.
