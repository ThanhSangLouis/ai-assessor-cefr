# Kế hoạch kiểm thử — Làm lại giao diện (D024)

| Thuộc tính | Giá trị |
| --- | --- |
| Phạm vi | Đợt 5 của `docs/web/SPEC_WEB.md`, tiêu chí UX-01..UX-11 |
| Quyết định | D024, chủ dự án duyệt ngày 06/10/2026 |
| Tầng | E2E (Playwright, chỉ chạy trên máy) và tích hợp (TestClient) |
| Mã kiểm thử | `tests/e2e/test_ui_e2e.py`, `tests/test_progress_and_stats.py` |
| Giữ khớp | `tests/test_ui_traceability.py`: mỗi ca trong mã có trong bảng dưới và ngược lại; mỗi UX có ít nhất một ca |

## 1. Vì sao chủ yếu là E2E

Đợt này chỉ đổi giao diện: luật chấm, dữ liệu và API giữ nguyên (trừ trường
`home` trong phản hồi đăng nhập). Thứ cần chứng minh là người dùng **làm được việc
trên màn hình** — nghe lại trước khi nộp, thấy đúng mục điều hướng, bấm được nút
trên điện thoại — nên tầng kiểm thử đúng là trình duyệt thật. Phần máy chủ đổi
(điều hướng theo vai trò) có một ca tích hợp.

Các bất biến mã nguồn của giao diện vẫn nằm ở `tests/test_frontend_contracts.py`
và `tests/test_web.py`; đợt này sửa hai ca ở đó cho khớp cách làm mới:

- `test_dataset_reads_match_the_attributes_written` nay đọc thuộc tính `data-*`
  từ chính các template thay cho danh sách viết tay, nên ngưỡng QC truyền qua
  `data-min-seconds` cũng được kiểm.
- `test_moi_ma_ly_do_deu_co_ten_tieng_viet_tren_man_duyet` nay đọc tên lý do ở
  `common.js` (`window.ui.REASON_NAMES`), nơi hàng đợi và trang duyệt dùng chung.

## 2. Ca kiểm thử

| Mã | Hàm kiểm thử | Tiêu chí | Loại | Nội dung |
| --- | --- | --- | --- | --- |
| TC-UI-I01 | `test_signed_in_pages_mark_the_current_nav_item_for_each_role` | UX-01 | Thuận | Mỗi trang của sinh viên và giảng viên có đúng một mục `aria-current`; giảng viên không thấy mục của sinh viên |
| TC-UI-E01 | `test_each_role_sees_only_its_own_navigation_and_lands_on_its_home` | UX-01 | Thuận | Đăng nhập không `next`: sinh viên về Luyện tập với bốn mục, giảng viên về Hàng đợi với ba mục (thêm Lộ trình luyện từ D025); logo về trang chính của vai trò |
| TC-UI-E02 | `test_account_menu_holds_consent_theme_and_sign_out` | UX-01 | Thuận | Menu tài khoản có Đồng thuận, Đăng xuất; đổi giao diện sáng/tối; Esc đóng menu |
| TC-UI-E03 | `test_recording_waits_for_listen_back_before_anything_is_sent` | UX-03 | Âm | Ghi bằng micro giả, dừng: hiện bước nghe lại; phím cách và chờ đợi không gửi gì; "Ghi lại" ghi tiếp |
| TC-UI-E04 | `test_uploaded_file_is_heard_back_then_submitted_to_a_report` | UX-04 | Thuận | Chọn file: hiện tên và độ dài 0:35, nút "Chọn file khác"; nộp xong tới báo cáo có bước tiếp và liên kết từng phần |
| TC-UI-E05 | `test_chosen_prompt_sits_above_the_record_button` | UX-05 | Thuận | Chọn đề thứ hai: đề hiện đầy đủ trên nút ghi âm, mã đề gửi đi đổi theo |
| TC-UI-E06 | `test_my_responses_filters_assessments_from_practice` | UX-07 | Thuận | Một bài đánh giá, một bài luyện: lọc Luyện tập còn một dòng "Không chấm", lọc Đánh giá còn dòng kia |
| TC-UI-E07 | `test_consent_asks_before_withdrawing_and_offers_next_steps` | UX-11 | Biên | Ký xong hiện lối đi tiếp; rút lại bấm Huỷ thì giữ nguyên, bấm OK mới rút |
| TC-UI-E08 | `test_teacher_opens_the_next_free_response_and_reads_names_not_codes` | UX-08 | Thuận | "Duyệt bài tiếp theo" mở một bài; thẻ máy chấm không còn mã dạng `A_B`; lý do soạn sẵn chèn vào ô lý do |
| TC-UI-E09 | `test_admin_edits_a_threshold_and_the_submit_page_follows` | UX-10 | Thuận | Sửa ngưỡng ngắn nhất 20 → 15 giây: phiên bản mới, trang nộp bài của sinh viên ghi "15 đến" (từ D026, `/` đưa quản trị viên về trang quản trị); trả lại 20 sau ca |
| TC-UI-E10 | `test_admin_activation_asks_first_and_only_compatible_models_offer_it` | UX-10 | Âm | Mô hình không tương thích hoặc hỏng không có nút kích hoạt; bấm kích hoạt rồi Huỷ thì mô hình đang chấm không đổi |
| TC-UI-E11 | `test_phone_student_pages_keep_a_bottom_tab_bar_and_no_sideways_scroll` | UX-02 | Biên | Ở 375 px, bốn trang của sinh viên: điều hướng cố định sát đáy, không cuộn ngang |

## 3. Ma trận phủ tiêu chí

| Tiêu chí | Ca kiểm thử |
| --- | --- |
| UX-01 | TC-UI-I01, TC-UI-E01, TC-UI-E02 |
| UX-02 | TC-UI-E11 |
| UX-03 | TC-UI-E03 |
| UX-04 | TC-UI-E04 |
| UX-05 | TC-UI-E05 |
| UX-06 | TC-UI-E04 |
| UX-07 | TC-UI-E06 |
| UX-08 | TC-UI-E08 |
| UX-09 | TC-UI-E08 |
| UX-10 | TC-UI-E09, TC-UI-E10 |
| UX-11 | TC-UI-E07 |

Bộ kiểm thử luyện tập (`tests/e2e/test_practice_e2e.py`, TC-PR-E01..E15) chạy lại
trên bộ ghi âm dùng chung: các ca nộp file, ghi bằng micro giả và chưa đồng
thuận nay đi qua bước nghe lại, nên chúng cũng là kiểm thử hồi quy cho UX-03.

## 4. Cách chạy

```bash
pytest -m e2e tests/e2e
```

Cần `pip install -e ".[e2e]"` và `playwright install chromium`. CI bỏ qua tầng
này (chủ dự án chọn ngày 06/10/2026), nên chạy trên máy trước khi mở PR.

## 5. Giới hạn

- Giao diện tối mới kiểm bằng mắt trên ảnh chụp, chưa có so sánh ảnh tự động.
- Trình đọc màn hình chỉ được kiểm gián tiếp (vai trò, `aria-*`, chữ ẩn), chưa thử
  với NVDA hay VoiceOver.
