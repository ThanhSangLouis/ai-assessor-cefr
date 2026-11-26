# Sơ đồ lớp SpeakUp

Mọi sơ đồ lớp của hệ thống đang chạy nằm trong thư mục này.

## Dùng file nào

| Việc | File | Ảnh |
|---|---|---|
| **Trình bày với giảng viên, đưa vào báo cáo** | [`02_class_core.drawio`](02_class_core.drawio) | [`02_class_core.png`](../../images/02_class_core.png) (Hình 2a trong SDD) |
| Rã xuống code, đối chiếu từng trường, đặt ở phụ lục | [`detailed/02_class_detailed.drawio`](detailed/02_class_detailed.drawio) | [`02_class_detailed.png`](../../images/02_class_detailed.png) (Hình 2c) |

Hai hình có **cùng bố cục, cùng vị trí hộp và đường nối**, cùng 19 lớp, 7 kiểu liệt kê, 43 quan hệ. Chỉ khác số thuộc tính:

- **Bản trình bày (gọn):** mỗi lớp chỉ giữ thuộc tính chính, gồm mã định danh, thuộc tính thể hiện quan hệ, trạng thái nghiệp vụ, và trường mà một luật nghiệp vụ dựa vào.
- **Bản chi tiết:** đủ trường nghiệp vụ; vẫn bỏ chi tiết kỹ thuật thuần (mốc thời gian không luật nào dựa vào, mã tham chiếu cổng thanh toán, mã OTP, khoá duyệt).

## Thư mục `detailed/`: các bản chi tiết

| File | Là gì | Có sửa không |
|---|---|---|
| `02_class_detailed.drawio` | **Bản chi tiết chính thức** (Hình 2c), đúng năm quy tắc quan hệ bên dưới | Không sửa tay: dựng lại bằng lệnh ở cuối trang |
| `02_class_a4_ngang.drawio` | Bản A4 ngang do **Nguyên** sửa (#145). Là **nguồn bố cục** để dựng cả hai hình trên. Ký hiệu quan hệ còn theo cách cũ | Chỉ Nguyên sửa. Sửa xong thì chạy lại lệnh ở cuối trang |
| `02_class.drawio` | Bản đầy đủ hiện trạng cũ (Hình 2), sinh bằng `tools/gen_class_diagram.py`. Test dùng bản này để ánh xạ từng thực thể với lớp trong code | Giữ để đối chiếu; không dùng trình bày |

## Năm quy tắc quan hệ (áp cho cả hai hình)

| Ký hiệu | Tên | Khi nào dùng | Câu kiểm tra |
|---|---|---|---|
| ──▶ | Association | A giữ một thuộc tính kiểu B (kể cả kiểu enum) | "A có trường nào kiểu B không?" |
| ◇── | Aggregation | A gom **nhiều** B qua `List<B>`, B sống độc lập | "Xoá A thì B còn không?" → còn |
| ◆── | Composition | B là một phần của A, sống chết theo A | "Xoá A thì B còn không?" → mất |
| ──▷ | Generalization | B là một loại A | "B có phải là một A không?" |
| ┄┄▶ | Dependency | A chỉ dùng tạm B, không lưu | "A có lưu B thành thuộc tính không?" → không |

Trên hai hình: 5 composition (Response◆Review, Response◆CoachUpgrade, LessonPath◆Unit, Unit◆Lesson, Lesson◆Step), 5 aggregation (Classroom◇Account ×3, LearningPlan◇Lesson, DrillPassage◇WordDrill `1..*`), 33 association. Không có dependency và generalization.

Ba quy ước khác của nhóm:

- Mỗi đường quan hệ phải có thuộc tính tương ứng ở lớp giữ.
- Bội số ghi trên đường, không ghi trong thuộc tính.
- Tập hợp ghi `List<T>`.
- Mỗi thực thể ghi mã định danh nghiệp vụ của nó (`orderId`, `responseId`, ...). `_id` là ObjectId MongoDB tự sinh, không lớp nào trong code dùng, nên chỉ có ở ERD.
- Thuộc tính tham chiếu đặt theo vai của đối tượng được trỏ tới (`Order.buyer: Account`), không theo thao tác (`createdBy`).

## Dựng lại sau khi bản A4 thay đổi

```bash
.venv/bin/python tools/derive_class_diagram.py docs/sdd/diagrams/class/detailed/02_class_a4_ngang.drawio docs/sdd/diagrams/class/detailed/02_class_detailed.drawio
.venv/bin/python tools/derive_class_diagram.py --level core docs/sdd/diagrams/class/detailed/02_class_a4_ngang.drawio docs/sdd/diagrams/class/02_class_core.drawio
```

Sau đó xuất lại hai ảnh PNG vào `docs/sdd/images/` bằng draw.io, rồi chạy `pytest tests/test_diagrams.py tests/test_class_diagram_in_code.py`. Test kiểm:

- mọi thuộc tính trên hình đều có trong code;
- quan hệ đúng năm quy tắc;
- bản gọn là tập con của bản chi tiết;
- không đường nào cắt hộp hay chồng lên nhau.

## Những gì class diagram không chứa

- **Lớp ghi chép kỹ thuật** (D110): `AuditEntry` (`audit_log`, nhật ký ai làm gì) và `LedgerEntry` (`ledger`, bút toán giữ, trừ, trả lượt), cùng `LedgerState`, `MeteredAction`. Vẫn có trong code, ERD và từ điển dữ liệu.
- **Trường kỹ thuật:** nằm ở sơ đồ ERD (`05_*`) và [`docs/db/TU_DIEN_DU_LIEU.md`](../../../db/TU_DIEN_DU_LIEU.md).
- **Hành vi** (chuỗi chấm điểm, luật chuyển bài cho giảng viên, cách tính lượt): nằm ở SRS và các sơ đồ tuần tự, hoạt động trong SDD.
