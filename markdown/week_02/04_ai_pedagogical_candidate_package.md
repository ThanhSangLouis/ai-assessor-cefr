# Xây dựng hệ thống AI hỗ trợ đánh giá năng lực nói tiếng Anh theo CEFR cho sinh viên đại học Việt Nam ở trình độ A2-B2

## 04. Candidate package tuần 2 do AI chuẩn bị

| Thuộc tính | Giá trị |
| --- | --- |
| Phạm vi | W2-01 đến W2-16 ở mức draft để G1/G2 và rater review |
| Trạng thái | DRAFT PREPARED - NOT HUMAN APPROVED, NO DATA ACQUISITION |
| Phiên bản | 0.1 |
| Ngày | 12/09/2026 |
| Nguồn chuẩn | W1 construct/evidence/ALTE/RQ, decision log và CEFR sources đã dẫn |

Package này không tự đóng G1/G2, không tạo anchor hoặc metric giả và không cho phép thu/tải dữ liệu. Mọi giá trị timing, prompt, threshold và sampling là candidate phải pilot.

## 1. Rubric candidate A2-B2

Quy tắc chung: chọn band mô tả tốt nhất toàn bộ evidence hợp lệ của criterion; không cộng điểm feature để gán band. Nếu task hoặc dữ liệu không tạo đủ evidence, chọn `insufficient_evidence` thay vì A2 hoặc 0.

| Criterion | A2 | B1 | B2 | Không đủ bằng chứng khi |
| --- | --- | --- | --- | --- |
| Range | Dùng mẫu câu/cụm từ cơ bản cho chủ đề quen thuộc; thường đơn giản hóa thông điệp | Có đủ ngôn ngữ để xử lý chủ đề quen thuộc, kể/giải thích và vòng diễn đạt khi thiếu từ | Diễn đạt rõ, hỗ trợ quan điểm bằng phạm vi từ/cấu trúc tương đối rộng; ít phải hạn chế thông điệp | Response quá ngắn hoặc transcript không đủ tin cậy để quan sát phạm vi |
| Accuracy | Một số cấu trúc đơn giản đúng; lỗi cơ bản còn hệ thống nhưng ý chính thường hiểu được | Kiểm soát tương đối các mẫu quen thuộc; lỗi tăng khi diễn đạt phức nhưng ý định rõ | Kiểm soát tương đối cao; lỗi hiếm khi gây hiểu nhầm và có self-repair phù hợp | Audio/transcript thiếu đoạn hoặc ASR risk không được giải quyết bằng nghe trực tiếp |
| Fluency | Tạo lượt nói ngắn với pause/false start rõ; có thể tiếp tục trong nội dung quen thuộc | Duy trì đoạn nói dễ theo dõi dù pause lập kế hoạch/sửa còn rõ | Nhịp tương đối đều trong đoạn dài; do dự ít làm gián đoạn khả năng theo dõi | Clipping, silence, VAD failure hoặc thời lượng không tạo đủ speech |
| Interaction | Hỏi/đáp routine, thường cần hỗ trợ; phản hồi được lượt đơn giản | Khởi tạo/duy trì/kết thúc trao đổi đơn giản; yêu cầu lặp/làm rõ khi cần | Lấy lượt, phản hồi và chủ động giúp thảo luận tiến triển; repair phù hợp | Không có contingent interaction, turn log hoặc không tách được system latency |
| Coherence | Nối câu/ý bằng connector phổ biến; thường theo dạng danh sách | Tạo chuỗi tuyến tính dễ theo dõi; kể/mô tả có trình tự | Phát triển và hỗ trợ ý thành diễn ngôn rõ bằng cohesive devices phù hợp | Response/transcript quá ngắn, thiếu đoạn hoặc task không tạo extended discourse |
| Phonology | Nhìn chung hiểu được; đôi lúc cần lặp, L1 influence có thể tăng listener effort | Nhìn chung intelligible; mispronunciation không ngăn hiểu thông điệp | Âm/stress/rhythm/intonation hỗ trợ thông điệp; accent còn nhưng ít ảnh hưởng intelligibility | Audio quality/alignment không đủ để nghe hoặc xác định breakdown |

## 2. Rating manual candidate

### 2.1. Trình tự

1. Xác minh `response_id`, `task_id`, prompt và QC status; không xem identity, AI prediction hoặc rating khác.
2. Lượt nghe 1: holistic impression và task completion flag, chưa điền analytic band chi tiết.
3. Lượt nghe 2: chấm từng criterion từ evidence audio; ghi một evidence note ngắn cho mỗi band.
4. Nếu criterion thiếu cơ hội quan sát hoặc dữ liệu invalid, ghi `null` + reason code.
5. Ghi confidence của rater `LOW/MEDIUM/HIGH`; không dùng confidence để tự đổi band.
6. Adjudication chỉ sau khi hai rating độc lập đã khóa.

### 2.2. Quy tắc tránh bias

- Không phạt accent Việt nếu thông điệp intelligible.
- Không xem transcript ASR ở vòng độc lập.
- Không suy Accuracy từ lỗi transcript chưa được xác minh.
- Không suy Interaction từ speech rate, monologue hoặc thời gian im lặng đơn lẻ.
- Off-topic là flag riêng; criterion nào vẫn có evidence thì vẫn chấm.
- Tối đa hai lượt nghe ở vòng độc lập; lượt bổ sung chỉ trong adjudication có reason code.

### 2.3. Adjudication candidate

Chuyển adjudication khi: khác overall band; hoặc khác từ một band ở ít nhất hai criterion; hoặc một rater ghi validity/evidence flag nghiêm trọng. Luôn báo pre-adjudication agreement trước label phân xử.

## 3. Task blueprint và prompt bank candidate

### Task A - kể/mô tả

- Thời lượng candidate: 90-120 giây; chuẩn bị 30 giây.
- Evidence chính: Range, Fluency, Coherence, Phonology; Accuracy khi evidence đủ.
- Interaction luôn `insufficient_evidence`.

Prompt A1: “Describe a memorable day at university. Say what happened, who was involved, and why you remember it.”

Prompt A2: “Describe a place at your university that is useful or important to you. Say what it is like, what you do there, and why it matters.”

### Task B - quan điểm

- Thời lượng candidate: 120 giây; chuẩn bị 30 giây; ba bullet scaffold.
- Evidence chính: Range, Accuracy, Fluency, Coherence, Phonology.
- Interaction luôn `insufficient_evidence`.

Prompt B1: “Should university students have a part-time job? Explain your view. You may talk about benefits, difficulties, and an example.”

Prompt B2: “Which is better for university students: studying alone or studying in a group? Explain your view. You may compare both choices, give reasons, and add an example.”

### Task C - hội thoại bán cấu trúc

- Thời lượng candidate: 3-4 phút; tối thiểu ba exchange có contingency.
- Delivery ưu tiên: human interlocutor theo branching script, không coaching.
- Evidence chính: Interaction, Fluency, response relevance và clarification; criterion khác chỉ chấm khi đủ evidence.

Scenario C1: người học và interlocutor lên kế hoạch một hoạt động câu lạc bộ với ngân sách/thời gian hạn chế.

1. Interlocutor hỏi đề xuất ban đầu.
2. Nếu người học đề xuất địa điểm/thời gian, interlocutor đưa một constraint đã định trước.
3. Interlocutor yêu cầu người học so sánh hai phương án hoặc làm rõ.
4. Người học được tạo một câu hỏi/đề nghị; interlocutor phản hồi theo nhánh chuẩn.
5. Hai bên thống nhất hoặc nêu bất đồng còn lại.

Scenario C2: người học và interlocutor xử lý xung đột lịch cho bài thuyết trình nhóm.

1. Interlocutor nêu lịch candidate.
2. Người học phải phản hồi và đề xuất thay thế.
3. Interlocutor đưa constraint về một thành viên/địa điểm.
4. Người học hỏi làm rõ hoặc điều chỉnh kế hoạch.
5. Hai bên tóm tắt quyết định.

Intervention rule: sau 8-10 giây không có response, dùng prompt hỗ trợ mức 1 đã soạn; không giải thích nội dung thay người học. Mỗi intervention phải có mã/timestamp. Recorded prompt tree chỉ là fallback và không mặc định đủ bằng chứng Interaction.

## 4. Prompt equivalence và RQ6

- Hai form cùng blueprint, instruction load, expected discourse functions, thời lượng và mức quen thuộc topic.
- Pilot ghi completion, response duration, rater distribution và perceived difficulty; không kết luận equivalence chỉ từ wording.
- Paired subset thực hiện cả A1/A2, counterbalance thứ tự và tách đủ xa để giảm carryover.
- Cỡ paired subset chỉ khóa sau precision analysis; ngoài subset có thể phân một form/người.

## 5. Rating form candidate

| Field | Kiểu/quy tắc |
| --- | --- |
| `rating_id` | UUID/internal stable ID |
| `response_id`, `task_id` | Pseudonymous foreign keys |
| `rater_id` | Role ID, không chứa tên |
| `rubric_version`, `prompt_version` | Bắt buộc |
| `criterion_ratings` | Sáu record: `level`, `evidence_status`, `evidence_note`, `reason_codes`, `confidence` |
| `task_relevance` | `ON_TOPIC/PARTIAL/OFF_TOPIC/NOT_ASSESSABLE` |
| `holistic_impression` | Candidate A2/B1/B2/null; không tự tính từ analytic ratings |
| `listen_count` | 1-2 ở independent phase |
| `rating_phase` | `INDEPENDENT/ADJUDICATION/TEACHER_REVIEW` |
| `teacher_verified` | Mặc định `false`; chỉ true khi có audit record thật |
| `created_at`, `rating_protocol_version` | Bắt buộc |

## 6. Reason-code schema candidate v0.1

| Nhóm | Codes |
| --- | --- |
| Audio/QC | `AUDIO_UNSUPPORTED`, `AUDIO_TOO_SHORT`, `AUDIO_TOO_LONG`, `HIGH_SILENCE`, `CLIPPING`, `NOISE_HIGH`, `VAD_FAILED` |
| ASR/alignment | `ASR_FAILED`, `ASR_LOW_CONFIDENCE`, `TRANSCRIPT_INCOMPLETE`, `ALIGNMENT_FAILED` |
| Task/evidence | `TASK_OFF_TOPIC`, `RESPONSE_TOO_SHORT`, `INTERACTION_MISSING`, `CONTINGENCY_MISSING`, `SYSTEM_LATENCY_UNKNOWN` |
| Review | `HUMAN_REVIEW_REQUIRED`, `RATER_DISAGREEMENT`, `ADJUDICATION_REQUIRED`, `CONFIG_VERSION_MISMATCH` |
| Data/privacy | `IDENTITY_FIELD_REJECTED`, `UNAPPROVED_DATA_ROOT`, `PROVENANCE_MISSING` |

Reason code phải machine-readable, không chứa transcript/PII và không được dùng thay evidence note của rater.

## 7. `speaking_profile` candidate v0.1

```json
{
  "participant_id": "PTEST-0001",
  "response_ids": ["RTEST-0001"],
  "rubric_version": "rubric-v0.1-candidate",
  "model_version": null,
  "calibration_version": null,
  "overall": {
    "level": null,
    "score_status": "not_scored_vertical_slice",
    "confidence": null,
    "evidence_ids": [],
    "review_reason": "MODEL_NOT_AVAILABLE"
  },
  "criteria": {
    "interaction": {
      "level": null,
      "score_status": "insufficient_evidence",
      "confidence": null,
      "evidence_ids": [],
      "review_reason": "INTERACTION_MISSING"
    }
  },
  "teacher_verified": false,
  "review_audit_ref": null
}
```

Ví dụ là synthetic và cố ý không tạo điểm CEFR. Production schema phải có đủ sáu criterion và validate evidence references.

## 8. Latency measurement protocol candidate

- Ghi riêng `prompt_playback_end_ms`, `mic_capture_start_ms`, `speech_onset_ms`, `speech_offset_ms` và `system_clock_source`.
- `human_response_latency_ms = speech_onset_ms - prompt_playback_end_ms` chỉ hợp lệ khi cùng clock và không có capture gap.
- `system_capture_latency_ms = mic_capture_start_ms - prompt_playback_end_ms` được báo riêng, không gộp vào năng lực Interaction.
- Timestamp invalid/khác clock hoặc dropped event phải tạo `SYSTEM_LATENCY_UNKNOWN`.
- Không dùng latency đơn lẻ để gán band; chỉ là evidence phụ sau pilot.

## 9. Anchor và calibration plan

- Anchor chỉ từ audio public có license phù hợp hoặc pilot được consent; không commit audio.
- Hai rater chấm độc lập trước thảo luận; AI/synthetic label không làm reference.
- Coverage tối thiểu: A2/B1/B2, mỗi band có clear và near-boundary case nếu dữ liệu cho phép.
- Session gồm familiarisation, blind rating, discussion theo evidence, re-rating và record deviation.
- Không đặt target agreement như kết quả giả. Báo observed agreement, uncertainty và unresolved cases.

## 10. Data schema candidate

Các entity tối thiểu: `ParticipantAlias`, `Session`, `TaskPrompt`, `Response`, `AudioArtifact`, `QcResult`, `TranscriptArtifact`, `FeatureSet`, `Evidence`, `HumanRating`, `Adjudication`, `ProcessingRun`, `TeacherReview`.

Invariant:

- Identity/contact không nằm trong research database.
- Mỗi artifact có version/provenance/hash phù hợp.
- `speaker_id` là khóa group split; cùng speaker không xuất hiện ở nhiều split.
- `Evidence` phải tồn tại trước score/feedback tham chiếu.
- `teacher_verified=true` cần `TeacherReview` audit record.
- Raw audio/transcript không xuất hiện trong log.

## 11. Fixture catalog plan

| Fixture ID | Loại | Mục đích | Trạng thái |
| --- | --- | --- | --- |
| `SYN-AUDIO-VALID-001` | Synthetic generated tone/speech-like envelope, không người thật | Audio validation happy path | TO CREATE IN APPROVED IMPLEMENTATION |
| `SYN-AUDIO-SHORT-001` | Synthetic | `AUDIO_TOO_SHORT` | TO CREATE IN APPROVED IMPLEMENTATION |
| `SYN-AUDIO-CLIP-001` | Synthetic | Clipping detection | TO CREATE IN APPROVED IMPLEMENTATION |
| `FAKE-ASR-001` | Typed fixture, không transcript người thật | Deterministic ASR adapter test | TO CREATE IN APPROVED IMPLEMENTATION |
| `EXT-L2A-VI-001` | External reference by source ID only | Optional ASR/Phonology smoke | BLOCKED BY LICENSE/STORAGE APPROVAL |

Selection dùng config/seed ổn định; không chọn sample vì score đẹp. Audio ngoài không được commit.

## 12. Precision-analysis specification

Artifact W2-15 phải mô phỏng theo speaker cluster, ordinal A2/B1/B2 và các scenario về prevalence/agreement. Config tối thiểu gồm estimand, sample range, responses/speaker, paired-subset size, assumed confusion matrices, missingness, seed và số lần lặp. Output phải báo interval width/power hoặc probability đạt precision target theo scenario; không chọn một scenario đẹp làm kết quả duy nhất.

Các planning number 60/70-90/25-30 chỉ là input scenario cho đến khi script/config/output được review. Confirmation/pilot data không được dùng để tune assumption rồi gọi là preregistered.

## 13. Contract/invariant test plan

| ID | Test | Kỳ vọng |
| --- | --- | --- |
| W2-T01 | Monologue rating | Interaction luôn null + `INTERACTION_MISSING` |
| W2-T02 | Missing evidence | Không tạo A2/0/default band |
| W2-T03 | Evidence reference | Ref không tồn tại bị reject |
| W2-T04 | Teacher verification | Không thể true nếu thiếu review audit |
| W2-T05 | Speaker split | Cùng speaker ở hai split làm test fail |
| W2-T06 | Privacy log | Transcript/audio/identity field bị reject hoặc redacted theo spec |
| W2-T07 | Versioning | Thiếu rubric/prompt/feature/model version phù hợp làm validation fail |
| W2-T08 | Task C timing | Khác clock/missing event tạo `SYSTEM_LATENCY_UNKNOWN` |
| W2-T09 | Reproducibility | Cùng fixture/config/seed cho output deterministic ở phần pure logic |

## 14. Trạng thái W2-01 đến W2-16 sau package

| Nhóm | Trạng thái trung thực |
| --- | --- |
| W2-01 đến W2-10 | DRAFT CANDIDATE PREPARED; chờ G1/G2, pilot và human review |
| W2-11/W2-14 | RESEARCH/PLAN PREPARED; không có anchor/audio acquisition |
| W2-12/W2-13 | DRAFT PLAN PREPARED; chưa có rater session/production database |
| W2-15 | SPEC PREPARED; chưa có script/config/output |
| W2-16 | TEST PLAN PREPARED; chưa implement/chạy |

Không hạng mục nào trong bảng này được gọi là `APPROVED`, `PASS` hoặc `DONE` chỉ vì package đã có nội dung.
