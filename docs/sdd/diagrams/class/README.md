# Sơ đồ lớp SpeakUp

Mọi sơ đồ lớp của hệ thống đang chạy nằm trong thư mục này.

## Dùng file nào

| Việc | File | Ảnh |
|---|---|---|
| **Trình bày với giảng viên, đưa vào báo cáo** | [`02_class_core.drawio`](02_class_core.drawio) | [`02_class_core.png`](../../images/02_class_core.png) (Hình 2a trong SDD) |
| Rã xuống code, đối chiếu từng trường, đặt ở phụ lục | [`detailed/02_class_detailed.drawio`](detailed/02_class_detailed.drawio) | [`02_class_detailed.png`](../../images/02_class_detailed.png) (Hình 2c) |

Hai hình có **cùng bố cục, cùng vị trí hộp và đường nối**, cùng 20 lớp, 9 kiểu liệt kê, 47 quan hệ. Mỗi lớp có định danh ở dòng đầu, đúng tên trường trong code viết camelCase: `accountId` ↔ `account_id`, `classId` ↔ `class_id`, `attemptId` ↔ `attempt_id`, `reviewId: int`. Achievement (`achievementId`) và CoachUpgrade (`upgradeId`) có định danh riêng từ D110, Wallet (`walletId`) và PriceList (`priceListId`) từ D111: lớp nào cũng có. Tên thuộc tính trên hình là tên trong code (D111 đổi code theo hình: `decidedAt`, `reasonCodes`, `feedback`, `lessons`). Tham chiếu tới lớp khác vẽ thành thuộc tính kiểu lớp đó (`owner: Account`) và lưu bằng mã của nó (`account_id`), như mọi kho tài liệu. Chỉ khác số thuộc tính:

- **Bản trình bày (gọn):** mỗi lớp chỉ giữ thuộc tính chính, gồm thuộc tính thể hiện quan hệ, trạng thái nghiệp vụ, và trường mà một luật nghiệp vụ dựa vào.
- **Bản chi tiết:** đủ trường nghiệp vụ; vẫn bỏ chi tiết kỹ thuật thuần (mã tự sinh, mốc thời gian không luật nào dựa vào, mã tham chiếu cổng thanh toán, mã OTP, khoá duyệt).

## Thư mục `detailed/`: các bản chi tiết

| File | Là gì | Có sửa không |
|---|---|---|
| `02_class_detailed.drawio` | **Bản chi tiết chính thức** (Hình 2c), đúng quy ước quan hệ bên dưới. Test dùng bản này để ánh xạ từng thuộc tính với code | Không sửa tay: dựng lại bằng lệnh ở cuối trang |
| `02_class_a4_ngang.drawio` | Bản A4 ngang do **Nguyên** sửa (#145). Là **nguồn bố cục** để dựng cả hai hình trên. Ký hiệu quan hệ còn theo cách cũ | Chỉ Nguyên sửa. Sửa xong thì chạy lại lệnh ở cuối trang |

## Quy ước quan hệ (áp cho cả hai hình)

| Ký hiệu | Tên | Khi nào dùng | Câu kiểm tra |
|---|---|---|---|
| ◆── | Composition | A giữ thuộc tính kiểu B, và B sống chết theo A | "Xoá A thì B còn không?" → mất |
| ◇── | Aggregation | A giữ thuộc tính kiểu B (kể cả `List<B>`), B sống độc lập | "A có trường nào kiểu B không?" → có |
| ┄┄> | Nét đứt tới enum | A giữ thuộc tính kiểu enum, mũi tên mở trỏ vào enum | "Kiểu của trường là enum?" → có |
| ─── | Association | A và B liên quan nhưng **không** lớp nào giữ thuộc tính kiểu lớp kia | Muốn giữ association thì phải xoá thuộc tính |

Kim cương nằm ở lớp giữ thuộc tính. Trên hai hình: 5 composition (Response◆Review, Response◆CoachUpgrade, LessonPath◆Unit, Unit◆Lesson, Lesson◆Step), 24 aggregation, 17 nét đứt tới enum, 1 association (LedgerEntry ── Response: bút toán ghi thứ nó thu tiền bằng `key`, có khi là một bài nói, có khi là bản ghi lộ trình hay đoạn đọc, nên không giữ thuộc tính kiểu Response); không có generalization.

Ba quy ước khác của nhóm:

- Mỗi đường aggregation/composition phải có thuộc tính tương ứng ở lớp giữ; mỗi thuộc tính kiểu lớp có đúng một đường, mỗi enum được dùng có đúng một đường nét đứt.
- Bội số ghi trên đường, không ghi trong thuộc tính. Ví dụ DrillPassage ◇ WordDrill ghi `1..*`: một đoạn đọc gom mọi từ đang ôn.
- Tập hợp ghi `List<T>`.
- `AuditEntry` (`audit_log`) là nhật ký kỹ thuật nên không vẽ.

## Dựng lại sau khi bản A4 thay đổi

```bash
.venv/bin/python tools/derive_class_diagram.py docs/sdd/diagrams/class/detailed/02_class_a4_ngang.drawio docs/sdd/diagrams/class/detailed/02_class_detailed.drawio
.venv/bin/python tools/derive_class_diagram.py --level core docs/sdd/diagrams/class/detailed/02_class_a4_ngang.drawio docs/sdd/diagrams/class/02_class_core.drawio
```

Sau đó xuất lại hai ảnh PNG vào `docs/sdd/images/` bằng draw.io, rồi chạy `pytest tests/test_diagrams.py tests/test_class_diagram_in_code.py`. Test kiểm:

- mọi thuộc tính trên hình đều có trong code;
- quan hệ đúng quy ước trên;
- bản gọn là tập con của bản chi tiết;
- không đường nào cắt hộp hay chồng lên nhau.

## Những gì class diagram không chứa

- **Trường kỹ thuật:** nằm ở sơ đồ ERD (`05_*`) và [`docs/db/TU_DIEN_DU_LIEU.md`](../../../db/TU_DIEN_DU_LIEU.md).
- **Hành vi** (chuỗi chấm điểm, luật chuyển bài cho giảng viên, cách tính lượt): nằm ở SRS và các sơ đồ tuần tự, hoạt động trong SDD.
