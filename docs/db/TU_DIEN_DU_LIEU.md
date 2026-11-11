# Từ điển dữ liệu — kho của dịch vụ `core` (D045, D048)

| Thuộc tính | Giá trị |
| --- | --- |
| Phiên bản cấu trúc | 7 (collection `schema_migrations`) |
| Hệ quản trị | MongoDB 7.0 (MongoDB 8 không khởi động được trên nhân Linux 6.19 đến 7.0.13, lỗi SERVER-121912), một database `aicefr`, một người dùng `core` chỉ đọc ghi database đó (D048). Kiểm thử và chạy thử một máy dùng kho trong bộ nhớ (`mongomock`) |
| Cấu trúc chuẩn | [`schema_core.json`](schema_core.json) (collection và chỉ mục), sinh bằng `python -m aicefr.db_cli snapshot` |
| Sơ đồ | [`erd_core.mmd`](erd_core.mmd) |
| Ngày chốt | 14/10/2026; collection theo sơ đồ lớp từ 29/10/2026 (D060) |

## 1. Quy tắc đã chốt

1. **Database theo dịch vụ (D051).** `identity`, `assessment`, `billing` nằm trong `aicefr`; `learning` trong `aicefr_learning`, `metering` trong `aicefr_metering` khi đặt `AICEFR_LEARNING_DB` / `AICEFR_METERING_DB` (compose đặt sẵn), không đặt thì cùng `aicefr`. Phần này không ghi vào collection của phần khác; đọc chéo đi qua facade (SDD mục 4.18).
2. **Cấu trúc có phiên bản.** Phiên bản 1 là các collection và chỉ mục của D044, do repository tự tạo. Mọi thay đổi sau đó là một migration đánh số trong `src/aicefr/storage/migrations.py`, không sửa âm thầm `INDEXES` của repository. `tests/test_schema.py` so kho mới với `schema_core.json`: thay đổi thiếu migration thì kiểm thử đổ.
3. **Tự nâng cấp khi khởi động.** Dịch vụ `core` chạy `migrate` trước khi đọc kho. Lệnh tay: `python -m aicefr.db_cli status` và `python -m aicefr.db_cli migrate`.
4. **Kiểu dữ liệu.** Mỗi bảng cũ là một collection cùng tên, mỗi dòng một document cùng tên trường. Mã định danh là chuỗi có tiền tố (`p…`, `u…`, `l…`) hoặc UUID, nằm trong trường riêng có chỉ mục duy nhất; `_id` của MongoDB chỉ dùng nội bộ để giữ thứ tự chèn. Thời điểm là chuỗi ISO 8601 có múi giờ UTC. Giá trị đúng/sai là số 0/1. Dữ liệu có cấu trúc là document lồng (D104; trước đó là chuỗi JSON `*_json`). Tiền tính bằng đồng (`*_vnd`, số nguyên). Số tự tăng (`id` của `audit_log`, `review_id` của một lần duyệt) lấy từ collection `_counters`.
5. **Khoá và ràng buộc.** "PK" và "duy nhất" ở các bảng dưới là chỉ mục duy nhất. "FK" là quan hệ do mã giữ, không do kho ép. Phần hợp thành nằm trong document của gốc nên đi cùng gốc: xoá một bài nộp xoá luôn lịch sử duyệt và khoá duyệt nằm trong nó. Không có giao dịch nhiều document; ghi cần chống tranh chấp là một cập nhật có điều kiện trên một document.
6. **Dữ liệu cá nhân.** Collection đánh dấu **CN** chứa dữ liệu gắn với một người. Xoá dữ liệu một người (`/api/v1/admin/erase`) đi qua các collection này. Bản ghi âm không nằm trong kho mà ở volume `uploads`; kho chỉ giữ khoá tệp.

## 2. Collection theo phần

Từ D060 mỗi collection là một aggregate root của sơ đồ lớp (`docs/sdd/diagrams/02_class.drawio`). Phần hợp thành nằm trong document của gốc, ghi ở cột "Phần nhúng".

### 2.1. Tài khoản (`identity`)

| Collection | CN | Nội dung | Phần nhúng | Khoá và ràng buộc |
| --- | --- | --- | --- | --- |
| `account` | CN | Tài khoản: email đăng nhập (`email`, chữ thường, duy nhất), đã được Google xác minh chưa (`email_verified`), họ và tên (`full_name`) (D071; tài khoản trước D071 có thể chưa có), bút danh (từ D071 chỉ là mã nội bộ cho xuất dữ liệu nghiên cứu và nhật ký), băm mật khẩu (bcrypt, NFR-07), vai trò, khoá do đăng nhập sai, mật khẩu tạm, mục tiêu luyện mỗi ngày, hình đại diện (không còn mốc đồng ý điều khoản: D064 bỏ, migration 8 xoá trường `terms_accepted_at`). D079: `email_reminders` (nhắc học qua email, mặc định bật với email đã xác minh), `reminder_sent_on` (ngày đã gửi thư nhắc, mỗi ngày một thư). D081: không còn mã khôi phục; migration 12 xoá `recovery_hash`, `recovery_issued_at` | `identities`: liên kết Google, chỉ giữ băm của mã người dùng Google, không giữ email (D029). `seen_markers`: dấu "đã xem" của thanh bên (D028); `email_codes`: mã gửi qua email theo mục đích (`reset`, `verify`), chỉ lưu dạng băm, hạn 10 phút, số lần thử | PK `account_id`; `pseudonym` duy nhất; (`identities.provider`, `identities.subject_hash`) duy nhất trên các tài khoản có liên kết |
| `session` | CN | Phiên đăng nhập: băm của mã phiên (`sid` trong JWT, D091), hạn, thiết bị, cách đăng nhập | | PK `token_hash`; FK `account_id` |
| `push_subscription` | CN | Trình duyệt nhận thông báo đẩy của một tài khoản (D088): địa chỉ `endpoint` trên dịch vụ push của trình duyệt (Google, Mozilla, Apple, Microsoft), khoá công khai `p256dh` và bí mật `auth` để mã hoá thông báo, lúc đăng ký. Một tài khoản nhiều trình duyệt, tối đa 10; đăng xuất, tắt thông báo hay dịch vụ push báo trình duyệt không còn thì xoá; xoá dữ liệu người học thì xoá hết. Migration 17 tạo collection | | Duy nhất `endpoint`; chỉ mục `account_id` |
| `audit_log` | CN | Nhật ký kiểm toán: ai làm gì, với đối tượng nào, phần nào ghi (`service`). Mỗi database có một collection này cho phần dùng nó | | PK `id` tự tăng |

### 2.2. Đánh giá và duyệt (`assessment`)

| Collection | CN | Nội dung | Phần nhúng | Khoá và ràng buộc |
| --- | --- | --- | --- | --- |
| `task` | | Đề bài đánh giá: lời đề, thời lượng, từ khoá chủ đề, band A1–C2 (ngân hàng 36 đề, giảng viên thêm được; ai thêm thì nhật ký kiểm toán ghi, D103); đề bị tắt có `active = 0`, P5 có `retired = D076`. D078: tên đề là "Đề <band>"; migration 11 xoá trường `part`. D083: không còn đề luyện tập; migration 14 xoá chúng và các trường `purpose`, `criterion`, `missions_json`, `tips_json`, `reference_text` | | PK `task_id`; chỉ mục `active` |
| `response` | CN | Một bài nộp đánh giá (D083: không còn lượt luyện tập; migration 14 xoá chúng cùng bản ghi âm và trường `purpose`). D104: document chính là báo cáo, lưu thẳng các trường của hợp đồng `Response`: `status`, `qc`, `asr`, `features`, `assessment` (điểm 0–6, band, tiêu chí, `teacher_verified`, phiên bản mô hình), `reasons`, `config_version`, `prompt_version`; không còn chuỗi `report_json` hay các cột chép lại điểm, band, xác nhận. Thêm khoá bản ghi âm, khoá duyệt `review_lock` (ai đang giữ, tới lúc nào, FR-30; trước D104 là collection `review_session`), bản nâng cấp lên band kế tiếp nếu người học đã yêu cầu (`coach_upgrade`: văn bản, các chỗ đổi, các cụm từ và nghĩa; D069, D070) | `reviews`: mỗi lần giảng viên giữ hay đổi điểm, band, kèm lý do. `replay_labels`: câu trả lời khi tự nghe lại (D056), không có audio hay bản chép.| PK `response_id` |
| `classroom` | | Lớp học (D054): tên, mã tham gia 6 ký tự, đã lưu trữ chưa | `teacher_ids`: mã tài khoản các giảng viên phụ trách, do quản trị viên phân công (D071, migration 9 thay `teacher_id`); giảng viên chỉ xem và chấm bài của thành viên lớp mình. `members`: mã tài khoản theo thứ tự vào lớp. `assignments`: đề giao cho lớp, hạn nộp (ngày theo giờ Việt Nam và mốc UTC cuối ngày), ghi chú; bài nộp là chính `response` của đề đó làm sau lúc giao | Duy nhất `class_id`; duy nhất `code` |

### 2.3. Lộ trình và bài học (`learning`)

| Collection | CN | Nội dung | Phần nhúng | Khoá và ràng buộc |
| --- | --- | --- | --- | --- |
| `path` | | Lộ trình: tên, band từ–đến, trạng thái (nháp, xuất bản, lưu trữ), lúc tạo. D103 bỏ `built_in`, D105 bỏ `updated_at` | `units`: chặng với chức năng giao tiếp, band, tiêu chí, chủ đề; thứ tự trong danh sách là thứ tự chặng (D103 bỏ `position`) | PK `path_id` |
| `lesson` | | Bài học của một chặng: bản nháp (`draft`, một document; D104), phiên bản đang xuất bản, đã lưu trữ chưa; "có sửa đổi chưa xuất bản" tính ra bằng cách so bản nháp với phiên bản đang xuất bản (D105 bỏ `draft_changed`). Document riêng vì lớn dần theo phiên bản | `versions`: mỗi lần xuất bản là một bản bất biến (`lesson`); lượt luyện ghi phiên bản đã dùng. `media`: âm thanh mẫu và hình giảng viên tải lên, trỏ tới tệp | PK `lesson_id`; FK `unit_id` |
| `attempt` | CN | Một lượt nói ở một bước: kết quả đo (`result`, một document; D104), khoá bản ghi âm, sửa của giảng viên (`override`). Bước, vòng, thời gian nói, bộ luật và đạt hay chưa đọc từ `result` cùng `override`, không chép ra ngoài (D105) | | PK `attempt_id` |
| `review_item` | CN | Hàng ôn tập ngắt quãng: từ hoặc bài nói cần ôn, hộp Leitner, ngày đến hạn. D089: từ đưa vào ôn từ phần luyện lại từ của một bài nói không có bài học (`lesson_id`, `step_id` rỗng) và trỏ về `drill_id`. D104: cụm từ của Sổ cụm từ là loại `phrase`, `word` là cụm từ đã chuẩn hoá, không bao giờ xong; không vào hàng ôn của bài học. D105 bỏ `updated_at` | | PK `item_id`; duy nhất theo người, loại, bài, bước, từ |
| `word_drill` | CN | Một từ máy nghe chưa rõ trong một bài nói mà người học đã nói lại (D089): từ (D105 bỏ vị trí `word_index`, không ai đọc), cụm từ để nói lại, số lượt rõ liên tiếp (`streak`), đã rõ hai lần liền chưa (`passed`). Chỉ tạo khi người học nói lại lần đầu; bản ghi âm của các lượt không lưu. Xoá dữ liệu người học thì xoá hết. Migration 18 tạo collection | `takes`: tối đa 20 lượt gần nhất, mỗi lượt ghi rõ hay chưa, máy nghe thành gì, lúc nói | PK `drill_id`; duy nhất (`account_id`, `response_id`, `word`); chỉ mục (`account_id`, `passed`, `updated_at`) |
| `drill_passage` | CN | Một đoạn đọc viết quanh 3–5 từ người học đang luyện dở (D090): `drill_ids` của các từ (chữ đọc từ chính các drill, D105), đoạn văn, nguồn (`model`: mô hình ngôn ngữ viết, học viên trả `AICEFR_PRICE_PASSAGE_RUNS` lượt; `phrases`: ghép từ cụm từ của chính người học, miễn phí). Chỉ các từ và band được gửi cho mô hình. Đọc lại không viết đoạn mới. Bản ghi âm của các lần đọc không lưu. Xoá dữ liệu người học thì xoá hết. Migration 19 tạo collection | `takes`: tối đa 20 lần đọc gần nhất, mỗi lần ghi từ nào máy nghe rõ (`clear`), từ nào chưa (`unclear`), lúc đọc | PK `passage_id`; chỉ mục (`account_id`, `created_at`) |
| `achievement` | CN | Thành tựu đã đạt (D032; D103 gỡ dấu đã xem) | | PK (`account_id`, `code`) |
| `learning_plan` | CN | Lộ trình do model gợi ý (D046): mục tiêu (`goal`) và kết quả (`plan`, không chép lại mục tiêu; D105), hai document (D104); đề xuất của giảng viên đã lưu thành lộ trình thì `active` về 0 (D103 gỡ `path_id`). D074: mục tiêu ghi band bắt đầu và band mục tiêu người học chọn (`band_from`, `band_to`); lộ trình giảng viên giao (phiên bản `teacher-assigned`) ghi thêm người giao (`assigned_by`), lộ trình gốc (`path_id`, `path_title`) | | PK `plan_id`; chỉ mục (`account_id`, `active`) |

### 2.4. Gói dịch vụ (`billing`)

| Collection | CN | Nội dung | Phần nhúng | Khoá và ràng buộc |
| --- | --- | --- | --- | --- |
| `order` | | Đơn nạp lượt (D053, D075): `runs` là số lượt (`seats` ở đơn trước D075), `amount_vnd` số tiền, `created_by` người mua (học viên hay giảng viên), trạng thái, hạn, `credited_at` lúc lượt vào ví. D104 gộp lại `payment` của D084: mã checkout của cổng (`checkout_ref`), mã giao dịch (`reference`), lúc chốt (`settled_at`). Không giữ số thẻ, tài khoản ngân hàng hay tên người trả (BR-32). Collection `license` của D033 không còn được tạo hay đọc (D075) | `events`: những gì cổng báo về đơn, tin trùng được đếm vào lần đầu (D035) | PK `order_id`; chỉ mục `checkout_ref` |

### 2.5. Tính lượt (`metering`, D049)

Chỉ có dữ liệu trên bản triển khai bật `AICEFR_METERING`, tức kênh NetID. Bản của trường và nghiên cứu không ghi gì vào đây (BR-29, BR-30).

| Collection | CN | Nội dung | Phần nhúng | Khoá và ràng buộc |
| --- | --- | --- | --- | --- |
| `price_list` | | Bảng giá do quản trị viên đặt trên dashboard (D078): giá bài nói đến 1 phút, mỗi phút thêm, hệ số bài luyện, giá một lần AI viết lại, IDPoint mỗi lượt, lượt miễn phí mỗi tháng, (D094) lượt mỗi phút nói của bản ghi lộ trình, số bản miễn phí mỗi ngày và trần mỗi ngày, phiên bản `price-admin-N`, lúc đổi. Ai đổi và các phiên bản trước nằm trong nhật ký kiểm toán (`metering.prices`; D103, D105). Chưa có thì dùng giá trong cấu hình máy chủ | `packs`: gói lượt đang bán (số lượt, giá đồng) | Một document `_id = current` |
| `wallet` | CN | Ví của một tài khoản: số lượt trả trước (1/1000 lượt), chu kỳ hiện tại (bắt đầu ngày 16) và số lượt miễn phí đã dùng trong chu kỳ đó; từ D094 thêm ngày giờ Việt Nam đang đếm (`lesson_day`), số bản ghi lộ trình đã đo trong ngày đó (`lesson_used`) và số bản miễn phí trong số đó (`lesson_free_used`) | `grants`: mỗi lần cộng lượt, nguồn (`admin`, `order` cho gói lượt mua qua cổng (D053), sau này `netid`), số tham chiếu, ai cộng; một khoản nạp chỉ cộng một lần | Duy nhất `user_ref` |
| `ledger` | CN | Sổ lượt: mỗi bài một bút toán, và mỗi bản nâng cấp do AI viết một bút toán (D072, khoá `upgrade-<mã bài>`), gồm hành động (`assessment`, `practice`, `upgrade`, `lesson_draft` từ D075: bản soạn bài của giảng viên, không gắn bài nào; `drill_passage` từ D090: một đoạn đọc, khoá `passage-<mã đoạn>`; `lesson` từ D094: một bản ghi trong lộ trình, khoá `lesson-<ngày><ngẫu nhiên>`, kèm `day` và `free_slot`), phần lấy từ lượt miễn phí và từ ví (cộng lại là số giữ chỗ, D103), số đã thu, trạng thái (`held` → `charged` hoặc `released`), chu kỳ, lúc chốt. D105 bỏ số token. Không chứa audio hay transcript | | Duy nhất `entry_id`; duy nhất (`key`, `action`): mỗi bài thu một lần |

### 2.6. Hệ thống

| Collection | CN | Nội dung | Khoá và ràng buộc |
| --- | --- | --- | --- |
| `system` | | Mỗi database một collection: khoá ký của bản triển khai (`identity.secret.*`, D036), cấu hình đang dùng có phiên bản (`assessment.*`: ngưỡng QC, mô hình chấm, sai số đo D042, gói của mô hình ngôn ngữ `assessment.coach_tier` D073: miễn phí hay trả phí và ngân sách USD/ngày, kèm người đổi và thời điểm), cài đặt gói của trường (`billing.*`), dấu nâng cấp một lần của dữ liệu mẫu (`learning.*`), bộ đếm dùng mô hình ngôn ngữ mỗi ngày của nhà cung cấp (`coach_usage.<YYYY-MM-DD>`, D072: số yêu cầu gửi đi gồm cả lỗi và gọi lại, số bản soạn bài của giảng viên `drafts` (D075), tách theo gói (D073: `free_requests`, `paid_requests`, `paid_cost_usd`), bản viết xong, lỗi theo lý do, số lần bị từ chối vì giới hạn chung hay mỗi người, token vào/ra, chi phí ước tính USD, danh sách `account_id` đã dùng; không chứa nội dung bài) | PK `key` |
| `schema_migrations` | | Các phiên bản cấu trúc đã áp dụng và thời điểm (nội bộ, không trong `schema_core.json`) | Duy nhất `version` |

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
