# SCRUM-69 — Chỉ dẫn correction đã phát hành

Historical target `3b2d2b78ba5bb35bd162b8f3e5de21ade946d237`; Sang reference `40907cc35b3d04408f9a8713f16d9be99f4cd6c7`; actual base `9748814`.

Các chỉ dẫn dưới đây tổng hợp từ vòng root review và dispatch thực tế; không phải transcript nguyên văn của user.

1. Đưa mọi reason Trust vào review routing; không để uncertainty sinh generic failure hoặc durable retry. Thiếu/invalid/hash calibration phải fail closed, không bỏ LID/guard evidence đã quan sát.
2. Resolve task bằng cả task_id/task_version. Lưu topic keywords qua runtime_settings hiện có; boot chỉ tạo metadata cho task mới, không ghi đè context của teacher. Model activation/reload phải rebind và kiểm calibration với scorer mới.
3. Không áp giới hạn provenance mới lên source_versions cũ chứa window_results dài. Test report cũ giữ đầy đủ JSON cửa sổ; LID riêng phải không ép English trước detector.
4. Trust REJECTED phải thành response REJECTED, report không score/band và không ordinary review candidate. Geometry cửa sổ sai phải thành controlled NOT_EVALUATED/review thay vì FAILED/retry.
5. Criterion indicators chỉ tham chiếu evidence hợp lệ và đúng criterion, không tạo evidence giả. GET report cho staff dựa trên response được phép đọc, không phụ thuộc candidate. Lọc path ở cả API và HTML, giữ projection tối thiểu cho student.
6. Chạy test/regression/coverage cho nhánh failure và authorization. Kiểm Ruff cả src/tests/scripts/tools, sửa import/unused và format toàn bộ Python đã thay đổi; không format sweep các file khác. Sau source freeze mới build wheel và thực hiện browser QA theo prompt riêng.

Root kiểm chứng độc lập; không commit/push từ lane. Approval cuối và Jira Done vẫn chờ reviewer/user.
