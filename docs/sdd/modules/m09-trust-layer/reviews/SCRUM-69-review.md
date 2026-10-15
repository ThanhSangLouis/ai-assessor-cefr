# Review implementation SCRUM-69

Historical target `3b2d2b78ba5bb35bd162b8f3e5de21ade946d237`; Sang reference `40907cc35b3d04408f9a8713f16d9be99f4cd6c7`; source base `d60e8a4`, G1 parent `9748814`.

Root review actual diff và các correction; Luna triển khai source/test. Những finding bắt buộc được giải quyết bằng regression:

| Finding | Hậu quả trước sửa | Giải quyết |
| --- | --- | --- |
| Trust reasons thiếu trong routing | uncertainty thành failure/retry | reason registry + routing tests |
| Resolve task chỉ theo ID/config snapshot | guard đọc sai prompt/version | repository resolver và metadata versioned, không overwrite boot |
| Model activation giữ calibration cũ | prediction không còn gắn scorer | rebind/check pin khi activate/reload |
| Bound source_versions cũ | report long-window cũ không đọc được | giữ old field; bound provenance mới riêng |
| Rejected language thành review | response/report disposition mâu thuẫn | explicit REJECTED, không score/candidate |
| Invalid geometry ném ValueError | retry không giải quyết được input | controlled LONG_RESPONSE_REVIEW |
| Indicator thiếu evidence | UI không truy vết được chỉ báo | IDs từ validator, cùng criterion |
| Staff report cần candidate | completed report bị 404 | staff kiểm response existence |
| HTML provenance lộ path | JSON an toàn nhưng DOM chưa an toàn | safe metadata projection cả HTML/API |

CV+ được kiểm riêng bằng quantile oracle trên sáu vector và pinned reference artifact ngoài Git; kết quả khớp đến tolerance 1e-10. Không diễn giải alpha thành empirical accuracy. LID không lấy forced-English ASR làm bằng chứng tiếng Anh. Guards không thay vector/score; missing prerequisite không fallback. Interaction và teacher verification invariant được giữ.

Final commands/counts/coverage, wheel và browser results được ghi ở final verification riêng. Reviewer/user verdict: **PENDING**; không tự đổi Jira Done hoặc global SDD DRAFT.
