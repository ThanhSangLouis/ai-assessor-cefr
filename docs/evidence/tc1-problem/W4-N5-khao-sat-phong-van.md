# W4-N5 — Bộ khảo sát và phỏng vấn TC1

**Owner:** Nguyên. **Ngày chuẩn bị:** 12/10/2026, thuộc W05; xử lý phần chuyển tiếp của W4. **Version:** v1.0. **Trạng thái:** `PREPARED`; thu thập và phân tích thực tế `NOT_RUN`.

Nguyên xác nhận ngày 12/10 chưa có kết quả khảo sát/phỏng vấn. Tài liệu này là bộ câu hỏi để dùng với người thật; chưa có phản hồi hoặc kết luận thực địa. Nguồn tiêu chí: [rubric gốc](../../rubric/Rubric_Do_An_Mon_Hoc_CNPM_sinhvien.docx.pdf), trang 13, và [plan W4](../../plan/week-04.md), task W4-N5.

## Mục tiêu và mẫu dự kiến

Làm rõ cách sinh viên luyện/nộp bài nói, cách giảng viên đánh giá và phản hồi, khó khăn trong luồng nộp → trạng thái → báo cáo → duyệt. Kết quả dùng để đề xuất sửa Requirement theo FR/AC, không tự thay phạm vi đã duyệt.

Đề xuất khảo sát ít nhất 5 sinh viên thuộc nhóm mục tiêu và phỏng vấn ít nhất 2 giảng viên có kinh nghiệm dạy/đánh giá nói tiếng Anh. Đây là mục tiêu thu thập đề xuất, không phải số người đã tham gia hoặc ngưỡng điểm rubric. Tuyển thuận tiện phải được ghi rõ; không diễn giải mẫu nhỏ thành đại diện toàn bộ sinh viên Việt Nam. Theo rubric, số bên liên quan đã khảo sát, số giải pháp được so sánh và số KPI được chốt là các metric riêng.

## Lời giới thiệu và đồng ý tham gia

> Nhóm đang phát triển AI Assessor CEFR để hỗ trợ đánh giá bài nói tiếng Anh độc thoại và giảng viên duyệt kết quả. Chúng tôi muốn tìm hiểu trải nghiệm hiện tại của bạn. Tham gia tự nguyện, có thể bỏ qua câu hỏi hoặc dừng bất cứ lúc nào. Khảo sát này không yêu cầu nộp audio, tài khoản hay thông tin liên hệ và không ảnh hưởng điểm học tập. Dữ liệu báo cáo dùng mã giả danh. Bạn có đồng ý tham gia không?

Chọn **Đồng ý / Không đồng ý**. Nếu không đồng ý, kết thúc và không lưu câu trả lời. Nếu muốn liên hệ tiếp, dùng danh sách liên hệ riêng ngoài Git, với sự đồng ý riêng. Phỏng vấn chỉ ghi âm nếu có đồng ý riêng; mặc định ghi chép. Khi người tham gia muốn rút phản hồi, dùng mã người tham gia và liên hệ Nguyên qua kênh đã trao đổi; không đặt thời hạn hay chính sách lưu trữ chưa được nhóm thống nhất.

## Phiếu khảo sát sinh viên

**Mã:** `SV-___`; ngày thực hiện: để trống đến khi thực hiện. Không thu tên, mã sinh viên, email hoặc số điện thoại trong phiếu đưa vào Git.

| ID | Câu hỏi | Kiểu trả lời |
| --- | --- | --- |
| SV01 | Trong 4 tuần gần đây, bạn luyện nói tiếng Anh bao nhiêu lần mỗi tuần? | 0 / 1–2 / 3–4 / 5 trở lên / không nhớ |
| SV02 | Bạn đang luyện hoặc nộp bài nói qua những hình thức nào? | Nói trực tiếp / gửi file / ghi âm trên web / app luyện nói / khác; chọn nhiều |
| SV03 | Khi nộp file/ghi âm, bạn từng gặp khó khăn nào? | Dung lượng/định dạng / micro / mạng / không biết đã nộp thành công / không gặp / khác; chọn nhiều |
| SV04 | Với bài gần nhất có nhận phản hồi, bạn chờ khoảng bao lâu? | Chưa nhận phản hồi / dưới 1 ngày / 1–3 ngày / 4–7 ngày / trên 7 ngày / không nhớ |
| SV05 | Phản hồi hiện tại giúp bạn xác định chỗ cần cải thiện ở mức nào? | 1 hoàn toàn không giúp → 5 rất rõ; chưa có phản hồi |
| SV06 | Bạn muốn biết điều gì khi bài đang được xử lý? | Đã nhận bài / đang xử lý / cần giảng viên duyệt / lý do lỗi / thời điểm có kết quả / khác |
| SV07 | Trên báo cáo, thông tin nào hữu ích nhất? | Overall ước lượng / nhận xét có dẫn chứng / nghe đúng đoạn / kết quả giảng viên / giới hạn của kết quả; chọn tối đa 3 |
| SV08 | Bạn muốn hệ thống xử lý thế nào khi chưa đủ bằng chứng để ước lượng? | Nêu lý do và hướng dẫn nộp lại / chuyển giảng viên / chưa chắc; có thể giải thích |
| SV09 | Khi AI và giảng viên có kết quả khác nhau, bạn cần thông tin gì để hiểu quyết định? | Trả lời ngắn |
| SV10 | Bạn lo ngại điều gì khi dùng hệ thống đánh giá nói? | Sai kết quả / riêng tư audio / không hiểu nhận xét / chi phí / không lo / khác |
| SV11 | Hãy kể một khó khăn cụ thể trong lần luyện hoặc nộp bài gần nhất. | Trả lời mở; nhắc không ghi tên người khác |
| SV12 | Một thay đổi nào sẽ giúp bạn nhiều nhất? | Trả lời mở |

Các câu có lựa chọn “khác” luôn có ô mô tả tự do. Không yêu cầu người tham gia chọn tính năng nhóm muốn phát triển; giữ cả phương án không gặp khó khăn/chưa chắc/chưa có trải nghiệm.

## Hướng dẫn phỏng vấn giảng viên

**Mã:** `GV-___`; dự kiến 15–20 phút. Hỏi ví dụ thực tế trước khi giới thiệu giải pháp. Các thời lượng là lịch đề xuất.

| ID | Câu hỏi | Dữ liệu cần ghi |
| --- | --- | --- |
| GV01 | Thầy/cô đang giao và nhận bài nói như thế nào? | Quy trình, công cụ, loại bài độc thoại/đối thoại |
| GV02 | Với một bài điển hình, các bước nghe, chấm và viết phản hồi tốn bao lâu? | Ước lượng do người trả lời cung cấp, hoặc số đo có nguồn; phân biệt hai loại |
| GV03 | Phần nào khó hoặc mất thời gian nhất? Xin một tình huống cụ thể. | Vấn đề và bối cảnh; không ghi danh tính sinh viên |
| GV04 | Rubric nào đang được dùng và ai phê duyệt? | Tên/version/nguồn được phép chia sẻ; chưa có nguồn thì ghi chưa xác minh |
| GV05 | Bằng chứng nào giúp thầy/cô tin hoặc bác một nhận xét tự động? | Yêu cầu về timestamp, transcript, audio và giới hạn |
| GV06 | Những ca nào cần giảng viên duyệt hoặc yêu cầu nộp lại? | Quy tắc đề xuất; không đổi reason map của M05 tự động |
| GV07 | Khi sửa band AI, lý do và lịch sử trước/sau cần được thể hiện thế nào? | M06/M07, accountability và UI wording |
| GV08 | Trong nghiên cứu, hai người chấm độc lập và một người phân xử cần điều kiện gì? | Năng lực, thời gian, tránh xem điểm AI/trước của người khác |
| GV09 | Audio và phản hồi nên được lưu, truy cập và rút/xóa theo quy trình nào? | Mong muốn và giới hạn; chưa phải quyết định pháp lý/vận hành |
| GV10 | Chỉ số nào thể hiện hệ thống có ích và mức mục tiêu nào hợp lý? | KPI đề xuất cùng đơn vị/cách đo; cần nhóm và GVHD chốt |
| GV11 | Có điểm nào nhóm hiểu sai hoặc bỏ sót? | Phản hồi mở và phần người tham gia muốn rút khỏi báo cáo |

Cuối buổi, đọc lại ghi chép chính để người tham gia sửa sai. Nếu dùng câu trích dẫn, xin phép riêng và chỉ đưa phiên bản đã ẩn danh vào hồ sơ.

## Thu thập, phân tích và traceability

1. Nguyên duyệt câu hỏi; thử cách hiểu câu hỏi với một người, ghi mọi sửa đổi version trước khảo sát chính thức. Pilot không nhập vào mẫu chính trừ khi protocol ghi rõ và dữ liệu tương thích.
2. Tuyển người thật, cấp mã và lấy đồng ý. Lưu ghi chép gốc/consent ngoài Git trong nơi hạn chế truy cập; dùng [manifest](W4-N5-evidence-manifest.md) để dẫn chiếu.
3. Ghi mỗi phản hồi một record trong [data template](W4-N5-data-template.json). Bỏ câu hỏi được phép; dùng `null` cho chưa trả lời, không thay bằng 0. Không tính mẫu từ template.
4. Tổng hợp tần suất với mẫu số riêng cho từng câu, phân biệt câu nhiều lựa chọn. Ghi các nhóm vấn đề từ câu mở, bằng chứng thuận và nghịch; không suy ra nhân quả từ ý kiến.
5. Tạo bảng `Finding ID → nguồn ẩn danh → vấn đề → M01/M06/M07 FR/AC → đề xuất → quyết định owner/GVHD`. Yêu cầu mới quay lại SDD; chưa duyệt thì giữ `PROPOSED`.

| Finding ID | Nguồn và ngày | Quan sát thực tế | FR/AC liên quan | Đề xuất/owner verdict |
| --- | --- | --- | --- | --- |
| Chưa cấp ID | Chưa thu thập | `NOT_RUN` | Chưa đối chiếu | `PENDING` |

## Điều kiện khép task

Có phản hồi/biên bản của người thật với ngày và nguồn truy cập được, consent phù hợp, tổng hợp đúng dữ liệu và bảng traceability được Nguyên kiểm tra. Chỉ chuẩn bị bộ câu hỏi chưa hoàn tất W4-N5. KPI chốt và so sánh giải pháp là phần TC1 riêng; tài liệu này chưa claim các mục đó đã đạt.
