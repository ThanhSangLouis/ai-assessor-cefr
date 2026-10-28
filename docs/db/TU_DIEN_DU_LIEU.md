# Từ điển dữ liệu — kho của dịch vụ `core` (D045, D048)

| Thuộc tính | Giá trị |
| --- | --- |
| Phiên bản cấu trúc | 3 (collection `schema_migrations`) |
| Hệ quản trị | MongoDB 7.0 (MongoDB 8 không khởi động được trên nhân Linux 6.19 đến 7.0.13, lỗi SERVER-121912), một database `aicefr`, một người dùng `core` chỉ đọc ghi database đó (D048). Kiểm thử và chạy thử một máy dùng kho trong bộ nhớ (`mongomock`) |
| Cấu trúc chuẩn | [`schema_core.json`](schema_core.json) (collection và chỉ mục), sinh bằng `python -m aicefr.db_cli snapshot` |
| Sơ đồ | [`erd_core.mmd`](erd_core.mmd) |
| Ngày chốt | 14/10/2026 |

## 1. Quy tắc đã chốt

1. **Database theo dịch vụ (D051).** `identity`, `assessment`, `billing` nằm trong `aicefr`; `learning` trong `aicefr_learning`, `metering` trong `aicefr_metering` khi đặt `AICEFR_LEARNING_DB` / `AICEFR_METERING_DB` (compose đặt sẵn), không đặt thì cùng `aicefr`. Phần này không ghi vào collection của phần khác; đọc chéo đi qua facade (SDD mục 4.18).
2. **Cấu trúc có phiên bản.** Phiên bản 1 là các collection và chỉ mục của D044, do repository tự tạo. Mọi thay đổi sau đó là một migration đánh số trong `src/aicefr/storage/migrations.py`, không sửa âm thầm `INDEXES` của repository. `tests/test_schema.py` so kho mới với `schema_core.json`: thay đổi thiếu migration thì kiểm thử đổ.
3. **Tự nâng cấp khi khởi động.** Dịch vụ `core` chạy `migrate` trước khi đọc kho. Lệnh tay: `python -m aicefr.db_cli status` và `python -m aicefr.db_cli migrate`.
4. **Kiểu dữ liệu.** Mỗi bảng cũ là một collection cùng tên, mỗi dòng một document cùng tên trường. Mã định danh là chuỗi có tiền tố (`p…`, `u…`, `l…`) hoặc UUID, nằm trong trường riêng có chỉ mục duy nhất; `_id` của MongoDB chỉ dùng nội bộ để giữ thứ tự chèn. Thời điểm là chuỗi ISO 8601 có múi giờ UTC. Giá trị đúng/sai là số 0/1. Dữ liệu có cấu trúc là chuỗi JSON (`*_json`). Tiền tính bằng đồng (`*_vnd`, số nguyên). Số tự tăng (`id` của `audit_log`, `review_action`, …) lấy từ collection `_counters`.
5. **Khoá và ràng buộc.** "PK" và "duy nhất" ở các bảng dưới là chỉ mục duy nhất. "FK" là quan hệ do mã giữ, không do kho ép: xoá một bài nộp tự xoá lịch sử duyệt, khoá duyệt, phiếu chấm mù, điểm chấm mù và dấu "đã xem kết quả máy" của nó. Không có giao dịch nhiều document; ghi cần chống tranh chấp là một cập nhật có điều kiện trên một document.
6. **Dữ liệu cá nhân.** Collection đánh dấu **CN** chứa dữ liệu gắn với một người. Xoá dữ liệu một người (`/api/v1/admin/erase`) đi qua các collection này. Bản ghi âm không nằm trong kho mà ở volume `uploads`; kho chỉ giữ khoá tệp.

## 2. Collection theo phần

### 2.1. Tài khoản và đồng thuận (`identity`)

| Bảng | CN | Nội dung | Khoá và ràng buộc |
| --- | --- | --- | --- |
| `account` | CN | Tài khoản: bút danh, băm mật khẩu (scrypt), vai trò, khoá do đăng nhập sai, mật khẩu tạm, mục tiêu luyện mỗi ngày, hình đại diện, thời điểm đồng ý điều khoản sử dụng (`terms_accepted_at`, D058) | PK `account_id`; `pseudonym` duy nhất |
| `auth_sessions` | CN | Phiên đăng nhập: băm của mã phiên, hạn, thiết bị, cách đăng nhập | PK `token_hash`; FK `account_id` |
| `account_identity` | CN | Liên kết Google: băm của mã người dùng Google, không giữ email | PK (`provider`, `subject_hash`); mỗi tài khoản một liên kết mỗi nhà cung cấp |
| `server_secret` | | Khoá ký của bản triển khai (cookie luồng Google, D036) | PK `name` |
| `audit_log` | CN | Nhật ký kiểm toán: ai làm gì, với đối tượng nào, phần nào ghi (`service`) | PK `id` tự tăng |

### 2.2. Đánh giá, duyệt và nghiên cứu (`assessment`)

| Bảng | CN | Nội dung | Khoá và ràng buộc |
| --- | --- | --- | --- |
| `task` | | Đề bài đánh giá và nhiệm vụ luyện tập: lời đề, thời lượng, từ khoá chủ đề, tiêu chí, band, nhiệm vụ | PK `task_id` |
| `response` | CN | Một bài nộp: trạng thái chấm, điểm tổng 0–6, band, phiên bản mô hình và cấu hình, toàn bộ báo cáo (`report_json`), khoá bản ghi âm, mục đích (đánh giá hay luyện tập) | PK `response_id` |
| `review_action` | CN | Mỗi lần giảng viên đổi điểm hay band, kèm lý do | PK `id`; FK `response_id` |
| `review_lock` | | Khoá bài đang được một giảng viên duyệt | PK và FK `response_id` |
| `review_session` | CN | Phiên duyệt: mở lúc nào, quyết định lúc nào, hành động gì (D041) | PK `id` |
| `seen_marker` | | Dấu "đã xem" của từng người (thanh bên, kết quả mới) | PK (`account_id`, `marker`) |
| `app_config` | | Cấu hình đang dùng: ngưỡng QC, mô hình chấm, sai số đo (D042), có phiên bản | PK `key` |
| `rating_batch` | | Đợt chấm mù hai người (D030), có hạt giống chia phiếu | PK `batch_id` |
| `rating_assignment` | | Phiếu chấm mù: bài nào, giám khảo nào, thứ tự | PK `assignment_id`; FK `batch_id`, `response_id`; mỗi bài một giám khảo một lần |
| `research_rating` | | Điểm của giám khảo cho một phiếu, hoặc lý do không chấm được | PK và FK `assignment_id` |
| `machine_seen` | | Giám khảo nào đã thấy điểm máy của bài nào, qua đường nào | PK (`account_id`, `response_id`) |
| `study` | | Thực nghiệm phản hồi (D040): trạng thái, mốc kết thúc giai đoạn đo | PK `study_id` |
| `study_participant` | CN | Người tham gia: nhóm, mã người tham gia, ngày rời | PK (`study_id`, `account_id`) |
| `study_survey` | CN | Câu trả lời khảo sát | PK (`study_id`, `account_id`) |
| `classroom` | | Lớp của giảng viên (D054): tên, mã tham gia 6 ký tự, đã lưu trữ chưa | Duy nhất `class_id`; duy nhất `code` |
| `class_member` | | Ai ở lớp nào, vào lúc nào | Duy nhất (`class_id`, `account_id`) |
| `assignment` | | Đề đánh giá giao cho một lớp, hạn nộp (ngày theo giờ Việt Nam và mốc UTC cuối ngày), ghi chú. Bài nộp không lưu ở đây: là chính `response` của đề đó làm sau lúc giao | Duy nhất `assignment_id` |
| `replay_label` | CN | Câu trả lời khi tự nghe lại (D056): đoạn nào, nguồn của đoạn (máy chọn hay đối chứng ngẫu nhiên), lựa chọn, câu "định nói gì". Không có audio hay bản chép | Duy nhất (`response_id`, `moment_id`) |

### 2.3. Lộ trình và bài học (`learning`)

| Bảng | CN | Nội dung | Khoá và ràng buộc |
| --- | --- | --- | --- |
| `lesson_path` | | Lộ trình: tên, band từ–đến, trạng thái (nháp, xuất bản, lưu trữ) | PK `path_id` |
| `lesson_unit` | | Chặng trong lộ trình: chức năng giao tiếp, band, tiêu chí, chủ đề, thứ tự | PK `unit_id`; FK `path_id` xoá dây chuyền |
| `lesson` | | Bài học: bản nháp (`draft_json`), phiên bản đã xuất bản, đã lưu trữ chưa | PK `lesson_id`; FK `unit_id` xoá dây chuyền |
| `lesson_version` | | Mỗi lần xuất bản là một bản bất biến; lượt luyện ghi phiên bản đã dùng | PK (`lesson_id`, `version`) |
| `lesson_media` | | Âm thanh mẫu và hình của bài học, trỏ tới tệp trong volume | PK `media_key` |
| `lesson_meta` | | Dấu nâng cấp một lần của dữ liệu mẫu | PK `key` |
| `step_attempt` | CN | Một lượt nói ở một bước: kết quả đo, đạt hay chưa, thời gian nói, khoá bản ghi âm, sửa của giảng viên | PK `attempt_id` |
| `review_item` | CN | Hàng ôn tập ngắt quãng: từ hoặc bài nói cần ôn, hộp Leitner, ngày đến hạn | PK `item_id`; duy nhất theo người, loại, bài, bước, từ |
| `achievement` | CN | Thành tựu đã đạt và đã xem chưa (D032) | PK (`account_id`, `code`) |
| `learning_plan` | CN | Lộ trình do model gợi ý (D046): mục tiêu, kết quả, phiên bản model; với giảng viên còn ghi lộ trình nháp đã lưu (`path_id`) | PK `plan_id`; chỉ mục (`account_id`, `active`) |

### 2.4. Gói dịch vụ (`billing`)

| Bảng | CN | Nội dung | Khoá và ràng buộc |
| --- | --- | --- | --- |
| `billing_order` | | Đơn mua, gia hạn, nâng cấp: số chỗ, số tháng, các khoản tiền, cổng, trạng thái. Đơn `kind = credits` là gói lượt của một sinh viên (D053): `seats` là số lượt, `created_by` là người mua, `credited_at` là lúc lượt vào ví | PK `order_id` |
| `billing_license` | | Giấy phép đang có hiệu lực: gói, số chỗ, thời hạn, nguồn (dùng thử, đơn, mã) | PK `license_id` |
| `billing_event` | | Thông báo từ cổng thanh toán, gộp các lần trùng (D035) | PK `event_id` |
| `billing_setting` | | Cài đặt gói của trường | PK `key` |

### 2.5. Tính lượt (`metering`, D049)

Chỉ có dữ liệu trên bản triển khai bật `AICEFR_METERING`, tức kênh NetID. Bản của trường và nghiên cứu không ghi gì vào đây (BR-29, BR-30).

| Collection | CN | Nội dung | Khoá và ràng buộc |
| --- | --- | --- | --- |
| `usage_ledger` | CN | Sổ lượt: mỗi bài một bút toán gồm số giữ chỗ, phần lấy từ lượt miễn phí và từ ví, số đã thu, trạng thái (`held` → `charged` hoặc `released`), chu kỳ, phiên bản bảng giá. Không chứa audio hay transcript | Duy nhất `entry_id`; duy nhất (`key`, `action`): mỗi bài thu một lần |
| `credit_wallet` | CN | Số lượt trả trước của mỗi tài khoản, tính bằng 1/10 lượt | Duy nhất `user_ref` |
| `free_quota` | CN | Số lượt miễn phí đã dùng trong mỗi chu kỳ (bắt đầu ngày 16) | Duy nhất (`user_ref`, `period`) |
| `credit_grant` | CN | Mỗi lần cộng lượt: nguồn (`admin`, `order` cho gói lượt mua qua cổng thanh toán (D053), sau này `netid`), số tham chiếu, ai cộng | Duy nhất `grant_id`; duy nhất (`source`, `ref`): một khoản nạp chỉ cộng một lần |

### 2.6. Hệ thống

| Bảng | CN | Nội dung | Khoá và ràng buộc |
| --- | --- | --- | --- |
| `schema_migrations` | | Các phiên bản cấu trúc đã áp dụng và thời điểm | Duy nhất `version` |

## 3. Đổi cấu trúc

1. Thêm một `Migration(version=N+1, name=..., apply=...)` vào cuối `MIGRATIONS` trong `src/aicefr/storage/migrations.py`. Hàm `apply` phải chạy lại được: tạo chỉ mục bằng `ensure_indexes`, sửa dữ liệu bằng cập nhật có điều kiện.
2. Sinh lại cấu trúc chuẩn: `python -m aicefr.db_cli snapshot > docs/db/schema_core.json`.
3. Thêm collection mới vào từ điển này và vào `erd_core.mmd`.
4. Chạy `pytest tests/test_schema.py`, kể cả với `AICEFR_TEST_MONGO=mongodb://...` để kiểm trên MongoDB thật.

Không sửa hay xoá một migration đã phát hành: kho đã chạy nó sẽ không chạy lại.

## 4. Sao lưu và khôi phục

- Máy chủ: `mongodump --db aicefr --archive --gzip` trong container `mongo`, cộng volume `uploads`. Kịch bản đầy đủ ở `deploy/vps/backup.sh` và `deploy/vps/restore.sh` (D047, D048).
- Kho nhỏ, không có công cụ MongoDB: `python -m aicefr.maintenance_cli backup --to backups/aicefr.json` (JSON mở rộng, mọi collection) và `restore --from …` vào một kho rỗng.
- Sau khi khôi phục một bản cũ, chạy `python -m aicefr.db_cli migrate` (hoặc khởi động `core`) để đưa kho lên phiên bản mới nhất.
