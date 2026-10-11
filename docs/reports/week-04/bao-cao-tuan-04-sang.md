# Báo cáo tiến độ tuần 4 — Võ Thanh Sang

**Tuần:** W4, 05/10–11/10/2026. **Phụ trách:** M03 Nhận dạng giọng nói, M04 Trích đặc trưng, M05 Chấm điểm.
**Kế hoạch đối chiếu:** kế hoạch W4 của nhóm, phần "Sang" (W4-S1 đến W4-S9).
**Trạng thái nộp:** bản để nộp lên projects-fit; chưa có xác nhận GVHD.

## 1. Việc đã làm

| ID | Việc | Kết quả | Minh chứng |
| --- | --- | --- | --- |
| W4-S1 | M03-TASK-002: ASR thật (faster-whisper `small`) chạy offline | Smoke S1/S2 chạy thật, không có lần thử kết nối mạng; trạng thái `OK`, đủ trường evidence (model, phiên bản, SHA-256, cấu hình giải mã, máy, thời gian) | PR #32; [M03-EV-004](../../sdd/modules/m03-asr/evidence/evidence-manifest.md) |
| W4-S2 | M04-TASK-003: VAD thật (Silero 6.2.1) | M04-TEST-016 (Silero không nạp được thì 10 đặc trưng ngừng nghỉ rỗng kèm lý do, không dùng VAD dự phòng) và smoke S1 qua | PR #32; [M04-EV-002](../../sdd/modules/m04-features/evidence/evidence-manifest.md) |
| W4-S3 | Ghép M04→M05 cho coordinator | Coordinator gọi extractor rồi scorer; thêm `RidgeScorer.artifact` và chuyển coordinator, portal, local runtime sang dùng tên công khai (nhóm đồng ý). M05-TASK-004 đã nghiệm thu từ 03/10 | PR #32, #25 |
| W4-S4 | Gỡ số liệu suy ra từ S&I khỏi tài liệu và test M03/M05 (SCRUM-51) | Thay bằng mô tả định tính; test tính kỳ vọng từ artifact lúc chạy, không chép số. Lịch sử Git chưa viết lại | PR #32 |
| W4-S5 | Email CUP&A (SCRUM-52) | Đã soạn, chưa gửi | [email-cupa-W4-S5.md](../../evidence/00-process/email-cupa-W4-S5.md) |
| W4-S6 | Phase 07–09 cho M03-TASK-002, M04-TASK-003 | Review Phase 07 PASS (2 lỗi nhỏ đã sửa); Phase 08 trên `main` PASS; Phase 09 đã chuẩn bị. Verdict của chủ module còn để trống | [07-status M03](../../sdd/modules/m03-asr/07-status.md), [07-status M04](../../sdd/modules/m04-features/07-status.md) |
| W4-S7, S8, S9 | Error analysis, sửa status, lý do QC | Đã xong trong W3 | PR #25, #26, #27 |
| W4-C2 | AI Prompt Log tuần 4 | 17 dòng trong sheet Sang, mỗi dòng có PR làm minh chứng | [AI Prompt Log W04](../../evidence/tc2-3-ai-usage/README.md#ai-prompt-log-theo-tuan) |

**Kiểm thử trên `main` sau khi merge PR #32:**
- CI GitHub (Python 3.11): 305 test qua, 17 bỏ qua.
- Trên máy, khi có artifact Ridge: 322 test qua; 2 smoke qua.
- Độ phủ của M03/M04/M05: 96%.

**Ngoài repo nộp bài** (repo cá nhân `ThanhSangLouis/ai-assessor-cefr`, private): phát triển trước các tính năng sẽ chuyển sang repo nộp bài theo từng PR có khai nguồn:
- chế độ luyện tập theo nhiệm vụ và lộ trình bài học;
- chấm mù kép, thành tựu;
- gói dịch vụ và thanh toán ở môi trường thử, đăng nhập Google PKCE;
- giao diện mới, sơ đồ lớp v3 dạng OOP gọn, refactor.

## 2. Vướng mắc

1. **Repo nộp bài còn public và chưa có LICENSE.** Lịch sử Git vẫn còn số liệu suy ra từ S&I. Cần Thắng chuyển repo sang private (W4-T1, cần quyền admin), rồi cấp quyền đọc cho GVHD và hội đồng.
2. **Chưa có trả lời của CUP&A** về việc công bố số liệu tổng hợp và dùng model để dự đoán. Tới khi có trả lời, số liệu chỉ lưu nội bộ.
3. **Audio smoke là giọng tổng hợp do nhóm tự tạo**, không phải giọng người học. Smoke chứng minh model chạy thật, nhưng chưa quan sát được ngừng nghỉ hay độ tự tin của ASR trên người nói thật.

## 3. Kế hoạch tuần 5

1. Ghi verdict Phase 07–09 cho M03-TASK-002 và M04-TASK-003; gửi email CUP&A.
2. Thu audio của thành viên nhóm (có đồng ý bằng văn bản), chạy lại smoke S1/S2 để quan sát `asr_conf_mean` và ngừng nghỉ trên giọng thật.
3. Chuyển từ repo cá nhân sang repo nộp bài các phần M03–M05 đã sẵn sàng (Trust Layer, lá chắn ngôn ngữ, chỉ báo theo tiêu chí), mỗi phần một PR có khai nguồn và review chéo.
4. Chuẩn bị số liệu cho bản cam kết sản phẩm và bộ metric (hạn trước tuần 11).
