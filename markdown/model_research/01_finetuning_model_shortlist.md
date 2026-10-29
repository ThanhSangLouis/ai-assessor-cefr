# Shortlist mô hình fine-tune cho AI Assessor CEFR A2–B2

## 1. Thông tin tài liệu

| Thuộc tính | Giá trị |
| --- | --- |
| Đề tài | Xây dựng hệ thống AI hỗ trợ đánh giá năng lực nói tiếng anh theo CEFR cho sinh viên đại học Việt Nam ở trình độ A2–B2 |
| Loại tài liệu | Research shortlist / đề xuất kỹ thuật có điều kiện |
| Trạng thái | `PROPOSED` — không phải quyết định đã được GVHD/GV Ngoại ngữ phê duyệt |
| Ngày kiểm tra nguồn | 12/09/2026 |
| Phạm vi | ASR; encoder âm thanh; encoder transcript; ordinal head, calibration và late fusion |
| Ngoài phạm vi | Tải model/dataset; huấn luyện; công bố metric; tự động hóa quyết định học vụ |

## 2. Kết luận điều hành

**Không nên tìm một model duy nhất để fine-tune rồi giao cho nó tự chấm toàn bộ bài nói.** Với dữ liệu dự kiến chỉ ở quy mô vài chục người nói, phương án có tính bảo vệ nghiên cứu tốt nhất là giữ bốn mô-đun riêng:

1. ASR tạo transcript và timestamp, được đánh giá bằng WER nhưng không trực tiếp tạo điểm CEFR.
2. Nhánh âm thanh cung cấp bằng chứng cho Fluency và Phonology.
3. Nhánh transcript cung cấp bằng chứng cho Range, Accuracy và Coherence.
4. Các head ordinal nhỏ dự đoán từng tiêu chí; late fusion kết hợp xác suất/bằng chứng và calibration quyết định ca cần giảng viên xem lại.

**Lựa chọn MVP đề xuất:**

- ASR: chạy local bằng `openai/whisper-small.en` qua `faster-whisper`, **đóng băng model ở baseline đầu tiên**.
- Scorer âm thanh: `facebook/wav2vec2-base` hoặc `facebook/wav2vec2-base-960h` đóng băng, chỉ huấn luyện pooling + head CORAL riêng cho Fluency và Phonology.
- Scorer transcript: `FacebookAI/roberta-base` đóng băng, kết hợp feature có thể giải thích và head CORAL riêng cho Range, Accuracy và Coherence.
- Interaction: chỉ dùng dữ liệu turn/latency/repair thực sự từ Task C; độc thoại phải trả `null`/`insufficient_evidence`.
- Fusion: mô hình tuyến tính/ordinal có regularization trên đầu ra out-of-fold của từng nhánh; calibration trên development fold tách theo speaker.

**Fallback nhẹ:** `whisper-base.en` + feature thủ công + ordinal logistic/CORAL head, không fine-tune backbone. Đây là phương án phù hợp nếu GPU không dùng được hoặc thời gian triển khai hạn chế.

**Điểm cần phân biệt:** fine-tune **ASR** tối ưu transcript theo cặp audio–bản chép tay; fine-tune **scorer** tối ưu nhãn A2/B1/B2 theo rubric. Hai bài toán dùng nhãn, loss và điều kiện nghiệm thu khác nhau. Đề xuất hiện tại ưu tiên fine-tune scorer nhỏ; chỉ fine-tune ASR khi kiểm tra WER trên giọng Việt cho thấy adaptation là cần thiết.

Không có checkpoint nào dưới đây đã được xác nhận sẵn cho đúng population “sinh viên đại học Việt Nam 18+, A2–B2” và đúng sáu tiêu chí của đề tài. Mọi lợi ích trên dữ liệu khác chỉ là bằng chứng về tính khả thi, không phải benchmark có thể chuyển thẳng sang đề tài.

## 3. Ràng buộc máy hiện tại

Snapshot do nhóm kiểm tra ngày 12/09/2026:

| Thành phần | Hiện trạng | Hệ quả |
| --- | --- | --- |
| GPU | NVIDIA RTX 3050 Ti Laptop, 4 GB VRAM | Có thể thử inference và head nhỏ; không nên mặc định full fine-tune Whisper/WavLM/RoBERTa |
| CPU | 20 logical CPUs | Có thể trích xuất embedding theo batch nhỏ rồi cache local |
| Python | 3.13.0 | Chưa phải môi trường dự án đã khóa; nên kiểm thử stack trong môi trường Python 3.11 riêng trước implementation |
| PyTorch | 2.9.1+cpu | CUDA hiện chưa dùng được; mọi ước lượng GPU training vẫn chưa được xác minh trên máy này |
| Package | Chưa có `peft`, chưa có `faster-whisper` | Task này không cài; chỉ thêm sau approval và pin version |
| Dung lượng | Ổ D còn khoảng 80 GB; ổ C còn khoảng 12,5 GB | Model cache/dataset chỉ nên đặt trên D sau khi storage và license được duyệt; không để mặc định tải vào C |

Con số VRAM trong bảng Whisper chính thức là cho **inference**, không phải training: `base` khoảng 1 GB, `small` khoảng 2 GB; full fine-tune cần nhiều bộ nhớ hơn đáng kể. [OpenAI Whisper README](https://github.com/openai/whisper#available-models-and-languages)

## 4. Lane 1 — ASR tiếng Anh có accent Việt

### 4.1. So sánh ứng viên

| Ứng viên | Quy mô / footprint đã xác minh | Fine-tune | Ưu điểm cho đề tài | Hạn chế và quyết định |
| --- | --- | --- | --- | --- |
| `openai/whisper-small.en` | 244M tham số; khoảng 2 GB VRAM inference theo repo gốc; một bộ weights Transformers khoảng 967 MB | Hugging Face có quy trình fine-tune Whisper; PEFT hỗ trợ LoRA. Checkpoint fine-tuned có thể chuyển sang CTranslate2 để chạy bằng `faster-whisper` | English-only, footprint còn phù hợp inference local; kiến trúc ASR end-to-end; có đường triển khai local sau fine-tune | **Primary ASR baseline, nhưng chưa fine-tune ở vòng đầu.** 4 GB VRAM không đủ cơ sở để hứa full fine-tune; phải đo WER giọng Việt trước. [OpenAI model table](https://github.com/openai/whisper#available-models-and-languages), [HF fine-tune guide](https://huggingface.co/blog/fine-tune-whisper), [faster-whisper conversion](https://github.com/SYSTRAN/faster-whisper#model-conversion) |
| `openai/whisper-base.en` | 74M tham số; khoảng 1 GB VRAM inference; weights `safetensors` khoảng 290 MB | Cùng pipeline Transformers/PEFT như trên | Nhẹ hơn `small.en`, thực tế hơn cho smoke test hoặc adapter experiment giới hạn tài nguyên | **Fallback ASR.** Không mặc định chính xác đủ cho accent Việt; phải so WER trên cùng tập. [OpenAI model table](https://github.com/openai/whisper#available-models-and-languages), [HF checkpoint](https://huggingface.co/openai/whisper-base.en) |
| `facebook/wav2vec2-base-960h` | Khoảng 95M tham số; repository weights khoảng 378 MB; model card ghi Apache-2.0 | Fine-tune CTC có tài liệu/code chính thức | Baseline CTC nhỏ, có thể dùng để kiểm tra liệu adaptation L2-English có ích; hidden state cũng dùng được cho audio scorer | Native/read-speech pretraining/fine-tuning không đại diện cho SV Việt Nam; decoder/alignment phức tạp hơn Whisper cho vertical slice. **ASR challenger, không phải default.** [Model card](https://huggingface.co/facebook/wav2vec2-base-960h), [wav2vec 2.0 recipe](https://github.com/facebookresearch/fairseq/tree/main/examples/wav2vec) |

Whisper là ASR/translation model chứ không phải speaking assessor; model card yêu cầu đánh giá mạnh theo domain trước triển khai. Vì vậy ASR confidence hoặc WER không được dùng trực tiếp làm điểm Phonology. [Whisper model card](https://github.com/openai/whisper/blob/main/model-card.md)

`faster-whisper` là engine **inference** CTranslate2, không phải framework training. Nó có thể nạp local path và chuyển model Transformers đã fine-tune; cấu hình bằng tên model có thể tự tải từ Hub, nên implementation phải dùng `local_files_only`/local directory và chặn implicit download. [faster-whisper README](https://github.com/SYSTRAN/faster-whisper)

### 4.2. Dữ liệu cần có trước khi fine-tune ASR

- Audio tiếng Anh tự nhiên của đúng population, kèm bản chép tay verbatim giữ hesitation, false start, repetition, repair và code-switch.
- Chuẩn hóa transcript/version rõ ràng; không dùng chính output Whisper làm “ground truth”.
- Speaker ID giả danh để tách train/dev/test theo người nói; cùng speaker tuyệt đối không xuất hiện ở hai split.
- Metadata task, thiết bị, noise/QC và band để báo WER theo subgroup; không dùng demographic inference.
- Tập manual transcript độc lập để đo WER trước/sau adaptation; không tune trên confirmation set.

[Speak & Improve Corpus 2025](https://www.repository.cam.ac.uk/items/611e9b8b-c5b2-4cbe-9b7a-036a48334118) là ví dụ tốt về transcript L2 verbatim: paper mô tả manual transcript chứa disfluency, lỗi, hesitation, false start và repair. Tuy nhiên corpus này chỉ cấp holistic scores, là bài monologic, dùng cho nghiên cứu phi thương mại và paper cảnh báo một speaker có thể xuất hiện ở cả train/test do thiếu speaker metadata. Vì vậy chỉ dùng auxiliary research nếu license được duyệt và có thể dựng subset speaker-disjoint; không dùng official split để chứng minh claim chính. [Paper chính thức, §4](https://api.repository.cam.ac.uk/server/api/core/bitstreams/d8eb9858-b152-48f9-a19a-d17c4779d683/content)

[L2-ARCTIC](https://psi.engr.tamu.edu/l2-arctic-corpus/) có 24 người nói, trong đó chỉ bốn người Việt; phần chính là read speech, có word/phone alignment và lỗi phát âm, license CC BY-NC 4.0. Nguồn này phù hợp cho smoke test ASR/phonology và nghiên cứu accent, nhưng không có nhãn CEFR/đúng task nên không thể thay dữ liệu chính.

### 4.3. Gate để cho phép ASR adaptation

Chỉ mở fine-tune Whisper/wav2vec2 khi đồng thời có:

1. WER/substitution analysis trên tập manual transcript cho thấy lỗi ASR ảnh hưởng đáng kể đến evidence Range/Accuracy/Coherence.
2. Có đủ speaker và audio–transcript trong training folds; số giờ thực tế được báo cáo thay vì đoán ngưỡng.
3. License, consent, nơi lưu, model cache và quyền dùng compute đã được duyệt.
4. Baseline frozen được lưu với revision, decoding config và WER; adapter phải so trên cùng test speaker.
5. Tập confirmation chưa bị xem hoặc dùng để chọn checkpoint.

## 5. Lane 2 — encoder audio cho Fluency và Phonology

### 5.1. So sánh ứng viên

| Ứng viên | Quy mô / license | Cách fine-tune đề xuất | Phù hợp | Hạn chế và quyết định |
| --- | --- | --- | --- | --- |
| `facebook/wav2vec2-base` / `base-960h` | Khoảng 95M; checkpoint `base-960h` khoảng 378 MB, Apache-2.0 trên model card | Đóng băng encoder; mean/attention pooling theo thời gian; CORAL head hai ngưỡng. Chỉ unfreeze top layers sau khi head-only baseline qua CV | Có nghiên cứu gốc dùng wav2vec2 representation cho proficiency/khía cạnh L2; footprint nhỏ hơn các model 300M+ | Pretraining thiên về native read English; embedding có thể học duration, prompt hoặc speaker shortcut. **MVP audio encoder vì license rõ và triển khai đơn giản.** [Model card](https://huggingface.co/facebook/wav2vec2-base-960h), [nghiên cứu proficiency gốc](https://arxiv.org/abs/2210.13168) |
| `microsoft/wavlm-base-plus` | 12 layers, hidden size 768; checkpoint khoảng 378 MB; input 16 kHz | Frozen embedding + weighted layer pooling + criterion heads; gradual unfreeze chỉ là challenger | WavLM được thiết kế cho nhiều downstream speech tasks và denoising, nên là ứng viên kỹ thuật hợp lý cho Fluency/Phonology | WavLM cũng giữ thông tin speaker và được dùng cho speaker verification, làm tăng nguy cơ leakage. Model card hiện không khai báo metadata license; link license trên card dẫn tới CC BY-SA 3.0 ở UniSpeech, còn source WavLM ở UniLM có MIT header. **Đây là upstream ambiguity phải làm rõ trước khi fine-tune/phân phối derivative; chưa chọn làm MVP.** [Model card](https://huggingface.co/microsoft/wavlm-base-plus), [paper](https://arxiv.org/abs/2110.13900), [license mà model card trỏ tới](https://github.com/microsoft/UniSpeech/blob/main/LICENSE) |
| `facebook/hubert-base-ls960` | Khoảng 95M; Apache-2.0; input 16 kHz | Frozen encoder + head giống wav2vec2 | Ablation cùng kích thước khi cần kiểm tra độ nhạy theo encoder | Không có lý do nghiên cứu để chạy cả HuBERT, WavLM và wav2vec2 trong MVP nhỏ. **Giữ làm optional ablation.** [Model card](https://huggingface.co/facebook/hubert-base-ls960), [official fairseq docs](https://github.com/facebookresearch/fairseq/tree/main/examples/hubert) |
| GOPT | Head Transformer trên GOP; code BSD-3-Clause; dữ liệu SpeechOcean762 CC BY 4.0 | Có thể train trên GOP + canonical phone để dự đoán pronunciation aspects | Hữu ích như tài liệu/diagnostic cho phone, word, utterance pronunciation | Cần canonical text và Kaldi GOP; SpeechOcean là 5.000 câu đọc của người L1 Mandarin, không có CEFR holistic. Repo cảnh báo tutorial own-audio có bug được báo cáo. **Không dùng làm core scorer cho speech tự phát; chỉ baseline/diagnostic riêng nếu có read-aloud task.** [GOPT repo](https://github.com/YuanGongND/gopt), [paper](https://arxiv.org/abs/2205.03432), [SpeechOcean762](https://openslr.org/101/) |

Nghiên cứu wav2vec2 về L2 proficiency chứng minh representation âm thanh có thể hỗ trợ assessment và các tác giả đóng băng feature extractor trong thí nghiệm, nhưng population, rubric và split khác đề tài này. Kết quả đó chỉ biện minh việc **thử** encoder audio, không chứng minh hiệu năng trên sinh viên Việt Nam. [Bannò & Matassoni, 2022](https://arxiv.org/abs/2210.13168)

### 5.2. Nhãn và feature cần có

- Nhãn độc lập của rater cho Fluency và Phonology ở A2/B1/B2; human–human agreement phải báo trước AI–human.
- Timestamp/VAD/QC để tạo speech rate, articulation rate, pause ratio, mean length of run, voiced ratio và repair counts.
- Evidence về intelligibility/listener effort cho Phonology; không dùng “giống native” hoặc accent Việt như ground truth lỗi.
- Giữ audio encoder riêng khỏi ASR decoder. Audio head không được tự chấm Range, Accuracy, Coherence hay Interaction chỉ vì embedding có thể chứa content.
- Cache embedding theo `audio_id`, exact model revision, feature version và checksum; tuyệt đối không cache/commit audio thật trong Git.

## 6. Lane 3 — model transcript cho Range, Accuracy và Coherence

### 6.1. So sánh ứng viên

| Ứng viên | Quy mô / license | Fine-tune | Phù hợp | Hạn chế và quyết định |
| --- | --- | --- | --- | --- |
| `FacebookAI/roberta-base` | Khoảng 0,1B/125M; context 512 token; model card ghi MIT | Frozen encoder + feature thủ công + CORAL heads; sau đó thử unfreeze 1–2 lớp trên cùng CV | Đủ context cho phần lớn bài 90–120 giây, hệ sinh thái sequence classification ổn định, footprint vừa | Model pretrain trên văn bản chuẩn/web, không phải transcript L2; bias trong pretraining có thể truyền vào fine-tune. **MVP text encoder.** [Model card](https://huggingface.co/FacebookAI/roberta-base), [official RoBERTa code](https://github.com/facebookresearch/fairseq/tree/main/examples/roberta) |
| `microsoft/deberta-v3-base` | 12 layers, hidden 768; 86M backbone + 98M embedding; MIT | Head-only trước, rồi adapter/top-layer fine-tune nếu đủ data | Candidate mạnh cho sequence classification; model card có recipe fine-tune chính thức | Tổng tham số lớn hơn RoBERTa base; lợi thế trên CEFR/L2 Việt Nam chưa được đo. **Primary challenger, chỉ thay MVP nếu paired CV thắng rõ và ổn định.** [Microsoft model card](https://huggingface.co/microsoft/deberta-v3-base) |
| `sentence-transformers/all-MiniLM-L6-v2` | Weights khoảng 90,9 MB; Apache-2.0; quá 256 wordpieces bị truncate mặc định | Frozen sentence/chunk embeddings + ordinal head | CPU-friendly, tốt cho coherence/relevance ở mức câu/chunk và fallback local | Không nên nhận nguyên bài dài mà không chunk; semantic embedding không thay thế lexical/grammar evidence. **Fallback nhẹ.** [Model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) |
| `Qwen/Qwen2.5-0.5B-Instruct` hoặc LLM nhỏ tương tự | Khoảng 0,49B; Apache-2.0 theo model card | LoRA/SFT chỉ trong thí nghiệm stretch, output schema bị khóa | Có thể nghiên cứu feedback template hoặc B3 local-LLM comparator | Generative scorer dễ tạo lý do/evidence không có thật; compute/data lớn hơn discriminative encoder; không có validation cho rubric này. **Không thuộc MVP scoring.** [Qwen model card](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct), [PEFT LoRA docs](https://huggingface.co/docs/peft/main/package_reference/lora) |

`EvalYaks` là nghiên cứu gốc fine-tune Mistral-7B bằng LoRA để chấm **transcript B2** và dữ liệu hội thoại synthetic/expert-validated. Đây là comparator về ý tưởng instruction tuning, nhưng không bao phủ A2/B1, audio/Phonology hoặc population Việt Nam; metric của paper không được chuyển sang đề tài này. [Paper](https://arxiv.org/abs/2408.12226), [official repo](https://github.com/Talking-Yak/EvalYaks)

### 6.2. Input và nhãn cần có

- Cả ASR transcript và manual transcript cho một subset để đo propagation error.
- Giữ bản disfluent để truy evidence; tạo bản normalized chỉ như view có version, không ghi đè raw transcript.
- Input gồm `prompt_id`, prompt text, task type và candidate response; prompt relevance không được học chỉ từ prompt ID shortcut.
- Nhãn criterion của rater, không phải nhãn do LLM tự sinh; mỗi prediction phải gắn `evidence_ids` về span thật.
- Range: feature lexical diversity/profile/collocation kèm embedding.
- Accuracy: error candidates theo clause/AS-unit, agreement/tense/preposition và manual audit parser/ASR confusion.
- Coherence: discourse markers, semantic relation giữa units, organization và prompt relevance.
- Transcript model không được chấm Fluency/Phonology khi thiếu audio và không được chấm Interaction khi task không tạo contingency.

## 7. Lane 4 — ordinal scoring, calibration và late fusion

### 7.1. Head scoring

A2 < B1 < B2 là biến có thứ tự. Cross-entropy ba lớp không biểu diễn trực tiếp khoảng cách thứ bậc. CORAL biến bài toán thành hai ngưỡng tích lũy và ràng buộc rank consistency; phương pháp dùng được với encoder bất kỳ. [CORAL paper](https://arxiv.org/abs/1901.07884), [MIT implementation](https://github.com/Raschka-research-group/coral-pytorch)

Đề xuất cho mỗi criterion:

```text
frozen features/embedding
    -> scaling + optional dimensionality reduction fitted inside fold
    -> linear/small MLP
    -> 2 cumulative ordinal logits (A2<B1<B2)
    -> class probabilities
    -> post-hoc calibration
```

CORAL không được mặc định là tốt nhất. Phải so trên cùng speaker folds với:

- majority/prior baseline;
- multinomial logistic regression;
- regularized ordinal logistic/cumulative-link baseline;
- CORAL linear head;
- chỉ khi đủ data mới thử CORAL head + unfreeze top encoder layers.

Mỗi tiêu chí có head riêng. `overall` không được lấy trung bình cơ học sáu tiêu chí trước khi D012/overall mapping được người có thẩm quyền duyệt.

### 7.2. Calibration

- Fit temperature/sigmoid calibration chỉ trên out-of-fold hoặc development predictions, tách theo speaker.
- Không fit calibration/threshold trên confirmation set.
- Với sample nhỏ, không ưu tiên isotonic: tài liệu scikit-learn cảnh báo isotonic dễ overfit khi calibration sample nhỏ hơn nhiều so với 1.000. [CalibratedClassifierCV docs](https://scikit-learn.org/stable/modules/generated/sklearn.calibration.CalibratedClassifierCV)
- Báo Brier score/ECE/reliability plot và coverage–error trade-off của teacher-review threshold; không chỉ báo QWK.
- Confidence thấp, audio invalid, ASR risk, missing evidence hoặc model conflict phải tạo `review_reason`, không tạo điểm mặc định.

### 7.3. Late fusion

Late fusion đề xuất không trộn raw audio và text vào một generative model. Nó nhận:

```text
audio criterion probabilities + text criterion probabilities
+ engineered feature subset + QC/ASR risk + interaction evidence/missing mask
    -> regularized ordinal fusion head
    -> calibrated criterion/overall probabilities
```

Phải dùng out-of-fold predictions của base models để train fusion, nếu không fusion học trên prediction in-sample và kết quả bị lạc quan. So B0/B1/B2/M1 trên đúng một fold manifest, preprocessing và seed. Nghiên cứu multimodal có tiền lệ kết hợp audio/text cho spoken proficiency, nhưng không chứng minh late fusion này sẽ thắng trên dữ liệu đề tài; RQ2 vẫn là exploratory. [RANLP 2023 paper](https://aclanthology.org/2023.ranlp-1.83/)

Interaction chỉ đi vào fusion khi response thuộc Task C hợp lệ và có bằng chứng contingent response, turn-taking, repair/clarification và latency đã trừ system latency. Với độc thoại hoặc recorded prompt không tạo đủ contingency, dùng missing mask và `interaction=null`, không nội suy từ các criterion khác.

## 8. Shortlist cuối cùng

| Ưu tiên | Vai trò | Model/phương án | Trạng thái đề xuất |
| --- | --- | --- | --- |
| 1 | ASR inference | `whisper-small.en` + `faster-whisper` local | MVP frozen; đo WER trước adaptation |
| 2 | Audio scorer | `wav2vec2-base` frozen + feature âm học + CORAL | MVP fine-tune head |
| 3 | Text scorer | `roberta-base` frozen + feature lexical/grammar/discourse + CORAL | MVP fine-tune head |
| 4 | Fusion/calibration | Regularized ordinal late fusion + temperature/sigmoid calibration | MVP sau khi unimodal baseline hợp lệ |
| 5 | ASR fallback | `whisper-base.en` | Dùng khi compute/latency không đáp ứng |
| 6 | Audio challenger | `wavlm-base-plus` | Chỉ sau license review và leakage controls |
| 7 | Text challenger | `deberta-v3-base` | Chỉ giữ nếu paired CV cho lợi ích ổn định |
| 8 | Lightweight fallback | feature thủ công + MiniLM/chính logistic ordinal | CPU-first, ít rủi ro overfit |
| 9 | Phonology diagnostic | GOPT/SpeechOcean762 | Ngoài core spontaneous scorer |
| 10 | Generative experiment | Qwen 0.5B/EvalYaks-style LoRA | Stretch only; không tự tạo score/evidence |

## 9. Kế hoạch fine-tune theo giai đoạn

| Giai đoạn | Công việc và điều kiện dừng |
| --- | --- |
| A — chưa có nhãn rater | Không train scorer; smoke test offline; đo WER trên manual transcript giọng Việt; benchmark latency/RAM/VRAM thật, phần chưa đo ghi `[CẦN ĐO]` |
| B — có pilot và nhãn human | Split speaker trước mọi transform; trích frozen embedding; train criterion-specific CORAL/ordinal logistic trong nested GroupKFold; báo human–human trước AI–human |
| C — head-only underfit và data đủ | Thử unfreeze 1–2 lớp hoặc PEFT; paired comparison cùng fold/seed; dừng nếu gain không ổn định, calibration xấu hoặc shortcut tăng |
| D — ASR adaptation có điều kiện | PEFT Whisper trên audio–manual transcript của training speakers; so WER/disfluency/downstream propagation; chỉ checkpoint đạt gate mới chuyển CTranslate2; không dùng confirmation để chọn |

## 10. Test plan tối thiểu

| Nhóm | Kiểm tra bắt buộc |
| --- | --- |
| Leakage | Assert giao của `speaker_id` giữa mọi split bằng rỗng; cùng speaker response/prompt forms đi cùng fold |
| Pipeline fitting | Scaling/PCA/feature selection/encoder unfreeze/calibration/threshold chỉ fit trong training/inner fold |
| ASR | WER + error type; manual transcript không bắt nguồn từ chính model đang đánh giá; kiểm tra giữ disfluency |
| Evidence | Mọi `evidence_id` tồn tại; timestamp/span nằm trong source; model không tự tạo evidence |
| Construct | Interaction `null` nếu không có Task C evidence; audio-only không tự chấm text criterion; text-only không tự chấm Phonology |
| Fairness | Không phạt accent Việt; audit intelligibility disagreement và error theo thiết bị/noise/task, không suy luận thuộc tính nhạy cảm |
| Calibration | Brier/ECE/reliability plot; calibration data tách model-fit data theo speaker; threshold chọn trước confirmation |
| Reproducibility | Pin model revision, tokenizer/processor, dependency, seed, fold manifest, config và artifact hash |
| Missing/failure | Audio invalid, ASR risk, missing transcript/modal conflict tạo reason code + teacher review, không tạo điểm giả |
| Privacy | Log không chứa audio/transcript/PII; model/data cache ngoài Git; `teacher_verified` mặc định `false` |

## 11. Rủi ro quyết định

| Rủi ro | Mức | Kiểm soát |
| --- | --- | --- |
| Fine-tune backbone lớn trên quá ít speaker | Cao | Frozen baseline; small head; nested speaker CV; early stopping; giữ negative result |
| Model học giọng/speaker/device thay vì proficiency | Cao | Speaker-disjoint split; duration/prompt/device ablation; embedding leakage diagnostics |
| ASR sửa mất disfluency hoặc biến lỗi nhận dạng thành lỗi ngôn ngữ | Cao | Manual subset; disfluent transcript view; WER propagation analysis; audio evidence |
| Phonology trở thành accent-likeness | P1 | Intelligibility rubric; human audit; không dùng native distance làm nhãn chính |
| Interaction bị suy ra từ độc thoại | P1 | Nullable schema + task validity check + missing mask |
| Calibration bị fit trên test/confirmation | P1 | Nested fold implementation test + locked confirmation manifest |
| License checkpoint/derivative không rõ | Cao | Exact revision/license snapshot; legal/license owner review; không commit weights |
| Tự tải model ra ổ C hoặc gọi Hub khi chạy | Trung bình | Approved cache trên D; local path; offline/local-files-only test |

## 12. Điều kiện ra quyết định cuối

Shortlist này chưa cho phép tải hay fine-tune model. Trước implementation cần:

1. G1/G2 thực tế phê duyệt construct, rubric, Task C, rater protocol, data/storage và local-first decision liên quan.
2. Chốt model/data license inventory, đặc biệt checkpoint WavLM và các derivative weights.
3. Khóa một gói V3 gồm base commit, exact model revisions, allowed files, compute budget, acceptance và test plan.
4. Tạo môi trường Python 3.11 riêng; xác minh PyTorch CUDA tương thích RTX 3050 Ti trước khi hứa GPU training.
5. Benchmark frozen baselines trước. Chỉ model nào cải thiện có ý nghĩa trên paired speaker folds, không làm xấu calibration/fairness và giữ evidence traceability mới được chọn.

**Khuyến nghị chốt ở thời điểm hiện tại:** phê duyệt hướng “fine-tune scorer heads, không fine-tune ASR ngay”; dùng Whisper small.en frozen + wav2vec2/RoBERTa frozen + criterion-specific CORAL + late fusion/calibration. Đây là lựa chọn phù hợp nhất với compute hiện có, quy mô dữ liệu dự kiến và mục tiêu nghiên cứu low-stakes; kết quả cuối vẫn phải do thí nghiệm và human review quyết định.
