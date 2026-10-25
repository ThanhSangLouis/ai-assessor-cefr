# SCRUM-88 — đề bài, rubric và kế hoạch thu

**Task:** SCRUM-88 / W6-N03 · **Owner:** Nguyên  
**Status:** Materials implemented; final task acceptance awaits owner review.  
**Authority:** Theo xác nhận của chủ dự án ngày 25/10/2026, GVHD đã đồng ý duyệt và chủ dự án được ủy quyền chốt. Không yêu cầu biên bản riêng.

## 1. Prompt bank

Hai task dưới đây là hai bài độc thoại theo [kế hoạch khảo sát](KE_HOACH_KHAO_SAT.md). Mỗi bài có 30 giây chuẩn bị và 40–60 giây trả lời bằng tiếng Anh; người học không đọc văn bản viết sẵn.

| Task ID / version | Tiêu đề | Prompt hiển thị |
|---|---|---|
| `demo-speaking` / `1` | Trải nghiệm học được điều mới | Bạn có 30 giây chuẩn bị. Sau đó hãy nói bằng tiếng Anh trong 40–60 giây; không đọc văn bản viết sẵn. Kể về một lần bạn học được điều gì đó mới ngoài trường lớp. Bạn đã học gì, học như thế nào, và vì sao nó đáng nhớ? |
| `demo-speaking-opinion` / `1` | Ý kiến về việc sinh viên làm thêm | Bạn có 30 giây chuẩn bị. Sau đó hãy nói bằng tiếng Anh trong 40–60 giây; không đọc văn bản viết sẵn. Có ý kiến cho rằng sinh viên nên đi làm thêm trong lúc học. Bạn đồng ý hay không, và vì sao? |

Hai task được seed trong local demo để sinh viên và giám khảo thấy cùng prompt, version và thời lượng. Đây là fixture của nhóm, không phải dữ liệu người tham gia.

## 2. Rubric cho giám khảo

Mỗi bài được hai giám khảo chấm độc lập. Mỗi tiêu chí có điểm `0–6`, bước `0,5`, kèm một dòng lý do. Điểm tổng `0–6` là nhận định tổng thể, không phải trung bình số học của năm tiêu chí. Dùng mô tả A2/B1/B2 làm mốc; chọn nửa điểm khi bài nằm giữa hai mốc. Chọn band tổng thể riêng theo mô tả CEFR, không tự suy ra band từ điểm số. Nếu toàn bài không thể chấm, chọn `Không chấm được` và nêu lý do.

| Tiêu chí | A2 | B1 | B2 |
|---|---|---|---|
| Range | Dùng mẫu câu và cụm từ quen thuộc; thường phải đơn giản hóa thông điệp. | Đủ ngôn ngữ cho chủ đề quen thuộc; còn do dự hoặc vòng diễn đạt. | Diễn đạt rõ, phát triển quan điểm và dùng được một số cấu trúc phức. |
| Accuracy | Dùng được một số cấu trúc đơn giản; lỗi cơ bản còn thường xuyên nhưng ý thường hiểu được. | Kiểm soát tương đối mẫu thường dùng; lỗi tăng khi nói phức tạp nhưng ý định rõ. | Kiểm soát ngữ pháp khá cao; lỗi hiếm khi gây hiểu nhầm và thường tự sửa được. |
| Fluency | Lượt nói ngắn; có khoảng dừng, bắt đầu lại hoặc diễn đạt lại rõ. | Duy trì được lời nói; vẫn có khoảng dừng để lên kế hoạch trong đoạn dài. | Nhịp tương đối đều ở đoạn dài; ít khoảng dừng dài nổi bật. |
| Coherence | Nối từ/câu bằng từ nối phổ biến; trình bày như các ý đơn giản. | Nối các ý ngắn thành chuỗi tuyến tính dễ theo dõi. | Dùng phương tiện liên kết để phát triển và hỗ trợ ý rõ ràng. |
| Phonology | Nhìn chung hiểu được; đôi lúc cần lặp, ảnh hưởng stress/rhythm/intonation có thể tăng effort. | Nhìn chung intelligible; ảnh hưởng L1 còn nghe thấy nhưng không cản trở thông điệp. | Âm rõ; stress/intonation hỗ trợ thông điệp; accent ít ảnh hưởng intelligibility. |

Hai prompt là độc thoại nên `Interaction` không được chấm và hệ thống giữ `null` với `insufficient_evidence`. Overall là điểm/band của bài, không hiển thị thành năm điểm tiêu chí trên báo cáo người học.

## 3. Kế hoạch thu

- **Thiết kế:** nghiên cứu cắt ngang; mỗi bài là một đơn vị phân tích và được máy cùng hai giám khảo chấm độc lập, blind với kết quả của nhau.
- **Bài của mỗi người:** một prompt trải nghiệm cá nhân và một prompt nêu ý kiến; 30 giây chuẩn bị, mỗi bài 40–60 giây.
- **Đối tượng:** sinh viên đại học Việt Nam, từ 18 tuổi, trình độ ước lượng A2–B2.
- **Quy mô:** mục tiêu 60–90 người, sàn 60; pilot usability 6–8 người trước, không nhập pilot vào tập chính.
- **Rater gate:** SCRUM-89 tập huấn hai giám khảo trước khi chấm; dùng mẫu chuẩn và kiểm agreement theo kế hoạch nguồn. Không bắt đầu chấm chính thức khi chưa đạt gate đã thống nhất.
- **Consent/data:** dùng hai lựa chọn tách biệt cho lưu audio và dùng cho nghiên cứu; cấp pseudonym; bảng ánh xạ danh tính giữ ngoài hệ thống; công bố quyền rút lui và thời hạn lưu 12 tháng. Không commit audio, PII hay dữ liệu người tham gia.
- **Kiểm tra bài lỗi:** nghe lại tại buổi thu; cho ghi lại nếu file hỏng hoặc dưới ngưỡng theo quy trình. Ghi thiết bị/môi trường khi không đồng nhất.
- **Giới hạn phân tích:** kế hoạch này chỉ báo các RQ1–RQ4 trong `KE_HOACH_KHAO_SAT.md`. Không tuyên bố Task C/Interaction hoặc parallel-form reliability/RQ6.
- **Trạng thái chạy:** chưa tuyển người, chưa thu audio, chưa tạo dữ liệu nghiên cứu; mọi metric thực nghiệm giữ `NOT_EVALUATED`.

## 4. Thay đổi trên giao diện

- Local demo seed hai prompt trên với version và thời lượng được lưu cùng task.
- Phiếu chấm mù hiển thị rubric A2/B1/B2, hướng dẫn chấm độc lập và `Interaction=null/insufficient_evidence` cho độc thoại.
- Browser evidence được lưu tại [SCRUM-88 browser report](../../sdd/modules/m13-learning-evidence/evidence/scrum-88/report.md).
