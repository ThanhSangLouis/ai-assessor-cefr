# W5-G1 — Contract đối chiếu và invariant

Historical target `3b2d2b78ba5bb35bd162b8f3e5de21ade946d237`; Sang reference `40907cc35b3d04408f9a8713f16d9be99f4cd6c7`; actual implementation base `d60e8a4` (T01–T03 merged).
User chỉ định Thắng thực hiện thay Sang (15/10/2026). Jira SCRUM63 hiện Testing; không tự ghi user/reviewer approval hoặc chuyển Done. Contract dưới đây chốt cách triển khai theo mô tả task và week05 §2.

| Invariant | Cách kiểm |
| --- | --- |
| Interaction null/insufficient_evidence cho độc thoại | typed report + regression |
| teacher_verified chỉ sau teacher action có audit | report/review transaction tests |
| practice/lesson không score/band | purpose boundary S02; không giả lập trong S01 |
| LID/off-topic/prompt-reading không trừ điểm | score input/output invariant, routing only |
| score/band có model/version/calibration/evidence | hash/schema/feature identity + fail closed |
| nghiên cứu cần consent còn hiệu lực | server checks; S04 + T02 contract |
| owner/role kiểm phía server | foreign-resource404, unauthorizedmutationtests |

Reference chỉ đọc qua `git show40907cc:<path>`; không fetch hoặc sửa repo Sang đang có thay đổi riêng. Khác biệt an toàn cần giữ: source `for_model` trảNone rồi dùng rule cũ khi thiếu calibration; target phải NOT_EVALUATED/503, không fallbackgiả. Source fold scale0 thay1; target phải từ chối invalidartifact. Source metadata nominalcoverage không phải empiricalcoverage trên người học; không copy claim876sample/coverage/modelstats vào Git như phép đo của target. Model/calibration/audio thật giữ ngoàiGit; chỉ dùng fixture tổng hợp cho tooltest khi chưa có dataset được duyệt.

CV+ tính fold predictions từ featurevector cùng artifact, không thể suy prediction set chỉ từ scalar score. Alpha0.10 là tham số, không tự chứng minh90% coverage. Primary reference: [Barber và cộng sự, Predictive inference with the jackknife+](https://arxiv.org/abs/1905.02928). Mọi benchmark target ghi fixture/data provenance, manifest/hash/seed và giới hạn, không dùng confirmation set đểtune.
