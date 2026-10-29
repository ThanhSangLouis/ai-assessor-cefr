# Xây dựng hệ thống AI hỗ trợ đánh giá năng lực nói tiếng Anh theo CEFR cho sinh viên đại học Việt Nam ở trình độ A2-B2

## 26. Báo cáo kiểm tra DMP bằng dữ liệu synthetic

| Thuộc tính | Giá trị |
| --- | --- |
| Trạng thái | COMPLETED WITH LIMITATIONS |
| Ngày chạy | 02/09/2026; chạy lại 12/09/2026 |
| Người/công cụ chạy | Codex hỗ trợ, Python 3.13 local |
| Script | `tools/week1_dmp_synthetic_check.py` |
| Config version | `week1-dmp-check-v1` |
| Dữ liệu | Chỉ dữ liệu synthetic được tạo trong thư mục tạm và tự xóa |

## 1. Mục tiêu

Kiểm tra một phần workflow trong `16_data_management_plan.md` trước khi có dữ liệu người thật. Script không đọc, sửa hoặc mô phỏng audio/transcript thật và không kiểm tra dịch vụ ngoài.

## 2. Lệnh đã chạy

```powershell
python tools/week1_dmp_synthetic_check.py
```

## 3. Kết quả lần chạy cuối

| Kiểm tra | Kết quả | Ý nghĩa |
| --- | --- | --- |
| `identity_separation` | PASS | Direct identity synthetic chỉ nằm ở identity root, không xuất hiện trong research workspace |
| `boundary_schema` | PASS | Manifest đủ field được nhận; thiếu `prompt_version` bị phát hiện deterministically |
| `log_privacy` | PASS | Log chỉ dùng pseudonymous ID/config/status/reason code, không có identity/audio/transcript field |
| `snapshot_checksum_restore` | PASS | Snapshot copy khớp SHA-256 và raw artifact không đổi trong thao tác |
| `withdrawal_deletion` | PASS | Artifact synthetic và identity mapping được xóa theo target; deletion log không chứa direct identity |
| `temporary_workspace_cleanup` | PASS | Thư mục phiên test cuối được dọn sau khi chạy |
| `encryption_at_rest` | NOT TESTED | Chưa có approved storage/encryption/key owner |
| `role_access_control` | NOT TESTED | Chưa có tài khoản/role thật để kiểm tra deny/allow |

## 4. Sự cố trong lần chạy đầu và xử lý

Hai lần chạy sandbox đầu không tạo được thư mục con do `PermissionError`; không có test nào được tính PASS từ các lần này. Script được chuyển sang workspace tạm và chạy lại với quyền cho phép. Một thư mục tạm bị kẹt từ lần lỗi đã được xác minh nằm trong workspace rồi xóa; lần chạy cuối hoàn tất và tự cleanup.

## 5. Giới hạn và điều kiện đóng

- PASS chỉ chứng minh logic synthetic của script, không chứng minh bảo mật của môi trường production.
- Chưa kiểm tra encryption, key recovery, quyền hệ điều hành, backup device thật hoặc institutional incident workflow.
- Script không tạo Pydantic/API contract và không thay test của implementation tương lai.
- Mục DMP chỉ được đóng hoàn toàn sau khi GVHD/ethics duyệt storage/retention, chỉ định key/access owner và chạy hai test còn thiếu trên môi trường đã duyệt.

## 6. Kết luận

Withdrawal/deletion workflow bằng dữ liệu synthetic đã được kiểm tra ở phạm vi tối thiểu. Checklist DMP có thể ghi nhận phần synthetic là `PASS`, nhưng toàn bộ DMP vẫn `DRAFT` vì encryption/access/retention và approval còn mở.

## 7. Lần chạy lại 12/09/2026

Script được chạy lại bằng Python 3.13.0 sau khi tạo Git baseline và cập nhật hồ sơ W1-W3. Sáu kiểm tra logic tiếp tục `PASS`; `encryption_at_rest` và `role_access_control` tiếp tục `NOT_TESTED` đúng stop condition. Phiên chạy đã tự cleanup; không có dữ liệu người thật được đọc hoặc tạo.
