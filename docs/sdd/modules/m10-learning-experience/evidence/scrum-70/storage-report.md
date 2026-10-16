# Báo cáo lane lưu trữ — SCRUM-70 / W5-S02

Trạng thái: implementation và kiểm tra lane lưu trữ hoàn tất để root review; chưa phải nghiệm thu hoặc APPROVED. Worktree `scrum-70`, branch base `51eff1fb2f1ecb5598262da65c804a7cda079fc8` (S01/PR40), source baseline được prompt ghim là `34da102`; target tham khảo lịch sử `3b2d2b78ba5bb35bd162b8f3e5de21ade946d237`, nguồn Sang `40907cc35b3d04408f9a8713f16d9be99f4cd6c7`.

## Thay đổi thuộc lane

- Thêm migration cộng dồn `011_learning_runtime.sql`, đăng ký schema 11, kiểm checksum prefix 5–10 và hỗ trợ restore backup tương ứng. Không sửa byte các migration 005–010. Migration lưu seed manifest, audio artifact reference, audit teacher override, review nguồn step; attempt cũ được chiếu `LEGACY` và giữ nguyên status/measurements/evidence gốc.
- Bổ sung `LearningRepository` cho seed, CAS CRUD/reorder draft, publish snapshot lesson/path, import/export hierarchy, media version, attempt/idempotency, review due-CAS practice/step, tiến độ, teacher override audit, cleanup intent, owner export/erasure và assessment-evidence projection.
- Student path chỉ đọc lesson có active version đã publish. Publish path yêu cầu unit/lesson có thứ tự hợp lệ và mọi lesson có typed published snapshot. Legacy path/lesson thiếu metadata lịch sử không được gán band/version/hash giả; legacy path thiếu schema typed được lược khỏi catalogue typed.
- Seed sample dùng ID và thứ tự ổn định: 18 units, 31 lessons. Rerun cùng hash không ghi DB; seed version mới chỉ cập nhật entity còn seed-owned và hash nguyên vẹn, bỏ qua nội dung/di chuyển teacher đã sửa; manifest ghi số insert/update/skip thực tế.
- Thêm regression cho prior PASS còn giữ tiến độ sau retry FAIL; FREE round có speech dương vẫn tính nỗ lực; review cùng due revision chỉ có một CAS winner; idempotency phân biệt full keys và round; published version cũ không đổi; import sai không ghi một phần; override không sửa raw result; xóa attempt xóa artifact reference và tạo cleanup intent.

## Kiểm tra

Lệnh focused đã chạy tại worktree này với `PYTHONPATH=src`:

```text
pytest -q tests/storage/test_learning_repository.py tests/storage/test_learning_migration_compat.py tests/storage/test_w5_storage_foundation.py tests/storage/test_sqlite_memory_migration.py tests/storage/test_sqlite_blob_store.py tests/storage/test_identity_compatibility.py tests/storage/test_privacy_migration.py tests/lessons tests/practice
116 passed in 22.25s
```

Coverage branch độc lập dùng `COVERAGE_FILE=/tmp/.coverage-scrum70-storage-final` trên cùng tập test:

| Module | Lines | Branches | Coverage |
| --- | ---: | ---: | ---: |
| `storage/learning.py` | 823/1174 (65%) | 258/500 (52%) | 65% |
| `storage/migrations.py` | 272/319 (82%) | 111/150 (74%) | 82% |
| `lessons/seed.py` | 38/40 (92%) | 6/8 (75%) | 92% |
| Tổng ba module | 1133/1533 (69%) | 375/658 (57%) | 69% |

Số liệu là coverage của targeted suite trên, không phải coverage toàn repository. Còn nhiều branch authoring/storage chưa được gọi trong suite; root cần quyết định có yêu cầu mở rộng coverage trước PR hay không. Một lần coverage run rộng hơn ban đầu bị NumPy extension reload lỗi khi collection, trước khi test chạy; lần chạy isolated với file coverage riêng thành công.

Ruff đã chạy `ruff format --check` và `ruff check` cho các file lane sở hữu: `storage/learning.py`, `storage/migrations.py`, `storage/sqlite.py`, migration 011, `lessons/seed.py`, `seed_topics.py`, `generate.py`, và ba test storage tương ứng. Kết quả: `9 files already formatted`; `All checks passed!`.

## Giới hạn và handoff

Coverage repository hiện 65%, vì vậy report không khẳng định mọi nhánh persistence đã được bao phủ. API/runtime, auth boundary, audio decoder/cleanup worker và portal backup/restore integration do integration lane sở hữu; root chạy xác minh tích hợp độc lập. Dữ liệu sample/seed là nội dung tổng hợp, không phải benchmark hoặc quan sát thực nghiệm. Không có residual/reference artifact được thêm vào Git; runtime evidence tiếp tục ở ngoài repository. Chưa commit hoặc push.
