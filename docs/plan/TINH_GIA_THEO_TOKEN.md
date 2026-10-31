# Bảng giá kênh tính lượt (D057)

**Trạng thái:** team đã chốt mức giá ngày 24/10/2026 (theo chủ dự án). Trong decision log, D057 vẫn ghi PROPOSED, chờ người có thẩm quyền ghi APPROVED. Thay phần bảng giá của D049 trên bản triển khai tính lượt (kênh NetID). Bản của trường và nghiên cứu không tính gì (BR-29, BR-30).

## Bảng giá đã chốt

Quy ước 1 IDPoint = 1 đồng (NetID chưa công bố tỷ giá).

| Loại bài | Lượt | IDPoint |
| --- | --- | --- |
| Đánh giá tới 1 phút | 1 | 2.000 |
| Mỗi phút bắt đầu thêm, tối đa 5 phút | +0,7 | +1.400 (5 phút: 7.600) |
| Luyện tập | 50% của bài đánh giá cùng thời lượng | 1.000 cho bài tới 1 phút |
| Bản nâng cấp do AI viết (D072) | 0,3 | 600 |
| Miễn phí mỗi chu kỳ (từ ngày 16) | 3 | 6.000 |
| Gói bán trực tiếp | 10 / 30 / 100 lượt | 19.000 / 49.000 / 149.000 đồng |

- **Thu và hoàn:** chỉ thu khi bài có kết quả; bài lỗi, quá hạn hay bị từ chối thì hoàn hết. Giữ chỗ theo thời lượng tối đa của đề. Trang Nộp bài báo trước "bài này tối đa X lượt (Y IDPoint)".
- **Token:** đo và ghi kèm từng bút toán (token âm thanh và token chữ của Whisper) để tính giá vốn và đối soát với NetID. Không dùng để tính giá. Người học chỉ thấy lượt và IDPoint.

| Biến | Ý nghĩa | Mặc định |
| --- | --- | --- |
| `AICEFR_PRICE_FIRST_MINUTE_RUNS` | Lượt cho bài tới 1 phút | 1,0 |
| `AICEFR_PRICE_EXTRA_MINUTE_RUNS` | Lượt cho mỗi phút bắt đầu thêm | 0,7 |
| `AICEFR_PRICE_PRACTICE_FACTOR` | Phần bài luyện tập phải trả | 0,5 |
| `AICEFR_IDPOINT_PER_RUN` | IDPoint cho 1 lượt | 2.000 |
| `AICEFR_PRICE_UPGRADE_RUNS` | Lượt cho một bản nâng cấp do AI viết (D072); 0 là miễn phí | 0,3 |
| `AICEFR_COACH_GLOBAL_DAILY` | Tổng số bản nâng cấp mới của cả hệ thống trong 24 giờ, dưới hạn mức miễn phí của nhà cung cấp | 400 |
| `AICEFR_CREDIT_PACKS` | Gói bán trực tiếp, `lượt:giá_đồng` | `10:19000,30:49000,100:149000` |

**Bản nâng cấp do AI viết (D072).** Giá tính theo bản, không theo token: giữ 0,3 lượt trước khi gọi mô hình, trừ khi AI viết xong, trả lại nếu mô hình lỗi; bản đã viết xem lại không tốn thêm. Số token vào/ra mà nhà cung cấp báo được ghi kèm bút toán (cột `input_tokens`, `output_tokens`, hành động `upgrade`) để tính giá vốn: một bản khoảng 2.000–3.000 token vào và 500–800 token ra. Ngoài giới hạn mỗi người (`AICEFR_COACH_DAILY`, 5/ngày) còn giới hạn chung `AICEFR_COACH_GLOBAL_DAILY` (400/24 giờ) để không vượt hạn mức miễn phí của Gemini 3.5 Flash-Lite (khoảng 500 lượt/ngày). Tắt tính lượt thì chỉ còn hai giới hạn này.

**Bật trên máy chủ.** Mặc định kênh tính lượt TẮT (bản của trường không tính gì). Trước 31/10/2026, `docker-compose.yml` không chuyển các biến trên vào container, nên đặt trong `.env` cũng không có tác dụng; nay đã chuyển cho core và web. Muốn bật: trong `/srv/aicefr/.env` đặt `AICEFR_METERING=1` (bán gói lượt thì cần thêm `AICEFR_BILLING=1` và một cổng thanh toán), rồi chạy lại `docker compose ... up -d core web`. Khi bật sẽ có menu "Lượt của tôi" (`/credits`), trang Nộp bài báo trước số lượt và IDPoint, và bài chỉ bị trừ lượt khi đã có kết quả.

Còn phải hỏi NetID: tỷ giá IDPoint thật, phần trăm NetID giữ lại, có cho giữ chỗ rồi hoàn phần thừa không. Các mục dưới là research và các phương án đã cân nhắc trước khi chốt.

## 0. Thị trường tính tiền thế nào (research ngày 24/10/2026)

| Nhóm dịch vụ | Cách tính | Mức tham chiếu | Nguồn |
| --- | --- | --- | --- |
| Mô hình ngôn ngữ, mô hình chép lời kiểu GPT-4o | Theo token: giá riêng cho 1 triệu token input (âm thanh, chữ) và output | GPT-4o Transcribe: trang mô hình ghi giá theo 1 triệu token; bảng giá chép lại và trang tổng hợp quy ra khoảng 0,006 USD/phút, ngang Whisper | [OpenAI](https://developers.openai.com/api/docs/models/gpt-4o-transcribe), [bảng giá chép lại](https://www.scribd.com/document/859642842/Pricing-OpenAI-API), [lmmarketcap](https://lmmarketcap.com/openai-whisper-pricing) (bên thứ ba) |
| Chép lời chuyên dụng | Theo thời lượng âm thanh (giây, phút, giờ) | Deepgram tính theo giây, Nova-3 khoảng 0,0077 USD/phút; AssemblyAI khoảng 0,15–0,45 USD/giờ | [Deepgram](https://www.activepieces.com/blog/deepgram-pricing-2026-per-minute-rates-and-add-ons.md), [so sánh](https://costbench.com/compare/assemblyai-vs-deepgram) (bên thứ ba) |
| Chấm phát âm | Phụ phí cộng thêm trên giá chép lời, theo giờ | Azure Pronunciation Assessment khoảng 0,30 USD/giờ cộng vào khoảng 1 USD/giờ chép lời thời gian thực (nguồn chưa thống nhất) | [Developers Digest](https://www.developersdigest.tech/models/speech/azure), [Microsoft Q&A](https://learn.microsoft.com/en-us/answers/questions/5608069/pricing-and-usage-of-pronunciation-assessment-feat) |
| API chấm nói (Speechace) | Gói theo tháng, chia hạng theo tính năng (BASIC, PRO, PREMIUM) | Trang công khai không ghi giá; trang tổng hợp ghi "từ 40 USD/tháng" | [tài liệu Speechace](https://developers.qodex.ai/speechace-s-public/speechace-api), [FitGap](https://us.fitgap.com/products/speechace-api) |
| Ứng dụng cho người học (ELSA) | Thuê bao: miễn phí, Pro, Premium | Không tìm được giá chính thức 1 năm tại Việt Nam | [ELSA](https://eikaiwa.weblio.jp/ninja-eikaiwa/elsaspeak-pricing) |
| SaaS có AI nói chung | Kết hợp (hybrid): phí nền hoặc gói, kèm tín dụng trả trước, có trần và cảnh báo | Khoảng 60–65% nhà cung cấp dùng hybrid; nhiều người mua từng bị hoá đơn AI bất ngờ | [Solvimon](https://www.solvimon.com/blog/ai-credit-pricing-models-how-tokens-credits-hybrid-billing-work), [HubSpot](https://blog.hubspot.com/website/ai-credits-buyers-guide) (blog của bên bán phần mềm tính tiền) |

Rút ra:
1. Bên bán **hạ tầng** cho lập trình viên tính theo token hoặc theo giây, vì người mua là kỹ sư, đọc được đơn vị đó.
2. Bên bán **sản phẩm** cho người học bán theo gói hoặc theo lượt, không bao giờ cho người học thấy token.
3. Token âm thanh tỷ lệ với thời lượng, nên tính theo token và tính theo phút gần như tương đương; token chỉ khác ở chỗ có thêm phần output.

## Đề xuất

**Đo bằng token, bán bằng lượt, cấu trúc kết hợp.**

1. **Đo nội bộ theo token (đã làm, D057).** Mỗi bài ghi token input và output thật. Đó là cơ sở để tính giá vốn, đối soát với NetID, và đổi giá mà không phải sửa mã.
2. **Người học chỉ thấy "lượt".** Đơn giá theo token quy ra lượt; mặc định một bài 1 phút khoảng 1 lượt. Trang Lượt của tôi vẫn hiện số token từng bài cho ai muốn kiểm tra, nhưng không bắt ai phải hiểu token.
3. **Ba tầng giá:**
   - 3 lượt miễn phí mỗi chu kỳ;
   - gói lượt trả trước (D053), gói lớn rẻ hơn mỗi lượt;
   - với trường: gói theo số sinh viên có kèm hạn mức (D033/D034).
4. **Đặt giá theo hai đầu:**
   - **sàn** là giá vốn đo được trên máy chủ thật (mục 6) cộng phần NetID giữ;
   - **trần** là giá tham chiếu thị trường: chép lời cộng chấm phát âm của các nền tảng lớn quanh 0,01 USD mỗi phút âm thanh.

   Giá bán nằm giữa và dựa trên giá trị riêng của sản phẩm: band CEFR có khoảng tin cậy, nhận xét có bằng chứng, giảng viên duyệt. Không cạnh tranh bằng giá thô.
5. **Chống hoá đơn bất ngờ:**
   - giữ chỗ trước khi chấm;
   - hoàn ngay phần thừa;
   - nhắc khi sắp hết lượt (D055);
   - nên thêm: hiện "bài này tối đa X lượt" ngay trên trang Nộp bài trước khi ghi âm.

Tỷ giá dùng 26.100 đồng/USD; giá vốn tự chạy tính ở mục "Chi phí hạ tầng trên EC2". Các con số thị trường ở trên đa số lấy từ trang tổng hợp của bên thứ ba, cần đối chiếu lại trang giá chính thức trước khi đưa vào báo cáo.

## Đề xuất giá trên NetID (giả định 1 IDPoint = 1 đồng)

NetID chưa công bố tỷ giá; IDPoint "không có giá trị quy đổi". Phần này **giả định 1 IDPoint = 1 đồng** theo yêu cầu của chủ dự án ngày 24/10/2026. Gợi ý duy nhất cho giả định này là phí duy trì tài khoản "thông thường là 30k" mỗi tháng.

**Quy đổi:** 1 lượt = **2.000 IDPoint**; mỗi phút thêm 0,7 lượt.

| Loại bài | Lượt (giá mặc định) | Giá trên NetID |
| --- | --- | --- |
| Đánh giá tới 1 phút | ~1,0 | **2.000 IDPoint** |
| Đánh giá 2 phút | ~1,7 | ~3.400 IDPoint |
| Đánh giá 5 phút (tối đa) | ~3,8 | ~7.600 IDPoint |
| Luyện tập tới 1 phút | ~0,5 | **1.000 IDPoint** |
| 3 lượt miễn phí mỗi chu kỳ | 3 | tặng, trị giá 6.000 IDPoint |

**Vì sao 2.000:**
- *Mặt bằng NetID:* AI Chat 200, Writer 350, File 1.000; tầng giữa 2.000–5.000 (MoA, AI Pic, Deep Research 2.500, War Room 3.000); tầng phân tích 15.000–50.000. Một bài chấm có band CEFR, khoảng tin cậy và nhận xét có bằng chứng ngang tầng MoA hay AI Pic, nhẹ hơn tầng phân tích.
- *Sức mua của sinh viên:* phí duy trì 30.000 đồng một tháng. 10 bài đánh giá cộng 10 bài luyện tập mỗi tháng là 30.000 IDPoint, bằng đúng một tháng phí duy trì.
- *Chi phí và lãi:* chạy thật W6-S03 (whisper-small, faster-whisper, Apple M5) hết 13,8 giây cho một bài, kể cả nạp mô hình. Theo benchmark công khai quy ra EC2 c7i.xlarge, phần máy chỉ khoảng 30–115 đồng một bài (mục "Chi phí hạ tầng trên EC2"). So với thị trường, API chép lời cộng chấm phát âm khoảng 0,01 USD mỗi phút, tức khoảng 260 đồng. 2.000 IDPoint vẫn còn biên rộng sau phần NetID giữ lại (**[CẦN HỎI]** NetID). Giá trị bán ra là phần CEFR, không phải chi phí máy.

**Phương án khác:**
- **1.000 IDPoint/bài** nếu muốn kéo người dùng nhanh lúc ra mắt; bài luyện tập 500.
- **3.000 IDPoint/bài** nếu sau thu thử W7 tỷ lệ bài phải chuyển giảng viên thấp và báo cáo được đánh giá cao.

Nên ra mắt ở **2.000** kèm 3 lượt miễn phí, và xem lại sau một chu kỳ (ngày 16) bằng ba số:
- tỷ lệ người dùng hết lượt miễn phí rồi nạp tiếp;
- số bài trung bình mỗi người;
- giá vốn mỗi bài đo được (mục 6).

**Đồng bộ với gói lượt bán trực tiếp (D053):** giá hiện tại 10 lượt 49.000 đồng tức 4.900 đồng một lượt, đắt hơn NetID 2,45 lần. Nên hạ cho thống nhất, có giảm giá khi mua nhiều: 10 lượt 19.000 đồng, 30 lượt 49.000 đồng, 100 lượt 149.000 đồng (biến `AICEFR_CREDIT_PACKS`).

## Chi phí hạ tầng trên EC2 (ước lượng ngày 24/10/2026)

**Đo được trên máy thật** (Apple M5, faster-whisper 1.2.1, whisper-small int8, 4 luồng, bản ghi giọng tổng hợp W6-S03):

| Bản ghi | Nhận dạng | Kiểm tra ngôn ngữ | Token chữ |
| --- | --- | --- | --- |
| 42,7 giây | 4,13 giây | 0,68 giây | 150 |
| 85,4 giây | 9,43 giây | 0,70 giây | 294 |

Tăng lên 8 luồng không nhanh hơn trên máy này.

**Quy ra EC2 bằng benchmark công khai (không cần đo lại):**
- README faster-whisper đo đúng cấu hình đang chạy (whisper-small, int8, beam 5) trên **Intel Xeon Gold 6226R 8 luồng**, chip máy chủ cùng họ với EC2: 13 phút âm thanh hết 2 phút 04 giây. Tức mỗi giây âm thanh tốn khoảng **0,16 giây máy**.
- c7i.xlarge có 4 vCPU (2 nhân vật lý, Sapphire Rapids), ít nhân hơn nhưng mỗi nhân nhanh hơn 6226R. Ước khoảng **0,25–0,32 giây máy mỗi giây âm thanh**. Một bài 1 phút tốn 15–19 giây nhận dạng, cộng khoảng 2 giây kiểm tra ngôn ngữ và 2 giây QC, VAD, đặc trưng, chấm điểm, tức **20–23 giây máy mỗi bài**.
- GPU T4 (g4dn): README đo large-v2 int8 trên RTX 3070 Ti là 13 phút âm thanh trong 59 giây. small nhanh hơn khoảng 4 lần, T4 chậm hơn 3070 Ti khoảng 2 lần, nên mỗi bài khoảng **5 giây**. Một báo cáo cộng đồng đo 93 giây âm thanh hết 24 giây trên g4dn.xlarge (không ghi mô hình), tức tới **15 giây** mỗi bài trong trường hợp xấu.
- Tỷ giá 26.100 đồng/USD (giá bán Vietcombank 20/10/2026).

Số đo trên Apple M5 ở trên (0,11 giây máy mỗi giây âm thanh) khớp với hướng này: M5 nhanh hơn Xeon 2019.

**Giá EC2 Singapore:** theo bảng giá tổng hợp của DoiT, cần đối chiếu trang AWS.

| Instance | Cấu hình | Theo giờ | Spot thấp nhất | Bài mỗi giờ (1 worker) | Giá vốn mỗi bài, chạy kín | Chạy 30% công suất |
| --- | --- | --- | --- | --- | --- | --- |
| c7i.xlarge | 4 vCPU, 8 GiB | 0,2058 USD | 0,0916 | ~160–180 | **~30–34 đồng** (spot ~13–15) | ~100–115 đồng |
| c7i.2xlarge | 8 vCPU, 16 GiB | 0,4116 USD | 0,1763 | ~320–360 (2 worker) | ~30–34 đồng | ~100–115 đồng |
| g4dn.xlarge | 4 vCPU, T4 16 GiB | 0,7360 USD | 0,3088 | ~240–700 | ~27–80 đồng (spot ~11–34) | ~90–270 đồng |
| Lambda (không giữ máy) | 4 GB, khoảng 30 giây mỗi bài | 0,0000166667 USD / GB-giây | — | tự co giãn | **~52 đồng**, không tốn khi không ai dùng | ~52 đồng |

**Chi phí thật nằm ở phần cố định**, không ở từng bài. Cộng cả phần chạy 24/7 thì giá vốn mỗi bài như sau:

| Bài mỗi tháng | Gói 1: một c7i.xlarge chạy tất cả (~4,2 triệu/tháng) | Gói 2: core c7i.large + worker c7i.xlarge (~6,1 triệu/tháng) | Gói 3: core c7i.large + worker Lambda (~2,2 triệu/tháng + 52 đồng/bài) |
| --- | --- | --- | --- |
| 1.000 | 4.182 đồng | 6.143 đồng | 2.274 đồng |
| 3.000 | 1.394 đồng | 2.048 đồng | 793 đồng |
| 10.000 | 418 đồng | 614 đồng | 274 đồng |
| 50.000 | 84 đồng | 123 đồng | 97 đồng |
| **Hoà vốn ở giá 2.000 IDPoint/bài** | ~2.100 bài/tháng | ~3.100 bài/tháng | ~1.150 bài/tháng |
| Hoà vốn nếu NetID giữ 30% (thu về 1.400) | ~3.000 bài/tháng | ~4.400 bài/tháng | ~1.650 bài/tháng |

Phần cố định gồm core, web, MongoDB, Redis, ổ EBS và S3. Gói 1 dồn tất cả vào một máy, hợp cho giai đoạn thử, nhưng chấm bài sẽ tranh CPU với cơ sở dữ liệu. GPU (g4dn chạy 24/7, khoảng 14 triệu đồng một tháng) chỉ đáng khi trên khoảng 100.000 bài mỗi tháng.

**Đề xuất hạ tầng:**
- **Ra mắt bằng gói 1** (một c7i.xlarge), hoặc **gói 3** nếu chấp nhận thêm việc đóng gói Whisper vào Lambda và độ trễ khởi động nguội vài giây.
- Khi đều trên khoảng 3.000 bài mỗi tháng thì tách worker (gói 2), sau đó dùng spot cho worker. Worker an toàn khi chạy spot vì BullMQ thử lại việc của worker bị thu hồi (D050).
- **Giá bán không đổi: 2.000 IDPoint mỗi bài.** Giá vốn phần máy chỉ vài chục đến vài trăm đồng mỗi bài; rủi ro thật là số bài mỗi tháng không đủ để gánh phần cố định.
- Theo cách tính token (mục 3), giá vốn khoảng 30 đồng cho 4.500 token âm thanh, tức khoảng **6.600 đồng cho 1 triệu token âm thanh khi chạy kín** (khoảng 22.000 đồng ở 30% công suất), so với giá bán 2.000 IDPoint cho một bài 1 phút (khoảng 4.500 token âm thanh).

Nguồn:
- [faster-whisper benchmark](https://github.com/SYSTRAN/faster-whisper) (Xeon Gold 6226R, RTX 3070 Ti)
- [Báo cáo cộng đồng trên g4dn.xlarge](https://github.com/openai/whisper/discussions/716)
- [c7i.xlarge](https://www.doit.com/compute/spot/ap-southeast-1/c7i.xlarge), [c7i.2xlarge](https://www.doit.com/compute/spot/ap-southeast-1/c7i.2xlarge), [g4dn.xlarge](https://www.doit.com/compute/spot/ap-southeast-1/g4dn.xlarge) (DoiT, bên thứ ba)
- [Lambda pricing](https://www.eon.io/blog/aws-lambda-pricing) (bên thứ ba)
- [tỷ giá Vietcombank 20/10/2026](https://webgia.com/ty-gia/vietcombank/20-10-2026.html)

## 1. Bài toán

Nhóm muốn tính tiền như API mô hình ngôn ngữ: mỗi yêu cầu có token input và token output, mỗi loại một đơn giá cho 1 triệu token, người bán tự chỉnh đơn giá. Ví dụ trong nhóm: 4 đô cho 1 triệu token input và 2 đô cho 1 triệu token output.

Câu hỏi khó là **token ở đâu ra**: hệ thống không gọi mô hình ngôn ngữ nào, nên không có số token để tính. Tự tách chữ thành token theo một bộ tách tự chọn thì con số không gắn với chi phí thật, và ai cũng hỏi được "sao lại là chừng này token".

## 2. Lời giải: dùng token thật của Whisper

Bộ nhận dạng giọng nói Whisper chính là một mô hình token, và là phần tốn máy nhất của pipeline. Nó có sẵn cả hai loại token:

| Loại | Đếm thế nào | Vì sao đúng |
| --- | --- | --- |
| **Input: token âm thanh** | 1.500 token cho mỗi cửa sổ 30 giây bắt đầu, thêm 1 cửa sổ cho bước kiểm tra ngôn ngữ (D022) | Whisper luôn cắt âm thanh thành cửa sổ 30 giây, cửa sổ cuối được đệm đủ 30 giây, mỗi cửa sổ thành đúng 1.500 vị trí của bộ mã hoá (50 mỗi giây). Đây là khối việc bộ mã hoá thật sự làm, không phụ thuộc người nói nói gì |
| **Output: token chữ** | Số token bộ giải mã sinh ra, do chính bộ nhận dạng đếm (`Transcript.output_tokens`, cộng `tokens` của từng đoạn ở cả `mlx_whisper` và `faster_whisper`) | Bộ giải mã sinh từng token một, nên thời gian giải mã tỷ lệ với số token này |

Nhờ vậy không phải tự viết bộ tách token: input cố định theo thiết kế của Whisper, output do mô hình báo. Bộ nhận dạng giả trong test không đếm được token, nên output được ước lượng từ số từ (4 token cho 3 từ) và bút toán ghi `usage_estimated = true`.

## 3. Công thức (phương án tính theo token, không chọn)

Team chọn bán theo bài, nên công thức này chỉ còn dùng để ước giá vốn theo token. Các biến `AICEFR_PRICE_INPUT_PER_M`, `AICEFR_PRICE_OUTPUT_PER_M`, `AICEFR_PRICE_MIN_RUNS` dưới đây không có trong bản cài đặt cuối.

```
token_input  = 1500 × (số cửa sổ 30 giây bắt đầu + 1)     # tối đa 300 giây
token_output = số token bộ giải mã đã sinh

phí (lượt) = max(sàn, token_input × giá_input / 1.000.000 + token_output × giá_output / 1.000.000)
phí bài luyện tập = phí × hệ số luyện tập
làm tròn lên 1/1000 lượt
```

Ví lưu số nguyên phần nghìn lượt, nên không có sai số làm tròn khi cộng dồn.

**Người bán tự đặt giá** bằng biến môi trường, không cần sửa mã:

| Biến | Ý nghĩa | Mặc định |
| --- | --- | --- |
| `AICEFR_PRICE_INPUT_PER_M` | Lượt cho 1 triệu token âm thanh | 200 |
| `AICEFR_PRICE_OUTPUT_PER_M` | Lượt cho 1 triệu token chữ | 600 |
| `AICEFR_PRICE_MIN_RUNS` | Mức sàn mỗi bài (QC, VAD, đặc trưng, chấm điểm luôn tốn) | 0,1 |
| `AICEFR_PRICE_PRACTICE_FACTOR` | Bài luyện tập trả bao nhiêu phần | 0,5 |

Giá output đặt cao hơn input vì bộ giải mã chạy tuần tự từng token, còn bộ mã hoá xử lý cả cửa sổ một lần. Mặc định được chọn để một bài đánh giá 1 phút vẫn khoảng **1 lượt**, giữ cách hiểu "1 lượt ≈ 1 bài" quen thuộc với NetID.

## 4. Ví dụ theo phương án token

| Bài | Token input | Token output | Phí |
| --- | --- | --- | --- |
| Đánh giá 35 giây, khoảng 75 từ (100 token) | 1500 × (2 + 1) = 4.500 | 100 | 0,9 + 0,06 = **0,96 lượt** |
| Đánh giá 60 giây, 170 token | 4.500 | 170 | 0,9 + 0,102 = **1,002 lượt** |
| Đánh giá 2 phút, 340 token | 1500 × (4 + 1) = 7.500 | 340 | 1,5 + 0,204 = **1,704 lượt** |
| Luyện tập 60 giây, 170 token | 4.500 | 170 | 1,002 × 0,5 = **0,501 lượt** |

Với giá trong ví dụ của nhóm (4 và 2 cho 1 triệu token), bài 60 giây là 4.500 × 4 / 10⁶ + 170 × 2 / 10⁶ ≈ 0,0183. Riêng con số "1.000 input + 1.000 output ≈ 0,002" trong tin nhắn là chưa đúng: theo đúng giá đó thì ra 0,004 + 0,002 = **0,006**.

## 5. Giữ chỗ và chốt (bản cài đặt)

- **Khi nộp:** giữ chỗ theo thời lượng tối đa của đề; trang Nộp bài báo trước con số này. Không đủ lượt thì HTTP 402.
- **Khi có kết quả:** thu theo thời lượng thật, trả phần thừa ngay, vào ví trước rồi tới lượt miễn phí.
- **Khi lỗi:** hoàn hết.
- **Lịch sử:** mỗi bút toán ghi số token input, output và có phải ước lượng không, để tính giá vốn và đối soát với NetID. Trang **Lượt của tôi** chỉ hiện lượt và IDPoint.

## 6. Đặt giá từ chi phí thật (khuyến nghị)

Token chỉ là đơn vị đo. Mức giá nên đi từ chi phí máy, theo bốn bước:

1. **Đo.** Chạy thử khoảng 100 bài trên máy chủ thật. Lấy thời gian xử lý mỗi bài từ Prometheus (`aicefr_job_seconds`, D051) và số token của bài đó từ sổ lượt (`usage_ledger`).
2. **Tách chi phí theo loại token.** Hồi quy tuyến tính `thời_gian ≈ a × token_input + b × token_output + t0`.
3. **Đổi ra tiền.** Gọi `c` là chi phí máy mỗi giây (giá thuê máy mỗi giờ ÷ 3.600 ÷ tỷ lệ máy bận). Khi đó:
   - giá vốn input = `c × a × 10⁶` cho 1 triệu token;
   - giá vốn output = `c × b × 10⁶`;
   - sàn = `c × t0`.
4. **Đặt giá bán.** Giá bán = giá vốn × (1 + biên lợi nhuận) + phần NetID giữ lại, rồi chia cho giá một lượt để ra số lượt cho 1 triệu token. Mỗi lần đổi giá, đổi phiên bản trong `PriceList.version`; bút toán cũ vẫn giữ phiên bản cũ.

Ước lượng hiện tại theo benchmark công khai: trên c7i.xlarge, `c` ≈ 0,2058 USD/giờ; `a` ≈ 4 giây máy cho mỗi 1.000 token âm thanh (0,25–0,32 giây cho mỗi giây âm thanh, 50 token mỗi giây); `t0` ≈ 2–4 giây. Phần output nhỏ so với input. `tools/bench_asr.py` vẫn có sẵn nếu muốn kiểm chéo trên máy thật, nhưng không bắt buộc để chốt giá.

## 7. Giới hạn

- Token input tính theo cửa sổ, nên bài 31 giây và 60 giây cùng giá input. Đó đúng là việc Whisper làm (cửa sổ cuối được đệm). Nếu muốn mịn hơn, có thể tính 50 token mỗi giây thật, nhưng khi đó giá không còn khớp với chi phí.
- Khi Whisper giải mã lại ở nhiệt độ cao hơn, số token bị bỏ không được đếm, vì bộ nhận dạng chỉ trả token của lần giải mã giữ lại. Phần tốn thêm này nằm trong mức sàn và biên lợi nhuận.
- Kênh NetID vẫn chưa có API IDPoint: cộng lượt hiện qua quản trị viên hoặc gói lượt (D053), chỉ ở chế độ thử.
