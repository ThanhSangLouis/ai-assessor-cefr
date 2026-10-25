# Kế hoạch thu dữ liệu và kiểm định trên sinh viên Việt Nam

> Mục đích: biến câu "hệ thống chấm được" thành một con số có thể bảo vệ được
> trước hội đồng, đo trên chính đối tượng mà đề tài nhắm tới.
>
> Tài liệu này là **giao kèo với chính nhóm**: ngưỡng chấp nhận được ghi ra
> **trước** khi thu dữ liệu, và nhóm cam kết báo cáo kết quả dù nó rơi vào phía
> nào của ngưỡng.

---

## 1. Vì sao phải làm, nói thẳng

Mô hình đang chạy có ba điểm yếu mà không một dòng mã nào chữa được:

| Điểm yếu | Con số | Hệ quả |
|---|---|---|
| Huấn luyện trên người học **không phải người Việt** | Speak & Improve 2025, 876 bài / 438 người nói | Không ai biết nó có giữ độ chính xác trên giọng Việt hay không |
| **Chưa hiệu chuẩn** | `calibration_version = "chua-hieu-chuan"` | Điểm số có thể lệch hệ thống cả nửa band mà vẫn tương quan tốt |
| **Kém nhất đúng ở band thấp** | A2 chỉ nhận đúng 16,7%; xếp sai band 26,6% | Nhóm sinh viên cần giúp nhất lại bị chấm sai nhiều nhất |

Tương quan chéo hiện tại là PCC 0,6966 và RMSE 0,5262 (GroupKFold 5 theo người
nói). Đó là con số trên tập nước ngoài. **Chưa có một con số nào trên sinh viên
Việt Nam.** Khảo sát này sinh ra con số đó.

---

## 2. Câu hỏi nghiên cứu

- **RQ1.** Điểm tổng thể do hệ thống sinh tương quan tới mức nào với điểm do hai
  giám khảo người chấm độc lập trên bài nói của sinh viên Việt Nam?
- **RQ2.** Tỷ lệ xếp đúng band A2/B1/B2 là bao nhiêu, và **riêng từng band** là
  bao nhiêu?
- **RQ3.** Sau khi hiệu chuẩn trên chính dữ liệu này, sai số giảm được bao nhiêu?
- **RQ4.** Cơ chế chuyển giảng viên có bắt đúng những bài mà máy chấm sai không?
  (Nếu cờ chuyển giảng viên không tương quan với sai số thì nó vô dụng.)

---

## 3. Thiết kế

**Kiểu.** Nghiên cứu cắt ngang, đo đồng thời: mỗi bài nói được chấm song song
bởi **máy** và **hai giám khảo người**, hai bên không thấy kết quả của nhau.

**Đơn vị phân tích.** *Một bài nói*, đúng bằng đơn vị suy luận của mô hình
(`unit_of_inference` trong artifact). Không gộp thành điểm của cả buổi thi.

**Mỗi sinh viên nói 2 bài** với hai đề khác nhau, cùng dạng độc thoại:
- một đề mô tả trải nghiệm cá nhân,
- một đề nêu ý kiến về một chủ đề quen thuộc.

**Thời lượng 40–60 giây mỗi bài.** Không phải con số tuỳ tiện: dải bài mà mô
hình được huấn luyện là 26,7–60,7 giây. Nói 3 phút là tự đẩy bài ra ngoài phân
bố huấn luyện rồi trách máy chấm sai.

---

## 4. Cỡ mẫu và phân tầng

**Mục tiêu 60–90 sinh viên, sàn cứng 60** (QĐ-03). Với 2 bài/người: 120–180 bài.

**Phân tầng theo trình độ ước lượng ban đầu**, lấy từ điểm học phần tiếng Anh
gần nhất hoặc bài kiểm tra xếp lớp của trường:

| Tầng | Mục tiêu | Vì sao |
|---|---|---|
| A2 | **≥ 25 người** | Đây là band máy đang chấm tệ nhất; muốn đo được cải thiện thì phải có đủ mẫu |
| B1 | 20–30 người | Band đông nhất trong thực tế |
| B2 | ≥ 15 người | Đủ để phát hiện hiệu ứng trần |

**Độ chính xác thật sự đạt được — nói trước để không ai kỳ vọng sai:**

- Với 60 người nói, nếu PCC quan sát được là 0,70 thì khoảng tin cậy 95% là
  **[0,54 ; 0,81]** (biến đổi Fisher z, SE = 1/√57). Đây là một khoảng rộng.
  Nó đủ để kết luận "có tương quan mạnh", **không** đủ để so sánh hai mô hình
  chênh nhau 0,03.
- Với 20 người mỗi band, tỷ lệ nhận đúng band ước lượng được với sai số khoảng
  **±0,21**. Đủ để phát hiện "A2 đang hỏng nặng", không đủ để nói "A2 đạt 78%
  chứ không phải 72%".

Viết thẳng hai giới hạn này vào báo cáo cuối. Một đồ án nói rõ mình đo được đến
đâu đáng tin hơn một đồ án báo cáo bốn chữ số thập phân.

---

## 5. Quy trình thu dữ liệu

### 5.1. Trước buổi thu

1. Sinh viên đọc và ký **bản đồng thuận** (phụ lục A), chọn riêng hai mục: cho
   phép lưu audio, và cho phép dùng cho nghiên cứu.
2. Cấp **bút danh** dạng `SV-###`. Bảng ánh xạ bút danh ↔ tên thật nằm **ngoài
   hệ thống**, trên giấy, do một người giữ (FR-33).
3. Ghi siêu dữ liệu không định danh: khoá học, trình độ ước lượng ban đầu, thiết
   bị ghi âm, phòng thu.

### 5.2. Trong buổi thu

1. Một bài **tập thử 20 giây** không tính điểm, để sinh viên quen với nút ghi âm
   và mức micro.
2. Đọc đề, cho **30 giây chuẩn bị**, rồi ghi âm 40–60 giây.
3. Phòng yên tĩnh, cùng một loại tai nghe có micro cho tất cả nếu có thể. Nếu
   không đồng nhất được thì **ghi lại thiết bị** để phân tích sau.
4. Nghe lại ngay: nếu bài bị `AUDIO_TOO_SHORT` hoặc `AUDIO_UNSUPPORTED` thì cho
   ghi lại tại chỗ. Không mang về mới phát hiện hỏng.

### 5.3. Thu thử trước

**Bắt buộc chạy thử với 6–8 sinh viên trước khi thu chính thức.** Mục đích không
phải lấy dữ liệu mà để phát hiện: đề bài có mơ hồ không, 40–60 giây có đủ không,
micro phòng đó có ồn không, luồng đồng thuận có vướng không. Dữ liệu thu thử
**không** trộn vào tập chính.

---

## 6. Chấm bởi người — phần quyết định chất lượng cả nghiên cứu

Toàn bộ giá trị của khảo sát nằm ở chỗ điểm người chấm có đáng tin hay không.
Nếu hai giám khảo không đồng ý với nhau thì việc máy "đồng ý với người" chẳng
còn nghĩa gì.

### 6.1. Giám khảo

- **Hai giám khảo độc lập** cho mọi bài, chấm mù: không biết bút danh, không
  biết trình độ ước lượng ban đầu, **không thấy điểm của máy**, không thấy điểm
  của nhau.
- Thứ tự bài được **xáo ngẫu nhiên** cho từng giám khảo, để hiệu ứng mệt mỏi
  không rơi cùng vào một nhóm bài.
- Giám khảo thứ ba chỉ vào cuộc khi cần phân xử (mục 6.4).

### 6.2. Đào tạo giám khảo

1. Đọc thang chấm (phụ lục B): 5 tiêu chí, thang 0–6, mô tả từng mức.
2. Chấm **10 bài mẫu chuẩn** đã có điểm đồng thuận từ trước, thảo luận từng chỗ
   lệch.
3. Chỉ bắt đầu chấm thật khi đạt **kappa có trọng số ≥ 0,70** trên bộ mẫu đó.
   Chưa đạt thì huấn luyện lại, không "chấm đại rồi chỉnh sau".

### 6.3. Đo độ tin cậy giữa hai giám khảo

| Chỉ số | Ngưỡng chấp nhận | Ghi chú |
|---|---|---|
| Kappa có trọng số bậc hai (band) | **≥ 0,70** | dưới ngưỡng thì dữ liệu không dùng để kết luận được |
| ICC(2,1) trên điểm 0–6 | **≥ 0,75** | đo mức đồng thuận tuyệt đối, không chỉ thứ hạng |
| Tỷ lệ trùng khớp tuyệt đối về band | báo cáo, không đặt ngưỡng | để hội đồng tự đọc |

### 6.4. Phân xử

Bài nào hai giám khảo lệch **≥ 1,0 điểm trên thang 0–6** hoặc **lệch band** thì
chuyển giám khảo thứ ba. Điểm cuối là **trung vị của ba** điểm, không phải trung
bình — trung vị không bị một người chấm lệch kéo đi.

### 6.5. Điểm đối chiếu dùng để so với máy

Bài không phải phân xử: **trung bình hai giám khảo**. Bài phải phân xử: trung vị
ba giám khảo. Ghi rõ bài nào thuộc loại nào khi báo cáo.

---

## 7. Phân tích

### 7.1. Chỉ số chính

| Chỉ số | Tính trên | Báo cáo kèm |
|---|---|---|
| PCC | điểm tổng 0–6 | khoảng tin cậy 95% bootstrap **theo người nói**, không theo bài |
| RMSE | điểm tổng 0–6 | khoảng tin cậy 95% |
| QWK | band A2/B1/B2 | ma trận nhầm lẫn 3×3 đầy đủ |
| Độ chính xác band **từng band** | riêng A2, B1, B2 | recall và precision mỗi band |

**Bootstrap phải lấy mẫu lại theo người nói, không theo bài.** Hai bài của cùng
một người không độc lập; lấy mẫu theo bài sẽ cho khoảng tin cậy hẹp giả tạo.

### 7.2. Chỉ số phụ

- Tương quan từng tiêu chí trong năm tiêu chí CEFR.
- **Kiểm chứng cơ chế chuyển giảng viên (RQ4):** so sai số tuyệt đối của nhóm bị
  gắn cờ với nhóm không bị gắn cờ. Nếu sai số hai nhóm như nhau thì cờ đang gắn
  nhầm chỗ và phải thiết kế lại `ReviewRouter`.
- Tỷ lệ bài rơi ngoài phân bố huấn luyện, và đặc trưng nào gây ra.

### 7.3. Hiệu chuẩn

1. Chia dữ liệu theo **người nói**, 5 fold — không bao giờ để hai bài của cùng
   một người rơi vào cả tập huấn luyện lẫn tập kiểm.
2. Khớp hồi quy đẳng hướng (isotonic) từ điểm máy sang điểm người, **chỉ trên
   fold huấn luyện**.
3. Ước lại hai ngưỡng band trên fold huấn luyện.
4. Báo cáo cải thiện trên fold kiểm, kèm khoảng tin cậy.
5. Nếu đạt, xuất artifact mới với `calibration_version` ghi ngày và cỡ mẫu, rồi
   kích hoạt qua chức năng ở mục 3.5 của `SPEC_HOAN_THIEN.md`.

### 7.4. Việc phải làm trước khi phân tích

Mô hình hiện được huấn luyện trên đặc trưng trích bằng Whisper **small**, còn hệ
thống chạy **large-v3-turbo**; chênh lệch đo được là +0,0198 ở độ tin cậy trung
bình (t = 4,64; p = 1e-5). **Trích lại đặc trưng của toàn bộ tập huấn luyện bằng
đúng mô hình đang chạy và huấn luyện lại**, nếu không thì không biết sai số đến
từ mô hình chấm hay từ việc đổi bộ nhận dạng.

---

## 8. Ngưỡng cam kết — ghi trước, không sửa sau

Đưa vào **Bản cam kết sản phẩm cuối** ký với GVHD trước hết tuần 7:

| Chỉ số | Ngưỡng đạt | Ngưỡng tối thiểu chấp nhận được |
|---|---|---|
| PCC với điểm người | ≥ 0,70 | ≥ 0,60 |
| RMSE | ≤ 0,60 | ≤ 0,75 |
| Trùng band tuyệt đối | ≥ 70% | ≥ 60% |
| Recall band A2 | ≥ 60% | ≥ 45% |
| Kappa giữa hai giám khảo | ≥ 0,70 | — không đạt thì **huỷ phân tích**, thu lại |

**Cam kết kèm theo:** nhóm báo cáo đúng con số đo được, kể cả khi dưới ngưỡng.
Một đồ án báo cáo "PCC 0,52, chưa đạt cam kết, nguyên nhân là …" trung thực hơn
và được rubric đánh giá cao hơn một đồ án lặng lẽ đổi ngưỡng sau khi thấy kết
quả.

---

## 9. Đạo đức và pháp lý

- Tham gia **tự nguyện**, không gắn với điểm học phần, rút lúc nào cũng được mà
  không cần nêu lý do.
- Giọng nói là **dữ liệu cá nhân** theo Luật 91/2025/QH15 và Nghị định
  356/2025/NĐ-CP. Không đẩy audio, bản chép lời hay `aicefr.db` lên git.
- Lưu trữ/xóa: thời hạn chưa được chốt trong chính sách dữ liệu hiện hành; mốc
  tối đa **12 tháng mới là đề xuất**, không phải cam kết đã duyệt. Ứng dụng hiện
  chưa tự động xóa audio theo lịch. Trước khi thu dữ liệu thật, GVHD cần chốt
  thời hạn và cách xóa. Khi người tham gia tắt lưu audio hoặc rút đồng ý, hệ
  thống chặn các lần nộp mới nhưng **không tự xóa audio đã lưu**; yêu cầu xóa
  bản đã lưu được gửi tới GVHD hoặc người phụ trách dự án. Không bắt đầu thu
  thật trước khi chính sách này được chốt và thông tin liên hệ được điền vào
  bản đồng thuận.
- Chỉ ba thành viên nhóm truy cập dữ liệu thô. Bảng ánh xạ danh tính do **một**
  người giữ, ngoài hệ thống.
- Tập Speak & Improve có giấy phép **phi thương mại, không phát tán lại**: mỗi
  người tự đăng ký tài khoản, không chia sẻ tệp cho nhau.
- Sinh viên tham gia được xem kết quả của chính mình, kèm câu nói rõ đây là công
  cụ hỗ trợ học tập, **không phải chứng chỉ**.

---

## 10. Rủi ro và phương án

| Rủi ro | Dấu hiệu sớm | Phương án |
|---|---|---|
| Không tuyển đủ 60 người | Hết tuần 9 mà dưới 35 người | Mở rộng sang lớp tiếng Anh khác; giảm còn 1 bài/người để đổi lấy số người — **giữ số người, hy sinh số bài**, vì khoảng tin cậy phụ thuộc số người nói |
| Hai giám khảo không đồng thuận nổi (kappa < 0,70) | Ngay ở bộ 10 bài mẫu | Huấn luyện lại bằng bộ mẫu khác; nếu vẫn hỏng thì xem lại mô tả thang chấm, đừng đổ cho giám khảo |
| Lệch tầng, gần như toàn B1 | Sau thu thử | Chủ động mời sinh viên năm nhất chưa qua học phần tiếng Anh để bù tầng A2 |
| Bản ghi ồn, hỏng hàng loạt | Trong thu thử | Chuẩn hoá một loại tai nghe; kiểm `/readyz` và nghe lại ngay tại buổi thu |
| Nhiều bài rơi ngoài phân bố huấn luyện | Tỷ lệ cờ ngoài phân bố > 20% | Xem lại đề bài và thời lượng trước khi đổ cho mô hình |
| Không kịp trước tuần 12 | Hết tuần 10 chưa chấm xong 50% | Cắt phần hiệu chuẩn, báo cáo kết quả thô kèm lý do — **không** cắt phần chấm kép |

---

## 11. Lịch

| Tuần | Việc | Ai | Đầu ra |
|---|---|---|---|
| 6 | Hoàn thiện đồng thuận trong hệ thống; soạn đề bài, thang chấm, bản đồng thuận | Nguyên (hệ thống), Sang (biểu mẫu) | Phụ lục A, B ký duyệt |
| **7** | **Ký bản cam kết + bộ metric với GVHD** | Cả nhóm | Mốc chặn của rubric |
| 7 | Thu thử 6–8 sinh viên, đào tạo giám khảo | Sang, Thắng | Báo cáo thu thử |
| 8–9 | Thu chính thức đợt 1 (≈ 40 người) | Cả nhóm | 80 bài |
| 9 | Chấm kép đợt 1, đo kappa | Hai giám khảo | Bảng điểm + kappa |
| 10 | Thu đợt 2 (≈ 25 người), chấm kép | Cả nhóm | Đủ 60–90 người |
| 10 | Trích lại đặc trưng bằng large-v3-turbo, huấn luyện lại | Thắng | Artifact `v4` |
| 11 | Phân tích chính, hiệu chuẩn, **báo cáo thực nghiệm người dùng** | Thắng, Lê | Đầu ra rubric mục 10 |
| 12 | Kích hoạt mô hình đã hiệu chuẩn, đo lại trên hệ thống thật | Nguyên | Báo cáo cuối |

---

## Phụ lục A — Nội dung bản đồng thuận (rút gọn)

Ghi đúng những điều này, bằng tiếng Việt, một trang:

1. Tôi được mời ghi âm **2 bài nói tiếng Anh, mỗi bài 40–60 giây**.
2. Bản ghi được dùng để **kiểm định một hệ thống chấm điểm tự động**; tôi hiểu
   đây là **công cụ hỗ trợ học tập, không phải chứng chỉ**.
3. Tôi chọn riêng: ☐ cho phép lưu bản ghi ☐ cho phép dùng cho nghiên cứu.
4. Bản ghi gắn với **bút danh**, không gắn tên tôi trong hệ thống.
5. Tôi có thể rút đồng ý bất cứ lúc nào mà **không ảnh hưởng tới điểm học
   phần**. Việc rút đồng ý chặn các lần nộp mới nhưng không tự xóa bản ghi đã
   lưu; đầu mối yêu cầu xóa phải được ghi trong phiếu sau khi chính sách được
   chốt.
6. Thời hạn lưu/xóa và đầu mối yêu cầu xóa phải được chốt, ghi đúng trong bản
   đồng thuận trước khi mời người tham gia; ứng dụng hiện chưa tự động xóa
   audio theo lịch.
7. Tôi được xem kết quả chấm của chính mình.

## Phụ lục B — Phiếu chấm của giám khảo

Mỗi bài, mỗi giám khảo ghi: mã bài (đã xáo), 5 tiêu chí × thang 0–6
(Range, Accuracy, Fluency, Coherence, Phonology), điểm tổng 0–6, band
A2/B1/B2, một dòng lý do, và ô "không chấm được" kèm lý do (bản ghi hỏng, không
nghe rõ, nói sai đề).

**Giám khảo không được thấy:** bút danh, trình độ ước lượng ban đầu, điểm của
máy, điểm của giám khảo còn lại.

## Phụ lục C — Hai đề bài

- **Đề 1 (trải nghiệm).** "Kể về một lần bạn học được điều gì đó mới ngoài
  trường lớp. Bạn đã học gì, học như thế nào, và vì sao nó đáng nhớ?"
- **Đề 2 (ý kiến).** "Có ý kiến cho rằng sinh viên nên đi làm thêm trong lúc
  học. Bạn đồng ý hay không, và vì sao?"

Cả hai đề: 30 giây chuẩn bị, nói 40–60 giây, không đọc văn bản viết sẵn.
