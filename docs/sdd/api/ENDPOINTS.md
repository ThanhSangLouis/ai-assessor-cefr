# Danh sách endpoint (sinh tự động)

Sinh bằng `python tools/export_openapi.py` từ chính các route của ứng dụng; không sửa tay. Cột *Dịch vụ* là nơi gateway chuyển yêu cầu tới (`aicefr.platform.gateway.service_for`).

Tổng: **191 thao tác**, trong đó **156** dưới `/api/` và 35 trang HTML hoặc đường dẫn khác.

| Nhóm người gọi (tag) | Số thao tác `/api/` |
| --- | --- |
| `student` | 50 |
| `teacher` | 48 |
| `admin` | 32 |
| `auth` | 20 |
| `me` | 4 |
| `billing` | 2 |

| Dịch vụ nhận | Số thao tác |
| --- | --- |
| `core` | 158 |
| `web` | 33 |

| Phương thức | Đường dẫn | Tag | Dịch vụ | Mô tả |
| --- | --- | --- | --- | --- |
| GET | `/` | web | web | Page Home |
| GET | `/account` | web | web | Page Account |
| GET | `/admin` | web | web | Page Admin |
| GET | `/api/v1/admin/accounts` | admin | core | List Accounts |
| POST | `/api/v1/admin/accounts` | admin | core | Create Accounts |
| GET | `/api/v1/admin/accounts/{account_id}` | admin | core | Account Detail |
| PATCH | `/api/v1/admin/accounts/{account_id}/contact` | admin | core | Change Account Contact |
| POST | `/api/v1/admin/accounts/{account_id}/delete` | admin | core | Delete Account As Admin |
| POST | `/api/v1/admin/accounts/{account_id}/disable` | admin | core | Disable Account |
| POST | `/api/v1/admin/accounts/{account_id}/enable` | admin | core | Enable Account |
| POST | `/api/v1/admin/accounts/{account_id}/reset-password` | admin | core | Reset Password |
| POST | `/api/v1/admin/accounts/{account_id}/revoke-sessions` | admin | core | Revoke Account Sessions |
| POST | `/api/v1/admin/accounts/{account_id}/role` | admin | core | Change Role |
| POST | `/api/v1/admin/accounts/{account_id}/unlink-google` | admin | core | Unlink Account Google |
| POST | `/api/v1/admin/accounts/{account_id}/unlock` | admin | core | Unlock Account |
| GET | `/api/v1/admin/coach` | admin | core | Coach Dashboard |
| PUT | `/api/v1/admin/coach/tier` | admin | core | Set Coach Tier |
| GET | `/api/v1/admin/config` | admin | core | Read Config |
| POST | `/api/v1/admin/config` | admin | core | Update Config |
| GET | `/api/v1/admin/credit-orders` | admin | core | Admin Credit Orders |
| GET | `/api/v1/admin/credit-orders/{order_id}/events` | admin | core | Admin Credit Order Events |
| POST | `/api/v1/admin/credits/grant` | admin | core | Grant Credits |
| GET | `/api/v1/admin/erase` | admin | core | Preview Erasure |
| POST | `/api/v1/admin/erase` | admin | core | Erase Participant |
| GET | `/api/v1/admin/google` | admin | core | Google Status |
| GET | `/api/v1/admin/models` | admin | core | List Models |
| POST | `/api/v1/admin/models/{name}/activate` | admin | core | Activate Model |
| GET | `/api/v1/admin/prices` | admin | core | Prices |
| PUT | `/api/v1/admin/prices` | admin | core | Set Prices |
| GET | `/api/v1/audit` | admin | core | Audit Entries |
| POST | `/api/v1/auth/forgot/email` | auth | core | Forgot By Email |
| POST | `/api/v1/auth/forgot/email/reset` | auth | core | Reset By Email |
| POST | `/api/v1/auth/login` | auth | core | Login |
| POST | `/api/v1/auth/logout` | auth | core | Logout |
| POST | `/api/v1/auth/signup` | auth | core | Signup |
| GET | `/api/v1/billing/notify/{gateway}` | billing | core | Billing Notify |
| POST | `/api/v1/billing/notify/{gateway}` | billing | core | Billing Notify |
| GET | `/api/v1/classes` | teacher | core | List Classes |
| POST | `/api/v1/classes` | teacher | core | Create Class |
| GET | `/api/v1/classes/{class_id}` | teacher | core | Class Detail |
| POST | `/api/v1/classes/{class_id}/archive` | teacher | core | Archive Class |
| DELETE | `/api/v1/classes/{class_id}/code` | teacher | core | Drop Join Code |
| POST | `/api/v1/classes/{class_id}/code` | teacher | core | New Join Code |
| DELETE | `/api/v1/classes/{class_id}/invites/{account_id}` | teacher | core | Withdraw Invite |
| POST | `/api/v1/classes/{class_id}/members` | teacher | core | Add Members |
| DELETE | `/api/v1/classes/{class_id}/members/{account_id}` | teacher | core | Remove Member |
| POST | `/api/v1/classes/{class_id}/restore` | teacher | core | Restore Class |
| POST | `/api/v1/classes/{class_id}/teachers` | admin | core | Add Teacher |
| DELETE | `/api/v1/classes/{class_id}/teachers/{account_id}` | admin | core | Remove Teacher |
| GET | `/api/v1/health` | admin | core | Health |
| GET | `/api/v1/learn` | student | core | Learn Home |
| GET | `/api/v1/learn/attempts/{attempt_id}/audio` | student | core | Attempt Audio |
| GET | `/api/v1/learn/bands` | student | core | My Bands |
| POST | `/api/v1/learn/bands` | student | core | Choose Bands |
| GET | `/api/v1/learn/drill` | student | core | My Drill Words |
| GET | `/api/v1/learn/drill/{response_id}` | student | core | Drill |
| POST | `/api/v1/learn/drill/{response_id}/takes` | student | core | Drill Take |
| GET | `/api/v1/learn/lessons/{lesson_id}` | student | core | Learn Lesson |
| POST | `/api/v1/learn/lessons/{lesson_id}/steps/{step_id}/attempts` | student | core | Learn Attempt |
| GET | `/api/v1/learn/media/{key}` | student | core | Lesson Media |
| GET | `/api/v1/learn/passage` | student | core | Passage State |
| POST | `/api/v1/learn/passage` | student | core | Make Passage |
| POST | `/api/v1/learn/passage/{passage_id}/takes` | student | core | Passage Take |
| DELETE | `/api/v1/learn/plan` | student | core | Close My Plan |
| GET | `/api/v1/learn/plan` | student | core | My Plan |
| POST | `/api/v1/learn/plan` | student | core | Make My Plan |
| GET | `/api/v1/learn/retell/{response_id}` | student | core | Retell |
| POST | `/api/v1/learn/retell/{response_id}/rounds` | student | core | Retell Round |
| GET | `/api/v1/learn/review` | student | core | Learn Review |
| POST | `/api/v1/learn/review/attempts` | student | core | Learn Review Attempt |
| GET | `/api/v1/me` | auth | core | Me |
| GET | `/api/v1/me/account` | auth | core | My Account |
| GET | `/api/v1/me/achievements` | student | core | My Achievements |
| GET | `/api/v1/me/activity` | auth | core | My Activity |
| GET | `/api/v1/me/badges` | auth | web | My Badges |
| GET | `/api/v1/me/classes` | student | core | My Classes |
| POST | `/api/v1/me/classes/join` | student | core | Join By Code |
| POST | `/api/v1/me/classes/{class_id}/accept` | student | core | Accept Invite |
| POST | `/api/v1/me/classes/{class_id}/decline` | student | core | Decline Invite |
| POST | `/api/v1/me/classes/{class_id}/leave` | student | core | Leave Class |
| PATCH | `/api/v1/me/contact` | auth | core | Change My Contact |
| POST | `/api/v1/me/credit-orders` | student | core | My Credit Order |
| GET | `/api/v1/me/credit-packs` | student | core | My Credit Packs |
| GET | `/api/v1/me/credits` | student | core | My Credits |
| GET | `/api/v1/me/credits/lesson` | student | core | Lesson Quote |
| GET | `/api/v1/me/credits/quote` | student | core | Quote |
| POST | `/api/v1/me/delete-account` | student | core | Delete My Account |
| GET | `/api/v1/me/email` | auth | core | My Email |
| PUT | `/api/v1/me/email/reminders` | auth | core | Set Reminders |
| POST | `/api/v1/me/email/verify` | auth | core | Verify |
| POST | `/api/v1/me/email/verify/send` | auth | core | Send Verification |
| GET | `/api/v1/me/events` | me | core | Events |
| GET | `/api/v1/me/export.json` | student | core | Export My Data |
| POST | `/api/v1/me/google/unlink` | auth | core | Unlink My Google |
| GET | `/api/v1/me/nudges` | student | web | My Nudges |
| POST | `/api/v1/me/password` | auth | core | Change My Password |
| GET | `/api/v1/me/phrases` | student | core | My Phrases |
| POST | `/api/v1/me/phrases/review` | student | core | Review Phrase |
| PATCH | `/api/v1/me/profile` | auth | core | Change My Profile |
| GET | `/api/v1/me/profile.json` | student | core | Speaking Profile |
| GET | `/api/v1/me/progress` | student | core | My Progress |
| GET | `/api/v1/me/pronunciation` | student | core | My Pronunciation |
| DELETE | `/api/v1/me/push` | me | core | Unsubscribe |
| GET | `/api/v1/me/push` | me | core | Push Config |
| PUT | `/api/v1/me/push` | me | core | Subscribe |
| GET | `/api/v1/me/replay-labels` | student | core | My Replay Labels |
| GET | `/api/v1/me/responses` | student | core | My Responses |
| GET | `/api/v1/me/sessions` | auth | core | My Sessions |
| POST | `/api/v1/me/sessions/revoke-others` | auth | core | Revoke My Other Sessions |
| DELETE | `/api/v1/me/sessions/{session_id}` | auth | core | End My Session |
| GET | `/api/v1/responses` | admin | core | List Responses |
| POST | `/api/v1/responses` | student | core | Submit Response |
| GET | `/api/v1/responses/{response_id}` | student | core | Get Report |
| GET | `/api/v1/responses/{response_id}/audio` | student | core | Get Audio |
| GET | `/api/v1/responses/{response_id}/coach` | student | core | Coach |
| GET | `/api/v1/responses/{response_id}/history` | teacher | core | History |
| GET | `/api/v1/responses/{response_id}/replay` | student | core | Replay |
| POST | `/api/v1/responses/{response_id}/replay/{moment_id}` | student | core | Answer |
| GET | `/api/v1/responses/{response_id}/status` | student | core | Response Status |
| POST | `/api/v1/responses/{response_id}/upgrade` | student | core | Upgrade |
| GET | `/api/v1/review/queue` | teacher | core | Review Queue |
| GET | `/api/v1/review/stats` | teacher | core | Cohort Stats |
| POST | `/api/v1/review/{response_id}` | teacher | core | Submit Review |
| POST | `/api/v1/review/{response_id}/close` | teacher | core | Close Review |
| DELETE | `/api/v1/review/{response_id}/lock` | teacher | core | Unlock Review |
| POST | `/api/v1/review/{response_id}/lock` | teacher | core | Lock Review |
| GET | `/api/v1/stats` | admin | core | Stats Summary |
| GET | `/api/v1/tasks` | student | core | List Tasks |
| GET | `/api/v1/teach/attempts/{attempt_id}` | teacher | core | Teach Attempt |
| POST | `/api/v1/teach/attempts/{attempt_id}/override` | teacher | core | Teach Override |
| GET | `/api/v1/teach/insights` | teacher | core | Teach Insights |
| GET | `/api/v1/teach/lessons/draft` | teacher | core | Lesson Draft Offer |
| POST | `/api/v1/teach/lessons/draft` | teacher | core | Write Lesson Draft |
| DELETE | `/api/v1/teach/lessons/{lesson_id}` | teacher | core | Teach Archive Lesson |
| GET | `/api/v1/teach/lessons/{lesson_id}` | teacher | core | Teach Lesson |
| PUT | `/api/v1/teach/lessons/{lesson_id}` | teacher | core | Teach Save Lesson |
| POST | `/api/v1/teach/lessons/{lesson_id}/move` | teacher | core | Teach Move Lesson |
| GET | `/api/v1/teach/lessons/{lesson_id}/preview` | teacher | core | Teach Preview Lesson |
| POST | `/api/v1/teach/lessons/{lesson_id}/publish` | teacher | core | Teach Publish |
| POST | `/api/v1/teach/lessons/{lesson_id}/steps/{step_id}/image` | teacher | core | Teach Image |
| POST | `/api/v1/teach/lessons/{lesson_id}/steps/{step_id}/model-audio` | teacher | core | Teach Model Audio |
| GET | `/api/v1/teach/paths` | teacher | core | Teach Paths |
| POST | `/api/v1/teach/paths` | teacher | core | Teach New Path |
| POST | `/api/v1/teach/paths/compose` | teacher | core | Compose Path |
| POST | `/api/v1/teach/paths/compose/{plan_id}/save` | teacher | core | Save Composed Path |
| POST | `/api/v1/teach/paths/import` | teacher | core | Teach Import |
| PATCH | `/api/v1/teach/paths/{path_id}` | teacher | core | Teach Patch Path |
| POST | `/api/v1/teach/paths/{path_id}/assign` | teacher | core | Assign Path |
| GET | `/api/v1/teach/paths/{path_id}/export` | teacher | core | Teach Export |
| POST | `/api/v1/teach/paths/{path_id}/units` | teacher | core | Teach New Unit |
| POST | `/api/v1/teach/preview` | teacher | core | Teach Preview Attempt |
| GET | `/api/v1/teach/pronunciation` | teacher | core | Class Pronunciation |
| GET | `/api/v1/teach/tasks` | teacher | core | Assessment Prompts |
| POST | `/api/v1/teach/tasks` | teacher | core | Add Prompt |
| PATCH | `/api/v1/teach/tasks/{task_id}` | teacher | core | Edit Prompt |
| DELETE | `/api/v1/teach/units/{unit_id}` | teacher | core | Teach Delete Unit |
| PATCH | `/api/v1/teach/units/{unit_id}` | teacher | core | Teach Patch Unit |
| POST | `/api/v1/teach/units/{unit_id}/lessons` | teacher | core | Teach New Lesson |
| POST | `/api/v1/teach/units/{unit_id}/move` | teacher | core | Teach Move Unit |
| GET | `/bands` | web | web | Page Bands |
| GET | `/billing/orders/{order_id}/receipt` | web | core | Billing Receipt |
| GET | `/billing/return/{gateway}` | web | core | Billing Return |
| GET | `/billing/sandbox/{order_id}` | web | core | Sandbox Page |
| POST | `/billing/sandbox/{order_id}/pay` | web | core | Sandbox Pay |
| GET | `/credits` | web | web | Page Credits |
| GET | `/drill/{response_id}` | web | web | Page Drill |
| GET | `/forgot` | web | web | Page Forgot |
| GET | `/login` | web | web | Page Login |
| GET | `/my-assignments` | web | web | Page My Assignments Gone |
| GET | `/my-classes` | web | web | Page My Classes |
| GET | `/my-progress` | web | web | Page My Progress |
| GET | `/my-responses` | web | web | Page My Responses |
| GET | `/passage` | web | web | Page Passage |
| GET | `/payment-terms` | web | web | Page Payment Terms |
| GET | `/phrases` | web | web | Page Phrases |
| GET | `/practice` | web | web | Page Practice |
| GET | `/practice/lessons/{lesson_id}` | web | web | Page Lesson |
| GET | `/practice/review` | web | web | Page Practice Review |
| GET | `/progress/{response_id}` | web | web | Page Progress |
| GET | `/report/{response_id}` | web | web | Page Report |
| GET | `/retell/{response_id}` | web | web | Page Retell |
| GET | `/review` | web | web | Page Queue |
| GET | `/review/stats` | web | web | Page Cohort Stats |
| GET | `/review/{response_id}` | web | web | Page Review One |
| GET | `/signup` | web | web | Page Signup |
| GET | `/teach` | web | web | Page Teach |
| GET | `/teach/classes` | web | web | Page Classes |
| GET | `/teach/classes/{class_id}` | web | web | Page Class |
| GET | `/teach/insights` | web | web | Page Teach Insights |
| GET | `/teach/lessons/{lesson_id}` | web | web | Page Teach Lesson |
| GET | `/teach/tasks` | web | web | Page Teach Tasks |
