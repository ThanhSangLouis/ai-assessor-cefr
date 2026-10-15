# SCRUM-70 — Implementation review

Baseline lịch sử: `3b2d2b78ba5bb35bd162b8f3e5de21ade946d237`.
Tham chiếu chức năng cố định: `40907cc35b3d04408f9a8713f16d9be99f4cd6c7`.
Actual parent: `a4c119fdbcf5e17a09372099cb1dc07de853b698`, tree giống `51eff1f`.

Codex điều phối/review; GPT-6 Luna triển khai theo quyền task-local của user. Không thay verdict SDD toàn cục hoặc reviewer acceptance. Review actual source, test và correction; kết quả cuối xem [final verification](../evidence/scrum-70/final-verification.md).

## Findings và xử lý

| Finding | Mức | Kết quả |
| --- | --- | --- |
| Retry review bỏ qua review_id trong URL, dùng binding của key cũ | MAJOR | RESOLVED: exact owned review lookup và so source kind/attempt/content; owned mismatch409, unknown/foreign404; đúng URL replay sau advance giữ attempt và lịch cũ. Regression cả practice và step. |
| Media của lesson published trong path draft vẫn đọc qua URL trực tiếp | MAJOR | RESOLVED: media student yêu cầu cả version và parent path published. Teacher draft preview và old published version vẫn giữ. HTTP test trước/sau publish path. |
| Revision true/số thập phân có thể mutate draft | MAJOR | RESOLVED: strict bounded integer trước mutation; validation tests kiểm DB/audit/blob không đổi. |
| StepAttemptRecord dataclass serialize lỗi500 sau khi đã lưu | MAJOR | RESOLVED: public projection xử lý dataclass/enum/datetime/typed result, bỏ artifact và private review binding. Journey POST/read kiểm payload. |
| Restore chỉ nhận manifest mới, chặn backup schema10 hợp lệ | MAJOR | RESOLVED: xác minh manifest/schema/ledger/hash rồi restore vào thư mục mới và migrate11; regression old report read. |
| Lookup due qua list có giới hạn bỏ sót review ngoài trang đầu | MINOR | RESOLVED cùng correction: POST exact owner/ID/due SQL; GET list vẫn bounded. |
| Ba fixture cũ vi phạm additive schema/active-version/idempotency | Test regression | RESOLVED bằng explicit columns, publish trước active-version và key riêng; giữ nguyên assertions. Targeted27PASS. |

## Kiểm tra thiết kế và invariant

- Một SQLite/BlobStore từ composition root; service điều phối repository, không mở database thứ hai hoặc thêm global mutable state.
- Practice/learning runner không gọi scorer hoặc assessment worker; purpose và immutable content/rules/audio snapshot truy vết được. Retry cùng nội dung trả original, khác nội dung409; completion/review CAS trong transaction.
- Lesson publish snapshot bất biến; draft sửa tiếp tạo version khác. Authoring có role guard, bounded input, revision/CAS và audit. Import/export JSON kiểm hash/hierarchy/authority trước transaction; không nhúng binary media.
- Pure progress giữ pass trước đó, FREE đếm actual speaking_s theo từng round riêng; teacher override append-only không sửa raw result hoặc biến thành điểm.
- Migration011 additive; 005–010 không đổi. Dữ liệu legacy giữ raw và đánh dấu thiếu typed provenance; không backfill kết quả giả.
- Export/erase/retention/cleanup/backup mở rộng cho audio và review mới; trigger ngăn xóa blob ref thiếu cleanup intent, owner isolation được kiểm thử.
- Seed có version/hash/order, không ghi lại khi rerun và bảo vệ teacher edits/moves. Codex oracle độc lập kiểm18unit/31lesson/15practice, foreign key và 0write rerun.
- Bổ sung simplemma pin và dependency note; alignment bị chặn ở512tokens để tránh cấp phát O(nm) không giới hạn.

## Giới hạn đánh giá

UI N02/N03 và achievement/streak/pronunciation S03 là task riêng; không nhận DONE cho các phần đó. Browser evidence của task này là API journey qua browser, không phải nghiệm thu giao diện learning hoàn chỉnh. Fixture ASR không chứng minh speech accuracy; real-model preflight được ghi riêng, không suy ra CEFR validity. Coverage repository/API có nhánh lỗi còn chưa phủ; công bố số thực và evidence các transaction/permission bắt buộc trong final verification.

Reviewer Thắng/Nguyên và user acceptance: **PENDING**. Không tự kéo Jira sang DONE.
