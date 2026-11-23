# Đề xuất D106: giảng viên nhờ AI viết nháp đề đánh giá

Trạng thái: **PROPOSED** — chờ chủ dự án duyệt. Chưa ghi vào decision log, SRS hay SDD; chưa có code.
Soạn ngày 17/11/2026 trên nhánh `FE-Teacher`. Khuôn mẫu: D075 (AI viết nháp bài học, FR-91, AC-91.4, AC-91.5).

## 1. Theo mẫu quyết định (decision log mục 3)

| Trường | Nội dung |
| --- | --- |
| ID | D106 |
| Ngày | 17/11/2026 (đề xuất) |
| Vấn đề | Ngân hàng đề theo band (D076) do giảng viên gõ tay: mỗi đề cần lời đề tiếng Việt đúng band và 6–15 từ khoá tiếng Anh để gắn cờ lạc đề. Viết đủ 3 đề đang dùng cho mỗi band tốn thời gian, từ khoá hay thiếu nên bài đúng chủ đề vẫn bị gắn cờ. |
| Các phương án | (A) Giữ gõ tay. (B) AI viết nháp lời đề và từ khoá trong hộp thoại "Thêm đề", giảng viên sửa rồi bấm Lưu như đề tự viết. (C) AI tự sinh và tự bật đề. |
| Quyết định | **(B).** Trong hộp thoại "Thêm đề"/"Sửa đề", nút "AI viết nháp" nhận band đang chọn và vài chữ về ý đề (hoặc lời đề đang có để gợi ý thêm từ khoá); mô hình trả lời đề tiếng Việt và từ khoá tiếng Anh, điền vào hai ô. Không lưu gì: đề chỉ vào ngân hàng khi giảng viên bấm Lưu, đi đúng đường `POST/PATCH /api/v1/teach/tasks` hiện có (phiên bản mới khi đổi lời, D076). Gửi ra ngoài chỉ band và chữ giảng viên gõ, không có gì về học viên. Trả lượt từ ví giảng viên như D075, chung giới hạn ngày và bộ đếm của D072, D073. Nút ẩn khi máy chủ chưa bật mô hình (`AICEFR_COACH_PROVIDER=off`). |
| Rationale | Dùng lại trọn hạ tầng của D075 (nhà cung cấp, giới hạn, sổ lượt, ẩn khi tắt), rủi ro thấp: không chạm rubric, band, điểm hay quyết định duyệt (BR-01, BR-07, M05); không gửi dữ liệu cá nhân. (C) bị loại vì đề vào bài thi của học viên mà không ai đọc. |
| Evidence/source | Đề xuất số 1 trong phiên 17/11/2026 ("áp dụng dùng thêm AI cho các chức năng trong role teacher"); khuôn `coach/lesson_draft.py`, `coach_api.py:211–290`. |
| Owner/approver | Chủ dự án |
| Files affected | Xem mục 4 |
| Trạng thái | PROPOSED |

## 2. FR đề xuất: FR-105 — Giảng viên nhờ AI viết nháp đề đánh giá (D106)

**Mô tả:** Trong hộp thoại thêm hoặc sửa đề, giảng viên nhờ mô hình ngôn ngữ viết nháp lời đề và từ khoá cho band đang chọn. Bản nháp chỉ điền vào form; giảng viên sửa và lưu như đề tự viết. Mỗi lần trừ lượt trong ví giảng viên, chung giới hạn ngày của mô hình.
**Ưu tiên:** C

| Acceptance Criteria (dự kiến, tên test đề xuất) |
| --- |
| **AC-105.1** — *Given* máy chủ bật mô hình, *When* giảng viên nhờ viết nháp đề B1 về "du lịch", *Then* nhận `prompt_text` tiếng Việt 10–600 ký tự và 6–15 từ khoá tiếng Anh viết thường, không trùng; không có đề mới trong ngân hàng (`test_a_teacher_gets_a_task_draft_and_nothing_is_saved`). |
| **AC-105.2** — *Given* lời đề đang có, *When* nhờ gợi ý từ khoá, *Then* lời đề giữ nguyên, chỉ trả từ khoá (`test_keywords_are_suggested_for_an_existing_prompt`). |
| **AC-105.3** — *Given* bản tính lượt, *When* viết nháp, *Then* trừ lượt trong ví giảng viên, lịch sử ghi "Soạn đề bằng AI"; mô hình lỗi thì hoàn lượt (`test_metered_a_task_draft_is_paid_and_refunded_on_failure`). |
| **AC-105.4** — *Given* `AICEFR_COACH_PROVIDER=off`, *When* mở trang Đề, *Then* không có nút "AI viết nháp"; gọi API trả 503 (`test_the_task_draft_is_hidden_when_the_model_is_off`). |
| **AC-105.5** — *Given* học viên, *When* gọi API viết nháp đề, *Then* 403 (`test_only_staff_can_draft_a_task`). |
| **AC-105.6** — *Given* mô hình trả lời đề tiếng Anh hoặc từ khoá ngoài giới hạn, *When* phân tích, *Then* từ chối bản nháp, báo lỗi tiếng Việt, hoàn lượt (`test_a_draft_out_of_bounds_is_refused`). |

## 3. Thiết kế

- **Lõi** `coach/task_draft.py` theo khuôn `lesson_draft.py`: `PROMPT_VERSION = "task-draft-v1"`, `SYSTEM`, `SCHEMA` (`prompt_text`, `topic_keywords: list[str]`), `user_message(band, idea, existing_prompt)`, `parse(raw)` kiểm: lời đề có dấu tiếng Việt, 10–600 ký tự, đề nói 40–60 giây (nêu quan điểm hoặc kể quá trình, như ghi chú trong hộp thoại); từ khoá tiếng Anh, chuẩn hoá viết thường, bỏ trùng, 6–15 từ.
- **API** trong `services/core/assessment/coach_api.py`, cùng chỗ với soạn bài:
  - `GET /api/v1/teach/tasks/draft` → `{available, price}`.
  - `POST /api/v1/teach/tasks/draft` (`STAFF_ONLY`), thân `TaskDraftIn {band, idea: 3–300 ký tự | None, prompt_text: str | None}` (ít nhất một trong hai) → `{prompt_text, topic_keywords}`; giữ lượt trước khi gọi, hoàn khi lỗi, như `write_lesson_draft`.
- **Sổ lượt:** thêm `MeteredAction.TASK_DRAFT = "task_draft"` (nhãn "Soạn đề bằng AI") — đổi enum nên **cập nhật sơ đồ lớp** (`02_class.drawio`, `tools/gen_class_diagram.py`). Giá: dùng chung giá bản nâng cấp như D075 (điểm cần chốt).
- **Giao diện** `teach_tasks.html` + `teach_tasks.js`: khối "AI viết nháp" ở đầu hộp thoại (một ô ý đề + nút phụ có biểu tượng sparkle, giống `#ai-draft` của Lộ trình), ẩn khi `available=false`; điền `#task-text`, `#task-keywords`; báo giá lượt trong gợi ý. Thông số giao diện theo khối Form đã có (S1–S16), mockup trước khi code.
- **Không làm:** AI không lưu, không bật/tắt đề, không thấy bài nói hay tên học viên.

## 4. Tệp bị ảnh hưởng

`src/aicefr/coach/task_draft.py` (mới), `src/aicefr/services/core/assessment/coach_api.py`, `src/aicefr/storage/metering_repository.py`, `src/aicefr/services/core/metering/facade.py`, `src/aicefr/api/templates/teach_tasks.html`, `src/aicefr/api/static/teach_tasks.js`, `tests/test_d106_task_draft.py` (mới), `docs/test/TEST_PLAN_D106.md` (mới), `docs/srs/SRS.md` (FR-105, lịch sử phiên bản, UC mở rộng của quản lý đề), `docs/sources/research-preparation/21_week1_decision_log.md` (dòng D106), `docs/sdd/diagrams/02_class.drawio`.

## 5. Thứ tự làm (AGENTS.md mục 2 + quy trình giao diện đã chốt)

1. Chủ dự án duyệt D106 và các điểm ở mục 6 → ghi D106 (APPROVED), FR-105 vào SRS, sơ đồ lớp.
2. `MeteredAction.TASK_DRAFT` + `coach/task_draft.py` + test đơn vị với nhà cung cấp giả.
3. Endpoint + test API (AC-105.1..105.6).
4. Giao diện: Codex dựng mockup khối "AI viết nháp" trong hộp thoại Thêm đề → Claude đo theo S1–S16 → `agy` code.
5. Kiểm: `ruff`, test tập trung, đo app thật; thử với một khoá thật do chủ dự án đặt trong `.env` (agent không đụng secret).

Ước lượng: 1–1,5 ngày sau khi duyệt.

## 6. Điểm chủ dự án cần chốt

1. Thêm `MeteredAction.TASK_DRAFT` riêng (khuyến nghị: lịch sử lượt rõ ràng) hay dùng lại `lesson_draft`.
2. Giá: chung giá bản nâng cấp như D075 (khuyến nghị, quản trị viên đã đặt được) hay rẻ hơn vì đầu ra ngắn.
3. Có làm luôn "gợi ý từ khoá cho đề đang có" (AC-105.2) trong vòng này không (khuyến nghị: có, cùng endpoint).
