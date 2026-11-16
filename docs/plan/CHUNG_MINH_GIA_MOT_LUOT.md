# Vì sao 1 lượt chấm bài nói có giá 2.000 đồng

*Lập ngày 16/11/2026. Quyết định liên quan: D057, D106, D107 (`docs/sources/research-preparation/21_week1_decision_log.md`). Bảng giá đang áp dụng và các biến cấu hình: [TINH_GIA_THEO_TOKEN.md](TINH_GIA_THEO_TOKEN.md).*

> **Dành cho người và AI viết báo cáo đồ án.** Đây là nguồn chuẩn cho mọi con số về giá một lượt, chi phí và điểm hoà vốn.
> - Chép số từ các bảng dưới đây, giữ nguyên đơn vị và mức làm tròn. Mỗi số đã ghi cách tính và nguồn [1]–[10].
> - Không tự ước lượng lại, không thay tỷ giá hay giá dịch vụ khác nếu chưa cập nhật file này.
> - Phân biệt **số đo trên production** (thời gian chấm, số token AI viết lại) với **ước lượng** (đoạn đọc AI, bản nháp của giảng viên, giá ổ đĩa ở Sydney). Mục 7 liệt kê các giới hạn; báo cáo nên nêu lại chúng.
> - Đổi giá trên dashboard hay đổi hạ tầng thì cập nhật file này cùng lúc.

## 1. Kết luận

**Một lượt bán 2.000 đồng (gói nhỏ nhất 5 lượt = 10.000 đồng); mua gói lớn thì từ 1.490 đến 1.900 đồng.** Một lượt gồm: chấm một bài nói bằng mô hình fine-tune, AI viết lại chính bài đó, và một đoạn đọc AI.

### 1.1 Cộng toàn bộ chi phí

Tính theo tháng, máy chủ chạy suốt 24/7. Tỷ giá 26.020 đ/USD.

| Khoản | Cách tính | Mỗi tháng |
| --- | --- | --- |
| **A. Chi phí cố định** | | |
| Máy chủ EC2 m7i-flex.large (Sydney) | 730 giờ × 0,1197 USD | 87,38 USD ≈ 2.273.700 đ |
| Ổ đĩa EBS gp3 40 GB | 40 GB × 0,10 USD (mức dự phòng) | 4,00 USD ≈ 104.100 đ |
| Địa chỉ IPv4 công khai (Elastic IP) | 730 giờ × 0,005 USD | 3,65 USD ≈ 95.000 đ |
| Tên miền speakup.fit | 45,98 USD/năm ÷ 12 | 3,83 USD ≈ 99.700 đ |
| Gửi email (Resend), thanh toán (payOS), CI (GitHub Actions), huấn luyện mô hình (Kaggle) | Đang trong gói miễn phí | 0 đ |
| **Cộng A** | | **98,86 USD ≈ 2.572.400 đ** |
| **B. Chi phí biến đổi mỗi lượt** (mức xấu nhất, mục 3) | | |
| CPU chấm một bài 60 giây | 0,1197 USD ÷ 3.600 × 60 | 52 đ |
| AI viết lại bài (đo thật, lấy lần cao hơn trong 2 lần đo) | 560 token vào, 754 token ra | 53 đ |
| Một đoạn đọc AI (trần) | 400 token vào, 1.200 token ra | 81 đ |
| **Cộng B** | | **187 đ mỗi lượt** |

**Tổng chi phí của một lượt = 187 đ + 2.572.400 đ ÷ số lượt bán trong tháng.**

| Lượt bán mỗi tháng | Chi phí thật của một lượt | So với giá bán |
| --- | --- | --- |
| 1.000 | 2.759 đ | Lỗ ở mọi gói |
| **1.419** | **2.000 đ** | **Hoà vốn ở gói 5 lượt (2.000 đ/lượt)** |
| 2.000 | 1.473 đ | Có lãi ở mọi gói, kể cả gói 100 lượt (1.490 đ) |
| 3.000 | 1.044 đ | Có lãi |
| 5.000 | 701 đ | Có lãi |

### 1.2 Vì sao 2.000 đ là hợp lý

1. **Che đủ chi phí biến đổi:** 187 đ mỗi lượt, chỉ chiếm 9–13 % giá bán.
2. **Hoà vốn ở lượng bán vừa phải:** khoảng 1.400–2.000 lượt mỗi tháng (47–66 lượt mỗi ngày). Giảm còn 1.000 đ thì phải bán khoảng 3.200–4.600 lượt mới hoà vốn.
3. **Rẻ cho sinh viên:** nói 1 bài mỗi ngày (gói 30 lượt) hết 49.000 đ/tháng.
4. **Dễ nhớ:** "mỗi bài nói 1 lượt = 2.000 đ", khớp quy ước 1 IDPoint = 1 đồng (D057).

Nếu chỉ bật máy chủ 8 giờ mỗi ngày khi demo, chi phí cố định còn khoảng 40,21 USD ≈ 1.046.300 đ/tháng, và hoà vốn chỉ cần khoảng 580–800 lượt.

## 2. Một lượt gồm những gì (D107)

| Việc | Chạy ở đâu | Có tốn tiền mỗi lần không |
| --- | --- | --- |
| Kiểm tra chất lượng âm thanh, Whisper chép lời, trích đặc trưng, chấm bằng `fusion_resp_v4` | Máy chủ EC2 của nhóm | Tốn CPU máy chủ |
| AI viết lại bài nói lên band cao hơn (một bản mỗi bài) | Gemini 3.5 Flash-Lite (API trả theo token) | Tốn tiền API |
| Một đoạn đọc AI quanh các từ nói chưa rõ | Gemini 3.5 Flash-Lite | Tốn tiền API |

Những thứ **không** tính vào giá lượt:

- **Luyện trong lộ trình** (tối đa 30 lần ghi âm mỗi ngày): chỉ qua Whisper và luật đếm từ, không qua mô hình chấm hay mô hình ngôn ngữ.
- **Giảng viên soạn bài bằng AI** (5 bản mỗi ngày): hệ thống trả, tính vào chi phí vận hành ở mục 4.

## 3. Chi phí biến đổi của một lượt

### 3.1 Số liệu đầu vào

| Đại lượng | Giá trị | Nguồn |
| --- | --- | --- |
| Tỷ giá | 26.020 đ/USD (Vietcombank bán ra, 24/10/2026) | [1] |
| Máy chủ m7i-flex.large (2 vCPU, 8 GB), Sydney, theo giờ | 0,1197 USD/giờ | [2] |
| Gemini 3.5 Flash-Lite | 0,30 USD / 1 triệu token vào; 2,50 USD / 1 triệu token ra | [3]; cũng là giá mặc định trong cấu hình (`AICEFR_COACH_PRICE_*`) |
| Thời gian chấm một bài trên production | 20 giây cho bài dài 27,9 giây: nộp lúc 04:59:01, có điểm lúc 04:59:21 ngày 16/11/2026 | Đo trên production [7] |
| Token của một lần AI viết lại | Lần 1 (10/11): 530 vào, 639 ra, 0,001757 USD. Lần 2 (16/11): 560 vào, 754 ra, 0,002053 USD | Đo trên production [7] |
| Giới hạn token ra của một đoạn đọc | 1.200 token | Mã nguồn `coach/passage.py` (`MAX_OUTPUT_TOKENS`) |
| Phí cổng thanh toán payOS | Gói BIDV-1K miễn phí, 1.000 giao dịch/năm, áp dụng đến 31/12/2026; trang không nêu phí theo giao dịch | [4] |

### 3.2 Tính chi phí

Mọi phép tính đều lấy mức **xấu nhất**, để giá không bị đặt quá thấp.

| Thành phần | Cách tính | USD | Đồng |
| --- | --- | --- | --- |
| CPU máy chủ cho một bài | Bài dài nhất 60 giây; tính 60 giây máy (thực đo: 20 giây cho bài 28 giây). 0,1197 / 3.600 × 60 | 0,00200 | **52** |
| AI viết lại | Lần đo cao hơn: 560 × 0,30/10⁶ + 754 × 2,50/10⁶ | 0,00205 | **53** |
| Đoạn đọc AI | Trần: 400 token vào (ước lượng) + 1.200 token ra (giới hạn trong mã) | 0,00312 | **81** |
| Lưu ghi âm | Khoảng 1 MB mỗi bài | ≈ 0 | **< 1** |
| Phí thanh toán | Trong gói miễn phí của payOS | 0 | **0** |
| **Cộng** | | **≈ 0,0072** | **≈ 187** |

### 3.3 Lãi gộp mỗi lượt theo gói

| Gói | Giá | Giá mỗi lượt | Lãi gộp mỗi lượt | Tỷ lệ |
| --- | --- | --- | --- | --- |
| 5 lượt | 10.000 đ | 2.000 đ | 1.813 đ | 90,6 % |
| 10 lượt | 19.000 đ | 1.900 đ | 1.713 đ | 90,2 % |
| 30 lượt | 49.000 đ | 1.633 đ | 1.446 đ | 88,5 % |
| 100 lượt | 149.000 đ | 1.490 đ | 1.303 đ | 87,4 % |

## 4. Chi phí cố định và điểm hoà vốn

| Khoản | Mỗi tháng | Nguồn |
| --- | --- | --- |
| Máy chủ chạy suốt tháng: 730 giờ × 0,1197 USD | 87,38 USD ≈ 2.273.700 đ | [2] |
| Ổ đĩa EBS gp3 40 GB (cấu hình máy production): 40 × 0,10 USD; giá Mỹ là 0,08 USD/GB, Sydney cao hơn nên lấy mức dự phòng | 4,00 USD ≈ 104.100 đ | [10] |
| Elastic IP: 0,005 USD/giờ × 730 giờ (AWS tính cả khi máy tắt nếu vẫn giữ IP) | 3,65 USD ≈ 95.000 đ | [8] |
| Tên miền `.fit`: 45,98 USD/năm khi gia hạn | 3,83 USD ≈ 99.700 đ | [9] |
| Resend (3.000 thư/tháng), payOS (1.000 giao dịch/năm), GitHub Actions, Kaggle | 0 đ (gói miễn phí) | [4] |
| **Cộng** | **98,86 USD ≈ 2.572.400 đ** | |
| Lượt miễn phí: 3 lượt mỗi tài khoản đã xác minh email × 187 đ | ≤ 561 đ mỗi tài khoản | |
| Giảng viên soạn bài AI miễn phí: 5 bản/ngày, khoảng 100–260 đ mỗi bản (ước lượng, chưa đo) | ≤ 1.300 đ mỗi giảng viên mỗi ngày | |

Số lượt cần bán để hoà vốn:

- **Bán theo gói 100 lượt (1.490 đ/lượt):** 2.572.400 / 1.303 ≈ **1.974 lượt/tháng**, khoảng 66 lượt mỗi ngày.
- **Bán theo gói nhỏ nhất (2.000 đ/lượt):** 2.572.400 / 1.813 ≈ **1.419 lượt/tháng**, khoảng 47 lượt mỗi ngày.

Bảng này chưa tính công phát triển của nhóm, vì đó là công sức làm đồ án, không phải tiền trả ra ngoài.

## 5. Vì sao không chọn giá khác

| Phương án | Hệ quả |
| --- | --- |
| **1.000 đ/lượt** | Gói rẻ nhất còn khoảng 745 đ/lượt. Khi chi phí lên khoảng 387 đ (kịch bản xấu nhất ở mục 6), lãi gộp chỉ còn khoảng 48 %. Hoà vốn cần khoảng 4.600 lượt/tháng (2.572.400 / 558), gấp hơn 2 lần mức 2.000 đ. |
| **2.000 đ/lượt (chọn)** | Lãi gộp 87–91 %. Hoà vốn khoảng 1.400–2.000 lượt/tháng. Con số tròn, khớp 1 IDPoint = 1 đồng. |
| **5.000 đ/lượt** | Nói 1 bài mỗi ngày tốn tới 150.000 đ/tháng (gói nhỏ nhất), cao hơn chi phí tháng của ELSA Pro (khoảng 91.000 đ). Sinh viên sẽ ngại luyện đều. |

So sánh với thị trường:

- **ELSA Pro 1 năm: 1.095.000 đ** [5]. ELSA bán thuê bao theo thời gian, không bán theo lượt. Để so được hai cách bán, quy về chi phí mỗi tháng của một người học đều đặn: ELSA Pro khoảng 91.000 đ/tháng; SpeakUp, 1 bài mỗi ngày với gói 30 lượt, **49.000 đ/tháng**. Khác biệt: lượt SpeakUp không hết hạn và chỉ trừ khi bài được chấm; mỗi bài có điểm CEFR theo 5 tiêu chí và giảng viên duyệt.
- **Azure Speech, chấm phát âm: khoảng 1,32 USD mỗi giờ âm thanh** [6]. Một bài 60 giây tốn khoảng 0,022 USD, tức **≈ 570 đ**, mới chỉ là tiền gọi API và chưa có điểm CEFR. SpeakUp tự chạy Whisper và mô hình chấm trên máy chủ của nhóm, nên phần này chỉ tốn khoảng 52 đ.

## 6. Độ nhạy: chi phí tăng thì sao

| Kịch bản | Chi phí biến đổi mỗi lượt | Lãi gộp ở gói rẻ nhất (1.490 đ) |
| --- | --- | --- |
| Cơ sở (mục 3) | 187 đ | 87,4 % |
| Tỷ giá lên 27.000 đ/USD | 194 đ | 87,0 % |
| Giá Gemini tăng gấp đôi | 321 đ | 78,5 % |
| Bài chấm lâu gấp đôi (120 giây máy) | 238 đ | 84,0 % |
| Cả ba cùng lúc | 387 đ | 74,0 % |

Ngay ở kịch bản xấu nhất, mỗi lượt vẫn lãi gộp khoảng 74 %. Vì vậy chưa cần đổi giá khi tỷ giá hay giá API dao động.

## 7. Giới hạn của phép tính

- **Thời gian chấm mới đo trên một bài thử:** 20 giây cho bài 28 giây. Phép tính đã lấy 60 giây máy để dự phòng. Cần đo thêm khi có nhiều bài thật.
- **Token của đoạn đọc chưa đo:** dùng giới hạn trên trong mã (1.200 token ra). Token đầu vào là ước lượng.
- **Bản nháp của giảng viên chưa đo trên production:** con số 100–260 đ là ước lượng.
- **Giá máy chủ và giá Gemini lấy từ trang tổng hợp**, không từ bảng giá gốc của AWS và Google. Tỷ giá lấy ngày 24/10/2026.
- **Giá ổ đĩa EBS ở Sydney chưa xác nhận:** dùng mức dự phòng 0,10 USD/GB-tháng (giá Mỹ 0,08). Phí truyền dữ liệu ra ngoài chưa tính, vì mỗi bài chỉ vài trăm KB.
- **Phí payOS khi quá 1.000 giao dịch/năm chưa rõ.** Vì vậy từ 16/11/2026, gói nhỏ nhất là 5 lượt (10.000 đ) thay vì 1 lượt: giá mỗi lượt không đổi, nhưng số giao dịch giảm khoảng 5 lần.
- **Production hiện dùng gói Gemini miễn phí**, nên tiền API thực trả hiện bằng 0. Bảng trên tính theo giá trả phí, để giá không phải đổi khi chuyển sang gói trả phí.

## 8. Nguồn

- [1] Vietbao, "Tỷ giá USD hôm nay 25/10", số liệu Vietcombank ngày 24/10/2026: https://vietbao.vn/ty-gia-usd-hom-nay-2510-ty-gia-trung-tam-giao-dich-o-muc-25627-dongusd-612906.html
- [2] Giá m7i-flex.large theo vùng: https://aws-pricing.com/m7i-flex.large.html và https://instances.vantage.sh/aws/ec2/m7i-flex.large
- [3] Giá Gemini 3.5 Flash-Lite: https://eesel.ai/blog/gemini-3-5-flash-lite-pricing và https://pricepertoken.com/pricing-page/model/google-gemini-3.5-flash-lite
- [4] payOS, trang chủ (gói BIDV-1K): https://payos.vn/
- [5] ELSA Speak Việt Nam, bảng giá trên trang chủ: https://vn.elsaspeak.com/en/homepage
- [6] Microsoft Learn Q&A, giá Pronunciation Assessment của Azure Speech: https://learn.microsoft.com/en-us/answers/questions/5608069/pricing-and-usage-of-pronunciation-assessment-feat
- [7] Số đo trên production https://speakup.fit: thời gian chấm bài thử b5a1f5466ee0 (16/11/2026) và số token của hai lần AI viết lại trên trang Quản trị → AI viết lại (10/11 và 16/11/2026).
- [8] AWS News Blog, phí địa chỉ IPv4 công khai 0,005 USD/giờ từ 01/02/2024: https://aws.amazon.com/blogs/aws/new-aws-public-ipv4-address-charge-public-ip-insights
- [9] Namecheap, giá tên miền .fit (gia hạn 45,98 USD/năm): https://www.namecheap.com/domains/registration/gtld/fit/
- [10] AWS, bảng giá EBS (gp3 0,08 USD/GB-tháng ở Mỹ; chưa xác nhận giá Sydney): https://aws.amazon.com/ebs/pricing
