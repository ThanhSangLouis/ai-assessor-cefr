# Xây dựng hệ thống AI hỗ trợ đánh giá năng lực nói tiếng Anh theo CEFR cho sinh viên đại học Việt Nam ở trình độ A2-B2

## 05. Đề xuất định nghĩa construct Speaking của đề tài

| Thuộc tính | Giá trị |
| --- | --- |
| Tuần | W1 - Nền tảng đo lường, phạm vi và điều kiện nghiên cứu |
| Trạng thái | DRAFT - cần thực hiện và xác nhận |
| Người phụ trách | SV2 + GV Ngoại ngữ |
| Người duyệt | GVHD |
| Phiên bản | 1.1 |
| Ngày cập nhật | 02/09/2026 |

## 1. Construct statement

**Trạng thái: PROPOSED theo D002-D006.** Đề tài dự kiến đánh giá khả năng của sinh viên đại học Việt Nam sử dụng tiếng Anh để thực hiện các nhiệm vụ spoken production và spoken interaction ở dải A2-B2, thể hiện qua Range, Accuracy, Fluency, Interaction, Coherence và Phonology. Kết quả là hồ sơ ước lượng có bằng chứng và confidence trong bối cảnh formative/low-stakes, không phải chứng chỉ CEFR. Nội dung này chỉ được khóa sau review thực tế của GV Ngoại ngữ và GVHD.

## 2. Đơn vị suy luận

- Đơn vị quan sát: một response cho một task/prompt.
- Đơn vị đánh giá: hồ sơ theo criterion của người nói qua nhiều response.
- Đơn vị tách dữ liệu: speaker.
- Đối tượng suy luận: sinh viên đại học Việt Nam từ 18 tuổi, A2-B2.

## 3. Các hoạt động trong phạm vi

| Hoạt động | Trong MVP | Lý do |
| --- | --- | --- |
| Kể/mô tả trải nghiệm | Có | Tạo evidence cho production, Range, Fluency, Coherence, Phonology |
| Trình bày quan điểm/lập luận | Có | Tạo evidence cho development, support và language range |
| Hội thoại bán cấu trúc | Có điều kiện, chưa duyệt phương thức interlocutor | Cần để tạo evidence cho Interaction; nhãn Task C tự thân chưa bảo đảm interactional authenticity |
| Mediation từ nguồn văn bản/audio | Không | Chưa có task riêng; tránh mở rộng construct |
| Đọc thành tiếng | Không dùng để chấm overall | Dễ đo phát âm nhưng coverage giao tiếp yếu |

## 4. Sáu tiêu chí

### Range

Mức người học huy động cấu trúc, từ vựng, cụm từ và cách diễn đạt để hoàn thành thông điệp. Đo breadth và functional adequacy, không chỉ đếm type/token.

### Accuracy

Mức kiểm soát cấu trúc và lựa chọn từ trong ngữ cảnh task. Đánh giá mức lỗi gây cản trở ý nghĩa, tính hệ thống, khả năng tự sửa; phải loại ảnh hưởng ASR.

### Fluency

Khả năng giữ lời nói tiếp diễn, lập kế hoạch và sửa mà không làm mất khả năng theo dõi. Tốc độ, pause và repetition là evidence chứ không phải construct.

### Interaction

Khả năng nghe-phản hồi, khởi tạo/duy trì/kết thúc, giữ lượt, phối hợp và làm rõ. Chỉ chấm khi task thực sự tạo bằng chứng tương tác, có turn log và prompt timing hợp lệ. Nếu không đủ, không suy diễn từ monologue hoặc latency đơn lẻ.

### Coherence

Khả năng phát triển ý, sắp xếp trình tự, hỗ trợ luận điểm và liên kết các phần thành diễn ngôn có thể theo dõi.

### Phonology

Mức kiểm soát âm và prosody đủ để thông điệp dễ hiểu. Accent được chấp nhận; chỉ quan tâm khi ảnh hưởng intelligibility hoặc làm interlocutor tăng effort đáng kể.

## 5. Chuỗi suy luận

`Task performance -> audio/transcript/turn evidence -> human criterion rating -> adjudicated reference label -> model probability -> calibrated confidence -> teacher review -> formative feedback`

Mỗi mũi tên phải có version, quality flag và log.

### Quy tắc dữ liệu khi thiếu Interaction

```json
{
  "interaction": {
    "level": null,
    "score_status": "insufficient_evidence",
    "evidence_ids": [],
    "review_reason": "INTERACTION_MISSING"
  }
}
```

Không thay `null` bằng A2, 0 hoặc trung bình của tiêu chí khác. `teacher_verified` mặc định là `false` cho đến khi có hành động xác nhận thực tế.

## 6. Construct exclusions

- Không đánh giá trí thông minh, tính cách, cảm xúc, động lực hoặc giới tính.
- Không đánh giá kiến thức chuyên ngành ngoài yêu cầu task.
- Không đánh giá khả năng đọc/viết trừ khi task chủ ý tích hợp và báo riêng.
- Không xem accent là lỗi.
- Không suy luận C1/C2 hoặc A1.
- Không cấp chứng chỉ hoặc quyết định học vụ tự động.

## 7. Construct under-representation cần theo dõi

- Không có Task C thì Interaction không được bao phủ.
- Chỉ dùng prompt quen thuộc có thể không đại diện non-routine language use.
- Audio-only không quan sát gesture/facial expression.
- Mẫu nhỏ có thể không bao phủ đủ prompt/device/noise.

## 8. Construct-irrelevant variance cần theo dõi

- Prompt đọc quá khó.
- Topic đòi hỏi kiến thức văn hóa/chuyên ngành.
- ASR sai do accent/noise.
- Microphone/connection làm mất âm.
- Interlocutor hỗ trợ không nhất quán.
- Thời gian chuẩn bị khác nhau.

## 9. Quyết định cần duyệt

- [ ] D003: construct statement và sáu tiêu chí được GV Ngoại ngữ duyệt.
- [ ] D004: Interaction chỉ từ task có bằng chứng tương tác đủ, dự kiến Task C.
- [ ] D005: Mediation ngoài MVP.
- [ ] D006: Phonology lấy intelligibility làm trọng tâm, không phạt accent.
- [ ] Rater workflow kiểm thử cognitive load trước khi khóa rubric.

## 10. Nguồn

- [CEFR Companion Volume 2020](https://rm.coe.int/cefr-companion-volume-with-new-descriptors-2020/16809ea0d4), oral production, oral interaction, phonological control và Appendix 3.
- [Manual for Relating Examinations to the CEFR 2009](https://rm.coe.int/1680667a2d), Specification và Standardisation.
