# Xây dựng hệ thống AI hỗ trợ đánh giá năng lực nói tiếng Anh theo CEFR cho sinh viên đại học Việt Nam ở trình độ A2-B2

## 01. Sổ nguồn dữ liệu công khai/có đăng ký

| Thuộc tính | Giá trị |
| --- | --- |
| Trạng thái | DRAFT - desk research completed, acquisition not approved |
| Ngày kiểm tra nguồn | 02/09/2026 |
| Phạm vi | Audio tiếng Anh L2 phục vụ baseline, ASR/Phonology sanity check hoặc anchor research |

## 1. Kết luận ngắn

Không tìm thấy corpus công khai nào đồng thời có đủ: người nói Việt Nam từ 18 tuổi là sinh viên, spontaneous production + contingent interaction, A2-B2, sáu nhãn Range/Accuracy/Fluency/Interaction/Coherence/Phonology và nhiều rater độc lập. Vì vậy:

1. Dữ liệu tự thu theo protocol dự án vẫn là tập xác nhận chính.
2. Speak & Improve 2025 là candidate tốt nhất cho baseline holistic monologue toàn cầu nhưng không dùng làm confirmation set của dự án.
3. L2-ARCTIC là candidate tốt nhất cho smoke test Phonology/ASR với giọng Việt, không phải dataset CEFR scoring.
4. SpeechOcean762 dùng cho kiểm tra pipeline pronunciation, không dùng suy luận về người Việt hoặc sáu tiêu chí.
5. Speech Accent Archive có thể bổ sung read-accent sanity check cho người Việt nhưng không có CEFR label.
6. ICNALE hữu ích cho task/rater research Asian university A2-B2, nhưng spoken modules hiện không có Việt Nam và điều khoản cấm tái phân phối.

## 2. Ma trận nguồn

| Dataset | Nội dung xác minh | License/access | Phù hợp với dự án | Không được dùng để claim |
| --- | --- | --- | --- | --- |
| Speak & Improve Corpus 2025 | Khoảng 315 giờ, hơn 45.000 utterances từ hơn 7.000 test submissions; open/spontaneous monologic responses; holistic CEFR-like A2-C1+; khoảng 55 giờ có manual transcript | Đăng ký và chấp nhận license; non-commercial research/education; không chuyển giao/tái phân phối; không đưa lên Git/Hugging Face; derivative release có hạn chế | B0/B1 holistic monologue baseline; ASR/disfluency/GEC research; tham khảo task functions | Không có sáu analytic labels; không có Interaction; không xác nhận người Việt; source paper cảnh báo speaker có thể xuất hiện ở cả train/test do thiếu speaker/L1 data, nên split phát hành không đạt invariant của dự án |
| L2-ARCTIC v5 | 24 L2 speakers, 4 Vietnamese; khoảng một giờ read speech/người; manual phone errors; suitcase spontaneous retelling cho 22/24 speakers. Từ danh sách hai người không tham gia suitcase (Arabic/Hindi), có thể suy ra cả bốn Vietnamese có phần này; phải xác minh sau tải | CC BY-NC 4.0; phải điền tên/email/affiliation, đồng ý license và nhận link | ASR/forced-alignment/Phonology smoke test; 4 Vietnamese speakers; suitcase dùng sanity check spontaneous narration | Không có CEFR level/rubric sáu tiêu chí; chỉ 4 Vietnamese; phần lớn là read speech; không đại diện sinh viên Việt Nam A2-B2 |
| SpeechOcean762 / OpenSLR SLR101 | 5.000 read utterances, 250 L1-Mandarin speakers, một nửa là trẻ em; 5 expert raters; sentence/word/phone pronunciation scores | OpenSLR ghi CC BY 4.0; tải trực tiếp khoảng 520 MB | Unit/smoke test pronunciation scoring, audio ingest, alignment và rater-score parsing | Không người Việt; sai population tuổi; không spontaneous; không CEFR; “fluency” hẹp của read pronunciation không tương đương Fluency construct dự án |
| Speech Accent Archive | Người nói bản ngữ/không bản ngữ cùng đọc một elicitation paragraph; có thể duyệt/lọc theo L1 và có phonetic transcription/metadata | GMU hiện công bố CC BY-NC-SA 4.0 và cung cấp MP3/transcript/FLAC qua OSF | External accent/read-speech sanity check cho Vietnamese entries | Không CEFR, không spontaneous construct chính, không sáu criterion; không dùng accent distance làm lỗi hoặc fairness claim |
| ICNALE SM/SD/GRA | SM: 4.400 bài monologue 60 giây; SD: 425 interviews, role plays; A2/B1_1/B1_2/B2+ gắn từ test/VST; GRA có 22.400 assessments của 140 speeches/140 essays bởi 80 raters | Download cần đăng ký/password; terms cấm tái tạo/tái phân phối; cấm phân tích interviewer speech trong SD | Tham khảo task control, Asian university learner variation, rating design/GRA | Danh sách spoken regions hiện không có VNM; Việt Nam chỉ xuất hiện trong Written Essays Plus; level không phải sáu analytic speaking labels; không phân tích interviewer lane |
| Mozilla Common Voice English 25.0 | Read speech cho ASR; `client_id` hỗ trợ group split; accent/age metadata tự khai và có thể thiếu | CC0-1.0 nhưng cấm re-host/re-share và cấm cố nhận dạng speaker | ASR smoke test hoặc robustness chung nếu cần thêm volume | Không CEFR, không spontaneous, không sáu tiêu chí; không được giả định accent metadata có đủ người Việt |

## 3. Shortlist đề nghị

| Ưu tiên | Nguồn | Vai trò đề nghị | Điều kiện trước acquisition |
| ---: | --- | --- | --- |
| 1 | L2-ARCTIC v5 | Vietnamese Phonology/ASR smoke fixture, tối đa một vài sample cho test local | License owner đăng ký; storage ngoài Git; ghi version/checksum; không claim CEFR |
| 2 | Speak & Improve 2025 | Auxiliary holistic monologue baseline/research comparison | GVHD duyệt license; người dùng tự đăng ký; xác minh có thể tạo speaker-disjoint subset, nếu không chỉ dùng train/dev research không làm confirmation claim |
| 3 | SpeechOcean762 | Pronunciation pipeline unit/smoke test | License inventory + checksum; filter adult nếu nghiên cứu cần; không dùng claim population |
| 4 | Speech Accent Archive | Optional Vietnamese read-accent sanity check | CC BY-NC-SA 4.0; lọc theo metadata source; không chấm accent như lỗi |
| 5 | ICNALE SM/SD/GRA | Literature/anchor-method study; có thể dùng learner lane nếu license/storage được duyệt | Đăng ký; không redistribute; không phân tích interviewer speech; không gọi là Vietnamese data |
| 6 | Common Voice English | Optional ASR robustness | Chỉ khi cần volume; group bằng `client_id`; không dùng CEFR scoring |

## 4. Nguồn chính thức

- [Speak & Improve Corpus 2025 - Cambridge ELiT](https://researchdatasets.cambridge.org/datasets/speak-and-improve-corpus-2025).
- [Speak & Improve Corpus paper](https://doi.org/10.17863/CAM.114333).
- [L2-ARCTIC homepage/license](https://psi.engr.tamu.edu/l2-arctic-corpus/).
- [L2-ARCTIC documentation](https://psi.engr.tamu.edu/l2-arctic-corpus-docs/).
- [SpeechOcean762 - OpenSLR SLR101](https://openslr.org/101/).
- [SpeechOcean762 paper](https://www.isca-archive.org/interspeech_2021/zhang21x_interspeech.pdf).
- [Speech Accent Archive - official download/license](https://accent.gmu.edu/download/).
- [ICNALE download/modules](https://language.sakura.ne.jp/icnale/download.html).
- [ICNALE terms/modules](https://language.sakura.ne.jp/icnale/).
- [Mozilla Common Voice datasets](https://commonvoice.mozilla.org/en/datasets).

## 5. Cảnh báo nguồn

- Không dùng mirror/community repack khi source chính thức và license không khớp; ví dụ Hugging Face card có thể ghi license khác OpenSLR.
- Không đưa corpus hoặc sample audio vào repository chỉ vì license cho phép nghiên cứu.
- Không công bố statistics/model artifacts bị license hạn chế nếu chưa có approval từ data owner.
- Không gộp A2+/B1+/B2+ vào A2/B1/B2 âm thầm; mapping phải là decision có rationale và sensitivity analysis.
