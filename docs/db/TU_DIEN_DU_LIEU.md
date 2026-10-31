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
4. **Kiểu dữ liệu.** Mỗi bảng cũ là một collection cùng tên, mỗi dòng một document cùng tên trường. Mã định danh là chuỗi có tiền tố (`p…`, `u…`, `l…`) hoặc UUID, nằm trong trường riêng có chỉ mục duy nhất; `_id` của MongoDB chỉ dùng nội bộ để giữ thứ tự chèn. Thời điểm là chuỗi ISO 8601 có múi giờ UTC. Giá trị đúng/sai là số 0/1. Dữ liệu có cấu trúc là chuỗi JSON (`*_json`). Tiền tính bằng đồng (`*_vnd`, số nguyên). Số tự tăng (`id` của `audit_log`, `review_id` của một lần duyệt) lấy từ collection `_counters`.
5. **Khoá và ràng buộc.** "PK" và "duy nhất" ở các bảng dưới là chỉ mục duy nhất. "FK" là quan hệ do mã giữ, không do kho ép. Phần hợp thành nằm trong document của gốc nên đi cùng gốc: xoá một bài nộp xoá luôn lịch sử duyệt, khoá duyệt và dấu "đã xem kết quả máy" nằm trong nó; các phiếu chấm mù về bài đó được rút khỏi đợt chấm. Không có giao dịch nhiều document; ghi cần chống tranh chấp là một cập nhật có điều kiện trên một document.
6. **Dữ liệu cá nhân.** Collection đánh dấu **CN** chứa dữ liệu gắn với một người. Xoá dữ liệu một người (`/api/v1/admin/erase`) đi qua các collection này. Bản ghi âm không nằm trong kho mà ở volume `uploads`; kho chỉ giữ khoá tệp.

## 2. Collection theo phần

Từ D060 mỗi collection là một aggregate root của sơ đồ lớp (`docs/sdd/diagrams/02_class.drawio`). Phần hợp thành nằm trong document của gốc, ghi ở cột "Phần nhúng".

### 2.1. Tài khoản (`identity`)

| Collection | CN | Nội dung | Phần nhúng | Khoá và ràng buộc |
| --- | --- | --- | --- | --- |
| `account` | CN | Tài khoản: bút danh, băm mật khẩu (bcrypt, NFR-07), băm mã khôi phục và thời điểm cấp (`recovery_hash`, `recovery_issued_at`, D065; không bao giờ lưu mã rõ), vai trò, khoá do đăng nhập sai, mật khẩu tạm, mục tiêu luyện mỗi ngày, hình đại diện (không còn mốc đồng ý điều khoản: D064 bỏ, migration 8 xoá trường `terms_accepted_at`) | `identities`: liên kết Google, chỉ giữ băm của mã người dùng Google, không giữ email (D029). `seen_markers`: dấu "đã xem" của thanh bên (D028) | PK `account_id`; `pseudonym` duy nhất; (`identities.provider`, `identities.subject_hash`) duy nhất trên các tài khoản có liên kết |
| `session` | CN | Phiên đăng nhập: băm của mã phiên, hạn, thiết bị, cách đăng nhập | | PK `token_hash`; FK `account_id` |
| `audit_log` | CN | Nhật ký kiểm toán: ai làm gì, với đối tượng nào, phần nào ghi (`service`). Mỗi database có một collection này cho phần dùng nó | | PK `id` tự tăng |

### 2.2. Đánh giá, duyệt và nghiên cứu (`assessment`)

| Collection | CN | Nội dung | Phần nhúng | Khoá và ràng buộc |
| --- | --- | --- | --- | --- |
| `task` | | Đề bài đánh giá và nhiệm vụ luyện tập: lời đề, thời lượng, từ khoá chủ đề, tiêu chí, band, nhiệm vụ | | PK `task_id` |
| `response` | CN | Một bài nộp: trạng thái chấm, điểm tổng 0–6, band, phiên bản mô hình và cấu hình, toàn bộ báo cáo (`report_json`), khoá bản ghi âm, mục đích (đánh giá hay luyện tập), bản nâng cấp lên band kế tiếp nếu người học đã yêu cầu (`coach_upgrade`: văn bản, các chỗ đổi, nhà cung cấp, thời điểm; D069), mỗi cụm từ trong đó kèm trạng thái ôn của Sổ cụm từ (`box`, `due`, `reviews`, `reviewed_at`; D070) | `reviews`: mỗi lần giảng viên giữ hay đổi điểm, band, kèm lý do và lúc mở bài. `review_lock`: ai đang duyệt, tới lúc nào. `review_visits`: mỗi lần mở bài để duyệt và kết thúc thế nào (D041). `replay_labels`: câu trả lời khi tự nghe lại (D056), không có audio hay bản chép. `machine_seen`: ai đã thấy điểm máy của bài, qua đường nào | PK `response_id` |
| `rating_batch` | | Đợt chấm mù hai người (D030): tên, hạt giống chia phiếu, đã đóng chưa (`closed`) | `ratings`: mỗi phiếu là một `Rating` (bài nào, giám khảo nào, ô thứ mấy, thứ tự, lúc mở) cùng điểm đã chấm hoặc lý do không chấm được | PK `batch_id` |
| `study` | | Thực nghiệm phản hồi (D040): trạng thái (`running`, `survey`, `closed`), mốc kết thúc giai đoạn đo | `participants`: nhóm, mã người tham gia, ngày rời, câu trả lời khảo sát | PK `study_id` |
| `classroom` | | Lớp của giảng viên (D054): tên, mã tham gia 6 ký tự, đã lưu trữ chưa | `members`: mã tài khoản theo thứ tự vào lớp. `assignments`: đề giao cho lớp, hạn nộp (ngày theo giờ Việt Nam và mốc UTC cuối ngày), ghi chú; bài nộp là chính `response` của đề đó làm sau lúc giao | Duy nhất `class_id`; duy nhất `code` |

### 2.3. Lộ trình và bài học (`learning`)

| Collection | CN | Nội dung | Phần nhúng | Khoá và ràng buộc |
| --- | --- | --- | --- | --- |
| `path` | | Lộ trình: tên, band từ–đến, trạng thái (nháp, xuất bản, lưu trữ) | `units`: chặng với chức năng giao tiếp, band, tiêu chí, chủ đề, thứ tự | PK `path_id` |
| `lesson` | | Bài học của một chặng: bản nháp (`draft_json`), phiên bản đang xuất bản, đã lưu trữ chưa. Document riêng vì lớn dần theo phiên bản | `versions`: mỗi lần xuất bản là một bản bất biến; lượt luyện ghi phiên bản đã dùng. `media`: âm thanh mẫu và hình giảng viên tải lên, trỏ tới tệp | PK `lesson_id`; FK `unit_id` |
| `attempt` | CN | Một lượt nói ở một bước: kết quả đo, đạt hay chưa, thời gian nói, khoá bản ghi âm, sửa của giảng viên | | PK `attempt_id` |
| `review_item` | CN | Hàng ôn tập ngắt quãng: từ hoặc bài nói cần ôn, hộp Leitner, ngày đến hạn | | PK `item_id`; duy nhất theo người, loại, bài, bước, từ |
| `achievement` | CN | Thành tựu đã đạt và đã xem chưa (D032) | | PK (`account_id`, `code`) |
| `learning_plan` | CN | Lộ trình do model gợi ý (D046): mục tiêu, kết quả, phiên bản model; với giảng viên còn ghi lộ trình nháp đã lưu (`path_id`) | | PK `plan_id`; chỉ mục (`account_id`, `active`) |

### 2.4. Gói dịch vụ (`billing`)

| Collection | CN | Nội dung | Phần nhúng | Khoá và ràng buộc |
| --- | --- | --- | --- | --- |
| `order` | | Đơn mua, gia hạn, nâng cấp, hạ cấp (`kind`): số chỗ, số tháng, các khoản tiền, cổng, trạng thái. Đơn `kind = credits` là gói lượt của một sinh viên (D053): `seats` là số lượt, `created_by` là người mua, `credited_at` là lúc lượt vào ví | `events`: thông báo từ cổng thanh toán, gộp các lần trùng (D035) | PK `order_id` |
| `license` | | Giấy phép: gói, số chỗ, thời hạn, nguồn (dùng thử, đơn, mã). Collection riêng vì giấy phép dùng thử hay từ mã không có đơn | | PK `license_id` |

### 2.5. Tính lượt (`metering`, D049)

Chỉ có dữ liệu trên bản triển khai bật `AICEFR_METERING`, tức kênh NetID. Bản của trường và nghiên cứu không ghi gì vào đây (BR-29, BR-30).

| Collection | CN | Nội dung | Phần nhúng | Khoá và ràng buộc |
| --- | --- | --- | --- | --- |
| `wallet` | CN | Ví của một tài khoản: số lượt trả trước (1/1000 lượt), chu kỳ hiện tại (bắt đầu ngày 16) và số lượt miễn phí đã dùng trong chu kỳ đó | `grants`: mỗi lần cộng lượt, nguồn (`admin`, `order` cho gói lượt mua qua cổng (D053), sau này `netid`), số tham chiếu, ai cộng; một khoản nạp chỉ cộng một lần | Duy nhất `user_ref` |
| `ledger` | CN | Sổ lượt: mỗi bài một bút toán gồm mục đích (`assessment`, `practice`), số giữ chỗ, phần lấy từ lượt miễn phí và từ ví, số đã thu, trạng thái (`held` → `charged` hoặc `released`), chu kỳ, phiên bản bảng giá. Không chứa audio hay transcript | | Duy nhất `entry_id`; duy nhất (`key`, `action`): mỗi bài thu một lần |

### 2.6. Hệ thống

| Collection | CN | Nội dung | Khoá và ràng buộc |
| --- | --- | --- | --- |
| `system` | | Mỗi database một collection: khoá ký của bản triển khai (`identity.secret.*`, D036), cấu hình đang dùng có phiên bản (`assessment.*`: ngưỡng QC, mô hình chấm, sai số đo D042), cài đặt gói của trường (`billing.*`), dấu nâng cấp một lần của dữ liệu mẫu (`learning.*`) | PK `key` |
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
