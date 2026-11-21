# Bộ tiêu chí chấm bài nói theo 5 tiêu chí CEFR (Rubric R5)

| Thuộc tính | Giá trị |
| --- | --- |
| Phiên bản | 1.0 |
| Ngày | 17/11/2026 |
| Phạm vi | M05 (chấm điểm); quyết định D110 |
| Người giao | Chủ dự án (Võ Thanh Sang) |
| Dùng cho | Người chấm khi tạo bộ điểm từng tiêu chí; cơ sở để huấn luyện và kiểm định mô hình chấm từng tiêu chí |
| Nguồn | Council of Europe (2020), *CEFR Companion Volume*: bảng đặc điểm định tính của ngôn ngữ nói (Range, Accuracy, Fluency, Coherence) và các thang kiểm soát âm vị học (Phonological control). ALTE (2014), *CEFR Grid for Speaking Tests*. Mô tả dưới đây là bản diễn giải tiếng Việt, không chép nguyên văn. |

## 1. Vì sao cần bộ này

Speak & Improve Corpus 2025 chỉ có **điểm tổng** cho mỗi phần thi, không có điểm riêng cho từng tiêu chí (QD-04, `docs/sources/scoring-audit.md`). Vì vậy hệ thống hiện chỉ chấm một điểm tổng. Năm tiêu chí trên báo cáo của học viên chỉ là **chỉ số mô tả** (`CriterionIndicator`), không phải điểm.

Muốn chấm thật từng tiêu chí thì trước hết phải có điểm do người chấm theo một bộ tiêu chí cố định. Tài liệu này là bộ tiêu chí đó, kèm quy trình để hai người chấm ra cùng một kết quả.

## 2. Thang điểm

Mỗi tiêu chí chấm trên **thang 0–6, cho phép nửa điểm**. Đây cũng là thang của điểm tổng S&I và của `band_map.py`, nên điểm từng tiêu chí và điểm tổng so được với nhau.

| Điểm | Mức CEFR | Ý nghĩa |
| --- | --- | --- |
| 0 | dưới A1 | Không có tiếng Anh chấm được: im lặng, chỉ nói tiếng Việt, hoặc vài từ rời không thành ý |
| 1 | A1 | Khớp mô tả A1 |
| 2 | A2 | Khớp mô tả A2 |
| 3 | B1 | Khớp mô tả B1 |
| 4 | B2 | Khớp mô tả B2 |
| 5 | C1 | Khớp mô tả C1 |
| 6 | C2 | Khớp mô tả C2 |
| x,5 | giữa hai mức | Vượt rõ mức dưới, có một phần đặc điểm của mức trên nhưng chưa ổn định suốt bài |

**Cách chọn điểm:** bắt đầu từ mức mà bài nói khớp **ổn định** (đúng ở phần lớn bài, không phải một câu hay nhất). Có dấu hiệu mức trên nhưng chưa đều thì cộng 0,5. Không trừ điểm vì một lỗi đơn lẻ.

## 3. Mô tả từng mức

### 3.1 Range: Phạm vi ngôn ngữ

*Câu hỏi khi chấm:* người nói có đủ từ và cấu trúc để nói điều mình muốn không, hay phải né, nói vòng, lặp lại?

| Điểm | Mô tả |
| --- | --- |
| 1 | Chỉ có vốn từ và cụm từ rất cơ bản về bản thân và những thứ cụ thể. Chủ yếu là từ đơn và cụm học thuộc. |
| 2 | Dùng các mẫu câu cơ bản, cụm từ và công thức học thuộc để nói được ít thông tin trong tình huống quen thuộc hằng ngày. Thường phải bỏ bớt ý vì thiếu từ. |
| 3 | Đủ vốn để xoay xở và nói được về chủ đề quen thuộc (gia đình, sở thích, học tập, du lịch, sự việc gần đây), dù còn ngập ngừng và phải nói vòng. Từ ngữ lặp lại nhiều. |
| 4 | Đủ phạm vi để mô tả rõ và nêu quan điểm về phần lớn chủ đề chung mà không phải dừng tìm từ thấy rõ. Dùng được một số câu phức (mệnh đề quan hệ, câu điều kiện, bị động). |
| 5 | Phạm vi rộng. Chọn được cách diễn đạt phù hợp để nói rõ ý mà không phải thu hẹp điều muốn nói. Dùng từ chính xác, có cụm từ cố định tự nhiên. |
| 6 | Diễn đạt lại một ý bằng nhiều cách để thể hiện sắc thái, nhấn mạnh, phân biệt và tránh mơ hồ. Dùng được thành ngữ và lối nói thông tục. |

### 3.2 Accuracy: Độ chính xác ngữ pháp

*Câu hỏi khi chấm:* ngữ pháp đúng đến đâu, và lỗi có làm người nghe hiểu sai không?

| Điểm | Mô tả |
| --- | --- |
| 1 | Kiểm soát rất hạn chế một vài cấu trúc đơn giản và mẫu câu học thuộc. |
| 2 | Dùng đúng một số cấu trúc đơn giản nhưng vẫn mắc lỗi cơ bản có hệ thống: lẫn thì, thiếu chia động từ, sai hoà hợp chủ ngữ và động từ. Ý chính thường vẫn hiểu được. |
| 3 | Dùng khá chính xác các mẫu câu quen thuộc trong tình huống dễ đoán. Lỗi còn nhiều khi nói ý phức tạp hơn nhưng hiếm khi gây hiểu sai. |
| 4 | Kiểm soát ngữ pháp tương đối tốt. Không có lỗi gây hiểu lầm. Phần lớn lỗi tự nhận ra và sửa được. |
| 5 | Giữ độ chính xác cao một cách nhất quán. Lỗi hiếm, khó nhận ra, thường được tự sửa. |
| 6 | Kiểm soát ngữ pháp nhất quán ngay cả với câu phức tạp, kể cả khi đang tập trung vào việc khác như sắp xếp ý. |

### 3.3 Fluency: Độ trôi chảy

*Câu hỏi khi chấm:* lời nói chảy liền hay đứt quãng? Chỗ dừng là để nghĩ nội dung, như người bản ngữ cũng dừng, hay để tìm từ và sửa lỗi?

| Điểm | Mô tả |
| --- | --- |
| 1 | Phát ngôn rất ngắn, rời rạc, chủ yếu là cụm học sẵn. Dừng nhiều để tìm từ, đọc từ lạ hoặc sửa lỗi. |
| 2 | Làm người nghe hiểu được bằng phát ngôn rất ngắn, dù dừng, bắt đầu lại và nói lại thấy rất rõ. |
| 3 | Giữ được mạch nói dễ theo dõi, dù dừng để nghĩ ngữ pháp và từ vựng, tự sửa thấy rõ, nhất là ở đoạn nói dài. |
| 4 | Nói được những đoạn khá đều nhịp. Có thể ngập ngừng khi tìm cấu trúc hay từ nhưng ít có chỗ dừng dài thấy rõ. |
| 5 | Nói trôi chảy, tự nhiên, gần như không gắng sức. Chỉ chủ đề khó về khái niệm mới làm chậm dòng nói. |
| 6 | Nói dài trôi chảy tự nhiên. Gặp khó thì né hoặc vượt qua khéo đến mức người nghe khó nhận ra. |

### 3.4 Coherence: Độ mạch lạc và liên kết

*Câu hỏi khi chấm:* các ý có nối với nhau thành một bài không, hay chỉ là các câu rời xếp cạnh nhau?

| Điểm | Mô tả |
| --- | --- |
| 1 | Nối từ hoặc nhóm từ bằng những liên từ tuyến tính rất cơ bản như *and*, *then*. |
| 2 | Nối các nhóm từ bằng từ nối đơn giản như *and*, *but*, *because*. |
| 3 | Nối một chuỗi ý ngắn, đơn giản thành một dãy tuyến tính. Có mở và kết nhưng các ý chủ yếu đặt cạnh nhau. |
| 4 | Dùng được một số phương tiện liên kết (*however*, *for example*, *as a result*…) để nối câu thành một bài rõ ràng, mạch lạc. Ở đoạn dài có thể còn "nhảy" ý. |
| 5 | Bài nói rõ ràng, trôi, bố cục tốt; dùng có kiểm soát các cách tổ chức ý, từ nối và phương tiện liên kết. |
| 6 | Bài nói mạch lạc, gắn kết chặt; dùng đầy đủ và phù hợp nhiều cách tổ chức ý và phương tiện liên kết. |

### 3.5 Phonology: Phát âm (kiểm soát âm vị)

*Câu hỏi khi chấm:* người nghe hiểu dễ đến đâu? **Chấm theo mức dễ hiểu, không trừ điểm vì còn giọng Việt.** CEFR 2020 không lấy giọng bản ngữ làm chuẩn.

| Điểm | Mô tả |
| --- | --- |
| 1 | Phát âm được một vốn rất nhỏ từ và cụm học thuộc. Người nghe phải cố gắng nhiều, thường chỉ người quen với người Việt nói tiếng Anh mới hiểu. |
| 2 | Nhìn chung đủ rõ để hiểu dù giọng nước ngoài rõ. Người nghe đôi khi phải hỏi lại. Trọng âm, ngữ điệu, nhịp theo tiếng Việt có lúc làm khó hiểu. |
| 3 | Nhìn chung dễ hiểu. Trọng âm từ và ngữ điệu câu không cản trở hiểu, dù giọng Việt rõ. Thỉnh thoảng phát âm sai một từ. |
| 4 | Phát âm và ngữ điệu nhìn chung rõ, tự nhiên. Biết dùng trọng âm và ngữ điệu để nhấn ý. Giọng Việt còn nhưng ít ảnh hưởng mức hiểu. |
| 5 | Kiểm soát đủ các đặc điểm phát âm để luôn dễ hiểu. Dùng trọng âm và ngữ điệu thể hiện sắc thái. Vài âm còn lệch nhưng không ảnh hưởng. |
| 6 | Kiểm soát phát âm cao và tự nhiên gần như suốt bài. Ngữ điệu, trọng âm, nhịp truyền tải sắc thái tinh tế. |

## 4. Dấu hiệu thường gặp ở người Việt

Bảng này giúp người chấm nghe đúng chỗ. Dấu hiệu chỉ làm **hạ điểm khi nó lặp lại và ảnh hưởng mức hiểu hoặc mức độ chính xác**, không trừ theo từng lần xuất hiện.

| Tiêu chí | Dấu hiệu |
| --- | --- |
| Phonology | Mất phụ âm cuối (*-t, -d, -k*, *-s* số nhiều, *-ed* quá khứ); đơn giản hoá cụm phụ âm (*street*, *asked*); /θ ð/ thành /t d/; lẫn /ʃ/ với /s/; không phân biệt nguyên âm dài và ngắn (*ship/sheep*); đặt trọng âm sai; nhịp đều từng âm tiết như tiếng Việt, không nối âm. |
| Accuracy | Thiếu *-s* số nhiều và ngôi thứ ba; không đổi thì khi kể chuyện quá khứ; thiếu hoặc thừa mạo từ; *there have* thay *there is*; thiếu động từ *to be* (*I very happy*). |
| Fluency | Dừng giữa cụm từ (không phải giữa ý); lặp lại đầu câu; *uh/um* dày đặc; đọc thuộc lòng đều đều rồi khựng khi hết phần chuẩn bị. |
| Coherence | Lạm dụng *and then*, *so*, *and*; liệt kê ý không có câu dẫn hay câu kết; chuyển ý đột ngột. |
| Range | Lặp lại từ trong đề bài; dùng *very* + tính từ đơn giản thay cho từ chính xác hơn; né thì và câu phức. |

## 5. Quy tắc chấm

1. **Chấm độc lập từng tiêu chí.** Không suy điểm tiêu chí này từ tiêu chí khác, và không suy ra từ ấn tượng chung (hiệu ứng hào quang). Không lấy trung bình 5 tiêu chí làm điểm tổng.
2. **Nghe hai lượt.**
   - Lượt 1: chỉ nghe, không xem chữ. Chấm Fluency, Phonology, Coherence.
   - Lượt 2: được xem bản chép tay của corpus (không phải bản chép của máy). Chấm Range, Accuracy.
   - Bài không có bản chép tay (bài train, bài từ app): chấm cả 5 tiêu chí bằng cách nghe, được nghe lượt 3 nếu cần.
3. **Người chấm không được thấy:** điểm tổng S&I, kết quả của mô hình, điểm của người chấm kia, thông tin về người nói.
4. **Thiếu bằng chứng:** ghi `IE` thay cho điểm, không đoán.
   - Bài có dưới 20 giây nói thực hoặc dưới 30 từ: Range và Coherence ghi `IE`.
   - Bài có dưới 10 giây nói thực: cả 5 tiêu chí ghi `IE`.
5. **Không chấm, chỉ gắn cờ:**
   - `OFF_TASK`: nói lạc đề hoàn toàn;
   - `READ_ALOUD`: đọc văn bản soạn sẵn;
   - `AUDIO_BAD`: âm thanh hỏng hay nhiễu đến mức không nghe được.
6. **Trần do bài thi:** bài P3/P4 chỉ dài khoảng 40–60 giây nên ít khi đủ bằng chứng cho mức 6. Chỉ cho 6 khi đặc điểm C2 xuất hiện rõ.
7. **Tốc độ:** khoảng 3–4 phút mỗi bài. Nghỉ sau mỗi 25 bài để tránh mệt làm lệch điểm.

## 6. Quy trình để hai người chấm ra cùng kết quả

| Bước | Việc | Điều kiện qua bước |
| --- | --- | --- |
| 1. Học bộ tiêu chí | Hai người chấm đọc tài liệu này và chấm **cùng nhau** 10 bài mẫu, thảo luận đến khi thống nhất | Chọn 10 bài làm **bài mốc**: mỗi mức A2–C1 có ít nhất 2 bài |
| 2. Hiệu chuẩn | Mỗi người chấm **riêng** 20 bài mới, rồi so điểm | Mỗi tiêu chí: lệch không quá 0,5 điểm ở ≥ 80% số bài, và không quá 1 điểm ở ≥ 95%. Chưa đạt thì thảo luận chỗ lệch, sửa ghi chú ở mục 4 rồi chấm thêm 20 bài |
| 3. Chấm chính thức | Hai người chấm độc lập toàn bộ mẫu, mỗi bài được cả hai chấm | — |
| 4. Phân xử | Lệch ≤ 1 điểm: điểm cuối là trung bình hai người. Lệch > 1 điểm: người thứ ba chấm, điểm cuối là trung bình của người thứ ba và người gần người thứ ba hơn | — |
| 5. Theo dõi độ lệch | Cứ 50 bài, chấm lại 5 bài mốc ở bước 1 (trộn lẫn, không báo trước) | Lệch so với điểm mốc quá 0,5 thì dừng, hiệu chuẩn lại |

**Đo độ đồng thuận** trên điểm cuối của bước 3, tính riêng từng tiêu chí:

- **QWK (Cohen's kappa có trọng số bậc hai):** quy điểm thành số nguyên 0–12 bằng cách nhân 2 rồi mới tính. Mục tiêu ≥ 0,70.
- **Tỉ lệ bài lệch ≤ 0,5 điểm và ≤ 1 điểm.**
- Tiêu chí nào QWK < 0,60 thì **chưa đủ tin cậy để huấn luyện mô hình**. Phải sửa mô tả, hiệu chuẩn và chấm lại.

## 7. Mẫu bài cần chấm

- **Điều kiện chọn bài:** bài P3/P4 vừa có audio, vừa có bản chép tay và bản sửa lỗi ngữ pháp của corpus. Có bản chép tay thì người chấm làm được lượt 2, và tính được chỉ số Accuracy và Fluency ở mục 8.
- **Nguồn chính:** tập dev. Audio dev đã có trên máy nhóm và phần lớn người nói ở dev có đủ chú thích. **Không lấy tập eval**, để giữ eval cho lần kiểm tra cuối.
- **Mỗi người nói chỉ lấy một bài**, để mô hình không học thuộc giọng người nói.
- **Chia theo điểm tổng S&I** (người chấm không được biết bài thuộc nhóm nào):
  - nhóm 3,5 / 4,0 / 4,5 / ≥ 5,0: mỗi nhóm 40 bài;
  - nhóm ≤ 3,0: lấy hết số bài dev có đủ chú thích. Nhóm này ở dev rất ít bài, nên tổng mẫu từ dev khoảng 200 bài.
- **Bù nhóm điểm thấp (A2), là trình độ đích của đồ án:**
  - tải thêm audio tập train để lấy bài nhóm ≤ 3,0. Phần lớn bài train không có bản chép tay, nên người chấm chỉ nghe, chấm cả 5 tiêu chí ở lượt 1;
  - thêm 60 bài của sinh viên Việt Nam thu từ app (có đồng ý), để kiểm tra bộ tiêu chí trên đúng đối tượng của đồ án.
- **Khối lượng cho 200 bài dev:**
  - chấm chính thức: 200 bài × 2 người × khoảng 3,5 phút ≈ 23 giờ;
  - hiệu chuẩn (30 bài × 2 người) khoảng 3,5 giờ; phân xử khoảng 1 giờ;
  - tổng khoảng 28 giờ người chấm.
- **Giấy phép S&I:** audio chỉ được nghe trong nhóm đã đăng ký giấy phép, không gửi ra ngoài, không đăng điểm thống kê khi CUP&A chưa duyệt.

Điểm ghi vào [`phieu-cham-5-tieu-chi.csv`](phieu-cham-5-tieu-chi.csv), mỗi người chấm và mỗi bài là một dòng.

| Cột | Ý nghĩa |
| --- | --- |
| `response_id` | Mã bài trong S&I hoặc trong app |
| `speaker_id` | Mã người nói (để kiểm tra mỗi người một bài) |
| `part` | `P3`, `P4` hoặc `APP` |
| `rater_id` | `R1`, `R2`, `R3` (người phân xử) |
| `round` | `calib` (hiệu chuẩn), `main` (chính thức), `adjud` (phân xử), `drift` (chấm lại bài mốc) |
| `range`, `accuracy`, `fluency`, `coherence`, `phonology` | 0–6, bước 0,5, hoặc `IE` |
| `flag` | Để trống, hoặc `OFF_TASK`, `READ_ALOUD`, `AUDIO_BAD` |
| `speech_seconds` | Số giây nói thực (ước lượng) |
| `minutes_spent` | Thời gian chấm bài đó |
| `note` | Ghi chú ngắn, nhất là khi phân vân giữa hai mức |
| `rated_at` | Ngày chấm, dạng `YYYY-MM-DD` |

## 8. Chỉ số máy đo hỗ trợ từng tiêu chí

Người chấm **không xem** các chỉ số này. Chúng dùng để kiểm tra điểm của người chấm có hợp lý không và làm đầu vào cho mô hình.

| Tiêu chí | Chỉ số đang có trong hệ thống | Chỉ số bổ sung từ chú thích người làm |
| --- | --- | --- |
| Range | `log_uniq`, `ttr`, `mean_word_len` | Tỉ lệ từ ở mức B1 trở lên theo danh sách CEFR-J; MTLD |
| Accuracy | `asr_conf_mean`, `asr_conf_geo` (gián tiếp) | Số lỗi ngữ pháp trên 100 từ, so bản chép tay với bản đã sửa lỗi (`gec`) của S&I |
| Fluency | `words_per_sec`, `vad_articulation_rate`, `vad_mean_pause`, `vad_pause_per_min`, `vad_long_pause_ratio` | Số lần ậm ừ, lặp, tự sửa trên 100 từ, lấy từ bản chép giữ nguyên lỗi nói (`asr` disfluent) của S&I |
| Coherence | `n_words`, `vad_mean_seg_len`, `total_dur`, số loại từ nối (D061) | Tỉ lệ từ nối ở mức trung bình và nâng cao |
| Phonology | `asr_conf_mean`, `vad_silence_ratio` | Điểm phát âm theo âm vị (GOP), mô hình học trên speechocean762 (giấy phép CC BY 4.0) |

Nếu điểm người chấm và chỉ số liên quan **tương quan âm hoặc gần 0**, kiểm tra lại cách hiểu tiêu chí trước khi dùng điểm.

## 9. Từ bộ điểm đến mô hình chấm từng tiêu chí

1. **Mô hình:** một mô hình đa nhiệm, phần đọc đặc trưng dùng chung, 5 đầu ra cho 5 tiêu chí. Điểm tổng S&I của toàn bộ tập train đưa vào làm tác vụ phụ, vì 240 bài là ít.
2. **Đánh giá:** kiểm định chéo theo người nói. So sánh mô hình với người chấm bằng QWK, trên từng tiêu chí.
3. **Điều kiện hiện điểm từng tiêu chí cho học viên:** QWK giữa mô hình và người chấm không thấp hơn QWK giữa hai người chấm quá 0,10, và đạt ít nhất 0,60. Tiêu chí chưa đạt thì giữ cách hiện như bây giờ: chỉ số mô tả, không có điểm.
4. **Ghi nhận phiên bản:** mỗi mô hình ghi kèm phiên bản bộ tiêu chí (`rubric_version = "R5-1.0"`). Đổi mô tả ở mục 3 thì phải tăng phiên bản và chấm lại phần hiệu chuẩn.

## 10. Phạm vi và giới hạn

- **Interaction không chấm.** Bài là độc thoại, giữ `Interaction = null`, lý do `insufficient_evidence` (QD-04).
- **Bộ tiêu chí là thang đo của nhóm**, xây theo CEFR. Chưa phải thang đã được một tổ chức khảo thí thẩm định. Mức tin cậy được chứng minh bằng số đo đồng thuận ở mục 6.
- **Mức 1 và 6 ít bài.** Corpus có ít bài ở A1 và C2 nên điểm ở hai đầu thang kém chắc chắn nhất, giống điểm tổng (`band_map.py`).

## 11. Đánh giá tính khả thi

Mục này đánh giá theo hiện trạng ngày 17/11/2026: dữ liệu nhóm đang có, nhân lực và thời hạn đồ án.

| Khía cạnh | Kết luận | Lý do và điều kiện |
| --- | --- | --- |
| Dữ liệu và chú thích | **Khả thi có điều kiện** | Tập dev có audio trên máy và đủ chú thích cho phần lớn người nói, đủ cho khoảng 200 bài. **Nhóm điểm thấp (A2) rất ít bài**, trong khi A2 là trình độ đích của đồ án. Phải bù bằng audio train và bài sinh viên Việt Nam (mục 7). |
| Người chấm | **Rủi ro chính** | Thành viên nhóm không phải giám khảo đã được đào tạo. Hai sinh viên chấm vẫn đo được mức đồng thuận, nhưng không chứng minh được điểm đúng mức CEFR. Cần ít nhất một người có chuyên môn (giảng viên tiếng Anh, hoặc người có chứng chỉ giảng dạy tiếng Anh) làm một trong hai người chấm hoặc làm người phân xử. |
| Giấy phép | **Khả thi có điều kiện** | Ai nghe audio S&I cũng phải nằm trong giấy phép của corpus: từng người tự đăng ký, không gửi audio qua chat hay thư mục dùng chung. Bài từ app cần học viên đồng ý cho dùng. speechocean762 (CC BY 4.0) và danh sách từ CEFR-J dùng được cho nghiên cứu, ghi nguồn. |
| Thời gian | **Không kịp trong thời hạn đồ án; khả thi sau đó** | Khoảng 28 giờ người chấm, cộng khoảng một tuần xử lý dữ liệu và huấn luyện. Nếu mỗi người chấm 1–1,5 giờ mỗi ngày thì mất 3–4 tuần. |
| Chi phí | **Khả thi** | 0 đồng nếu người chấm là thành viên nhóm hoặc giảng viên hỗ trợ. Mô hình đa nhiệm nhỏ và mô hình điểm phát âm chạy được trên GPU T4 miễn phí của Colab hoặc Kaggle. |
| Độ tin cậy thống kê | **Khả thi** | Với khoảng 200 bài, sai số chuẩn của QWK vào khoảng 0,04–0,05. Mức đó đủ để kết luận một tiêu chí đạt hay không đạt ngưỡng 0,60 và 0,70. |
| Tách được 5 tiêu chí | **Rủi ro** | Điểm theo tiêu chí do người chấm thường tương quan cao với nhau (hiệu ứng hào quang). Hai tiêu chí tương quan trên 0,90 trong điểm người chấm thì coi là chưa tách được: gộp lại hoặc chỉ báo cáo chung. |
| Mô hình đạt ngưỡng | **Khác nhau theo tiêu chí** | Fluency và Phonology có khả năng đạt cao nhất, vì đặc trưng âm thanh đo trực tiếp. Range và Accuracy ở mức trung bình, vì phụ thuộc chất lượng nhận dạng giọng người học. Coherence thấp nhất: bài 40–60 giây có ít bằng chứng về cách tổ chức ý, nên có thể phải giữ lâu dài dạng chỉ số mô tả. |
| Tích hợp vào app | **Khả thi** | Hợp đồng dữ liệu đã có `Criterion` và `CriterionCoverage`. Thêm điểm tiêu chí là mở rộng schema có phiên bản, không phá API. Điều kiện hiện điểm ở mục 9 ngăn hiện số chưa tin cậy. |

**Kết luận:** bộ tiêu chí khả thi về kỹ thuật, dữ liệu, chi phí và thống kê. Hai điều kiện quyết định là **có người chấm có chuyên môn** và **mọi người chấm nằm trong giấy phép S&I**. Kế hoạch không kịp hoàn thành trước khi kết thúc đồ án, nên báo cáo trình bày nó như hướng phát triển đã có kế hoạch cụ thể. Không trình bày như kết quả.

**Thứ tự làm sau đồ án:**
1. Mời một giảng viên tiếng Anh làm người chấm hoặc người phân xử.
2. Chọn 10 bài mốc và hiệu chuẩn trên 20 bài (khoảng 1 tuần).
3. Chấm 200 bài dev (2–3 tuần).
4. Tính độ đồng thuận và tương quan giữa các tiêu chí; bỏ hoặc gộp tiêu chí chưa đạt.
5. Huấn luyện mô hình đa nhiệm; chỉ bật điểm cho tiêu chí đạt điều kiện ở mục 9.
