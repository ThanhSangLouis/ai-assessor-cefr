# SCRUM-70 — Task-local authority và baseline

Historical target `3b2d2b78ba5bb35bd162b8f3e5de21ade946d237`; pinned Sang reference `40907cc35b3d04408f9a8713f16d9be99f4cd6c7`. Actual branch base **51eff1f** (S01, PR40; code34da102). Nhánh user tạo được fast-forward từ d60e8a4 để có dependency đã review, không reset hoặc đổi baseline W5.

User yêu cầu làm G1→S01→S02→S03→S04, Luna implement, root prompt/review/verify và PR riêng; ghi log vào sheet Sang repo chính. Chỉ dẫn trực tiếp này cho phép task-local implementation/push/PR, thay executor Antigravity bằng Luna; không tự đổi global SDD DRAFT/APPROVED hoặc Jira Done. Root chủ trách nhiệm diff/chất lượng; reviewer cuối PENDING.

S02 covers M10FR001–008/010 và work packages S02.1–.7; achievements/streak S03 không implement sớm. Domain lane sở hữu pure model/rules; repository lane sở hữu schema/seed/authoring/persistence; integration lane sở hữu purpose-aware audio/service/API/runtime/privacy handoff. Contract freeze và owners nêu trong prompt trước dispatch, không hai owner sửa cùng file.

Source baseline test S01:780PASS,2smoke deselected; statement90.8241%,branch80.1893%. Giữ invariants: learning không scorer/band/teacher_verified/assessmentqueue/researchexport; immutable publish; seed không overwrite teacher; owner authorization/audit; foreign404; delete cleanup retry; no D043; một SQLite/composition root. Runtime evidence ngoài Git.

## Recovery và giới hạn mới nhất

User yêu cầu hoàn tất SCRUM-70, tạo PR rồi dừng; chưa triển khai SCRUM-71/72. PR40 được user merge vào nhánh G1 ngày15/10; PR39 vào main vẫn mở khi kiểm tra. Worktree70 fast-forward từ51eff1f tới merge commit a4c119fdbcf5e17a09372099cb1dc07de853b698; hai tree giống hệt nhau, không đổi source đang kiểm thử. PR70 sẽ dùng nhánh G1 làm base để diff chỉ chứa S02. Không tự merge PR39 hoặc đổi Jira status.
