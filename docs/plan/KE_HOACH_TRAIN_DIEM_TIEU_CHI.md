# Kế hoạch huấn luyện điểm riêng cho từng tiêu chí (Range, Accuracy, Fluency, Coherence, Phonology)

**Phiên bản:** v0.1, BẢN THẢO. Chưa có `USER VERDICT`.
**Ngày lập:** 17/11/2026 (W10), múi giờ Asia/Ho_Chi_Minh.
**Người soạn:** Nguyên (với Claude).
**Phạm vi:** M05 (chấm điểm), M09 (lớp tin cậy), M04 (đặc trưng). Có chạm hợp đồng dữ liệu chung trong `contracts.py`.

> **Cổng chặn (AGENTS.md mục 3).** Kế hoạch này thay đổi rubric chấm của M05: hệ thống sẽ phát điểm theo từng tiêu chí thay vì chỉ phát chỉ báo mạnh/yếu. Các thành viên **được** chuẩn bị dữ liệu, viết công cụ trích đặc trưng và huấn luyện thử ngoài repo. **Không** đưa điểm tiêu chí ra giao diện, không đổi `contracts.py` và không bật artifact mới trên máy chủ cho tới khi chủ dự án chốt các mục ở [mục 11](#11-quyết-định-cần-chủ-dự-án-chốt).

---

## 0. Mục tiêu và nguyên tắc

**Mục tiêu.** Mỗi bài nói độc thoại được chấm thêm năm điểm riêng trên thang 0–6, mỗi điểm có khoảng tin cậy 90%. Tiêu chí nào chưa đủ căn cứ thì để trống kèm mã lý do. Mô hình điểm tổng đang chạy (`ridge_resp_v2`, hoặc `fusion_resp_v4` khi admin bật) **giữ nguyên**.

**Bảy nguyên tắc không đổi:**

1. **Năm mô hình riêng, dùng chung một chuỗi trích đặc trưng.** Mỗi tiêu chí là một mô hình nhỏ, huấn luyện trên bộ dữ liệu có nhãn của tiêu chí đó. Chỉ gộp thành một mô hình đa nhiệm ở giai đoạn 3, khi đã có dữ liệu sinh viên Việt Nam chấm đủ năm tiêu chí.
2. **Không tính điểm tổng bằng trung bình năm tiêu chí.** Điểm tổng theo CEFR là đánh giá chung của người chấm, không phải phép cộng.
3. **Mọi bộ dữ liệu đi qua đúng chuỗi xử lý của hệ thống**: giải mã về 16 kHz một kênh ([decoder.py](../../src/aicefr/audio/decoder.py)), Whisper small, Silero VAD ngưỡng 0,5, khoảng lặng tối thiểu 150 ms. Đặc trưng tính bằng công cụ khác thì mô hình sẽ lệch khi chạy thật.
4. **Thiếu dữ liệu là `None` kèm mã lý do, không bao giờ là 0** (CLAUDE.md, `contracts.py`).
5. **Interaction luôn `null`, lý do `insufficient_evidence`.** Bài độc thoại không có người đáp lại.
6. **Không đưa dữ liệu hay số đo vào Git.** Âm thanh, bản chép lời, ma trận đặc trưng, artifact `.json`, số đo suy ra từ bộ dữ liệu có giấy phép hạn chế đều nằm ngoài repo, trong `../aicefr-models/` và `../criteria-work/`. Code nạp artifact theo đường dẫn cấu hình và kiểm SHA-256. `python scripts/ci/check_forbidden_files.py` phải xanh trước mỗi PR.
7. **Chia dữ liệu theo người nói.** Bài của cùng một người không được vừa ở tập huấn luyện vừa ở tập kiểm tra (GroupKFold).

---

## 1. Hiện trạng

| Hạng mục | Hiện có | Còn thiếu |
| --- | --- | --- |
| Điểm tổng | Ridge trên 18 đặc trưng `v3`, huấn luyện trên S&I 2025 P3/P4 ([train_scorer.py](../../tools/train_scorer.py)); khoảng tin cậy CV+ ([calibrate_conformal.py](../../tools/calibrate_conformal.py)) | Không đổi |
| Tiêu chí | `CriterionIndicator`: chỉ báo mạnh/yếu bằng cách so đặc trưng với phân phối huấn luyện | Điểm riêng, khoảng tin cậy riêng, mô hình riêng |
| Đặc trưng | 19 tên trong [extract.py](../../src/aicefr/features/extract.py) (gồm `filler_ratio`), độ liên quan đề bài ([relevance.py](../../src/aicefr/features/relevance.py)), mẫu lỗi phát âm của người Việt ([vietnamese.py](../../src/aicefr/pronunciation/vietnamese.py)) | Đặc trưng phát âm theo âm vị, lỗi ngữ pháp, độ khó từ vựng, liên kết ý |
| Nhãn theo tiêu chí | Không có. S&I chỉ có điểm tổng | Dữ liệu ở [mục 2](#2-bộ-dữ-liệu-và-tiêu-chí-tương-ứng) và dữ liệu tự gán nhãn ở [mục 8](#8-giai-đoạn-3-dữ-liệu-sinh-viên-việt-nam-và-mô-hình-đa-nhiệm) |

---

## 2. Bộ dữ liệu và tiêu chí tương ứng

Không có bộ công khai nào chấm đủ năm tiêu chí trên bài nói tự do. Mỗi tiêu chí lấy nhãn từ bộ phù hợp nhất. Ở cột "Vai trò": **Train** là dùng để huấn luyện; **Pre** là huấn luyện trước, sau đó phải hiệu chỉnh lại; **Val** chỉ dùng để kiểm chứng, không dùng để chọn tham số.

| Bộ dữ liệu | Nhãn có sẵn | Thang gốc | Quy mô, loại bài | Giấy phép (phải xác minh lại trước khi tải) | Range | Accuracy | Fluency | Coherence | Phonology |
| --- | --- | --- | --- | --- | :---: | :---: | :---: | :---: | :---: |
| **speechocean762** | Accuracy, Fluency, Prosody, Completeness theo câu; điểm theo từ và âm vị; 5 chuyên gia chấm | 0–10 | 5.000 câu đọc to, người nói tiếng Trung, một nửa trẻ em; 16 kHz | OpenSLR ghi CC BY 4.0, bản Hugging Face ghi Apache-2.0 | – | – | Pre | – | **Train** |
| **L2-ARCTIC** | Nhãn lỗi âm vị (thay, bỏ, thêm); không có điểm | – | 24 người, có **4 người Việt** (HQTV, PNV, THV, TLV); có phần nói tự do (suitcase) | CC BY-NC 4.0 | – | – | – | – | **Train** đặc trưng GOP; Val giọng Việt |
| **Speak & Improve 2025** (đang dùng) | Điểm tổng; 55–60 giờ có chép lời và nhãn lỗi | 0–6 | ~315–340 giờ bài nói tự do | Phi thương mại, đăng ký qua ELiT; cấm công bố số đo khi chưa được CUP&A cho phép | Pre | **Train** (nhãn lỗi) | Pre | Pre | – |
| **EduHK English Speech Corpus** | 4 tiêu chí IELTS: Fluency & Coherence (FC), Lexical Resource (LR), Grammatical Range & Accuracy (GRA), Pronunciation (P) | Band 5.0–9.0 | 72–78 bộ bài nói tự do, người học Trung Quốc đại lục và Hồng Kông, cùng 30 video IELTS chính thức | Ghi "mở cho nghiên cứu", **chưa thấy văn bản giấy phép** | **Train** (LR) | Train (GRA) | Train (FC) | **Train** (FC) | Val (P) |
| **ICNALE GRA** v2.1 | 10 tiêu chí riêng (Fluency, Accuracy, Intelligibility, Sophistication, Logicality, Purposefulness…) và điểm tổng; ~80 người chấm mỗi bài | 100 điểm | 140 bài nói (đoạn mở đầu đóng vai thuyết phục), người học châu Á | **Chưa thấy văn bản giấy phép**, tải ở trang ICNALE | Val | Val | Val | Val | Val |
| **Sinh viên Việt Nam (tự thu, [mục 8](#8-giai-đoạn-3-dữ-liệu-sinh-viên-việt-nam-và-mô-hình-đa-nhiệm))** | Năm tiêu chí, 2 giảng viên chấm độc lập | 0–6 | Mục tiêu 300–500 bài | Phiếu đồng ý của sinh viên; Luật Bảo vệ dữ liệu cá nhân 91/2025/QH15 | **Train** + hiệu chỉnh | **Train** + hiệu chỉnh | **Train** + hiệu chỉnh | **Train** + hiệu chỉnh | **Train** + hiệu chỉnh |

**Nguồn:** [speechocean762 (Hugging Face)](https://huggingface.co/datasets/mispeech/speechocean762), [bài báo speechocean762](https://arxiv.org/abs/2104.01378), [L2-ARCTIC](https://psi.engr.tamu.edu/l2-arctic-corpus/), [Speak & Improve 2025](https://arxiv.org/abs/2412.11986), [EduHK English Speech Corpus](https://corpus.eduhk.hk/english_speaking/index.php/english_speech_corpus/), [ICNALE](https://language.sakura.ne.jp/icnale/download.html).

**Không dùng:** dữ liệu Shaip (trả phí, không có nhãn chấm, phần lớn là tổng đài 8 kHz), TLT-school (người nói là trẻ em, chưa rõ đã phát hành), LearnerVoice (không có điểm theo tiêu chí).

**Việc phải làm trước khi tải** (Thắng phụ trách, [mục 9](#9-phân-công-và-nhánh)): đọc giấy phép gốc của từng bộ, chụp lại trang giấy phép và lưu bằng chứng vào `docs/sdd/modules/m05-scoring/evidence/`. Bộ nào không rõ giấy phép thì gửi thư hỏi tác giả. Chưa có trả lời thì chỉ dùng làm Val nội bộ, không công bố số đo.

---

## 3. Chuẩn hoá thang điểm về 0–6

Mỗi bộ dùng một thang riêng, nên phải quy về 0–6 trước khi so sánh hoặc ghép. Mọi bảng quy đổi được lưu trong artifact (`scale_map`) để tái lập.

| Bộ | Cách quy đổi | Ghi chú |
| --- | --- | --- |
| IELTS band (EduHK) | Theo bảng đối chiếu IELTS–CEFR: 4.0–5.0 → B1, 5.5–6.5 → B2, 7.0–8.0 → C1, 8.5–9.0 → C2. Nội suy tuyến tính trong từng khoảng sang ngưỡng band của hệ thống (B1 bắt đầu từ 2,75; B2 từ 3,75) | Phải trích nguồn chính thức của IELTS trong evidence |
| speechocean762 (0–10) | **Không** quy trực tiếp sang CEFR, vì đây là điểm chất lượng phát âm bài đọc chứ không phải bậc năng lực. Huấn luyện trên thang gốc, rồi hiệu chỉnh sang 0–6 bằng hồi quy đẳng biến (isotonic) trên dữ liệu sinh viên Việt Nam ([mục 8](#8-giai-đoạn-3-dữ-liệu-sinh-viên-việt-nam-và-mô-hình-đa-nhiệm)) | Trước khi có dữ liệu Việt Nam, điểm Phonology chỉ dùng nội bộ |
| ICNALE (100 điểm) | Không quy đổi. Chỉ đo tương quan thứ hạng (Spearman) giữa điểm máy và điểm người chấm | Dùng để kiểm chứng |
| S&I (0–6) | Giữ nguyên | |
| Sinh viên Việt Nam (0–6) | Giữ nguyên. Đây là thang chuẩn cuối cùng | |

---

## 4. Đặc trưng theo tiêu chí

Phiên bản đặc trưng mới là **`v4-criteria`**. Mười chín đặc trưng `v3` được giữ nguyên tên và thứ tự; các đặc trưng mới được thêm vào sau. Mỗi đặc trưng mới phải có:

- hàm tính trong `src/aicefr/features/criteria/<tiêu_chí>.py`, chỉ phụ thuộc vào `Word`, kết quả VAD, âm thanh 16 kHz hoặc bản chép lời;
- test trên dữ liệu tổng hợp trong `tests/`, không dùng âm thanh thật;
- giá trị `None` kèm `ReasonCode.FEATURE_NOT_COMPUTABLE` khi không tính được.

| Tiêu chí | Đặc trưng `v3` dùng lại | Đặc trưng mới đề xuất | Công cụ |
| --- | --- | --- | --- |
| **Range** | `ttr`, `log_uniq`, `mean_word_len`, `n_words` | `mtld` (độ đa dạng từ vựng không phụ thuộc độ dài bài); `zipf_mean`, `rare_word_ratio` (tỷ lệ từ có tần suất Zipf dưới 4); `clause_per_sentence`, `subordinate_ratio` (độ phức tạp câu) | `wordfreq` (tần suất từ), spaCy `en_core_web_sm` (tách câu, mệnh đề) |
| **Accuracy** | `asr_conf_mean`, `asr_conf_geo` | `gec_err_per_100w` (số lỗi ngữ pháp trên 100 từ); `gec_err_types` (thì, mạo từ, hoà hợp chủ–vị, giới từ); `edit_ratio` (tỷ lệ từ bị sửa) | LanguageTool chạy cục bộ, hoặc mô hình sửa lỗi ngữ pháp chạy CPU. Không gọi dịch vụ ngoài với bản chép lời |
| **Fluency** | `words_per_sec`, `vad_articulation_rate`, `vad_mean_pause`, `vad_pause_per_min`, `vad_long_pause_ratio`, `vad_pause_sd`, `filler_ratio` | `mid_clause_pause_ratio` (tỷ lệ khoảng ngừng nằm giữa cụm từ, so với ngừng ở ranh giới câu); `repair_ratio` (lặp từ, tự sửa) | Thời điểm từng từ của Whisper, spaCy |
| **Coherence** | `total_dur`, `vad_mean_seg_len`, `vad_n_seg_per_min` | `connective_per_100w` (từ nối theo nhóm: thời gian, nguyên nhân, đối lập, bổ sung); `adjacent_sim_mean` (độ tương đồng ngữ nghĩa giữa hai câu liền kề); `keyword_relevance` (đã có ở D022) | Danh sách từ nối viết tay; sentence-transformers `all-MiniLM-L6-v2` chạy CPU |
| **Phonology** | `asr_conf_mean`, `vad_silence_ratio` | `gop_mean`, `gop_p10` (Goodness of Pronunciation theo âm vị, căn chỉnh cưỡng bức); `phone_err_rate`; `vn_pattern_rate` (năm mẫu lỗi của người Việt, đã có ở D039); `f0_range`, `stress_contrast` (ngữ điệu) | wav2vec2 nhận dạng âm vị (CTC) để căn chỉnh; `librosa` hoặc `parselmouth` để đo cao độ |

Đặc trưng nào cần thư viện nặng (torch, spaCy, sentence-transformers) thì đưa vào một extra riêng `.[criteria]` trong `pyproject.toml`, giống cách `.[text]` đang làm cho DeBERTa. Image mặc định không bị phình.

---

## 5. Quy trình huấn luyện chung (giống nhau cho mọi tiêu chí)

Thư mục làm việc nằm **ngoài repo**:

```text
../criteria-work/
  raw/<bộ_dữ_liệu>/          # âm thanh và nhãn gốc, không bao giờ vào Git
  features/<bộ>_<v4>.parquet # một dòng một bài: speaker_id, sample_rate_goc, các đặc trưng, nhãn
  runs/<tiêu_chí>/<ngày>/    # log, biểu đồ, số đo
../aicefr-models/
  crit_<tiêu_chí>_v1.json    # artifact cuối, ghim SHA-256
  conformal_crit_<tiêu_chí>_v1.json
```

**Các bước:**

1. **Tải và kiểm kê.** Ghi số bài, số người nói, phân bố điểm, tần số lấy mẫu gốc vào `runs/<tiêu_chí>/inventory.md`.
2. **Trích đặc trưng bằng chuỗi xử lý của hệ thống.** Công cụ chung `tools/extract_criteria_features.py <bộ> <thư-mục-raw>` gọi đúng `decoder`, `WhisperAsr`, `SileroVad`, `FeatureExtractor`, cộng các đặc trưng mới, rồi ghi ra parquet. Không tự viết lại bước giải mã hay VAD.
3. **Tăng cường băng thông** (chỉ cho tập huấn luyện). Với mỗi bài 16 kHz, tạo thêm một bản hạ xuống 8 kHz rồi nâng lại 16 kHz, giữ nguyên nhãn. Ghi cột `augmented=true`. Mục đích là để mô hình không trừ điểm chỉ vì micro hoặc đường truyền kém.
4. **Chia dữ liệu.** GroupKFold 5 fold theo `speaker_id`. Bản tăng cường luôn đi cùng fold với bản gốc.
5. **Huấn luyện.** `StandardScaler` → `RidgeCV` (alpha trong `logspace(-2, 4, 40)`, chọn bằng GroupKFold lồng nhau theo người nói, như tuỳ chọn `--group-alpha` của `train_scorer.py`). Mỗi tiêu chí dùng 19 đặc trưng `v3` cộng các đặc trưng mới của tiêu chí đó.
6. **Đo trên dự đoán ngoài fold:**
   - RMSE, Pearson (PCC), Spearman (SRC) trên thang 0–6;
   - QWK theo band so với nhãn;
   - **mốc so sánh**: RMSE của cách đoán luôn bằng trung bình (mô hình phải tốt hơn rõ rệt), và RMSE của chỉ 19 đặc trưng `v3` (để biết đặc trưng mới có giúp gì không);
   - tách số đo theo nhóm: theo bộ dữ liệu, theo tần số lấy mẫu gốc (8 / 16 / từ 44 kHz), theo band.
7. **Khoảng tin cậy.** Chạy CV+ như `calibrate_conformal.py`, mức phủ danh nghĩa 90%, đo mức phủ thực tế bằng CV lồng nhau.
8. **Ghi artifact** `crit_<tiêu_chí>_v1.json` theo cùng cấu trúc với `ridge_resp_v1`, thêm các trường: `criterion`, `scale_map`, `train_sets`, `feature_version: "v4-criteria"`, `augmentation`, `cv_qwk`, `baseline_rmse`, `acceptance` (đạt hay không theo [mục 7](#7-tiêu-chí-nghiệm-thu-một-mô-hình-tiêu-chí)). Ghim SHA-256 trong `src/aicefr/scoring/artifacts.py`.
9. **Evidence.** Mỗi lần chạy có một mục trong `docs/sdd/modules/m05-scoring/evidence/evidence-manifest.md`: lệnh đã chạy, revision, SHA của ma trận đặc trưng và nhãn, kết quả **đạt / không đạt** (không ghi số đo suy ra từ S&I vào repo). Ghi lần dùng AI vào sheet cá nhân của workbook tuần.

**Công cụ chung cần viết trước** (Sang, tuần 1): `tools/extract_criteria_features.py` và `tools/train_criterion.py --criterion <tên> --sets <bộ,...>`. Ba người dùng chung hai script này, mỗi người chỉ viết phần đặc trưng của tiêu chí mình. Như vậy không ai sửa cùng một file.

---

## 6. Kế hoạch riêng cho từng tiêu chí

### 6.1. Phonology (Nguyên)

- **Dữ liệu:** speechocean762 (Train), L2-ARCTIC (Train cho đặc trưng GOP, Val trên 4 người Việt), EduHK cột P (Val).
- **Nhãn:** điểm Accuracy theo câu của speechocean762 làm nhãn chính; Prosody làm nhãn phụ để kiểm tra đặc trưng ngữ điệu.
- **Lưu ý:** speechocean762 là bài đọc to, có văn bản chuẩn để căn chỉnh. Bài của SpeakUp là nói tự do, nên khi chạy thật phải căn chỉnh theo bản chép lời của Whisper. Cần đo chênh lệch GOP giữa hai cách căn chỉnh trên L2-ARCTIC phần suitcase (có cả hai) trước khi tin vào kết quả.
- **Kiểm tra công bằng:** đo riêng trên 4 người Việt của L2-ARCTIC. Giọng không phải lỗi; mô hình không được cho điểm thấp chỉ vì giọng địa phương nếu người nghe vẫn hiểu.
- **Sản phẩm:** `features/criteria/phonology.py`, `crit_phonology_v1.json`, evidence.

### 6.2. Fluency (Nguyên)

- **Dữ liệu:** EduHK cột FC (Train), speechocean762 Fluency (Pre), S&I điểm tổng (Pre, vì độ trôi chảy giải thích phần lớn điểm tổng).
- **Lưu ý:** cột FC của EduHK gộp Fluency với Coherence. Dùng nó làm nhãn chung cho cả hai, rồi tách bằng tập đặc trưng: Fluency chỉ dùng đặc trưng nhịp nói và khoảng ngừng, Coherence chỉ dùng đặc trưng nội dung và liên kết. Ghi rõ giới hạn này trong artifact.
- **Kiểm tra:** Whisper hay bỏ các từ ngập ngừng ("uh", "um"), nên `filler_ratio` bị đếm thiếu. Đo trên phần S&I có chép lời tay để biết thiếu bao nhiêu.
- **Sản phẩm:** `features/criteria/fluency.py`, `crit_fluency_v1.json`.

### 6.3. Accuracy (Thắng)

- **Dữ liệu:** phần S&I có chép lời và nhãn lỗi (Train: nhãn là số lỗi chuẩn hoá theo độ dài, hoặc điểm tổng làm nhãn phụ), EduHK cột GRA (Train), ICNALE Accuracy (Val).
- **Lưu ý:** công cụ sửa lỗi ngữ pháp chạy trên **bản chép của Whisper**, mà Whisper có xu hướng tự sửa ngữ pháp khi chép. Phải đo trên phần S&I có chép lời tay: số lỗi tìm được trên bản Whisper so với bản chép tay. Nếu bị đếm thiếu quá nhiều thì Accuracy để trống kèm lý do, không phát điểm.
- **Sản phẩm:** `features/criteria/accuracy.py`, `crit_accuracy_v1.json`, ghi chú về độ lệch giữa chép tay và chép máy.

### 6.4. Range (Thắng)

- **Dữ liệu:** EduHK cột LR (Train), ICNALE Sophistication (Val), S&I (Pre).
- **Lưu ý:** bài 40–60 giây chỉ khoảng 60–150 từ, nên TTR dao động mạnh theo độ dài bài. Ưu tiên `mtld` và đặc trưng tần suất từ. Đo riêng nhóm bài dưới 60 từ.
- **Sản phẩm:** `features/criteria/range.py`, `crit_range_v1.json`.

### 6.5. Coherence (Sang)

- **Dữ liệu:** EduHK cột FC (Train, như ở 6.2), ICNALE Logicality và Purposefulness (Val), S&I (Pre).
- **Lưu ý:** đây là tiêu chí yếu nhất về dữ liệu, gần như chắc chắn **không đạt** cổng nghiệm thu trước giai đoạn 3. Mục tiêu ở giai đoạn 1–2 là có đặc trưng tốt và số đo trung thực. Phát điểm Coherence chỉ khi đã có dữ liệu sinh viên Việt Nam.
- **Sản phẩm:** `features/criteria/coherence.py`, `crit_coherence_v1.json` (có thể mang `acceptance: false`).

### 6.6. Hợp đồng dữ liệu và giao diện (Sang và Thắng, chỉ làm sau khi chủ dự án chốt)

- `contracts.py`: thêm vào `CriterionIndicator` (hoặc một model mới `CriterionScore`) các trường `score_0_6: float | None`, `interval: tuple[float, float] | None`, `model_version: str | None`, `reason: ReasonCode | None`. Mã lý do mới đề xuất: `CRITERION_MODEL_MISSING`, `CRITERION_LOW_CONFIDENCE`, `CRITERION_NOT_VALIDATED`.
- Scorer: thêm adapter `CriterionScorer` cho cổng mới trong `ports.py`; `ResponseProcessor` gọi sau bước chấm điểm tổng. Lỗi ở một tiêu chí không được làm hỏng điểm tổng.
- Admin bật hoặc tắt từng mô hình tiêu chí như đang bật mô hình điểm tổng (UC-09).
- Báo cáo (M06, Nguyên): hiện điểm tiêu chí kèm khoảng tin cậy; tiêu chí bị để trống thì hiện lý do bằng lời.

---

## 7. Tiêu chí nghiệm thu một mô hình tiêu chí

Một mô hình được phép hiện điểm cho người học khi đạt **tất cả** các điều kiện sau. Ngưỡng là **đề xuất**, chủ dự án chốt ở [mục 11](#11-quyết-định-cần-chủ-dự-án-chốt).

| Điều kiện | Ngưỡng đề xuất |
| --- | --- |
| Tốt hơn đoán trung bình | RMSE ngoài fold ≤ 80% RMSE của cách đoán luôn bằng trung bình |
| Đồng thuận với người chấm | QWK máy–người ≥ 0,9 × QWK giữa hai người chấm trên cùng bộ (giai đoạn 3) |
| Khoảng tin cậy dùng được | Mức phủ thực tế từ 85% trở lên; độ rộng trung bình dưới 2 band |
| Ổn định theo băng thông | RMSE nhóm 8 kHz không quá 1,2 lần RMSE nhóm 16 kHz |
| Kiểm chứng ngoài | Spearman với ICNALE dương và có ý nghĩa thống kê (p < 0,05) |

Mô hình không đạt vẫn được giữ artifact để tiếp tục cải thiện, nhưng hệ thống trả `None` và mã `CRITERION_NOT_VALIDATED`.

---

## 8. Giai đoạn 3: dữ liệu sinh viên Việt Nam và mô hình đa nhiệm

Đây là bước duy nhất cho Range và Coherence đủ dữ liệu, và là bước hiệu chỉnh cuối cho mọi tiêu chí.

**Thu dữ liệu (Nguyên tổ chức, giảng viên hướng dẫn duyệt):**

1. Phiếu đồng ý nêu rõ mục đích, thời gian lưu và quyền rút lại. Bài của sinh viên không đồng ý không được dùng.
2. Mục tiêu 300–500 bài, trải đều các band A2–C1 và nhiều đề. Thu trên SpeakUp bằng chính trang Nộp bài, để điều kiện thu giống lúc chạy thật.
3. Dữ liệu chỉ nằm trong kho riêng ngoài repo, đổi tên người nói thành mã. Không ghi họ tên, email vào tệp nhãn.

**Gán nhãn:**

1. Hướng dẫn chấm dựa trên bảng các khía cạnh định tính của CEFR Companion Volume (2020), viết thành phiếu chấm năm tiêu chí trên thang 0–6. Lưu tại `docs/sdd/modules/m05-scoring/` sau khi chủ dự án duyệt.
2. Hai giảng viên chấm độc lập mọi bài; 10% bài có người thứ ba chấm để xử lý chênh lệch lớn hơn 1 điểm.
3. Đo QWK giữa hai người chấm cho từng tiêu chí trước khi huấn luyện. Tiêu chí có QWK người–người thấp thì cả máy cũng không học được, phải xem lại phiếu chấm.

**Huấn luyện:**

1. Hiệu chỉnh từng mô hình ở giai đoạn 1–2 sang thang của giảng viên (isotonic), rồi đo lại theo [mục 7](#7-tiêu-chí-nghiệm-thu-một-mô-hình-tiêu-chí).
2. Thử mô hình đa nhiệm: dùng chung các đặc trưng `v4-criteria`, năm đầu ra, huấn luyện cùng lúc (Ridge đa đầu ra trước; mạng nhỏ hai lớp nếu đủ dữ liệu). So với năm mô hình riêng bằng cùng các fold. Chỉ chuyển sang mô hình đa nhiệm nếu nó tốt hơn trên ít nhất bốn tiêu chí và không kém hơn ở tiêu chí nào.

---

## 9. Phân công và nhánh

| Người | Phần việc | Nhánh | File được sửa |
| --- | --- | --- | --- |
| **Sang** | Công cụ chung (mục 5), Coherence (6.5), hợp đồng dữ liệu (6.6) | `train/common`, `train/coherence` | `tools/extract_criteria_features.py`, `tools/train_criterion.py`, `src/aicefr/features/criteria/__init__.py`, `coherence.py`, `contracts.py` (sau khi chốt) |
| **Thắng** | Xác minh giấy phép và tải dữ liệu (mục 2), Accuracy (6.3), Range (6.4), extra `.[criteria]` | `train/accuracy`, `train/range` | `features/criteria/accuracy.py`, `range.py`, `pyproject.toml` |
| **Nguyên** | Phonology (6.1), Fluency (6.2), thu và gán nhãn dữ liệu Việt Nam (mục 8), báo cáo (6.6) | `train/phonology`, `train/fluency` | `features/criteria/phonology.py`, `fluency.py`, template báo cáo |

**Quy tắc:**

- Mỗi nhánh tách từ `main`, PR vào `main` qua review của một người khác; CI phải xanh (format, lint, test, độ phủ ≥ 70%, kiểm file cấm, kiểm link tài liệu).
- Nhánh `train/common` merge trước. Các nhánh tiêu chí rebase lên sau đó.
- Commit đứng tên người làm. Không commit dữ liệu, artifact hay số đo suy ra từ S&I.
- Ai cũng có thể huấn luyện thử trên máy mình. Artifact chỉ được chép lên máy chủ sau khi đạt [mục 7](#7-tiêu-chí-nghiệm-thu-một-mô-hình-tiêu-chí) và có review.

---

## 10. Lịch đề xuất

| Tuần | Việc | Ai |
| --- | --- | --- |
| 1 | Xác minh giấy phép, tải speechocean762 và L2-ARCTIC, hỏi tác giả EduHK và ICNALE. Viết hai script chung và test trên dữ liệu tổng hợp | Thắng; Sang |
| 2 | Viết đặc trưng mới cho từng tiêu chí, kèm test. Trích đặc trưng các bộ đã tải | Cả nhóm |
| 3 | Huấn luyện, đo, CV+; viết evidence. Soạn phiếu chấm và phiếu đồng ý cho giai đoạn 3 | Cả nhóm; Nguyên |
| 4 | Chủ dự án xem số đo và chốt [mục 11](#11-quyết-định-cần-chủ-dự-án-chốt). Nếu được duyệt: sửa hợp đồng dữ liệu, adapter, giao diện | Chủ dự án; Sang, Nguyên |
| Sau đó | Thu và gán nhãn dữ liệu Việt Nam, hiệu chỉnh, thử mô hình đa nhiệm | Cả nhóm |

---

## 11. Quyết định cần chủ dự án chốt

| Mã | Câu hỏi | Khuyến nghị |
| --- | --- | --- |
| CR-O-001 | Có cho hệ thống phát điểm riêng từng tiêu chí không (thay đổi rubric M05)? | Có, nhưng chỉ cho tiêu chí đạt mục 7; các tiêu chí khác giữ chỉ báo mạnh/yếu như hiện nay |
| CR-O-002 | Ngưỡng nghiệm thu ở mục 7 | Dùng ngưỡng đề xuất, xem lại sau giai đoạn 3 |
| CR-O-003 | Dùng bộ dữ liệu phi thương mại (L2-ARCTIC, S&I) trong khi SpeakUp có chức năng bán gói lượt | Chỉ dùng cho đồ án và nghiên cứu; ghi rõ trong báo cáo; hỏi giảng viên hướng dẫn |
| CR-O-004 | Bảng quy đổi IELTS–CEFR sang thang 0–6 ở mục 3 | Dùng bảng đối chiếu chính thức của IELTS, nội suy tuyến tính |
| CR-O-005 | Thu bài nói thật của sinh viên ở giai đoạn 3 (dữ liệu cá nhân, âm thanh thật) | Cần phiếu đồng ý và giảng viên hướng dẫn duyệt trước |
| CR-O-006 | Hiện điểm Coherence trước giai đoạn 3? | Không |

---

## 12. Rủi ro

| Rủi ro | Hậu quả | Cách giảm |
| --- | --- | --- |
| Giấy phép EduHK, ICNALE không rõ | Không được dùng hoặc công bố số đo | Hỏi tác giả từ tuần 1; chưa có trả lời thì chỉ dùng làm Val nội bộ |
| Người nói trong dữ liệu không phải người Việt | Mô hình lệch với sinh viên Việt Nam | Đo riêng 4 người Việt của L2-ARCTIC; hiệu chỉnh ở giai đoạn 3 |
| Bài đọc to (speechocean762) khác bài nói tự do | Đặc trưng phát âm lệch khi chạy thật | Đo GOP theo hai cách căn chỉnh trên L2-ARCTIC suitcase |
| Whisper tự sửa ngữ pháp và bỏ từ ngập ngừng | Accuracy, Fluency bị đánh giá cao hơn thực tế | Đo trên phần S&I chép tay; không đạt thì để trống |
| Quá ít bài cho Range, Coherence | Mô hình không đạt cổng | Không hiện điểm; chờ giai đoạn 3 |
| Thư viện nặng làm image phình | Triển khai chậm, tốn bộ nhớ | Extra `.[criteria]` riêng, torch bản CPU |
| Số đo S&I lọt vào repo | Vi phạm giấy phép CUP&A | Evidence chỉ ghi đạt/không đạt; số đo nằm trong artifact ngoài repo |
