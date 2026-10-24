# Xây dựng hệ thống AI hỗ trợ đánh giá năng lực nói tiếng Anh theo CEFR cho sinh viên đại học Việt Nam ở trình độ A2-B2

## 07. Ma trận construct - nhiệm vụ - bằng chứng

| Thuộc tính | Giá trị |
| --- | --- |
| Tuần | W1 - Nền tảng đo lường, phạm vi và điều kiện nghiên cứu |
| Trạng thái | DRAFT - cần thực hiện và xác nhận |
| Người phụ trách | SV1 + SV2 |
| Người duyệt | GV Ngoại ngữ |
| Phiên bản | 1.1 |
| Ngày cập nhật | 02/09/2026 |

## 1. Nguyên tắc

Machine feature chỉ là proxy. Điểm tiêu chí phải dựa trên nhiều evidence và được kiểm định với rater. Quy tắc thiếu bằng chứng dưới đây áp dụng cho **đầu ra AI**; human rater vẫn có thể chấm trực tiếp từ audio nếu protocol cho phép và phải ghi nguồn evidence.

## 2. Ma trận chính

| Tiêu chí | Task tạo evidence | Con người quan sát | Proxy máy dự kiến | Confounder chính | Khi trả insufficient evidence |
| --- | --- | --- | --- | --- | --- |
| Range | A, B, C | Độ rộng từ/cấu trúc, paraphrase, khả năng diễn đạt ý | Lexical profile, MTLD/HD-D, n-gram/collocation, syntactic patterns, embedding coverage | ASR substitution, topic, duration | Transcript confidence thấp hoặc response quá ngắn |
| Accuracy | A, B, C | Lỗi cấu trúc/lựa chọn từ, mức cản trở nghĩa, self-repair | Error candidates theo AS-unit/clause, agreement/tense/preposition, repair patterns | ASR error, parser error, disfluency | WER/confidence không đạt; transcript thiếu đoạn |
| Fluency | A, B, C | Duy trì lời nói, pause phù hợp, hesitation/repair | Articulation rate, mean run length, pause ratio/count, repetitions, voiced ratio | Noise/VAD, task complexity, prep time | Audio clipping/silence hoặc VAD thất bại |
| Interaction | C nếu task tạo tương tác đủ | Initiative, response relevance, turn-taking, clarification, collaboration | Client-side latency, turn completion, question/response relation, clarification markers | System latency, prompt timing, interlocutor inconsistency, recorded prompt thiếu responsiveness | Không có Task C/turn log; system latency không tách được; task chỉ là chuỗi độc thoại trước prompt |
| Coherence | A, B, C | Idea progression, organisation, support, cohesion | Discourse markers, semantic continuity, topic relevance, idea units | ASR, prompt bias, memorised answer | Transcript không đủ tin cậy/response quá ngắn |
| Phonology | A, B, C | Intelligibility, sound clarity, stress/rhythm/intonation | wav2vec2 local GOP proxy, pronunciation confidence, F0/rhythm/stress metrics | Accent bias, microphone, noise, ASR alignment | Audio quality không đạt hoặc alignment fail |

## 3. Task coverage dự kiến

| Task | Dạng hoạt động | Evidence mạnh | Evidence yếu/không có |
| --- | --- | --- | --- |
| A - kể/mô tả | Sustained monologue | Range, Fluency, Coherence, Phonology | Interaction không chấm; Accuracy phụ thuộc transcript |
| B - quan điểm | Sustained monologue: putting a case | Range, Accuracy, Coherence, Fluency | Interaction không chấm |
| C - hội thoại ba lượt (PROPOSED) | Oral interaction nếu có contingent response hợp lệ | Interaction, Fluency, relevance, clarification | Coherence dài hạn có thể ít; recorded prompt có thể làm coverage tương tác yếu; cần GV Ngoại ngữ duyệt |

## 4. Evidence hierarchy

1. Audio/turn log gốc và metadata task.
2. QC flags và ASR confidence.
3. Transcript/timestamp có version.
4. Feature có version và reason code.
5. Rater scores độc lập.
6. Adjudicated label.
7. Model probability và calibration.
8. Feedback chỉ tham chiếu evidence hợp lệ.

## 5. Reason codes tối thiểu

`AUDIO_TOO_SHORT`, `HIGH_SILENCE`, `CLIPPING`, `NOISE_HIGH`, `ASR_LOW_CONFIDENCE`, `TRANSCRIPT_INCOMPLETE`, `ALIGNMENT_FAILED`, `TASK_OFF_TOPIC`, `INTERACTION_MISSING`, `SYSTEM_LATENCY_UNKNOWN`, `HUMAN_REVIEW_REQUIRED`.

## 6. Invariant của evidence

- Mỗi `evidence_id` phải trỏ tới artifact tồn tại và có `response_id`, `task_id`, `source_type`, `start_ms`/`end_ms` khi phù hợp, `extractor_version` và quality status.
- Không để LLM tự tạo timestamp, transcript, feature hoặc `evidence_id`.
- Evidence invalid không được dùng để sinh score/feedback; trả `null`/`insufficient_evidence` và `review_reason` phù hợp.
- Log vận hành không chứa audio, transcript hoặc PII; chỉ ghi ID giả danh, version, trạng thái, timing và reason code cần thiết.
- `teacher_verified=false` là mặc định; chỉ chuyển `true` sau hành động xác nhận thực tế có audit record.

## 7. Checklist review

- [ ] Mỗi criterion có human evidence trước machine proxy.
- [ ] Interaction không lấy từ A/B.
- [ ] Quality flag có thể chặn scoring.
- [ ] Confounder có kế hoạch log/kiểm tra.
- [ ] Feedback không dùng evidence bị invalid.
