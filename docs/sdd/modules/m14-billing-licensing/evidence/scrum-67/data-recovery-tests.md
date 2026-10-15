# Báo cáo kiểm thử phục hồi dữ liệu W5

Historical target `3b2d2b7`; Sang `40907cc`; actual base `bab5f25` (T01 + T02).

Đã thêm `tests/portal/test_w5_data_recovery.py` cho retry cleanup sau lỗi unlink, giữ blob còn được lesson media tham chiếu, retention dry-run/apply cho job và attempt cũ trong khi giữ attempt đang hoạt động, và orphan dry-run/apply. Không sửa source hoặc test khác.

Kiểm chứng riêng: 6 test pass; Ruff check và format pass. Coverage tổng `portal/data.py` được chạy cùng bộ portal sau khi lane backup/restore hoàn tất.
