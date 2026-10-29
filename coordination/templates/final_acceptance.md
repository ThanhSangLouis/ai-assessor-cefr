# Final user acceptance

| Field | Value |
| --- | --- |
| `work_id` | `[required]` |
| `codex_review_ref` | `[required]` |
| `reviewed_head_commit` | `[required]` |
| `decision` | `[ACCEPT/REJECT/REQUEST_CHANGES - user only]` |
| `acceptance_ref` | `[actual user confirmation]` |
| `date` | `[actual date]` |

Codex chỉ chuyển work item sang `CLOSED` sau khi có quyết định thực tế ở bảng trên. Technical review pass không tự động trở thành nghiệm thu của người dùng.

