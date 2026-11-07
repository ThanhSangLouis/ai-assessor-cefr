# Kế hoạch và kết quả kiểm thử D098 — Vòng đời đơn gói lượt theo mẫu State

| Thuộc tính | Giá trị |
| --- | --- |
| Thay đổi | D098: mỗi trạng thái đơn gói lượt là một lớp (`billing/order_state.py`); service, repository và API hỏi đối tượng trạng thái. Không thêm hay đổi yêu cầu chức năng |
| Phiên bản mã | nhánh `feat/d095-payos` |
| Người lập | Võ Thanh Sang |
| Ngày | 07/11/2026 |

## 1. Mục tiêu

1. **Đúng bảng chuyển.** Chỉ 7 bước chuyển hợp lệ trong 25 cặp (trạng thái, đích); bước còn lại ném `TransitionRefused`.
2. **Sơ đồ khớp mã.** Hình 10 vẽ đúng và đủ các bước `transitions()` cho phép.
3. **Hành vi không đổi.** Mọi test thanh toán có sẵn vẫn qua; kho chỉ đổi đơn một lần dù lời báo đến theo thứ tự nào.

## 2. Test case — `tests/test_d098_order_state.py`

| Mã | Test | Tầng | Kết quả mong đợi |
| --- | --- | --- | --- |
| TC-OS-01 | `test_each_state_allows_only_its_own_moves` | Unit | 25 cặp: đúng 7 cặp hợp lệ đi tới đích, còn lại bị từ chối và nêu trạng thái, đích |
| TC-OS-02 | `test_a_settled_order_is_final_and_an_expired_one_still_takes_the_money` | Unit | Paid, Failed, Cancelled là trạng thái cuối; Expired vẫn nhận "đã trả"; "chưa xong" không là bước chuyển; nguồn của Paid là Pending và Expired; tên tiếng Việt |
| TC-OS-03 | `test_the_state_diagram_draws_exactly_the_moves_the_code_allows` | Unit | Các mũi tên trong `10_state_don_hang.mmd` bằng `transitions()` |
| TC-OS-04 | `test_the_store_moves_an_order_once_whatever_arrives_after` | Integration | Đơn đã trả: "thất bại" đến sau, chạy hết hạn, "đã trả" lần hai đều không đổi gì; đơn hết hạn vẫn nhận tiền đến muộn |

## 3. Kết quả

| Lệnh | Kết quả |
| --- | --- |
| `pytest tests/test_d098_order_state.py` | 4 passed |
| Các test thanh toán có sẵn (`test_billing*`, `test_credit_packs`, `test_gateways*`, `test_d095_*`, `test_d096_*`) | đều qua, không sửa test nào |
