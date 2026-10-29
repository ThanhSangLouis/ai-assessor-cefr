# Quy trình phối hợp Codex - Antigravity - Git

| Thuộc tính | Giá trị |
| --- | --- |
| Trạng thái quy trình | APPROVED theo D017 |
| Người duyệt V3 và nghiệm thu cuối | Người dùng/chủ dự án |
| Điều phối và review | Codex |
| Triển khai | Antigravity |
| Nguồn đồng bộ | Git repository |
| Ngày ban hành | 08/09/2026 |
| Trạng thái kích hoạt hiện tại | ACTIVE FOR PLANNING - Git baseline hợp lệ; implementation vẫn cần V3 được duyệt |

## 1. Mục tiêu

Quy trình này tách quyền đặc tả, triển khai và nghiệm thu để mọi thay đổi có scope rõ, test được và review trên diff thực tế. Nó bổ sung, không thay thế chuỗi bắt buộc trong `AGENTS.md`:

`Requirement -> Research -> Survey -> Spec -> Test Plan -> Plan -> Implement -> Review`

## 2. Vai trò và quyền

| Vai trò | Được làm | Không được tự làm |
| --- | --- | --- |
| Người dùng/chủ dự án | Duyệt gói V3, cho phép thay đổi scope, nghiệm thu hoặc từ chối kết quả cuối | Không cần xác nhận kỹ thuật thay cho evidence/test |
| Codex | Khảo sát repo; viết Brief/Specification/Plan/Tasks/Test Plan; tạo prompt đã khóa; kiểm tra diff/test/evidence; phát hành prompt fix | Không tự ghi approval của người dùng; không nghiệm thu thay người dùng; trong workflow này không triển khai feature đã giao Antigravity |
| Antigravity | Implement đúng prompt đã khóa; chạy test; ghi raw report; sửa theo prompt fix | Không tự đổi requirement/spec/acceptance; không tự đánh dấu gate; không che giấu test fail hoặc sửa ngoài allowed files |
| Git/repository | Giữ approved package, base/head commit, implementation diff, test report và review trail | Không chứa PII/audio/secret hoặc artifact bị license cấm tái phân phối |

## 3. Luồng chuẩn

```text
User request
  -> Codex survey
  -> Codex Brief -> Specification -> Plan -> Tasks/Test Plan
  -> User approves V3
  -> Codex creates locked implementation prompt
  -> Antigravity implements
  -> Antigravity runs tests/QA and writes raw report
  -> Codex verifies actual diff, commands and evidence
  -> if failed: Codex creates locked fix prompt -> Antigravity fixes -> Codex re-reviews
  -> if passed: User performs final acceptance
```

## 4. State machine

| Trạng thái | Ai có quyền chuyển | Điều kiện |
| --- | --- | --- |
| `DRAFT_V1`/`DRAFT_V2` | Codex | Đang làm rõ/sửa gói |
| `READY_FOR_V3_APPROVAL` | Codex | Brief, spec, plan, tasks và test plan đầy đủ |
| `V3_APPROVED` | Người dùng | Có xác nhận rõ work ID + version; ghi `approval_ref` |
| `PROMPT_LOCKED` | Codex | Prompt khớp V3; có base commit và hash/ref |
| `IMPLEMENTING` | Antigravity | Git hợp lệ; checkout đúng base/branch |
| `IMPLEMENTATION_REPORTED` | Antigravity | Có head commit, actual files, raw commands/output và known issues |
| `CODEX_REVIEW_FAILED` | Codex | Diff/test/evidence không đạt; có finding P0-P2 |
| `FIX_PROMPT_LOCKED` | Codex | Fix scope gắn finding và acceptance rõ |
| `CODEX_REVIEW_PASSED` | Codex | Actual diff đúng spec; required checks đạt; giới hạn được ghi |
| `USER_ACCEPTED` | Người dùng | Người dùng nghiệm thu cuối |
| `CLOSED` | Codex | Acceptance được ghi và hồ sơ đầy đủ |

Antigravity không được bắt đầu ở `READY_FOR_V3_APPROVAL`. Nếu V3 thay đổi sau duyệt, Codex tạo V4 và yêu cầu duyệt lại; không sửa ngầm prompt đã khóa.

### 4.1. Thẩm quyền từng gate

| Gate | Người quyết định | Ý nghĩa |
| --- | --- | --- |
| `V3_APPROVED` | Người dùng/chủ dự án | Cho phép Codex khóa prompt triển khai cho đúng work item |
| `PROMPT_LOCKED` | Codex | Gói triển khai khớp V3, đủ base/scope/test/report contract |
| `CODEX_REVIEW_PASSED/FAILED` | Codex | Kết luận kỹ thuật dựa trên actual diff/test/evidence; chưa phải nghiệm thu cuối |
| `USER_ACCEPTED` | Người dùng/chủ dự án | Nghiệm thu cuối work item |
| G1/G2/... nghiên cứu | Vai trò ghi trong gate/decision log, ví dụ GVHD/GV Ngoại ngữ | Phê duyệt construct, ethics, rater hoặc validity; không được thay bằng gate kỹ thuật |

## 5. Cấu trúc một work item

```text
coordination/work_items/WI-YYYY-NNN-short-name/
  01_brief.md
  02_specification.md
  03_plan_tasks_test_plan.md
  04_locked_implementation_prompt.md
  05_antigravity_raw_report.md
  06_codex_review.md
  07_fix_prompt_v1.md              # chỉ có khi review fail
  08_final_acceptance.md
```

Khởi tạo từ các file trong `coordination/templates/`. Mỗi file phải ghi `work_id`, version, status, base/head commit khi phù hợp và đường dẫn tới artifact liên quan.

## 6. Quy tắc V3 và prompt lock

- V3 là một gói thống nhất gồm Brief, Specification, Plan, Tasks và Test Plan; không chỉ là số phiên bản của một file.
- Người dùng duyệt bằng xác nhận có work ID và version, ví dụ `APPROVE WI-2026-001 V3`.
- `approval_ref` là tham chiếu tới xác nhận thật; Codex không tự tạo.
- Prompt đã khóa phải chép đầy đủ acceptance, allowed files, forbidden changes, test commands và reporting contract.
- Base commit là commit chứa gói V3 đã duyệt. Nếu không có base commit hợp lệ, trạng thái phải là `BLOCKED`, không giao implement.

## 7. Quy tắc Git

- Một work item dùng một branch, đề nghị `work/<work-id>-antigravity`.
- Branch bắt đầu đúng `base_commit` trong prompt lock.
- Antigravity commit implementation; không force-push/rebase sau khi gửi raw report.
- Vòng fix thêm commit mới để giữ audit trail.
- Codex review bằng `git diff <base_commit>...<head_commit>` và trạng thái working tree, không chỉ đọc tóm tắt.
- Nếu có remote/PR, PR chỉ là phương tiện review; repository và commit hash mới là bằng chứng chuẩn.

## 8. Reporting contract

Antigravity phải báo:

- base/head commit và branch;
- danh sách file thực đổi;
- requirement/acceptance nào đã xử lý;
- từng command test/QA, exit code và raw output hoặc đường dẫn artifact;
- test không chạy được và lý do;
- known issue, deviation, dependency/license/privacy impact;
- xác nhận không đưa PII/audio/secret vào commit.

Codex phải kiểm tra lại độc lập các mục trên. “Antigravity báo PASS” không phải bằng chứng nếu không khớp diff và output thực tế.

## 9. Stop conditions

Dừng trước implement/review pass khi:

- V3 chưa được người dùng duyệt;
- Git không hợp lệ hoặc base/head không resolve;
- requirement/spec có hai cách hiểu ảnh hưởng đáng kể;
- prompt cho phép dữ liệu thật/external service nhưng chưa có consent/approval;
- test plan thiếu privacy, speaker leakage, evidence hoặc reproducibility khi có liên quan;
- implementation sửa ngoài scope hoặc test output không truy được.

## 10. Trạng thái hiện tại

Ngày 12/09/2026, theo D019, metadata Git hỏng đã được sao lưu riêng và workspace hiện tại được ghi thành baseline mới `c0ddd8acd79836fd55badad01ec70b4ae0ebfe7b` trên branch `main`. Lịch sử trước baseline không được coi là đã phục hồi. Workflow có thể tạo package và review diff từ baseline này; implementation vẫn không được bắt đầu nếu chưa có work item V3 được người dùng duyệt và prompt `PROMPT_LOCKED`.
