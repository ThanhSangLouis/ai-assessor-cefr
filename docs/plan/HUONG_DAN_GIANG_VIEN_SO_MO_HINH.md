# Hướng dẫn chấm mù để chọn mô hình chấm điểm

Dành cho giảng viên chấm bài và quản trị viên điều phối. Mục tiêu: dùng điểm của giảng viên để
quyết định nên giữ mô hình chấm hiện tại (`ridge_resp_v2`) hay chuyển sang bản đã hiệu chuẩn
(`ridge_resp_v2_cal`). Quyết định liên quan: D052 (hiệu chuẩn), D030 (chấm mù), D067 (so hai mô hình
trên cùng phiếu chấm).

## 1. Vì sao cần giảng viên

Hai mô hình đọc cùng một bộ đặc trưng của bài nói, chỉ khác cách trải điểm:

| | `ridge_resp_v2` (đang chạy) | `ridge_resp_v2_cal` (bản thử) |
|---|---|---|
| Cách cho điểm | Dồn điểm về giữa thang | Kéo dãn khoảng cách giữa các bài (hệ số × 1,41) |
| Ngưỡng A2/B1 và B1/B2 | 2,75 và 3,75 | 2,65 và 3,85 |
| Sai số trên dữ liệu huấn luyện (RMSE) | 0,526 | 0,538 |
| Điểm yếu đã biết | Gần như không bao giờ cho A2 | Mới hiệu chuẩn trên dữ liệu Speak & Improve, **chưa kiểm trên giọng Việt** |

Con số trên dữ liệu huấn luyện không trả lời được câu hỏi "mô hình nào gần với giảng viên Việt
Nam hơn". Chỉ điểm của giảng viên trên bài của sinh viên thật trả lời được.

## 2. Quy trình tổng thể

1. **Quản trị viên** tạo một đợt chấm mù gồm 20–30 bài (mục 3).
2. **Mỗi bài có hai giảng viên** chấm độc lập, không thấy điểm của máy hay của nhau (mục 4).
3. Bài hai người lệch nhau từ 1 điểm hoặc khác band thì **người thứ ba phân xử**.
4. **Quản trị viên** mở báo cáo đồng thuận, cho máy chấm lại cùng các bài bằng từng mô hình, so
   với điểm giảng viên (mục 5).
5. Nhóm quyết định theo quy tắc ở mục 6, rồi quản trị viên bật mô hình được chọn (mục 7).

Không cần bật `ridge_resp_v2_cal` trước khi chấm: báo cáo chấm lại được các bài đã có bằng mô
hình nào cũng được, trên chính đặc trưng đã lưu của bài đó.

## 3. Quản trị viên: tạo đợt chấm

1. Đăng nhập tài khoản quản trị, vào **Quản trị → Chấm mù**.
2. Dòng "Bài đủ điều kiện" cho biết có bao nhiêu bài nộp (bài đánh giá, không phải bài luyện)
   chưa vào đợt nào. Nên có **ít nhất 20 bài, tốt nhất 30**, từ nhiều sinh viên và nhiều trình độ.
   Chưa đủ thì chờ thêm bài nộp.
3. Điền **Tên đợt** (ví dụ "So mô hình — tuần 9"), chọn **ít nhất hai giám khảo**, đặt **Số bài**
   là 30 (để trống là lấy tất cả), giữ ô "Chỉ bài chưa vào đợt nào".
4. Bấm **Tạo đợt**. Hệ thống tự giao mỗi bài cho hai giám khảo, xáo thứ tự riêng cho từng người.
5. Báo giảng viên vào trang **Chấm mù** và hạn chót.

## 4. Giảng viên: chấm từng phiếu

Vào **Chấm mù** ở thanh bên (địa chỉ `/rate`). Mỗi dòng là một phiếu. Mở từng phiếu:

1. **Đọc đề bài**, rồi **nghe hết bản ghi**. Nghe lại bao nhiêu lần cũng được.
2. Chấm **năm tiêu chí** trên thang **0–6, bước 0,5**: Vốn từ, Ngữ pháp, Độ trôi chảy, Mạch lạc,
   Phát âm dễ nghe. Thang 0–6 gắn với CEFR: khoảng 2 là A2, 3 là B1, 4 là B2, 5 là C1. Mô tả từng
   band ở trang `/bands`.
3. Cho **điểm tổng** (0–6, bước 0,5) và chọn **band** (A1–C2). Điểm tổng là đánh giá chung của
   bạn, không bắt buộc bằng trung bình năm tiêu chí.
4. Ghi **một dòng lý do**, ví dụ "ý rõ, ngập ngừng nhiều ở nửa sau".
5. Bấm **Nộp phiếu**. **Phiếu đã nộp không sửa được**, nên kiểm lại trước khi nộp.

Không chấm được (bản ghi hỏng, không nghe rõ, nói sai đề) thì đánh dấu **"Không chấm được bài này"**
và chọn lý do, không đoán điểm.

### Quy tắc để kết quả dùng được

- **Không mở báo cáo hay hàng đợi duyệt của bài đang chấm mù.** Hệ thống chặn sẵn; nếu bạn đã
  thấy điểm máy của một bài, phiếu đó mất hiệu lực và được giao cho người khác.
- **Không trao đổi điểm với giám khảo khác** trước khi cả hai đã nộp.
- **Chấm theo mô tả CEFR, không theo cảm giác so với bài trước.** Thứ tự bài đã xáo để giảm ảnh
  hưởng này.
- **Mỗi lượt khoảng 10–15 bài** rồi nghỉ. Chấm mệt làm điểm trôi dần.
- Mỗi bài thường mất 2–3 phút. Hệ thống ghi thời gian chấm để báo cáo, không dùng để đánh giá
  giảng viên.

## 5. Quản trị viên: đọc kết quả

Khi các phiếu đã nộp đủ, bài lệch đã được giao phân xử (nút **Giao phân xử** ở dòng của đợt) và người thứ ba đã nộp phiếu, mở
**Báo cáo** của đợt.

**Mục 1 — Hai giám khảo với nhau.** Đọc mục này trước. Hai người phải đủ thống nhất thì điểm
của người mới làm thước đo cho máy được. Mốc kế hoạch: kappa band ≥ 0,70 và ICC điểm tổng ≥ 0,75.
Dưới mốc thì nhóm giảng viên nên thống nhất lại cách hiểu thang điểm (nghe chung vài bài mẫu) và
chấm thêm, trước khi dùng mục 2.

**Mục 2 — Máy so với người.** Ô **Điểm máy** có ba lựa chọn:

- *Như lúc chấm*: điểm máy đã cho khi bài được nộp;
- *Chấm lại bằng ridge_resp_v2*: chấm lại các bài này bằng mô hình hiện tại;
- *Chấm lại bằng ridge_resp_v2_cal*: chấm lại các bài này bằng bản hiệu chuẩn.

Chọn lần lượt hai mô hình và ghi lại vào bảng sau:

| Chỉ số | `ridge_resp_v2` | `ridge_resp_v2_cal` | Tốt hơn khi |
|---|---|---|---|
| Kappa có trọng số bậc hai, band | | | cao hơn |
| Pearson | | | cao hơn |
| RMSE | | | thấp hơn |
| Recall band A2 | | | cao hơn |
| Recall band B2 | | | cao hơn |
| Số bài bỏ ra khi chấm lại (ghi chú cuối báo cáo) | | | — |

Bài nói dài (P5, chấm theo từng khung) và bài không có đặc trưng đã lưu không chấm lại được; báo
cáo ghi rõ số bài này.

## 6. Quy tắc quyết định

Chọn `ridge_resp_v2_cal` khi **cả ba** điều sau đúng:

1. Mục 1 đạt mốc (hai giám khảo đủ thống nhất);
2. Kappa band của `ridge_resp_v2_cal` **cao hơn** `ridge_resp_v2`;
3. RMSE của `ridge_resp_v2_cal` **không cao hơn quá 0,05 điểm**.

Ngược lại thì giữ `ridge_resp_v2`. Với 20–30 bài, khoảng tin cậy trong báo cáo còn rộng: chênh
lệch nhỏ hơn độ rộng khoảng tin cậy thì coi là **chưa phân biệt được**, giữ mô hình hiện tại và
chấm thêm một đợt nữa.

Ghi kết quả và quyết định vào nhật ký quyết định (D067), kèm tên đợt.

## 7. Bật hoặc quay lại mô hình

1. **Quản trị → Mô hình**, bấm **Kích hoạt** ở dòng `ridge_resp_v2_cal`.
2. Chỉ bài nộp **từ lúc đó** được chấm bằng mô hình mới. Bài cũ giữ nguyên điểm và ghi rõ đã được
   chấm bằng mô hình nào.
3. Muốn quay lại, kích hoạt lại `ridge_resp_v2`. Mỗi lần đổi được ghi vào nhật ký kiểm toán.

Không cần deploy hay khởi động lại máy chủ.

## 8. Dữ liệu cá nhân

Giọng nói là dữ liệu cá nhân (Nghị định 13/2023). Chỉ nghe bản ghi trong hệ thống, không tải về
máy riêng hay gửi qua chat. Bản xuất CSV của đợt chấm có bút danh giám khảo và điểm, chỉ dùng
trong nhóm.
