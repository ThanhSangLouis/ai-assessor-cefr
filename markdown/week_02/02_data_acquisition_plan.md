# Xây dựng hệ thống AI hỗ trợ đánh giá năng lực nói tiếng Anh theo CEFR cho sinh viên đại học Việt Nam ở trình độ A2-B2

## 02. Kế hoạch tiếp nhận dữ liệu ngoài

| Thuộc tính | Giá trị |
| --- | --- |
| Trạng thái | PROPOSED - NO DOWNLOAD AUTHORIZED |
| Owner đề nghị | SV3 vận hành; GVHD phê duyệt; SV2 duyệt construct use |
| Ngày | 02/09/2026 |

## 1. Requirement

Mục tiêu không phải gom càng nhiều audio càng tốt. Mỗi corpus phải có vai trò cụ thể trong validation argument, license dùng được, split không leakage và không làm thay đổi target population claim.

## 2. Gate trước khi tải

Tất cả ô sau phải có bằng chứng:

- [ ] Dataset/version/source URL đã khóa.
- [ ] License được lưu và reviewer xác nhận mục đích sử dụng phù hợp.
- [ ] Người có thẩm quyền tự hoàn tất form/CAPTCHA/license acceptance nếu nguồn yêu cầu.
- [ ] `external_data_root` đã được phê duyệt, mã hóa và nằm ngoài repository.
- [ ] Dung lượng và checksum plan đã xác định.
- [ ] Không có điều khoản cấm loại processing dự kiến.
- [ ] Có speaker/group identifier hoặc có quyết định không dùng dataset cho evaluation.
- [ ] Có mapping từ source label sang vai trò dự án; không đổi semantics âm thầm.
- [ ] Có deletion/expiry rule theo license và DMP.

## 3. Thứ tự acquisition đề nghị

### A. L2-ARCTIC v5

1. GVHD/license owner mở trang chính thức, đọc CC BY-NC 4.0 và tự đăng ký.
2. Tải vào `external_data_root/l2_arctic/v5/raw/`, không vào Git.
3. Lưu license, source URL, ngày, archive SHA-256 và version trong manifest.
4. Xác minh bốn speaker code Vietnamese: `HQTV`, `PNV`, `THV`, `TLV`.
5. Chọn fixture deterministically sau QC; giữ speaker-disjoint nếu chia train/test.
6. Gắn purpose `ASR_PHONOLOGY_SMOKE_ONLY`; `cefr_label=null`.

### B. Speak & Improve Corpus 2025

1. Chỉ người dùng/đơn vị nghiên cứu tự điền registration và chấp nhận license Cambridge.
2. Trước tải, GVHD xác nhận hạn chế non-transferable, no redistribution và derivative release.
3. Kiểm tra material thực tế có stable speaker identifier hay không. Nếu không thể bảo đảm speaker-disjoint, đặt `evaluation_eligible=false` cho claim chính.
4. Giữ source grades nguyên bản; mapping A2+/B1+/B2+ chỉ trong config versioned và chạy sensitivity analysis.
5. Không gửi corpus tới commercial API; ưu tiên model local như chính data owner khuyến cáo.

### C. SpeechOcean762

1. Dùng OpenSLR chính thức, không dùng mirror có metadata license mâu thuẫn.
2. Xác minh archive checksum và README đi kèm.
3. Chỉ dùng fixture/pipeline test hoặc auxiliary pronunciation experiment.
4. Split theo speaker field; không dùng random utterance split.
5. Báo rõ L1 Mandarin và một nửa speaker là trẻ em.

## 4. Fixture selection

Không chọn sample vì “nghe hay” hoặc score đẹp. Sau khi corpus được phê duyệt:

1. Lọc theo purpose và QC rule đã công bố.
2. Sắp xếp bằng stable file ID.
3. Dùng seed/config cố định để lấy 3-5 sample.
4. Mỗi speaker tối đa một fixture trong smoke set, trừ test within-speaker được ghi riêng.
5. Không commit audio; test config chỉ tham chiếu `dataset_id` + `source_item_id`.

## 5. Không dùng public data cho các claim sau

- Accuracy/sáu tiêu chí trên sinh viên đại học Việt Nam A2-B2.
- Interaction nếu corpus chỉ là monologue/read speech.
- Fairness cho accent Việt từ bốn speaker.
- AI-human agreement của dự án nếu label source dùng rubric khác.
- Confirmation result nếu split nguồn có speaker leakage hoặc speaker ID không xác minh được.

## 6. Acceptance sau acquisition

- Archive và extracted tree có checksum/version/provenance.
- Raw là read-only hoặc immutable-by-process; preprocessing tạo artifact version mới.
- License inventory nêu citation, redistribution, commercial, derivative và LLM/API rules.
- Manifest không chứa tên/email hoặc contact dùng lúc đăng ký.
- Data card ghi population mismatch và allowed/prohibited use.
- Test speaker leakage chạy trước mọi experiment.

